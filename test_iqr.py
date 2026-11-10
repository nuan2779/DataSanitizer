
import pandas as pd
from backend.services.adapter import clean_dataframe

# Create sample dataset
df = pd.DataFrame({
    "Age": [20, 21, 22, 23, 24, 25, 26, 27, 150]
})

print("BEFORE CLEANING:")
print(df)

# Configure cleaning options
options = {
    "missing_method": "median",
    "outlier_method": "iqr",
    "encoding_method": "none",
    "scaling_method": "none"
}

# Execute real DataCleaner
cleaned_df = clean_dataframe(df, options)

print("\nAFTER CLEANING:")
print(cleaned_df)

# Verify the outlier was removed
assert len(cleaned_df) == 8
assert 150 not in cleaned_df["Age"].values

print("\nIQR TEST PASSED!")
