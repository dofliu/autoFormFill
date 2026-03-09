"""
Indexing Service — parses, chunks, embeds files and manages FileIndex records.

Handles the full lifecycle:
  1. Calculate file hash (SHA-256)
  2. Extract text (docx/pdf/txt/md)
  3. Chunk text into segments
  4. Embed chunks via LLM adapter
  5. Store in ChromaDB (auto_indexed collection)
  6. Track in FileIndex table (SQLite)

Supports incremental indexing:
  - New files: full index
  - Modified files (hash changed): delete old chunks → re-index
  - Deleted files: remove chunks + mark as deleted
"""
import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.llm.factory import get_llm_adapter
from app.models.file_index import FileIndex
from app.services.document_service import extract_text
from app.utils.chunker import chunk_text
from app.utils.file_utils import detect_file_type
from app.vector_store import get_collection

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_auto_collection():
    """Get or create the auto-indexed ChromaDB collection."""
    return get_collection(settings.auto_index_collection)


async def _remove_chunks_from_chroma(doc_id: str) -> int:
    """Remove all chunks for a given doc_id from ChromaDB. Returns count removed."""
    collection = _get_auto_collection()

    # Get existing IDs for this doc
    try:
        existing = await asyncio.to_thread(
            collection.get, where={"doc_id": doc_id}, include=[]
        )
        if existing and existing["ids"]:
            await asyncio.to_thread(collection.delete, ids=existing["ids"])
            return len(existing["ids"])
    except Exception as e:
        logger.warning(f"Failed to remove chunks for doc_id={doc_id}: {e}")
    return 0


