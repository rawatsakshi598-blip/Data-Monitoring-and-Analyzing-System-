import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from checks import get_check, list_checks, REGISTRY

def test_registry_has_all_types():
    assert "completeness" in REGISTRY
    assert "uniqueness" in REGISTRY
    assert "validity" in REGISTRY
    assert "freshness" in REGISTRY
    assert "volume" in REGISTRY
    assert "schema" in REGISTRY

def test_get_check_returns_correct_type():
    c = get_check("completeness")
    assert c.check_type == "completeness"
    c2 = get_check("uniqueness")
    assert c2.check_type == "uniqueness"

def test_get_check_unknown_raises():
    try:
        get_check("nonexistent_type")
        assert False, "Should have raised"
    except ValueError as e:
        assert "nonexistent_type" in str(e)

def test_list_checks_returns_list():
    checks = list_checks()
    assert isinstance(checks, list)
    assert len(checks) >= 6
    types = [c["type"] for c in checks]
    assert "completeness" in types
    assert "uniqueness" in types

def test_alias_types_work():
    c = get_check("missing")
    assert c.check_type == "completeness"
    c2 = get_check("duplicate")
    assert c2.check_type == "uniqueness"
