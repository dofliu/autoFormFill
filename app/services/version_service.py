"""Version service — tracks document versions and computes text diffs.

When a document is indexed (or re-indexed), a snapshot of the extracted text
is stored as a DocumentVersion. Users can then compare any two versions to see
a line-level diff.
"""
import difflib
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_version import DocumentVersion
from app.schemas.version import (
    DiffHunk,
    DiffLine,
    DiffResult,
    DocumentVersionUpdate,
)

logger = logging.getLogger(__name__)


# ---- Version CRUD ----

async def create_version(
    db: AsyncSession,
    user_id: int,
    file_path: str,
    file_hash: str,
    content_text: str,
    label: str = "",
) -> DocumentVersion:
    """Create a new version snapshot for a document."""
    # Determine next version number
    result = await db.execute(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.user_id == user_id,
            DocumentVersion.file_path == file_path,
        )
    )
    max_ver = result.scalar() or 0
    next_ver = max_ver + 1

    version = DocumentVersion(
        user_id=user_id,
        file_path=file_path,
        file_hash=file_hash,
        version_number=next_ver,
        content_text=content_text,
        content_length=len(content_text),
        label=label or f"v{next_ver}",
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def get_version(db: AsyncSession, version_id: int) -> DocumentVersion | None:
    """Get a single version by ID."""
    result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.id == version_id)
    )
    return result.scalar_one_or_none()


