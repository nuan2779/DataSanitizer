from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineStep(BaseModel):
    step_type: Literal[
        "standardize_nulls", "clean_numeric", "missing_values", "outlier",
        "encoding", "scaling", "round", "drop_duplicates", "optimize_memory"
    ]
    config: dict[str, Any] = Field(default_factory=dict)


class CleanRequest(BaseModel):
    file_id: UUID

    # New frontend contract: an ordered, user-configured sequence.
    pipeline: list[PipelineStep] | None = Field(default=None, min_length=1, max_length=50)

    # ML Mode & Anti Data Leakage configurations
    purpose: Literal["eda", "ml"] = "eda"
    train_ratio: float = Field(default=0.8, ge=0.1, le=0.95)

    # Legacy contract: preserve compatibility with existing backend/test clients.
    missing_method: Literal[
        "mean", "median", "mode", "drop_rows", "drop_columns", "interpolation", "interpolate"
    ] = "median"
    outlier_method: Literal["none", "iqr", "zscore"] = "none"
    encoding_method: Literal["none", "onehot", "label"] = "none"
    scaling_method: Literal["none", "minmax", "standard"] = "none"
