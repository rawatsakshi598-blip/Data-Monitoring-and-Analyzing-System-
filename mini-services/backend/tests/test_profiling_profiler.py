import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from profiling.profiler import profiler

def test_basic_profile():
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"], "score": [95.5, 87.3, 92.1]})
    p = profiler.profile(df, "test_table")
    assert p["table_name"] == "test_table"
    assert p["row_count"] == 3
    assert p["column_count"] == 3
    assert "id" in p["columns"]
    assert "name" in p["columns"]
    assert "score" in p["columns"]

def test_numeric_stats():
    df = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
    p = profiler.profile(df)
    col = p["columns"]["val"]
    assert col["min"] == 10.0
    assert col["max"] == 50.0
    assert col["mean"] == 30.0

def test_null_counts():
    df = pd.DataFrame({"x": [1, None, 3, None, 5]})
    p = profiler.profile(df)
    col = p["columns"]["x"]
    assert col["null_count"] == 2
    assert col["null_percent"] == 40.0

def test_string_top_values():
    df = pd.DataFrame({"status": ["a", "b", "a", "c", "a"]})
    p = profiler.profile(df)
    col = p["columns"]["status"]
    assert col["unique_count"] == 3
    assert len(col["top_values"]) > 0

def test_empty_dataframe():
    df = pd.DataFrame({"x": pd.Series([], dtype=float)})
    p = profiler.profile(df)
    assert p["row_count"] == 0
