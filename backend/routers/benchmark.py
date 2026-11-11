from pathlib import Path
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.services.benchmark import compute_data_quality_score

router = APIRouter()

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


@router.get("/benchmark/{file_id}")
def get_benchmark_score(file_id: UUID):
    # Ưu tiên đọc file đã qua làm sạch trong processed/
    target_path = PROCESSED_DIR / f"{file_id}.csv"
    initial_rows = None
    legitimate_dropped = 0

    if not target_path.is_file():
        # Nếu chưa làm sạch, đọc file thô trong raw/
        for ext in [".csv", ".xlsx"]:
            raw_candidate = RAW_DIR / f"{file_id}{ext}"
            if raw_candidate.is_file():
                target_path = raw_candidate
                break

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Dataset not found for benchmark evaluation")

    try:
        if target_path.suffix == ".csv":
            df = pd.read_csv(target_path)
        else:
            df = pd.read_excel(target_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read dataset: {e}")

    # Lấy số dòng gốc và phát hiện số dòng rác/trùng lặp hợp lệ từ raw nếu có
    for ext in [".csv", ".xlsx"]:
        raw_path = RAW_DIR / f"{file_id}{ext}"
        if raw_path.is_file():
            try:
                raw_df = pd.read_csv(raw_path) if ext == ".csv" else pd.read_excel(raw_path)
                initial_rows = len(raw_df)
                raw_dups = int(raw_df.duplicated().sum())
                raw_all_nulls = int(raw_df.isnull().all(axis=1).sum())
                legitimate_dropped = raw_dups + raw_all_nulls
                break
            except Exception:
                pass

    return compute_data_quality_score(
        df,
        initial_rows=initial_rows,
        legitimate_dropped_rows=legitimate_dropped,
    )
