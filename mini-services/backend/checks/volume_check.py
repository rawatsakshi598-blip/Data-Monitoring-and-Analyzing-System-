"""
Volume Check
Detects unusual spikes or drops in row counts.
Pillar: COMPLETENESS (volume dimension)
"""

import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class VolumeCheck(BaseCheck):
    check_type = "volume"
    description = "Check if row count is within expected range"
    supported_rule_types = ["volume", "row_count"]

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

        # Check row count against min/max
        min_rows = config.min_value if config.min_value is not None else 0
        max_rows = config.max_value if config.max_value is not None else float("inf")
        threshold = config.threshold  # used as expected row count

        passed = min_rows <= total_rows <= max_rows

        if threshold and threshold > 0:
            deviation = abs(total_rows - threshold) / threshold * 100
            passed = passed and deviation <= 50  # max 50% deviation

        message = (
            f"Table '{table_name}': {total_rows} rows. "
            f"Expected range: [{min_rows}, {max_rows if max_rows != float('inf') else '∞'}]"
        )
        if threshold:
            message += f", expected: ~{int(threshold)}"

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name="",
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=total_rows if passed else 0,
            failed_rows=0 if passed else total_rows,
            metric_value=total_rows,
            threshold_value=threshold or 0,
            failed_samples=[],
            execution_time_ms=self._end_timer(start),
        )
