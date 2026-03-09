"""Compliance service — rule CRUD + field validation engine.

The rule engine validates filled form fields against user-defined rules:
  - required: field must not be empty or '[需人工補充]'
  - min_length: field value must be at least N characters
  - max_length: field value must be at most N characters
  - regex: field value must match the pattern
  - contains: field value must contain a keyword
"""
import fnmatch
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_rule import ComplianceRule
from app.schemas.compliance import (
    ComplianceCheckResult,
    ComplianceRuleCreate,
    ComplianceRuleUpdate,
    ComplianceViolation,
)
from app.schemas.form import FieldFillResult

logger = logging.getLogger(__name__)

VALID_RULE_TYPES = {"required", "min_length", "max_length", "regex", "contains"}
VALID_SEVERITIES = {"error", "warning", "info"}


# ---- CRUD ----

async def create_rule(
    db: AsyncSession, user_id: int, data: ComplianceRuleCreate
) -> ComplianceRule:
    """Create a new compliance rule."""
    rule = ComplianceRule(
        user_id=user_id,
        rule_name=data.rule_name,
        field_pattern=data.field_pattern,
        rule_type=data.rule_type,
        rule_value=data.rule_value,
        severity=data.severity if data.severity in VALID_SEVERITIES else "warning",
        message=data.message,
        is_active=1,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def get_rule(db: AsyncSession, rule_id: int) -> ComplianceRule | None:
    """Get a single compliance rule by ID."""
    result = await db.execute(
        select(ComplianceRule).where(ComplianceRule.id == rule_id)
    )
    return result.scalar_one_or_none()


async def list_rules(
    db: AsyncSession, user_id: int, active_only: bool = False
) -> list[ComplianceRule]:
    """List all compliance rules for a user."""
    query = select(ComplianceRule).where(ComplianceRule.user_id == user_id)
    if active_only:
        query = query.where(ComplianceRule.is_active == 1)
    query = query.order_by(ComplianceRule.id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_rule(
    db: AsyncSession, rule_id: int, data: ComplianceRuleUpdate
) -> ComplianceRule | None:
    """Update an existing compliance rule."""
    rule = await get_rule(db, rule_id)
    if not rule:
        return None
    if data.rule_name is not None:
        rule.rule_name = data.rule_name
    if data.field_pattern is not None:
        rule.field_pattern = data.field_pattern
    if data.rule_type is not None:
        rule.rule_type = data.rule_type
    if data.rule_value is not None:
        rule.rule_value = data.rule_value
    if data.severity is not None and data.severity in VALID_SEVERITIES:
        rule.severity = data.severity
    if data.message is not None:
        rule.message = data.message
    if data.is_active is not None:
        rule.is_active = 1 if data.is_active else 0
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(db: AsyncSession, rule_id: int) -> bool:
    """Delete a compliance rule."""
    rule = await get_rule(db, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    await db.commit()
    return True


# ---- Validation Engine ----

def _field_matches_pattern(field_name: str, pattern: str) -> bool:
    """Check if a field name matches a rule pattern.

    Supports:
      - "*" matches all fields
      - Exact match
      - fnmatch-style glob (e.g., "日期*", "name_*")
    """
    if pattern == "*":
        return True
    if field_name == pattern:
        return True
    return fnmatch.fnmatch(field_name, pattern)


def _check_single_rule(
    field_name: str, value: str, rule: ComplianceRule
) -> ComplianceViolation | None:
    """Apply one rule to one field. Returns a violation or None."""
    rule_type = rule.rule_type
    rule_value = rule.rule_value

    if rule_type == "required":
        if not value.strip() or value.strip() == "[需人工補充]":
            return ComplianceViolation(
                field_name=field_name,
                rule_name=rule.rule_name,
                rule_type=rule_type,
                severity=rule.severity,
                message=rule.message or f"欄位「{field_name}」為必填",
            )

    elif rule_type == "min_length":
        try:
            min_len = int(rule_value)
        except (ValueError, TypeError):
            return None
        if len(value.strip()) < min_len:
            return ComplianceViolation(
                field_name=field_name,
                rule_name=rule.rule_name,
                rule_type=rule_type,
                severity=rule.severity,
                message=rule.message or f"欄位「{field_name}」至少需要 {min_len} 個字元",
            )

    elif rule_type == "max_length":
        try:
            max_len = int(rule_value)
        except (ValueError, TypeError):
            return None
        if len(value.strip()) > max_len:
            return ComplianceViolation(
                field_name=field_name,
                rule_name=rule.rule_name,
                rule_type=rule_type,
                severity=rule.severity,
                message=rule.message or f"欄位「{field_name}」不可超過 {max_len} 個字元",
            )

    elif rule_type == "regex":
        try:
            if not re.search(rule_value, value):
                return ComplianceViolation(
                    field_name=field_name,
                    rule_name=rule.rule_name,
                    rule_type=rule_type,
                    severity=rule.severity,
                    message=rule.message or f"欄位「{field_name}」格式不符合規則",
                )
        except re.error:
            logger.warning(f"Invalid regex in rule {rule.rule_name}: {rule_value}")
            return None

    elif rule_type == "contains":
        if rule_value and rule_value not in value:
            return ComplianceViolation(
                field_name=field_name,
                rule_name=rule.rule_name,
                rule_type=rule_type,
                severity=rule.severity,
                message=rule.message or f"欄位「{field_name}」必須包含「{rule_value}」",
            )

    return None


def check_compliance(
    fields: list[FieldFillResult], rules: list[ComplianceRule]
) -> ComplianceCheckResult:
    """Run all active rules against all filled fields.

    Returns a ComplianceCheckResult with violations and summary counts.
    """
    violations: list[ComplianceViolation] = []

    active_rules = [r for r in rules if r.is_active]

    for field in fields:
        for rule in active_rules:
            if not _field_matches_pattern(field.field_name, rule.field_pattern):
                continue
            violation = _check_single_rule(field.field_name, field.value, rule)
            if violation:
                violations.append(violation)

    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")
    info = sum(1 for v in violations if v.severity == "info")

    return ComplianceCheckResult(
        violations=violations,
        total_errors=errors,
        total_warnings=warnings,
        total_info=info,
        passed=errors == 0,
    )


async def check_form_compliance(
    db: AsyncSession, user_id: int, fields: list[FieldFillResult]
) -> ComplianceCheckResult:
    """Load rules from DB and check compliance for form fields."""
    rules = await list_rules(db, user_id, active_only=True)
    return check_compliance(fields, rules)
