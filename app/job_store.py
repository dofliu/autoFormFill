"""
Job Store - In-memory storage for form fill jobs
"""
import uuid
from typing import Dict, Optional, List
from datetime import datetime

class JobStore:
    def __init__(self):
        self._jobs: Dict[str, dict] = {}
    
    def create_job(self, job_data: dict) -> str:
        job_id = str(uuid.uuid4())
        job_data["job_id"] = job_id
        # Only set created_at if not already provided
        if "created_at" not in job_data:
            job_data["created_at"] = datetime.now().isoformat()
        self._jobs[job_id] = job_data
        return job_id
    
    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, updates: dict) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].update(updates)
            return True
        return False
    
    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False
    
    def get_jobs_by_user(self, user_id: int, limit: int = 20) -> List[dict]:
        """Get all jobs for a specific user, sorted by most recent first."""
        user_jobs = [
            job for job in self._jobs.values() 
            if job.get("user_id") == user_id
        ]
        # Sort by created_at descending (convert to datetime for proper sorting)
        def sort_key(job):
            created = job.get("created_at", "")
            try:
                return datetime.fromisoformat(created)
            except (ValueError, TypeError):
                return datetime.min
        user_jobs.sort(key=sort_key, reverse=True)
        return user_jobs[:limit]
    
    def get_jobs_by_template(self, template_filename: str, user_id: int, limit: int = 10) -> List[dict]:
        """Get jobs for a specific user that used the same template."""
        matching_jobs = [
            job for job in self._jobs.values()
            if job.get("user_id") == user_id and 
            job.get("template_filename") == template_filename
        ]
        # Sort by created_at descending (convert to datetime for proper sorting)
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
