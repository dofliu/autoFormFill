from datetime import datetime

from pydantic import BaseModel


class UserProfileCreate(BaseModel):
    name_zh: str | None = None
    name_en: str | None = None
    title: str | None = None
    department: str | None = None
    university: str | None = None
    email: str | None = None
    phone_office: str | None = None
    address: str | None = None


class UserProfileUpdate(BaseModel):
    name_zh: str | None = None
    name_en: str | None = None
    title: str | None = None
    department: str | None = None
    university: str | None = None
    email: str | None = None
    phone_office: str | None = None
    address: str | None = None


class UserProfileResponse(BaseModel):
    id: int
    name_zh: str | None = None
    name_en: str | None = None
    title: str | None = None
    department: str | None = None
    university: str | None = None
    email: str | None = None
    phone_office: str | None = None
    address: str | None = None
    # Phase 6.1: Authentication fields
    role: str = "user"
    is_active: bool = True
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
