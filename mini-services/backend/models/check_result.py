"""
Check Result Models
Field names match YOUR QualityCheck DB columns exactly:
  ruleId, datasetId, status, score, recordsChecked, recordsFailed, duration, failures

Extra fields (message, pass_rate, table_name, column_name) are computed internally,
NOT stored in DB. They're used by checks and reports.
"""

from pydantic import BaseModel
from typing import Optional


class CheckResult(BaseModel):
    """Result of a single check execution."""

    # ── Fields that match your DB columns ──
    rule_id: str = ""
    dataset_id: Optional[str] = None
    status: str = "passed"  # passed, failed
    score: float = 100.0
    records_checked: int = 0
    records_failed: int = 0
    duration: int = 0  # milliseconds
    failures: list = []  # JSON array stored in DB

    # ── Computed fields (NOT in DB, used internally) ──
    message: str = ""
    pass_rate: float = 100.0
    table_name: str = ""
    column_name: str = ""
    metric_value: float = 0.0
    threshold_value: float = 0.0
    failed_samples: list = []


class RunRulesRequest(BaseModel):
    """Request to run rules against data."""

    table_name: str = ""
    dataset_id: Optional[str] = None
    rule_ids: Optional[list[str]] = None
