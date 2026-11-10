"""Authenticated pipeline history and result re-download endpoints."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response

from backend.database import execute_query, fetch_all, fetch_one
from backend.security import get_current_user

router = APIRouter(prefix="/history", tags=["Personal History"])
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _history_payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        stats = json.loads(row.get("stats_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        stats = {}
    return {
        "id": row["id"],
        "filename": row["filename"],
        "file_id": row["file_id"],
        "created_at": row.get("created_at"),
        "stats": stats,
    }


def _get_owned_history(history_id: int, user_id: int) -> dict[str, Any]:
    row = fetch_one(
        "SELECT id, user_id, filename, file_id, stats_json, created_at "
        "FROM pipeline_history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="History record not found")
    return row


@router.get("")
def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
):
    rows = fetch_all(
        "SELECT id, user_id, filename, file_id, stats_json, created_at "
        "FROM pipeline_history WHERE user_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (int(user["id"]), limit, offset),
    )
    count = fetch_one(
        "SELECT COUNT(*) AS total FROM pipeline_history WHERE user_id = ?",
        (int(user["id"]),),
    )
    return {
        "history": [_history_payload(row) for row in rows],
        "total": int(count["total"] if count else 0),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{history_id}")
def get_history_item(history_id: int, user: dict[str, Any] = Depends(get_current_user)):
    row = _get_owned_history(history_id, int(user["id"]))
    return {"history": _history_payload(row)}


@router.get("/{history_id}/download")
def download_history_result(
    history_id: int,
    file_format: Literal["csv", "json"] = "csv",
    suffix: Literal["train_cleaned", "test_cleaned"] | None = None,
    user: dict[str, Any] = Depends(get_current_user),
):
    row = _get_owned_history(history_id, int(user["id"]))
    file_id = UUID(row["file_id"])
    suffix_text = f"_{suffix}" if suffix else ""
    file_path = PROCESSED_DIR / f"{file_id}{suffix_text}.csv"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Processed result is no longer available")

    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(row["filename"]).stem).strip("._") or "dataset"
    export_name = f"{safe_stem}_cleaned{suffix_text}"
    if file_format == "csv":
        return FileResponse(file_path, media_type="text/csv", filename=f"{export_name}.csv")

    try:
        frame = pd.read_csv(file_path)
        payload = frame.to_json(orient="records", force_ascii=False)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise HTTPException(status_code=500, detail=f"Cannot export history result: {exc}") from exc
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{export_name}.json"'},
    )


@router.delete("/{history_id}")
def delete_history_item(history_id: int, user: dict[str, Any] = Depends(get_current_user)):
    _get_owned_history(history_id, int(user["id"]))
    execute_query(
        "DELETE FROM pipeline_history WHERE id = ? AND user_id = ?",
        (history_id, int(user["id"])),
    )
    return {"message": "History record deleted", "history_id": history_id}
