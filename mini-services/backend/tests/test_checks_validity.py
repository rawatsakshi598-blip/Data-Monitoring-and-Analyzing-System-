import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.validity_check import ValidityCheck
from models.rule import CheckConfig

check = ValidityCheck()

def test_valid_values_pass():
    df = pd.DataFrame({"status": ["active", "inactive", "active", "inactive"]})
    r = check.execute(df, CheckConfig(column="status", valid_values=["active", "inactive"], threshold=95.0))
    assert r.status == "passed"

def test_valid_values_fail():
    df = pd.DataFrame({"status": ["active", "unknown", "active", "deleted"]})
    r = check.execute(df, CheckConfig(column="status", valid_values=["active", "inactive"], threshold=95.0))
    assert r.status == "failed"
    assert r.records_failed == 2

def test_regex_pass():
    df = pd.DataFrame({"email": ["a@b.com", "c@d.com", "e@f.com"]})
    r = check.execute(df, CheckConfig(column="email", regex=r"^[^@]+@[^@]+\.[^@]+$", threshold=95.0))
    assert r.status == "passed"

def test_regex_fail():
    df = pd.DataFrame({"email": ["a@b.com", "not-an-email", "c@d.com"]})
    r = check.execute(df, CheckConfig(column="email", regex=r"^[^@]+@[^@]+\.[^@]+$", threshold=95.0))
    assert r.status == "failed"

def test_range_pass():
    df = pd.DataFrame({"age": [25, 30, 45, 18, 60]})
    r = check.execute(df, CheckConfig(column="age", min_value=0, max_value=120, threshold=95.0))
    assert r.status == "passed"

def test_range_fail():
    df = pd.DataFrame({"age": [25, -5, 45, 200, 30]})
    r = check.execute(df, CheckConfig(column="age", min_value=0, max_value=120, threshold=95.0))
    assert r.status == "failed"

def test_no_rule_specified():
    df = pd.DataFrame({"col": [1, 2, 3]})
    r = check.execute(df, CheckConfig(column="col"))
    assert r.status == "failed"
    assert "No validity rule" in r.message

def test_column_not_found():
    df = pd.DataFrame({"a": [1]})
    r = check.execute(df, CheckConfig(column="z"))
    assert r.status == "failed"

def test_nulls_ignored_not_counted_as_invalid():
    df = pd.DataFrame({"status": ["active", None, "active", None]})
    r = check.execute(df, CheckConfig(column="status", valid_values=["active", "inactive"], threshold=95.0))
    assert r.status == "passed"
