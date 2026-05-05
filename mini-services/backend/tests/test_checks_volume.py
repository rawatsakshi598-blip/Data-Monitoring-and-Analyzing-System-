import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.volume_check import VolumeCheck
from models.rule import CheckConfig

check = VolumeCheck()

def test_within_range():
    df = pd.DataFrame({"a": range(100)})
    r = check.execute(df, CheckConfig(min_value=50, max_value=200), table_name="t")
    assert r.status == "passed"

def test_below_min():
    df = pd.DataFrame({"a": range(10)})
    r = check.execute(df, CheckConfig(min_value=50, max_value=200), table_name="t")
    assert r.status == "failed"

def test_above_max():
    df = pd.DataFrame({"a": range(500)})
    r = check.execute(df, CheckConfig(min_value=0, max_value=100), table_name="t")
    assert r.status == "failed"

def test_no_range_always_pass():
    df = pd.DataFrame({"a": range(10)})
    r = check.execute(df, CheckConfig(), table_name="t")
    assert r.status == "passed"

def test_exact_min():
    df = pd.DataFrame({"a": range(50)})
    r = check.execute(df, CheckConfig(min_value=50, max_value=200), table_name="t")
    assert r.status == "passed"

def test_exact_max():
    df = pd.DataFrame({"a": range(201)})
    r = check.execute(df, CheckConfig(min_value=0, max_value=200), table_name="t")
    assert r.status == "failed"

def test_empty_dataframe():
    df = pd.DataFrame({"a": pd.Series([], dtype=int)})
    r = check.execute(df, CheckConfig(min_value=1), table_name="t")
    assert r.status == "failed"
