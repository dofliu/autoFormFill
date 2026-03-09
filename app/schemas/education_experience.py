from typing import Literal

from pydantic import BaseModel


class EducationExperienceCreate(BaseModel):
    type: Literal["Education", "Experience"]
    organization: str | None = None
    role_degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class EducationExperienceUpdate(BaseModel):
    type: Literal["Education", "Experience"] | None = None
    organization: str | None = None
    role_degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class EducationExperienceResponse(BaseModel):
    id: int
    user_id: int
    type: str
    organization: str | None = None
    role_degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    model_config = {"from_attributes": True}
