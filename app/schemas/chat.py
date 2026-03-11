"""Pydantic models for the Chat (Knowledge QA) feature."""
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """A single message in the conversation."""

    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str
    history: list[ChatMessage] = []
    collections: list[str] | None = None  # None = search all collections
    n_results: int = 5
    user_id: int | None = None  # fallback when AUTH_ENABLED=False


class SourceChunk(BaseModel):
    """A retrieved document chunk with its metadata."""

    text: str
    metadata: dict
    distance: float | None = None
    collection: str
