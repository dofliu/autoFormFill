"""Compliance rules CRUD + validation endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, verify_ownership
from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas.compliance import (
    ComplianceCheckResult,
    ComplianceRuleCreate,
    ComplianceRuleResponse,
    ComplianceRuleUpdate,
)
from app.schemas.error import ERR_NOT_FOUND, ERR_VALIDATION
from app.schemas.form import FieldFillResult
from app.services import compliance_service
from app.job_store import job_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users/{user_id}/compliance-rules",
    tags=["Compliance"],
)


def _rule_response(rule) -> ComplianceRuleResponse:
    d = rule.to_dict()
    return ComplianceRuleResponse(**d)


# ---- CRUD ----

@router.post("/", response_model=ComplianceRuleResponse, status_code=201)
async def create_rule(
    user_id: int,
    data: ComplianceRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Create a new compliance rule."""
    verify_ownership(current_user, user_id)
    if data.rule_type not in compliance_service.VALID_RULE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": f"Invalid rule_type: {data.rule_type}. Valid types: {', '.join(sorted(compliance_service.VALID_RULE_TYPES))}",
                "code": ERR_VALIDATION,
            },
        )
    rule = await compliance_service.create_rule(db, user_id, data)
    return _rule_response(rule)


@router.get("/", response_model=list[ComplianceRuleResponse])
async def list_rules(
    user_id: int,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """List all compliance rules for a user."""
    verify_ownership(current_user, user_id)
    rules = await compliance_service.list_rules(db, user_id, active_only=active_only)
    return [_rule_response(r) for r in rules]


@router.get("/{rule_id}", response_model=ComplianceRuleResponse)
async def get_rule(
    user_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Get a single compliance rule."""
    verify_ownership(current_user, user_id)
    rule = await compliance_service.get_rule(db, rule_id)
    if not rule or rule.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Rule not found", "code": ERR_NOT_FOUND},
        )
    return _rule_response(rule)


@router.put("/{rule_id}", response_model=ComplianceRuleResponse)
async def update_rule(
    user_id: int,
    rule_id: int,
    data: ComplianceRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Update a compliance rule."""
    verify_ownership(current_user, user_id)
    existing = await compliance_service.get_rule(db, rule_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Rule not found", "code": ERR_NOT_FOUND},
        )
    if data.rule_type and data.rule_type not in compliance_service.VALID_RULE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"detail": f"Invalid rule_type: {data.rule_type}", "code": ERR_VALIDATION},
        )
    updated = await compliance_service.update_rule(db, rule_id, data)
    return _rule_response(updated)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    user_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Delete a compliance rule."""
    verify_ownership(current_user, user_id)
    existing = await compliance_service.get_rule(db, rule_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Rule not found", "code": ERR_NOT_FOUND},
        )
    await compliance_service.delete_rule(db, rule_id)


# ---- Validation ----

@router.post("/check/{job_id}", response_model=ComplianceCheckResult)
async def check_job_compliance(
    user_id: int,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile | None = Depends(get_current_user),
):
    """Check compliance of a specific job's fill results against user's rules."""
    verify_ownership(current_user, user_id)
    job = await job_store.get_job(job_id, db)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Job not found", "code": ERR_NOT_FOUND},
        )

    fields = [FieldFillResult(**f) for f in job.get("fields", [])]
    result = await compliance_service.check_form_compliance(db, user_id, fields)
    return result
