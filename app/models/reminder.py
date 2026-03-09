"""Reminder ORM model — stores deadline-based and fill-diff notifications.

Reminder types:
  - deadline: document has an upcoming deadline
  - fill_diff: a form was filled differently from last time
  - manual: user-created reminder
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Type: deadline | fill_diff | manual
    reminder_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Related entity (optional) — e.g. job_id, file_path
    related_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    # Status: active | read | dismissed
    status: Mapped[str] = mapped_column(String, nullable=False, default="active", index=True)
    # Priority: high | medium | low
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    # Due date (for deadlines)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "reminder_type": self.reminder_type,
            "title": self.title,
            "message": self.message,
            "related_id": self.related_id,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
