"""
Test: models/rule.py
Verifies RuleCreate and CheckConfig match your DB column names.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.rule import RuleCreate, CheckConfig, NLRuleRequest


# ── CheckConfig Tests ──


def test_check_config_defaults():
    c = CheckConfig()
    assert c.column is None
    assert c.threshold is None
    assert c.valid_values is None
    assert c.regex is None
    assert c.min_value is None
    assert c.max_value is None


def test_check_config_with_column():
    c = CheckConfig(column="email")
    assert c.column == "email"


def test_check_config_with_threshold():
    c = CheckConfig(column="email", threshold=95.0)
    assert c.threshold == 95.0


def test_check_config_with_valid_values():
    c = CheckConfig(column="status", valid_values=["active", "inactive"])
    assert c.valid_values == ["active", "inactive"]


def test_check_config_with_range():
    c = CheckConfig(column="age", min_value=0, max_value=150)
    assert c.min_value == 0
    assert c.max_value == 150


def test_check_config_with_regex():
    c = CheckConfig(column="email", regex=r"^[^@]+@[^@]+\.[^@]+$")
    assert c.regex is not None


def test_check_config_serializes_to_json():
    """Config must be JSON-serializable for storing in DB config column."""
    import json

    c = CheckConfig(column="email", threshold=95.0)
    raw = json.dumps(c.model_dump())
    parsed = json.loads(raw)
    assert parsed["column"] == "email"
    assert parsed["threshold"] == 95.0


# ── RuleCreate Tests ──


def test_rule_create_defaults():
    r = RuleCreate(name="test rule")
    assert r.name == "test rule"
    assert r.description == ""
    assert r.type == "validity"
    assert r.dimension == "validity"
    assert r.severity == "warning"
    assert r.enabled is True
    assert r.schedule == "manual"
    assert r.datasetId is None


def test_rule_create_matches_your_db_columns():
    """Field names must match your QualityRule table: type, dimension, severity, config, enabled, schedule, datasetId."""
    r = RuleCreate(
        name="Email Not Null",
        description="Email field must not be null",
        type="completeness",
        dimension="completeness",
        severity="error",
        config=CheckConfig(column="email"),
        enabled=True,
        schedule="daily",
        datasetId="abc123",
    )
    assert r.type == "completeness"
    assert r.dimension == "completeness"
    assert r.severity == "error"
    assert r.config.column == "email"
    assert r.enabled is True
    assert r.schedule == "daily"
    assert r.datasetId == "abc123"


def test_rule_create_completeness():
    r = RuleCreate(
        name="Check nulls",
        type="completeness",
        dimension="completeness",
        severity="error",
    )
    assert r.type == "completeness"
    assert r.dimension == "completeness"
    assert r.severity == "error"


def test_rule_create_uniqueness():
    r = RuleCreate(
        name="Check dups", type="uniqueness", dimension="uniqueness", severity="warning"
    )
    assert r.type == "uniqueness"


def test_rule_create_validity():
    r = RuleCreate(
        name="Check format", type="validity", dimension="validity", severity="error"
    )
    assert r.type == "validity"


def test_rule_create_freshness():
    r = RuleCreate(
        name="Check fresh", type="freshness", dimension="timeliness", severity="warning"
    )
    assert r.type == "freshness"
    assert r.dimension == "timeliness"


def test_rule_create_disabled():
    r = RuleCreate(name="Disabled rule", enabled=False)
    assert r.enabled is False


# ── NLRuleRequest Tests ──


def test_nl_rule_request_basic():
    r = NLRuleRequest(prompt="Make sure email contains @")
    assert r.prompt == "Make sure email contains @"
    assert r.datasetId is None
    assert r.tableName is None
    assert r.columnName is None


def test_nl_rule_request_with_context():
    r = NLRuleRequest(
        prompt="Check status is active or inactive",
        datasetId="ds123",
        tableName="users",
        columnName="status",
        columns_info=[{"name": "status", "type": "string"}],
    )
    assert r.datasetId == "ds123"
    assert r.tableName == "users"
    assert r.columnName == "status"
    assert len(r.columns_info) == 1
