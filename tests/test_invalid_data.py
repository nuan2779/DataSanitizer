
import importlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

clean_module = importlib.import_module(
    "backend.routers.clean"
)


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    folder = tmp_path / "raw"
    folder.mkdir()

    monkeypatch.setattr(
        clean_module,
        "RAW_DIR",
        folder
    )

    return folder


# TEST 1: Empty CSV
def test_empty_csv(raw_dir):

    file_id = str(uuid4())

    file_path = raw_dir / f"{file_id}.csv"
    file_path.write_bytes(b"")

    response = client.post(
        "/api/clean",
        json={"file_id": file_id}
    )

    assert response.status_code == 400


# TEST 2: Corrupted Excel file
def test_invalid_excel(raw_dir):

    file_id = str(uuid4())

    file_path = raw_dir / f"{file_id}.xlsx"

    file_path.write_bytes(b"PK\x03\x04broken")

    response = client.post(
        "/api/clean",
        json={"file_id": file_id}
    )

    assert response.status_code == 400
