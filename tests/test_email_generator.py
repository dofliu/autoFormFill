"""
Tests for email_generator — RAG-powered email draft generation.

All tests mock ``search_all_collections`` and ``get_llm_adapter``
so no real LLM or ChromaDB calls are made.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import SourceChunk
from app.schemas.email import EmailDraftRequest
from app.services.email_generator import build_email_prompt, email_draft_stream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(text: str, collection: str = "academic_papers", distance: float = 0.3) -> SourceChunk:
    """Create a mock SourceChunk."""
    return SourceChunk(
        text=text,
        metadata={"title": "Test Paper", "source": "test.pdf"},
        distance=distance,
        collection=collection,
    )


def _mock_adapter(chunks: list[str]):
    """Create a mock LLM adapter that yields given chunks via generate_text_stream."""
    adapter = MagicMock()

    async def _stream(*args, **kwargs):
        for c in chunks:
            yield c

    adapter.generate_text_stream = MagicMock(side_effect=_stream)
    return adapter


async def _collect_events(async_gen) -> list[dict]:
    """Collect all SSE events from an async generator into a list of dicts."""
    events = []
    async for raw in async_gen:
        # Parse "data: {...}\n\n" format
        line = raw.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# build_email_prompt() tests
# ---------------------------------------------------------------------------

class TestBuildEmailPrompt:
    """Tests for the prompt construction function."""

    def test_includes_recipient_info(self):
        """Prompt should contain recipient name and email."""
        sources = [_source("Research paper about AI.")]
        prompt = build_email_prompt(
            recipient_name="Prof. Wang",
            recipient_email="wang@ntu.edu.tw",
            subject_hint="Research collaboration",
            purpose="Invite to collaborate on AI project",
            tone="formal",
            context_chunks=sources,
        )

        assert "Prof. Wang" in prompt
        assert "wang@ntu.edu.tw" in prompt

    def test_includes_tone(self):
        """Prompt should contain the requested tone."""
        prompt = build_email_prompt(
            recipient_name="Alice",
            recipient_email="alice@test.com",
            subject_hint=None,
            purpose="Say hello",
            tone="friendly",
            context_chunks=[],
        )

        assert "friendly" in prompt

    def test_includes_subject_hint(self):
        """Subject hint should appear in prompt when provided."""
        prompt = build_email_prompt(
            recipient_name="Bob",
            recipient_email="bob@test.com",
            subject_hint="Project Update Q2",
            purpose="Update on project progress",
            tone="professional",
            context_chunks=[],
        )

        assert "Project Update Q2" in prompt

    def test_no_subject_hint(self):
        """When subject_hint is None, should show '(not specified)'."""
        prompt = build_email_prompt(
            recipient_name="Charlie",
            recipient_email="charlie@test.com",
            subject_hint=None,
            purpose="General inquiry",
            tone="professional",
            context_chunks=[],
        )

        assert "(not specified)" in prompt

    def test_includes_purpose(self):
        """User's purpose should appear in the prompt."""
        prompt = build_email_prompt(
            recipient_name="Dave",
            recipient_email="dave@test.com",
            subject_hint=None,
            purpose="Discuss research findings on quantum computing",
            tone="professional",
            context_chunks=[],
        )

        assert "Discuss research findings on quantum computing" in prompt

    def test_includes_context_from_sources(self):
        """Retrieved context should be formatted and included."""
        sources = [
            _source("Our lab published a paper on NLP transformers."),
            _source("The research project covers deep learning for vision.", collection="research_projects"),
        ]
        prompt = build_email_prompt(
            recipient_name="Eve",
            recipient_email="eve@test.com",
            subject_hint=None,
            purpose="Share research progress",
            tone="professional",
            context_chunks=sources,
        )

        assert "NLP transformers" in prompt
        assert "deep learning for vision" in prompt
        assert "[Source 1]" in prompt
        assert "[Source 2]" in prompt

    def test_empty_context(self):
        """Empty context should show '(No relevant documents found)'."""
        prompt = build_email_prompt(
            recipient_name="Frank",
            recipient_email="frank@test.com",
            subject_hint=None,
            purpose="General inquiry",
            tone="professional",
            context_chunks=[],
        )

        assert "(No relevant documents found)" in prompt

    def test_context_includes_collection_name(self):
        """Source formatting should include the collection name."""
        sources = [_source("Some text.", collection="auto_indexed")]
        prompt = build_email_prompt(
            recipient_name="Grace",
            recipient_email="grace@test.com",
            subject_hint=None,
            purpose="Ask about indexed documents",
            tone="professional",
            context_chunks=sources,
        )

        assert "auto_indexed" in prompt


