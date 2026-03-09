"""Pydantic schemas for the reminder / notification system."""
from pydantic import BaseModel


class ReminderCreate(BaseModel):
    reminder_type: str = "manual"  # deadline | fill_diff | manual
    title: str
    message: str = ""
    related_id: str = ""
    priority: str = "medium"  # high | medium | low
    due_date: str | None = None  # ISO 8601 string


class ReminderUpdate(BaseModel):
    title: str | None = None
    message: str | None = None
    status: str | None = None  # active | read | dismissed
    priority: str | None = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    reminder_type: str
    title: str
    message: str
    related_id: str
    status: str
    priority: str
    due_date: str | None
    created_at: str
    updated_at: str


class FillDiffItem(BaseModel):
    """A field whose value differs from the previous fill of the same template."""
    field_name: str
    old_value: str
    new_value: str


class FillDiffResult(BaseModel):
    """Result of comparing current fill with the most recent fill of the same template."""
    template_filename: str
    previous_job_id: str
    current_job_id: str
    diffs: list[FillDiffItem]
    total_diffs: int
