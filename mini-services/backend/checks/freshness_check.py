"""
Freshness Check
Alerts if data hasn't been updated within expected time.
Pillar: TIMELINESS — "Is data fresh/up-to-date?"
"""

import pandas as pd
from datetime import datetime, timedelta
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class FreshnessCheck(BaseCheck):
    check_type = "freshness"
    description = "Check if data is fresh (updated recently)"
    supported_rule_types = ["freshness", "timeliness"]

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

        # Parse timestamp column
        try:
            ts_col = pd.to_datetime(df[column], errors="coerce")
        except Exception:
            return self._build_result(
                rule_id=rule_id,
                table_name=table_name,
                column_name=column,
                passed=False,
                message=f"Column '{column}' is not a valid timestamp",
                total_rows=total_rows,
                passed_rows=0,
                failed_rows=total_rows,
                metric_value=0,
                threshold_value=0,
                failed_samples=[],
                execution_time_ms=self._end_timer(start),
            )

        # Get the most recent timestamp
        max_ts = ts_col.max()
        if pd.isna(max_ts):
            return self._build_result(
                rule_id=rule_id,
                table_name=table_name,
                column_name=column,
                passed=False,
                message=f"No valid timestamps in '{column}'",
                total_rows=total_rows,
                passed_rows=0,
                failed_rows=total_rows,
                metric_value=0,
                threshold_value=0,
                failed_samples=[],
                execution_time_ms=self._end_timer(start),
            )

        # Calculate age in hours
        now = datetime.now()
        age_hours = (now - max_ts).total_seconds() / 3600

        # Threshold: default 24 hours
        max_age_hours = config.threshold if config.threshold else 24.0
        passed = age_hours <= max_age_hours

        # Count stale rows (older than threshold)
        cutoff = now - timedelta(hours=max_age_hours)
        stale_mask = ts_col < cutoff
        stale_count = int(stale_mask.sum())

        message = (
            f"Column '{column}': Latest data is {age_hours:.1f} hours old "
            f"(max allowed: {max_age_hours}h). "
            f"Newest: {max_ts}, Stale rows: {stale_count}/{total_rows}"
        )

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column,
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=total_rows - stale_count,
            failed_rows=stale_count,
            metric_value=age_hours,
            threshold_value=max_age_hours,
            failed_samples=[],
            execution_time_ms=self._end_timer(start),
        )
