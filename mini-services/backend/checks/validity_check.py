"""
Validity Check
Checks if values conform to expected formats, ranges, or value sets.
Pillar: VALIDITY — "Does data conform to rules?"
"""

import re
import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class ValidityCheck(BaseCheck):
    check_type = "validity"
    description = "Check if values match expected format, range, or value set"
    supported_rule_types = ["validity", "valid_values", "regex", "range"]

    def execute(
        self,
        df: pd.DataFrame,
        config: CheckConfig,
        rule_id: str = "",
        table_name: str = "",
        column_name: str = "",
        **kwargs,
    ) -> CheckResult:
        start = self._start_timer()
        total_rows = len(df)
        column = config.column or column_name

        if not column or column not in df.columns:
            return self._build_result(
                rule_id=rule_id,
                table_name=table_name,
                column_name=column,
                passed=False,
                message=f"Column '{column}' not found",
                total_rows=total_rows,
                passed_rows=0,
                failed_rows=total_rows,
                metric_value=0,
                threshold_value=0,
                failed_samples=[],
                execution_time_ms=self._end_timer(start),
            )

        # Non-null values only
        non_null = df[column].dropna()
        non_null_count = len(non_null)

        # Determine which validity check to run
        if config.valid_values:
            invalid_mask = self._check_valid_values(non_null, config.valid_values)
        elif config.regex:
            invalid_mask = self._check_regex(non_null, config.regex)
        elif config.min_value is not None or config.max_value is not None:
            invalid_mask = self._check_range(
                non_null, config.min_value, config.max_value
            )
        else:
            return self._build_result(
                rule_id=rule_id,
                table_name=table_name,
                column_name=column,
                passed=False,
                message="No validity rule specified (valid_values, regex, or range)",
                total_rows=total_rows,
                passed_rows=0,
                failed_rows=total_rows,
                metric_value=0,
                threshold_value=0,
                failed_samples=[],
                execution_time_ms=self._end_timer(start),
            )

        # Calculate results
        invalid_count = int(invalid_mask.sum())
        valid_count = non_null_count - invalid_count
        validity_rate = (
            (valid_count / non_null_count * 100) if non_null_count > 0 else 100.0
        )

        threshold = config.threshold if config.threshold else 95.0
        passed = validity_rate >= threshold

        # Get full mask including nulls for samples
        full_invalid = pd.Series(False, index=df.index)
        full_invalid.loc[non_null.index] = invalid_mask
        failed_samples = self._get_failed_samples(df, full_invalid, column)

        rule_desc = ""
        if config.valid_values:
            rule_desc = f"valid_values={config.valid_values}"
        elif config.regex:
            rule_desc = f"regex='{config.regex}'"
        elif config.min_value is not None:
            rule_desc = f"range=[{config.min_value}, {config.max_value}]"

        message = (
            f"Column '{column}': {validity_rate:.1f}% valid "
            f"({invalid_count}/{non_null_count} invalid values). "
            f"Rule: {rule_desc}. Threshold: {threshold}%"
        )

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column,
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=valid_count,
            failed_rows=invalid_count,
            metric_value=validity_rate,
            threshold_value=threshold,
            failed_samples=failed_samples,
            execution_time_ms=self._end_timer(start),
        )

    def _check_valid_values(self, series: pd.Series, valid_values: list) -> pd.Series:
        """Check if values are in the allowed set."""
        return ~series.isin(valid_values)

    def _check_regex(self, series: pd.Series, pattern: str) -> pd.Series:
        """Check if values match regex pattern."""
        try:
            return ~series.astype(str).str.match(pattern, na=False)
        except re.error:
            return pd.Series(False, index=series.index)

    def _check_range(
        self, series: pd.Series, min_val: float = None, max_val: float = None
    ) -> pd.Series:
        """Check if numeric values are within range."""
        numeric = pd.to_numeric(series, errors="coerce")
        mask = pd.Series(False, index=series.index)
        if min_val is not None:
            mask = mask | (numeric < min_val)
        if max_val is not None:
            mask = mask | (numeric > max_val)
        # Values that couldn't be converted to numeric are invalid
        # BUT: only count them if there are SOME numeric values (otherwise it's a string column)
        numeric_count = numeric.notna().sum()
        if numeric_count > 0:
            # Some values are numeric — non-numeric ones are invalid
            mask = mask | numeric.isna()
        else:
            # ALL values are non-numeric — can't do range check, nothing is "invalid" by range
            # This prevents false failures on string columns
            pass
        return mask
