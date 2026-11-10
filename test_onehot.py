
import pandas as pd
from backend.services.cleaner import DataCleaner

# STEP 1: Create sample dataset
df = pd.DataFrame({
    "Name": ["An", "Binh", "Chi"],
    "City": ["Hanoi", "HCM", "Hanoi"],
    "Age": [20, 21, 22]
})

print("=== BEFORE ENCODING ===")
print(df)

# STEP 2: Configure encoding pipeline
pipeline_steps = [
    {
        "step_type": "encoding",
        "config": {
            "columns": ["City"],
            "method": "one_hot"
        }
    }
]

# STEP 3: Initialize DataCleaner
cleaner = DataCleaner(df.copy())

# STEP 4: Execute pipeline
encoded_df = cleaner.execute_pipeline(pipeline_steps)

print("\n=== AFTER ENCODING ===")
print(encoded_df)

# STEP 5: Validate result
assert isinstance(encoded_df, pd.DataFrame)

assert "City" not in encoded_df.columns

assert any(
    col.startswith("City_")
    for col in encoded_df.columns
)

print("\nONE-HOT ENCODING TEST PASSED!")
