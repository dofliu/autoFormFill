"""
Tests for LLM retry logic, error response schema, and service-level fallbacks.

Covers:
- is_retryable() classification
- with_retry() exponential backoff decorator
- Intent router SKIP fallback on LLM failure
- RAG pipeline [需人工補充] fallback on LLM failure
- SSE pipeline stream retry
- ErrorResponse schema
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.retry import is_retryable, with_retry
from app.schemas.error import ERR_INTERNAL, ERR_NOT_FOUND, ERR_VALIDATION, ErrorResponse


# ---------------------------------------------------------------------------
# is_retryable() tests
# ---------------------------------------------------------------------------

class TestIsRetryable:

    def test_timeout_error_is_retryable(self):
        assert is_retryable(TimeoutError("timed out")) is True

    def test_asyncio_timeout_is_retryable(self):
        assert is_retryable(asyncio.TimeoutError()) is True

    def test_value_error_is_not_retryable(self):
        assert is_retryable(ValueError("bad input")) is False

    def test_runtime_error_is_not_retryable(self):
        assert is_retryable(RuntimeError("crash")) is False

    def test_generic_exception_is_not_retryable(self):
        assert is_retryable(Exception("generic")) is False

    def test_server_error_is_retryable(self):
        """google.genai ServerError should be retryable."""
        try:
            from google.genai.errors import ServerError
            exc = ServerError.__new__(ServerError)
            assert is_retryable(exc) is True
        except ImportError:
            pytest.skip("google.genai not installed")

    def test_api_error_429_is_retryable(self):
        """Rate limit error (429) should be retryable."""
        try:
            from google.genai.errors import APIError
            exc = APIError.__new__(APIError)
            exc.code = 429
            assert is_retryable(exc) is True
        except ImportError:
            pytest.skip("google.genai not installed")

    def test_api_error_400_is_not_retryable(self):
        """Client error (400) should NOT be retryable."""
        try:
            from google.genai.errors import APIError
            exc = APIError.__new__(APIError)
            exc.code = 400
            assert is_retryable(exc) is False
        except ImportError:
            pytest.skip("google.genai not installed")


# ---------------------------------------------------------------------------
# with_retry() decorator tests
# ---------------------------------------------------------------------------

class TestWithRetry:

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        """Function that succeeds immediately should return normally."""
        @with_retry(max_attempts=3, base_delay=0.01, timeout=5.0)
        async def fn():
            return "ok"

        result = await fn()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retries_on_timeout_then_succeeds(self):
        """Should retry on TimeoutError and succeed on second attempt."""
        call_count = 0

        async def fn_impl():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("first call timed out")
            return "recovered"

        @with_retry(max_attempts=3, base_delay=0.01, timeout=5.0)
        async def fn():
            return await fn_impl()

        result = await fn()
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Non-retryable errors should propagate immediately."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, timeout=5.0)
        async def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            await fn()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """After max retries, the last error should propagate."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, timeout=5.0)
        async def fn():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("always times out")

        with pytest.raises(TimeoutError, match="always times out"):
            await fn()
        assert call_count == 3


# ---------------------------------------------------------------------------
# RAG pipeline fallback tests
# ---------------------------------------------------------------------------

class TestRagPipelineFallback:

    @pytest.mark.asyncio
    async def test_returns_placeholder_on_llm_failure(self):
        """RAG pipeline should return [需人工補充] if LLM call fails."""
        adapter = MagicMock()
        adapter.generate_text = AsyncMock(side_effect=RuntimeError("LLM down"))

        mock_search = AsyncMock(return_value=[
            {"text": "Some relevant academic content about the topic.", "metadata": {}, "distance": 0.5}
        ])

        with (
            patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter),
            patch("app.services.rag_pipeline.search_documents", mock_search),
        ):
            from app.services.rag_pipeline import generate_field_content
            text, confidence = await generate_field_content(
                field_name="research_summary",
                search_query="research projects",
            )

        assert text == "[需人工補充]"
        assert confidence == 0.0


# ---------------------------------------------------------------------------
# SSE pipeline stream retry tests
# ---------------------------------------------------------------------------

class TestSsePipelineRetry:

    @pytest.mark.asyncio
    async def test_stream_retry_on_transient_error(self):
        """SSE pipeline should retry once on a retryable error."""
        call_count = 0

        async def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("stream timeout")
            yield "chunk1"
            yield "chunk2"

        adapter = MagicMock()
        adapter.generate_text_stream = mock_stream

        mock_sources = AsyncMock(return_value=[])

        with (
            patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter),
            patch("app.services.sse_pipeline.search_all_collections", mock_sources),
        ):
            from app.services.sse_pipeline import rag_sse_stream, StreamConfig
            events = []
            async for event in rag_sse_stream(
                search_query="test",
                build_prompt=lambda _: "prompt",
                config=StreamConfig(temperature=0.3, max_tokens=100),
            ):
                events.append(event)

        # Should have: sources + chunk1 + chunk2 + done
        event_types = []
        import json as json_mod
        for ev in events:
            data = json_mod.loads(ev.replace("data: ", "").strip())
            event_types.append(data["type"])

        assert "error" not in event_types
        assert "done" in event_types
        assert call_count == 2  # first call failed, second succeeded

    @pytest.mark.asyncio
    async def test_stream_emits_error_after_max_retries(self):
        """SSE pipeline should emit error event if all retries exhausted."""
        async def mock_stream(*args, **kwargs):
            raise TimeoutError("always fails")
            yield  # make it an async generator  # noqa: RUF027

        adapter = MagicMock()
        adapter.generate_text_stream = mock_stream

        mock_sources = AsyncMock(return_value=[])

        with (
            patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter),
            patch("app.services.sse_pipeline.search_all_collections", mock_sources),
        ):
            from app.services.sse_pipeline import rag_sse_stream, StreamConfig
            events = []
            async for event in rag_sse_stream(
                search_query="test",
                build_prompt=lambda _: "prompt",
                config=StreamConfig(temperature=0.3, max_tokens=100),
            ):
                events.append(event)

        import json as json_mod
        event_types = [json_mod.loads(ev.replace("data: ", "").strip())["type"] for ev in events]
        assert "error" in event_types
        assert "done" not in event_types


# ---------------------------------------------------------------------------
# ErrorResponse schema tests
# ---------------------------------------------------------------------------

class TestErrorResponseSchema:

    def test_full_error_response(self):
        err = ErrorResponse(detail="Not found", code=ERR_NOT_FOUND, field="user_id")
        d = err.model_dump()
        assert d["detail"] == "Not found"
        assert d["code"] == "not_found"
        assert d["field"] == "user_id"

    def test_error_response_without_field(self):
        err = ErrorResponse(detail="Server error", code=ERR_INTERNAL)
        d = err.model_dump()
        assert d["field"] is None

    def test_error_response_validation_code(self):
        err = ErrorResponse(detail="Invalid input", code=ERR_VALIDATION, field="email")
        assert err.code == "validation_error"
        assert err.field == "email"
