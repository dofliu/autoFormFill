"""
FileIndex ORM model — tracks files that have been indexed into the vector store.

State machine:
    pending → indexing → indexed
                           ↓ (file hash changed)
                         stale → indexing → indexed
                           ↓ (file deleted)
                        deleted
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FileIndex(Base):
    __tablename__ = "file_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending", index=True
    )  # pending | indexing | indexed | stale | deleted | error
    collection: Mapped[str] = mapped_column(String, nullable=False, default="auto_indexed")
    doc_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    chunks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(String, nullable=False, default="")
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "status": self.status,
            "collection": self.collection,
            "doc_id": self.doc_id,
            "chunks_count": self.chunks_count,
            "error_message": self.error_message,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
