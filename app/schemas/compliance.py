"""Pydantic schemas for the compliance checking system."""
from pydantic import BaseModel


class ComplianceRuleCreate(BaseModel):
    rule_name: str
    field_pattern: str = "*"
    rule_type: str  # required | min_length | max_length | regex | contains
    rule_value: str = ""
    severity: str = "warning"  # error | warning | info
    message: str = ""


class ComplianceRuleUpdate(BaseModel):
    rule_name: str | None = None
    field_pattern: str | None = None
    rule_type: str | None = None
    rule_value: str | None = None
    severity: str | None = None
    message: str | None = None
    is_active: bool | None = None


class ComplianceRuleResponse(BaseModel):
    id: int
    user_id: int
    rule_name: str
    field_pattern: str
    rule_type: str
    rule_value: str
    severity: str
    message: str
    is_active: bool
    created_at: str
    updated_at: str


class ComplianceViolation(BaseModel):
    """A single compliance violation found during checking."""
    field_name: str
    rule_name: str
    rule_type: str
    severity: str  # error | warning | info
    message: str


class ComplianceCheckResult(BaseModel):
    """Result of running compliance checks on a set of fill results."""
    violations: list[ComplianceViolation] = []
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0
    passed: bool = True
