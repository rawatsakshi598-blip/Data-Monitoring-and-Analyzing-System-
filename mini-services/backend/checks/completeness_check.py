"""
Completeness Check
Monitors for null values, missing records, incomplete fields.
Pillar: COMPLETENESS — "Are all required fields filled?"
"""

import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class CompletenessCheck(BaseCheck):
    check_type = "completeness"
    description = "Check for null/missing values in columns"
    supported_rule_types = ["completeness", "missing", "not_null"]

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

        # Count nulls
        null_mask = df[column].isna() | (df[column].astype(str).str.strip() == "")
        null_count = int(null_mask.sum())
        non_null_count = total_rows - null_count
        completeness_rate = (
            (non_null_count / total_rows * 100) if total_rows > 0 else 100.0
        )

        # Threshold: default 95% completeness required
        threshold = config.threshold if config.threshold else 95.0
        max_null_pct = (
            config.max_null_percent if config.max_null_percent else (100 - threshold)
        )
        passed = completeness_rate >= threshold

        # Get samples of failed rows
        failed_samples = self._get_failed_samples(df, null_mask, column)

        message = (
            f"Column '{column}': {completeness_rate:.1f}% complete "
            f"({null_count}/{total_rows} null values). "
            f"Threshold: {threshold}%"
        )

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column,
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=non_null_count,
            failed_rows=null_count,
            metric_value=completeness_rate,
            threshold_value=threshold,
            failed_samples=failed_samples,
            execution_time_ms=self._end_timer(start),
        )
