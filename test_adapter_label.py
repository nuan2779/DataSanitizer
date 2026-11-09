
import pandas as pd
from pandas.api.types import is_numeric_dtype

from backend.services.adapter import clean_dataframe


# STEP 1: Create sample dataset
df = pd.DataFrame({
    "City": ["Hanoi", "HCM", "Hanoi", "Danang"],
    "Age": [20, None, 22, 24]
})

print("=== BEFORE CLEANING ===")
print(df)


# STEP 2: Configure options from Frontend
options = {
    "missing_method": "median",
    "outlier_method": "none",
    "encoding_method": "label",
    "scaling_method": "none"
}


# STEP 3: Execute Adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)


# STEP 4: Verify Label Encoding
assert isinstance(cleaned_df, pd.DataFrame)

assert "City" in cleaned_df.columns

assert is_numeric_dtype(cleaned_df["City"])

assert cleaned_df.loc[0, "City"] == cleaned_df.loc[2, "City"]

assert cleaned_df.loc[0, "City"] != cleaned_df.loc[1, "City"]


# STEP 5: Verify Median
assert cleaned_df["Age"].isna().sum() == 0

assert cleaned_df.loc[1, "Age"] == 22.0


# STEP 6: Verify row count
assert len(cleaned_df) == 4

print("\nMEDIAN + LABEL ENCODING TEST PASSED!")
