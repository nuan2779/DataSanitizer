import json
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import is_zipfile

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.services.retention_guard import cleanup_ephemeral_files, delete_ephemeral_dataset

router = APIRouter()

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    # Kích hoạt quét dọn dẹp các tệp tạm đã hết hạn TTL (>30 phút)
    background_tasks.add_task(cleanup_ephemeral_files)

    extension = Path(file.filename or "").suffix.lower()

    if extension not in [".csv", ".xlsx"]:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and XLSX files are allowed"
        )

    file_id = str(uuid4())
    saved_path = RAW_DIR / f"{file_id}{extension}"

    content = await file.read(10 * 1024 * 1024 + 1)
    await file.close()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File must be 10 MB or smaller"
        )
    # Check empty file
    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    # Check Excel ZIP structure
    if extension == ".xlsx":
        if not is_zipfile(BytesIO(content)):
            raise HTTPException(
                status_code=400,
                detail="Invalid Excel file"
            )

    saved_path.write_bytes(content)
    metadata_path = RAW_DIR / f"{file_id}.meta.json"
    metadata_path.write_text(
        json.dumps({"filename": file.filename}, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "message": "Upload successful",
        "file_id": file_id,
        "filename": file.filename
    }


@router.delete("/upload/{file_id}")
def delete_dataset(file_id: UUID):
    """Xóa ngay lập tức tệp tạm trên máy chủ khi kết thúc phiên Offline (Zero Retention)."""
    clean_id = str(file_id)
    deleted = delete_ephemeral_dataset(clean_id)
    return {
        "message": "Ephemeral dataset cleaned successfully",
        "file_id": clean_id,
        "deleted": deleted
    }
