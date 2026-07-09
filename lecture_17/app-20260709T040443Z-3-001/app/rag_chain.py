# rag_chain.py — All RAG logic: embeddings, indexing, querying, and document management.
#
# PIPELINE OVERVIEW
#
# UPLOAD (indexing):
#   File on disk
#     ↓  file_loader.py                    load pages/rows into Documents
#     ↓  RecursiveCharacterTextSplitter    split into ~500-char chunks
#     ↓  embeddings.embed_query()          convert each chunk to a vector
#     ↓  qdrant_client.upsert()            store vector + metadata in Qdrant
#
# QUERY:
#   User question (str)
#     ↓  embeddings.embed_query()          convert question to a vector
#     ↓  qdrant_client.query_points()      find the top-K most similar chunks
#     ↓  extract .payload                  get file_name, page_number, chunk_text
#     ↓  build context string              combine chunks into one block of text
#     ↓  prompt | llm | StrOutputParser    generate the answer (same LCEL from Lecture 10)

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.models import Reference   # app.models because we are inside the app/ package

logger = logging.getLogger(__name__)

CHUNK_SIZE    = 500   # Max characters per chunk
CHUNK_OVERLAP = 50    # Characters shared between consecutive chunks to preserve context


# ─────────────────────────────────────────────────────────────────────────────
# EMBEDDINGS
# ─────────────────────────────────────────────────────────────────────────────

def get_embeddings(provider: str):
    """
    Return the embedding model.
    "openai"      → text-embedding-3-small  (1536 dims, paid API call)
    "huggingface" → all-MiniLM-L6-v2        (384 dims, free, runs on your CPU)
    """
    if provider == "openai":
        return OpenAIEmbeddings(model="text-embedding-3-small")
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# ─────────────────────────────────────────────────────────────────────────────
# QDRANT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_qdrant_client(url: str, api_key: str) -> QdrantClient:
    """Create and return a Qdrant client connected to the cloud cluster."""
    return QdrantClient(url=url, api_key=api_key)


