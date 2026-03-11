"""Reminder CRUD + notification endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_ownership
from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas.error import ERR_NOT_FOUND, ERR_VALIDATION
from app.schemas.reminder import (
    FillDiffResult,
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.services import reminder_service
from app.job_store import job_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users/{user_id}/reminders",
    tags=["Reminders"],
)


def _reminder_response(r) -> ReminderResponse:
    d = r.to_dict()
    return ReminderResponse(**d)


# ---- CRUD ----

@router.post("/", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    user_id: int,
    data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Create a new reminder."""
    verify_ownership(current_user, user_id)
    reminder = await reminder_service.create_reminder(db, user_id, data)
    return _reminder_response(reminder)


@router.get("/", response_model=list[ReminderResponse])
async def list_reminders(
    user_id: int,
    status: str | None = Query(None, description="Filter by status: active, read, dismissed"),
    reminder_type: str | None = Query(None, description="Filter by type: deadline, fill_diff, manual"),
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """List reminders for a user."""
    verify_ownership(current_user, user_id)
    reminders = await reminder_service.list_reminders(
        db, user_id, status=status, reminder_type=reminder_type, limit=limit
    )
    return [_reminder_response(r) for r in reminders]


@router.get("/count")
async def count_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Get count of active (unread) reminders."""
    verify_ownership(current_user, user_id)
    count = await reminder_service.count_active_reminders(db, user_id)
    return {"count": count}


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    user_id: int,
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Get a single reminder."""
    verify_ownership(current_user, user_id)
    reminder = await reminder_service.get_reminder(db, reminder_id)
    if not reminder or reminder.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Reminder not found", "code": ERR_NOT_FOUND},
        )
    return _reminder_response(reminder)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    user_id: int,
    reminder_id: int,
    data: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Update a reminder (e.g. mark as read/dismissed)."""
    verify_ownership(current_user, user_id)
    existing = await reminder_service.get_reminder(db, reminder_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Reminder not found", "code": ERR_NOT_FOUND},
        )
    updated = await reminder_service.update_reminder(db, reminder_id, data)
    return _reminder_response(updated)


@router.post("/dismiss-all")
async def dismiss_all(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Dismiss all active reminders."""
    verify_ownership(current_user, user_id)
    count = await reminder_service.dismiss_all(db, user_id)
    return {"dismissed": count}


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    user_id: int,
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Delete a reminder."""
    verify_ownership(current_user, user_id)
    existing = await reminder_service.get_reminder(db, reminder_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Reminder not found", "code": ERR_NOT_FOUND},
        )
    await reminder_service.delete_reminder(db, reminder_id)


# ---- Fill Diff ----

@router.get("/fill-diff/{job_id}", response_model=FillDiffResult)
async def get_fill_diff(
    user_id: int,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Compare a job's fill results against the previous fill of the same template."""
    verify_ownership(current_user, user_id)
    job = await job_store.get_job(job_id, db)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Job not found", "code": ERR_NOT_FOUND},
        )

    result = await reminder_service.detect_fill_diffs(db, user_id, job)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"detail": "No previous fill found for comparison", "code": ERR_NOT_FOUND},
        )
    return result
