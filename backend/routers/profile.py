
from pathlib import Path
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.services.profiler import (
    generate_profile,
    profile_single_column
)

router = APIRouter(tags=["Profile"])

# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"


# STEP 1: Find and read uploaded dataset
def load_dataset(file_id: UUID):

    file_key = str(file_id)

    # Supported file formats
    candidates = [
        RAW_DIR / f"{file_key}.csv",
        RAW_DIR / f"{file_key}.xlsx"
    ]

    existing_files = [
        path for path in candidates
        if path.is_file()
    ]

    if not existing_files:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    if len(existing_files) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple datasets found for file_id"
        )

    file_path = existing_files[0]

    try:
        if file_path.suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

    except (ValueError, UnicodeError, pd.errors.ParserError, OSError):
        raise HTTPException(
            status_code=400,
            detail="Cannot read dataset"
        )

    return df, file_path


# STEP 2: Profile entire dataset
@router.get("/profile/{file_id}")
def get_dataset_profile(file_id: UUID):

    df, file_path = load_dataset(file_id)

    result = generate_profile(
        df=df,
        file_id=str(file_id),
        filename=file_path.name
    )

    return result


# STEP 3: Profile a single column
@router.get("/profile/{file_id}/{col_name}")
def get_column_profile(
    file_id: UUID,
    col_name: str
):

    df, _ = load_dataset(file_id)

    if col_name not in df.columns:
        raise HTTPException(
            status_code=404,
            detail=f"Column '{col_name}' not found"
        )

    result = profile_single_column(
        df=df,
        col_name=col_name
    )

    return result
