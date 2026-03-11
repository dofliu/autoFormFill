"""
Authentication Router — register, login, token refresh, and current user info.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _user_to_auth_response(user: UserProfile) -> AuthUserResponse:
    """Convert UserProfile ORM to AuthUserResponse."""
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        name_zh=user.name_zh,
        name_en=user.name_en,
        role=user.role,
        is_active=bool(user.is_active),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account.

    Creates a UserProfile with hashed password and returns JWT tokens.
    """
    # Check email uniqueness
    result = await db.execute(
        select(UserProfile).where(UserProfile.email == data.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user with hashed password
    user = UserProfile(
        email=data.email,
        password_hash=hash_password(data.password),
        name_zh=data.name_zh,
        name_en=data.name_en,
        role="user",
        is_active=1,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    logger.info("User registered: id=%d email=%s", user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_auth_response(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password, returns JWT tokens."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.email == data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    logger.info("User logged in: id=%d email=%s", user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_to_auth_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    import jwt as pyjwt

    try:
        payload = decode_token(data.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = await db.get(UserProfile, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access_token = create_access_token(user.id, user.role)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=_user_to_auth_response(user),
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_me(current_user: UserProfile = Depends(require_auth)):
    """Get the currently authenticated user's info."""
    return _user_to_auth_response(current_user)
