"""
Type Conversion Transformer — Auto-detect and convert data types.
Methods: auto, to_numeric, to_string, to_datetime, to_category, to_boolean
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class TypeConversionTransformer(BaseTransformer):
    """Convert column data types automatically or manually."""

    transform_type = "type_conversion"
    description = "Convert column data types (auto-detect or manual)"
    supported_methods = ["auto", "to_numeric", "to_string", "to_datetime", "to_category", "to_boolean"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "auto")
        columns = config.get("columns", [])
        target_type = config.get("target_type", method if method != "auto" else None)
        date_format = config.get("date_format", None)
        true_values = config.get("true_values", ["true", "yes", "1", "y", "t"])
        false_values = config.get("false_values", ["false", "no", "0", "n", "f"])

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        if not target_columns and method == "auto":
            target_columns = df.columns.tolist()
        target_columns = [c for c in target_columns if c in df.columns]

        if not target_columns:
            return TransformResult(
                df=df, success=False, message="No columns specified for type conversion",
                duration_ms=int((time.time() - start) * 1000),
            )

        result_df = df.copy()
        total_conversions = 0
        details = {}

        for col in target_columns:
            original_dtype = str(result_df[col].dtype)

            if method == "auto":
                result_df, converted = self._auto_convert(result_df, col)
            elif method == "to_numeric" or target_type == "numeric":
                result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
                converted = str(result_df[col].dtype) != original_dtype
            elif method == "to_string" or target_type == "string":
                result_df[col] = result_df[col].astype(str)
                converted = True
            elif method == "to_datetime" or target_type == "datetime":
                result_df[col] = pd.to_datetime(result_df[col], format=date_format, errors='coerce')
                converted = str(result_df[col].dtype) != original_dtype
            elif method == "to_category" or target_type == "category":
                result_df[col] = result_df[col].astype('category')
                converted = True
            elif method == "to_boolean" or target_type == "boolean":
                result_df[col] = self._to_boolean(result_df[col], true_values, false_values)
                converted = True
            else:
                converted = False

            new_dtype = str(result_df[col].dtype)
            if converted:
                total_conversions += 1
            details[col] = {"from": original_dtype, "to": new_dtype, "converted": converted}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Type conversion: {total_conversions} columns converted ({method})",
            rows_affected=len(df),
            columns_affected=target_columns,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    def _auto_convert(self, df, col):
        """Smart type detection — try numeric, then datetime, then boolean, then category."""
        original = df[col].copy()
        original_dtype = str(df[col].dtype)

        # Skip if already numeric or datetime
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            return df, False

        # Try numeric
        numeric = pd.to_numeric(df[col], errors='coerce')
        if numeric.notna().sum() / max(len(df[col].dropna()), 1) > 0.9:
            df[col] = numeric
            return df, str(df[col].dtype) != original_dtype

        # Try datetime
        try:
            dt = pd.to_datetime(df[col], errors='coerce')
            if dt.notna().sum() / max(len(df[col].dropna()), 1) > 0.8:
                df[col] = dt
                return df, str(df[col].dtype) != original_dtype
        except Exception:
            pass

        # Try boolean
        unique_vals = df[col].dropna().str.lower().unique()
        bool_vals = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n', 't', 'f'}
        if set(unique_vals).issubset(bool_vals) and len(unique_vals) <= 2:
            df[col] = df[col].str.lower().map(
                {v: True for v in ['true', 'yes', '1', 'y', 't']} |
                {v: False for v in ['false', 'no', '0', 'n', 'f']}
            )
            return df, True

        # Convert to category if low cardinality
        if df[col].nunique() / len(df[col]) < 0.5:
            df[col] = df[col].astype('category')
            return df, str(df[col].dtype) != original_dtype

        return df, False

    def _to_boolean(self, series, true_values, false_values):
        lower = series.astype(str).str.lower().str.strip()
        mapping = {v: True for v in true_values}
        mapping.update({v: False for v in false_values})
        return lower.map(mapping).astype('boolean')
