import asyncio
import json
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from backend.database import execute_query
from backend.services.benchmark import compute_data_quality_score
from backend.services.cleaner import DataCleaner
from backend.services.retention_guard import (
    cleanup_ephemeral_files,
    delete_ephemeral_dataset,
    get_persisted_file_ids,
)


def test_retention_score_no_double_penalty():
    """Hạng mục 3: Đảm bảo không phạt kép khi xóa trùng lặp hoặc dòng rác."""
    # 10 dòng ban đầu, trong đó có 5 dòng trùng lặp
    raw_df = pd.DataFrame({
        "num": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
        "cat": pd.Categorical(["A", "B", "C", "D", "E", "A", "B", "C", "D", "E"])
    })
    # Sau khi drop_duplicates, còn 5 dòng sạch
    cleaned_df = raw_df.drop_duplicates()
    assert len(cleaned_df) == 5

    # Tính điểm với legitimate_dropped_rows = 5
    score = compute_data_quality_score(
        cleaned_df,
        initial_rows=10,
        legitimate_dropped_rows=5
    )

    # Retention score phải đạt tối đa 25.0 điểm vì 5 dòng bị drop là hợp lệ
    assert score["breakdown"]["retention_score"] == 25.0
    assert score["breakdown"]["retention_rate"] == 100.0
    assert score["breakdown"]["legitimate_dropped_rows"] == 5
    assert score["overall_score"] == 100.0


def test_retention_score_penalizes_excessive_valid_data_loss():
    """Hạng mục 3: Vẫn phạt điểm nếu làm mất dữ liệu hợp lệ."""
    cleaned_df = pd.DataFrame({
        "num": [1, 2],
        "cat": pd.Categorical(["A", "B"])
    })
    # Ban đầu có 10 dòng hợp lệ, drop mất 8 dòng hợp lệ (legitimate_dropped_rows=0)
    score = compute_data_quality_score(cleaned_df, initial_rows=10, legitimate_dropped_rows=0)
    assert score["breakdown"]["retention_rate"] == 20.0
    assert score["breakdown"]["retention_score"] == 5.0  # 25.0 * 0.2


def test_cleaner_memory_optimization_no_intermediate_concat():
    """Hạng mục 2: Tái cấu trúc quản lý RAM, không pd.concat sau mỗi bước ML."""
    df = pd.DataFrame({
        "num": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        "cat": ["low", "low", "med", "med", "high", "high", "low", "med", "high", "low"]
    })
    cleaner = DataCleaner(df)
    cleaner.split_train_test(test_size=0.2, random_state=42)

    # Thực hiện encoding và scaling
    cleaner.encode_categorical(["cat"], method="label")
    cleaner.scale_features(["num"], method="standard")

    # Kiểm tra train_df và test_df đã được xử lý độc lập
    assert cleaner.train_df is not None
    assert cleaner.test_df is not None
    assert len(cleaner.train_df) == 8
    assert len(cleaner.test_df) == 2

    # Ghép lại duy nhất một lần qua sync_full_df
    synced_df = cleaner.sync_full_df()
    assert len(synced_df) == 10
    assert "cat" in synced_df.columns
    assert "num" in synced_df.columns


def test_ephemeral_file_deletion_and_retention_guard(isolated_client, tmp_path, monkeypatch):
    """Hạng mục 1: Zero Retention - Xóa tệp tạm thời khi kết thúc phiên Offline."""
    import backend.routers.clean as clean_router
    import backend.routers.download as download_router
    import backend.routers.upload as upload_router
    import backend.services.retention_guard as guard_module

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()

    monkeypatch.setattr(upload_router, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_router, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_router, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(download_router, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(guard_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(guard_module, "PROCESSED_DIR", processed_dir)

    client = isolated_client

    # 1. Upload file ở chế độ Offline (không đăng nhập)
    upload_res = client.post(
        "/api/upload",
        files={"file": ("offline_temp.csv", b"colA,colB\n1,2\n3,4\n", "text/csv")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    raw_file = raw_dir / f"{file_id}.csv"
    assert raw_file.is_file()

    # 2. Thực thi làm sạch
    clean_res = client.post(
        "/api/clean",
        json={"file_id": file_id, "pipeline": [{"step_type": "standardize_nulls", "config": {}}]},
    )
    assert clean_res.status_code == 200
    processed_file = processed_dir / f"{file_id}.csv"
    assert processed_file.is_file()

    # 3. Gọi DELETE /api/upload/{file_id} để xóa ngay (Zero Retention)
    del_res = client.delete(f"/api/upload/{file_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 4. Xác nhận đĩa cứng đã giải phóng hoàn toàn
    assert not raw_file.is_file()
    assert not processed_file.is_file()


def test_clean_pipeline_timeout_returns_408(isolated_client, tmp_path, monkeypatch):
    """Hạng mục 4: Tối ưu Web Concurrency - ngắt tiến trình và trả về HTTP 408 nếu quá timeout."""
    import backend.routers.clean as clean_router
    import time

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()

    monkeypatch.setattr(clean_router, "RAW_DIR", raw_dir)
    monkeypatch.setattr(clean_router, "PROCESSED_DIR", processed_dir)
    # Giảm timeout xuống 0.05 giây để test timeout phản hồi nhanh
    monkeypatch.setattr(clean_router, "PIPELINE_TIMEOUT_SECONDS", 0.05)

    client = isolated_client

    file_id = "00000000-0000-0000-0000-000000000099"
    raw_file = raw_dir / f"{file_id}.csv"
    raw_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    def mock_slow_runner(*args, **kwargs):
        time.sleep(0.2)  # Vượt quá 0.05s timeout
        return pd.DataFrame({"a": [1, 3], "b": [2, 4]}), {}

    monkeypatch.setattr(clean_router, "run_selected_pipeline", mock_slow_runner)

    res = client.post(
        "/api/clean",
        json={"file_id": file_id, "pipeline": [{"step_type": "standardize_nulls", "config": {}}]}
    )
    assert res.status_code == 408
    assert "timed out" in res.json()["detail"].lower()