def compute_doc_id(file_name: str) -> str:
    """
    Produce a short, stable ID for a file by hashing its name.
    Same filename → same ID every time.
    Every chunk of a file stores this ID, so we can find and delete them all with one filter.
    """
    return hashlib.sha256(file_name.encode()).hexdigest()[:16]


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """Return True if the named collection already exists in Qdrant."""
    existing = [c.name for c in client.get_collections().collections]
    return collection_name in existing


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int):
    """
    Create the Qdrant collection if it does not exist yet.
    Also creates a keyword payload index on 'doc_id' — required for DELETE filtering.
    If the collection already exists with a different vector dimension, raise a clear error.
    """
    if not collection_exists(client, collection_name):
        # Create the collection — cosine similarity is standard for text embeddings
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(f"Created collection '{collection_name}' ({vector_size} dims)")

        # Create the doc_id keyword index — required for DELETE filtering
        client.create_payload_index(
            collection_name=collection_name,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        return   # New collection — no dimension check needed

    # Collection already exists — ensure the doc_id index is present.
    # Old collections created before this fix may be missing it.
    # Qdrant silently ignores this call if the index already exists.
    client.create_payload_index(
        collection_name=collection_name,
        field_name="doc_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    # Make sure its dimension matches our embedding model
    info        = client.get_collection(collection_name)
    vectors_cfg = info.config.params.vectors

    # Newer qdrant-client returns a dict {"": VectorParams}; older returns VectorParams directly
    if isinstance(vectors_cfg, dict):
        existing_size = list(vectors_cfg.values())[0].size
    else:
        existing_size = vectors_cfg.size

    if existing_size != vector_size:
        raise ValueError(
            f"Collection '{collection_name}' was built with {existing_size}-dim vectors "
            f"but the current embedding model produces {vector_size}-dim vectors. "
            f"Change EMBEDDING_PROVIDER in .env to match, or delete the collection "
            f"in Qdrant Cloud and restart the server."
        )


# ─────────────────────────────────────────────────────────────────────────────
# INDEXING
# ─────────────────────────────────────────────────────────────────────────────

def index_documents(docs_by_file: dict, client: QdrantClient, embeddings, collection_name: str) -> dict:
    """
    Split, embed, and store documents in Qdrant. Handles re-uploads correctly.

    Args:
        docs_by_file: {file_name: List[Document]} — output from file_loader.load_file()

    Returns:
        {file_name: {"doc_id": str, "chunks_created": int}}

    Every Qdrant point stores this payload:
        file_name, file_type, page_number, chunk_index, doc_id, chunk_text, upload_timestamp
    """
    splitter  = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    results   = {}     # Will hold the return value — one entry per file
    all_points: list = []   # All Qdrant points built across every file
    upload_ts = datetime.now(timezone.utc).isoformat()   # Single timestamp for this batch
    collection_ready = False   # Tracks whether ensure_collection has been called yet

    for file_name, docs in docs_by_file.items():
        doc_id      = compute_doc_id(file_name)    # Stable ID for this file
        chunks      = splitter.split_documents(docs)  # Split pages/sections into small chunks
        actual_count = 0   # Count only non-empty chunks that actually get indexed

        logger.info(f"  '{file_name}': {len(docs)} doc(s) → {len(chunks)} raw chunks")

        for idx, chunk in enumerate(chunks):
            text = chunk.page_content.strip()   # Remove whitespace
            if not text:
                continue   # Skip blank pages or empty rows

            vector = embeddings.embed_query(text)   # Convert text to a float vector

            # On the very first vector we create, set up the Qdrant collection.
            # This is the earliest point we know the vector dimension — doing it
            # here avoids wasting embed calls if the collection has a dimension mismatch.
            if not collection_ready:
                ensure_collection(client, collection_name, len(vector))
                collection_ready = True

            all_points.append(PointStruct(
                id      = str(uuid.uuid4()),   # Random unique ID for this Qdrant point
                vector  = vector,
                payload = {
                    "file_name":         file_name,
                    "file_type":         chunk.metadata.get("file_type", "unknown"),
                    "page_number":       chunk.metadata.get("page_number", 1),
                    "chunk_index":       idx,       # Position of this chunk within the file
                    "doc_id":            doc_id,    # Links ALL chunks of this file together
                    "chunk_text":        text,      # Stored for instant citation display
                    "upload_timestamp":  upload_ts,
                },
            ))
            actual_count += 1   # Only count chunks that were actually embedded

        results[file_name] = {"doc_id": doc_id, "chunks_created": actual_count}

    if not all_points:
        logger.warning("No non-empty chunks found to index")
        return results

    # Delete old chunks for every file being re-uploaded.
    # Without this, uploading the same file twice creates duplicate chunks.
    for file_name in docs_by_file:
        old_count = delete_indexed_document(compute_doc_id(file_name), client, collection_name)
        if old_count > 0:
            logger.info(f"  Replaced {old_count} old chunks for '{file_name}'")

    # Store all new points in a single Qdrant batch call (faster than one-by-one)
    client.upsert(collection_name=collection_name, points=all_points)
    logger.info(f"Stored {len(all_points)} chunks in '{collection_name}'")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# QUERYING
# ─────────────────────────────────────────────────────────────────────────────

def query_with_references(
    question: str,
    top_k: int,
    client: QdrantClient,
    embeddings,
    llm: ChatOpenAI,
    collection_name: str,
) -> dict:
    """
    Answer a question using the indexed documents and return source references.
    Returns: {"answer": str, "references": List[Reference]}
    """
    # Return early if no documents have been uploaded yet (collection does not exist)
    if not collection_exists(client, collection_name):
        return {
            "answer":     "No documents have been uploaded yet. Please upload files first.",
            "references": [],
        }

    # Step 1: Convert the question into a vector so we can do similarity search
    query_vector = embeddings.embed_query(question)

    # Step 2: Find the top_k chunks most similar to the question vector.
    # with_payload=True → get the stored metadata back (file_name, page_number, etc.)
    # with_vectors=False → skip returning raw float arrays (we don't need them)
    results = client.query_points(
        collection_name = collection_name,
        query           = query_vector,
        limit           = top_k,
        with_payload    = True,
        with_vectors    = False,
    )

    # If the collection exists but has no points, nothing has been indexed yet
    if not results.points:
        return {
            "answer":     "No documents have been uploaded yet. Please upload files first.",
            "references": [],
        }

    # Step 3: Build the references list and context string from the search results
    references: List[Reference] = []
    context_parts: List[str]    = []

    for hit in results.points:
        p = hit.payload   # The metadata dict we stored during indexing

        references.append(Reference(
            file_name       = p["file_name"],
            file_type       = p.get("file_type", "unknown"),
            page_number     = p.get("page_number", 1),
            chunk_index     = p.get("chunk_index", 0),
            chunk_text      = p["chunk_text"],
            relevance_score = round(hit.score, 4),   # Cosine similarity: higher = more relevant
        ))

        # Label each context section with its source so the LLM can attribute answers
        context_parts.append(
            f"[{p['file_name']} — page {p.get('page_number', '?')}]\n{p['chunk_text']}"
        )

    context = "\n\n---\n\n".join(context_parts)   # Single context block passed to the LLM

    # Step 4: Generate the answer using LCEL — same | operator from Lecture 10
    prompt = ChatPromptTemplate.from_template(
        """You are a helpful assistant. Answer the question using ONLY the context below.
Do NOT mention file names, page numbers, or sources in your answer — those are shown separately.
If the answer is not in the context, say "I couldn't find that in the uploaded documents."

Context:
{context}

Question: {question}

Answer:"""
    )

    chain  = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    return {"answer": answer, "references": references}


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def list_indexed_documents(client: QdrantClient, collection_name: str) -> List[dict]:
    """
    Return one summary entry per file (not per chunk).
    Returns an empty list if no files have been uploaded yet.
    """
    # If no collection exists yet, no files have been uploaded — return empty list
    if not collection_exists(client, collection_name):
        return []

    seen   = {}     # {doc_id: aggregated info dict}
    offset = None   # Qdrant scroll cursor — None starts from the beginning

    while True:
        # Fetch up to 200 points at a time (pagination)
        records, next_offset = client.scroll(
            collection_name = collection_name,
            limit           = 200,
            offset          = offset,
            with_payload    = True,
            with_vectors    = False,
        )

        for record in records:
            p      = record.payload
            doc_id = p.get("doc_id", "unknown")

            if doc_id not in seen:
                # First time we see this doc_id — create its entry
                seen[doc_id] = {
                    "doc_id":           doc_id,
                    "file_name":        p.get("file_name", "unknown"),
                    "file_type":        p.get("file_type", "unknown"),
                    "upload_timestamp": p.get("upload_timestamp", ""),
                    "chunk_count":      0,
                }
            seen[doc_id]["chunk_count"] += 1   # Count every chunk belonging to this file

        if next_offset is None:
            break   # scroll() returns None when there are no more pages
        offset = next_offset

    return list(seen.values())


def delete_indexed_document(doc_id: str, client: QdrantClient, collection_name: str) -> int:
    """
    Delete every chunk in Qdrant that belongs to this doc_id.
    Returns the number of points deleted (0 if doc_id not found).
    Filtering by doc_id works because we created a keyword payload index in ensure_collection().
    """
    # Guard: if collection doesn't exist, nothing to delete
    if not collection_exists(client, collection_name):
        return 0

    # Filter: match all points where payload.doc_id == doc_id
    filt = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))])

    # Count first so we can return how many were removed
    count_result = client.count(collection_name=collection_name, count_filter=filt)
    n = count_result.count

    if n > 0:
        client.delete(collection_name=collection_name, points_selector=filt)

    return n
