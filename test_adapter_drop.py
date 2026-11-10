
import pandas as pd
from backend.services.adapter import clean_dataframe


def get_options(method, scaling="none"):
    return {
        "missing_method": method,
        "outlier_method": "none",
        "encoding_method": "none",
        "scaling_method": scaling
    }


# TEST 1: DROP ROWS
df_rows = pd.DataFrame({
    "Name": ["An", "Binh", "Chi", "Dung"],
    "Age": [20, None, 22, 23],
    "Score": [8.5, 7.0, None, 8.0]
})

print("=== BEFORE DROP ROWS ===")
print(df_rows)

result_rows = clean_dataframe(
    df_rows,
    get_options("drop_rows")
)

print("\n=== AFTER DROP ROWS ===")
print(result_rows)

assert len(result_rows) == 2
assert result_rows["Name"].tolist() == ["An", "Dung"]
assert result_rows.isna().sum().sum() == 0

print("\nDROP ROWS TEST PASSED!")


# TEST 2: DROP COLUMNS
df_cols = pd.DataFrame({
    "Name": ["An", "Binh", "Chi", "Dung"],
    "Age": [20, None, 22, 23],
    "Score": [8.5, 7.0, 9.0, 8.0]
})

print("\n=== BEFORE DROP COLUMNS ===")
print(df_cols)

result_cols = clean_dataframe(
    df_cols,
    get_options("drop_columns")
)

print("\n=== AFTER DROP COLUMNS ===")
print(result_cols)

assert "Age" not in result_cols.columns
assert "Name" in result_cols.columns
assert "Score" in result_cols.columns
assert len(result_cols) == 4

print("\nDROP COLUMNS TEST PASSED!")


# TEST 3: DROP COLUMNS + SCALING
result_scaled = clean_dataframe(
    df_cols,
    get_options("drop_columns", "minmax")
)

assert "Age" not in result_scaled.columns
assert result_scaled["Score"].min() == 0.0
assert result_scaled["Score"].max() == 1.0

print("\nDROP COLUMNS + SCALING TEST PASSED!")
