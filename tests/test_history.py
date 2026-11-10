import importlib

from backend.database import fetch_all

upload_module = importlib.import_module("backend.routers.upload")
clean_module = importlib.import_module("backend.routers.clean")
history_module = importlib.import_module("backend.routers.history")


def test_clean_is_saved_to_authenticated_user_history(isolated_client, tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()

    monkeypatch.setattr(upload_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(history_module, "PROCESSED_DIR", processed_dir)

    client = isolated_client
    registered = client.post(
        "/api/auth/register",
        json={"username": "history_user", "email": "history@example.com", "password": "HistoryPass123"},
    )
    assert registered.status_code == 201

    uploaded = client.post(
        "/api/upload",
        files={"file": ("students.csv", b"Name,Age\nAn,20\nBinh,\nChi,22\n", "text/csv")},
    )
    assert uploaded.status_code == 200
    file_id = uploaded.json()["file_id"]

    cleaned = client.post(
        "/api/clean",
        json={
            "file_id": file_id,
            "pipeline": [
                {"step_type": "missing_values", "config": {"columns": ["Age"], "strategy": "median"}}
            ],
        },
    )
    assert cleaned.status_code == 200, cleaned.text
    history_id = cleaned.json()["history_id"]
    assert history_id is not None

    listing = client.get("/api/history")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    item = listing.json()["history"][0]
    assert item["filename"] == "students.csv"
    assert item["file_id"] == file_id

    detail = client.get(f"/api/history/{history_id}")
    assert detail.status_code == 200
    assert detail.json()["history"]["stats"]["processed_data"]["rows"] == 3

    download = client.get(f"/api/history/{history_id}/download")
    assert download.status_code == 200
    assert b"Name,Age" in download.content


def test_anonymous_clean_does_not_create_personal_history(isolated_client, tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()
    monkeypatch.setattr(upload_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_module, "PROCESSED_DIR", processed_dir)

    uploaded = isolated_client.post(
        "/api/upload",
        files={"file": ("offline.csv", b"Age\n20\n\n22\n", "text/csv")},
    )
    file_id = uploaded.json()["file_id"]
    cleaned = isolated_client.post(
        "/api/clean",
        json={"file_id": file_id, "pipeline": [{"step_type": "standardize_nulls", "config": {}}]},
    )
    assert cleaned.status_code == 200
    assert cleaned.json()["history_id"] is None
    assert fetch_all("SELECT id FROM pipeline_history") == []


def test_user_cannot_read_another_users_history(isolated_client, tmp_path, monkeypatch):
    from backend.database import execute_query
    import json

    client = isolated_client
    first = client.post(
        "/api/auth/register",
        json={"username": "owner_user", "email": "owner@example.com", "password": "OwnerPass123"},
    )
    assert first.status_code == 201
    owner_id = first.json()["user"]["id"]
    history_id = execute_query(
        "INSERT INTO pipeline_history (user_id, filename, file_id, stats_json) VALUES (?, ?, ?, ?)",
        (owner_id, "private.csv", "00000000-0000-0000-0000-000000000001", json.dumps({})),
    )

    client.post("/api/auth/logout")
    second = client.post(
        "/api/auth/register",
        json={"username": "other_user", "email": "other@example.com", "password": "OtherPass123"},
    )
    assert second.status_code == 201
    assert client.get(f"/api/history/{history_id}").status_code == 404
    assert client.get("/api/history").json()["total"] == 0
