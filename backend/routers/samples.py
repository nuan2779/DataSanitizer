from fastapi import APIRouter, HTTPException
from pathlib import Path
import shutil
import uuid

router = APIRouter()

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_MAP = {
    "melbourne": {
        "file": "melbourne_housing.csv",
        "display_name": "melbourne_housing.csv",
        "title": "Melbourne Housing",
        "description": "34k dòng | Dự đoán giá nhà (dữ liệu hỗn hợp)",
        "task": "Regression / Valuation"
    },
    "titanic": {
        "file": "titanic.csv",
        "display_name": "titanic.csv",
        "title": "Titanic Disaster",
        "description": "891 dòng | Dự đoán sống sót (nhiều ô khuyết thiếu)",
        "task": "Binary Classification"
    },
    "iris": {
        "file": "iris.csv",
        "display_name": "iris.csv",
        "title": "Iris Species",
        "description": "150 dòng | Phân loại 3 loài hoa Iris chuẩn số học",
        "task": "Multi-class Classification"
    },
    "churn": {
        "file": "customer_churn.csv",
        "display_name": "customer_churn.csv",
        "title": "Customer Churn",
        "description": "7k dòng | Dự đoán khách hàng rời bỏ viễn thông",
        "task": "Binary Classification"
    }
}

@router.get("/samples")
def get_sample_catalog():
    """Tra ve danh muc 4 bo du lieu mau Kaggle Hub."""
    catalog = []
    for key, info in SAMPLE_MAP.items():
        file_path = SAMPLES_DIR / info["file"]
        catalog.append({
            "id": key,
            "title": info["title"],
            "filename": info["display_name"],
            "description": info["description"],
            "task": info["task"],
            "available": file_path.is_file()
        })
    return {"samples": catalog}

@router.post("/samples/{sample_id}/load")
def load_sample_dataset(sample_id: str):
    """Cap phat 1-click du lieu mau vao phien lam viec."""
    normalized_id = sample_id.lower().strip()
    if normalized_id not in SAMPLE_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Sample '{sample_id}' not found. Available samples: {list(SAMPLE_MAP.keys())}"
        )

    info = SAMPLE_MAP[normalized_id]
    src_path = SAMPLES_DIR / info["file"]
    if not src_path.is_file():
        raise HTTPException(status_code=500, detail=f"Sample file '{info['file']}' is missing on server.")

    # Sinh UUID moi va copy sang data/raw/
    new_file_id = uuid.uuid4()
    dst_path = RAW_DIR / f"{new_file_id}.csv"
    shutil.copyfile(src_path, dst_path)

    return {
        "file_id": str(new_file_id),
        "filename": info["display_name"],
        "message": f"Successfully provisioned sample dataset: {info['title']}"
    }
