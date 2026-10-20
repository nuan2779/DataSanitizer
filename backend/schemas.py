from pydantic import BaseModel
from typing import Literal
from uuid import UUID

class CleanRequest(BaseModel):
    file_id: UUID

    missing_method: Literal[
        "mean", "median", "mode",
        "drop_rows", "drop_columns", "interpolate"] = "median"

    outlier_method: Literal[
        "none","iqr","zscore"] = "none"

    encoding_method: Literal[
        "none","onehot","label"] = "none"
    scaling_method: Literal[
        "none","minmax","standard"] = "none"