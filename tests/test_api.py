
from fastapi.testclient import TestClient
from backend.main import app
from uuid import uuid4

# Create a test client
client = TestClient(app)


# TEST 1: Check Backend
def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "DataSanitizer Backend is running"
    )


# TEST 2: Reject invalid file extension
def test_invalid_upload():
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "test.txt",
                b"Hello World",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400


# TEST 3: Reject invalid cleaning method
def test_invalid_clean_method():
    data = {
        "file_id": str(uuid4()),
        "missing_method": "banana",
        "outlier_method": "iqr",
        "encoding_method": "onehot",
        "scaling_method": "standard"
    }

    response = client.post(
        "/api/clean",
        json=data
    )

    assert response.status_code == 422


# TEST 4: Download nonexistent file
def test_file_not_found():
    fake_id = str(uuid4())

    response = client.get(
        f"/api/download/{fake_id}"
    )

    assert response.status_code == 404
