import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.form import FormFillResponse, FormParseResponse, FormPreviewResponse, FormSubmitRequest, FieldFillResult
from app.services import form_parser
from app.utils.file_utils import detect_file_type, save_upload_file
from app.job_store import job_store

router = APIRouter(prefix="/api/v1/forms", tags=["Forms"])


@router.post("/parse", response_model=FormParseResponse)
async def parse_form(file: UploadFile = File(...)):
    """Upload a blank form and detect fillable fields."""
    file_type = detect_file_type(file.filename or "")
    if file_type == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported file type. Use .docx or .pdf")

    file_path = await save_upload_file(file, settings.upload_dir)
    try:
        fields = form_parser.parse_form(file_path, file_type)
        return FormParseResponse(
            filename=file.filename or "unknown",
            file_type=file_type,
            fields=fields,
            total_fields=len(fields),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)


@router.post("/fill", response_model=FormFillResponse)
async def fill_form(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a form, auto-fill using user data + RAG, return filled document."""
    file_type = detect_file_type(file.filename or "")
    if file_type == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported file type. Use .docx or .pdf")

    file_path = await save_upload_file(file, settings.upload_dir)
    try:
        from app.services.form_filler import fill_form as do_fill

        result = await do_fill(
            file_path=file_path,
            file_type=file_type,
            original_filename=file.filename or "form",
            user_id=user_id,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Keep the uploaded file for reference; form_filler handles cleanup if needed
        if os.path.exists(file_path):
            os.unlink(file_path)


@router.get("/download/{filename}")
async def download_filled_form(filename: str):
    """Download a filled form by filename."""
    file_path = os.path.join(settings.output_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/preview/{job_id}", response_model=FormPreviewResponse)
async def get_form_preview(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get form preview data for a job."""
    job = await job_store.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return FormPreviewResponse(
        job_id=job_id,
        filename=job["filename"],
        template_filename=job["template_filename"],
        fields=[FieldFillResult(**field) for field in job["fields"]],
        created_at=job["created_at"],
    )


@router.post("/submit", response_model=FormFillResponse)
async def submit_form(
    request: FormSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit form with field overrides."""
    try:
        from app.services.form_filler import submit_form_with_overrides
        result = await submit_form_with_overrides(
            job_id=request.job_id,
            field_overrides=request.field_overrides,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FormHistoryItem(BaseModel):
    job_id: str
    filename: str
    template_filename: str
    fields_filled: int
    fields_skipped: int
    created_at: str


@router.get("/history/{user_id}", response_model=list[FormHistoryItem])
async def get_form_history(user_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get form filling history for a user."""
    jobs = await job_store.get_jobs_by_user(user_id, limit, db)

    return [
        FormHistoryItem(
            job_id=job["job_id"],
            filename=job["filename"],
            template_filename=job["template_filename"],
            fields_filled=sum(1 for f in job.get("fields", []) if f.get("source") != "skip"),
            fields_skipped=sum(1 for f in job.get("fields", []) if f.get("source") == "skip"),
            created_at=job["created_at"],
        )
        for job in jobs
    ]


@router.get("/history/{user_id}/similar/{template_filename}", response_model=list[FormHistoryItem])
async def get_similar_forms(user_id: int, template_filename: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get similar forms that used the same template."""
    jobs = await job_store.get_jobs_by_template(template_filename, user_id, limit, db)

    return [
        FormHistoryItem(
            job_id=job["job_id"],
            filename=job["filename"],
            template_filename=job["template_filename"],
            fields_filled=sum(1 for f in job.get("fields", []) if f.get("source") != "skip"),
            fields_skipped=sum(1 for f in job.get("fields", []) if f.get("source") == "skip"),
            created_at=job["created_at"],
        )
        for job in jobs
    ]
