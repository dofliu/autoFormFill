"""
Job Store - Database-backed storage for form fill jobs.

All methods are async. Uses SQLite database when db session is provided,
falls back to in-memory storage otherwise.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import job_service


class JobStore:
    """
    Job Store with database-backed persistence.
    All methods are async. Falls back to in-memory if no db session provided.
    """

    # In-memory fallback storage
    _memory_store: Dict[str, dict] = {}

    async def create_job(
        self, job_data: dict, db: Optional[AsyncSession] = None
    ) -> str:
        """Create a new job. Uses database if db session provided."""
        if db:
            try:
                return await job_service.create_job(db, job_data)
            except Exception:
                pass  # Fallback to memory

        # In-memory fallback
        job_id = str(uuid.uuid4())
        job_data["job_id"] = job_id
        if "created_at" not in job_data:
            job_data["created_at"] = datetime.now().isoformat()
        self._memory_store[job_id] = job_data
        return job_id

    async def get_job(
        self, job_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[dict]:
        """Get a job by ID. Uses database if db session provided."""
        if db:
            try:
                result = await job_service.get_job(db, job_id)
                if result:
                    return result
            except Exception:
                pass

        return self._memory_store.get(job_id)

    async def update_job(
        self, job_id: str, updates: dict, db: Optional[AsyncSession] = None
    ) -> bool:
        """Update a job. Uses database if db session provided."""
        if db:
            try:
                return await job_service.update_job(db, job_id, updates)
            except Exception:
                pass

        if job_id in self._memory_store:
            self._memory_store[job_id].update(updates)
            return True
        return False

    async def delete_job(
        self, job_id: str, db: Optional[AsyncSession] = None
    ) -> bool:
        """Delete a job. Uses database if db session provided."""
        if db:
            try:
                return await job_service.delete_job(db, job_id)
            except Exception:
                pass

        if job_id in self._memory_store:
            del self._memory_store[job_id]
            return True
        return False

    async def get_jobs_by_user(
        self, user_id: int, limit: int = 20, db: Optional[AsyncSession] = None
    ) -> List[dict]:
        """Get all jobs for a user. Uses database if db session provided."""
        if db:
            try:
                return await job_service.get_jobs_by_user(db, user_id, limit)
            except Exception:
                pass

        # In-memory fallback
        user_jobs = [
            job
            for job in self._memory_store.values()
            if job.get("user_id") == user_id
        ]

        def sort_key(job):
            created = job.get("created_at", "")
            try:
                return datetime.fromisoformat(created)
            except (ValueError, TypeError):
                return datetime.min

        user_jobs.sort(key=sort_key, reverse=True)
        return user_jobs[:limit]

    async def get_jobs_by_template(
        self,
        template_filename: str,
        user_id: int,
        limit: int = 10,
        db: Optional[AsyncSession] = None,
    ) -> List[dict]:
        """Get jobs by template. Uses database if db session provided."""
        if db:
            try:
                return await job_service.get_jobs_by_template(
                    db, template_filename, user_id, limit
                )
            except Exception:
                pass

        # In-memory fallback
        matching_jobs = [
            job
            for job in self._memory_store.values()
            if job.get("user_id") == user_id
            and job.get("template_filename") == template_filename
        ]

        def sort_key(job):
            created = job.get("created_at", "")
            try:
                return datetime.fromisoformat(created)
            except (ValueError, TypeError):
                return datetime.min

        matching_jobs.sort(key=sort_key, reverse=True)
        return matching_jobs[:limit]


# Global instance
job_store = JobStore()
