"""Execute the ordered pipeline submitted by the web UI and retain audit details.

The original DataCleaner implementation stays unchanged.  This layer validates
user-selected columns/methods and safely handles currency-like strings.
"""
from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from backend.services.cleaner import DataCleaner

# Clear, documented US-style separators; ambiguous locale formats are rejected.
_MONEY = re.compile(
    r"^\s*([+-]?)\s*\$?\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(?:đ|₫|vnd|vnđ)?\s*$",
    re.IGNORECASE,
)
_AMBIGUOUS = re.compile(
    r"^\s*[+-]?\s*\$?\s*\d{1,3}\.\d{3}\s*(?:đ|₫|vnd|vnđ)\s*$",
    re.IGNORECASE,
)
_ALLOWED = {"standardize_nulls", "clean_numeric", "missing_values", "outlier", "encoding", "scaling", "round"}


def _selected_columns(df: pd.DataFrame, config: dict, *, allow_all: bool = False) -> list[str]:
    columns = config.get("columns")
    if columns is None and allow_all:
        return df.columns.tolist()
    if not isinstance(columns, list) or not columns or not all(isinstance(x, str) for x in columns):
        raise ValueError("Select at least one column for this step")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Columns not found at this stage: {', '.join(missing)}")
    return columns


def _convert_numeric_column(series: pd.Series, col_name: str) -> pd.Series:
    # Existing numeric values remain intact, including negative values.
    if pd.api.types.is_numeric_dtype(series):
        return series
    converted = []
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


def run_selected_pipeline(df: pd.DataFrame, pipeline: list[dict[str, Any]]):
    """Return (clean_dataframe, DataCleaner audit summary)."""
    cleaner = DataCleaner(df)
    if not pipeline:
        raise ValueError("Pipeline must contain at least one step")

    for index, step in enumerate(pipeline, start=1):
        kind = step.get("step_type")
        config = step.get("config", {})
        if kind not in _ALLOWED or not isinstance(config, dict):
            raise ValueError(f"Unsupported pipeline step #{index}: {kind}")

        if kind == "standardize_nulls":
            cleaner.standardize_nulls()
            continue

        # With no selection, Missing Values defaults to numeric columns for
        # numeric-only strategies, and all columns for mode/drop/constant.
        if kind == "missing_values" and config.get("columns") is None and config.get("strategy", "mean") in {"mean", "median", "interpolate"}:
            columns = cleaner.df.select_dtypes(include="number").columns.tolist()
            if not columns:
                raise ValueError("No numeric columns are available for this method")
        else:
            columns = _selected_columns(cleaner.df, config, allow_all=(kind == "missing_values"))

        if kind == "clean_numeric":
            for col in columns:
                cleaner.df[col] = _convert_numeric_column(cleaner.df[col], col)
            cleaner._log("clean_numeric", f"Converted selected numeric/currency columns: {columns}")
            continue

        if kind == "missing_values":
            method = config.get("strategy", "mean")
            if method not in {"mean", "median", "mode", "interpolate", "drop_row", "drop_col", "constant"}:
                raise ValueError(f"Unsupported missing value strategy: {method}")
            if method in {"mean", "median", "interpolate"}:
                invalid = [c for c in columns if not pd.api.types.is_numeric_dtype(cleaner.df[c])]
                if invalid:
                    raise ValueError(f"{method} requires numeric columns: {invalid}")
            if method == "drop_col" and len(columns) == len(cleaner.df.columns):
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
            if any(not pd.api.types.is_numeric_dtype(cleaner.df[c]) for c in columns):
                raise ValueError("Outlier detection requires numeric columns")
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
            if any(not pd.api.types.is_numeric_dtype(cleaner.df[c]) for c in columns):
                raise ValueError("Scaling requires numeric columns")
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

    return cleaner.df, cleaner.get_audit_summary()
