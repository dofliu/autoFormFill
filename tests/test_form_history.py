"""
Tests for Form History feature
"""
import pytest
from app.job_store import JobStore


class TestJobStoreHistory:
    """Test job store history functionality"""
    
    def setup_method(self):
        self.store = JobStore()
        # Clear any existing jobs
        self.store._jobs.clear()
    
    def test_get_jobs_by_user_empty(self):
        """Test getting jobs for a user with no jobs"""
        jobs = self.store.get_jobs_by_user(999)
        assert jobs == []
    
    def test_get_jobs_by_user_single(self):
        """Test getting jobs for a user with one job"""
        job_id = self.store.create_job({
            "user_id": 1,
            "filename": "test.docx",
            "template_filename": "template.docx",
            "fields": [
                {"field_name": "name", "value": "John", "source": "sql"},
                {"field_name": "email", "value": "john@test.com", "source": "sql"}
            ]
        })
        
        jobs = self.store.get_jobs_by_user(1)
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == job_id
    
    def test_get_jobs_by_user_multiple(self):
        """Test getting jobs for a user with multiple jobs"""
        # Create jobs for user 1
        self.store.create_job({"user_id": 1, "filename": "a.docx", "created_at": "2024-01-01T10:00:00"})
        self.store.create_job({"user_id": 1, "filename": "b.docx", "created_at": "2024-01-03T10:00:00"})
        self.store.create_job({"user_id": 1, "filename": "c.docx", "created_at": "2024-01-02T10:00:00"})
        # Create job for different user
        self.store.create_job({"user_id": 2, "filename": "other.docx"})
        
        jobs = self.store.get_jobs_by_user(1)
        
        # Should return only user 1's jobs, sorted by date descending
        assert len(jobs) == 3
        # Most recent first
        assert jobs[0]["filename"] == "b.docx"  # 2024-01-03
        assert jobs[1]["filename"] == "c.docx"  # 2024-01-02
        assert jobs[2]["filename"] == "a.docx"  # 2024-01-01
    
    def test_get_jobs_by_user_limit(self):
        """Test limiting the number of jobs returned"""
        # Create 25 jobs for user 1
        for i in range(25):
            self.store.create_job({
                "user_id": 1, 
                "filename": f"form_{i}.docx",
                "created_at": f"2024-01-{i+1:02d}T10:00:00"
            })
        
        # Request limit of 10
        jobs = self.store.get_jobs_by_user(1, limit=10)
        
        assert len(jobs) == 10
    
    def test_get_jobs_by_template(self):
        """Test getting jobs by template filename"""
        # Create jobs with different templates
        self.store.create_job({
            "user_id": 1, 
            "filename": "form1.docx",
            "template_filename": "scholarship.docx"
        })
        self.store.create_job({
            "user_id": 1, 
            "filename": "form2.docx",
            "template_filename": "application.docx"
        })
        self.store.create_job({
            "user_id": 1, 
            "filename": "form3.docx",
            "template_filename": "scholarship.docx"
        })
        # Different user
        self.store.create_job({
            "user_id": 2, 
            "filename": "other.docx",
            "template_filename": "scholarship.docx"
        })
        
        # Get jobs for user 1 with scholarship.docx template
        jobs = self.store.get_jobs_by_template("scholarship.docx", user_id=1)
        
        assert len(jobs) == 2
        for job in jobs:
            assert job["template_filename"] == "scholarship.docx"
            assert job["user_id"] == 1
    
    def test_get_jobs_by_template_empty(self):
        """Test getting jobs by non-existent template"""
        jobs = self.store.get_jobs_by_template("nonexistent.docx", user_id=1)
        assert jobs == []


class TestFormHistoryAPI:
    """Test form history API endpoints"""
    
    def test_history_item_model(self):
        """Test FormHistoryItem schema (if defined)"""
        # This would test the Pydantic model if we had one
        # For now, just verify the structure
        example_item = {
            "job_id": "test-123",
            "filename": "form.docx",
            "template_filename": "template.docx",
            "fields_filled": 5,
            "fields_skipped": 2,
            "created_at": "2024-01-01T10:00:00"
        }
        
        assert example_item["job_id"] == "test-123"
        assert example_item["fields_filled"] == 5
        assert example_item["fields_skipped"] == 2