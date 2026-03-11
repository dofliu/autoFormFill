import logging
import os
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models.user_profile import UserProfile
from app.schemas.document import DocumentUploadResponse
from app.schemas.error import ERR_FILE_UNSUPPORTED, ERR_INTERNAL
from app.services import document_service
from app.utils.file_utils import detect_file_type, save_upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: Literal["paper", "project"] = Form(...),
    title: str = Form(...),
    authors: str = Form(None),
    publish_year: int = Form(None),
    keywords: str = Form(None),
    project_name: str = Form(None),
    funding_agency: str = Form(None),
    execution_period: str = Form(None),
    tech_stack: str = Form(None),
    user_id: int | None = Form(None),  # fallback when AUTH_ENABLED=False
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Upload a document (paper or project), extract text, chunk, embed, and store."""
    file_type = detect_file_type(file.filename or "")
    if file_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail={"detail": "Unsupported file type. Use .docx or .pdf", "code": ERR_FILE_UNSUPPORTED, "field": "file"},
        )

    # Resolve user_id: JWT token takes precedence, then Form field fallback
    resolved_user_id = current_user.id if current_user else user_id

    file_path = await save_upload_file(file, settings.upload_dir)
    try:
        from app.schemas.document import DocumentMetadataInput

        metadata = DocumentMetadataInput(
            doc_type=doc_type,
            title=title,
            authors=authors,
            publish_year=publish_year,
            keywords=keywords,
            project_name=project_name,
            funding_agency=funding_agency,
            execution_period=execution_period,
            tech_stack=tech_stack,
        )
        result = await document_service.embed_and_store(
            file_path, file_type, metadata, user_id=resolved_user_id
        )
        return result
    except Exception as e:
        logger.exception("Document upload failed")
        raise HTTPException(
            status_code=500,
            detail={"detail": str(e), "code": ERR_INTERNAL},
        )
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)


@router.get("/search")
async def search_documents(
    q: str,
    collection: Literal["academic_papers", "research_projects"] = "academic_papers",
    n_results: int = 5,
    user_id: int | None = Query(None, description="Filter by owner (fallback when AUTH disabled)"),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Search embedded documents by semantic query."""
    # Resolve user_id: JWT token takes precedence, then query param fallback
    resolved_user_id = current_user.id if current_user else user_id

    try:
        results = await document_service.search_documents(
            q, collection, n_results, user_id=resolved_user_id
        )
        return {"query": q, "collection": collection, "results": results}
    except Exception as e:
        logger.exception("Document search failed")
        raise HTTPException(
            status_code=500,
            detail={"detail": str(e), "code": ERR_INTERNAL},
        )
