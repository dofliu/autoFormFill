"""
Indexing Router — API endpoints for auto-indexing management.

Provides status, manual rescan, and file listing for the auto-indexing system.
"""
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services.file_watcher import file_watcher
from app.services.indexing_service import (
    get_index_status,
    get_indexed_files,
    index_file,
    remove_file,
    scan_directory,
)

router = APIRouter(prefix="/api/v1/indexing", tags=["Indexing"])

# Valid status values for filtering
VALID_STATUSES = {"pending", "indexing", "indexed", "stale", "deleted", "error"}


# --- Request body models (avoid file paths in query params) ---

class FilePathRequest(BaseModel):
    file_path: str


# --- Security helpers ---

def _is_within_watch_dirs(file_path: str) -> bool:
    """Validate that a file path is inside one of the configured watch directories.

    Prevents path traversal attacks by ensuring the resolved absolute path
    starts with an allowed directory prefix.
    """
    resolved = os.path.abspath(os.path.normpath(file_path))
    for watch_dir in settings.get_watch_dirs():
        watch_dir_normalized = os.path.abspath(os.path.normpath(watch_dir))
        # Ensure trailing separator to prevent prefix false matches
        # e.g. /home/user/docs matching /home/user/docs_backup
        if resolved.startswith(watch_dir_normalized + os.sep) or resolved == watch_dir_normalized:
            return True
    return False


# --- Endpoints ---

@router.get("/status")
async def indexing_status():
    """Get overall indexing statistics and watcher status."""
    index_stats = await get_index_status()
    watcher_status = file_watcher.get_status()
    return {
        "watcher": watcher_status,
        "index": index_stats,
    }


@router.post("/rescan")
async def rescan_directories():
    """Manually trigger a full rescan of all watched directories."""
    watch_dirs = settings.get_watch_dirs()
    if not watch_dirs:
        return {"message": "No watch directories configured", "stats": {}}

    all_stats = {}
    for dir_path in watch_dirs:
        try:
            stats = await scan_directory(dir_path)
            all_stats[dir_path] = stats
        except Exception as e:
            all_stats[dir_path] = {"error": str(e)}

    return {"message": "Rescan complete", "stats": all_stats}


@router.get("/files")
async def list_indexed_files(
    status: str | None = Query(None, description="Filter by status: indexed, indexing, error, deleted, stale, pending"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List indexed files, optionally filtered by status."""
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Valid values: {', '.join(sorted(VALID_STATUSES))}",
        )
    files = await get_indexed_files(status=status, limit=limit)
    return {"files": files, "total": len(files)}


@router.post("/index-file")
async def index_single_file(body: FilePathRequest):
    """Manually index a single file by its absolute path.

    The file must be located within one of the configured WATCH_DIRS.
    """
    file_path = body.file_path

    if not _is_within_watch_dirs(file_path):
        raise HTTPException(
            status_code=403,
            detail="File path is not within any configured watch directory",
        )
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    try:
        result = await index_file(file_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove-file")
async def remove_single_file(body: FilePathRequest):
    """Remove a single file from the index.

    The file must be located within one of the configured WATCH_DIRS.
    """
    file_path = body.file_path

    if not _is_within_watch_dirs(file_path):
        raise HTTPException(
            status_code=403,
            detail="File path is not within any configured watch directory",
        )
    try:
        result = await remove_file(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
