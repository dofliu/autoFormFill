"""ComplianceRule ORM model — stores per-user validation rules for form fields.

Rule types:
  - required: field must not be empty or '[需人工補充]'
  - min_length / max_length: character count constraints
  - regex: pattern validation (e.g. date format, email)
  - contains: must contain a keyword
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String, nullable=False)
    # Which field(s) this rule applies to — exact field name or "*" for all fields
    field_pattern: Mapped[str] = mapped_column(String, nullable=False, default="*")
    # Rule type: required | min_length | max_length | regex | contains
    rule_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Rule parameter (e.g., "10" for min_length, "\\d{4}/\\d{2}/\\d{2}" for regex)
    rule_value: Mapped[str] = mapped_column(String, nullable=False, default="")
    # Severity: error | warning | info
    severity: Mapped[str] = mapped_column(String, nullable=False, default="warning")
    # Human-readable message
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Enabled flag
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

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
            "rule_name": self.rule_name,
            "field_pattern": self.field_pattern,
            "rule_type": self.rule_type,
            "rule_value": self.rule_value,
            "severity": self.severity,
            "message": self.message,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
