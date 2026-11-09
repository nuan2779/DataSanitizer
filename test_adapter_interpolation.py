
import pandas as pd
import numpy as np

from backend.services.adapter import clean_dataframe


# STEP 1: Create sample dataset
df = pd.DataFrame({
    "Day": [1, 2, 3, 4, 5],
    "Temperature": [20, None, 24, None, 28],
    "City": ["Hanoi"] * 5
})

print("=== BEFORE CLEANING ===")
print(df)


# STEP 2: Configure Interpolation
options = {
    "missing_method": "interpolation",
    "outlier_method": "none",
    "encoding_method": "none",
    "scaling_method": "none"
}


# STEP 3: Execute Adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)


# STEP 4: Verify interpolated values
assert isinstance(cleaned_df, pd.DataFrame)

assert np.isclose(
    cleaned_df.loc[1, "Temperature"],
    22.0
)

assert np.isclose(
    cleaned_df.loc[3, "Temperature"],
    26.0
)

# No missing values in Temperature
assert cleaned_df["Temperature"].isna().sum() == 0

# Keep original columns and rows
assert len(cleaned_df) == 5

assert "City" in cleaned_df.columns

# Original DataFrame must remain unchanged
assert pd.isna(df.loc[1, "Temperature"])

print("\nINTERPOLATION INTEGRATION TEST PASSED!")
