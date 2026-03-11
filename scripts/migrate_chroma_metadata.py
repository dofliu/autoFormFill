#!/usr/bin/env python3
"""
Migration script: add ``user_id`` + ``shared`` metadata to existing ChromaDB documents.

Existing documents (created before Phase 6.2) do not have isolation metadata.
This script backfills them with safe defaults:
  - user_id = "-1"   (system-owned, no specific user)
  - shared  = "true"  (visible to all users)

The script is **idempotent** — re-running it will skip documents that already
have both fields set.

Usage:
    cd autoFill
    python -m scripts.migrate_chroma_metadata
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so ``app.*`` imports work
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.vector_store import COLLECTIONS, get_collection  # noqa: E402


def migrate_collection(collection_name: str) -> dict:
    """Backfill ``user_id`` and ``shared`` for all documents in a collection.

    Returns a dict with migration stats.
    """
    collection = get_collection(collection_name)
    stats = {"total": 0, "updated": 0, "skipped": 0, "errors": 0}

    # Fetch all documents (ChromaDB returns everything when no filter)
    try:
        all_docs = collection.get(include=["metadatas"])
    except Exception as e:
        print(f"  ERROR: Could not read collection '{collection_name}': {e}")
        stats["errors"] = 1
        return stats

    if not all_docs or not all_docs["ids"]:
        print(f"  Collection '{collection_name}' is empty — nothing to migrate.")
        return stats

    ids = all_docs["ids"]
    metadatas = all_docs["metadatas"]
    stats["total"] = len(ids)

    ids_to_update = []
    metas_to_update = []

    for doc_id, meta in zip(ids, metadatas):
        if meta is None:
            meta = {}

        has_user_id = "user_id" in meta
        has_shared = "shared" in meta

        if has_user_id and has_shared:
            stats["skipped"] += 1
            continue

        # Backfill missing fields
        new_meta = dict(meta)
        if not has_user_id:
            new_meta["user_id"] = "-1"
        if not has_shared:
            new_meta["shared"] = "true"

        ids_to_update.append(doc_id)
        metas_to_update.append(new_meta)

    if not ids_to_update:
        print(f"  All {stats['total']} documents already have isolation metadata.")
        return stats

    # Batch update
    try:
        collection.update(ids=ids_to_update, metadatas=metas_to_update)
        stats["updated"] = len(ids_to_update)
    except Exception as e:
        print(f"  ERROR during update: {e}")
        stats["errors"] = len(ids_to_update)

    return stats


def main():
    print("=" * 60)
    print("ChromaDB Metadata Migration — Phase 6.2 Multi-User Isolation")
    print("=" * 60)
    print()

    total_stats = {"total": 0, "updated": 0, "skipped": 0, "errors": 0}

    for col_name in COLLECTIONS:
        print(f"[{col_name}]")
        stats = migrate_collection(col_name)
        print(f"  total={stats['total']}  updated={stats['updated']}  "
              f"skipped={stats['skipped']}  errors={stats['errors']}")
        print()

        for key in total_stats:
            total_stats[key] += stats[key]

    print("-" * 60)
    print(f"TOTAL: {total_stats['total']} documents, "
          f"{total_stats['updated']} updated, "
          f"{total_stats['skipped']} already migrated, "
          f"{total_stats['errors']} errors")

    if total_stats["errors"] > 0:
        print("\n⚠️  Some errors occurred. Re-run the script after fixing issues.")
        sys.exit(1)
    else:
        print("\n✅  Migration complete!")


if __name__ == "__main__":
    main()
