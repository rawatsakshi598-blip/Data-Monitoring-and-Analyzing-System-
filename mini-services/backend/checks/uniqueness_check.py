"""
Uniqueness Check
Detects duplicate records.
Pillar: UNIQUENESS — "No unwanted duplicates?"
"""

import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class UniquenessCheck(BaseCheck):
    check_type = "uniqueness"
    description = "Check for duplicate values in columns"
    supported_rule_types = ["uniqueness", "unique", "duplicate"]

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

        # Count duplicates
        duplicated_mask = df[column].duplicated(keep=False)
        duplicate_count = int(duplicated_mask.sum())
        unique_count = total_rows - duplicate_count
        uniqueness_rate = (unique_count / total_rows * 100) if total_rows > 0 else 100.0

        # Threshold: default 100% uniqueness (no duplicates allowed)
        threshold = config.threshold if config.threshold else 100.0
        passed = uniqueness_rate >= threshold

        # Get samples of duplicated values
        failed_samples = self._get_failed_samples(df, duplicated_mask, column)

        # Show what values are duplicated
        dup_values = df[duplicated_mask][column].value_counts().head(5).to_dict()
        dup_info = [f"{v} (×{c})" for v, c in dup_values.items()]

        message = (
            f"Column '{column}': {uniqueness_rate:.1f}% unique "
            f"({duplicate_count}/{total_rows} duplicate rows). "
            f"Top duplicates: {', '.join(dup_info[:3])}. "
            f"Threshold: {threshold}%"
        )

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column,
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=unique_count,
            failed_rows=duplicate_count,
            metric_value=uniqueness_rate,
            threshold_value=threshold,
            failed_samples=failed_samples,
            execution_time_ms=self._end_timer(start),
        )
