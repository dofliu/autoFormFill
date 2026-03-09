import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_job import FormJob


async def create_job(db: AsyncSession, job_data: dict) -> str:
    """Create a new form job in the database."""
    job_id = str(uuid.uuid4())
    job = FormJob(
        job_id=job_id,
        user_id=job_data["user_id"],
        filename=job_data["filename"],
        template_filename=job_data["template_filename"],
        output_path=job_data.get("output_path", ""),
        fields_json=json.dumps(job_data.get("fields", []), ensure_ascii=False),
        fill_data_json=json.dumps(job_data.get("fill_data", {}), ensure_ascii=False),
        field_overrides_json=json.dumps(job_data.get("field_overrides", {}), ensure_ascii=False),
        created_at=datetime.now(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job_id


async def get_job(db: AsyncSession, job_id: str) -> Optional[dict]:
    """Get a job by job_id."""
    result = await db.execute(select(FormJob).where(FormJob.job_id == job_id))
    job = result.scalar_one_or_none()
    return job.to_dict() if job else None


async def update_job(db: AsyncSession, job_id: str, updates: dict) -> bool:
    """Update a job with new data."""
    result = await db.execute(select(FormJob).where(FormJob.job_id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return False
    
    for key, value in updates.items():
        if hasattr(job, key):
            setattr(job, key, value)
    
    await db.commit()
    return True


async def delete_job(db: AsyncSession, job_id: str) -> bool:
    """Delete a job by job_id."""
    result = await db.execute(select(FormJob).where(FormJob.job_id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return False
    
    await db.delete(job)
    await db.commit()
    return True


async def get_jobs_by_user(db: AsyncSession, user_id: int, limit: int = 20) -> list[dict]:
    """Get all jobs for a specific user, sorted by most recent first."""
    result = await db.execute(
        select(FormJob)
        .where(FormJob.user_id == user_id)
        .order_by(FormJob.created_at.desc())
        .limit(limit)
    )
    return [row.to_dict() for row in result.scalars().all()]


async def get_jobs_by_template(
    db: AsyncSession, template_filename: str, user_id: int, limit: int = 10
) -> list[dict]:
    """Get jobs for a specific user that used the same template."""
    result = await db.execute(
        select(FormJob)
        .where(FormJob.user_id == user_id, FormJob.template_filename == template_filename)
        .order_by(FormJob.created_at.desc())
        .limit(limit)
    )
    return [row.to_dict() for row in result.scalars().all()]