# ---------------------------------------------------------------------------
# email_draft_stream() — SSE event sequence
# ---------------------------------------------------------------------------

class TestEmailDraftStreamEvents:
    """Tests for the SSE event sequence of email_draft_stream()."""

    @pytest.mark.asyncio
    async def test_event_sequence_sources_chunks_done(self):
        """Normal flow should emit: sources → chunk(s) → done."""
        mock_sources = [_source("Research context about AI applications.")]
        mock_chunks = ["Dear ", "Prof. Wang,\n\n", "I hope this email finds you well."]
        adapter = _mock_adapter(mock_chunks)

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Prof. Wang",
                    recipient_email="wang@ntu.edu.tw",
                    purpose="Research collaboration",
                )
            )

        # Check event types in order
        event_types = [e["type"] for e in events]
        assert event_types[0] == "sources"
        assert event_types[-1] == "done"
        # All middle events should be chunks
        for t in event_types[1:-1]:
            assert t == "chunk"

    @pytest.mark.asyncio
    async def test_sources_event_contains_source_data(self):
        """Sources event should contain the retrieved documents."""
        mock_sources = [
            _source("Paper about machine learning.", collection="academic_papers"),
            _source("Project on NLP.", collection="research_projects"),
        ]
        adapter = _mock_adapter(["Email body here."])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test purpose",
                )
            )

        sources_event = events[0]
        assert sources_event["type"] == "sources"
        assert len(sources_event["sources"]) == 2
        assert sources_event["sources"][0]["collection"] == "academic_papers"
        assert sources_event["sources"][1]["collection"] == "research_projects"

    @pytest.mark.asyncio
    async def test_chunk_events_contain_text(self):
        """Chunk events should contain the streamed text fragments."""
        mock_sources = [_source("Context text for generation.")]
        adapter = _mock_adapter(["Hello ", "World"])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                )
            )

        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert len(chunk_events) == 2
        assert chunk_events[0]["content"] == "Hello "
        assert chunk_events[1]["content"] == "World"

    @pytest.mark.asyncio
    async def test_empty_sources_still_generates(self):
        """Even with no search results, should still attempt generation."""
        adapter = _mock_adapter(["Draft without context."])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=[]), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="General greeting",
                )
            )

        event_types = [e["type"] for e in events]
        assert "sources" in event_types
        assert "chunk" in event_types
        assert "done" in event_types


# ---------------------------------------------------------------------------
# email_draft_stream() — search query composition
# ---------------------------------------------------------------------------

class TestEmailDraftStreamSearch:
    """Tests for how email_draft_stream composes the search query."""

    @pytest.mark.asyncio
    async def test_search_query_includes_name_and_purpose(self):
        """Search query should combine recipient_name and purpose."""
        mock_search = AsyncMock(return_value=[])
        adapter = _mock_adapter(["Draft text."])

        with patch("app.services.sse_pipeline.search_all_collections", mock_search), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Prof. Chen",
                    recipient_email="chen@test.com",
                    purpose="discuss AI ethics",
                )
            )

        # Verify search was called with combined query
        mock_search.assert_called_once()
        query = mock_search.call_args[0][0]
        assert "Prof. Chen" in query
        assert "discuss AI ethics" in query

    @pytest.mark.asyncio
    async def test_custom_collections_forwarded(self):
        """Custom collections should be forwarded to search."""
        mock_search = AsyncMock(return_value=[])
        adapter = _mock_adapter(["Draft."])

        with patch("app.services.sse_pipeline.search_all_collections", mock_search), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                    collections=["auto_indexed"],
                )
            )

        _, args, kwargs = mock_search.mock_calls[0]
        assert args[1] == ["auto_indexed"]

    @pytest.mark.asyncio
    async def test_custom_n_results_forwarded(self):
        """Custom n_results should be forwarded to search."""
        mock_search = AsyncMock(return_value=[])
        adapter = _mock_adapter(["Draft."])

        with patch("app.services.sse_pipeline.search_all_collections", mock_search), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                    n_results=10,
                )
            )

        _, args, kwargs = mock_search.mock_calls[0]
        assert args[2] == 10


