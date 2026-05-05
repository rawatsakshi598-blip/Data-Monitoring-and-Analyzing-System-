import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.schema_check import SchemaCheck
from models.rule import CheckConfig

check = SchemaCheck()

def test_schema_matches():
    df = pd.DataFrame({"id": [1], "name": ["a"], "email": ["b@c.com"]})
    r = check.execute(df, CheckConfig(valid_values=["id", "name", "email"]))
    assert r.status == "passed"

def test_missing_columns():
    df = pd.DataFrame({"id": [1], "name": ["a"]})
    r = check.execute(df, CheckConfig(valid_values=["id", "name", "email"]))
    assert r.status == "failed"
    assert "Missing" in r.message

def test_extra_columns():
    df = pd.DataFrame({"id": [1], "name": ["a"], "extra": ["x"]})
    r = check.execute(df, CheckConfig(valid_values=["id", "name"]))
    assert r.status == "failed"
    assert "Extra" in r.message

def test_no_expected_schema():
    df = pd.DataFrame({"a": [1], "b": [2]})
    r = check.execute(df, CheckConfig())
    assert r.status == "passed"
    assert "2 columns" in r.message

def test_both_missing_and_extra():
    df = pd.DataFrame({"id": [1], "extra": ["x"]})
    r = check.execute(df, CheckConfig(valid_values=["id", "name"]))
    assert r.status == "failed"
    assert "Missing" in r.message
    assert "Extra" in r.message
