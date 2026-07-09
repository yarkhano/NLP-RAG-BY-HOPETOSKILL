import logging
import os
from pathlib import Path
from typing import List

from fastapi import Depends, File, HTTPException, UploadFile
from langchain_groq import ChatGroq
from qdrant_client import QdrantClient


from app.config import settings
from app.file_loader import is_supported, load_file

from app.models import(
    DeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    FileUploadResult,
    QueryRequest,
    QueryResponse,
    UploadResponse,
)


from app.rag_chain import (
    compute_doc_id,
    delete_indexed_document,
    index_documents,
    list_indexed_documents,
    query_with_references,
)

logger = logging.getLogger(__name__)

app_state: dict = {}


def get_client()-> QdrantClient:
    return app_state["qdrant_client"]

def get_emb():
    return app_state["embeddings"]

def get_llm():
    return app_state["llm"]


async def upload_files(
      files: List[UploadFile] = File(..., description="One or more files: PDF, DOCX, MD, CSV, TXT"),
      client: QdrantClient = Depends(get_client),
)-> UploadResponse:

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files to upload")