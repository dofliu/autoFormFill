from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_zh = Column(String, nullable=True)
    name_en = Column(String, nullable=True)
    title = Column(String, nullable=True)
    department = Column(String, nullable=True)
    university = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True, index=True)
    phone_office = Column(String, nullable=True)
    address = Column(String, nullable=True)

    # Phase 6.1: Authentication fields
    password_hash = Column(String, nullable=True)  # nullable for legacy data
    role = Column(String, nullable=False, default="user")  # "admin" / "user" / "viewer"
    is_active = Column(Integer, nullable=False, default=1)  # 1=active, 0=disabled
    created_at = Column(DateTime, default=func.now())

    education_experiences = relationship(
        "EducationExperience", back_populates="user", cascade="all, delete-orphan"
    )
