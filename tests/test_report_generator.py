"""
Tests for report_generator — structured report generation via RAG + SSE streaming.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import SourceChunk
from app.schemas.report import ReportRequest
from app.services.report_generator import (
    AUDIENCE_TONE,
    DEFAULT_SECTIONS,
    build_report_prompt,
    report_stream,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(
    text: str,
    collection: str = "academic_papers",
    distance: float = 0.3,
) -> SourceChunk:
    """Create a mock SourceChunk."""
    return SourceChunk(
        text=text,
        metadata={"title": "Test Paper", "source": "test.pdf"},
        distance=distance,
        collection=collection,
    )


def _mock_adapter(chunks: list[str]):
    """Create a mock LLM adapter that yields given chunks."""
    adapter = MagicMock()

    async def _stream(*args, **kwargs):
        for c in chunks:
            yield c

    adapter.generate_text_stream = MagicMock(side_effect=_stream)
    return adapter


async def _collect_events(async_gen) -> list[dict]:
    """Collect all SSE events from an async generator."""
    events = []
    async for raw in async_gen:
        line = raw.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# build_report_prompt() tests
# ---------------------------------------------------------------------------

class TestBuildReportPrompt:
    """Tests for report prompt assembly."""

    def test_basic_prompt_contains_topic(self):
        """Topic should appear in the prompt."""
        prompt = build_report_prompt(
            topic="AI in healthcare",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="en",
            context_chunks=[_source("Some research data")],
        )
        assert "AI in healthcare" in prompt

    def test_prompt_contains_context(self):
        """Context chunks should be formatted in the prompt."""
        src = _source("Deep learning results show 95% accuracy")
        prompt = build_report_prompt(
            topic="DL accuracy",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="en",
            context_chunks=[src],
        )
        assert "Deep learning results show 95% accuracy" in prompt
        assert "[Source 1" in prompt

    def test_prompt_uses_default_sections_for_summary(self):
        """Summary report should use default summary sections."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="zh-TW",
            context_chunks=[],
        )
        for section in DEFAULT_SECTIONS["summary"]:
            assert section in prompt

    def test_prompt_uses_default_sections_for_detailed(self):
        """Detailed report should use longer default outline."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="detailed",
            target_audience="academic",
            sections=None,
            language="en",
            context_chunks=[],
        )
        for section in DEFAULT_SECTIONS["detailed"]:
            assert section in prompt

    def test_prompt_uses_default_sections_for_executive(self):
        """Executive report should use executive outline."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="executive",
            target_audience="business",
            sections=None,
            language="en",
            context_chunks=[],
        )
        for section in DEFAULT_SECTIONS["executive"]:
            assert section in prompt

    def test_prompt_uses_custom_sections(self):
        """Custom sections should override defaults."""
        custom = ["Introduction", "Analysis", "Conclusion"]
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="academic",
            sections=custom,
            language="en",
            context_chunks=[],
        )
        for section in custom:
            assert section in prompt
        # Default summary sections should NOT be present
        for default_section in DEFAULT_SECTIONS["summary"]:
            assert default_section not in prompt

    def test_prompt_audience_tone(self):
        """Prompt should reflect target audience tone."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="business",
            sections=None,
            language="en",
            context_chunks=[],
        )
        assert AUDIENCE_TONE["business"] in prompt

    def test_prompt_language_field(self):
        """Language preference should appear in prompt."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="zh-TW",
            context_chunks=[],
        )
        assert "zh-TW" in prompt

    def test_empty_context_placeholder(self):
        """Empty context should show placeholder message."""
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="en",
            context_chunks=[],
        )
        assert "No context documents found" in prompt

    def test_multiple_context_chunks(self):
        """Multiple sources should be numbered sequentially."""
        sources = [
            _source("First source"),
            _source("Second source", collection="research_projects"),
            _source("Third source", collection="auto_indexed"),
        ]
        prompt = build_report_prompt(
            topic="Test",
            report_type="summary",
            target_audience="academic",
            sections=None,
            language="en",
            context_chunks=sources,
        )
        assert "[Source 1" in prompt
        assert "[Source 2" in prompt
        assert "[Source 3" in prompt
        assert "First source" in prompt
        assert "Third source" in prompt


