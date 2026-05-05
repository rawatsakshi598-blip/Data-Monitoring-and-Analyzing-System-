"""
Deduplication Transformations
==============================
Remove duplicate rows from DataFrames.

Available transforms:
  - ColumnDeduplication : remove duplicates based on specific columns
  - FullRowDeduplication: remove exact duplicate rows
"""

import pandas as pd

from transformations.base_transform import BaseTransform, TransformResult


class ColumnDeduplication(BaseTransform):
    """Remove rows that are duplicates based on a subset of columns.

    Config keys
    -----------
    subset : list[str]
        Column names to consider for identifying duplicates (required).
    keep : str
        Which duplicates to keep: "first", "last", or "none"
        (default "first").  "none" removes *all* duplicate rows.
    """

    transform_type = "column_deduplication"
    description = "Remove duplicate rows based on specific columns"

    def execute(
        self,
        df: pd.DataFrame,
        config: dict,
        table_id: str = "",
        column: str = "",
    ) -> TransformResult:
        start = self._start_timer()

        err = self._validate_df(df)
        if err:
            return self._make_error_result(err, table_id, column, start)

        subset = config.get("subset")
        if not subset:
            return self._make_error_result(
                "Config key 'subset' (list of column names) is required",
                table_id, column, start,
            )

        # Validate subset columns
        missing = [c for c in subset if c not in df.columns]
        if missing:
            return self._make_error_result(
                f"Subset columns not found: {missing}",
                table_id, column, start,
            )

        keep = config.get("keep", "first")
        if keep not in ("first", "last", "none"):
            return self._make_error_result(
                f"Invalid 'keep' value: {keep!r}. Must be 'first', 'last', or 'none'.",
                table_id, column, start,
            )

        # Snapshot — use first subset column as representative
        snap_col = subset[0]
        before = self._snapshot(df[snap_col])

        dup_mask = df.duplicated(subset=subset, keep=keep if keep != "none" else False)
        dup_count = int(dup_mask.sum())

        if dup_count == 0:
            return TransformResult(
                success=True,
                table_id=table_id,
                transform_type=self.transform_type,
                column=", ".join(subset),
                rows_affected=0,
                duration_ms=self._end_timer(start),
                before_snapshot=before,
                after_snapshot=before,
                message=f"No duplicates found on columns {subset}",
                df=df.copy(),
            )

        result_df = df.loc[~dup_mask].copy().reset_index(drop=True)
        after = self._snapshot(result_df[snap_col])

        return TransformResult(
            success=True,
            table_id=table_id,
            transform_type=self.transform_type,
            column=", ".join(subset),
            rows_affected=dup_count,
            duration_ms=self._end_timer(start),
            before_snapshot=before,
            after_snapshot=after,
            message=(
                f"Removed {dup_count} duplicate row(s) based on columns {subset} "
                f"(keep={keep}). Rows remaining: {len(result_df)}"
            ),
            df=result_df,
        )


class FullRowDeduplication(BaseTransform):
    """Remove exact duplicate rows across all columns.

    Config keys
    -----------
    keep : str
        Which duplicates to keep: "first", "last", or "none"
        (default "first").
    """

    transform_type = "full_row_deduplication"
    description = "Remove exact duplicate rows across all columns"

    def execute(
        self,
        df: pd.DataFrame,
        config: dict,
        table_id: str = "",
        column: str = "",
    ) -> TransformResult:
        start = self._start_timer()

        err = self._validate_df(df)
        if err:
            return self._make_error_result(err, table_id, column, start)

        keep = config.get("keep", "first")
        if keep not in ("first", "last", "none"):
            return self._make_error_result(
                f"Invalid 'keep' value: {keep!r}. Must be 'first', 'last', or 'none'.",
                table_id, column, start,
            )

        # Snapshot of first column as representative
        snap_col = df.columns[0]
        before = self._snapshot(df[snap_col])

        dup_mask = df.duplicated(keep=keep if keep != "none" else False)
        dup_count = int(dup_mask.sum())

        if dup_count == 0:
            return TransformResult(
                success=True,
                table_id=table_id,
                transform_type=self.transform_type,
                column="(all columns)",
                rows_affected=0,
                duration_ms=self._end_timer(start),
                before_snapshot=before,
                after_snapshot=before,
                message="No exact duplicate rows found",
                df=df.copy(),
            )

        result_df = df.loc[~dup_mask].copy().reset_index(drop=True)
        after = self._snapshot(result_df[snap_col])

        return TransformResult(
            success=True,
            table_id=table_id,
            transform_type=self.transform_type,
            column="(all columns)",
            rows_affected=dup_count,
            duration_ms=self._end_timer(start),
            before_snapshot=before,
            after_snapshot=after,
            message=(
                f"Removed {dup_count} exact duplicate row(s) "
                f"(keep={keep}). Rows remaining: {len(result_df)}"
            ),
            df=result_df,
        )