async def _set_error_status(file_path: str, error_msg: str):
    """Helper: set a FileIndex record to error status."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileIndex).where(FileIndex.file_path == file_path)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "error"
            record.error_message = str(error_msg)[:500]
            await db.commit()


async def index_file(file_path: str) -> dict:
    """Index a single file: extract -> chunk -> embed -> store.

    Returns a dict with indexing results.
    """
    file_path = os.path.abspath(file_path)
    file_type = detect_file_type(file_path)

    if file_type == "unknown":
        raise ValueError(f"Unsupported file type: {file_path}")

    # Compute hash (blocking I/O, run in thread)
    file_hash = await asyncio.to_thread(compute_file_hash, file_path)
    file_size = await asyncio.to_thread(os.path.getsize, file_path)

    # Check if already indexed with same hash
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileIndex).where(FileIndex.file_path == file_path)
        )
        existing = result.scalar_one_or_none()

        if existing and existing.file_hash == file_hash and existing.status == "indexed":
            logger.info(f"Skipping (unchanged): {file_path}")
            return {"action": "skipped", "file_path": file_path, "reason": "unchanged"}

        # If exists with different hash, need to re-index
        if existing and existing.doc_id:
            logger.info(f"Re-indexing (hash changed): {file_path}")
            await _remove_chunks_from_chroma(existing.doc_id)
            existing.status = "indexing"
            existing.doc_id = ""
            await db.commit()
        elif existing:
            existing.status = "indexing"
            await db.commit()
        else:
            # New file — write doc_id early so we can track orphans
            existing = FileIndex(
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                file_type=file_type,
                status="indexing",
                collection=settings.auto_index_collection,
            )
            db.add(existing)
            await db.commit()
            await db.refresh(existing)

    # Extract text
    try:
        text = await asyncio.to_thread(extract_text, file_path, file_type)
    except Exception as e:
        await _set_error_status(file_path, str(e))
        logger.error(f"Text extraction failed for {file_path}: {e}")
        return {"action": "error", "file_path": file_path, "error": str(e)}

    if not text.strip():
        await _set_error_status(file_path, "No text extracted")
        return {"action": "error", "file_path": file_path, "error": "No text extracted"}

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        await _set_error_status(file_path, "No chunks produced")
        return {"action": "error", "file_path": file_path, "error": "No chunks produced"}

    # Embed
    try:
        adapter = get_llm_adapter()
        embeddings = await asyncio.to_thread(adapter.embed_batch, chunks)
    except Exception as e:
        await _set_error_status(file_path, f"Embedding failed: {e}")
        logger.error(f"Embedding failed for {file_path}: {e}")
        return {"action": "error", "file_path": file_path, "error": str(e)}

    # Store in ChromaDB
    doc_id = uuid.uuid4().hex
    collection = _get_auto_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    filename = os.path.basename(file_path)
    metadatas = [
        {
            "doc_id": doc_id,
            "source": "auto_index",
            "file_path": file_path,
            "filename": filename,
            "file_type": file_type,
        }
        for _ in chunks
    ]

    await asyncio.to_thread(
        collection.add,
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    # Update FileIndex record
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileIndex).where(FileIndex.file_path == file_path)
        )
        record = result.scalar_one_or_none()
        if record:
            record.file_hash = file_hash
            record.file_size = file_size
            record.file_type = file_type
            record.status = "indexed"
            record.doc_id = doc_id
            record.chunks_count = len(chunks)
            record.error_message = ""
            record.last_indexed_at = datetime.now(timezone.utc)
            await db.commit()

    logger.info(f"Indexed: {file_path} ({len(chunks)} chunks)")
    return {
        "action": "indexed",
        "file_path": file_path,
        "doc_id": doc_id,
        "chunks_count": len(chunks),
    }


async def remove_file(file_path: str) -> dict:
    """Remove a file from the index (when file is deleted from disk)."""
    file_path = os.path.abspath(file_path)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileIndex).where(FileIndex.file_path == file_path)
        )
        record = result.scalar_one_or_none()
        if not record:
            return {"action": "skipped", "file_path": file_path, "reason": "not_indexed"}

        # Remove from ChromaDB
        if record.doc_id:
            removed = await _remove_chunks_from_chroma(record.doc_id)
            logger.info(f"Removed {removed} chunks for {file_path}")

        record.status = "deleted"
        record.chunks_count = 0
        record.doc_id = ""
        await db.commit()

    logger.info(f"Removed from index: {file_path}")
    return {"action": "removed", "file_path": file_path}


async def scan_directory(directory: str) -> dict:
    """Scan a directory and index all supported files.

    Handles:
      - New files -> index
      - Modified files (hash changed) -> re-index
      - Deleted files (in DB but not on disk) -> remove
    """
    directory = os.path.abspath(directory)
    supported_exts = settings.get_supported_extensions()

    if not os.path.isdir(directory):
        logger.warning(f"Watch directory does not exist: {directory}")
        return {"error": f"Directory not found: {directory}"}

    # Collect all supported files on disk
    disk_files: set[str] = set()
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in supported_exts:
                full_path = os.path.abspath(os.path.join(root, filename))
                disk_files.add(full_path)

    # Get all indexed files for this directory from DB
    # Use trailing separator to prevent prefix false matches
    # e.g. /home/docs matching /home/docs_backup
    dir_prefix = directory.rstrip(os.sep) + os.sep
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileIndex).where(
                FileIndex.file_path.startswith(dir_prefix),
                FileIndex.status != "deleted",
            )
        )
        db_records = {r.file_path: r for r in result.scalars().all()}

    stats = {"indexed": 0, "re_indexed": 0, "removed": 0, "skipped": 0, "errors": 0}

    # Index new / modified files
    for file_path in disk_files:
        try:
            result = await index_file(file_path)
            action = result.get("action", "")
            if action == "indexed":
                if file_path in db_records:
                    stats["re_indexed"] += 1
                else:
                    stats["indexed"] += 1
            elif action == "skipped":
                stats["skipped"] += 1
            elif action == "error":
                stats["errors"] += 1
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            stats["errors"] += 1

    # Remove files that are in DB but no longer on disk
    for db_path in db_records:
        if db_path not in disk_files:
            try:
                await remove_file(db_path)
                stats["removed"] += 1
            except Exception as e:
                logger.error(f"Error removing {db_path}: {e}")
                stats["errors"] += 1

    logger.info(f"Scan complete for {directory}: {stats}")
    return stats


async def get_index_status() -> dict:
    """Get overall indexing statistics."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FileIndex))
        records = result.scalars().all()

    status_counts: dict[str, int] = {}
    total_chunks = 0
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        total_chunks += r.chunks_count

    return {
        "total_files": len(records),
        "total_chunks": total_chunks,
        "by_status": status_counts,
        "watch_dirs": settings.get_watch_dirs(),
        "supported_extensions": list(settings.get_supported_extensions()),
    }


async def get_indexed_files(
    status: str | None = None, limit: int = 100
) -> list[dict]:
    """Get list of indexed files, optionally filtered by status."""
    async with AsyncSessionLocal() as db:
        query = select(FileIndex)
        if status:
            query = query.where(FileIndex.status == status)
        query = query.order_by(FileIndex.updated_at.desc()).limit(limit)
        result = await db.execute(query)
        return [r.to_dict() for r in result.scalars().all()]
