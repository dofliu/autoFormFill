"""
Pydantic schemas for authentication endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, description="Email address (used as login)")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    name_zh: str | None = None
    name_en: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthUserResponse(BaseModel):
    """Minimal user info returned in auth responses."""

    id: int
    email: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    role: str = "user"
    is_active: bool = True

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
