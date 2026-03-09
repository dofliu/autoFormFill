"""Unified API error response schema."""

from pydantic import BaseModel

# Error code constants
ERR_NOT_FOUND = "not_found"
ERR_VALIDATION = "validation_error"
ERR_LLM_UNAVAILABLE = "llm_unavailable"
ERR_FILE_UNSUPPORTED = "file_unsupported"
ERR_INTERNAL = "internal_error"


class ErrorResponse(BaseModel):
    """Structured error response returned by all API endpoints."""
    detail: str  # Human-readable error message
    code: str  # Machine-readable error code
    field: str | None = None  # Optional: which field/parameter caused the error