# ---------------------------------------------------------------------------
# report_stream() SSE event tests
# ---------------------------------------------------------------------------

class TestReportStreamEvents:
    """Tests for SSE event sequence from report_stream()."""

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_event_sequence(self, mock_search, mock_get_adapter):
        """Events should follow: sources → chunks → done."""
        mock_search.return_value = [_source("context data")]
        mock_get_adapter.return_value = _mock_adapter(["Report ", "content."])

        events = await _collect_events(
            report_stream(topic="Test topic")
        )

        types = [e["type"] for e in events]
        assert types[0] == "sources"
        assert "chunk" in types
        assert types[-1] == "done"

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_sources_event_contains_data(self, mock_search, mock_get_adapter):
        """Sources event should contain the searched documents."""
        mock_search.return_value = [
            _source("Source A"),
            _source("Source B", collection="research_projects"),
        ]
        mock_get_adapter.return_value = _mock_adapter(["Done."])

        events = await _collect_events(report_stream(topic="Test"))

        sources_event = events[0]
        assert sources_event["type"] == "sources"
        assert len(sources_event["sources"]) == 2

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_chunk_content_concatenation(self, mock_search, mock_get_adapter):
        """Chunk events should contain LLM text fragments."""
        mock_search.return_value = []
        mock_get_adapter.return_value = _mock_adapter(["## Summary\n", "This is a ", "test report."])

        events = await _collect_events(report_stream(topic="Test"))

        chunk_texts = [e["content"] for e in events if e["type"] == "chunk"]
        full_text = "".join(chunk_texts)
        assert "## Summary" in full_text
        assert "test report" in full_text

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_empty_sources_still_generates(self, mock_search, mock_get_adapter):
        """Report should still be generated even with no search results."""
        mock_search.return_value = []
        mock_get_adapter.return_value = _mock_adapter(["[需補充]"])

        events = await _collect_events(report_stream(topic="Unknown topic"))

        types = [e["type"] for e in events]
        assert "sources" in types
        assert "chunk" in types
        assert "done" in types


# ---------------------------------------------------------------------------
# report_stream() search query tests
# ---------------------------------------------------------------------------

class TestReportStreamSearch:
    """Tests for search behavior in report_stream()."""

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_search_uses_topic(self, mock_search, mock_get_adapter):
        """Search query should be the topic."""
        mock_search.return_value = []
        mock_get_adapter.return_value = _mock_adapter(["X"])

        await _collect_events(report_stream(topic="quantum computing"))

        mock_search.assert_called_once()
        args = mock_search.call_args
        assert args[0][0] == "quantum computing"

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_search_passes_n_results(self, mock_search, mock_get_adapter):
        """n_results should be forwarded to search."""
        mock_search.return_value = []
        mock_get_adapter.return_value = _mock_adapter(["X"])

        await _collect_events(report_stream(topic="Test", n_results=15))

        args = mock_search.call_args
        assert args[0][2] == 15  # n_results is 3rd positional arg

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_search_passes_collections(self, mock_search, mock_get_adapter):
        """Custom collections should be forwarded to search."""
        mock_search.return_value = []
        mock_get_adapter.return_value = _mock_adapter(["X"])

        await _collect_events(
            report_stream(topic="Test", collections=["auto_indexed"])
        )

        args = mock_search.call_args
        assert args[0][1] == ["auto_indexed"]


# ---------------------------------------------------------------------------
# report_stream() LLM prompt tests
# ---------------------------------------------------------------------------

