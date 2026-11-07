import pandas as pd
import numpy as np
import pytest

from backend.services.cleaner import DataCleaner
from backend.services.pipeline_runner import run_selected_pipeline

def test_split_train_test_proportions():
    df = pd.DataFrame({
        "age": range(100),
        "city": ["Hanoi", "Danang", "Saigon", "Hue"] * 25
    })
    cleaner = DataCleaner(df)
    cleaner.split_train_test(test_size=0.25, random_state=42)

    assert cleaner.is_split is True
    assert len(cleaner.train_df) == 75
    assert len(cleaner.test_df) == 25
    summary = cleaner.get_audit_summary()
    assert summary["is_split"] is True
    assert summary["train_rows"] == 75
    assert summary["test_rows"] == 25

def test_onehot_encoding_anti_data_leakage_unseen_category():
    """
    Kiem tra: Neu tap Test xuat hien gia tri la ma tap Train chua tung co,
    OneHotEncoder phai bo qua (gan 0 cho toan bo dummy) va KHONG duoc sinh them cot moi
    gay ro ri vao tap Train!
    """
    # 8 dong dau la Train (chi co Hanoi va Danang)
    # 2 dong cuoi la Test (xuat hien CanTho la unseen category)
    df = pd.DataFrame({
        "city": ["Hanoi", "Danang", "Hanoi", "Danang", "Hanoi", "Danang", "Hanoi", "Danang", "CanTho", "CanTho"]
    })
    cleaner = DataCleaner(df)
    cleaner.split_train_test(test_size=0.2, random_state=42)

    # Co tinh dam bao tap Train khong co CanTho
    cleaner.train_df["city"] = ["Hanoi", "Danang", "Hanoi", "Danang", "Hanoi", "Danang", "Hanoi", "Danang"]
    cleaner.test_df["city"] = ["CanTho", "CanTho"]

    cleaner.encode_categorical(columns=["city"], method="one_hot")

    # Tap train chi co nhan Danang (vi drop_first=True, nhan dau tien bi drop)
    assert "city_CanTho" not in cleaner.train_df.columns
    assert "city_CanTho" not in cleaner.test_df.columns

    # Vi CanTho la nhan la, toan bo cot dummy tren tap Test phai bang 0
    onehot_cols = [c for c in cleaner.test_df.columns if c.startswith("city_")]
    for col in onehot_cols:
        assert (cleaner.test_df[col] == 0).all()

def test_label_encoding_anti_data_leakage_unseen_category():
    """
    Kiem tra: Nhan la o tap Test se duoc gan nhan Unknown (-1) de khong pha vo mapping
    cua tap Train.
    """
    df = pd.DataFrame({
        "category": ["A", "B", "A", "B", "A", "B", "A", "B", "X", "Y"]
    })
    cleaner = DataCleaner(df)
    cleaner.split_train_test(test_size=0.2, random_state=42)

    cleaner.train_df["category"] = ["A", "B", "A", "B", "A", "B", "A", "B"]
    cleaner.test_df["category"] = ["X", "Y"]

    cleaner.encode_categorical(columns=["category"], method="label")

    # A va B trong train nhan gia tri >= 0
    assert (cleaner.train_df["category"] >= 0).all()
    # X va Y la nhan la trong test, phai duoc gan -1
    assert (cleaner.test_df["category"] == -1).all()

def test_scaling_anti_data_leakage():
    """
    Kiem tra: Mean va Std phai duoc tinh TUYET DOI tu tap Train.
    Tap Test chi duoc transform theo thong so cua Train.
    """
    df = pd.DataFrame({
        "income": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 1000.0, 1000.0]
    })
    cleaner = DataCleaner(df)
    cleaner.split_train_test(test_size=0.2, random_state=42)

    cleaner.train_df["income"] = [10.0] * 8
    cleaner.test_df["income"] = [1000.0] * 2

    # Std cua train bang 0 (cac gia tri deu la 10.0) -> StandardScaler se giu nguyen hoac tra ve 0
    cleaner.scale_features(columns=["income"], method="min_max")

    # MinMaxScaler tren tap Train (toan 10.0) min=max=10 -> train bi scale thanh 0
    assert (cleaner.train_df["income"] == 0.0).all()
    # Nhung tap Test co gia tri 1000.0, vi dung min/max cua train nen gia tri test se khong bi danh dong vao phan phoi
    assert (cleaner.test_df["income"] > 0.0).all()

def test_pipeline_runner_ml_mode():
    df = pd.DataFrame({
        "age": [20, 30, 40, 50, 60, 25, 35, 45, 55, 65],
        "gender": ["M", "F", "M", "F", "M", "F", "M", "F", "M", "F"]
    })
    pipeline = [
        {"step_type": "standardize_nulls", "config": {}},
        {"step_type": "encoding", "config": {"columns": ["gender"], "method": "one_hot"}},
        {"step_type": "scaling", "config": {"columns": ["age"], "method": "min_max"}}
    ]

    clean_df, audit, train_df, test_df = run_selected_pipeline(
        df, pipeline, is_ml_mode=True, test_size=0.2, random_state=42, return_split_dfs=True
    )

    assert audit["is_split"] is True
    assert train_df is not None and len(train_df) == 8
    assert test_df is not None and len(test_df) == 2
    assert "gender_M" in train_df.columns
    assert "gender_M" in test_df.columns
