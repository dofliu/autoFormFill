from typing import Literal

from pydantic import BaseModel


class DocumentMetadataInput(BaseModel):
    doc_type: Literal["paper", "project"]
    title: str
    authors: str | None = None
    publish_year: int | None = None
    keywords: str | None = None
    project_name: str | None = None
    funding_agency: str | None = None
    execution_period: str | None = None
    tech_stack: str | None = None


class DocumentUploadResponse(BaseModel):
    doc_id: str
    collection: str
    chunks_count: int
    metadata: dict


class DocumentSearchResult(BaseModel):
    doc_id: str
    text: str
    metadata: dict
    distance: float | None = None
