"""
Unit tests for Form Preview feature — async JobStore + schemas + integration
"""
import os
import tempfile
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.job_store import JobStore, job_store
from app.schemas.form import FormPreviewResponse, FormSubmitRequest, FieldFillResult
from app.services.form_filler import submit_form_with_overrides


class TestJobStore:
    """Test job store functionality (in-memory mode, async)"""

    def setup_method(self):
        self.store = JobStore()
        self.store._memory_store.clear()

    @pytest.mark.asyncio
    async def test_create_job(self):
        """Test creating a job"""
        job_data = {"test": "data", "user_id": 1}
        job_id = await self.store.create_job(job_data)

        assert isinstance(job_id, str)
        assert len(job_id) > 0

        job = await self.store.get_job(job_id)
        assert job is not None
        assert job["test"] == "data"
        assert job["user_id"] == 1
        assert "job_id" in job
        assert "created_at" in job

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self):
        """Test getting a non-existent job"""
        job = await self.store.get_job("non-existent-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_update_job(self):
        """Test updating a job"""
        job_id = await self.store.create_job({"test": "data"})

        # Update the job
        success = await self.store.update_job(job_id, {"new_field": "value"})
        assert success is True

        job = await self.store.get_job(job_id)
        assert job["test"] == "data"  # Original data preserved
        assert job["new_field"] == "value"  # New data added

    @pytest.mark.asyncio
    async def test_update_nonexistent_job(self):
        """Test updating a non-existent job"""
        success = await self.store.update_job("non-existent-id", {"test": "data"})
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_job(self):
        """Test deleting a job"""
        job_id = await self.store.create_job({"test": "data"})

        # Delete the job
        success = await self.store.delete_job(job_id)
        assert success is True

        # Job should no longer exist
        job = await self.store.get_job(job_id)
        assert job is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self):
        """Test deleting a non-existent job"""
        success = await self.store.delete_job("non-existent-id")
        assert success is False


class TestFormPreviewSchemas:
    """Test form preview schemas"""

    def test_form_preview_response(self):
        """Test FormPreviewResponse schema"""
        fields = [
            FieldFillResult(
                field_name="name",
                value="John Doe",
                source="sql",
                confidence=0.95
            )
        ]

        response = FormPreviewResponse(
            job_id="test-job-id",
            filename="test.docx",
            template_filename="template.docx",
            fields=fields,
            created_at="2024-01-01T00:00:00"
        )

        assert response.job_id == "test-job-id"
        assert response.filename == "test.docx"
        assert response.template_filename == "template.docx"
        assert len(response.fields) == 1
        assert response.fields[0].field_name == "name"
        assert response.created_at == "2024-01-01T00:00:00"

    def test_form_submit_request(self):
        """Test FormSubmitRequest schema"""
        request = FormSubmitRequest(
            job_id="test-job-id",
            field_overrides={"name": "Jane Doe"}
        )

        assert request.job_id == "test-job-id"
        assert request.field_overrides == {"name": "Jane Doe"}


class TestFormFillerIntegration:
    """Test integration between form_filler and job_store"""

    @pytest.mark.asyncio
    async def test_submit_form_with_overrides(self):
        """Test submit_form_with_overrides function"""
        # Mock job data
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "filename": "test_form.docx",
            "template_filename": "test.docx",
            "user_id": 1,
            "fields": [],
            "fill_data": {},
            "output_path": "/tmp/output.docx",
            "field_overrides": {"existing": "value"}
        }

        # Add job to store
        job_store._memory_store[job_id] = job_data

        # Mock dependencies
        mock_db = AsyncMock()

        # Create a dummy template file for testing
        os.makedirs("data/uploads", exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False, dir='data/uploads') as f:
            temp_template = os.path.basename(f.name)
            job_data["template_filename"] = temp_template

        try:
            with patch('app.services.form_filler.fill_form') as mock_fill_form:
                # Mock the fill_form response
                mock_response = MagicMock()
                mock_response.job_id = "new-job-id"
                mock_fill_form.return_value = mock_response

                # Call the function
                result = await submit_form_with_overrides(
                    job_id=job_id,
                    field_overrides={"new_field": "new_value"},
                    db=mock_db
                )

                # Verify fill_form was called with merged overrides
                mock_fill_form.assert_called_once()
                call_kwargs = mock_fill_form.call_args.kwargs
                assert call_kwargs["field_overrides"] == {
                    "existing": "value",
                    "new_field": "new_value"
                }
                assert call_kwargs["user_id"] == 1
        finally:
            # Clean up
            if job_id in job_store._memory_store:
                del job_store._memory_store[job_id]
            # Clean up temp file
            temp_path = os.path.join("data/uploads", temp_template)
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_submit_form_job_not_found(self):
        """Test submit_form_with_overrides with non-existent job"""
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Job non-existent-id not found"):
            await submit_form_with_overrides(
                job_id="non-existent-id",
                field_overrides={},
                db=mock_db
            )
