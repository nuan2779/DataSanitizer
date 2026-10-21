
import importlib
from io import BytesIO

import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app


# Import API modules
upload_module = importlib.import_module(
    "backend.routers.upload"
)

clean_module = importlib.import_module(
    "backend.routers.clean"
)

download_module = importlib.import_module(
    "backend.routers.download"
)


def test_full_pipeline(tmp_path, monkeypatch):

    # STEP 1: Create temporary folders
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    raw_dir.mkdir()
    processed_dir.mkdir()

    monkeypatch.setattr(
        upload_module, "RAW_DIR", raw_dir
    )

    monkeypatch.setattr(
        clean_module, "RAW_DIR", raw_dir
    )

    monkeypatch.setattr(
        clean_module, "PROCESSED_DIR", processed_dir
    )

    monkeypatch.setattr(
        download_module, "PROCESSED_DIR", processed_dir
    )

    client = TestClient(app)

    # STEP 2: Create sample CSV
    csv_data = (
        b"Name,Age,Score\n"
        b"An,20,8.5\n"
        b"Binh,,7.0\n"
        b"Chi,21,9.0\n"
    )

    # STEP 3: Upload
    upload_response = client.post(
        "/api/upload",
        files={
            "file": (
                "students.csv",
                csv_data,
                "text/csv"
            )
        }
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["file_id"]

    assert (raw_dir / f"{file_id}.csv").is_file()

    print("UPLOAD PASSED")

    # STEP 4: Clean with real DataCleaner
    options = {
        "file_id": file_id,
        "missing_method": "median",
        "outlier_method": "iqr",
        "encoding_method": "onehot",
        "scaling_method": "standard"
    }

    clean_response = client.post(
        "/api/clean",
        json=options
    )

    assert clean_response.status_code == 200

    output_file = processed_dir / f"{file_id}.csv"

    assert output_file.is_file()

    print("CLEAN API PASSED")

    # STEP 5: Download processed CSV
    csv_response = client.get(
        f"/api/download/{file_id}?file_format=csv"
    )

    assert csv_response.status_code == 200

    cleaned_df = pd.read_csv(
        BytesIO(csv_response.content)
    )

    # Verify number of rows
    assert len(cleaned_df) == 3

    # Verify missing values handled
    assert cleaned_df["Age"].isna().sum() == 0

    # Verify One-Hot Encoding
    assert "Name" not in cleaned_df.columns

    assert any(
        col.startswith("Name_")
        for col in cleaned_df.columns
    )

    # Verify original numeric columns exist
    assert "Age" in cleaned_df.columns
    assert "Score" in cleaned_df.columns

    # Verify Standard Scaling
    assert np.isclose(
        cleaned_df["Age"].mean(),
        0.0,
        atol=1e-6
    )

    assert np.isclose(
        cleaned_df["Score"].mean(),
        0.0,
        atol=1e-6
    )

    print("CSV DOWNLOAD PASSED")
    print("MEDIAN PASSED")
    print("ONE-HOT PASSED")
    print("STANDARD SCALING PASSED")

    # STEP 6: Download JSON
    json_response = client.get(
        f"/api/download/{file_id}?file_format=json"
    )

    assert json_response.status_code == 200

    json_data = json_response.json()

    assert isinstance(json_data, list)
    assert len(json_data) == len(cleaned_df)

    # Verify JSON columns match processed CSV
    assert set(json_data[0].keys()) == set(
        cleaned_df.columns
    )

    print("JSON DOWNLOAD PASSED")

    # STEP 7: Final result
    print("\nFULL PIPELINE TEST PASSED!")
