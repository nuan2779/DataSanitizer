
import pandas as pd
from backend.services.adapter import clean_dataframe

# Sample dataset
df = pd.DataFrame({
    "City": ["Hanoi", "HCM", "Hanoi"],
    "Age": [20, None, 22],
    "Score": [8.5, 7.0, 9.0]
})

print("=== BEFORE CLEANING ===")
print(df)

options = {
    "missing_method": "median",
    "outlier_method": "none",
    "encoding_method": "onehot",
    "scaling_method": "none"
}

# Execute adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)

# Check missing values
assert cleaned_df["Age"].isna().sum() == 0
assert cleaned_df.loc[1, "Age"] == 21.0

# Check One-Hot Encoding
assert "City" not in cleaned_df.columns

assert any(
    col.startswith("City_")
    for col in cleaned_df.columns
)

# Check number of rows
assert len(cleaned_df) == 3

print("\nMEDIAN + ONE-HOT INTEGRATION PASSED!")
