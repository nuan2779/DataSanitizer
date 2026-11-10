
import pandas as pd
import numpy as np

from backend.services.adapter import clean_dataframe


# STEP 1: Create dataset
df = pd.DataFrame({
    "Age": [
        20, 21, 22, 23, 24, 25,
        None, 27, 28, 29, 30, 31, 150
    ],
    "Score": list(range(50, 63)),
    "City": ["Hanoi", "HCM"] * 6 + ["Hanoi"]
})

print("=== ORIGINAL DATA ===")
print(df)

# STEP 2: Configure all cleaning methods
options = {
    "missing_method": "median",
    "outlier_method": "iqr",
    "encoding_method": "onehot",
    "scaling_method": "standard"
}

# STEP 3: Run the complete pipeline
cleaned_df = clean_dataframe(df, options)

print("\n=== PROCESSED DATA ===")
print(cleaned_df)

# STEP 4: Check DataFrame
assert isinstance(cleaned_df, pd.DataFrame)

# STEP 5: Check missing values
assert cleaned_df.isna().sum().sum() == 0

print("Missing values: PASSED")

# STEP 6: Check outlier removal
assert len(cleaned_df) == 12

print("IQR: PASSED")

# STEP 7: Check One-Hot Encoding
assert "City" not in cleaned_df.columns

assert any(
    col.startswith("City_")
    for col in cleaned_df.columns
)

print("One-Hot: PASSED")

# STEP 8: Check Standard Scaling
assert np.isclose(
    cleaned_df["Age"].mean(),
    0.0,
    atol=1e-6
)

assert np.isclose(
    cleaned_df["Score"].mean(),
    0.0,
    atol=1e-6
)

print("Standard Scaling: PASSED")

# STEP 9: Check original data is unchanged
assert len(df) == 13
assert pd.isna(df.loc[6, "Age"])
assert df.loc[12, "Age"] == 150

print("Original data unchanged: PASSED")

print("\nFULL PIPELINE TEST PASSED!")
