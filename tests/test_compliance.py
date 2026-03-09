"""Tests for Phase 5.2 — Compliance Checking (Rule Engine + field validation).

Tests cover:
  - ComplianceRule ORM model
  - Compliance schemas
  - Compliance service CRUD + validation engine
  - Router integration (validation, ownership)
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.compliance import (
    ComplianceCheckResult,
    ComplianceRuleCreate,
    ComplianceRuleResponse,
    ComplianceRuleUpdate,
    ComplianceViolation,
)
from app.schemas.form import FieldFillResult
from app.services.compliance_service import (
    VALID_RULE_TYPES,
    _check_single_rule,
    _field_matches_pattern,
    check_compliance,
)


# ---- Helpers ----

def _make_rule_mock(
    rule_type: str = "required",
    rule_value: str = "",
    field_pattern: str = "*",
    severity: str = "warning",
    rule_name: str = "test_rule",
    message: str = "",
    is_active: int = 1,
):
    """Create a mock ComplianceRule object."""
    rule = MagicMock()
    rule.id = 1
    rule.user_id = 1
    rule.rule_name = rule_name
    rule.field_pattern = field_pattern
    rule.rule_type = rule_type
    rule.rule_value = rule_value
    rule.severity = severity
    rule.message = message
    rule.is_active = is_active
    rule.created_at = datetime(2026, 3, 10)
    rule.updated_at = datetime(2026, 3, 10)
    rule.to_dict = MagicMock(return_value={
        "id": rule.id, "user_id": rule.user_id, "rule_name": rule.rule_name,
        "field_pattern": rule.field_pattern, "rule_type": rule.rule_type,
        "rule_value": rule.rule_value, "severity": rule.severity,
        "message": rule.message, "is_active": bool(rule.is_active),
        "created_at": "2026-03-10T00:00:00", "updated_at": "2026-03-10T00:00:00",
    })
    return rule


def _make_field(name: str, value: str, source: str = "sql") -> FieldFillResult:
    return FieldFillResult(field_name=name, value=value, source=source, confidence=0.9)


# ---- TestComplianceRuleModel ----

class TestComplianceRuleModel:
    def test_model_import(self):
        from app.models.compliance_rule import ComplianceRule
        assert ComplianceRule.__tablename__ == "compliance_rules"

    def test_to_dict(self):
        from app.models.compliance_rule import ComplianceRule
        rule = ComplianceRule(
            id=1, user_id=1, rule_name="required_field",
            field_pattern="*", rule_type="required",
            rule_value="", severity="error", message="必填",
            is_active=1,
        )
        rule.created_at = datetime(2026, 3, 10)
        rule.updated_at = datetime(2026, 3, 10)
        d = rule.to_dict()
        assert d["rule_name"] == "required_field"
        assert d["rule_type"] == "required"
        assert d["is_active"] is True


# ---- TestComplianceSchemas ----

class TestComplianceSchemas:
    def test_rule_create(self):
        data = ComplianceRuleCreate(
            rule_name="max_200", rule_type="max_length",
            rule_value="200", severity="warning",
        )
        assert data.rule_type == "max_length"
        assert data.field_pattern == "*"

    def test_rule_update(self):
        data = ComplianceRuleUpdate(rule_name="updated_name", is_active=False)
        assert data.rule_name == "updated_name"
        assert data.is_active is False
        assert data.rule_type is None

    def test_rule_response(self):
        resp = ComplianceRuleResponse(
            id=1, user_id=1, rule_name="test", field_pattern="*",
            rule_type="required", rule_value="", severity="error",
            message="test", is_active=True,
            created_at="2026-03-10T00:00:00", updated_at="2026-03-10T00:00:00",
        )
        assert resp.is_active is True

    def test_violation(self):
        v = ComplianceViolation(
            field_name="name", rule_name="required",
            rule_type="required", severity="error",
            message="必填",
        )
        assert v.severity == "error"

    def test_check_result_passed(self):
        r = ComplianceCheckResult(violations=[], passed=True)
        assert r.total_errors == 0
        assert r.passed is True

    def test_check_result_failed(self):
        v = ComplianceViolation(
            field_name="x", rule_name="r", rule_type="required",
            severity="error", message="fail",
        )
        r = ComplianceCheckResult(
            violations=[v], total_errors=1, passed=False,
        )
        assert r.passed is False


# ---- TestFieldMatchesPattern ----

class TestFieldMatchesPattern:
    def test_wildcard(self):
        assert _field_matches_pattern("any_field", "*") is True

    def test_exact_match(self):
        assert _field_matches_pattern("name_zh", "name_zh") is True

    def test_no_match(self):
        assert _field_matches_pattern("name_zh", "email") is False

    def test_glob_pattern(self):
        assert _field_matches_pattern("日期_start", "日期*") is True
        assert _field_matches_pattern("name_zh", "日期*") is False


# ---- TestCheckSingleRule ----

class TestCheckSingleRule:
    def test_required_empty(self):
        rule = _make_rule_mock(rule_type="required")
        v = _check_single_rule("name", "", rule)
        assert v is not None
        assert v.rule_type == "required"

    def test_required_placeholder(self):
        rule = _make_rule_mock(rule_type="required")
        v = _check_single_rule("name", "[需人工補充]", rule)
        assert v is not None

    def test_required_filled(self):
        rule = _make_rule_mock(rule_type="required")
        v = _check_single_rule("name", "王大明", rule)
        assert v is None

    def test_min_length_fail(self):
        rule = _make_rule_mock(rule_type="min_length", rule_value="5")
        v = _check_single_rule("bio", "hi", rule)
        assert v is not None
        assert v.rule_type == "min_length"

    def test_min_length_pass(self):
        rule = _make_rule_mock(rule_type="min_length", rule_value="3")
        v = _check_single_rule("bio", "hello world", rule)
        assert v is None

    def test_max_length_fail(self):
        rule = _make_rule_mock(rule_type="max_length", rule_value="5")
        v = _check_single_rule("bio", "hello world", rule)
        assert v is not None

    def test_max_length_pass(self):
        rule = _make_rule_mock(rule_type="max_length", rule_value="100")
        v = _check_single_rule("bio", "short text", rule)
        assert v is None

    def test_regex_fail(self):
        rule = _make_rule_mock(rule_type="regex", rule_value=r"\d{4}/\d{2}/\d{2}")
        v = _check_single_rule("date", "March 10", rule)
        assert v is not None

    def test_regex_pass(self):
        rule = _make_rule_mock(rule_type="regex", rule_value=r"\d{4}/\d{2}/\d{2}")
        v = _check_single_rule("date", "2026/03/10", rule)
        assert v is None

    def test_regex_invalid_pattern(self):
        rule = _make_rule_mock(rule_type="regex", rule_value="[invalid")
        v = _check_single_rule("date", "any", rule)
        assert v is None  # Invalid regex silently skipped

    def test_contains_fail(self):
        rule = _make_rule_mock(rule_type="contains", rule_value="教授")
        v = _check_single_rule("title", "學生", rule)
        assert v is not None

    def test_contains_pass(self):
        rule = _make_rule_mock(rule_type="contains", rule_value="教授")
        v = _check_single_rule("title", "王教授", rule)
        assert v is None

    def test_min_length_invalid_value(self):
        rule = _make_rule_mock(rule_type="min_length", rule_value="abc")
        v = _check_single_rule("bio", "hi", rule)
        assert v is None  # Invalid rule_value silently skipped


# ---- TestCheckCompliance ----

class TestCheckCompliance:
    def test_no_rules(self):
        fields = [_make_field("name", "value")]
        result = check_compliance(fields, [])
        assert result.passed is True
        assert result.violations == []

    def test_all_pass(self):
        rules = [_make_rule_mock(rule_type="required")]
        fields = [_make_field("name", "王大明")]
        result = check_compliance(fields, rules)
        assert result.passed is True

    def test_multiple_violations(self):
        rules = [
            _make_rule_mock(rule_type="required", severity="error"),
            _make_rule_mock(rule_type="min_length", rule_value="10", severity="warning"),
        ]
        fields = [_make_field("name", "")]
        result = check_compliance(fields, rules)
        assert result.passed is False
        assert result.total_errors == 1
        assert result.total_warnings == 1
        assert len(result.violations) == 2

    def test_inactive_rules_ignored(self):
        rules = [_make_rule_mock(rule_type="required", is_active=0)]
        fields = [_make_field("name", "")]
        result = check_compliance(fields, rules)
        assert result.passed is True
        assert result.violations == []

    def test_pattern_filter(self):
        rules = [_make_rule_mock(rule_type="required", field_pattern="email")]
        fields = [
            _make_field("name", ""),
            _make_field("email", ""),
        ]
        result = check_compliance(fields, rules)
        # Only email should trigger
        assert len(result.violations) == 1
        assert result.violations[0].field_name == "email"

    def test_custom_message(self):
        rules = [_make_rule_mock(rule_type="required", message="請填寫此欄位")]
        fields = [_make_field("name", "")]
        result = check_compliance(fields, rules)
        assert result.violations[0].message == "請填寫此欄位"


# ---- TestRouterIntegration ----

class TestComplianceRouterIntegration:
    def test_valid_rule_types(self):
        assert "required" in VALID_RULE_TYPES
        assert "min_length" in VALID_RULE_TYPES
        assert "max_length" in VALID_RULE_TYPES
        assert "regex" in VALID_RULE_TYPES
        assert "contains" in VALID_RULE_TYPES
        assert "unknown" not in VALID_RULE_TYPES

    @pytest.mark.asyncio
    async def test_check_form_compliance(self):
        from app.services.compliance_service import check_form_compliance
        mock_db = AsyncMock()

        rules = [_make_rule_mock(rule_type="required", severity="error")]

        with patch("app.services.compliance_service.list_rules", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = rules
            fields = [_make_field("name", "")]
            result = await check_form_compliance(mock_db, 1, fields)
            assert result.passed is False
            assert result.total_errors == 1
