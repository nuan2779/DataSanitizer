
from fastapi.testclient import TestClient
from backend.main import app
import importlib

upload_module = importlib.import_module(
    "backend.routers.upload"
)
client = TestClient(app)


def test_empty_upload():
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "empty.csv",
                b"",
                "text/csv"
            )
        }
    )

    assert response.status_code == 400


def test_fake_excel():
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "fake.xlsx",
                b"This is not an Excel file",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        }
    )

    assert response.status_code == 400

def test_large_upload(tmp_path, monkeypatch):

    # Use temporary folder instead of real data/raw
    monkeypatch.setattr(
        upload_module,
        "RAW_DIR",
        tmp_path
    )

    # Create file larger than 10 MiB
    large_file = b"A" * (10 * 1024 * 1024 + 1)

    # Send file to Upload API
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "large.csv",
                large_file,
                "text/csv"
            )
        }
    )

    # Server must reject oversized file
    assert response.status_code == 413

    # File must not be saved
    assert list(tmp_path.iterdir()) == []
