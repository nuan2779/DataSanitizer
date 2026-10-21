
import re
import pandas as pd

from backend.services.cleaner import DataCleaner


# 1. CURRENCY DETECTION

# Supported examples:
# $1,200.50
# 1,500 đ
# 2500 VND
# 2300

CURRENCY_FORMAT = re.compile(
    r"^\s*\$?\s*"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?"
    r"\s*(?:đ|₫|vnd|vnđ)?\s*$",
    re.IGNORECASE
)

CURRENCY_MARKER = re.compile(
    r"^\s*\$|(?:đ|₫|vnd|vnđ)\s*$",
    re.IGNORECASE
)

AMBIGUOUS_FORMAT = re.compile(
    r"^\s*\$?\s*\d{1,3}\.\d{3}"
    r"\s*(?:đ|₫|vnd|vnđ)?\s*$",
    re.IGNORECASE
)


def find_currency_columns(df: pd.DataFrame):
    """
    Detect currency-like columns without
    modifying ordinary categorical columns.
    """

    currency_columns = []

    object_columns = df.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    for col in object_columns:

        values = (
            df[col]
            .dropna()
            .astype(str)
            .str.strip()
        )

        if values.empty:
            continue

        valid_values = values.map(
            lambda x: bool(CURRENCY_FORMAT.fullmatch(x))
        )

        currency_markers = values.map(
            lambda x: bool(CURRENCY_MARKER.search(x))
        )

        # At least one value must be clearly
        # recognizable as currency.
        if not (
            valid_values.any()
            and currency_markers.any()
        ):
            continue

        # Reject mixed or unsupported formats
        # rather than silently corrupting data.
        if not valid_values.all():
            raise ValueError(
                f"Unsupported currency format in column: {col}"
            )

        if values.map(
            lambda x: bool(AMBIGUOUS_FORMAT.fullmatch(x))
        ).any():
            raise ValueError(
                f"Ambiguous decimal format in column: {col}"
            )

        currency_columns.append(col)

    return currency_columns


# 2. MAIN ADAPTER

def clean_dataframe(
    df: pd.DataFrame,
    options: dict
) -> pd.DataFrame:

    # STEP 1: Get cleaning options
    missing_method = options.get(
        "missing_method", "median"
    )

    outlier_method = options.get(
        "outlier_method", "none"
    )

    encoding_method = options.get(
        "encoding_method", "none"
    )

    scaling_method = options.get(
        "scaling_method", "none"
    )


    # STEP 2: Validate options


    valid_missing = [
        "mean",
        "median",
        "mode",
        "drop_rows",
        "drop_columns",
        "interpolation"
    ]

    if missing_method not in valid_missing:
        raise ValueError(
            "Unsupported missing value method"
        )

    if outlier_method not in [
        "none", "iqr", "zscore"
    ]:
        raise ValueError(
            "Unsupported outlier method"
        )

    if encoding_method not in [
        "none", "onehot", "label"
    ]:
        raise ValueError(
            "Unsupported encoding method"
        )

    if scaling_method not in [
        "none", "minmax", "standard"
    ]:
        raise ValueError(
            "Unsupported scaling method"
        )


    # STEP 3: Currency cleaning


    # Avoid modifying original DataFrame
    df = df.copy()
    cleaner = DataCleaner(df)
    df = cleaner.standardize_nulls().df
    # Detect currency columns
    currency_columns = find_currency_columns(df)

    if currency_columns:

        # DataCleaner's numeric cleaner handles
        # object dtype, so convert string/category
        # columns to object before processing.
        for col in currency_columns:
            df[col] = df[col].astype(object)

        currency_cleaner = DataCleaner(df)

        currency_pipeline = [
            {
                "step_type": "clean_numeric",
                "config": {
                    "columns": currency_columns
                }
            }
        ]

        df = currency_cleaner.execute_pipeline(
            currency_pipeline
        )

        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                "Currency cleaning must return a DataFrame"
            )

        # Verify that currency conversion worked
        for col in currency_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError(
                    f"Cannot convert currency column: {col}"
                )


    # STEP 4: Identify column types


    # Important: detect columns AFTER
    # currency conversion.

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()

    pipeline_steps = [{"step_type": "standardize_nulls", "config": {}},
{"step_type": "clean_numeric", "config": {"columns": numeric_columns}},]


    # STEP 5: Missing Values

    strategy_mapping = {
        "mean": "mean",
        "median": "median",
        "mode": "mode",
        "drop_rows": "drop_row",
        "drop_columns": "drop_col",
        "interpolate": "interpolate"
    }

    missing_columns = [
        col for col in df.columns
        if df[col].isna().any()
    ]

    if missing_method in [
        "mean",
        "median",
        "interpolation"
    ]:

        target_columns = [
            col for col in numeric_columns
            if col in missing_columns
        ]

    else:

        target_columns = missing_columns

    if target_columns:

        pipeline_steps.append({
            "step_type": "missing_values",
            "config": {
                "columns": target_columns,
                "strategy": strategy_mapping[missing_method]
            }
        })

    # Update columns after Drop Columns
    if missing_method == "drop_columns":

        remaining_columns = [
            col for col in df.columns
            if col not in target_columns
        ]

        if not remaining_columns:
            raise ValueError(
                "Drop Columns would remove all columns"
            )

        numeric_columns = [
            col for col in numeric_columns
            if col in remaining_columns
        ]

        categorical_columns = [
            col for col in categorical_columns
            if col in remaining_columns
        ]

    # STEP 6: Outlier Detection

    if outlier_method in ["iqr", "zscore"]:

        if not numeric_columns:
            raise ValueError(
                "No numeric columns for outlier detection"
            )

        method_mapping = {
            "iqr": "iqr",
            "zscore": "z_score"
        }

        threshold = (
            1.5 if outlier_method == "iqr"
            else 3.0
        )

        pipeline_steps.append({
            "step_type": "outlier",
            "config": {
                "columns": numeric_columns,
                "method": method_mapping[outlier_method],
                "threshold": threshold,
                "handling": "remove"
            }
        })

    # STEP 7: Encoding

    if encoding_method in ["onehot", "label"]:

        if not categorical_columns:
            raise ValueError(
                "No categorical columns for encoding"
            )

        encoding_mapping = {
            "onehot": "one_hot",
            "label": "label"
        }

        pipeline_steps.append({
            "step_type": "encoding",
            "config": {
                "columns": categorical_columns,
                "method": encoding_mapping[encoding_method]
            }
        })

    # STEP 8: Scaling

    if scaling_method in ["minmax", "standard"]:

        if not numeric_columns:
            raise ValueError(
                "No numeric columns for scaling"
            )

        pipeline_steps.append({
            "step_type": "scaling",
            "config": {
                "columns": numeric_columns,
                "method": scaling_method
            }
        })


    # STEP 9: Execute DataCleaner


    cleaner = DataCleaner(df.copy())

    cleaned_df = cleaner.execute_pipeline(
        pipeline_steps
    )

    if not isinstance(cleaned_df, pd.DataFrame):
        raise TypeError(
            "DataCleaner must return a DataFrame"
        )


    return cleaned_df