async def list_versions(
    db: AsyncSession, user_id: int, file_path: str | None = None
) -> list[DocumentVersion]:
    """List all versions for a user, optionally filtered by file path."""
    query = select(DocumentVersion).where(DocumentVersion.user_id == user_id)
    if file_path:
        query = query.where(DocumentVersion.file_path == file_path)
    query = query.order_by(DocumentVersion.file_path, DocumentVersion.version_number.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_tracked_files(db: AsyncSession, user_id: int) -> list[dict]:
    """List all files with version tracking, grouped with latest version info."""
    result = await db.execute(
        select(
            DocumentVersion.file_path,
            func.count(DocumentVersion.id).label("version_count"),
            func.max(DocumentVersion.version_number).label("latest_version"),
            func.max(DocumentVersion.created_at).label("last_updated"),
        )
        .where(DocumentVersion.user_id == user_id)
        .group_by(DocumentVersion.file_path)
        .order_by(func.max(DocumentVersion.created_at).desc())
    )
    rows = result.all()
    return [
        {
            "file_path": row.file_path,
            "version_count": row.version_count,
            "latest_version": row.latest_version,
            "last_updated": row.last_updated.isoformat() if row.last_updated else "",
        }
        for row in rows
    ]


async def update_version(
    db: AsyncSession, version_id: int, data: DocumentVersionUpdate
) -> DocumentVersion | None:
    """Update version metadata (label)."""
    version = await get_version(db, version_id)
    if not version:
        return None
    if data.label is not None:
        version.label = data.label
    await db.commit()
    await db.refresh(version)
    return version


async def delete_version(db: AsyncSession, version_id: int) -> bool:
    """Delete a single version."""
    version = await get_version(db, version_id)
    if not version:
        return False
    await db.delete(version)
    await db.commit()
    return True


# ---- Diff Engine ----

def compute_diff(
    old_text: str, new_text: str,
    file_path: str = "",
    old_version: int = 0, new_version: int = 0,
    old_hash: str = "", new_hash: str = "",
    context_lines: int = 3,
) -> DiffResult:
    """Compute a line-level unified diff between two text versions.

    Uses Python's difflib.SequenceMatcher for efficient comparison.
    Groups changes into hunks with surrounding context.
    """
    if old_text == new_text:
        return DiffResult(
            file_path=file_path,
            old_version=old_version,
            new_version=new_version,
            old_hash=old_hash,
            new_hash=new_hash,
            hunks=[],
            identical=True,
        )

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    opcodes = matcher.get_opcodes()

    hunks: list[DiffHunk] = []
    total_additions = 0
    total_deletions = 0

    # Group opcodes into hunks with context
    current_hunk_lines: list[DiffLine] = []
    hunk_old_start = 0
    hunk_old_count = 0
    hunk_new_start = 0
    hunk_new_count = 0
    in_hunk = False

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            lines = old_lines[i1:i2]
            if in_hunk:
                # Add trailing context
                ctx = lines[:context_lines]
                for k, line in enumerate(ctx):
                    current_hunk_lines.append(DiffLine(
                        line_number_old=i1 + k + 1,
                        line_number_new=j1 + k + 1,
                        tag="equal",
                        content=line.rstrip("\n\r"),
                    ))
                    hunk_old_count += 1
                    hunk_new_count += 1

                # If remaining equal lines are long enough, close hunk
                if len(lines) > context_lines * 2:
                    hunks.append(DiffHunk(
                        old_start=hunk_old_start,
                        old_count=hunk_old_count,
                        new_start=hunk_new_start,
                        new_count=hunk_new_count,
                        lines=current_hunk_lines,
                    ))
                    current_hunk_lines = []
                    in_hunk = False
                elif len(lines) > context_lines:
                    # Add all remaining as context
                    for k, line in enumerate(lines[context_lines:]):
                        current_hunk_lines.append(DiffLine(
                            line_number_old=i1 + context_lines + k + 1,
                            line_number_new=j1 + context_lines + k + 1,
                            tag="equal",
                            content=line.rstrip("\n\r"),
                        ))
                        hunk_old_count += 1
                        hunk_new_count += 1
            continue

        # Start a new hunk if needed
        if not in_hunk:
            in_hunk = True
            current_hunk_lines = []
            # Add leading context from previous equal block
            ctx_start = max(0, i1 - context_lines)
            hunk_old_start = ctx_start + 1
            hunk_new_start = max(0, j1 - context_lines) + 1
            hunk_old_count = 0
            hunk_new_count = 0
            for k in range(ctx_start, i1):
                if k < len(old_lines):
                    current_hunk_lines.append(DiffLine(
                        line_number_old=k + 1,
                        line_number_new=hunk_new_start + (k - ctx_start),
                        tag="equal",
                        content=old_lines[k].rstrip("\n\r"),
                    ))
                    hunk_old_count += 1
                    hunk_new_count += 1

        if tag == "delete":
            for k in range(i1, i2):
                current_hunk_lines.append(DiffLine(
                    line_number_old=k + 1,
                    line_number_new=None,
                    tag="delete",
                    content=old_lines[k].rstrip("\n\r"),
                ))
                hunk_old_count += 1
                total_deletions += 1

        elif tag == "insert":
            for k in range(j1, j2):
                current_hunk_lines.append(DiffLine(
                    line_number_old=None,
                    line_number_new=k + 1,
                    tag="insert",
                    content=new_lines[k].rstrip("\n\r"),
                ))
                hunk_new_count += 1
                total_additions += 1

        elif tag == "replace":
            for k in range(i1, i2):
                current_hunk_lines.append(DiffLine(
                    line_number_old=k + 1,
                    line_number_new=None,
                    tag="delete",
                    content=old_lines[k].rstrip("\n\r"),
                ))
                hunk_old_count += 1
                total_deletions += 1
            for k in range(j1, j2):
                current_hunk_lines.append(DiffLine(
                    line_number_old=None,
                    line_number_new=k + 1,
                    tag="insert",
                    content=new_lines[k].rstrip("\n\r"),
                ))
                hunk_new_count += 1
                total_additions += 1

    # Close final hunk
    if in_hunk and current_hunk_lines:
        hunks.append(DiffHunk(
            old_start=hunk_old_start,
            old_count=hunk_old_count,
            new_start=hunk_new_start,
            new_count=hunk_new_count,
            lines=current_hunk_lines,
        ))

    return DiffResult(
        file_path=file_path,
        old_version=old_version,
        new_version=new_version,
        old_hash=old_hash,
        new_hash=new_hash,
        hunks=hunks,
        total_additions=total_additions,
        total_deletions=total_deletions,
        total_changes=total_additions + total_deletions,
        identical=False,
    )


async def diff_versions(
    db: AsyncSession, version_id_old: int, version_id_new: int
) -> DiffResult | None:
    """Compare two document versions and return a diff result."""
    old_ver = await get_version(db, version_id_old)
    new_ver = await get_version(db, version_id_new)

    if not old_ver or not new_ver:
        return None

    return compute_diff(
        old_text=old_ver.content_text,
        new_text=new_ver.content_text,
        file_path=old_ver.file_path,
        old_version=old_ver.version_number,
        new_version=new_ver.version_number,
        old_hash=old_ver.file_hash,
        new_hash=new_ver.file_hash,
    )
