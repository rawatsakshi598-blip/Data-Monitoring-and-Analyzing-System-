import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.uniqueness_check import UniquenessCheck
from models.rule import CheckConfig

check = UniquenessCheck()

def test_all_unique():
    df = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
    r = check.execute(df, CheckConfig(column="id", threshold=100.0))
    assert r.status == "passed"
    assert r.records_failed == 0

def test_has_duplicates():
    df = pd.DataFrame({"id": [1, 2, 2, 3, 3, 3]})
    r = check.execute(df, CheckConfig(column="id", threshold=100.0))
    assert r.status == "failed"
    assert r.records_failed > 0

def test_duplicates_below_threshold():
    df = pd.DataFrame({"id": [1, 2, 2, 3, 4, 5]})
    r = check.execute(df, CheckConfig(column="id", threshold=50.0))
    assert r.status == "passed"

def test_column_not_found():
    df = pd.DataFrame({"name": ["a"]})
    r = check.execute(df, CheckConfig(column="id"))
    assert r.status == "failed"
    assert "not found" in r.message

def test_empty_dataframe():
    df = pd.DataFrame({"id": pd.Series([], dtype=int)})
    r = check.execute(df, CheckConfig(column="id", threshold=100.0))
    assert r.status == "passed"

def test_uses_column_name_fallback():
    df = pd.DataFrame({"id": [1, 1, 2]})
    r = check.execute(df, CheckConfig(), column_name="id", threshold=100.0)
    assert r.column_name == "id"
