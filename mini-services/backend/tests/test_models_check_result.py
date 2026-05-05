"""
Test: models/check_result.py
Verifies CheckResult matches your QualityCheck DB columns:
  ruleId, datasetId, status, score, recordsChecked, recordsFailed, duration, failures
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.check_result import CheckResult


# ── Defaults ──


def test_check_result_defaults():
    r = CheckResult()
    assert r.rule_id == ""
    assert r.dataset_id is None
    assert r.status == "passed"
    assert r.score == 100.0
    assert r.records_checked == 0
    assert r.records_failed == 0
    assert r.duration == 0
    assert r.failures == []


# ── Match your DB column names ──


def test_matches_your_db_passed():
    """Simulates a passed check stored in your QualityCheck table."""
    r = CheckResult(
        rule_id="abc123",
        dataset_id="ds456",
        status="passed",
        score=98.5,
        records_checked=1250000,
        records_failed=18750,
        duration=2340,
        failures=[],
    )
    assert r.rule_id == "abc123"
    assert r.dataset_id == "ds456"
    assert r.status == "passed"
    assert r.score == 98.5
    assert r.records_checked == 1250000
    assert r.records_failed == 18750
    assert r.duration == 2340
    assert r.failures == []


def test_matches_your_db_failed():
    """Simulates a failed check stored in your QualityCheck table."""
    r = CheckResult(
        rule_id="xyz789",
        dataset_id="ds456",
        status="failed",
        score=42.3,
        records_checked=4500000,
        records_failed=2599500,
        duration=5600,
        failures=[
            {"row": 5, "column": "amount", "value": "-15.99", "reason": "Below minimum"}
        ],
    )
    assert r.status == "failed"
    assert r.score == 42.3
    assert r.records_failed == 2599500
    assert len(r.failures) == 1


# ── Serialization ──


def test_failures_serialize_to_json():
    """failures column stores JSON string in your DB."""
    import json

    r = CheckResult(failures=[{"row": 1, "value": "NULL"}])
    raw = json.dumps(r.failures)
    parsed = json.loads(raw)
    assert parsed[0]["row"] == 1


def test_score_is_float():
    r = CheckResult(score=99.9)
    assert isinstance(r.score, float)


def test_status_values():
    """status must be 'passed' or 'failed' matching your DB."""
    r1 = CheckResult(status="passed")
    r2 = CheckResult(status="failed")
    assert r1.status == "passed"
    assert r2.status == "failed"


# ── Extra computed fields (not in DB, used internally) ──


def test_message_field():
    """message is for internal use, not stored in DB."""
    r = CheckResult(message="Column 'email': 98.5% complete")
    assert r.message == "Column 'email': 98.5% complete"


def test_pass_rate_field():
    """pass_rate is computed, not stored in DB."""
    r = CheckResult(pass_rate=98.5)
    assert r.pass_rate == 98.5


def test_table_name_field():
    r = CheckResult(table_name="users")
    assert r.table_name == "users"


def test_column_name_field():
    r = CheckResult(column_name="email")
    assert r.column_name == "email"
