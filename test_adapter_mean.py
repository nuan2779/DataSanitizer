
import pandas as pd
import numpy as np

from backend.services.adapter import clean_dataframe

# STEP 1: Sample dataset
df = pd.DataFrame({
    "Name": ["An", "Binh", "Chi", "Dung"],
    "Age": [20, 21, 40, None]
})

print("=== BEFORE CLEANING ===")
print(df)

# STEP 2: Configure Mean
options = {
    "missing_method": "mean",
    "outlier_method": "none",
    "encoding_method": "none",
    "scaling_method": "none"
}

# STEP 3: Run Adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)

# STEP 4: Validate Mean
assert isinstance(cleaned_df, pd.DataFrame)

assert cleaned_df["Age"].isna().sum() == 0

assert np.isclose(
    cleaned_df.loc[3, "Age"],
    27.0
)

# STEP 5: Original data unchanged
assert pd.isna(df.loc[3, "Age"])

print("\nMEAN INTEGRATION TEST PASSED!")
