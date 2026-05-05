"""
Date Parser Transformer — Parse dates and extract features.
Methods: parse, extract_features, to_format
"""

import pandas as pd
import numpy as np
from transformations.base_transformer import BaseTransformer, TransformResult


class DateParserTransformer(BaseTransformer):
    """Parse date strings and extract temporal features."""

    transform_type = "date_parse"
    description = "Parse date strings and extract date/time features"
    supported_methods = ["parse", "extract_features", "to_format", "auto_detect"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "parse")
        columns = config.get("columns", [])
        date_format = config.get("format", config.get("date_format", None))
        output_format = config.get("output_format", "%Y-%m-%d")
        features = config.get("features", ["year", "month", "day", "dayofweek", "quarter"])

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        target_columns = [c for c in target_columns if c in df.columns]

        if not target_columns:
            # Auto-detect date-like columns
            target_columns = self._detect_date_columns(df)
            if not target_columns:
                return TransformResult(
                    df=df, success=False, message="No date-like columns found",
                    duration_ms=int((time.time() - start) * 1000),
                )

        result_df = df.copy()
        all_new_cols = []
        details = {}

        for col in target_columns:
            if method == "parse" or method == "auto_detect":
                result_df[col] = self._parse_dates(result_df[col], date_format)
                details[col] = {"method": "parse", "parsed_count": int(pd.to_datetime(result_df[col], errors='coerce').notna().sum())}
            elif method == "extract_features":
                result_df, new_cols = self._extract_features(result_df, col, features)
                all_new_cols.extend(new_cols)
                details[col] = {"method": "extract_features", "new_columns": new_cols}
            elif method == "to_format":
                parsed = pd.to_datetime(result_df[col], errors='coerce')
                result_df[col] = parsed.dt.strftime(output_format)
                details[col] = {"method": "to_format", "output_format": output_format}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Date processing: {method} on {len(target_columns)} columns, {len(all_new_cols)} features extracted",
            rows_affected=len(df),
            columns_affected=target_columns + all_new_cols,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    def _detect_date_columns(self, df):
        """Auto-detect columns that look like dates."""
        date_cols = []
        for col in df.columns:
            if df[col].dtype == 'object':
                sample = df[col].dropna().head(20)
                if len(sample) > 0:
                    try:
                        parsed = pd.to_datetime(sample, errors='coerce')
                        if parsed.notna().sum() / len(sample) > 0.8:
                            date_cols.append(col)
                    except Exception:
                        pass
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                date_cols.append(col)
        return date_cols

    def _parse_dates(self, series, date_format=None):
        if date_format:
            return pd.to_datetime(series, format=date_format, errors='coerce')
        return pd.to_datetime(series, errors='coerce')

    def _extract_features(self, df, col, features):
        parsed = pd.to_datetime(df[col], errors='coerce')
        new_cols = []

        feature_map = {
            "year": lambda s: s.dt.year,
            "month": lambda s: s.dt.month,
            "day": lambda s: s.dt.day,
            "hour": lambda s: s.dt.hour,
            "minute": lambda s: s.dt.minute,
            "dayofweek": lambda s: s.dt.dayofweek,
            "dayofyear": lambda s: s.dt.dayofyear,
            "quarter": lambda s: s.dt.quarter,
            "weekofyear": lambda s: s.dt.isocalendar().week.astype(int),
            "is_weekend": lambda s: s.dt.dayofweek.isin([5, 6]).astype(int),
            "is_month_start": lambda s: s.dt.is_month_start.astype(int),
            "is_month_end": lambda s: s.dt.is_month_end.astype(int),
        }

        for feat in features:
            if feat in feature_map:
                new_col = f"{col}_{feat}"
                try:
                    df[new_col] = feature_map[feat](parsed)
                    new_cols.append(new_col)
                except Exception:
                    pass

        return df, new_cols
