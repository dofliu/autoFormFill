"""Reminder service — CRUD + fill-diff detection + deadline scanning.

Features:
  1. CRUD for reminders (manual, deadline, fill_diff types)
  2. Fill-diff detection: compare current form fill against the most recent
     fill of the same template and generate reminders for changed fields
  3. Deadline detection: scan text content for date patterns and create
     deadline reminders when dates are approaching
"""
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder
from app.schemas.reminder import (
    FillDiffItem,
    FillDiffResult,
    ReminderCreate,
    ReminderUpdate,
)

logger = logging.getLogger(__name__)

VALID_STATUSES = {"active", "read", "dismissed"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_TYPES = {"deadline", "fill_diff", "manual"}

# Date patterns for deadline detection
DATE_PATTERNS = [
    # YYYY/MM/DD or YYYY-MM-DD
    (r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", "%Y-%m-%d"),
    # YYYY年MM月DD日
    (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "%Y-%m-%d"),
    # MM/DD/YYYY
    (r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", "%m-%d-%Y"),
]

# Keywords that suggest a deadline
DEADLINE_KEYWORDS = [
    "截止", "期限", "到期", "deadline", "due date", "due by",
    "before", "submit by", "繳交", "申請截止", "報名截止",
]


# ---- CRUD ----

async def create_reminder(
    db: AsyncSession, user_id: int, data: ReminderCreate
) -> Reminder:
    """Create a new reminder."""
    due_date = None
    if data.due_date:
        try:
            due_date = datetime.fromisoformat(data.due_date)
        except ValueError:
            pass

    reminder = Reminder(
        user_id=user_id,
        reminder_type=data.reminder_type if data.reminder_type in VALID_TYPES else "manual",
        title=data.title,
        message=data.message,
        related_id=data.related_id,
        status="active",
        priority=data.priority if data.priority in VALID_PRIORITIES else "medium",
        due_date=due_date,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def get_reminder(db: AsyncSession, reminder_id: int) -> Reminder | None:
    """Get a single reminder by ID."""
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id)
    )
    return result.scalar_one_or_none()


async def list_reminders(
    db: AsyncSession, user_id: int,
    status: str | None = None,
    reminder_type: str | None = None,
    limit: int = 50,
) -> list[Reminder]:
    """List reminders for a user."""
    query = select(Reminder).where(Reminder.user_id == user_id)
    if status:
        query = query.where(Reminder.status == status)
    if reminder_type:
        query = query.where(Reminder.reminder_type == reminder_type)
    query = query.order_by(Reminder.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_active_reminders(db: AsyncSession, user_id: int) -> int:
    """Count active (unread) reminders for a user."""
    result = await db.execute(
        select(sql_func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.status == "active",
        )
    )
    return result.scalar() or 0


async def update_reminder(
    db: AsyncSession, reminder_id: int, data: ReminderUpdate
) -> Reminder | None:
    """Update a reminder."""
    reminder = await get_reminder(db, reminder_id)
    if not reminder:
        return None
    if data.title is not None:
        reminder.title = data.title
    if data.message is not None:
        reminder.message = data.message
    if data.status is not None and data.status in VALID_STATUSES:
        reminder.status = data.status
    if data.priority is not None and data.priority in VALID_PRIORITIES:
        reminder.priority = data.priority
    await db.commit()
    await db.refresh(reminder)
    return reminder


async def dismiss_all(db: AsyncSession, user_id: int) -> int:
    """Dismiss all active reminders for a user. Returns count dismissed."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.status == "active",
        )
    )
    reminders = list(result.scalars().all())
    for r in reminders:
        r.status = "dismissed"
    if reminders:
        await db.commit()
    return len(reminders)


async def delete_reminder(db: AsyncSession, reminder_id: int) -> bool:
    """Delete a reminder."""
    reminder = await get_reminder(db, reminder_id)
    if not reminder:
        return False
    await db.delete(reminder)
    await db.commit()
    return True


# ---- Fill-Diff Detection ----

def compute_fill_diffs(
    current_fields: list[dict],
    previous_fields: list[dict],
) -> list[FillDiffItem]:
    """Compare two sets of field fill results and return differences.

    Both inputs are lists of dicts with at least 'field_name' and 'value'.
    """
    prev_map = {f["field_name"]: f.get("value", "") for f in previous_fields}
    diffs: list[FillDiffItem] = []

    for field in current_fields:
        name = field["field_name"]
        new_val = field.get("value", "")
        old_val = prev_map.get(name)

        if old_val is not None and old_val != new_val:
            diffs.append(FillDiffItem(
                field_name=name,
                old_value=old_val,
                new_value=new_val,
            ))

    return diffs


async def detect_fill_diffs(
    db: AsyncSession,
    user_id: int,
    current_job: dict,
) -> FillDiffResult | None:
    """Compare current job's fill against the most recent fill of the same template.

    Returns None if no previous fill exists.
    """
    from app.job_store import job_store

    template = current_job.get("template_filename", "")
    if not template:
        return None

    # Get previous fills of the same template
    previous_jobs = await job_store.get_jobs_by_template(template, user_id, limit=2, db=db)

    # Find the most recent job that isn't the current one
    current_job_id = current_job.get("job_id", "")
    prev_job = None
    for job in previous_jobs:
        if job.get("job_id") != current_job_id:
            prev_job = job
            break

    if not prev_job:
        return None

    current_fields = current_job.get("fields", [])
    previous_fields = prev_job.get("fields", [])

    diffs = compute_fill_diffs(current_fields, previous_fields)

    if not diffs:
        return None

    return FillDiffResult(
        template_filename=template,
        previous_job_id=prev_job.get("job_id", ""),
        current_job_id=current_job_id,
        diffs=diffs,
        total_diffs=len(diffs),
    )


# ---- Deadline Detection ----

def extract_dates_from_text(text: str) -> list[tuple[datetime, str]]:
    """Extract dates from text that appear near deadline keywords.

    Returns list of (datetime, context_snippet) tuples.
    """
    results: list[tuple[datetime, str]] = []
    lines = text.split("\n")

    for line in lines:
        # Check if any deadline keyword is in this line
        has_keyword = any(kw.lower() in line.lower() for kw in DEADLINE_KEYWORDS)
        if not has_keyword:
            continue

        # Try each date pattern
        for pattern, _ in DATE_PATTERNS:
            for match in re.finditer(pattern, line):
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        # Determine year/month/day order from pattern
                        if "年" in pattern or pattern.startswith(r"(\d{4})"):
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])

                        dt = datetime(year, month, day, tzinfo=timezone.utc)
                        # Only include future or recent dates
                        now = datetime.now(timezone.utc)
                        if dt >= now - timedelta(days=7):
                            snippet = line.strip()[:100]
                            results.append((dt, snippet))
                except (ValueError, OverflowError):
                    continue

    return results


async def scan_for_deadlines(
    db: AsyncSession, user_id: int, text: str, source_path: str = ""
) -> list[Reminder]:
    """Scan text for deadline dates and create reminders.

    Returns list of newly created reminders.
    """
    dates = extract_dates_from_text(text)
    created: list[Reminder] = []
    now = datetime.now(timezone.utc)

    for dt, snippet in dates:
        days_until = (dt - now).days

        # Determine priority
        if days_until <= 3:
            priority = "high"
        elif days_until <= 14:
            priority = "medium"
        else:
            priority = "low"

        # Check for duplicate (same user, same source, same date)
        existing = await db.execute(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.reminder_type == "deadline",
                Reminder.related_id == source_path,
                Reminder.due_date == dt,
            )
        )
        if existing.scalar_one_or_none():
            continue

        reminder = Reminder(
            user_id=user_id,
            reminder_type="deadline",
            title=f"截止日期提醒：{dt.strftime('%Y/%m/%d')}",
            message=snippet,
            related_id=source_path,
            status="active",
            priority=priority,
            due_date=dt,
        )
        db.add(reminder)
        created.append(reminder)

    if created:
        await db.commit()
        for r in created:
            await db.refresh(r)

    return created
