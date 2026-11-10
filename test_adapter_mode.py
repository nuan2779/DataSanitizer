
import pandas as pd

from backend.services.adapter import clean_dataframe

# STEP 1: Sample dataset
df = pd.DataFrame({
    "City": ["Hanoi", "Hanoi", "HCM", None],
    "Age": [20, 20, 22, None]
})

print("=== BEFORE CLEANING ===")
print(df)

# STEP 2: Cleaning options
options = {
    "missing_method": "mode",
    "outlier_method": "none",
    "encoding_method": "none",
    "scaling_method": "none"
}

# STEP 3: Execute Adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)

# STEP 4: Verify Mode for categorical column
assert cleaned_df.loc[3, "City"] == "Hanoi"

# STEP 5: Verify Mode for numeric column
assert cleaned_df.loc[3, "Age"] == 20.0

# STEP 6: Verify missing values
assert cleaned_df.isna().sum().sum() == 0

# STEP 7: Check original DataFrame
assert pd.isna(df.loc[3, "City"])
assert pd.isna(df.loc[3, "Age"])

print("\nMODE INTEGRATION TEST PASSED!")
