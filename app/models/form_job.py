import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FormJob(Base):
    __tablename__ = "form_jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    template_filename: Mapped[str] = mapped_column(String, nullable=False)
    template_path: Mapped[str | None] = mapped_column(String, nullable=True)
    output_path: Mapped[str] = mapped_column(String, nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    fill_data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    field_overrides_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "template_filename": self.template_filename,
            "template_path": self.template_path,
            "output_path": self.output_path,
            "fields": json.loads(self.fields_json),
            "fill_data": json.loads(self.fill_data_json),
            "field_overrides": json.loads(self.field_overrides_json),
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
