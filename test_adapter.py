
import pandas as pd
from backend.services.adapter import clean_dataframe

df = pd.DataFrame({
    "Name": ["An", "Binh", "Chi"],
    "Age": [20, None, 21],
    "Score": [8.5, 7.0, 9.0]
})

options = {
    "missing_method": "median",
    "outlier_method": "none",
    "encoding_method": "none",
    "scaling_method": "none"
}

print("BEFORE:")
print(df)

cleaned_df = clean_dataframe(df, options)

print("\nAFTER:")
print(cleaned_df)

assert cleaned_df.loc[1, "Age"] == 20.5
assert cleaned_df["Age"].isna().sum() == 0

print("\nADAPTER TEST PASSED!")
