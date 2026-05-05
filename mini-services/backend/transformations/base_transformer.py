"""
Base Transformer — Abstract base class for all data transformations.
Every transformer inherits this and implements transform().
"""

from abc import ABC, abstractmethod
import pandas as pd
import time
from typing import Any


class TransformResult:
    """Result of a transformation operation."""

    def __init__(
        self,
        df: pd.DataFrame,
        success: bool = True,
        message: str = "",
        duration_ms: int = 0,
        rows_affected: int = 0,
        columns_affected: list[str] = None,
        details: dict = None,
        extra_outputs: dict = None,
    ):
        self.df = df
        self.success = success
        self.message = message
        self.duration_ms = duration_ms
        self.rows_affected = rows_affected
        self.columns_affected = columns_affected or []
        self.details = details or {}
        self.extra_outputs = extra_outputs or {}

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "rows_affected": self.rows_affected,
            "columns_affected": self.columns_affected,
            "details": self.details,
            "extra_outputs": {k: str(v) for k, v in self.extra_outputs.items()},
            "shape": list(self.df.shape),
        }


class BaseTransformer(ABC):
    """Abstract base class for all data transformations."""

    transform_type: str = "base"
    description: str = "Base transformer"
    supported_methods: list[str] = []

    @abstractmethod
    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        """Apply the transformation and return a TransformResult."""
        pass

    def _time_it(self, fn, *args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        duration = int((time.time() - start) * 1000)
        return result, duration

    def _validate_column(self, df: pd.DataFrame, column: str) -> bool:
        return column in df.columns

    def _get_column(self, config: dict, default: str = "") -> str:
        return config.get("column", config.get("columnName", default))

    def _get_method(self, config: dict, default: str = "") -> str:
        method = config.get("method", default)
        # Validate against supported_methods if defined by subclass
        if self.supported_methods and method and method not in self.supported_methods:
            # Try common aliases
            alias_map = {
                "iqr": "iqr_cap",
                "zscore": "zscore_cap",
                "onehot": "one_hot",
            }
            method = alias_map.get(method, default)
        return method
