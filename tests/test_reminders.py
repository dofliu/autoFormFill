"""Tests for Phase 5.4 — Smart Reminders (Deadline detection + notifications).

Tests cover:
  - Reminder ORM model
  - Reminder schemas
  - Reminder service CRUD
  - Fill-diff detection
  - Deadline extraction
  - Router integration
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.reminder import (
    FillDiffItem,
    FillDiffResult,
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.services.reminder_service import (
    VALID_STATUSES,
    VALID_TYPES,
    compute_fill_diffs,
    extract_dates_from_text,
)


# ---- TestReminderModel ----

class TestReminderModel:
    def test_model_import(self):
        from app.models.reminder import Reminder
        assert Reminder.__tablename__ == "reminders"

    def test_to_dict(self):
        from app.models.reminder import Reminder
        r = Reminder(
            id=1, user_id=1, reminder_type="deadline",
            title="截止日提醒", message="計畫書下週到期",
            related_id="job_123", status="active",
            priority="high",
        )
        r.due_date = datetime(2026, 3, 20, tzinfo=timezone.utc)
        r.created_at = datetime(2026, 3, 10)
        r.updated_at = datetime(2026, 3, 10)
        d = r.to_dict()
        assert d["reminder_type"] == "deadline"
        assert d["status"] == "active"
        assert d["priority"] == "high"
        assert d["due_date"] is not None

    def test_to_dict_no_due_date(self):
        from app.models.reminder import Reminder
        r = Reminder(
            id=1, user_id=1, reminder_type="manual",
            title="test", message="", related_id="",
            status="active", priority="medium",
        )
        r.due_date = None
        r.created_at = datetime(2026, 3, 10)
        r.updated_at = datetime(2026, 3, 10)
        d = r.to_dict()
        assert d["due_date"] is None


# ---- TestReminderSchemas ----

class TestReminderSchemas:
    def test_reminder_create(self):
        data = ReminderCreate(
            title="提醒", reminder_type="deadline",
            priority="high", due_date="2026-03-20T00:00:00",
        )
        assert data.title == "提醒"
        assert data.reminder_type == "deadline"

    def test_reminder_create_defaults(self):
        data = ReminderCreate(title="test")
        assert data.reminder_type == "manual"
        assert data.priority == "medium"
        assert data.due_date is None

    def test_reminder_update(self):
        data = ReminderUpdate(status="read")
        assert data.status == "read"
        assert data.title is None

    def test_reminder_response(self):
        resp = ReminderResponse(
            id=1, user_id=1, reminder_type="manual",
            title="test", message="", related_id="",
            status="active", priority="medium",
            due_date=None,
            created_at="2026-03-10T00:00:00",
            updated_at="2026-03-10T00:00:00",
        )
        assert resp.id == 1

    def test_fill_diff_item(self):
        item = FillDiffItem(
            field_name="name", old_value="王大明", new_value="李小華"
        )
        assert item.field_name == "name"

    def test_fill_diff_result(self):
        result = FillDiffResult(
            template_filename="form.docx",
            previous_job_id="job_1",
            current_job_id="job_2",
            diffs=[FillDiffItem(field_name="name", old_value="A", new_value="B")],
            total_diffs=1,
        )
        assert result.total_diffs == 1


# ---- TestComputeFillDiffs ----

class TestComputeFillDiffs:
    def test_no_diffs(self):
        current = [{"field_name": "name", "value": "王大明"}]
        previous = [{"field_name": "name", "value": "王大明"}]
        diffs = compute_fill_diffs(current, previous)
        assert len(diffs) == 0

    def test_single_diff(self):
        current = [{"field_name": "name", "value": "李小華"}]
        previous = [{"field_name": "name", "value": "王大明"}]
        diffs = compute_fill_diffs(current, previous)
        assert len(diffs) == 1
        assert diffs[0].old_value == "王大明"
        assert diffs[0].new_value == "李小華"

    def test_multiple_diffs(self):
        current = [
            {"field_name": "name", "value": "新名字"},
            {"field_name": "email", "value": "new@mail.com"},
            {"field_name": "phone", "value": "0987654321"},
        ]
        previous = [
            {"field_name": "name", "value": "舊名字"},
            {"field_name": "email", "value": "old@mail.com"},
            {"field_name": "phone", "value": "0987654321"},
        ]
        diffs = compute_fill_diffs(current, previous)
        assert len(diffs) == 2
        field_names = {d.field_name for d in diffs}
        assert field_names == {"name", "email"}

    def test_new_field_not_in_previous(self):
        """Fields that don't exist in previous fill are not flagged as diffs."""
        current = [{"field_name": "new_field", "value": "value"}]
        previous = [{"field_name": "other_field", "value": "value"}]
        diffs = compute_fill_diffs(current, previous)
        assert len(diffs) == 0

    def test_empty_previous(self):
        current = [{"field_name": "name", "value": "value"}]
        diffs = compute_fill_diffs(current, [])
        assert len(diffs) == 0


