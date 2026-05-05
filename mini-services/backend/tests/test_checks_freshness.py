import os, sys
import pandas as pd
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks.freshness_check import FreshnessCheck
from models.rule import CheckConfig

check = FreshnessCheck()

def test_fresh_data_pass():
    now = datetime.now()
    df = pd.DataFrame({"ts": [now - timedelta(hours=i) for i in range(5)]})
    r = check.execute(df, CheckConfig(column="ts", threshold=24.0))
    assert r.status == "passed"

def test_stale_data_fail():
    old = datetime.now() - timedelta(hours=48)
    df = pd.DataFrame({"ts": [old - timedelta(hours=i) for i in range(3)]})
    r = check.execute(df, CheckConfig(column="ts", threshold=24.0))
    assert r.status == "failed"

def test_column_not_found():
    df = pd.DataFrame({"name": ["a"]})
    r = check.execute(df, CheckConfig(column="ts"))
    assert r.status == "failed"

def test_non_datetime_column():
    df = pd.DataFrame({"ts": ["not", "a", "date"]})
    r = check.execute(df, CheckConfig(column="ts", threshold=24.0))
    assert r.status == "failed"

def test_all_null_timestamps():
    df = pd.DataFrame({"ts": [None, None, None]})
    r = check.execute(df, CheckConfig(column="ts", threshold=24.0))
    assert r.status == "failed"

def test_custom_threshold_hours():
    now = datetime.now()
    df = pd.DataFrame({"ts": [now - timedelta(hours=5)]})
    r = check.execute(df, CheckConfig(column="ts", threshold=3.0))
    assert r.status == "failed"
