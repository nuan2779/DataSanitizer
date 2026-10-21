
import importlib
from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app

upload_module = importlib.import_module("backend.routers.upload")
clean_module = importlib.import_module("backend.routers.clean")
download_module = importlib.import_module("backend.routers.download")


def test_real_cleaning_pipeline(tmp_path, monkeypatch):

    # STEP 1: Temporary folders
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    raw_dir.mkdir()
    processed_dir.mkdir()

    monkeypatch.setattr(upload_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(download_module, "PROCESSED_DIR", processed_dir)

    client = TestClient(app)

    # STEP 2: Sample CSV with a missing value
    csv_data = (
        b"Name,Age,Score\n"
        b"An,20,8.5\n"
        b"Binh,,7.0\n"
        b"Chi,21,9.0\n"
    )

    # STEP 3: Upload
    response = client.post(
        "/api/upload",
        files={
            "file": ("students.csv", csv_data, "text/csv")
        }
    )

    assert response.status_code == 200

    file_id = response.json()["file_id"]
    print("UPLOAD PASSED")

    # STEP 4: Clean using the real Median algorithm
    options = {
        "file_id": file_id,
        "missing_method": "median",
        "outlier_method": "none",
        "encoding_method": "none",
        "scaling_method": "none"
    }

    response = client.post("/api/clean", json=options)

    assert response.status_code == 200
    print("CLEAN API PASSED")

    # STEP 5: Verify saved processed data
    output_file = processed_dir / f"{file_id}.csv"

    assert output_file.exists()

    cleaned_df = pd.read_csv(output_file)

    assert cleaned_df["Age"].isna().sum() == 0
    assert cleaned_df.loc[1, "Age"] == 20.5

    print("REAL MEDIAN ALGORITHM PASSED")

    # STEP 6: Download CSV
    response = client.get(
        f"/api/download/{file_id}?file_format=csv"
    )

    assert response.status_code == 200

    downloaded_df = pd.read_csv(BytesIO(response.content))

    assert downloaded_df.loc[1, "Age"] == 20.5

    print("CSV DOWNLOAD PASSED")

    # STEP 7: Download JSON
    response = client.get(
        f"/api/download/{file_id}?file_format=json"
    )

    assert response.status_code == 200

    json_data = response.json()

    assert len(json_data) == 3
    assert json_data[1]["Age"] == 20.5

    print("JSON DOWNLOAD PASSED")

    print("\nREAL END-TO-END PIPELINE PASSED!")
