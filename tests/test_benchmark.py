import pandas as pd
import numpy as np
import pytest

from backend.services.benchmark import compute_data_quality_score

def test_data_quality_score_clean_data():
    df = pd.DataFrame({
        "num1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "num2": [10, 20, 30, 40, 50],
        "cat": pd.Categorical(["A", "B", "C", "A", "B"])
    })
    res = compute_data_quality_score(df, initial_rows=5)

    assert res["overall_score"] == 100.0
    assert res["badge_color"] == "success"
    assert res["breakdown"]["missing_cell_rate"] == 0.0
    assert res["breakdown"]["duplicate_rate"] == 0.0

def test_data_quality_score_with_nulls_and_duplicates():
    df = pd.DataFrame({
        "a": [1.0, np.nan, 1.0, np.nan],
        "b": ["x", "y", "x", "z"]
    })
    res = compute_data_quality_score(df, initial_rows=10)

    assert res["overall_score"] < 100.0
    assert res["breakdown"]["missing_cell_rate"] > 0
    assert res["breakdown"]["duplicate_rate"] > 0

def test_data_quality_score_empty_data():
    df = pd.DataFrame()
    res = compute_data_quality_score(df)
    assert res["overall_score"] == 0.0
    assert res["badge_color"] == "danger"

def test_data_quality_score_diagnostics():
    df = pd.DataFrame({
        "constant_col": [1, 1, 1, 1, 1],
        "varying_col": [1, 2, 3, 4, 5]
    })
    res = compute_data_quality_score(df)
    assert "constant_col" in res["diagnostics"]["zero_variance_columns"]
    assert "varying_col" not in res["diagnostics"]["zero_variance_columns"]
