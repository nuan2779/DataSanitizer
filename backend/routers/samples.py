"""One-click provisioning of the bundled sample datasets."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/samples", tags=["Sample Datasets"])
BASE_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DIR = BASE_DIR / "data" / "samples"
RAW_DIR = BASE_DIR / "data" / "raw"

SAMPLE_MAP = {
    "melbourne": {
        "file": "melbourne_housing.csv",
        "title": "Melbourne Housing",
        "description": "Dữ liệu nhà ở với nhiều kiểu dữ liệu và giá trị cần tiền xử lý",
        "task": "Regression / Valuation",
    },
    "titanic": {
        "file": "titanic.csv",
        "title": "Titanic Disaster",
        "description": "Dữ liệu hành khách với các giá trị khuyết thiếu",
        "task": "Binary Classification",
    },
    "iris": {
        "file": "iris.csv",
        "title": "Iris Species",
        "description": "Dữ liệu số học dùng cho bài toán phân loại ba loài hoa Iris",
        "task": "Multi-class Classification",
    },
    "churn": {
        "file": "customer_churn.csv",
        "title": "Customer Churn",
        "description": "Dữ liệu khách hàng viễn thông dùng cho bài toán dự đoán rời bỏ",
        "task": "Binary Classification",
    },
}


def _count_csv_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    except (OSError, UnicodeError, csv.Error):
        return None


@router.get("")
def get_sample_catalog():
    """Tra ve danh muc 4 bo du lieu mau thuc nghiem (Benchmark Datasets)."""
    catalog = []
    for sample_id, info in SAMPLE_MAP.items():
        file_path = SAMPLES_DIR / info["file"]
        available = file_path.is_file()
        catalog.append(
            {
                "id": sample_id,
                "title": info["title"],
                "filename": info["file"],
                "description": info["description"],
                "task": info["task"],
                "available": available,
                "rows": _count_csv_rows(file_path) if available else None,
                "size_bytes": file_path.stat().st_size if available else None,
            }
        )
    return {"samples": catalog}


@router.post("/{sample_id}/load")
def load_sample_dataset(sample_id: str):
    """Copy one bundled CSV into raw/ under a new UUID for a fresh session."""
    normalized_id = sample_id.strip().lower()
    info = SAMPLE_MAP.get(normalized_id)
    if info is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sample '{sample_id}' not found. Available samples: {list(SAMPLE_MAP)}",
        )

    source_path = SAMPLES_DIR / info["file"]
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample file '{info['file']}' is missing")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid4()
    destination = RAW_DIR / f"{file_id}.csv"
    metadata_path = RAW_DIR / f"{file_id}.meta.json"

    try:
        shutil.copyfile(source_path, destination)
        metadata_path.write_text(
            json.dumps(
                {
                    "filename": info["file"],
                    "sample_id": normalized_id,
                    "title": info["title"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        destination.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not provision sample dataset") from exc

    return {
        "file_id": str(file_id),
        "filename": info["file"],
        "sample_id": normalized_id,
        "rows": _count_csv_rows(destination),
        "message": f"Successfully provisioned sample dataset: {info['title']}",
    }
