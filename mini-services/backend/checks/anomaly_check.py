"""
Anomaly Check — Statistical anomaly detection
Uses Z-score for outlier detection and volume deviation analysis
Pure numpy/pandas — no external ML libraries needed
"""

import numpy as np
import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class AnomalyCheck(BaseCheck):
    check_type = "anomaly"
    description = "Detect statistical anomalies using Z-score and distribution analysis"
    supported_rule_types = ["anomaly", "outlier", "drift", "zscore"]

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

        # No column → volume anomaly check
        if not column:
            return self._check_volume_anomaly(df, config, rule_id, table_name, start)

        if column not in df.columns:
            return self._build_result(
                rule_id=rule_id, table_name=table_name, column_name=column,
                passed=False, message=f"Column '{column}' not found",
                total_rows=total_rows, passed_rows=0, failed_rows=total_rows,
                execution_time_ms=self._end_timer(start),
            )

        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 3:
            return self._build_result(
                rule_id=rule_id, table_name=table_name, column_name=column,
                passed=True, message=f"Not enough numeric data for anomaly detection ({len(series)} values)",
                total_rows=total_rows, passed_rows=total_rows, failed_rows=0,
                execution_time_ms=self._end_timer(start),
            )

        # ── Z-score outlier detection ──
        z_threshold = config.threshold or 3.0
        mean = float(series.mean())
        std = float(series.std())

        if std == 0:
            return self._build_result(
                rule_id=rule_id, table_name=table_name, column_name=column,
                passed=True, message=f"Column '{column}' has zero variance — no anomalies detectable",
                total_rows=total_rows, passed_rows=total_rows, failed_rows=0,
                metric_value=0, threshold_value=z_threshold,
                execution_time_ms=self._end_timer(start),
            )

        z_scores = ((series - mean) / std).abs()
        outlier_mask = z_scores > z_threshold
        outlier_count = int(outlier_mask.sum())
        outlier_pct = round(outlier_count / len(series) * 100, 2)

        passed = outlier_pct < 5.0  # Fail if >5% are outliers

        outlier_values = series[outlier_mask].head(5).tolist()
        samples = []
        for v in outlier_values:
            z_val = float(z_scores.loc[series == v].iloc[0])
            samples.append({"value": v, "z_score": round(z_val, 2)})

        message = (
            f"Column '{column}': {outlier_count} outliers ({outlier_pct}%) "
            f"via Z-score > {z_threshold}. "
            f"Mean={round(mean, 2)}, Std={round(std, 2)}. "
            f"Top: {outlier_values[:3]}"
        )

        return self._build_result(
            rule_id=rule_id, table_name=table_name, column_name=column,
            passed=passed, message=message,
            total_rows=total_rows, passed_rows=len(series) - outlier_count,
            failed_rows=outlier_count,
            metric_value=outlier_pct, threshold_value=z_threshold,
            failed_samples=samples,
            execution_time_ms=self._end_timer(start),
        )

    def _check_volume_anomaly(self, df, config, rule_id, table_name, start):
        """Detect volume anomalies — row count deviation from expected."""
        total_rows = len(df)
        expected = config.threshold or 1000
        tolerance = config.max_value if config.max_value is not None else 0.5

        deviation = abs(total_rows - expected) / expected if expected > 0 else 0
        deviation_pct = round(deviation * 100, 1)
        passed = deviation <= tolerance
        direction = "above" if total_rows > expected else "below"

        message = (
            f"Volume anomaly: {total_rows} rows, expected ~{expected}. "
            f"Deviation: {deviation_pct}% {direction} expected (tolerance: {tolerance * 100}%)."
        )

        return self._build_result(
            rule_id=rule_id, table_name=table_name, column_name="",
            passed=passed, message=message,
            total_rows=total_rows,
            passed_rows=total_rows if passed else 0,
            failed_rows=0 if passed else abs(total_rows - int(expected)),
            metric_value=deviation_pct, threshold_value=tolerance * 100,
            execution_time_ms=self._end_timer(start),
        )
