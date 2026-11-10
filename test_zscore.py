
import pandas as pd
from backend.services.adapter import clean_dataframe

# STEP 1: Create sample dataset
df = pd.DataFrame({
    "Age": list(range(20, 40)) + [300]
})

print("=== BEFORE CLEANING ===")
print(df)

# STEP 2: Options from Frontend
options = {
    "missing_method": "median",
    "outlier_method": "zscore",
    "encoding_method": "none",
    "scaling_method": "none"
}

# STEP 3: Call Adapter
cleaned_df = clean_dataframe(df, options)

print("\n=== AFTER CLEANING ===")
print(cleaned_df)

# STEP 4: Validate
assert isinstance(cleaned_df, pd.DataFrame)
assert len(cleaned_df) == 20
assert 300 not in cleaned_df["Age"].values

print("\nADAPTER Z-SCORE TEST PASSED!")
