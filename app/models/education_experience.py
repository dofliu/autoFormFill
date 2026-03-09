from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class EducationExperience(Base):
    __tablename__ = "education_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    type = Column(String, nullable=False)  # "Education" or "Experience"
    organization = Column(String, nullable=True)
    role_degree = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    user = relationship("UserProfile", back_populates="education_experiences")
