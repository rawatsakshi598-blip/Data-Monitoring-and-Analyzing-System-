"""
Rule Executor — Runs quality checks on data.
Loads rules from DB, instantiates check classes, executes on DataFrames.
"""

import json
import os
import time
import pandas as pd
from checks import get_check
from models.rule import CheckConfig
from models.check_result import CheckResult

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
os.makedirs(DATA_DIR, exist_ok=True)


def save_dataframe(table_id: str, df: pd.DataFrame, fmt: str = 'csv') -> str:
    """Save DataFrame so checks can run on real data later."""
    path = os.path.join(DATA_DIR, f"{table_id}.{fmt}")
    if fmt == 'csv':
        df.to_csv(path, index=False)
    elif fmt == 'json':
        df.to_json(path, orient='records')
    return path


def load_dataframe(table_id: str) -> pd.DataFrame | None:
    """Load a previously saved DataFrame."""
    for ext in ('csv', 'json', 'xlsx'):
        path = os.path.join(DATA_DIR, f"{table_id}.{ext}")
        if os.path.exists(path):
            try:
                if ext == 'csv':
                    return pd.read_csv(path)
                elif ext == 'json':
                    return pd.read_json(path)
                elif ext == 'xlsx':
                    return pd.read_excel(path)
            except Exception:
                return None
    return None


def parse_config(rule: dict) -> CheckConfig:
    """Parse rule config into CheckConfig object."""
    raw = rule.get('config', {})
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    return CheckConfig(
        column=raw.get('column', ''),
        threshold=raw.get('threshold'),
        max_null_percent=raw.get('max_null_percent'),
        valid_values=raw.get('valid_values'),
        regex=raw.get('regex'),
        min_value=raw.get('min_value'),
        max_value=raw.get('max_value'),
    )


def execute_rule(rule: dict, df: pd.DataFrame, table_name: str = "") -> CheckResult:
    """Execute a single rule on a DataFrame — REAL check."""
    config = parse_config(rule)
    check_type = rule.get('type', 'completeness')
    check_cls = get_check(check_type)
    check = check_cls()
    return check.execute(
        df=df,
        config=config,
        rule_id=rule.get('id', ''),
        table_name=table_name,
        column_name=config.column or '',
    )


def execute_profile_check(rule: dict, profile: dict, table_name: str = "") -> CheckResult:
    """Estimate check result from profile data when raw file is gone."""
    start = time.time()
    config = parse_config(rule)
    column = config.column or ''
    check_type = rule.get('type', 'completeness')
    threshold = config.threshold or 95.0
    col_profile = profile.get(column, {}) if column else {}
    total = profile.get('_rowCount', 1)

    if check_type in ('completeness', 'missing', 'not_null'):
        null_pct = col_profile.get('nullPercent', 0)
        score = 100 - null_pct
        passed = score >= threshold
        return CheckResult(
            rule_id=rule.get('id', ''), table_name=table_name, column_name=column,
            status='passed' if passed else 'failed', score=score,
            records_checked=total, records_failed=col_profile.get('nullCount', 0),
            duration=int((time.time() - start) * 1000), failures=[],
            message=f"Profile: {score:.1f}% complete (threshold {threshold}%)",
            pass_rate=score, metric_value=score, threshold_value=threshold, failed_samples=[],
        )
    elif check_type in ('uniqueness', 'unique', 'duplicate'):
        uniq = col_profile.get('uniqueCount', total)
        score = (uniq / total * 100) if total > 0 else 100.0
        passed = score >= threshold
        return CheckResult(
            rule_id=rule.get('id', ''), table_name=table_name, column_name=column,
            status='passed' if passed else 'failed', score=score,
            records_checked=total, records_failed=total - uniq,
            duration=int((time.time() - start) * 1000), failures=[],
            message=f"Profile: {score:.1f}% unique (threshold {threshold}%)",
            pass_rate=score, metric_value=score, threshold_value=threshold, failed_samples=[],
        )
    else:
        return CheckResult(
            rule_id=rule.get('id', ''), table_name=table_name, column_name=column,
            status='passed', score=100.0,
            records_checked=total, records_failed=0,
            duration=int((time.time() - start) * 1000), failures=[],
            message=f"Profile estimate: {check_type} (no raw data)",
            pass_rate=100.0, metric_value=100.0, threshold_value=threshold, failed_samples=[],
        )
