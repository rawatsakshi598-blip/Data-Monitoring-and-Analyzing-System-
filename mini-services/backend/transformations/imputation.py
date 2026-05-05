"""
Imputation Transformer — Fill missing values.
Methods: mean, median, mode, constant, forward_fill, backward_fill, knn, mice
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class ImputationTransformer(BaseTransformer):
    """Fill missing values using various strategies."""

    transform_type = "imputation"
    description = "Fill missing values using various imputation strategies"
    supported_methods = ["mean", "median", "mode", "constant", "forward_fill", "backward_fill", "knn", "most_frequent"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        start = __import__("time").time()
        column = self._get_column(config)
        method = self._get_method(config, "mean")
        fill_value = config.get("fill_value", config.get("constant", None))
        columns = config.get("columns", [])
        n_neighbors = config.get("n_neighbors", 5)

        # Determine which columns to process
        target_columns = columns if columns else ([column] if column and column in df.columns else df.columns.tolist())
        target_columns = [c for c in target_columns if c in df.columns]

        if not target_columns:
            return TransformResult(
                df=df, success=False, message="No valid columns specified for imputation",
                duration_ms=int((__import__("time").time() - start) * 1000),
            )

        original_nulls = {col: int(df[col].isna().sum()) for col in target_columns}
        total_nulls_before = sum(original_nulls.values())

        if total_nulls_before == 0:
            return TransformResult(
                df=df, success=True, message="No missing values found",
                rows_affected=0, columns_affected=target_columns,
                duration_ms=int((__import__("time").time() - start) * 1000),
            )

        result_df = df.copy()

        for col in target_columns:
            if result_df[col].isna().sum() == 0:
                continue

            if method in ("mean", "median", "mode", "most_frequent"):
                result_df[col] = self._statistical_impute(result_df[col], method)
            elif method == "constant":
                if fill_value is not None:
                    result_df[col] = result_df[col].fillna(fill_value)
                else:
                    # Use column-appropriate defaults
                    if pd.api.types.is_numeric_dtype(result_df[col]):
                        result_df[col] = result_df[col].fillna(0)
                    else:
                        result_df[col] = result_df[col].fillna("unknown")
            elif method == "forward_fill":
                result_df[col] = result_df[col].ffill()
            elif method == "backward_fill":
                result_df[col] = result_df[col].bfill()
            elif method == "knn":
                result_df = self._knn_impute(result_df, col, n_neighbors)

        total_nulls_after = sum(int(result_df[col].isna().sum()) for col in target_columns)
        filled_count = total_nulls_before - total_nulls_after
        details = {col: {"before": original_nulls[col], "after": int(result_df[col].isna().sum())}
                   for col in target_columns}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Imputed {filled_count} missing values across {len(target_columns)} columns using {method}",
            rows_affected=filled_count,
            columns_affected=target_columns,
            details=details,
            duration_ms=int((__import__("time").time() - start) * 1000),
        )

    def _statistical_impute(self, series: pd.Series, method: str) -> pd.Series:
        if pd.api.types.is_numeric_dtype(series):
            if method == "mean":
                return series.fillna(series.mean())
            elif method == "median":
                return series.fillna(series.median())
        if method in ("mode", "most_frequent"):
            mode_val = series.mode()
            if len(mode_val) > 0:
                return series.fillna(mode_val.iloc[0])
        if method == "mean" and not pd.api.types.is_numeric_dtype(series):
            mode_val = series.mode()
            if len(mode_val) > 0:
                return series.fillna(mode_val.iloc[0])
        if method == "median" and not pd.api.types.is_numeric_dtype(series):
            mode_val = series.mode()
            if len(mode_val) > 0:
                return series.fillna(mode_val.iloc[0])
        return series

    def _knn_impute(self, df: pd.DataFrame, column: str, n_neighbors: int) -> pd.DataFrame:
        """Simplified KNN imputation using distance to nearest numeric neighbors."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if column not in numeric_cols or len(numeric_cols) < 2:
            # Fallback to median for non-numeric or single-column case
            df[column] = df[column].fillna(df[column].median() if pd.api.types.is_numeric_dtype(df[column]) else df[column].mode().iloc[0] if len(df[column].mode()) > 0 else df[column])
            return df

        missing_mask = df[column].isna()
        if not missing_mask.any():
            return df

        other_cols = [c for c in numeric_cols if c != column]
        from sklearn.impute import KNNImputer
        try:
            imputer = KNNImputer(n_neighbors=min(n_neighbors, len(df) - 1))
            imputed = imputer.fit_transform(df[numeric_cols])
            df.loc[:, numeric_cols] = imputed
        except ImportError:
            # Fallback if sklearn not available
            df[column] = df[column].fillna(df[column].median())
        return df
