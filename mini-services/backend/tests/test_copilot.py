"""
Comprehensive unit tests for the AI Copilot Engine.
Tests chat, suggestions, heuristic fallback, and response parsing.
Uses heuristic mode (no LLM API key set) for deterministic testing.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from copilot.engine import (
    CopilotEngine,
    _heuristic_chat,
    _heuristic_suggestions,
    _parse_copilot_response,
    _parse_suggestions_response,
    _build_table_context_block,
)


# ── Fixtures ──

@pytest.fixture
def engine():
    return CopilotEngine()


@pytest.fixture
def profile_data():
    return {
        'col_a': {'null_pct': 30, 'dtype': 'float64'},
        'col_b': {'null_pct': 0, 'dtype': 'object'},
        'col_c': {'null_pct': 5, 'dtype': 'int64', 'skew': 3.5},
    }


@pytest.fixture
def check_results():
    return [
        {'status': 'failed', 'score': 60, 'ruleName': 'completeness_check',
         'type': 'completeness', 'message': 'Column has 30% null values', 'column': 'col_a'},
    ]


@pytest.fixture
def complex_check_results():
    return [
        {'status': 'failed', 'score': 60, 'type': 'completeness',
         'message': '30% missing values', 'column': 'col_a'},
        {'status': 'failed', 'score': 70, 'type': 'uniqueness',
         'message': 'Duplicate rows found', 'column': ''},
        {'status': 'failed', 'score': 80, 'type': 'validity',
         'message': 'Format mismatch', 'column': 'col_b'},
        {'status': 'passed', 'score': 100, 'type': 'freshness',
         'message': 'Data is fresh'},
    ]


# ═══════════════════════════════════════════════
# Chat - Heuristic Mode
# ═══════════════════════════════════════════════

class TestCopilotChat:
    def test_copilot_chat(self, engine):
        result = engine.chat("How do I handle missing values?")
        assert 'message' in result
        assert 'suggested_actions' in result

    def test_chat_returns_generation_method(self, engine):
        result = engine.chat("Help with outliers")
        assert 'generation_method' in result

    def test_chat_missing_values_keyword(self, engine):
        result = engine.chat("I have null values in my data")
        assert 'suggested_actions' in result
        assert len(result['suggested_actions']) > 0
        assert result['suggested_actions'][0]['type'] == 'transformation'

    def test_chat_outlier_keyword(self, engine):
        result = engine.chat("How to handle outlier data?")
        assert len(result['suggested_actions']) > 0
        assert result['suggested_actions'][0]['config']['transform_type'] == 'outlier'

    def test_chat_encoding_keyword(self, engine):
        result = engine.chat("I need to encode categorical columns")
        assert len(result['suggested_actions']) > 0

    def test_chat_duplicate_keyword(self, engine):
        result = engine.chat("How to dedup my data?")
        assert len(result['suggested_actions']) > 0
        assert result['suggested_actions'][0]['config']['transform_type'] == 'dedup'

    def test_chat_ml_keyword(self, engine):
        result = engine.chat("How to prepare for machine learning?")
        assert len(result['suggested_actions']) > 0

    def test_chat_normalize_keyword(self, engine):
        result = engine.chat("How to normalize features?")
        assert len(result['suggested_actions']) > 0

    def test_chat_generic_fallback(self, engine):
        result = engine.chat("Hello there!")
        assert 'message' in result
        # Generic fallback may or may not have suggested_actions
        assert isinstance(result['suggested_actions'], list)

    def test_chat_empty_message(self, engine):
        result = engine.chat("")
        assert 'message' in result

    def test_chat_whitespace_message(self, engine):
        result = engine.chat("   ")
        assert 'message' in result

    def test_chat_with_table_context(self, engine):
        context = {
            'table_name': 'users',
            'quality_score': 75,
            'row_count': 1000,
            'column_count': 10,
        }
        result = engine.chat("What's wrong with my data?", context)
        assert 'message' in result


# ═══════════════════════════════════════════════
# Suggestions - Heuristic Mode
# ═══════════════════════════════════════════════

class TestCopilotSuggestions:
    def test_copilot_suggestions(self, engine, profile_data, check_results):
        result = engine.get_suggestions(profile_data, check_results, 'test_table')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_suggestions_have_required_fields(self, engine, profile_data, check_results):
        result = engine.get_suggestions(profile_data, check_results, 'test_table')
        for suggestion in result:
            assert 'type' in suggestion
            assert 'label' in suggestion
            assert 'description' in suggestion
            assert 'config' in suggestion
            assert 'priority' in suggestion
            assert 'generation_method' in suggestion

    def test_suggestions_valid_types(self, engine, profile_data, check_results):
        result = engine.get_suggestions(profile_data, check_results, 'test_table')
        valid_types = {'transformation', 'quality_rule', 'ml_preparation'}
        for suggestion in result:
            assert suggestion['type'] in valid_types

    def test_suggestions_priorities(self, engine, profile_data, check_results):
        result = engine.get_suggestions(profile_data, check_results, 'test_table')
        valid_priorities = {'high', 'medium', 'low'}
        for suggestion in result:
            assert suggestion['priority'] in valid_priorities

    def test_suggestions_sorted_by_priority(self, engine, profile_data, complex_check_results):
        result = engine.get_suggestions(profile_data, complex_check_results, 'test_table')
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        for i in range(len(result) - 1):
            assert priority_order.get(result[i]['priority'], 1) <= \
                   priority_order.get(result[i + 1]['priority'], 1)

    def test_suggestions_max_eight(self, engine, profile_data, complex_check_results):
        result = engine.get_suggestions(profile_data, complex_check_results, 'test_table')
        assert len(result) <= 8

    def test_suggestions_with_empty_profile(self, engine):
        result = engine.get_suggestions({}, [], 'test_table')
        assert isinstance(result, list)

    def test_suggestions_generation_method(self, engine, profile_data, check_results):
        result = engine.get_suggestions(profile_data, check_results, 'test_table')
        for suggestion in result:
            assert suggestion['generation_method'] == 'heuristic'


# ═══════════════════════════════════════════════
# Heuristic Chat (Direct)
# ═══════════════════════════════════════════════

class TestHeuristicChat:
    def test_missing_values_intent(self):
        result = _heuristic_chat("I have missing data")
        assert 'message' in result
        assert 'suggested_actions' in result

    def test_outlier_intent(self):
        result = _heuristic_chat("How to handle outlier data?")
        assert len(result['suggested_actions']) > 0

    def test_encoding_intent(self):
        result = _heuristic_chat("Need to do one-hot encoding")
        assert len(result['suggested_actions']) > 0

    def test_duplicate_intent(self):
        result = _heuristic_chat("Remove duplicate rows")
        assert len(result['suggested_actions']) > 0

    def test_ml_intent(self):
        result = _heuristic_chat("I want to train a model")
        assert len(result['suggested_actions']) > 0

    def test_normalize_intent(self):
        result = _heuristic_chat("How to scale my features")
        assert len(result['suggested_actions']) > 0

    def test_generic_fallback(self):
        result = _heuristic_chat("Tell me a joke")
        assert 'message' in result


# ═══════════════════════════════════════════════
# Heuristic Suggestions (Direct)
# ═══════════════════════════════════════════════

class TestHeuristicSuggestions:
    def test_completeness_suggestion(self):
        checks = [{'status': 'failed', 'type': 'completeness', 'score': 50,
                    'message': 'missing values', 'column': 'col_a'}]
        result = _heuristic_suggestions({}, checks, 'test')
        impute_actions = [s for s in result if s.get('config', {}).get('transform_type') == 'imputation']
        assert len(impute_actions) > 0

    def test_uniqueness_suggestion(self):
        checks = [{'status': 'failed', 'type': 'uniqueness', 'score': 70,
                    'message': 'duplicate rows', 'column': ''}]
        result = _heuristic_suggestions({}, checks, 'test')
        dedup_actions = [s for s in result if s.get('config', {}).get('transform_type') == 'dedup']
        assert len(dedup_actions) > 0

    def test_encoding_suggestion_from_profile(self):
        profile = {
            'columns': {
                'cat_col': {'dtype': 'object', 'unique': 5, 'count': 100},
            }
        }
        result = _heuristic_suggestions(profile, [], 'test')
        encode_actions = [s for s in result if s.get('config', {}).get('transform_type') == 'encoding']
        assert len(encode_actions) > 0

    def test_small_dataset_suggestion(self):
        profile = {'row_count': 50, 'column_count': 5}
        result = _heuristic_suggestions(profile, [], 'test')
        ml_actions = [s for s in result if s['type'] == 'ml_preparation']
        assert len(ml_actions) > 0


# ═══════════════════════════════════════════════
# Response Parsing
# ═══════════════════════════════════════════════

class TestResponseParsing:
    def test_parse_copilot_response_json(self):
        import json
        raw = json.dumps({
            'message': 'Test message',
            'suggested_actions': [{
                'type': 'transformation',
                'label': 'Test action',
                'description': 'A test',
                'config': {'transform_type': 'imputation'},
                'priority': 'high',
            }]
        })
        result = _parse_copilot_response(raw)
        assert result['message'] == 'Test message'
        assert len(result['suggested_actions']) == 1

    def test_parse_copilot_response_empty(self):
        result = _parse_copilot_response('')
        assert 'message' in result
        assert 'suggested_actions' in result

    def test_parse_copilot_response_none(self):
        result = _parse_copilot_response(None)
        assert 'message' in result

    def test_parse_suggestions_response_json(self):
        import json
        raw = json.dumps({
            'suggestions': [{
                'type': 'transformation',
                'label': 'Impute',
                'description': 'Fill missing',
                'config': {'transform_type': 'imputation'},
                'priority': 'high',
            }]
        })
        result = _parse_suggestions_response(raw)
        assert len(result) == 1
        assert result[0]['label'] == 'Impute'

    def test_parse_suggestions_response_empty(self):
        result = _parse_suggestions_response('')
        assert result == []

    def test_parse_suggestions_response_none(self):
        result = _parse_suggestions_response(None)
        assert result == []

    def test_parse_copilot_response_action_type_inference(self):
        import json
        raw = json.dumps({
            'message': 'Test',
            'suggested_actions': [{
                'type': 'unknown_type',
                'label': 'Test',
                'config': {'transform_type': 'imputation'},
            }]
        })
        result = _parse_copilot_response(raw)
        # Should infer type as 'transformation' from config
        assert result['suggested_actions'][0]['type'] == 'transformation'


# ═══════════════════════════════════════════════
# Context Builder
# ═══════════════════════════════════════════════

class TestContextBuilder:
    def test_build_context_with_table_name(self):
        context = {'table_name': 'users'}
        result = _build_table_context_block(context)
        assert 'users' in result

    def test_build_context_with_quality_score(self):
        context = {'quality_score': 85}
        result = _build_table_context_block(context)
        assert '85' in result

    def test_build_context_empty(self):
        context = {}
        result = _build_table_context_block(context)
        assert isinstance(result, str)

    def test_build_context_with_check_results(self):
        context = {
            'check_results': [
                {'rule_name': 'completeness', 'status': 'failed', 'score': 60}
            ]
        }
        result = _build_table_context_block(context)
        assert 'completeness' in result

    def test_build_context_with_profile_data(self):
        context = {
            'profile_data': {
                'columns': {
                    'col_a': {'dtype': 'int64', 'null_pct': 10}
                }
            }
        }
        result = _build_table_context_block(context)
        assert 'col_a' in result
