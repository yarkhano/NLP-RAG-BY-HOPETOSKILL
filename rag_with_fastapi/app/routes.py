from fastapi import APIRouter

#apis imports

from app.api import (
    delete_document,
    health,
    list_documents,
    query,
    upload_files,
)


#models import

from app.models import (
    DeleteResponse,
    DocumentListResponse,
    QueryResponse,
    UploadResponse,
)

router = APIRouter()

router.add_api_route("/upload",                upload_files,    methods=["POST"],   response_model=UploadResponse,       tags=["Documents"])
router.add_api_route("/query",                 query,           methods=["POST"],   response_model=QueryResponse,        tags=["RAG"])
router.add_api_route("/documents",             list_documents,  methods=["GET"],    response_model=DocumentListResponse, tags=["Documents"])
router.add_api_route("/documents/{doc_id}",    delete_document, methods=["DELETE"], response_model=DeleteResponse,       tags=["Documents"])
router.add_api_route("/health",                health,          methods=["GET"],                                         tags=["Ops"])

