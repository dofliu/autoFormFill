"""
Tests for Phase 6.1: Authentication & Authorization (JWT + RBAC).

Covers:
- Password hashing / verification
- JWT token creation / decoding / expiry
- Auth router endpoints (register, login, refresh, me)
- Dependencies (get_current_user, require_auth, require_admin, verify_ownership)
- AUTH_ENABLED toggle behavior
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

# Ensure AUTH_ENABLED=False by default (set by conftest.py), override per-test as needed
os.environ.setdefault("AUTH_ENABLED", "False")


# ─── Password hashing ──────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.auth.security import hash_password, verify_password
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert verify_password("mypassword", hashed)

    def test_wrong_password_fails(self):
        from app.auth.security import hash_password, verify_password
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes_for_same_password(self):
        from app.auth.security import hash_password
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salts are different


# ─── JWT tokens ─────────────────────────────────────────────────────

class TestJWT:
    def test_create_access_token(self):
        from app.auth.security import create_access_token, decode_token
        token = create_access_token(42, "admin")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        from app.auth.security import create_refresh_token, decode_token
        token = create_refresh_token(7)
        payload = decode_token(token)
        assert payload["sub"] == "7"
        assert payload["type"] == "refresh"
        assert "role" not in payload

    def test_expired_token_raises(self, monkeypatch):
        import jwt as pyjwt
        from app.auth.security import decode_token
        from app.config import settings

        now = datetime.now(timezone.utc)
        payload = {
            "sub": "1",
            "type": "access",
            "iat": now - timedelta(hours=48),
            "exp": now - timedelta(hours=1),
        }
        token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token)

    def test_invalid_token_raises(self):
        import jwt as pyjwt
        from app.auth.security import decode_token
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token("not.a.valid.token")


# ─── Auth schemas ───────────────────────────────────────────────────

class TestAuthSchemas:
    def test_register_request_validation(self):
        from app.schemas.auth import RegisterRequest
        req = RegisterRequest(email="a@b.com", password="123456")
        assert req.email == "a@b.com"

    def test_register_request_short_password(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="12345")  # min_length=6

    def test_token_response_schema(self):
        from app.schemas.auth import TokenResponse, AuthUserResponse
        user = AuthUserResponse(id=1, email="a@b.com", role="user", is_active=True)
        resp = TokenResponse(access_token="a", refresh_token="b", user=user)
        assert resp.token_type == "bearer"


# ─── Auth router (register / login / refresh / me) ──────────────

class TestAuthRouter:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        """Create a test client with a fresh SQLite database.

        Uses dependency_overrides to inject a test database session,
        avoiding module reload issues with get_db references.
        """
        import asyncio
        from collections.abc import AsyncGenerator

        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from app.database import Base, get_db
        from app.models.user_profile import UserProfile  # noqa: F401
        from app.routers.auth import router

        # Enable auth for these tests
        monkeypatch.setattr("app.config.settings.auth_enabled", True)

        # Create a test-specific engine + session factory
        db_path = tmp_path / "test_auth.db"
        test_engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}", echo=False
        )
        TestSessionLocal = async_sessionmaker(
            test_engine, expire_on_commit=False
        )

        # Create tables
        async def _setup():
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_setup())

        # Override get_db to use our test database
        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            async with TestSessionLocal() as session:
                yield session

        test_app = FastAPI()
        test_app.include_router(router)
        test_app.dependency_overrides[get_db] = _override_get_db

        yield TestClient(test_app)

        # Cleanup
        loop.run_until_complete(test_engine.dispose())
        loop.close()

    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "name_zh": "測試使用者",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["role"] == "user"

    def test_register_duplicate_email(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "dup@example.com", "password": "password123",
        })
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@example.com", "password": "password123",
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        # Register first
        client.post("/api/v1/auth/register", json={
            "email": "login@example.com", "password": "password123",
        })
        # Login
        resp = client.post("/api/v1/auth/login", json={
            "email": "login@example.com", "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "wrong@example.com", "password": "password123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "wrong@example.com", "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "noone@example.com", "password": "password123",
        })
        assert resp.status_code == 401

    def test_refresh_success(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "refresh@example.com", "password": "password123",
        })
        refresh_token = reg.json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "refresh@example.com"

    def test_refresh_invalid_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "bad.token.value",
        })
        assert resp.status_code == 401

    def test_refresh_with_access_token_fails(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "rtype@example.com", "password": "password123",
        })
        access_token = reg.json()["access_token"]
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert resp.status_code == 401
        assert "Invalid token type" in resp.json()["detail"]

    def test_me_with_token(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "me@example.com", "password": "password123",
            "name_zh": "我",
        })
        token = reg.json()["access_token"]
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@example.com"
        assert data["name_zh"] == "我"

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)  # 401 from our handler, 403 from HTTPBearer


# ─── Dependencies ───────────────────────────────────────────────────

class TestDependencies:
    def test_verify_ownership_pass(self):
        from app.auth.dependencies import verify_ownership
        from unittest.mock import MagicMock
        user = MagicMock()
        user.id = 5
        user.role = "user"
        verify_ownership(user, 5)  # Should not raise

    def test_verify_ownership_admin_bypass(self):
        from app.auth.dependencies import verify_ownership
        from unittest.mock import MagicMock
        user = MagicMock()
        user.id = 1
        user.role = "admin"
        verify_ownership(user, 99)  # Admin can access any user's resources

    def test_verify_ownership_forbidden(self):
        from app.auth.dependencies import verify_ownership
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        user = MagicMock()
        user.id = 5
        user.role = "user"
        with pytest.raises(HTTPException) as exc_info:
            verify_ownership(user, 99)
        assert exc_info.value.status_code == 403

    def test_verify_ownership_none_skips(self):
        from app.auth.dependencies import verify_ownership
        verify_ownership(None, 42)  # AUTH_ENABLED=False, should not raise


# ─── UserProfile auth fields ───────────────────────────────────────

class TestUserProfileAuthFields:
    def test_model_has_auth_fields(self):
        from app.models.user_profile import UserProfile
        # Check columns exist
        columns = {c.name for c in UserProfile.__table__.columns}
        assert "password_hash" in columns
        assert "role" in columns
        assert "is_active" in columns
        assert "created_at" in columns

    def test_response_schema_has_auth_fields(self):
        from app.schemas.user_profile import UserProfileResponse
        fields = UserProfileResponse.model_fields
        assert "role" in fields
        assert "is_active" in fields
        assert "created_at" in fields

    def test_email_unique_constraint(self):
        from app.models.user_profile import UserProfile
        email_col = UserProfile.__table__.columns["email"]
        assert email_col.unique is True


# ─── Config auth settings ──────────────────────────────────────────

class TestConfigAuthSettings:
    def test_auth_settings_exist(self):
        from app.config import Settings
        fields = Settings.model_fields
        assert "auth_enabled" in fields
        assert "jwt_secret_key" in fields
        assert "jwt_algorithm" in fields
        assert "jwt_access_token_expire_hours" in fields
        assert "jwt_refresh_token_expire_days" in fields

    def test_default_values(self):
        from app.config import Settings
        s = Settings(
            gemini_api_key="test-key",
        )
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_access_token_expire_hours == 24
        assert s.jwt_refresh_token_expire_days == 7
