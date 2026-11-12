"""Personal and built-in pipeline recipe endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.database import execute_query, fetch_all, fetch_one
from backend.schemas import PipelineStep
from backend.security import get_current_user

router = APIRouter(prefix="/recipes", tags=["Pipeline Recipes"])


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    steps: list[PipelineStep] = Field(min_length=1, max_length=50)


class RecipeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    steps: list[PipelineStep] | None = Field(default=None, min_length=1, max_length=50)


_STEP_ALIASES = {
    "imputation": "missing_values",
}


def _normalize_steps(raw_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert older seeded recipe records to the current pipeline contract."""
    normalized: list[dict[str, Any]] = []
    for raw_step in raw_steps:
        kind = raw_step.get("step_type", raw_step.get("type"))
        if not isinstance(kind, str):
            continue
        kind = _STEP_ALIASES.get(kind, kind)
        config = dict(raw_step.get("config") or {})

        if kind == "missing_values":
            strategy_aliases = {"drop_rows": "drop_row", "drop_columns": "drop_col"}
            strategy = config.get("strategy")
            if strategy in strategy_aliases:
                config["strategy"] = strategy_aliases[strategy]
        elif kind == "encoding":
            if config.get("method") == "onehot":
                config["method"] = "one_hot"
        elif kind == "scaling":
            if config.get("method") == "minmax":
                config["method"] = "min_max"

        normalized.append({"step_type": kind, "config": config})
    return normalized


def _recipe_payload(row: dict[str, Any], current_user_id: int) -> dict[str, Any]:
    try:
        raw_steps = json.loads(row.get("steps_json") or "[]")
    except (TypeError, json.JSONDecodeError):
        raw_steps = []
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row.get("description"),
        "steps": _normalize_steps(raw_steps if isinstance(raw_steps, list) else []),
        "is_public": bool(row.get("is_public")),
        "is_owner": row.get("user_id") == current_user_id,
        "created_at": row.get("created_at"),
    }


def _get_accessible_recipe(recipe_id: int, user_id: int) -> dict[str, Any]:
    row = fetch_one(
        "SELECT id, user_id, name, description, steps_json, is_public, created_at "
        "FROM pipeline_recipes WHERE id = ? AND (user_id = ? OR is_public = 1)",
        (recipe_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return row


@router.get("")
def list_recipes(user: dict[str, Any] = Depends(get_current_user)):
    """List the current user's recipes and shared built-in recipes."""
    rows = fetch_all(
        "SELECT id, user_id, name, description, steps_json, is_public, created_at "
        "FROM pipeline_recipes WHERE user_id = ? OR is_public = 1 "
        "ORDER BY is_public DESC, created_at DESC, id DESC",
        (int(user["id"]),),
    )
    return {"recipes": [_recipe_payload(row, int(user["id"])) for row in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeCreate,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Save an ordered cleaning pipeline for the authenticated user."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Tên kịch bản không được để trống")

    exists = fetch_one(
        "SELECT id FROM pipeline_recipes WHERE user_id = ? AND lower(name) = lower(?)",
        (int(user["id"]), name),
    )
    if exists:
        raise HTTPException(status_code=409, detail="Bạn đã có một kịch bản với tên này trong tài khoản. Vui lòng chọn tên khác.")

    steps = [step.model_dump(mode="json") for step in payload.steps]
    recipe_id = execute_query(
        "INSERT INTO pipeline_recipes (user_id, name, description, steps_json, is_public) "
        "VALUES (?, ?, ?, ?, 0)",
        (int(user["id"]), name, payload.description, json.dumps(steps, ensure_ascii=False)),
    )
    row = fetch_one(
        "SELECT id, user_id, name, description, steps_json, is_public, created_at "
        "FROM pipeline_recipes WHERE id = ?",
        (recipe_id,),
    )
    return {"recipe": _recipe_payload(row, int(user["id"]))}


@router.get("/{recipe_id}")
def get_recipe(recipe_id: int, user: dict[str, Any] = Depends(get_current_user)):
    row = _get_accessible_recipe(recipe_id, int(user["id"]))
    return {"recipe": _recipe_payload(row, int(user["id"]))}


@router.post("/{recipe_id}/apply")
def apply_recipe(recipe_id: int, user: dict[str, Any] = Depends(get_current_user)):
    """Return a recipe's pipeline in the exact shape accepted by /api/clean."""
    row = _get_accessible_recipe(recipe_id, int(user["id"]))
    recipe = _recipe_payload(row, int(user["id"]))
    if not recipe["steps"]:
        raise HTTPException(status_code=422, detail="Recipe contains no valid pipeline steps")
    return {"recipe_id": recipe_id, "name": recipe["name"], "pipeline": recipe["steps"]}


@router.put("/{recipe_id}")
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    user: dict[str, Any] = Depends(get_current_user),
):
    row = fetch_one(
        "SELECT id, user_id FROM pipeline_recipes WHERE id = ? AND user_id = ?",
        (recipe_id, int(user["id"])),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found or not editable")

    fields: list[str] = []
    values: list[Any] = []
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Recipe name cannot be empty")
        fields.append("name = ?")
        values.append(name)
    if payload.description is not None:
        fields.append("description = ?")
        values.append(payload.description)
    if payload.steps is not None:
        fields.append("steps_json = ?")
        values.append(json.dumps([step.model_dump(mode="json") for step in payload.steps], ensure_ascii=False))
    if not fields:
        raise HTTPException(status_code=400, detail="No recipe fields were supplied")

    values.extend([recipe_id, int(user["id"])])
    execute_query(
        f"UPDATE pipeline_recipes SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
        tuple(values),
    )
    updated = fetch_one(
        "SELECT id, user_id, name, description, steps_json, is_public, created_at "
        "FROM pipeline_recipes WHERE id = ?",
        (recipe_id,),
    )
    return {"recipe": _recipe_payload(updated, int(user["id"]))}


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, user: dict[str, Any] = Depends(get_current_user)):
    result = fetch_one(
        "SELECT id FROM pipeline_recipes WHERE id = ? AND user_id = ?",
        (recipe_id, int(user["id"])),
    )
    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found or not deletable")
    execute_query(
        "DELETE FROM pipeline_recipes WHERE id = ? AND user_id = ?",
        (recipe_id, int(user["id"])),
    )
    return {"message": "Recipe deleted successfully", "recipe_id": recipe_id}
