import pandas as pd

from backend.services.pipeline_runner import run_selected_pipeline


def test_ml_mode_splits_even_when_pipeline_only_imputes_missing_values():
    frame = pd.DataFrame({"age": [10.0, 20.0, None, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]})
    _, audit, train_df, test_df = run_selected_pipeline(
        frame,
        [{"step_type": "missing_values", "config": {"columns": ["age"], "strategy": "median"}}],
        is_ml_mode=True,
        test_size=0.2,
        return_split_dfs=True,
    )
    assert audit["is_split"] is True
    assert len(train_df) == 8
    assert len(test_df) == 2
    assert train_df["age"].isna().sum() == 0
    assert test_df["age"].isna().sum() == 0


def test_ml_mode_always_returns_split_for_deterministic_only_pipeline():
    frame = pd.DataFrame({"amount": ["$1.00", "$2.00", "$3.00", "$4.00", "$5.00"]})
    _, audit, train_df, test_df = run_selected_pipeline(
        frame,
        [{"step_type": "clean_numeric", "config": {"columns": ["amount"]}}],
        is_ml_mode=True,
        test_size=0.2,
        return_split_dfs=True,
    )
    assert audit["is_split"] is True
    assert len(train_df) == 4
    assert len(test_df) == 1


def test_builtin_recipe_style_empty_column_selection_is_resolved():
    frame = pd.DataFrame({"age": [10.0, None, 30.0, 40.0], "city": ["A", "B", "A", "C"]})
    cleaned, audit = run_selected_pipeline(
        frame,
        [
            {"step_type": "missing_values", "config": {"columns": [], "strategy": "median"}},
            {"step_type": "encoding", "config": {"columns": [], "method": "one_hot"}},
            {"step_type": "scaling", "config": {"columns": [], "method": "min_max"}},
        ],
    )
    assert cleaned["age"].isna().sum() == 0
    assert any(column.startswith("city_") for column in cleaned.columns)
    assert audit["total_steps"] == 3
