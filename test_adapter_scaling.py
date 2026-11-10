
import pandas as pd
import numpy as np

from backend.services.adapter import clean_dataframe


# STEP 1: Sample data
df = pd.DataFrame({
    "Age": [10, 20, 30],
    "Score": [100, 200, 300]
})


# STEP 2: Function for testing options
def run_adapter(method):

    options = {
        "missing_method": "median",
        "outlier_method": "none",
        "encoding_method": "none",
        "scaling_method": method
    }

    return clean_dataframe(df, options)


# STEP 3: Test MinMax Scaling
minmax_df = run_adapter("minmax")

print("=== MINMAX RESULT ===")
print(minmax_df)

np.testing.assert_allclose(
    minmax_df["Age"].to_numpy(),
    [0.0, 0.5, 1.0],
    atol=1e-6
)

print("ADAPTER MINMAX TEST PASSED!")


# STEP 4: Test Standard Scaling
standard_df = run_adapter("standard")

print("\n=== STANDARD RESULT ===")
print(standard_df)

np.testing.assert_allclose(
    standard_df["Age"].to_numpy(),
    [-1.22474487, 0.0, 1.22474487],
    atol=1e-6
)

print("ADAPTER STANDARD TEST PASSED!")


# STEP 5: Verify original data unchanged
assert df["Age"].tolist() == [10, 20, 30]

print("\nALL ADAPTER SCALING TESTS PASSED!")
