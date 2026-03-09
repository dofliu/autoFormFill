"""Document version tracking + diff comparison endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.error import ERR_NOT_FOUND, ERR_VALIDATION
from app.schemas.version import (
    DiffResult,
    DocumentVersionResponse,
    DocumentVersionUpdate,
)
from app.services import version_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users/{user_id}/versions",
    tags=["Versions"],
)


def _version_response(ver) -> DocumentVersionResponse:
    d = ver.to_dict()
    return DocumentVersionResponse(**d)


@router.get("/files", response_model=list[dict])
async def list_tracked_files(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all files with version tracking, showing latest version info."""
    return await version_service.list_tracked_files(db, user_id)


@router.get("/", response_model=list[DocumentVersionResponse])
async def list_versions(
    user_id: int,
    file_path: str | None = Query(None, description="Filter by file path"),
    db: AsyncSession = Depends(get_db),
):
    """List all document versions for a user, optionally filtered by file path."""
    versions = await version_service.list_versions(db, user_id, file_path=file_path)
    return [_version_response(v) for v in versions]


@router.get("/{version_id}", response_model=DocumentVersionResponse)
async def get_version(
    user_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single document version."""
    ver = await version_service.get_version(db, version_id)
    if not ver or ver.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Version not found", "code": ERR_NOT_FOUND},
        )
    return _version_response(ver)


@router.put("/{version_id}", response_model=DocumentVersionResponse)
async def update_version(
    user_id: int,
    version_id: int,
    data: DocumentVersionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update version metadata (label)."""
    existing = await version_service.get_version(db, version_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Version not found", "code": ERR_NOT_FOUND},
        )
    updated = await version_service.update_version(db, version_id, data)
    return _version_response(updated)


@router.delete("/{version_id}", status_code=204)
async def delete_version(
    user_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single version."""
    existing = await version_service.get_version(db, version_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Version not found", "code": ERR_NOT_FOUND},
        )
    await version_service.delete_version(db, version_id)


@router.get("/diff/{old_version_id}/{new_version_id}", response_model=DiffResult)
async def diff_versions(
    user_id: int,
    old_version_id: int,
    new_version_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Compare two document versions and return a line-level diff."""
    # Verify ownership
    old_ver = await version_service.get_version(db, old_version_id)
    if not old_ver or old_ver.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Version {old_version_id} not found", "code": ERR_NOT_FOUND},
        )
    new_ver = await version_service.get_version(db, new_version_id)
    if not new_ver or new_ver.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Version {new_version_id} not found", "code": ERR_NOT_FOUND},
        )

    if old_ver.file_path != new_ver.file_path:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Cannot diff versions of different files",
                "code": ERR_VALIDATION,
            },
        )

    result = await version_service.diff_versions(db, old_version_id, new_version_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Could not compute diff", "code": ERR_NOT_FOUND},
        )
    return result
