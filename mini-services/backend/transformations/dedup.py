"""
Dedup Transformer — Remove duplicate rows.
Methods: exact, fuzzy, subset_columns
"""

import pandas as pd
from transformations.base_transformer import BaseTransformer, TransformResult


class DedupTransformer(BaseTransformer):
    """Remove duplicate rows using exact matching or column subset matching."""

    transform_type = "dedup"
    description = "Remove duplicate rows from dataset"
    supported_methods = ["exact", "subset", "keep_first", "keep_last", "keep_none"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        method = self._get_method(config, "exact")
        columns = config.get("columns", config.get("subset", []))
        keep = config.get("keep", "first")

        # Map method to keep parameter
        keep_map = {"keep_first": "first", "keep_last": "last", "keep_none": False}
        keep = keep_map.get(method, keep)
        if method == "exact":
            keep = config.get("keep", "first")

        original_count = len(df)

        # Count duplicates before removal
        if columns:
            invalid_cols = [c for c in columns if c not in df.columns]
            if invalid_cols:
                return TransformResult(
                    df=df, success=False,
                    message=f"Columns not found: {invalid_cols}",
                    duration_ms=int((time.time() - start) * 1000),
                )
            dup_mask = df.duplicated(subset=columns, keep=keep)
        else:
            dup_mask = df.duplicated(keep=keep)

        duplicate_count = int(dup_mask.sum())
        result_df = df[~dup_mask].reset_index(drop=True)

        details = {
            "original_rows": original_count,
            "duplicate_rows": duplicate_count,
            "remaining_rows": len(result_df),
            "method": method,
            "subset_columns": columns if columns else "all columns",
        }

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Removed {duplicate_count} duplicate rows ({method} on {', '.join(columns) if columns else 'all columns'})",
            rows_affected=duplicate_count,
            columns_affected=[],
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )
