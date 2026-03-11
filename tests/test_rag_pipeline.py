"""
Tests for rag_pipeline — RAG retrieval + generation + hallucination guard.

All tests mock ``get_llm_adapter()`` and ``search_documents()`` so no
real LLM or ChromaDB calls are made.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_pipeline import _hallucination_check, generate_field_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_result(text: str, distance: float = 0.3) -> dict:
    """Create a mock search_documents() result item."""
    return {
        "doc_id": "doc_1",
        "text": text,
        "metadata": {"source": "test.pdf"},
        "distance": distance,
    }


def _mock_adapter(generate_return: str, second_return: str | None = None):
    """Create a mock LLM adapter with preset generate_text() responses.

    If ``second_return`` is given, the second call returns that value
    (for testing the shortening logic).
    """
    adapter = MagicMock()
    if second_return is not None:
        adapter.generate_text = AsyncMock(side_effect=[generate_return, second_return])
    else:
        adapter.generate_text = AsyncMock(return_value=generate_return)
    return adapter


# ---------------------------------------------------------------------------
# _hallucination_check() unit tests
# ---------------------------------------------------------------------------

class TestHallucinationCheck:
    """Unit tests for the _hallucination_check() helper."""

    def test_empty_chunks_returns_fallback(self):
        """Empty source_chunks → '[需人工補充]'."""
        assert _hallucination_check("some text", []) == "[需人工補充]"

    def test_all_short_chunks_returns_fallback(self):
        """All chunks < 20 chars → '[需人工補充]'."""
        chunks = ["short", "tiny", "abc"]
        assert _hallucination_check("generated answer", chunks) == "[需人工補充]"

    def test_one_long_chunk_passes(self):
        """At least one chunk >= 20 chars → generated text is preserved."""
        chunks = ["short", "This is a long enough chunk to pass the check"]
        result = _hallucination_check("generated answer", chunks)
        assert result == "generated answer"

    def test_all_long_chunks_pass(self):
        """Multiple adequate chunks → generated text preserved."""
        chunks = [
            "A sufficiently long text chunk for testing purposes",
            "Another chunk that is definitely long enough",
        ]
        result = _hallucination_check("my answer", chunks)
        assert result == "my answer"

    def test_exactly_20_chars_passes(self):
        """Chunk with exactly 20 chars should pass (< 20 fails, >= 20 passes)."""
        chunk_20 = "a" * 20  # exactly 20 chars
        result = _hallucination_check("ok", [chunk_20])
        assert result == "ok"

    def test_exactly_19_chars_fails(self):
        """Chunk with 19 chars should fail."""
        chunk_19 = "a" * 19
        result = _hallucination_check("text", [chunk_19])
        assert result == "[需人工補充]"

    def test_whitespace_stripping(self):
        """Chunks with whitespace padding should be stripped before length check."""
        # "   short   " stripped → 5 chars → < 20 → fail
        chunks = ["   short   ", "  tiny  "]
        result = _hallucination_check("answer", chunks)
        assert result == "[需人工補充]"

    def test_one_padded_long_chunk_passes(self):
        """Long chunk with whitespace padding should still pass after stripping."""
        chunks = ["   This is a long enough chunk after stripping   "]
        result = _hallucination_check("answer", chunks)
        assert result == "answer"


# ---------------------------------------------------------------------------
# generate_field_content() — empty/no results
# ---------------------------------------------------------------------------

class TestGenerateFieldContentNoResults:
    """Tests when search_documents returns empty or thin results."""

    @pytest.mark.asyncio
    async def test_no_search_results(self):
        """No documents found → ('[需人工補充]', 0.0)."""
        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=[]):
            text, confidence = await generate_field_content(
                field_name="research_summary",
                search_query="研究概述",
            )

        assert text == "[需人工補充]"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_thin_context_under_50_chars(self):
        """Total context < 50 chars → early return '[需人工補充]'."""
        short_results = [_search_result("tiny")]  # 4 chars

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=short_results):
            text, confidence = await generate_field_content(
                field_name="research_summary",
                search_query="research",
            )

        assert text == "[需人工補充]"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_context_exactly_49_chars(self):
        """Total context exactly 49 chars → should return '[需人工補充]'."""
        results = [_search_result("a" * 49)]

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results):
            text, confidence = await generate_field_content(
                field_name="topic",
                search_query="topic",
            )

        assert text == "[需人工補充]"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_context_exactly_50_chars_passes(self):
        """Total context exactly 50 chars → should proceed to LLM generation."""
        results = [_search_result("a" * 50)]
        adapter = _mock_adapter("Generated content about the topic")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, confidence = await generate_field_content(
                field_name="topic",
                search_query="topic",
            )

        # Should NOT be fallback (50 chars >= 50 threshold)
        # But _hallucination_check may reject if chunks are too short
        # In this case "a"*50 stripped is 50 chars >= 20, so it passes
        assert text == "Generated content about the topic"
        assert confidence > 0.0


# ---------------------------------------------------------------------------
# generate_field_content() — normal generation
# ---------------------------------------------------------------------------

class TestGenerateFieldContentNormal:
    """Tests for successful generation flow."""

    @pytest.mark.asyncio
    async def test_basic_generation(self):
        """Normal flow: search → generate → return."""
        results = [
            _search_result("This is a research paper about machine learning and its applications in NLP."),
        ]
        adapter = _mock_adapter("Machine learning research summary")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, confidence = await generate_field_content(
                field_name="research_summary",
                search_query="machine learning",
            )

        assert text == "Machine learning research summary"
        assert confidence > 0.0

    @pytest.mark.asyncio
    async def test_generation_with_multiple_results(self):
        """Multiple search results should all be included in context."""
        results = [
            _search_result("Paper 1: Deep learning for NLP tasks is gaining traction."),
            _search_result("Paper 2: Transformer architectures revolutionized NLP."),
            _search_result("Paper 3: BERT achieved state-of-the-art on many benchmarks."),
        ]
        adapter = _mock_adapter("NLP research is advancing rapidly")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, confidence = await generate_field_content(
                field_name="research_summary",
                search_query="NLP",
            )

        # Verify the prompt contains all chunks
        prompt = adapter.generate_text.call_args[0][0]
        assert "Paper 1" in prompt
        assert "Paper 2" in prompt
        assert "Paper 3" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_field_name(self):
        """The prompt should include the target field_name."""
        results = [_search_result("A sufficiently long text chunk about research interests.")]
        adapter = _mock_adapter("Generated content")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                field_name="research_interests",
                search_query="research",
            )

        prompt = adapter.generate_text.call_args[0][0]
        assert "research_interests" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_constraints(self):
        """The prompt should include max_length, language, and format_hint."""
        results = [_search_result("A sufficiently long text chunk for context retrieval.")]
        adapter = _mock_adapter("Output")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                field_name="field",
                search_query="query",
                max_length=500,
                language="en",
                format_hint="bullet_points",
            )

        prompt = adapter.generate_text.call_args[0][0]
        assert "500" in prompt
        assert "en" in prompt
        assert "bullet_points" in prompt

    @pytest.mark.asyncio
    async def test_search_called_with_correct_args(self):
        """search_documents should be called with the right parameters."""
        mock_search = AsyncMock(return_value=[
            _search_result("Long enough chunk to pass all checks and validations."),
        ])
        adapter = _mock_adapter("result")

        with patch("app.services.rag_pipeline.search_documents", mock_search), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                field_name="topic",
                search_query="quantum computing",
                collection_name="research_projects",
            )

        mock_search.assert_called_once_with("quantum computing", "research_projects", n_results=5, user_id=None)

    @pytest.mark.asyncio
    async def test_generate_text_called_with_temperature(self):
        """generate_text should be called with temperature=0.3."""
        results = [_search_result("Long enough context for generation to proceed normally.")]
        adapter = _mock_adapter("output")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                field_name="field",
                search_query="query",
            )

        _, kwargs = adapter.generate_text.call_args
        assert kwargs.get("temperature") == 0.3


# ---------------------------------------------------------------------------
# generate_field_content() — length shortening
# ---------------------------------------------------------------------------

class TestGenerateFieldContentShortening:
    """Tests for the length-constraint self-correction step."""

    @pytest.mark.asyncio
    async def test_no_shortening_when_within_limit(self):
        """If generated text <= max_length, no shortening call."""
        results = [_search_result("A long enough chunk of text for context retrieval and processing.")]
        short_text = "Short"  # 5 chars, well within default 1000
        adapter = _mock_adapter(short_text)

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, _ = await generate_field_content(
                field_name="field",
                search_query="query",
                max_length=1000,
            )

        # generate_text should be called only ONCE (no shortening)
        assert adapter.generate_text.call_count == 1
        assert text == "Short"

    @pytest.mark.asyncio
    async def test_shortening_when_exceeds_limit(self):
        """If generated text > max_length, a second call is made to shorten."""
        results = [_search_result("A long enough chunk of text for the context to be sufficient.")]
        long_text = "x" * 200  # exceeds max_length=50
        shortened_text = "Shortened version"
        adapter = _mock_adapter(long_text, second_return=shortened_text)

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, _ = await generate_field_content(
                field_name="field",
                search_query="query",
                max_length=50,
            )

        # generate_text called twice: generation + shortening
        assert adapter.generate_text.call_count == 2
        assert text == "Shortened version"

    @pytest.mark.asyncio
    async def test_shortening_uses_lower_temperature(self):
        """Shortening call should use temperature=0.1."""
        results = [_search_result("Sufficient context text for the retrieval process to work.")]
        adapter = _mock_adapter("x" * 100, second_return="short")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                field_name="field",
                search_query="query",
                max_length=10,
            )

        # Second call should have temperature=0.1
        second_call = adapter.generate_text.call_args_list[1]
        assert second_call.kwargs.get("temperature") == 0.1

    @pytest.mark.asyncio
    async def test_exactly_at_max_length_no_shortening(self):
        """Generated text exactly at max_length → no shortening needed."""
        results = [_search_result("Sufficient context text chunk for processing and analysis.")]
        exact_text = "x" * 50
        adapter = _mock_adapter(exact_text)

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, _ = await generate_field_content(
                field_name="field",
                search_query="query",
                max_length=50,
            )

        # No shortening (50 is NOT > 50)
        assert adapter.generate_text.call_count == 1


# ---------------------------------------------------------------------------
# generate_field_content() — confidence score
# ---------------------------------------------------------------------------

class TestGenerateFieldContentConfidence:
    """Tests for confidence score calculation."""

    @pytest.mark.asyncio
    async def test_confidence_with_1_result(self):
        """1 result → confidence = min(0.9, 0.5 + 0.1*1) = 0.6."""
        results = [_search_result("A long enough document chunk for context in generation.")]
        adapter = _mock_adapter("answer")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            _, confidence = await generate_field_content("f", "q")

        assert confidence == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_confidence_with_3_results(self):
        """3 results → confidence = min(0.9, 0.5 + 0.1*3) = 0.8."""
        results = [
            _search_result("Long enough chunk one for context retrieval."),
            _search_result("Long enough chunk two for context retrieval."),
            _search_result("Long enough chunk three for context retrieval."),
        ]
        adapter = _mock_adapter("answer")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            _, confidence = await generate_field_content("f", "q")

        assert confidence == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_confidence_capped_at_0_9(self):
        """5+ results → confidence capped at 0.9."""
        results = [
            _search_result(f"Long enough document chunk number {i} for testing.")
            for i in range(5)
        ]
        adapter = _mock_adapter("answer")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            _, confidence = await generate_field_content("f", "q")

        # min(0.9, 0.5 + 0.1*5) = min(0.9, 1.0) = 0.9
        assert confidence == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_confidence_zero_for_no_results(self):
        """No results → confidence = 0.0."""
        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=[]):
            _, confidence = await generate_field_content("f", "q")

        assert confidence == 0.0


# ---------------------------------------------------------------------------
# generate_field_content() — hallucination guard integration
# ---------------------------------------------------------------------------

class TestGenerateFieldContentHallucination:
    """Tests for hallucination guard integration in the pipeline."""

    @pytest.mark.asyncio
    async def test_short_chunks_trigger_fallback(self):
        """All source chunks < 20 chars → fallback despite LLM generating text."""
        results = [_search_result("hi")]  # 2 chars
        # total context = 2 chars < 50 → early return before LLM

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results):
            text, confidence = await generate_field_content("f", "q")

        assert text == "[需人工補充]"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_mixed_chunk_lengths_passes(self):
        """At least one long chunk → hallucination guard passes."""
        results = [
            _search_result("tiny"),  # 4 chars
            _search_result("This is a sufficiently long text chunk that should pass the hallucination guard."),
        ]
        adapter = _mock_adapter("LLM generated text based on context")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, _ = await generate_field_content("field", "query")

        assert text == "LLM generated text based on context"


# ---------------------------------------------------------------------------
# generate_field_content() — error handling
# ---------------------------------------------------------------------------

class TestGenerateFieldContentErrors:
    """Tests for error propagation."""

    @pytest.mark.asyncio
    async def test_search_error_propagates(self):
        """If search_documents raises, it should propagate."""
        with patch(
            "app.services.rag_pipeline.search_documents",
            new_callable=AsyncMock,
            side_effect=RuntimeError("ChromaDB unavailable"),
        ):
            with pytest.raises(RuntimeError, match="ChromaDB unavailable"):
                await generate_field_content("f", "q")

    @pytest.mark.asyncio
    async def test_llm_error_falls_back_to_placeholder(self):
        """If LLM adapter raises, should return [需人工補充] fallback."""
        results = [_search_result("Long enough text for context processing in the pipeline.")]
        adapter = MagicMock()
        adapter.generate_text = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            text, confidence = await generate_field_content("f", "q")

        assert text == "[需人工補充]"
        assert confidence == 0.0


# ---------------------------------------------------------------------------
# generate_field_content() — parameter forwarding
# ---------------------------------------------------------------------------

class TestGenerateFieldContentParameters:
    """Tests for custom parameter values."""

    @pytest.mark.asyncio
    async def test_custom_collection_name(self):
        """collection_name should be forwarded to search_documents."""
        mock_search = AsyncMock(return_value=[
            _search_result("A long enough text chunk for context retrieval and processing."),
        ])
        adapter = _mock_adapter("result")

        with patch("app.services.rag_pipeline.search_documents", mock_search), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content(
                "field", "query", collection_name="auto_indexed"
            )

        mock_search.assert_called_once_with("query", "auto_indexed", n_results=5, user_id=None)

    @pytest.mark.asyncio
    async def test_default_collection_name(self):
        """Default collection should be 'academic_papers'."""
        mock_search = AsyncMock(return_value=[
            _search_result("A long enough text chunk for the default collection test."),
        ])
        adapter = _mock_adapter("result")

        with patch("app.services.rag_pipeline.search_documents", mock_search), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content("field", "query")

        mock_search.assert_called_once_with("query", "academic_papers", n_results=5, user_id=None)

    @pytest.mark.asyncio
    async def test_custom_language_in_prompt(self):
        """Custom language should appear in the LLM prompt."""
        results = [_search_result("A sufficiently long chunk of context text for prompting.")]
        adapter = _mock_adapter("result")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content("f", "q", language="en")

        prompt = adapter.generate_text.call_args[0][0]
        assert "en" in prompt

    @pytest.mark.asyncio
    async def test_custom_format_hint_in_prompt(self):
        """Custom format_hint should appear in the LLM prompt."""
        results = [_search_result("A sufficiently long chunk of context text for prompting.")]
        adapter = _mock_adapter("result")

        with patch("app.services.rag_pipeline.search_documents", new_callable=AsyncMock, return_value=results), \
             patch("app.services.rag_pipeline.get_llm_adapter", return_value=adapter):
            await generate_field_content("f", "q", format_hint="numbered_list")

        prompt = adapter.generate_text.call_args[0][0]
        assert "numbered_list" in prompt
