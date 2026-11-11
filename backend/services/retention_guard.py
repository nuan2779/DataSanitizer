"""Zero-Retention Guard for Offline and Ephemeral Dataset Storage.

Ensures that uploaded and processed datasets in Offline mode (or unlinked to
an authenticated user's history in SQLite) are strictly ephemeral:
1. Automated periodic / background sweeping of unpersisted files with TTL (default 30 mins).
2. Explicit deletion endpoint DELETE /api/upload/{file_id} for immediate cleanup upon session reset.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Set
from uuid import UUID

from backend.database import fetch_all

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
DEFAULT_OFFLINE_TTL_SECONDS = 1800  # 30 minutes


def get_persisted_file_ids() -> Set[str]:
    """Retrieve all file_id UUIDs linked to authenticated pipeline history in SQLite."""
    try:
        rows = fetch_all("SELECT DISTINCT file_id FROM pipeline_history WHERE file_id IS NOT NULL")
        return {str(r["file_id"]).strip().lower() for r in rows if r.get("file_id")}
    except Exception as exc:
        logger.warning("Could not query pipeline_history for persisted file IDs: %s", exc)
        return set()


def delete_ephemeral_dataset(file_id: str | UUID, force: bool = False) -> bool:
    """Immediately remove all raw and processed files matching file_id if not persisted.
    
    Returns True if at least one related file was removed, False otherwise.
    """
    clean_id = str(file_id).strip().lower()
    if not clean_id:
        return False

    if not force:
        persisted = get_persisted_file_ids()
        if clean_id in persisted:
            logger.info("Skipping deletion of persisted file_id %s (linked to user history)", clean_id)
            return False

    deleted_any = False

    # 1. Clean RAW_DIR
    if RAW_DIR.is_dir():
        for candidate in RAW_DIR.glob(f"{clean_id}*"):
            try:
                candidate.unlink(missing_ok=True)
                deleted_any = True
                logger.info("Deleted raw ephemeral file: %s", candidate.name)
            except OSError as err:
                logger.warning("Failed to delete %s: %s", candidate, err)

    # 2. Clean PROCESSED_DIR
    if PROCESSED_DIR.is_dir():
        for candidate in PROCESSED_DIR.glob(f"{clean_id}*"):
            try:
                candidate.unlink(missing_ok=True)
                deleted_any = True
                logger.info("Deleted processed ephemeral file: %s", candidate.name)
            except OSError as err:
                logger.warning("Failed to delete %s: %s", candidate, err)

    return deleted_any


def cleanup_ephemeral_files(ttl_seconds: int = DEFAULT_OFFLINE_TTL_SECONDS) -> int:
    """Scan raw and processed directories and purge unpersisted files exceeding TTL.
    
    Returns the total number of deleted files.
    """
    persisted = get_persisted_file_ids()
    now = time.time()
    deleted_count = 0

    target_dirs = [d for d in (RAW_DIR, PROCESSED_DIR) if d.is_dir()]

    for directory in target_dirs:
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue

            # Identify the base file_id (36-character UUID)
            stem = file_path.name.split(".")[0].split("_")[0]
            if len(stem) == 36:
                clean_stem = stem.lower()
                if clean_stem in persisted:
                    # File belongs to an authenticated user's history - do not purge
                    continue

            # Check if file has exceeded the TTL
            try:
                mtime = file_path.stat().st_mtime
                age = now - mtime
                if age >= ttl_seconds:
                    file_path.unlink(missing_ok=True)
                    deleted_count += 1
                    logger.info("Purged expired ephemeral file (%ds old): %s", int(age), file_path.name)
            except OSError as err:
                logger.warning("Could not inspect or delete %s: %s", file_path, err)

    return deleted_count
