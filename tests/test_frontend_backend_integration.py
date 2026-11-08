import os
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_kaggle_samples_api():
    # 1. Lay danh muc mau
    res = client.get("/api/samples")
    assert res.status_code == 200
    catalog = res.json()["samples"]
    assert len(catalog) == 4
    sample_ids = [s["id"] for s in catalog]
    assert "melbourne" in sample_ids
    assert "titanic" in sample_ids
    assert "iris" in sample_ids
    assert "churn" in sample_ids

    # 2. Nap 1-click dataset Iris
    load_res = client.post("/api/samples/iris/load")
    assert load_res.status_code == 200
    data = load_res.json()
    assert "file_id" in data
    assert data["filename"] == "iris.csv"

def test_ml_mode_pipeline_execution_and_split_download():
    # 1. Nap dataset iris
    load_res = client.post("/api/samples/iris/load")
    file_id = load_res.json()["file_id"]

    # 2. Chay pipeline o che do Machine Learning
    clean_payload = {
        "file_id": file_id,
        "purpose": "ml",
        "train_ratio": 0.8,
        "pipeline": [
            {"step_type": "standardize_nulls", "config": {}},
            {"step_type": "scaling", "config": {"columns": ["sepal_length"], "method": "min_max"}}
        ]
    }
    clean_res = client.post("/api/clean", json=clean_payload)
    assert clean_res.status_code == 200
    clean_data = clean_res.json()
    assert clean_data["purpose"] == "ml"
    assert "ml_split" in clean_data
    assert clean_data["ml_split"]["train_rows"] == 120
    assert clean_data["ml_split"]["test_rows"] == 30

    # 3. Tai file train_cleaned qua suffix
    train_dl = client.get(f"/api/download/{file_id}?file_format=csv&suffix=train_cleaned")
    assert train_dl.status_code == 200
    assert "cleaned_" in train_dl.headers["content-disposition"]
    assert "train_cleaned.csv" in train_dl.headers["content-disposition"]

    # 4. Tai file test_cleaned qua suffix
    test_dl = client.get(f"/api/download/{file_id}?file_format=csv&suffix=test_cleaned")
    assert test_dl.status_code == 200
    assert "test_cleaned.csv" in test_dl.headers["content-disposition"]

def test_benchmark_api_compatibility():
    # 1. Nap dataset titanic
    load_res = client.post("/api/samples/titanic/load")
    file_id = load_res.json()["file_id"]

    # 2. Goi API benchmark
    bench_res = client.get(f"/api/benchmark/{file_id}")
    assert bench_res.status_code == 200
    data = bench_res.json()
    # Kiem tra truong ml_readiness_score ma frontend cua Van yeu cau
    assert "ml_readiness_score" in data
    assert "overall_score" in data
    assert 0 <= data["ml_readiness_score"] <= 100
    assert "breakdown" in data
