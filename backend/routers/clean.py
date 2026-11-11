import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.database import execute_query
from backend.schemas import CleanRequest
from backend.security import get_optional_current_user
from backend.services.adapter import clean_dataframe
from backend.services.pipeline_runner import run_selected_pipeline
from backend.services.retention_guard import cleanup_ephemeral_files

# Khoi tao Router
router = APIRouter(tags=["Cleaning Pipeline"])
logger = logging.getLogger(__name__)

# Thoi gian timeout toi da cho 1 lan chay pipeline (15 giay de tranh nghen Threadpool)
PIPELINE_TIMEOUT_SECONDS = 15.0

# Thu muc luu du lieu goc
RAW_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
)

# Thu muc luu du lieu sau xu ly
PROCESSED_DIR = RAW_DIR.parent / "processed"

# Tao thu muc neu chua ton tai
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/clean")
async def clean_file(
    request: CleanRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict | None = Depends(get_optional_current_user),
):
    # Kích hoạt quét dọn dẹp các tệp tạm đã hết hạn TTL
    background_tasks.add_task(cleanup_ephemeral_files)

    # BƯỚC 1: Tim file da upload
    file_path = None

    for extension in [".csv", ".xlsx"]:
        path = RAW_DIR / f"{request.file_id}{extension}"

        if path.is_file():
            file_path = path
            break

    # BƯỚC 2: Kiem tra file co ton tai khong
    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # BƯỚC 3: Doc du lieu bang Pandas
    try:
        if file_path.suffix == ".csv":
            df = await asyncio.to_thread(pd.read_csv, file_path)
        else:
            df = await asyncio.to_thread(pd.read_excel, file_path)

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeError,
        ValueError,
        BadZipFile,
        OSError
    ) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot read dataset: {error}"
        )

    # BƯỚC 4: Thong ke du lieu goc
    total_rows = len(df)
    total_columns = len(df.columns)

    column_names = df.columns.tolist()

    missing_values = {
        str(column): int(count)
        for column, count in df.isna().sum().items()
    }

    # STEP 5: Frontend can submit an ordered pipeline with optional ML mode.
    options = request.model_dump(mode="json", exclude={"file_id", "pipeline"})
    train_df = None
    test_df = None

    try:
        if request.pipeline is not None:
            pipeline = [step.model_dump(mode="json") for step in request.pipeline]
            is_ml_mode = (request.purpose == "ml")
            test_size = 1.0 - request.train_ratio

            def _run_pipeline():
                if is_ml_mode:
                    return run_selected_pipeline(
                        df, pipeline, is_ml_mode=True, test_size=test_size, return_split_dfs=True
                    )
                else:
                    return run_selected_pipeline(
                        df, pipeline, is_ml_mode=False
                    )

            try:
                pipeline_result = await asyncio.wait_for(
                    asyncio.to_thread(_run_pipeline),
                    timeout=PIPELINE_TIMEOUT_SECONDS,
                )
                if is_ml_mode:
                    cleaned_df, audit_summary, train_df, test_df = pipeline_result
                else:
                    cleaned_df, audit_summary = pipeline_result
            except asyncio.TimeoutError:
                logger.error("Pipeline execution timed out (>%ss) for file_id %s", PIPELINE_TIMEOUT_SECONDS, request.file_id)
                raise HTTPException(
                    status_code=408,
                    detail=f"Pipeline execution timed out (limit: {int(PIPELINE_TIMEOUT_SECONDS)}s). Dataset may be too large or complex for real-time processing."
                )
        else:
            try:
                cleaned_df = await asyncio.wait_for(
                    asyncio.to_thread(clean_dataframe, df, options),
                    timeout=PIPELINE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error("Legacy cleaning timed out (>%ss) for file_id %s", PIPELINE_TIMEOUT_SECONDS, request.file_id)
                raise HTTPException(
                    status_code=408,
                    detail=f"Cleaning timed out (limit: {int(PIPELINE_TIMEOUT_SECONDS)}s)."
                )

            audit_summary = {
                "initial_rows": total_rows,
                "final_rows": len(cleaned_df),
                "rows_removed": total_rows - len(cleaned_df),
                "initial_columns": total_columns,
                "final_columns": len(cleaned_df.columns),
                "columns_added_or_removed": len(cleaned_df.columns) - total_columns,
                "total_steps": 1,
                "history": [{
                    "step": 1,
                    "action": "legacy_adapter",
                    "description": "Processed using the legacy four-option adapter",
                    "details": options,
                }],
            }
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Kiem tra ket qua tu Data Engine
    if not isinstance(cleaned_df, pd.DataFrame):
        raise HTTPException(
            status_code=500,
            detail="Data Engine must return a DataFrame"
        )

    # BƯỚC 7: Luu du lieu sau xu ly
    output_path = PROCESSED_DIR / f"{request.file_id}.csv"
    try:
        await asyncio.to_thread(cleaned_df.to_csv, output_path, index=False)

        # Luu rieng 2 tap Train va Test neu chay o che do Machine Learning
        if train_df is not None and test_df is not None:
            train_path = PROCESSED_DIR / f"{request.file_id}_train_cleaned.csv"
            test_path = PROCESSED_DIR / f"{request.file_id}_test_cleaned.csv"
            await asyncio.to_thread(train_df.to_csv, train_path, index=False)
            await asyncio.to_thread(test_df.to_csv, test_path, index=False)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Failed to save processed file"
        )

    # Luu lich su chi khi request co session hop le (Online Workspace).
    # Request an danh van xu ly binh thuong va khong tao ban ghi DB (Offline Mode).
    history_id = None
    if current_user is not None:
        metadata_path = RAW_DIR / f"{request.file_id}.meta.json"
        source_filename = file_path.name
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                source_filename = metadata.get("filename") or source_filename
            except (OSError, json.JSONDecodeError):
                logger.warning("Could not read upload metadata for %s", request.file_id)

        history_stats = {
            "original_data": {"rows": total_rows, "columns": total_columns},
            "processed_data": {"rows": len(cleaned_df), "columns": len(cleaned_df.columns)},
            "audit_summary": audit_summary,
            "purpose": request.purpose,
        }
        if train_df is not None and test_df is not None:
            history_stats["ml_split"] = {
                "train_rows": len(train_df),
                "test_rows": len(test_df),
                "train_file": f"{request.file_id}_train_cleaned.csv",
                "test_file": f"{request.file_id}_test_cleaned.csv",
            }
        try:
            history_id = execute_query(
                "INSERT INTO pipeline_history (user_id, filename, file_id, stats_json) VALUES (?, ?, ?, ?)",
                (int(current_user["id"]), source_filename, str(request.file_id), json.dumps(history_stats, ensure_ascii=False, default=str)),
            )
        except sqlite3.Error:
            # A history-storage issue must not discard an otherwise valid clean result.
            logger.exception("Failed to persist pipeline history for file %s", request.file_id)

    # BƯỚC 8: Tra ket qua ve Frontend
    response_data = {
        "message": "Dataset processed and saved",
        "file_id": str(request.file_id),

        "original_data": {
            "rows": total_rows,
            "columns": total_columns,
            "column_names": [
                str(column) for column in column_names
            ],
            "missing_values": missing_values
        },

        "processed_data": {
            "rows": len(cleaned_df),
            "columns": len(cleaned_df.columns),
            "output_file": output_path.name
        },

        "cleaning_applied": True,
        "audit_summary": audit_summary,
        "options": options,
        "purpose": request.purpose,
        "history_id": history_id
    }

    if train_df is not None and test_df is not None:
        response_data["ml_split"] = {
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "train_file": f"{request.file_id}_train_cleaned.csv",
            "test_file": f"{request.file_id}_test_cleaned.csv"
        }

    return response_data
