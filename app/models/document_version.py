"""DocumentVersion ORM model — tracks versions of documents for diff comparison.

Each time a file is indexed (or re-indexed), a snapshot of the extracted text
is stored. Users can then compare versions to see what changed.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_hash: Mapped[str] = mapped_column(String, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Store extracted text for diffing
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Optional label (e.g. "v2 draft", "final")
    label: Mapped[str] = mapped_column(String, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "version_number": self.version_number,
            "content_length": self.content_length,
            "label": self.label,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
