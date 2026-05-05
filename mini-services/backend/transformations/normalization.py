"""
Normalization Transformer — Scale numeric features.
Methods: minmax, zscore, robust, log, max_abs
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class NormalizationTransformer(BaseTransformer):
    """Normalize/standardize numeric features for ML pipelines."""

    transform_type = "normalization"
    description = "Scale and normalize numeric features"
    supported_methods = ["minmax", "zscore", "robust", "log", "max_abs"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "minmax")
        columns = config.get("columns", [])
        feature_range = tuple(config.get("feature_range", [0, 1]))

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        if not target_columns:
            target_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        target_columns = [c for c in target_columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

        if not target_columns:
            return TransformResult(
                df=df, success=False, message="No numeric columns found for normalization",
                duration_ms=int((time.time() - start) * 1000),
            )

        result_df = df.copy()
        details = {}

        for col in target_columns:
            original_stats = {"min": float(result_df[col].min()), "max": float(result_df[col].max()),
                              "mean": round(float(result_df[col].mean()), 4), "std": round(float(result_df[col].std()), 4)}

            if method == "minmax":
                result_df[col] = self._minmax(result_df[col], feature_range)
            elif method == "zscore":
                result_df[col] = self._zscore(result_df[col])
            elif method == "robust":
                result_df[col] = self._robust(result_df[col])
            elif method == "log":
                result_df[col] = self._log_transform(result_df[col])
            elif method == "max_abs":
                result_df[col] = self._max_abs(result_df[col])

            new_stats = {"min": round(float(result_df[col].min()), 4), "max": round(float(result_df[col].max()), 4),
                         "mean": round(float(result_df[col].mean()), 4), "std": round(float(result_df[col].std()), 4)}
            details[col] = {"method": method, "before": original_stats, "after": new_stats}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Normalized {len(target_columns)} columns using {method}",
            rows_affected=len(df),
            columns_affected=target_columns,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    def _minmax(self, series, feature_range=(0, 1)):
        min_val, max_val = series.min(), series.max()
        if max_val == min_val:
            return pd.Series(feature_range[0], index=series.index)
        scaled = (series - min_val) / (max_val - min_val)
        return scaled * (feature_range[1] - feature_range[0]) + feature_range[0]

    def _zscore(self, series):
        mean, std = series.mean(), series.std()
        if std == 0:
            return pd.Series(0, index=series.index)
        return (series - mean) / std

    def _robust(self, series):
        median = series.median()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return pd.Series(0, index=series.index)
        return (series - median) / iqr

    def _log_transform(self, series):
        # Handle negatives and zeros with log1p
        min_val = series.min()
        if min_val <= 0:
            series = series - min_val + 1
        return np.log1p(series)

    def _max_abs(self, series):
        max_abs = series.abs().max()
        if max_abs == 0:
            return series
        return series / max_abs
