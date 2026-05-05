"""
Base Transform — Abstract base class for all data transformations.
Every transformation inherits this and implements execute().
Provides snapshot, timing, and edge-case handling utilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd
import numpy as np
import time


@dataclass
class TransformResult:
    """Result of a transformation execution."""

    success: bool = False
    table_id: str = ""
    transform_type: str = ""
    column: str = ""
    rows_affected: int = 0
    duration_ms: int = 0
    before_snapshot: dict = field(default_factory=dict)
    after_snapshot: dict = field(default_factory=dict)
    message: str = ""
    df: Optional[pd.DataFrame] = None  # the transformed dataframe copy
    extra: dict = field(default_factory=dict)  # for split indices, etc.

    def to_dict(self) -> dict:
        """Serialize result, excluding the DataFrame."""
        return {
            "success": self.success,
            "table_id": self.table_id,
            "transform_type": self.transform_type,
            "column": self.column,
            "rows_affected": self.rows_affected,
            "duration_ms": self.duration_ms,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
            "message": self.message,
            "extra": self.extra,
        }


class BaseTransform(ABC):
    """Abstract base class for all data transformations.

    Subclasses must:
      - Set ``transform_type`` and ``description`` class attributes.
      - Implement ``execute(df, config, table_id, column)``.

    The ``execute`` method should:
      1. Validate inputs (empty df, missing column, etc.).
      2. Take a *copy* of the DataFrame — never mutate the original.
      3. Capture a before-snapshot via ``_snapshot``.
      4. Apply the transformation.
      5. Capture an after-snapshot.
      6. Return a ``TransformResult``.
    """

    transform_type: str = "base"
    description: str = ""

    # ── Abstract interface ──────────────────────────────────────────

    @abstractmethod
    def execute(
        self,
        df: pd.DataFrame,
        config: dict,
        table_id: str = "",
        column: str = "",
    ) -> TransformResult:
        """Run the transformation and return a TransformResult.

        Parameters
        ----------
        df : pd.DataFrame
            Source data (will NOT be mutated).
        config : dict
            Transformation-specific configuration.
        table_id : str
            Identifier of the source table (for metadata only).
        column : str
            Target column name (if applicable).

        Returns
        -------
        TransformResult
        """
        ...

    # ── Snapshot helpers ────────────────────────────────────────────

    def _snapshot(self, series: pd.Series) -> dict:
        """Capture column statistics for before/after comparison.

        Returns a dict with null_count, unique_count, dtype, and
        type-specific stats (min/max/mean for numeric, top values
        for categorical).
        """
        if series is None or len(series) == 0:
            return {
                "null_count": 0,
                "unique_count": 0,
                "dtype": "unknown",
                "total_count": 0,
            }

        null_count = int(series.isna().sum())
        non_null = series.dropna()
        unique_count = int(non_null.nunique())
        total_count = len(series)

        snap: dict[str, Any] = {
            "null_count": null_count,
            "null_pct": round(null_count / total_count * 100, 2) if total_count else 0.0,
            "unique_count": unique_count,
            "dtype": str(series.dtype),
            "total_count": total_count,
        }

        if len(non_null) == 0:
            snap["note"] = "all_null"
            return snap

        # Numeric stats
        if pd.api.types.is_numeric_dtype(series):
            snap["min"] = float(non_null.min())
            snap["max"] = float(non_null.max())
            snap["mean"] = float(non_null.mean())
            snap["median"] = float(non_null.median())
            snap["std"] = float(non_null.std()) if len(non_null) > 1 else 0.0
            snap["q25"] = float(non_null.quantile(0.25))
            snap["q75"] = float(non_null.quantile(0.75))
        else:
            # Categorical stats — top 5 values
            vc = non_null.value_counts().head(5)
            snap["top_values"] = {str(k): int(v) for k, v in vc.items()}

        return snap

    # ── Timing helpers ──────────────────────────────────────────────

    def _start_timer(self) -> float:
        """Return current monotonic time."""
        return time.time()

    def _end_timer(self, start: float) -> int:
        """Return elapsed milliseconds since *start*."""
        return int((time.time() - start) * 1000)

    # ── Validation helpers ──────────────────────────────────────────

    @staticmethod
    def _validate_df(df: pd.DataFrame) -> Optional[str]:
        """Return an error message if the DataFrame is unusable, else None."""
        if df is None:
            return "DataFrame is None"
        if not isinstance(df, pd.DataFrame):
            return f"Expected DataFrame, got {type(df).__name__}"
        if df.empty:
            return "DataFrame is empty"
        return None

    @staticmethod
    def _validate_column(df: pd.DataFrame, column: str) -> Optional[str]:
        """Return an error message if the column is missing, else None."""
        if not column:
            return "No column specified"
        if column not in df.columns:
            return f"Column '{column}' not found in DataFrame (columns: {list(df.columns)})"
        return None

    def _make_error_result(
        self,
        message: str,
        table_id: str = "",
        column: str = "",
        start: float = 0.0,
    ) -> TransformResult:
        """Build a failed TransformResult with timing."""
        return TransformResult(
            success=False,
            table_id=table_id,
            transform_type=self.transform_type,
            column=column,
            rows_affected=0,
            duration_ms=self._end_timer(start) if start else 0,
            message=message,
        )
