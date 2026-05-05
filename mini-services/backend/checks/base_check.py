"""
Base Check — Abstract base class for all quality checks.
Every check inherits this and implements execute().
"""

from abc import ABC, abstractmethod
import pandas as pd
import time
from models.check_result import CheckResult
from models.rule import CheckConfig


class BaseCheck(ABC):
    check_type: str = "base"
    description: str = "Base check"
    supported_types: list[str] = []

    @abstractmethod
    def execute(
        self,
        df: pd.DataFrame,
        config: CheckConfig,
        rule_id: str = "",
        table_name: str = "",
        column_name: str = "",
        **kwargs,
    ) -> CheckResult:
        """Run the check and return a CheckResult."""
        pass

    def _start_timer(self) -> float:
        return time.time()

    def _timer(self) -> float:
        return self._start_timer()

    def _end_timer(self, start: float) -> int:
        return int((time.time() - start) * 1000)

    def _elapsed(self, start: float) -> int:
        return self._end_timer(start)

    def _get_failed_samples(
        self, df: pd.DataFrame, mask: pd.Series, column: str, n: int = 10
    ) -> list[dict]:
        failed = df[mask].head(n)
        cols_to_show = [column] + [c for c in df.columns[:3] if c != column]
        return [
            {col: row.get(col, "N/A") for col in cols_to_show}
            for _, row in failed.iterrows()
        ]

    def _failed_samples(
        self, df: pd.DataFrame, mask: pd.Series, column: str, n: int = 10
    ) -> list[dict]:
        return self._get_failed_samples(df, mask, column, n)

    def _build_result(
        self,
        *,
        rule_id: str = "",
        table_name: str = "",
        column_name: str = "",
        status: str = None,
        score: float = None,
        records_checked: int = None,
        records_failed: int = None,
        duration: int = None,
        message: str = "",
        metric_value: float = 0.0,
        threshold_value: float = 0.0,
        failed_samples: list = None,
        # Aliases that checks actually use
        passed: bool = None,
        total_rows: int = None,
        passed_rows: int = None,
        failed_rows: int = None,
        execution_time_ms: int = None,
    ) -> CheckResult:
        # Map alias params to canonical ones
        if passed is not None and status is None:
            status = "passed" if passed else "failed"
        if status is None:
            status = "passed"
        if score is None:
            score = 100.0 if passed else 0.0
        if total_rows is not None and records_checked is None:
            records_checked = total_rows
        if records_checked is None:
            records_checked = 0
        if failed_rows is not None and records_failed is None:
            records_failed = failed_rows
        if records_failed is None:
            records_failed = 0
        if execution_time_ms is not None and duration is None:
            duration = execution_time_ms
        if duration is None:
            duration = 0

        pass_rate = (
            round((records_checked - records_failed) / records_checked * 100, 2)
            if records_checked > 0
            else 100.0
        )

        return CheckResult(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column_name,
            status=status,
            score=score,
            records_checked=records_checked,
            records_failed=records_failed,
            duration=duration,
            failures=failed_samples[:10] if failed_samples else [],
            message=message,
            pass_rate=pass_rate,
            metric_value=metric_value,
            threshold_value=threshold_value,
            failed_samples=failed_samples or [],
        )
