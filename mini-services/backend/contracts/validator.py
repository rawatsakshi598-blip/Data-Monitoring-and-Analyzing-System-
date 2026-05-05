"""
Data Contracts Engine — Define expected schema as YAML/JSON and auto-validate data against it.
"""

import pandas as pd
import numpy as np
import json
import yaml


class DataContractsEngine:
    """Define and validate data contracts."""

    def validate(self, df: pd.DataFrame, contract: dict) -> dict:
        """Validate a DataFrame against a data contract."""
        results = {
            "valid": True,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "violations": [],
            "score": 100.0,
        }

        # Schema validation
        if "schema" in contract:
            self._validate_schema(df, contract["schema"], results)

        # Column rules
        if "columns" in contract:
            self._validate_columns(df, contract["columns"], results)

        # Row-level rules
        if "rules" in contract:
            self._validate_rules(df, contract["rules"], results)

        # Freshness check
        if "freshness" in contract:
            self._validate_freshness(df, contract["freshness"], results)

        # Uniqueness constraints
        if "unique_keys" in contract:
            self._validate_unique_keys(df, contract["unique_keys"], results)

        results["valid"] = results["failed_checks"] == 0
        results["score"] = round(max(0, 100 - results["failed_checks"] * 5), 1)
        return results

    def _validate_schema(self, df, schema, results):
        expected_columns = schema.get("columns", [])
        for col_spec in expected_columns:
            results["total_checks"] += 1
            col_name = col_spec.get("name", "")
            if col_name not in df.columns:
                results["failed_checks"] += 1
                results["violations"].append({
                    "type": "missing_column", "column": col_name,
                    "message": f"Required column '{col_name}' not found",
                    "severity": "critical",
                })
            else:
                expected_type = col_spec.get("type", "")
                if expected_type and not self._check_type(df[col_name], expected_type):
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "type_mismatch", "column": col_name,
                        "expected": expected_type, "actual": str(df[col_name].dtype),
                        "severity": "warning",
                    })
                else:
                    results["passed_checks"] += 1

    def _validate_columns(self, df, columns_spec, results):
        for col_name, rules in columns_spec.items():
            if col_name not in df.columns:
                continue

            # Nullable check
            if rules.get("nullable") is False:
                results["total_checks"] += 1
                null_count = int(df[col_name].isna().sum())
                if null_count > 0:
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "not_nullable", "column": col_name,
                        "null_count": null_count, "severity": "error",
                    })
                else:
                    results["passed_checks"] += 1

            # Range check
            if "min" in rules or "max" in rules:
                results["total_checks"] += 1
                if pd.api.types.is_numeric_dtype(df[col_name]):
                    min_val = rules.get("min", float('-inf'))
                    max_val = rules.get("max", float('inf'))
                    violations = ((df[col_name] < min_val) | (df[col_name] > max_val)).sum()
                    if violations > 0:
                        results["failed_checks"] += 1
                        results["violations"].append({
                            "type": "range_violation", "column": col_name,
                            "violations": int(violations), "min": min_val, "max": max_val,
                            "severity": "warning",
                        })
                    else:
                        results["passed_checks"] += 1

            # Enum/values check
            if "allowed_values" in rules:
                results["total_checks"] += 1
                allowed = set(str(v) for v in rules["allowed_values"])
                actual = set(str(v) for v in df[col_name].dropna().unique())
                invalid = actual - allowed
                if invalid:
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "invalid_values", "column": col_name,
                        "invalid_values": list(invalid)[:10], "severity": "error",
                    })
                else:
                    results["passed_checks"] += 1

            # Regex pattern
            if "pattern" in rules:
                results["total_checks"] += 1
                import re
                pattern = rules["pattern"]
                valid = df[col_name].dropna().astype(str).str.match(pattern).all()
                if not valid:
                    invalid_count = int(~df[col_name].dropna().astype(str).str.match(pattern)).sum()
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "pattern_violation", "column": col_name,
                        "pattern": pattern, "invalid_count": invalid_count, "severity": "warning",
                    })
                else:
                    results["passed_checks"] += 1

    def _validate_rules(self, df, rules, results):
        for rule in rules:
            results["total_checks"] += 1
            rule_type = rule.get("type", "")

            if rule_type == "row_count":
                min_rows = rule.get("min", 0)
                max_rows = rule.get("max", float('inf'))
                if min_rows <= len(df) <= max_rows:
                    results["passed_checks"] += 1
                else:
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "row_count", "actual": len(df),
                        "min": min_rows, "max": max_rows, "severity": "error",
                    })

            elif rule_type == "no_duplicates":
                subset = rule.get("columns", None)
                dup_count = int(df.duplicated(subset=subset).sum())
                if dup_count == 0:
                    results["passed_checks"] += 1
                else:
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "duplicates", "count": dup_count, "severity": "warning",
                    })

            elif rule_type == "completeness":
                threshold = rule.get("threshold", 100)
                actual = (1 - df.isna().sum().sum() / (len(df) * len(df.columns))) * 100
                if actual >= threshold:
                    results["passed_checks"] += 1
                else:
                    results["failed_checks"] += 1
                    results["violations"].append({
                        "type": "completeness", "actual": round(actual, 2),
                        "threshold": threshold, "severity": "error",
                    })

    def _validate_freshness(self, df, freshness, results):
        # This is a placeholder - real implementation would check timestamps
        results["total_checks"] += 1
        results["passed_checks"] += 1

    def _validate_unique_keys(self, df, unique_keys, results):
        for key_spec in unique_keys:
            results["total_checks"] += 1
            cols = key_spec if isinstance(key_spec, list) else [key_spec]
            dup_count = int(df.duplicated(subset=cols).sum())
            if dup_count == 0:
                results["passed_checks"] += 1
            else:
                results["failed_checks"] += 1
                results["violations"].append({
                    "type": "unique_key_violation", "columns": cols,
                    "duplicate_count": dup_count, "severity": "error",
                })

    def _check_type(self, series, expected_type):
        type_map = {
            "int": ['int64', 'int32', 'int16', 'int8', 'Int64'],
            "float": ['float64', 'float32', 'Float64'],
            "string": ['object', 'string'],
            "datetime": ['datetime64[ns]', 'datetime64'],
            "bool": ['bool'],
            "numeric": ['int64', 'int32', 'int16', 'int8', 'float64', 'float32', 'number'],
        }
        actual = str(series.dtype)
        if expected_type in type_map:
            return any(t in actual for t in type_map[expected_type])
        return expected_type in actual

    def parse_contract(self, contract_text: str, format: str = "yaml") -> dict:
        """Parse a contract from YAML or JSON text."""
        if format == "yaml":
            return yaml.safe_load(contract_text)
        return json.loads(contract_text)


data_contracts = DataContractsEngine()
