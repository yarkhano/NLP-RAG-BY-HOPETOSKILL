# routes.py — Route declarations only.
# Maps every URL path + HTTP method to its handler function in api.py.
# No business logic here — just the routing table.

from fastapi import APIRouter

from app.api import (
    delete_document,
    health,
    list_documents,
    query,
    upload_files,
)
from app.models import (
    DeleteResponse,
    DocumentListResponse,
    QueryResponse,
    UploadResponse,
)

router = APIRouter()   # All routes registered here, included in main.py with one line

# path              method    handler function    response shape
router.add_api_route("/upload",                upload_files,    methods=["POST"],   response_model=UploadResponse,       tags=["Documents"])
router.add_api_route("/query",                 query,           methods=["POST"],   response_model=QueryResponse,        tags=["RAG"])
router.add_api_route("/documents",             list_documents,  methods=["GET"],    response_model=DocumentListResponse, tags=["Documents"])
router.add_api_route("/documents/{doc_id}",    delete_document, methods=["DELETE"], response_model=DeleteResponse,       tags=["Documents"])
router.add_api_route("/health",                health,          methods=["GET"],                                         tags=["Ops"])
