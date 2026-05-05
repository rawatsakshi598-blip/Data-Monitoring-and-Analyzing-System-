import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.check_result import CheckResult
from engine.quality_scorer import scorer

def test_empty_results():
    assert scorer.calculate_score([]) == 100.0

def test_all_passed():
    results = [CheckResult(column_name="email", score=98.0), CheckResult(column_name="id", score=100.0)]
    score = scorer.calculate_score(results)
    assert score >= 95.0

def test_all_failed():
    results = [CheckResult(column_name="email", score=0.0), CheckResult(column_name="id", score=0.0)]
    score = scorer.calculate_score(results)
    assert score < 10.0

def test_mixed():
    results = [CheckResult(column_name="email", score=100.0), CheckResult(column_name="id", score=50.0)]
    score = scorer.calculate_score(results)
    assert 50.0 <= score <= 100.0

def test_table_score_empty():
    r = scorer.calculate_table_score([])
    assert r["overall_score"] == 100.0
    assert r["total"] == 0

def test_table_score_with_data():
    results = [CheckResult(status="passed"), CheckResult(status="failed"), CheckResult(status="passed")]
    r = scorer.calculate_table_score(results)
    assert r["total"] == 3
    assert r["passed"] == 2
    assert r["failed"] == 1
