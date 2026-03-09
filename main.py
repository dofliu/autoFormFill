import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.models import UserProfile, EducationExperience  # noqa: F401 — register ORM models
from app.routers import documents, education_experience, forms, user_profiles
from app.vector_store import init_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create data directories and initialize database
    for dir_path in [settings.upload_dir, settings.output_dir]:
        os.makedirs(dir_path, exist_ok=True)
    await init_db()
    init_vector_store()
    yield


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
app.include_router(documents.router)
app.include_router(forms.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
