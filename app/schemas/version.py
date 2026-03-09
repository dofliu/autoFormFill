"""Pydantic schemas for document version tracking."""
from pydantic import BaseModel


class DocumentVersionResponse(BaseModel):
    id: int
    user_id: int
    file_path: str
    file_hash: str
    version_number: int
    content_length: int
    label: str
    created_at: str


class DocumentVersionUpdate(BaseModel):
    label: str | None = None


class DiffLine(BaseModel):
    """A single line in the diff output."""
    line_number_old: int | None = None
    line_number_new: int | None = None
    tag: str  # "equal" | "insert" | "delete" | "replace"
    content: str


class DiffHunk(BaseModel):
    """A group of related changes."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


class DiffResult(BaseModel):
    """Result of comparing two document versions."""
    file_path: str
    old_version: int
    new_version: int
    old_hash: str
    new_hash: str
    hunks: list[DiffHunk]
    total_additions: int = 0
    total_deletions: int = 0
    total_changes: int = 0
    identical: bool = False
