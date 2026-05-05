"""
String Clean Transformer — Clean and standardize string columns.
Methods: trim, lowercase, uppercase, title_case, regex_replace, remove_special, standardize_whitespace
"""

import pandas as pd
import re
from transformations.base_transformer import BaseTransformer, TransformResult


class StringCleanTransformer(BaseTransformer):
    """Clean and standardize string/categorical columns."""

    transform_type = "string_clean"
    description = "Clean and standardize string data"
    supported_methods = ["trim", "lowercase", "uppercase", "title_case", "regex_replace",
                         "remove_special", "standardize_whitespace", "snake_case", "camel_case"]

    def transform(self, df: pd.DataFrame, config: dict) -> TransformResult:
        import time
        start = time.time()
        column = self._get_column(config)
        method = self._get_method(config, "trim")
        columns = config.get("columns", [])
        pattern = config.get("pattern", config.get("regex", ""))
        replacement = config.get("replacement", "")

        target_columns = columns if columns else ([column] if column and column in df.columns else [])
        if not target_columns:
            target_columns = df.select_dtypes(include=['object', 'string']).columns.tolist()
        target_columns = [c for c in target_columns if c in df.columns]

        if not target_columns:
            return TransformResult(
                df=df, success=False, message="No string columns found to clean",
                duration_ms=int((time.time() - start) * 1000),
            )

        result_df = df.copy()
        total_changes = 0
        details = {}

        for col in target_columns:
            original = result_df[col].copy()
            result_df[col] = result_df[col].astype(str)

            if method == "trim":
                result_df[col] = result_df[col].str.strip()
            elif method == "lowercase":
                result_df[col] = result_df[col].str.lower()
            elif method == "uppercase":
                result_df[col] = result_df[col].str.upper()
            elif method == "title_case":
                result_df[col] = result_df[col].str.title()
            elif method == "regex_replace":
                if pattern:
                    result_df[col] = result_df[col].str.replace(pattern, replacement, regex=True)
            elif method == "remove_special":
                result_df[col] = result_df[col].apply(lambda x: re.sub(r'[^a-zA-Z0-9\s]', '', x))
            elif method == "standardize_whitespace":
                result_df[col] = result_df[col].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
            elif method == "snake_case":
                result_df[col] = result_df[col].apply(self._to_snake_case)
            elif method == "camel_case":
                result_df[col] = result_df[col].apply(self._to_camel_case)

            # Restore NaN values
            result_df.loc[original.isna(), col] = None

            changes = int((original.astype(str) != result_df[col].astype(str)).sum())
            total_changes += changes
            details[col] = {"method": method, "values_changed": changes}

        return TransformResult(
            df=result_df,
            success=True,
            message=f"Cleaned {len(target_columns)} string columns: {total_changes} values changed via {method}",
            rows_affected=total_changes,
            columns_affected=target_columns,
            details=details,
            duration_ms=int((time.time() - start) * 1000),
        )

    @staticmethod
    def _to_snake_case(s):
        s = re.sub(r'[^a-zA-Z0-9]', ' ', str(s))
        return re.sub(r'\s+', '_', s.strip()).lower()

    @staticmethod
    def _to_camel_case(s):
        parts = re.sub(r'[^a-zA-Z0-9]', ' ', str(s)).split()
        return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:]) if parts else s
