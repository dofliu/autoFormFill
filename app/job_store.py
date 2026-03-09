"""
Job Store - Database-backed storage for form fill jobs
Now uses SQLite database for persistence!
"""
import uuid
from typing import Dict, Optional, List
from datetime import datetime

# Import job service for database operations
from app.services import job_service

# This module provides both sync (fallback) and async (database) interfaces
# The router will use async methods when db session is available


class JobStore:
    """
    Job Store with database-backed persistence.
    Falls back to in-memory if no db session provided.
    """
    
    # In-memory fallback storage
    _memory_store: Dict[str, dict] = {}
    _use_database: bool = True  # Flag to use database
    
    def create_job(self, job_data: dict, db=None) -> str:
        """Create a new job. Uses database if db session provided."""
        if db and self._use_database:
            # Use database
            import asyncio
            try:
                # Run async function in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we need to schedule the coroutine
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            job_service.create_job(db, job_data)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.create_job(db, job_data))
            except Exception:
                # Fallback to memory
                pass
        
        # Fallback to in-memory
        job_id = str(uuid.uuid4())
        job_data["job_id"] = job_id
        if "created_at" not in job_data:
            job_data["created_at"] = datetime.now().isoformat()
        self._memory_store[job_id] = job_data
        return job_id
    
    def get_job(self, job_id: str, db=None) -> Optional[dict]:
        """Get a job by ID. Uses database if db session provided."""
        if db and self._use_database:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            job_service.get_job(db, job_id)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.get_job(db, job_id))
            except Exception:
                pass
        
        return self._memory_store.get(job_id)
    
    def update_job(self, job_id: str, updates: dict, db=None) -> bool:
        """Update a job. Uses database if db session provided."""
        if db and self._use_database:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            job_service.update_job(db, job_id, updates)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.update_job(db, job_id, updates))
            except Exception:
                pass
        
        if job_id in self._memory_store:
            self._memory_store[job_id].update(updates)
            return True
        return False
    
    def delete_job(self, job_id: str, db=None) -> bool:
        """Delete a job. Uses database if db session provided."""
        if db and self._use_database:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            job_service.delete_job(db, job_id)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.delete_job(db, job_id))
            except Exception:
                pass
        
        if job_id in self._memory_store:
            del self._memory_store[job_id]
            return True
        return False
    
    def get_jobs_by_user(self, user_id: int, limit: int = 20, db=None) -> List[dict]:
        """Get all jobs for a user. Uses database if db session provided."""
        if db and self._use_database:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            job_service.get_jobs_by_user(db, user_id, limit)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.get_jobs_by_user(db, user_id, limit))
            except Exception:
                pass
        
        # Fallback to in-memory
        user_jobs = [
            job for job in self._memory_store.values() 
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
    
    def get_jobs_by_template(self, template_filename: str, user_id: int, limit: int = 10, db=None) -> List[dict]:
        """Get jobs by template. Uses database if db session provided."""
        if db and self._use_database:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            job_service.get_jobs_by_template(db, template_filename, user_id, limit)
                        )
                        return future.result()
                else:
                    return asyncio.run(job_service.get_jobs_by_template(db, template_filename, user_id, limit))
            except Exception:
                pass
        
        # Fallback to in-memory
        matching_jobs = [
            job for job in self._memory_store.values()
            if job.get("user_id") == user_id and 
            job.get("template_filename") == template_filename
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
