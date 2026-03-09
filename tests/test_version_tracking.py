"""Tests for Phase 5.3 — Version Tracking (Document versioning + diff).

Tests cover:
  - DocumentVersion ORM model
  - Version schemas
  - Version service CRUD
  - Diff engine (compute_diff)
  - Router integration
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.version import (
    DiffHunk,
    DiffLine,
    DiffResult,
    DocumentVersionResponse,
    DocumentVersionUpdate,
)
from app.services.version_service import compute_diff


# ---- TestDocumentVersionModel ----

class TestDocumentVersionModel:
    def test_model_import(self):
        from app.models.document_version import DocumentVersion
        assert DocumentVersion.__tablename__ == "document_versions"

    def test_to_dict(self):
        from app.models.document_version import DocumentVersion
        ver = DocumentVersion(
            id=1, user_id=1, file_path="/test/doc.txt",
            file_hash="abc123", version_number=1,
            content_text="hello world", content_length=11,
            label="v1",
        )
        ver.created_at = datetime(2026, 3, 10)
        d = ver.to_dict()
        assert d["version_number"] == 1
        assert d["file_path"] == "/test/doc.txt"
        assert d["content_length"] == 11
        # content_text should NOT be in to_dict (it's too large for API listing)
        assert "content_text" not in d

    def test_to_dict_no_created_at(self):
        from app.models.document_version import DocumentVersion
        ver = DocumentVersion(
            id=1, user_id=1, file_path="/test/doc.txt",
            file_hash="abc", version_number=1,
            content_text="", content_length=0, label="v1",
        )
        ver.created_at = None
        d = ver.to_dict()
        assert d["created_at"] == ""


# ---- TestVersionSchemas ----

class TestVersionSchemas:
    def test_version_response(self):
        resp = DocumentVersionResponse(
            id=1, user_id=1, file_path="/test.txt",
            file_hash="abc", version_number=1,
            content_length=100, label="v1",
            created_at="2026-03-10T00:00:00",
        )
        assert resp.version_number == 1

    def test_version_update(self):
        data = DocumentVersionUpdate(label="final draft")
        assert data.label == "final draft"

    def test_diff_line(self):
        line = DiffLine(
            line_number_old=1, line_number_new=None,
            tag="delete", content="old text",
        )
        assert line.tag == "delete"

    def test_diff_result_identical(self):
        result = DiffResult(
            file_path="test.txt", old_version=1, new_version=2,
            old_hash="a", new_hash="b",
            hunks=[], identical=True,
        )
        assert result.identical is True
        assert result.total_changes == 0


# ---- TestComputeDiff ----

class TestComputeDiff:
    def test_identical_texts(self):
        text = "line 1\nline 2\nline 3\n"
        result = compute_diff(text, text, file_path="test.txt")
        assert result.identical is True
        assert result.hunks == []
        assert result.total_changes == 0

    def test_simple_addition(self):
        old = "line 1\nline 2\n"
        new = "line 1\nline 2\nline 3\n"
        result = compute_diff(old, new, file_path="test.txt", old_version=1, new_version=2)
        assert result.identical is False
        assert result.total_additions >= 1
        assert result.total_deletions == 0

    def test_simple_deletion(self):
        old = "line 1\nline 2\nline 3\n"
        new = "line 1\nline 3\n"
        result = compute_diff(old, new)
        assert result.identical is False
        assert result.total_deletions >= 1

    def test_replacement(self):
        old = "hello world\n"
        new = "hello universe\n"
        result = compute_diff(old, new)
        assert result.identical is False
        assert result.total_changes >= 2  # 1 delete + 1 insert

    def test_multiline_change(self):
        old = "line 1\nline 2\nline 3\nline 4\nline 5\n"
        new = "line 1\nmodified 2\nline 3\nnew 4\nline 5\n"
        result = compute_diff(old, new)
        assert result.identical is False
        assert result.total_changes > 0

    def test_empty_to_content(self):
        result = compute_diff("", "new content\n")
        assert result.total_additions >= 1

    def test_content_to_empty(self):
        result = compute_diff("old content\n", "")
        assert result.total_deletions >= 1

    def test_hunks_have_lines(self):
        old = "a\nb\nc\n"
        new = "a\nx\nc\n"
        result = compute_diff(old, new)
        assert len(result.hunks) >= 1
        for hunk in result.hunks:
            assert len(hunk.lines) > 0

    def test_version_metadata(self):
        result = compute_diff(
            "a\n", "b\n",
            file_path="/docs/test.txt",
            old_version=3, new_version=4,
            old_hash="aaa", new_hash="bbb",
        )
        assert result.file_path == "/docs/test.txt"
        assert result.old_version == 3
        assert result.new_version == 4
        assert result.old_hash == "aaa"
        assert result.new_hash == "bbb"


# ---- TestVersionService ----

class TestVersionService:
    @pytest.mark.asyncio
    async def test_create_version(self):
        from app.services.version_service import create_version

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        ver = await create_version(
            mock_db, user_id=1,
            file_path="/test.txt", file_hash="abc",
            content_text="hello world", label="test",
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_diff_versions(self):
        from app.services.version_service import diff_versions

        mock_db = AsyncMock()

        old_ver = MagicMock()
        old_ver.content_text = "line 1\nline 2\n"
        old_ver.file_path = "/test.txt"
        old_ver.version_number = 1
        old_ver.file_hash = "aaa"

        new_ver = MagicMock()
        new_ver.content_text = "line 1\nline 3\n"
        new_ver.file_path = "/test.txt"
        new_ver.version_number = 2
        new_ver.file_hash = "bbb"

        with patch("app.services.version_service.get_version", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [old_ver, new_ver]
            result = await diff_versions(mock_db, 1, 2)
            assert result is not None
            assert result.identical is False
            assert result.old_version == 1
            assert result.new_version == 2

    @pytest.mark.asyncio
    async def test_diff_versions_not_found(self):
        from app.services.version_service import diff_versions

        mock_db = AsyncMock()
        with patch("app.services.version_service.get_version", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await diff_versions(mock_db, 1, 2)
            assert result is None


# ---- TestRouterIntegration ----

class TestVersionRouterIntegration:
    @pytest.mark.asyncio
    async def test_diff_same_file_path_required(self):
        """diff_versions router should reject diffing across different files."""
        from app.routers.versions import diff_versions as router_diff

        mock_db = AsyncMock()
        old_ver = MagicMock()
        old_ver.user_id = 1
        old_ver.file_path = "/a.txt"

        new_ver = MagicMock()
        new_ver.user_id = 1
        new_ver.file_path = "/b.txt"

        with patch("app.services.version_service.get_version", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [old_ver, new_ver]
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await router_diff(user_id=1, old_version_id=1, new_version_id=2, db=mock_db)
            assert exc_info.value.status_code == 400
