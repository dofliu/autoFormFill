"""
Tests for intent_router — LLM-based field classification with mocked LLM.

All tests mock ``get_llm_adapter()`` so no real LLM calls are made.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.form import FieldRoutingResult, FormField
from app.services.intent_router import route_fields


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _field(name: str, ftype: str = "template_var") -> FormField:
    """Shortcut to create a FormField."""
    return FormField(field_name=name, field_type=ftype)


def _mock_adapter(json_return: list | dict):
    """Create a mock LLM adapter with a preset generate_json() response."""
    adapter = MagicMock()
    adapter.generate_json = AsyncMock(return_value=json_return)
    return adapter


# ---------------------------------------------------------------------------
# Basic routing tests
# ---------------------------------------------------------------------------

class TestRouteFieldsBasic:
    """Core happy-path tests for route_fields()."""

    @pytest.mark.asyncio
    async def test_empty_fields_returns_empty(self):
        """Empty input list should return empty list without calling LLM."""
        result = await route_fields([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_sql_field(self):
        """LLM classifies a name field as SQL_DB."""
        mock_llm_response = [
            {
                "field_name": "applicant_name",
                "data_source": "SQL_DB",
                "sql_target": "user_profiles.name_zh",
                "search_query": None,
                "confidence": 0.95,
            }
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("applicant_name")])

        assert len(result) == 1
        assert result[0].field_name == "applicant_name"
        assert result[0].data_source == "SQL_DB"
        assert result[0].sql_target == "user_profiles.name_zh"
        assert result[0].search_query is None
        assert result[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_single_vector_field(self):
        """LLM classifies a research field as VECTOR_DB."""
        mock_llm_response = [
            {
                "field_name": "research_summary",
                "data_source": "VECTOR_DB",
                "sql_target": None,
                "search_query": "research summary and publications",
                "confidence": 0.85,
            }
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("research_summary")])

        assert len(result) == 1
        assert result[0].data_source == "VECTOR_DB"
        assert result[0].search_query == "research summary and publications"
        assert result[0].sql_target is None

    @pytest.mark.asyncio
    async def test_single_skip_field(self):
        """LLM classifies a signature field as SKIP."""
        mock_llm_response = [
            {
                "field_name": "signature",
                "data_source": "SKIP",
                "sql_target": None,
                "search_query": None,
                "confidence": 0.99,
            }
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("signature")])

        assert len(result) == 1
        assert result[0].data_source == "SKIP"

    @pytest.mark.asyncio
    async def test_multiple_fields_mixed_sources(self):
        """Multiple fields classified into different data sources."""
        mock_llm_response = [
            {
                "field_name": "name",
                "data_source": "SQL_DB",
                "sql_target": "user_profiles.name_zh",
                "search_query": None,
                "confidence": 0.95,
            },
            {
                "field_name": "research_topic",
                "data_source": "VECTOR_DB",
                "sql_target": None,
                "search_query": "主要研究方向",
                "confidence": 0.8,
            },
            {
                "field_name": "stamp",
                "data_source": "SKIP",
                "sql_target": None,
                "search_query": None,
                "confidence": 0.99,
            },
        ]

        fields = [_field("name"), _field("research_topic"), _field("stamp")]
        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields(fields)

        assert len(result) == 3
        sources = {r.field_name: r.data_source for r in result}
        assert sources == {
            "name": "SQL_DB",
            "research_topic": "VECTOR_DB",
            "stamp": "SKIP",
        }


# ---------------------------------------------------------------------------
# Default value / missing key tests
# ---------------------------------------------------------------------------

class TestRouteFieldsDefaults:
    """Test that missing keys from LLM response get proper defaults."""

    @pytest.mark.asyncio
    async def test_missing_field_name_defaults_to_empty(self):
        """If LLM omits field_name, default to empty string."""
        mock_llm_response = [
            {"data_source": "SQL_DB", "confidence": 0.7}
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("name")])

        assert result[0].field_name == ""

    @pytest.mark.asyncio
    async def test_missing_data_source_defaults_to_skip(self):
        """If LLM omits data_source, default to 'SKIP'."""
        mock_llm_response = [
            {"field_name": "unknown_field"}
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("unknown_field")])

        assert result[0].data_source == "SKIP"

    @pytest.mark.asyncio
    async def test_missing_confidence_defaults_to_0_5(self):
        """If LLM omits confidence, default to 0.5."""
        mock_llm_response = [
            {"field_name": "email", "data_source": "SQL_DB"}
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("email")])

        assert result[0].confidence == 0.5

    @pytest.mark.asyncio
    async def test_missing_sql_target_defaults_to_none(self):
        """sql_target should be None when not provided."""
        mock_llm_response = [
            {"field_name": "name", "data_source": "SQL_DB", "confidence": 0.9}
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("name")])

        assert result[0].sql_target is None

    @pytest.mark.asyncio
    async def test_missing_search_query_defaults_to_none(self):
        """search_query should be None when not provided."""
        mock_llm_response = [
            {"field_name": "topic", "data_source": "VECTOR_DB", "confidence": 0.8}
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("topic")])

        assert result[0].search_query is None


# ---------------------------------------------------------------------------
# Return type validation
# ---------------------------------------------------------------------------

class TestRouteFieldsReturnTypes:
    """Ensure correct return types and schema conformance."""

    @pytest.mark.asyncio
    async def test_returns_list_of_field_routing_result(self):
        """All items should be FieldRoutingResult instances."""
        mock_llm_response = [
            {"field_name": "a", "data_source": "SKIP", "confidence": 0.5},
            {"field_name": "b", "data_source": "SQL_DB", "confidence": 0.9},
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("a"), _field("b")])

        assert all(isinstance(r, FieldRoutingResult) for r in result)

    @pytest.mark.asyncio
    async def test_result_count_matches_llm_response(self):
        """Number of results should match LLM response length."""
        mock_llm_response = [
            {"field_name": f"field_{i}", "data_source": "SKIP"}
            for i in range(5)
        ]

        fields = [_field(f"field_{i}") for i in range(5)]
        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields(fields)

        assert len(result) == 5


# ---------------------------------------------------------------------------
# LLM interaction tests
# ---------------------------------------------------------------------------

class TestRouteFieldsLLMInteraction:
    """Test how route_fields interacts with the LLM adapter."""

    @pytest.mark.asyncio
    async def test_prompt_contains_field_info(self):
        """The prompt sent to LLM should contain serialized field data."""
        adapter = _mock_adapter([{"field_name": "name", "data_source": "SQL_DB"}])

        with patch("app.services.intent_router.get_llm_adapter", return_value=adapter):
            await route_fields([_field("applicant_name")])

        # Verify generate_json was called
        adapter.generate_json.assert_called_once()
        prompt = adapter.generate_json.call_args[0][0]

        # Prompt should contain the field name
        assert "applicant_name" in prompt
        assert "template_var" in prompt  # field_type

    @pytest.mark.asyncio
    async def test_llm_not_called_for_empty_fields(self):
        """Empty fields list should short-circuit without calling LLM."""
        adapter = _mock_adapter([])

        with patch("app.services.intent_router.get_llm_adapter", return_value=adapter):
            result = await route_fields([])

        # generate_json should NOT be called
        adapter.generate_json.assert_not_called()
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_fields_serialized_in_prompt(self):
        """All input fields should appear in the serialized JSON prompt."""
        adapter = _mock_adapter([
            {"field_name": "name", "data_source": "SQL_DB"},
            {"field_name": "email", "data_source": "SQL_DB"},
            {"field_name": "topic", "data_source": "VECTOR_DB"},
        ])

        fields = [_field("name"), _field("email"), _field("topic")]
        with patch("app.services.intent_router.get_llm_adapter", return_value=adapter):
            await route_fields(fields)

        prompt = adapter.generate_json.call_args[0][0]
        assert "name" in prompt
        assert "email" in prompt
        assert "topic" in prompt

    @pytest.mark.asyncio
    async def test_pdf_widget_field_type_in_prompt(self):
        """PDF widget field_type should be serialized correctly."""
        adapter = _mock_adapter([{"field_name": "widget1", "data_source": "SKIP"}])

        with patch("app.services.intent_router.get_llm_adapter", return_value=adapter):
            await route_fields([_field("widget1", ftype="pdf_widget")])

        prompt = adapter.generate_json.call_args[0][0]
        assert "pdf_widget" in prompt


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestRouteFieldsEdgeCases:
    """Edge case handling for route_fields()."""

    @pytest.mark.asyncio
    async def test_llm_returns_extra_fields(self):
        """LLM returns more items than input — all should be processed."""
        mock_llm_response = [
            {"field_name": "a", "data_source": "SQL_DB"},
            {"field_name": "b", "data_source": "SKIP"},
            {"field_name": "c", "data_source": "VECTOR_DB"},
        ]

        # Only one input field, but LLM returns 3
        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("a")])

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_confidence_boundary_values(self):
        """Confidence at boundaries (0.0 and 1.0) should be accepted."""
        mock_llm_response = [
            {"field_name": "sure", "data_source": "SQL_DB", "confidence": 1.0},
            {"field_name": "unsure", "data_source": "SKIP", "confidence": 0.0},
        ]

        with patch("app.services.intent_router.get_llm_adapter", return_value=_mock_adapter(mock_llm_response)):
            result = await route_fields([_field("sure"), _field("unsure")])

        assert result[0].confidence == 1.0
        assert result[1].confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self):
        """If LLM adapter raises, the error should propagate."""
        adapter = MagicMock()
        adapter.generate_json = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with patch("app.services.intent_router.get_llm_adapter", return_value=adapter):
            with pytest.raises(RuntimeError, match="LLM timeout"):
                await route_fields([_field("name")])