# ---- TestExtractDatesFromText ----

class TestExtractDatesFromText:
    def test_no_dates(self):
        text = "This is just regular text without any dates."
        dates = extract_dates_from_text(text)
        assert len(dates) == 0

    def test_date_without_keyword(self):
        """Dates without deadline keywords should not be extracted."""
        text = "Today is 2026/12/25."
        dates = extract_dates_from_text(text)
        assert len(dates) == 0

    def test_date_with_keyword(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        date_str = future.strftime("%Y/%m/%d")
        text = f"申請截止日期：{date_str}"
        dates = extract_dates_from_text(text)
        assert len(dates) >= 1
        assert dates[0][0].year == future.year

    def test_chinese_date_format(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        date_str = f"{future.year}年{future.month}月{future.day}日"
        text = f"截止日期：{date_str}"
        dates = extract_dates_from_text(text)
        assert len(dates) >= 1

    def test_multiple_dates(self):
        future1 = datetime.now(timezone.utc) + timedelta(days=10)
        future2 = datetime.now(timezone.utc) + timedelta(days=30)
        text = (
            f"報名截止：{future1.strftime('%Y/%m/%d')}\n"
            f"繳交期限：{future2.strftime('%Y/%m/%d')}\n"
        )
        dates = extract_dates_from_text(text)
        assert len(dates) >= 2

    def test_past_date_excluded(self):
        """Dates more than 7 days in the past should be excluded."""
        past = datetime.now(timezone.utc) - timedelta(days=30)
        text = f"截止日期：{past.strftime('%Y/%m/%d')}"
        dates = extract_dates_from_text(text)
        assert len(dates) == 0


# ---- TestReminderService ----

class TestReminderService:
    @pytest.mark.asyncio
    async def test_create_reminder(self):
        from app.services.reminder_service import create_reminder

        mock_db = AsyncMock()
        data = ReminderCreate(title="test", message="hello")
        r = await create_reminder(mock_db, 1, data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_reminder_with_due_date(self):
        from app.services.reminder_service import create_reminder

        mock_db = AsyncMock()
        data = ReminderCreate(
            title="deadline",
            reminder_type="deadline",
            due_date="2026-04-01T00:00:00",
        )
        r = await create_reminder(mock_db, 1, data)
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_all(self):
        from app.services.reminder_service import dismiss_all

        mock_db = AsyncMock()
        r1 = MagicMock()
        r1.status = "active"
        r2 = MagicMock()
        r2.status = "active"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [r1, r2]
        mock_db.execute.return_value = mock_result

        count = await dismiss_all(mock_db, 1)
        assert count == 2
        assert r1.status == "dismissed"
        assert r2.status == "dismissed"

    @pytest.mark.asyncio
    async def test_detect_fill_diffs_no_previous(self):
        from app.services.reminder_service import detect_fill_diffs

        mock_db = AsyncMock()
        current_job = {
            "job_id": "job_2",
            "template_filename": "form.docx",
            "fields": [{"field_name": "name", "value": "test"}],
        }

        with patch("app.job_store.job_store") as mock_store:
            mock_store.get_jobs_by_template = AsyncMock(return_value=[])
            result = await detect_fill_diffs(mock_db, 1, current_job)
            assert result is None

    @pytest.mark.asyncio
    async def test_detect_fill_diffs_with_changes(self):
        from app.services.reminder_service import detect_fill_diffs

        mock_db = AsyncMock()
        current_job = {
            "job_id": "job_2",
            "template_filename": "form.docx",
            "fields": [{"field_name": "name", "value": "李小華"}],
        }
        previous_job = {
            "job_id": "job_1",
            "template_filename": "form.docx",
            "fields": [{"field_name": "name", "value": "王大明"}],
        }

        with patch("app.job_store.job_store") as mock_store:
            mock_store.get_jobs_by_template = AsyncMock(return_value=[current_job, previous_job])
            result = await detect_fill_diffs(mock_db, 1, current_job)
            assert result is not None
            assert result.total_diffs == 1
            assert result.diffs[0].old_value == "王大明"
            assert result.diffs[0].new_value == "李小華"


# ---- TestConstants ----

class TestReminderConstants:
    def test_valid_statuses(self):
        assert VALID_STATUSES == {"active", "read", "dismissed"}

    def test_valid_types(self):
        assert VALID_TYPES == {"deadline", "fill_diff", "manual"}
