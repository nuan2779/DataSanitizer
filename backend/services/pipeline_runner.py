"""Validate and execute ordered EDA or Train/Test cleaning pipelines.

The DataCleaner class remains the source of truth for transformations. This
orchestration layer selects sensible default columns, validates configuration,
and makes sure ML-mode transformations that learn statistics run only after the
Train/Test split has been created.
"""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd

from backend.services.cleaner import DataCleaner

_MONEY = re.compile(
    r"^\s*([+-]?)\s*\$?\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:đ|₫|vnd|vnđ)?\s*$",
    re.IGNORECASE,
)
_AMBIGUOUS = re.compile(
    r"^\s*[+-]?\s*\$?\s*\d{1,3}\.\d{3}\s*(?:đ|₫|vnd|vnđ)\s*$",
    re.IGNORECASE,
)
_ALLOWED = {
    "standardize_nulls",
    "clean_numeric",
    "missing_values",
    "outlier",
    "encoding",
    "scaling",
    "round",
    "drop_duplicates",
    "optimize_memory",
}
# These steps estimate values/distributions from data. In ML mode, split before
# executing them so their statistics can be learned from Train only.
_SPLIT_BEFORE = {"missing_values", "outlier", "encoding", "scaling"}


def _convert_numeric_column(series: pd.Series, col_name: str) -> pd.Series:
    """Convert plain numbers and unambiguous currency strings to float."""
    if pd.api.types.is_numeric_dtype(series):
        return series

    converted: list[float] = []
    for value in series:
        if pd.isna(value):
            converted.append(float("nan"))
            continue
        text = str(value).strip()
        if text in {"", "?", "N/A", "NA", "null", "NULL"}:
            converted.append(float("nan"))
            continue
        if _AMBIGUOUS.fullmatch(text):
            raise ValueError(f"Ambiguous currency format in column '{col_name}': {text}")
        match = _MONEY.fullmatch(text)
        if not match:
            raise ValueError(f"Non-numeric value in selected column '{col_name}': {text[:60]}")
        number = float(match.group(2).replace(",", ""))
        if match.group(1) == "-":
            number = -number
        if not math.isfinite(number):
            raise ValueError(f"Non-finite numeric value in column '{col_name}'")
        converted.append(number)
    return pd.Series(converted, index=series.index, dtype="float64")


def _auto_columns(df: pd.DataFrame, kind: str, config: dict[str, Any]) -> list[str]:
    """Resolve empty/missing column selections for built-in recipes and UI presets."""
    if kind == "missing_values":
        strategy = config.get("strategy", "mean")
        if strategy in {"mean", "median", "interpolate"}:
            return df.select_dtypes(include="number").columns.tolist()
        return df.columns.tolist()
    if kind in {"outlier", "scaling", "round"}:
        return df.select_dtypes(include="number").columns.tolist()
    if kind == "encoding":
        return df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    if kind == "clean_numeric":
        candidates: list[str] = []
        for column in df.select_dtypes(include=["object", "string"]).columns:
            try:
                converted = _convert_numeric_column(df[column], str(column))
            except ValueError:
                continue
            if converted.notna().any():
                candidates.append(str(column))
        return candidates
    return []


def _selected_columns(df: pd.DataFrame, config: dict[str, Any], kind: str) -> list[str]:
    columns = config.get("columns")
    if columns is None or columns == []:
        columns = _auto_columns(df, kind, config)
        if not columns:
            raise ValueError(f"No suitable columns found automatically for '{kind}'")
    if not isinstance(columns, list) or not all(isinstance(x, str) for x in columns):
        raise ValueError("Columns must be a list of column names")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Columns not found at this stage: {', '.join(missing)}")
    return columns


