"""
Test: checks/base_check.py
Verifies BaseCheck provides correct timer, result builder, and failed samples.
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from checks.base_check import BaseCheck
from models.rule import CheckConfig
from models.check_result import CheckResult


# ── Concrete implementation for testing ──


class FakeCheck(BaseCheck):
    check_type = "fake"
    description = "Fake check for testing"
    supported_types = ["fake", "test"]

    def execute(self, df, config, rule_id="", table_name="", column_name=""):
        start = self._timer()
        return self._build_result(
            rule_id=rule_id,
            table_name=table_name,
            column_name=column_name,
            status="passed",
            score=100.0,
            records_checked=len(df),
            records_failed=0,
            duration=self._elapsed(start),
            message="All good",
        )


check = FakeCheck()


# ── Timer Tests ──


def test_timer_returns_float():
    t = check._timer()
    assert isinstance(t, float)


def test_elapsed_returns_int():
    start = check._timer()
    elapsed = check._elapsed(start)
    assert isinstance(elapsed, int)
    assert elapsed >= 0


def test_elapsed_is_milliseconds():
    import time

    start = check._timer()
    time.sleep(0.01)
    elapsed = check._elapsed(start)
    assert elapsed >= 5  # at least 5ms for 10ms sleep


# ── Result Builder Tests ──


def test_build_result_passed():
    df = pd.DataFrame({"a": [1, 2, 3]})
    r = check.execute(
        df, CheckConfig(), rule_id="r1", table_name="users", column_name="email"
    )
    assert isinstance(r, CheckResult)
    assert r.rule_id == "r1"
    assert r.table_name == "users"
    assert r.column_name == "email"
    assert r.status == "passed"
    assert r.score == 100.0
    assert r.records_checked == 3
    assert r.records_failed == 0
    assert r.duration >= 0
    assert r.message == "All good"


def test_build_result_failed():
    df = pd.DataFrame({"a": [1, 2, 3]})
    r = check._build_result(
        rule_id="r2",
        table_name="orders",
        column_name="amount",
        status="failed",
        score=42.3,
        records_checked=1000,
        records_failed=577,
        duration=150,
        message="42.3% valid",
    )
    assert r.status == "failed"
    assert r.score == 42.3
    assert r.records_checked == 1000
    assert r.records_failed == 577


def test_build_result_pass_rate_calculated():
    r = check._build_result(
        rule_id="r3",
        table_name="t",
        column_name="c",
        status="passed",
        score=95.0,
        records_checked=100,
        records_failed=5,
        duration=10,
        message="test",
    )
    assert r.pass_rate == 95.0


# ── Failed Samples Tests ──


def test_failed_samples_returns_rows():
    df = pd.DataFrame({"email": ["a@b.com", None, "c@d.com", "", "e@f.com"]})
    mask = df["email"].isna() | (df["email"].astype(str).str.strip() == "")
    samples = check._failed_samples(df, mask, "email")
    assert len(samples) == 2  # None and ""


def test_failed_samples_limits_count():
    df = pd.DataFrame({"val": [None] * 50})
    mask = df["val"].isna()
    samples = check._failed_samples(df, mask, "val", n=5)
    assert len(samples) == 5


def test_failed_samples_empty_mask():
    df = pd.DataFrame({"email": ["a@b.com", "c@d.com"]})
    mask = pd.Series(False, index=df.index)
    samples = check._failed_samples(df, mask, "email")
    assert len(samples) == 0


# ── Abstract Method Enforcement ──


def test_cannot_instantiate_base_directly():
    try:
        BaseCheck()
        assert False, "Should not instantiate abstract class"
    except TypeError:
        pass  # expected


# ── Attributes ──


def test_fake_check_has_type():
    assert check.check_type == "fake"


def test_fake_check_has_description():
    assert check.description == "Fake check for testing"


def test_fake_check_has_supported_types():
    assert check.supported_types == ["fake", "test"]
