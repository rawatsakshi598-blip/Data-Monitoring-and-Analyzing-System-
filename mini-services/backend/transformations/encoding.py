"""
Encoding Transformer — Categorical encoding for ML pipelines.
Methods: one_hot, label, ordinal, target, frequency, binary
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class EncodingTransformer(BaseTransformer):
    """Encode categorical columns for machine learning pipelines."""

    transform_type = "encoding"
    description = "Encode categorical variables for ML pipelines"
    supported_methods = ["one_hot", "label", "ordinal", "target", "frequency", "binary"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "label")
        columns = config.get("columns", [])
        categories = config.get("categories", config.get("order", []))
        target_column = config.get("target_column", "")
        drop_original = config.get("drop_original", True)
        prefix = config.get("prefix", None)

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        target_columns = [c for c in target_columns if c in df.columns]

        if not target_columns:
            # Auto-detect categorical columns
            target_columns = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
            if not target_columns:
                return TransformResult(
                    df=df, success=True, message="No categorical columns found to encode",
                    duration_ms=int((time.time() - start) * 1000),
                )

        result_df = df.copy()
        all_new_cols = []
        details = {}

        for col in target_columns:
            if method == "one_hot":
                result_df, new_cols = self._one_hot_encode(result_df, col, prefix, drop_original)
                all_new_cols.extend(new_cols)
            elif method == "label":
                result_df, new_col = self._label_encode(result_df, col, drop_original)
                all_new_cols.append(new_col)
            elif method == "ordinal":
                result_df, new_col = self._ordinal_encode(result_df, col, categories, drop_original)
                all_new_cols.append(new_col)
            elif method == "target":
                result_df, new_col = self._target_encode(result_df, col, target_column, drop_original)
                all_new_cols.append(new_col)
            elif method == "frequency":
                result_df, new_col = self._frequency_encode(result_df, col, drop_original)
                all_new_cols.append(new_col)
            elif method == "binary":
                result_df, new_col = self._binary_encode(result_df, col, drop_original)
                all_new_cols.append(new_col)

            details[col] = {"method": method, "new_columns": [c for c in all_new_cols if col in c]}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Encoded {len(target_columns)} columns using {method}: {len(all_new_cols)} new columns created",
            rows_affected=len(df),
            columns_affected=target_columns,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    def _one_hot_encode(self, df, col, prefix, drop_original):
        p = prefix or col
        dummies = pd.get_dummies(df[col], prefix=p, dtype=int)
        df = pd.concat([df, dummies], axis=1)
        if drop_original:
            df = df.drop(columns=[col])
        return df, dummies.columns.tolist()

    def _label_encode(self, df, col, drop_original):
        new_col = f"{col}_encoded"
        df[new_col] = pd.Categorical(df[col]).codes
        # Replace -1 (NaN categories) with 0
        df[new_col] = df[new_col].replace(-1, 0)
        if drop_original:
            df = df.drop(columns=[col])
        return df, new_col

    def _ordinal_encode(self, df, col, categories, drop_original):
        new_col = f"{col}_ordinal"
        if categories:
            cat_map = {v: i for i, v in enumerate(categories)}
            df[new_col] = df[col].map(cat_map).fillna(0).astype(int)
        else:
            df[new_col] = pd.Categorical(df[col]).codes
            df[new_col] = df[new_col].replace(-1, 0)
        if drop_original:
            df = df.drop(columns=[col])
        return df, new_col

    def _target_encode(self, df, col, target_column, drop_original):
        new_col = f"{col}_target_enc"
        if not target_column or target_column not in df.columns:
            # Fallback to frequency encoding
            return self._frequency_encode(df, col, drop_original)

        if pd.api.types.is_numeric_dtype(df[target_column]):
            means = df.groupby(col)[target_column].mean()
            df[new_col] = df[col].map(means).fillna(df[target_column].mean())
        else:
            # For classification: map to frequency of most common class
            freqs = df.groupby(col)[target_column].apply(lambda x: x.value_counts().index[0] if len(x) > 0 else 0)
            df[new_col] = df[col].map(freqs)

        if drop_original:
            df = df.drop(columns=[col])
        return df, new_col

    def _frequency_encode(self, df, col, drop_original):
        new_col = f"{col}_freq"
        freq = df[col].value_counts(normalize=True)
        df[new_col] = df[col].map(freq).fillna(0)
        if drop_original:
            df = df.drop(columns=[col])
        return df, new_col

    def _binary_encode(self, df, col, drop_original):
        new_col = f"{col}_binary"
        unique_vals = df[col].dropna().unique()
        if len(unique_vals) <= 2:
            map_dict = {unique_vals[0]: 0, unique_vals[1]: 1} if len(unique_vals) == 2 else {unique_vals[0]: 0}
            df[new_col] = df[col].map(map_dict).fillna(-1).astype(int)
        else:
            # Convert to label first, then binary
            labels = pd.Categorical(df[col]).codes
            df[new_col] = labels
        if drop_original:
            df = df.drop(columns=[col])
        return df, new_col
