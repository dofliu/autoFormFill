"""Pydantic schemas for Entity CRUD operations."""

from pydantic import BaseModel


class EntityCreate(BaseModel):
    entity_type: str  # "person", "organization", "project", or custom
    name: str
    description: str = ""
    attributes: dict[str, str] = {}


class EntityUpdate(BaseModel):
    entity_type: str | None = None
    name: str | None = None
    description: str | None = None
    attributes: dict[str, str] | None = None


class EntityResponse(BaseModel):
    id: int
    user_id: int
    entity_type: str
    name: str
    description: str
    attributes: dict[str, str]
    created_at: str
    updated_at: str
