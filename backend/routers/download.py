
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import UUID
import pandas as pd
from typing import Literal
from fastapi.responses import Response
router = APIRouter()

PROCESSED_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
)
@router.get("/download/{file_id}")
def download_file(
    file_id: UUID,
    file_format: Literal["csv", "json"] = "csv"
):

    # Step 1: Find processed file
    file_path = PROCESSED_DIR / f"{file_id}.csv"

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Processed file not found"
        )

    # Step 2: Download as CSV
    if file_format == "csv":
        return FileResponse(
            path=file_path,
            media_type="text/csv",
            filename=f"cleaned_{file_id}.csv"
        )

    # Step 3: Convert CSV to JSON
    try:
        df = pd.read_csv(file_path)

        json_data = df.to_json(
            orient="records",
            force_ascii=False
        )

    except (ValueError, OSError, pd.errors.ParserError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Cannot export JSON: {error}"
        )

    # Step 4: Return downloadable JSON
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition":
            f'attachment; filename="cleaned_{file_id}.json"'
        }
    )