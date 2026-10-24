from backend.services.adapter import clean_dataframe
from backend.services.pipeline_runner import run_selected_pipeline
from fastapi import APIRouter, HTTPException
from pathlib import Path
from backend.schemas import CleanRequest
import pandas as pd
from zipfile import BadZipFile

# Khoi tao Router
router = APIRouter()

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
def clean_file(request: CleanRequest):

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
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

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

    # STEP 5: Frontend can submit an ordered pipeline. Older clients may
    # still submit the legacy four cleaning options.
    options = request.model_dump(mode="json", exclude={"file_id", "pipeline"})
    try:
        if request.pipeline is not None:
            pipeline = [step.model_dump(mode="json") for step in request.pipeline]
            cleaned_df, audit_summary = run_selected_pipeline(df, pipeline)
        else:
            cleaned_df = clean_dataframe(df, options)
            # Legacy adapter does not expose the DataCleaner audit log.
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
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


    # Kiem tra ket qua tu Data Engine
    if not isinstance(cleaned_df, pd.DataFrame):
        raise HTTPException(
            status_code=500,
            detail="Data Engine must return a DataFrame"
        )

    # BƯỚC 7: Luu du lieu sau xu ly
    output_path = (
        PROCESSED_DIR / f"{request.file_id}.csv"
    )
    try:
        cleaned_df.to_csv(
            output_path,
            index=False
        )
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Failed to save processed file"
        )

    # BƯỚC 8: Tra ket qua ve Frontend
    return {
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
        "options": options
    }