class TestReportStreamPrompt:
    """Tests for LLM prompt construction in report_stream()."""

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_llm_called_with_temperature(self, mock_search, mock_get_adapter):
        """LLM should be called with temperature=0.3."""
        mock_search.return_value = []
        adapter = _mock_adapter(["X"])
        mock_get_adapter.return_value = adapter

        await _collect_events(report_stream(topic="Test"))

        call_kwargs = adapter.generate_text_stream.call_args[1]
        assert call_kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_llm_called_with_max_tokens(self, mock_search, mock_get_adapter):
        """LLM should be called with max_tokens=4096."""
        mock_search.return_value = []
        adapter = _mock_adapter(["X"])
        mock_get_adapter.return_value = adapter

        await _collect_events(report_stream(topic="Test"))

        call_kwargs = adapter.generate_text_stream.call_args[1]
        assert call_kwargs["max_tokens"] == 4096


# ---------------------------------------------------------------------------
# report_stream() error handling tests
# ---------------------------------------------------------------------------

class TestReportStreamErrors:
    """Tests for error handling in report_stream()."""

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_llm_error_emits_error_event(self, mock_search, mock_get_adapter):
        """LLM exception should result in an error SSE event."""
        mock_search.return_value = []

        adapter = MagicMock()
        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("LLM service down")
            yield  # make it an async generator
        adapter.generate_text_stream = MagicMock(side_effect=_failing_stream)
        mock_get_adapter.return_value = adapter

        events = await _collect_events(report_stream(topic="Test"))

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM service down" in error_events[0]["message"]

    @pytest.mark.asyncio
    @patch("app.services.report_generator.get_llm_adapter")
    @patch("app.services.report_generator.search_all_collections", new_callable=AsyncMock)
    async def test_error_event_is_last(self, mock_search, mock_get_adapter):
        """After an error event, no done event should follow."""
        mock_search.return_value = []

        adapter = MagicMock()
        async def _failing_stream(*args, **kwargs):
            raise ValueError("Bad input")
            yield  # make it an async generator
        adapter.generate_text_stream = MagicMock(side_effect=_failing_stream)
        mock_get_adapter.return_value = adapter

        events = await _collect_events(report_stream(topic="Test"))

        types = [e["type"] for e in events]
        assert types[-1] == "error"
        assert "done" not in types


# ---------------------------------------------------------------------------
# ReportRequest schema tests
# ---------------------------------------------------------------------------

class TestReportRequestSchema:
    """Tests for ReportRequest Pydantic model."""

    def test_minimal_request(self):
        """Should only require topic."""
        req = ReportRequest(topic="Test")
        assert req.topic == "Test"
        assert req.report_type == "summary"
        assert req.target_audience == "academic"
        assert req.language == "zh-TW"
        assert req.n_results == 8

    def test_full_request(self):
        """All fields should be settable."""
        req = ReportRequest(
            topic="AI Ethics",
            report_type="detailed",
            target_audience="business",
            sections=["Intro", "Analysis", "Conclusion"],
            language="en",
            collections=["auto_indexed"],
            n_results=15,
        )
        assert req.report_type == "detailed"
        assert req.target_audience == "business"
        assert req.sections == ["Intro", "Analysis", "Conclusion"]
        assert req.language == "en"
        assert req.n_results == 15

    def test_default_sections_is_none(self):
        """Sections should default to None."""
        req = ReportRequest(topic="Test")
        assert req.sections is None

    def test_default_collections_is_none(self):
        """Collections should default to None."""
        req = ReportRequest(topic="Test")
        assert req.collections is None


# ---------------------------------------------------------------------------
# DEFAULT_SECTIONS constant tests
# ---------------------------------------------------------------------------

class TestDefaultSections:
    """Tests for the default section outlines."""

    def test_summary_has_sections(self):
        assert len(DEFAULT_SECTIONS["summary"]) >= 2

    def test_detailed_has_more_sections(self):
        assert len(DEFAULT_SECTIONS["detailed"]) > len(DEFAULT_SECTIONS["summary"])

    def test_executive_has_sections(self):
        assert len(DEFAULT_SECTIONS["executive"]) >= 2

    def test_all_types_exist(self):
        assert set(DEFAULT_SECTIONS.keys()) == {"summary", "detailed", "executive"}
