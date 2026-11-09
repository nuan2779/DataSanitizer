
import pandas as pd
from backend.services.cleaner import DataCleaner

# STEP 1: Create sample data
df = pd.DataFrame({
    "Name": ["An", "Binh", "Chi"],
    "Age": [20, None, 21],
    "Score": [8.5, 7.0, 9.0]
})

print("=== ORIGINAL DATA ===")
print(df)

# STEP 2: Define cleaning pipeline

pipeline_steps = [
    {
        "step_type": "missing_values",
        "config": {
            "columns": ["Age"],
            "strategy": "median"
        }
    }
]


# STEP 3: Initialize DataCleaner
cleaner = DataCleaner(df)

# STEP 4: Run cleaning algorithm
cleaned_df = cleaner.execute_pipeline(pipeline_steps)

print("\n=== CLEANED DATA ===")
print(cleaned_df)

# STEP 5: Verify the result
assert isinstance(cleaned_df, pd.DataFrame)
assert cleaned_df["Age"].isna().sum() == 0
assert cleaned_df.loc[1, "Age"] == 20.5

print("\nSUCCESS: Median cleaning works correctly!")
