"""
Data Split Transformer — Split datasets for ML.
Methods: random, stratified, time_based
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class DataSplitTransformer(BaseTransformer):
    """Split dataset into train/test/validation sets."""

    transform_type = "data_split"
    description = "Split dataset into train/test/validation sets for ML"
    supported_methods = ["random", "stratified", "time_based"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        method = self._get_method(config, "random")
        test_size = config.get("test_size", 0.2)
        val_size = config.get("val_size", 0.0)
        random_state = config.get("random_state", 42)
        stratify_column = config.get("stratify_column", config.get("column", ""))
        time_column = config.get("time_column", "")

        total_rows = len(df)

        if method == "stratified" and stratify_column and stratify_column in df.columns:
            train_df, test_df = self._stratified_split(df, stratify_column, test_size, random_state)
        elif method == "time_based" and time_column and time_column in df.columns:
            train_df, test_df = self._time_split(df, time_column, test_size)
        else:
            # Random split
            train_df = df.sample(frac=1 - test_size, random_state=random_state)
            test_df = df.drop(train_df.index)

        # Further split train into train + val if requested
        val_df = pd.DataFrame()
        if val_size > 0:
            val_frac = val_size / (1 - test_size)
            val_df = train_df.sample(frac=val_frac, random_state=random_state)
            train_df = train_df.drop(val_df.index)

        details = {
            "method": method,
            "total_rows": total_rows,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "val_rows": len(val_df),
            "train_pct": round(len(train_df) / total_rows * 100, 1),
            "test_pct": round(len(test_df) / total_rows * 100, 1),
        }

        if len(val_df) > 0:
            details["val_pct"] = round(len(val_df) / total_rows * 100, 1)

        extra_outputs = {
            "train_shape": str(train_df.shape),
            "test_shape": str(test_df.shape),
        }

        return TransformResult(
            df=train_df,  # Return train as primary df
            success=True,
            message=f"Split data: {len(train_df)} train / {len(test_df)} test" +
                    (f" / {len(val_df)} val" if len(val_df) > 0 else "") + f" ({method})",
            rows_affected=total_rows,
            columns_affected=[],
            details=details,
            extra_outputs={
                "train": train_df,
                "test": test_df,
                "val": val_df,
                "split_method": method,
                "split_config": config,
            },
            duration_ms=int((time.time() - start) * 1000),
        )

    def _stratified_split(self, df, column, test_size, random_state):
        """Stratified split maintaining class distribution."""
        try:
            from sklearn.model_selection import train_test_split
            train_df, test_df = train_test_split(
                df, test_size=test_size, random_state=random_state,
                stratify=df[column]
            )
            return train_df, test_df
        except ImportError:
            # Manual stratified split
            train_parts, test_parts = [], []
            for label, group in df.groupby(column):
                test_n = max(1, int(len(group) * test_size))
                test_idx = group.sample(n=test_n, random_state=random_state).index
                test_parts.append(group.loc[test_idx])
                train_parts.append(group.drop(test_idx))
            return pd.concat(train_parts), pd.concat(test_parts)

    def _time_split(self, df, column, test_size):
        """Time-based split - use earliest data for train, latest for test."""
        df_sorted = df.sort_values(column)
        split_idx = int(len(df_sorted) * (1 - test_size))
        return df_sorted.iloc[:split_idx], df_sorted.iloc[split_idx:]
