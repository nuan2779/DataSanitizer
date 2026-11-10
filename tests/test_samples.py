from pathlib import Path

import backend.routers.samples as samples_router


def test_sample_catalog_lists_four_available_datasets(isolated_client):
    response = isolated_client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert {item["id"] for item in samples} == {"melbourne", "titanic", "iris", "churn"}
    assert all(item["available"] for item in samples)
    assert all(item["rows"] and item["rows"] > 0 for item in samples)


def test_load_sample_creates_unique_raw_file_and_metadata(isolated_client, tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    monkeypatch.setattr(samples_router, "RAW_DIR", raw_dir)

    response = isolated_client.post("/api/samples/iris/load")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["sample_id"] == "iris"
    assert data["filename"] == "iris.csv"

    copied = raw_dir / f"{data['file_id']}.csv"
    metadata = raw_dir / f"{data['file_id']}.meta.json"
    assert copied.is_file()
    assert metadata.is_file()
    assert metadata.read_text(encoding="utf-8").find("iris.csv") >= 0


def test_unknown_or_missing_sample_returns_404(isolated_client):
    assert isolated_client.post("/api/samples/not-a-sample/load").status_code == 404
