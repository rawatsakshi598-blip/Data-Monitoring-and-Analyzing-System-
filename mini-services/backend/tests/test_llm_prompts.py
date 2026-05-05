import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from llm.prompts import RULE_SYSTEM, RULE_USER, REPORT_SYSTEM, REPORT_USER, FIX_SYSTEM, FIX_USER

def test_rule_system_has_json_instruction():
    assert "JSON" in RULE_SYSTEM
    assert "type" in RULE_SYSTEM
    assert "completeness" in RULE_SYSTEM

def test_rule_user_has_placeholders():
    assert "{prompt}" in RULE_USER
    assert "{table_name}" in RULE_USER
    assert "{column_name}" in RULE_USER

def test_report_system_has_json_instruction():
    assert "JSON" in REPORT_SYSTEM
    assert "summary" in REPORT_SYSTEM

def test_report_user_has_placeholders():
    assert "{table_name}" in REPORT_USER
    assert "{check_results}" in REPORT_USER

def test_fix_system_has_pandas():
    assert "df" in FIX_SYSTEM
    assert "JSON" in FIX_SYSTEM

def test_fix_user_has_placeholders():
    assert "{table_name}" in FIX_USER
    assert "{failures}" in FIX_USER

def test_all_prompts_are_strings():
    for p in [RULE_SYSTEM, RULE_USER, REPORT_SYSTEM, REPORT_USER, FIX_SYSTEM, FIX_USER]:
        assert isinstance(p, str)
        assert len(p) > 50
