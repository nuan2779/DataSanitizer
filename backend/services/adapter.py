
import pandas as pd
from backend.services.cleaner import DataCleaner


def clean_dataframe(
    df: pd.DataFrame,
    options: dict
) -> pd.DataFrame:

    # STEP 1: Get cleaning options
    missing_method = options.get("missing_method", "median")
    outlier_method = options.get("outlier_method", "none")
    encoding_method = options.get("encoding_method", "none")
    scaling_method = options.get("scaling_method", "none")

    # STEP 2: Validate methods
    if missing_method not in [
        "mean",
        "median",
        "mode",
        "drop_rows",
        "drop_columns",
         "interpolation"
    ]:
        raise ValueError(
            "Unsupported missing value method"
        )



    if outlier_method not in ["none", "iqr", "zscore"]:
        raise ValueError("Unsupported outlier method")


    if encoding_method not in ["none", "onehot", "label"]:
        raise ValueError("Unsupported encoding method")

    if scaling_method not in ["none", "minmax", "standard"]:
        raise ValueError("Unsupported scaling method")

    # STEP 3: Identify columns
    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = df.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()

    pipeline_steps = []
    # STEP 4: Missing value handling

    strategy_mapping = {
        "mean": "mean",
        "median": "median",
        "mode": "mode",
        "drop_rows": "drop_row",
        "drop_columns": "drop_col",
        "interpolation": "interpolate"
    }

    # Find columns containing missing values
    missing_columns = [
        col for col in df.columns
        if df[col].isna().any()
    ]

    # Select columns for each strategy
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

    # Create missing value pipeline step
    if target_columns:

        pipeline_steps.append({
            "step_type": "missing_values",
            "config": {
                "columns": target_columns,
                "strategy": strategy_mapping[missing_method]
            }
        })

    # Update columns when using Drop Columns
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



    # STEP 5: Outlier handling
    if outlier_method in ["iqr", "zscore"]:

        if not numeric_columns:
            raise ValueError("No numeric columns for outlier handling")

        method_mapping = {
            "iqr": "iqr",
            "zscore": "z_score"
        }

        threshold = (
            1.5 if outlier_method == "iqr" else 3.0
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

    # STEP 6: Categorical Encoding

    if encoding_method in ["onehot", "label"]:

        if not categorical_columns:
            raise ValueError(
                "No categorical columns for encoding"
            )

        method_mapping = {
            "onehot": "one_hot",
            "label": "label"
        }

        pipeline_steps.append({
            "step_type": "encoding",
            "config": {
                "columns": categorical_columns,
                "method": method_mapping[encoding_method]
            }
        })

    # STEP 7: Feature Scaling
    if scaling_method in ["minmax", "standard"]:

        if not numeric_columns:
            raise ValueError("No numeric columns for scaling")

        pipeline_steps.append({
            "step_type": "scaling",
            "config": {
                "columns": numeric_columns,
                "method": scaling_method
            }
        })

    # STEP 8: Execute DataCleaner
    cleaner = DataCleaner(df.copy())

    cleaned_df = cleaner.execute_pipeline(pipeline_steps)

    # STEP 9: Validate output
    if not isinstance(cleaned_df, pd.DataFrame):
        raise TypeError("DataCleaner must return a DataFrame")

    return cleaned_df
