
import pandas as pd

from backend.services.adapter import clean_dataframe


df = pd.DataFrame({
    "Name": ["An", "Binh", "Chi"],
    "City": ["Hanoi", "HCM", "Hanoi"],
    "Salary": ["$1,200.50", "1,500 đ", "2300"],
    "Age": [20, 21, 22]
})

options = {
    "missing_method": "median",
    "outlier_method": "none",
    "encoding_method": "none",
    "scaling_method": "none"
}

print("=== BEFORE ===")
print(df)

result = clean_dataframe(df, options)

print("\n=== AFTER ===")
print(result)

# Verify currency conversion
assert pd.api.types.is_numeric_dtype(result["Salary"])

assert result["Salary"].tolist() == [
    1200.5, 1500.0, 2300.0
]

# Verify text columns remain unchanged
assert result["Name"].tolist() == df["Name"].tolist()
assert result["City"].tolist() == df["City"].tolist()

# Verify original data remains unchanged
assert df.loc[0, "Salary"] == "$1,200.50"

print("\nCURRENCY CLEANING TEST PASSED!")
