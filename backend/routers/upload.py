
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from uuid import uuid4
from io import BytesIO
from zipfile import is_zipfile

router = APIRouter()

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

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

    return {
        "message": "Upload successful",
        "file_id": file_id,
        "filename": file.filename
    }
