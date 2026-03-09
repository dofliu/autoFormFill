"""Entity ORM model — flexible, type-tagged data record with JSON attributes.

Sits alongside UserProfile (not a replacement). The Intent Router queries
both UserProfile and Entity to resolve form fields.
"""

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    attributes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def attributes(self) -> dict[str, str]:
        """Parse attributes_json into a dict."""
        return json.loads(self.attributes_json)

    @attributes.setter
    def attributes(self, value: dict[str, str]) -> None:
        """Serialize dict to JSON string."""
        self.attributes_json = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        """Convert to a plain dict (for Pydantic response serialization)."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
