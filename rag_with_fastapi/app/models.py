from pydantic import BaseModel, Field
from typing import List, Optional

class Reference(BaseModel):
    file_name: str
    file_type: str
    page_number: int
    chunk_text: str
    chunk_index: int
    relevance_score: float


class QueryRequest(BaseModel):
    """What the user sends when asking a question."""
    question: str                                              # The question to answer
    top_k: int = Field(default=5, ge=1, le=20)               # How many chunks to retrieve (1–20)


class QueryResponse(BaseModel):
    """What we send back: the answer plus every source used to generate it."""
    question: str                  # Echo the original question back
    answer: str                    # The generated answer
    references: List[Reference]    # All chunks used to build the answer
    embedding_provider: str        # Which embedding model was active ("openai" or "huggingface")


class FileUploadResult(BaseModel):
    """Status for a single file in a batch upload."""
    file_name: str              # Original filename
    doc_id: str                 # Unique ID for this file (used in DELETE)
    file_type: str              # Extension without dot
    status: str                 # "indexed" if success, "error" if something went wrong
    chunks_created: int         # How many chunks were stored in Qdrant
    error: Optional[str] = None # Error message if status == "error"


class UploadResponse(BaseModel):
    """Summary of a batch upload — one FileUploadResult per file."""
    total_files: int                   # How many files were in the request
    successful: int                    # How many were indexed without errors
    failed: int                        # How many failed
    results: List[FileUploadResult]    # Per-file detail



class DocumentInfo(BaseModel):
    """One row in the list of indexed documents."""
    doc_id: str              # ID to use when calling DELETE /documents/{doc_id}
    file_name: str           # Original filename
    file_type: str           # Extension without dot
    chunk_count: int         # Total chunks stored in Qdrant for this file
    upload_timestamp: str    # ISO timestamp of when it was indexed


class DocumentListResponse(BaseModel):
    """Response for GET /documents."""
    documents: List[DocumentInfo]   # One entry per file (not per chunk)
    total: int                      # Total number of indexed files


# ── /documents/{doc_id} DELETE response ──────────────────────────────────────

class DeleteResponse(BaseModel):
    """Confirmation that a document was removed."""
    status: str          # Always "deleted" on success
    doc_id: str          # The ID that was deleted
    file_name: str       # Human-readable filename for confirmation
    chunks_deleted: int  # How many Qdrant points were removed




