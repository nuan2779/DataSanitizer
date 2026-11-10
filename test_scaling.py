
import pandas as pd
import numpy as np

from backend.services.cleaner import DataCleaner

# STEP 1: Create sample dataset
df = pd.DataFrame({
    "Age": [10, 20, 30],
    "Score": [100, 200, 300]
})

print("=== ORIGINAL DATA ===")
print(df)


# STEP 2: Function to test scaling
def run_scaling(method):

    cleaner = DataCleaner(df.copy())

    pipeline_steps = [
        {
            "step_type": "scaling",
            "config": {
                "columns": ["Age", "Score"],
                "method": method
            }
        }
    ]

    return cleaner.execute_pipeline(pipeline_steps)


# STEP 3: Test MinMax
minmax_df = run_scaling("minmax")

print("\n=== MINMAX SCALING ===")
print(minmax_df)

np.testing.assert_allclose(
    minmax_df["Age"].to_numpy(),
    [0.0, 0.5, 1.0],
    atol=1e-6
)

np.testing.assert_allclose(
    minmax_df["Score"].to_numpy(),
    [0.0, 0.5, 1.0],
    atol=1e-6
)

print("MINMAX TEST PASSED!")


# STEP 4: Test Standard Scaling
standard_df = run_scaling("standard")

print("\n=== STANDARD SCALING ===")
print(standard_df)

assert np.isclose(
    standard_df["Age"].mean(),
    0.0,
    atol=1e-6
)

assert np.isclose(
    standard_df["Age"].std(ddof=0),
    1.0,
    atol=1e-6
)

print("STANDARD TEST PASSED!")
