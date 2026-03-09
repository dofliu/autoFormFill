import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.models import UserProfile, EducationExperience, Entity, EntityRelation, FormJob, FileIndex, ComplianceRule, DocumentVersion, Reminder  # noqa: F401 — register ORM models
from app.routers import chat, compliance, documents, education_experience, email, entities, entity_relations, forms, indexing, reminders, report, user_profiles, versions
from app.schemas.error import ERR_INTERNAL
from app.services.file_watcher import file_watcher
from app.vector_store import init_vector_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create data directories and initialize database
    for dir_path in [settings.upload_dir, settings.output_dir]:
        os.makedirs(dir_path, exist_ok=True)
    await init_db()
    init_vector_store()

    # Start file watcher for auto-indexing (Phase 3)
    await file_watcher.start()

    yield

    # Shutdown: stop file watcher
    await file_watcher.stop()


app = FastAPI(
    title="SmartFill-Scholar",
    description="智能學術表單填寫系統 API",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_profiles.router)
app.include_router(education_experience.router)
app.include_router(entities.router)
app.include_router(entity_relations.router)
app.include_router(documents.router)
app.include_router(forms.router)
app.include_router(indexing.router)
app.include_router(chat.router)
app.include_router(email.router)
app.include_router(report.router)
app.include_router(compliance.router)
app.include_router(versions.router)
app.include_router(reminders.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions — returns structured JSON."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": ERR_INTERNAL},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
