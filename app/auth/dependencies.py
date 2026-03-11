"""
FastAPI dependency injection for authentication and authorization.

Provides reusable dependencies that can be injected into route handlers:
- get_current_user: Extract and validate JWT from Authorization header
- require_auth: Ensure user is authenticated (non-None)
- require_admin: Ensure user has admin role
"""

import logging

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.config import settings
from app.database import get_db
from app.models.user_profile import UserProfile
from app.services import user_service

logger = logging.getLogger(__name__)

# auto_error=False so we can handle missing tokens ourselves (for dev mode)
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserProfile | None:
    """Extract current user from JWT Bearer token.

    - AUTH_ENABLED=True + no token → 401
    - AUTH_ENABLED=True + valid token → UserProfile
    - AUTH_ENABLED=False + no token → None (anonymous access)
    - AUTH_ENABLED=False + valid token → UserProfile
    """
    if credentials is None:
        if settings.auth_enabled:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account disabled")

    return user


async def require_auth(
    current_user: UserProfile | None = Depends(get_current_user),
) -> UserProfile:
    """Dependency that ensures a user is authenticated (non-None).

    Use this in endpoints that MUST have a logged-in user.
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


async def require_admin(
    current_user: UserProfile | None = Depends(get_current_user),
) -> UserProfile:
    """Dependency that ensures the user is an admin."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def verify_ownership(current_user: UserProfile | None, user_id: int) -> None:
    """Check that the authenticated user owns the resource.

    Skips check when AUTH_ENABLED=False (current_user is None).
    Admins can access any user's resources.
    """
    if current_user is None:
        # AUTH_ENABLED=False — dev mode, skip ownership check
        return
    if current_user.role == "admin":
        return
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this user's resources"
        )
