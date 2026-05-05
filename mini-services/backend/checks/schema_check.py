"""
Schema Check
Detects unexpected schema changes (columns added/removed/type changes).
Pillar: CONFORMITY — "Correct format/standards?"
"""

import pandas as pd
from checks.base_check import BaseCheck
from models.check_result import CheckResult
from models.rule import CheckConfig


class SchemaCheck(BaseCheck):
    check_type = "schema"
    description = "Detect schema changes (columns added/removed/type changes)"
    supported_rule_types = ["schema", "schema_change"]

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

        # Expected columns from config
        expected_columns = config.valid_values  # list of expected column names
        if not expected_columns:
            # If no expected columns specified, just report current schema
            current_cols = list(df.columns)
            current_types = {col: str(df[col].dtype) for col in current_cols}
            return self._build_result(
                rule_id=rule_id,
                table_name=table_name,
                column_name="",
                passed=True,
                message=f"Schema: {len(current_cols)} columns detected. No expected schema defined.",
                total_rows=total_rows,
                passed_rows=total_rows,
                failed_rows=0,
                metric_value=len(current_cols),
                threshold_value=0,
                failed_samples=[{"columns": current_cols, "types": current_types}],
                execution_time_ms=self._end_timer(start),
            )

        # Compare actual vs expected
        actual_cols = set(df.columns)
        expected_cols = set(expected_columns)

        missing_cols = expected_cols - actual_cols
        extra_cols = actual_cols - expected_cols

        passed = len(missing_cols) == 0 and len(extra_cols) == 0

        issues = []
        if missing_cols:
            issues.append(f"Missing columns: {', '.join(missing_cols)}")
        if extra_cols:
            issues.append(f"Extra columns: {', '.join(extra_cols)}")

        message = (
            f"Schema check: {'PASS' if passed else 'FAIL'}. "
            f"Expected {len(expected_cols)} columns, found {len(actual_cols)}. "
            + ("; ".join(issues) if issues else "Schema matches expected.")
        )

        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name="",
            passed=passed,
            message=message,
            total_rows=total_rows,
            passed_rows=total_rows if passed else 0,
            failed_rows=len(missing_cols) + len(extra_cols),
            metric_value=len(actual_cols & expected_cols),
            threshold_value=len(expected_cols),
            failed_samples=[
                {"missing_columns": list(missing_cols)},
                {"extra_columns": list(extra_cols)},
            ],
            execution_time_ms=self._end_timer(start),
        )