# ---------------------------------------------------------------------------
# email_draft_stream() — prompt forwarding
# ---------------------------------------------------------------------------

class TestEmailDraftStreamPrompt:
    """Tests for how email_draft_stream builds and uses the prompt."""

    @pytest.mark.asyncio
    async def test_prompt_includes_tone(self):
        """The LLM prompt should include the requested tone."""
        mock_sources = [_source("Context for the email.")]
        adapter = _mock_adapter(["Draft."])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                    tone="formal",
                )
            )

        # Check the prompt passed to generate_text_stream
        call_args = adapter.generate_text_stream.call_args
        prompt = call_args[0][0]
        assert "formal" in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_subject_hint(self):
        """Subject hint should appear in the LLM prompt."""
        mock_sources = [_source("Context.")]
        adapter = _mock_adapter(["Draft."])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                    subject_hint="Meeting Request",
                )
            )

        prompt = adapter.generate_text_stream.call_args[0][0]
        assert "Meeting Request" in prompt

    @pytest.mark.asyncio
    async def test_llm_called_with_temperature_0_4(self):
        """Email generation should use temperature=0.4."""
        mock_sources = [_source("Context.")]
        adapter = _mock_adapter(["Draft."])

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                )
            )

        kwargs = adapter.generate_text_stream.call_args[1]
        assert kwargs.get("temperature") == 0.4


# ---------------------------------------------------------------------------
# email_draft_stream() — error handling
# ---------------------------------------------------------------------------

class TestEmailDraftStreamErrors:
    """Tests for error handling in email_draft_stream."""

    @pytest.mark.asyncio
    async def test_llm_error_emits_error_event(self):
        """If LLM streaming fails, an error event should be emitted."""
        mock_sources = [_source("Context.")]
        adapter = MagicMock()

        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("LLM unavailable")
            yield  # make it an async generator  # noqa: E501

        adapter.generate_text_stream = MagicMock(side_effect=_failing_stream)

        with patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock, return_value=mock_sources), \
             patch("app.services.sse_pipeline.get_llm_adapter", return_value=adapter):
            events = await _collect_events(
                email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                )
            )

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM unavailable" in error_events[0]["message"]

    @pytest.mark.asyncio
    async def test_search_error_propagates(self):
        """If search_all_collections raises, it should propagate."""
        with patch(
            "app.services.sse_pipeline.search_all_collections",
            new_callable=AsyncMock,
            side_effect=RuntimeError("ChromaDB down"),
        ):
            with pytest.raises(RuntimeError, match="ChromaDB down"):
                events = []
                async for raw in email_draft_stream(
                    recipient_name="Test",
                    recipient_email="test@test.com",
                    purpose="Test",
                ):
                    events.append(raw)


# ---------------------------------------------------------------------------
# EmailDraftRequest schema tests
# ---------------------------------------------------------------------------

class TestEmailDraftRequestSchema:
    """Tests for the Pydantic request model."""

    def test_required_fields(self):
        """Should require recipient_name, recipient_email, purpose."""
        req = EmailDraftRequest(
            recipient_name="Alice",
            recipient_email="alice@test.com",
            purpose="Hello",
        )
        assert req.recipient_name == "Alice"
        assert req.recipient_email == "alice@test.com"
        assert req.purpose == "Hello"

    def test_default_tone(self):
        """Default tone should be 'professional'."""
        req = EmailDraftRequest(
            recipient_name="Bob",
            recipient_email="bob@test.com",
            purpose="Greet",
        )
        assert req.tone == "professional"

    def test_default_n_results(self):
        """Default n_results should be 5."""
        req = EmailDraftRequest(
            recipient_name="Charlie",
            recipient_email="charlie@test.com",
            purpose="Ask",
        )
        assert req.n_results == 5

    def test_optional_fields(self):
        """Optional fields should be None by default."""
        req = EmailDraftRequest(
            recipient_name="Dave",
            recipient_email="dave@test.com",
            purpose="Inquiry",
        )
        assert req.subject_hint is None
        assert req.collections is None

    def test_custom_tone(self):
        """Custom tone should be accepted."""
        req = EmailDraftRequest(
            recipient_name="Eve",
            recipient_email="eve@test.com",
            purpose="Invite",
            tone="formal",
        )
        assert req.tone == "formal"
