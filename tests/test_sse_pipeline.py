"""
Tests for sse_pipeline — shared SSE streaming infrastructure.

Covers:
- _sse() formatting
- search_all_collections() multi-collection search
- format_context_default() / format_context_report() context formatters
- StreamConfig dataclass
- rag_sse_stream() end-to-end pipeline
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import SourceChunk
from app.services.sse_pipeline import (
    _sse,
    format_context_default,
    format_context_report,
    rag_sse_stream,
    search_all_collections,
    StreamConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(
    text: str,
    collection: str = "academic_papers",
    distance: float = 0.3,
    title: str = "Test Paper",
) -> SourceChunk:
    """Create a mock SourceChunk."""
    return SourceChunk(
        text=text,
        metadata={"title": title, "source": "test.pdf"},
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
        line = raw.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# _sse() tests
# ---------------------------------------------------------------------------

class TestSse:
    """Tests for the SSE event formatter."""

    def test_basic_formatting(self):
        """Should produce 'data: {json}\n\n' format."""
        result = _sse({"type": "done"})
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        parsed = json.loads(result[6:].strip())
        assert parsed == {"type": "done"}

    def test_unicode_content(self):
        """Should handle unicode (CJK) characters without escaping."""
        result = _sse({"type": "chunk", "content": "你好世界"})
        assert "你好世界" in result
        parsed = json.loads(result[6:].strip())
        assert parsed["content"] == "你好世界"

    def test_complex_payload(self):
        """Should handle nested dicts and lists."""
        payload = {
            "type": "sources",
            "sources": [
                {"text": "abc", "collection": "c1"},
                {"text": "def", "collection": "c2"},
            ],
        }
        result = _sse(payload)
        parsed = json.loads(result[6:].strip())
        assert len(parsed["sources"]) == 2


# ---------------------------------------------------------------------------
# search_all_collections() tests
# ---------------------------------------------------------------------------

class TestSearchAllCollections:
    """Tests for multi-collection parallel search."""

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.search_documents", new_callable=AsyncMock)
    @patch("app.services.sse_pipeline.COLLECTIONS", ["col_a", "col_b"])
    async def test_searches_all_default_collections(self, mock_search):
        """Should search all default collections when none specified."""
        mock_search.return_value = []
        await search_all_collections("test query")
        assert mock_search.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.search_documents", new_callable=AsyncMock)
    async def test_searches_specified_collections(self, mock_search):
        """Should only search specified collections."""
        mock_search.return_value = []
        await search_all_collections("test", collections=["custom_col"])
        mock_search.assert_called_once_with("test", "custom_col", n_results=5, user_id=None)

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.search_documents", new_callable=AsyncMock)
    async def test_results_sorted_by_distance(self, mock_search):
        """Results should be sorted by ascending distance."""
        mock_search.side_effect = [
            [{"text": "far", "distance": 0.9, "metadata": {}}],
            [{"text": "close", "distance": 0.1, "metadata": {}}],
        ]
        results = await search_all_collections(
            "test", collections=["a", "b"], n_results=10
        )
        assert results[0].text == "close"
        assert results[1].text == "far"

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.search_documents", new_callable=AsyncMock)
    async def test_results_limited_to_n_results(self, mock_search):
        """Should return at most n_results items."""
        mock_search.return_value = [
            {"text": f"doc{i}", "distance": 0.1 * i, "metadata": {}}
            for i in range(5)
        ]
        results = await search_all_collections(
            "test", collections=["col"], n_results=3
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.search_documents", new_callable=AsyncMock)
    async def test_handles_collection_errors_gracefully(self, mock_search):
        """Failed collections should be skipped, not crash the whole search."""
        mock_search.side_effect = [
            RuntimeError("DB error"),  # col_a fails
            [{"text": "ok", "distance": 0.2, "metadata": {}}],  # col_b succeeds
        ]
        results = await search_all_collections(
            "test", collections=["col_a", "col_b"]
        )
        assert len(results) == 1
        assert results[0].text == "ok"


# ---------------------------------------------------------------------------
# format_context_default() tests
# ---------------------------------------------------------------------------

class TestFormatContextDefault:
    """Tests for the default context formatter (used by chat/email)."""

    def test_empty_returns_placeholder(self):
        """Empty list should return default empty message."""
        result = format_context_default([])
        assert result == "(No relevant documents found)"

    def test_custom_empty_message(self):
        """Custom empty message should be used."""
        result = format_context_default([], empty_message="No data")
        assert result == "No data"

    def test_single_source_formatting(self):
        """Single source should have [Source 1] header and text."""
        src = _source("Research findings on NLP.")
        result = format_context_default([src])
        assert "[Source 1]" in result
        assert "academic_papers" in result
        assert "Research findings on NLP." in result

    def test_multiple_sources_numbered(self):
        """Multiple sources should be numbered sequentially."""
        sources = [
            _source("First doc", collection="c1"),
            _source("Second doc", collection="c2"),
        ]
        result = format_context_default(sources)
        assert "[Source 1]" in result
        assert "[Source 2]" in result
        assert "c1" in result
        assert "c2" in result

    def test_metadata_included(self):
        """Metadata key-value pairs should appear in header."""
        src = _source("Text", title="My Paper")
        result = format_context_default([src])
        assert "title: My Paper" in result


# ---------------------------------------------------------------------------
# format_context_report() tests
# ---------------------------------------------------------------------------

class TestFormatContextReport:
    """Tests for the report-style context formatter."""

    def test_empty_returns_placeholder(self):
        """Empty list should return report-specific empty message."""
        result = format_context_report([])
        assert "No context documents found" in result
        assert "需補充" in result

    def test_single_source_formatting(self):
        """Single source should use report format: [Source i | collection | title]."""
        src = _source("Report data", collection="papers", title="AI Study")
        result = format_context_report([src])
        assert "[Source 1 | papers | AI Study]" in result
        assert "Report data" in result

    def test_multiple_sources(self):
        """Multiple sources should be numbered and separated."""
        sources = [
            _source("First", collection="c1", title="Paper A"),
            _source("Second", collection="c2", title="Paper B"),
        ]
        result = format_context_report(sources)
        assert "[Source 1 | c1 | Paper A]" in result
        assert "[Source 2 | c2 | Paper B]" in result


# ---------------------------------------------------------------------------
# StreamConfig tests
# ---------------------------------------------------------------------------

class TestStreamConfig:
    """Tests for the StreamConfig dataclass."""

    def test_defaults(self):
        """Default values should be temperature=0.3, max_tokens=2048."""
        config = StreamConfig()
        assert config.temperature == 0.3
        assert config.max_tokens == 2048

    def test_custom_values(self):
        """Custom values should override defaults."""
        config = StreamConfig(temperature=0.7, max_tokens=4096)
        assert config.temperature == 0.7
        assert config.max_tokens == 4096


# ---------------------------------------------------------------------------
# rag_sse_stream() end-to-end tests
# ---------------------------------------------------------------------------

class TestRagSseStream:
    """Tests for the shared RAG → SSE streaming pipeline."""

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_event_sequence_sources_chunks_done(self, mock_search, mock_adapter):
        """Normal flow should emit: sources → chunk(s) → done."""
        mock_search.return_value = [_source("Context")]
        mock_adapter.return_value = _mock_adapter(["Hello ", "World"])

        events = await _collect_events(
            rag_sse_stream(
                search_query="test",
                build_prompt=lambda sources: "prompt",
            )
        )

        types = [e["type"] for e in events]
        assert types[0] == "sources"
        assert types[-1] == "done"
        assert types.count("chunk") == 2

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_build_prompt_called_with_sources(self, mock_search, mock_adapter):
        """build_prompt callback should receive the search results."""
        mock_sources = [_source("Source text")]
        mock_search.return_value = mock_sources
        mock_adapter.return_value = _mock_adapter(["X"])

        received_sources = []

        def capture_prompt(sources):
            received_sources.extend(sources)
            return "test prompt"

        await _collect_events(
            rag_sse_stream(search_query="q", build_prompt=capture_prompt)
        )

        assert len(received_sources) == 1
        assert received_sources[0].text == "Source text"

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_config_forwarded_to_llm(self, mock_search, mock_adapter):
        """StreamConfig should be forwarded to generate_text_stream."""
        mock_search.return_value = []
        adapter = _mock_adapter(["X"])
        mock_adapter.return_value = adapter

        config = StreamConfig(temperature=0.9, max_tokens=1024)
        await _collect_events(
            rag_sse_stream(
                search_query="q",
                build_prompt=lambda s: "p",
                config=config,
            )
        )

        call_kwargs = adapter.generate_text_stream.call_args[1]
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 1024

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_llm_error_emits_error_event(self, mock_search, mock_adapter):
        """LLM exception should yield an error event instead of crashing."""
        mock_search.return_value = []

        adapter = MagicMock()

        async def _failing(*args, **kwargs):
            raise RuntimeError("LLM crashed")
            yield  # make it an async generator

        adapter.generate_text_stream = MagicMock(side_effect=_failing)
        mock_adapter.return_value = adapter

        events = await _collect_events(
            rag_sse_stream(search_query="q", build_prompt=lambda s: "p")
        )

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert "LLM crashed" in error_events[0]["message"]
        # No done event after error
        types = [e["type"] for e in events]
        assert types[-1] == "error"

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_search_params_forwarded(self, mock_search, mock_adapter):
        """collections and n_results should be forwarded to search."""
        mock_search.return_value = []
        mock_adapter.return_value = _mock_adapter(["X"])

        await _collect_events(
            rag_sse_stream(
                search_query="my query",
                build_prompt=lambda s: "p",
                collections=["special"],
                n_results=12,
            )
        )

        mock_search.assert_called_once_with("my query", ["special"], 12, user_id=None)

    @pytest.mark.asyncio
    @patch("app.services.sse_pipeline.get_llm_adapter")
    @patch("app.services.sse_pipeline.search_all_collections", new_callable=AsyncMock)
    async def test_empty_sources_still_streams(self, mock_search, mock_adapter):
        """Even with no search results, should emit sources + chunks + done."""
        mock_search.return_value = []
        mock_adapter.return_value = _mock_adapter(["Generated anyway."])

        events = await _collect_events(
            rag_sse_stream(search_query="q", build_prompt=lambda s: "p")
        )

        types = [e["type"] for e in events]
        assert "sources" in types
        assert "chunk" in types
        assert "done" in types
        # Sources event should have empty list
        assert events[0]["sources"] == []