def _optimize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the same conservative dtype reductions as DataCleaner.optimize_memory."""
    result = frame.copy()
    for column in result.columns:
        series = result[column]
        if pd.api.types.is_integer_dtype(series.dtype) and not series.isna().any():
            minimum, maximum = series.min(), series.max()
            if minimum >= np.iinfo(np.int8).min and maximum <= np.iinfo(np.int8).max:
                result[column] = series.astype(np.int8)
            elif minimum >= np.iinfo(np.int16).min and maximum <= np.iinfo(np.int16).max:
                result[column] = series.astype(np.int16)
            elif minimum >= np.iinfo(np.int32).min and maximum <= np.iinfo(np.int32).max:
                result[column] = series.astype(np.int32)
        elif pd.api.types.is_float_dtype(series.dtype):
            result[column] = series.astype(np.float32)
        elif series.dtype == "object":
            total = len(series)
            if total and (series.nunique(dropna=False) / total) < 0.5:
                result[column] = series.astype("category")
    return result


def run_selected_pipeline(
    df: pd.DataFrame,
    pipeline: list[dict[str, Any]],
    *,
    is_ml_mode: bool = False,
    test_size: float = 0.2,
    random_state: int = 42,
    return_split_dfs: bool = False,
):
    """Return the cleaned frame and audit summary; optionally return Train/Test.

    In ML mode, deterministic formatting steps may run before splitting. The
    split is created before the first statistical/learned transformation. If a
    pipeline contains only deterministic steps, the split is created at the end
    so callers still receive separate Train and Test datasets.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not pipeline:
        raise ValueError("Pipeline must contain at least one step")
    if is_ml_mode:
        try:
            test_size = float(test_size)
        except (TypeError, ValueError) as exc:
            raise ValueError("test_size must be numeric") from exc
        if not 0 < test_size < 1:
            raise ValueError("test_size must be between 0 and 1")
        if len(df) < 2:
            raise ValueError("At least two rows are required for Train/Test splitting")

    cleaner = DataCleaner(df)

    for index, step in enumerate(pipeline, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Pipeline step #{index} must be an object")
        kind = step.get("step_type")
        config = step.get("config", {})
        if kind not in _ALLOWED or not isinstance(config, dict):
            raise ValueError(f"Unsupported pipeline step #{index}: {kind}")

        if is_ml_mode and kind in _SPLIT_BEFORE and not cleaner.is_split:
            cleaner.split_train_test(test_size=test_size, random_state=random_state)

        if kind == "standardize_nulls":
            cleaner.standardize_nulls()
            continue

        if kind == "drop_duplicates":
            subset = config.get("subset")
            if subset in (None, []):
                subset = None
            elif not isinstance(subset, list) or not all(isinstance(col, str) for col in subset):
                raise ValueError("drop_duplicates subset must be a list of column names")
            elif any(col not in cleaner.df.columns for col in subset):
                raise ValueError("drop_duplicates contains an unknown column")
            keep = config.get("keep", "first")
            if keep not in {"first", "last", False}:
                raise ValueError("drop_duplicates keep must be 'first', 'last' or false")
            cleaner.drop_duplicates(subset=subset, keep=keep)
            continue

        if kind == "optimize_memory":
            if cleaner.is_split and cleaner.train_df is not None and cleaner.test_df is not None:
                cleaner.train_df = _optimize_frame(cleaner.train_df)
                cleaner.test_df = _optimize_frame(cleaner.test_df)
                cleaner.df = pd.concat([cleaner.train_df, cleaner.test_df], axis=0)
                cleaner._log("optimize_memory", "Optimized memory independently on Train and Test frames")
            else:
                cleaner.optimize_memory()
            continue

        columns = _selected_columns(cleaner.df, config, kind)

        if kind == "clean_numeric":
            cleaner.df.loc[:, columns] = pd.DataFrame(
                {col: _convert_numeric_column(cleaner.df[col], col) for col in columns},
                index=cleaner.df.index,
            )
            if cleaner.is_split and cleaner.train_df is not None and cleaner.test_df is not None:
                for col in columns:
                    cleaner.train_df[col] = _convert_numeric_column(cleaner.train_df[col], col)
                    cleaner.test_df[col] = _convert_numeric_column(cleaner.test_df[col], col)
                cleaner.df = pd.concat([cleaner.train_df, cleaner.test_df], axis=0)
            cleaner._log("clean_numeric", f"Converted selected numeric/currency columns: {columns}")
            continue

        if kind == "missing_values":
            method = config.get("strategy", "mean")
            if method in {"drop", "drop_rows"}:
                method = "drop_row"
            elif method in {"drop_cols"}:
                method = "drop_col"
            if method not in {"mean", "median", "mode", "interpolate", "drop_row", "drop_col", "constant"}:
                raise ValueError(f"Unsupported missing value strategy: {method}")
            if method in {"mean", "median", "interpolate"}:
                invalid = [col for col in columns if not pd.api.types.is_numeric_dtype(cleaner.df[col])]
                if invalid:
                    raise ValueError(f"{method} requires numeric columns: {invalid}")
            if method == "drop_col" and len(columns) >= len(cleaner.df.columns):
                raise ValueError("Cannot remove every column")
            if method == "constant" and config.get("fill_value") is None:
                raise ValueError("Constant filling requires fill_value")
            cleaner.handle_missing_values(columns, method, config.get("fill_value"))
            continue

        if kind == "outlier":
            method = config.get("method", "iqr")
            handling = config.get("handling", "remove")
            if method not in {"iqr", "z_score"} or handling not in {"remove", "cap"}:
                raise ValueError("Unsupported outlier method or handling")
            try:
                threshold = float(config.get("threshold", 1.5))
            except (TypeError, ValueError) as exc:
                raise ValueError("Outlier threshold must be numeric") from exc
            if not math.isfinite(threshold) or threshold <= 0:
                raise ValueError("Outlier threshold must be positive and finite")
            invalid = [col for col in columns if not pd.api.types.is_numeric_dtype(cleaner.df[col])]
            if invalid:
                raise ValueError(f"Outlier detection requires numeric columns: {invalid}")
            cleaner.handle_outliers(columns, method, threshold, handling)
            continue

        if kind == "encoding":
            method = config.get("method", "label")
            if method not in {"label", "one_hot"}:
                raise ValueError(f"Unsupported encoding method: {method}")
            cleaner.encode_categorical(columns, method)
            continue

        if kind == "scaling":
            method = config.get("method", "standard")
            if method not in {"standard", "min_max", "minmax"}:
                raise ValueError(f"Unsupported scaling method: {method}")
            invalid = [col for col in columns if not pd.api.types.is_numeric_dtype(cleaner.df[col])]
            if invalid:
                raise ValueError(f"Scaling requires numeric columns: {invalid}")
            cleaner.scale_features(columns, "standard" if method == "standard" else "min_max")
            continue

        if kind == "round":
            try:
                decimals = int(config.get("decimals", 0))
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid rounding decimals") from exc
            if not -10 <= decimals <= 10:
                raise ValueError("Rounding decimals must be between -10 and 10")
            cleaner.round_feature(columns, decimals, config.get("to_integer", False) is True)

    if is_ml_mode and not cleaner.is_split:
        cleaner.split_train_test(test_size=test_size, random_state=random_state)

    if return_split_dfs:
        return cleaner.df, cleaner.get_audit_summary(), cleaner.train_df, cleaner.test_df
    return cleaner.df, cleaner.get_audit_summary()
