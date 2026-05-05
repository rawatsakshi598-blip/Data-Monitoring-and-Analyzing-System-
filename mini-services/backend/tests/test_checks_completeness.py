import os, sys, pytest
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.completeness_check import CompletenessCheck
from models.rule import CheckConfig

check = CompletenessCheck()

def test_all_values_present():
    df = pd.DataFrame({"email": ["a@b.com", "c@d.com", "e@f.com"]})
    r = check.execute(df, CheckConfig(column="email", threshold=95.0))
    assert r.status == "passed"
    assert r.records_failed == 0

def test_some_nulls_below_threshold():
    df = pd.DataFrame({"email": ["a@b.com", None, "e@f.com", "g@h.com", None]})
    r = check.execute(df, CheckConfig(column="email", threshold=95.0))
    assert r.status == "failed"
    assert r.records_failed == 2

def test_some_nulls_above_threshold():
    df = pd.DataFrame({"email": ["a@b.com", "c@d.com", "e@f.com", None, "g@h.com"]})
    r = check.execute(df, CheckConfig(column="email", threshold=50.0))
    assert r.status == "passed"

def test_empty_strings_count_as_null():
    df = pd.DataFrame({"email": ["a@b.com", "", "e@f.com"]})
    r = check.execute(df, CheckConfig(column="email", threshold=95.0))
    assert r.status == "failed"
    assert r.records_failed == 1

def test_column_not_found():
    df = pd.DataFrame({"name": ["alice"]})
    r = check.execute(df, CheckConfig(column="email"))
    assert r.status == "failed"
    assert "not found" in r.message

def test_all_nulls():
    df = pd.DataFrame({"email": [None, None, None]})
    r = check.execute(df, CheckConfig(column="email", threshold=95.0))
    assert r.status == "failed"
    assert r.records_failed == 3

def test_empty_dataframe():
    df = pd.DataFrame({"email": pd.Series([], dtype=str)})
    r = check.execute(df, CheckConfig(column="email", threshold=95.0))
    assert r.status == "passed"

def test_uses_column_name_fallback():
    df = pd.DataFrame({"email": ["a@b.com", None]})
    r = check.execute(df, CheckConfig(), column_name="email", threshold=95.0)
    assert r.column_name == "email"
