from sqlalchemy import Column, Integer, String
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
    email = Column(String, nullable=True)
    phone_office = Column(String, nullable=True)
    address = Column(String, nullable=True)

    education_experiences = relationship(
        "EducationExperience", back_populates="user", cascade="all, delete-orphan"
    )
