"""
Outlier Transformer — Detect and handle outliers.
Methods: iqr_remove, iqr_cap, zscore_remove, zscore_cap, winsorize, percentile_clip
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class OutlierTransformer(BaseTransformer):
    """Detect and handle outliers using statistical methods."""

    transform_type = "outlier"
    description = "Detect and handle outliers using IQR, Z-score, or Winsorization"
    supported_methods = ["iqr_remove", "iqr_cap", "zscore_remove", "zscore_cap", "winsorize", "percentile_clip"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "iqr_remove")
        columns = config.get("columns", [])
        threshold = config.get("threshold", config.get("z_threshold", 3.0))
        iqr_multiplier = config.get("iqr_multiplier", config.get("multiplier", 1.5))
        lower_percentile = config.get("lower_percentile", 1)
        upper_percentile = config.get("upper_percentile", 99)
        limits = config.get("limits", (0.05, 0.05))  # for winsorize

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        # Auto-detect numeric columns if none specified
        if not target_columns:
            target_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        target_columns = [c for c in target_columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

        if not target_columns:
            return TransformResult(
                df=df, success=False, message="No numeric columns found for outlier detection",
                duration_ms=int((time.time() - start) * 1000),
            )

        result_df = df.copy()
        total_outliers = 0
        details = {}

        for col in target_columns:
            series = result_df[col].dropna()
            if len(series) < 3:
                continue

            if method in ("iqr_remove", "iqr_cap"):
                outlier_count, result_df = self._iqr_handle(result_df, col, method, iqr_multiplier)
            elif method in ("zscore_remove", "zscore_cap"):
                outlier_count, result_df = self._zscore_handle(result_df, col, method, threshold)
            elif method == "winsorize":
                outlier_count, result_df = self._winsorize_handle(result_df, col, limits)
            elif method == "percentile_clip":
                outlier_count, result_df = self._percentile_clip(result_df, col, lower_percentile, upper_percentile)
            else:
                outlier_count = 0

            total_outliers += outlier_count
            details[col] = {"outliers_found": outlier_count, "method": method}

        action = "removed" if "remove" in method else "capped/clipped"
        return TransformResult(
            df=result_df,
            success=True,
            message=f"Outliers {action}: {total_outliers} outliers across {len(target_columns)} columns via {method}",
            rows_affected=total_outliers if "remove" in method else 0,
            columns_affected=target_columns,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    def _iqr_handle(self, df, col, method, multiplier):
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - multiplier * IQR
        upper = Q3 + multiplier * IQR
        outlier_mask = (df[col] < lower) | (df[col] > upper)
        outlier_count = int(outlier_mask.sum())

        if method == "iqr_remove":
            df = df[~outlier_mask]
        elif method == "iqr_cap":
            df[col] = df[col].clip(lower=lower, upper=upper)

        return outlier_count, df

    def _zscore_handle(self, df, col, method, threshold):
        series = df[col].dropna()
        mean = series.mean()
        std = series.std()
        if std == 0:
            return 0, df
        z_scores = ((df[col] - mean) / std).abs()
        outlier_mask = z_scores > threshold
        outlier_count = int(outlier_mask.sum())

        if method == "zscore_remove":
            df = df[~outlier_mask]
        elif method == "zscore_cap":
            lower = mean - threshold * std
            upper = mean + threshold * std
            df[col] = df[col].clip(lower=lower, upper=upper)

        return outlier_count, df

    def _winsorize_handle(self, df, col, limits):
        try:
            from scipy.stats.mstats import winsorize
            original = df[col].copy()
            winsorized = winsorize(df[col].values, limits=limits)
            df[col] = winsorized
            outlier_count = int((original != df[col]).sum())
            return outlier_count, df
        except ImportError:
            # Fallback to percentile clipping
            return self._percentile_clip(df, col, int(limits[0]*100), 100-int(limits[1]*100))

    def _percentile_clip(self, df, col, lower_pct, upper_pct):
        lower = df[col].quantile(lower_pct / 100)
        upper = df[col].quantile(upper_pct / 100)
        outlier_mask = (df[col] < lower) | (df[col] > upper)
        outlier_count = int(outlier_mask.sum())
        df[col] = df[col].clip(lower=lower, upper=upper)
        return outlier_count, df
