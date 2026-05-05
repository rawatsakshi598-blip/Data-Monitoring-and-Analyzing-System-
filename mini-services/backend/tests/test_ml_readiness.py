"""
Comprehensive unit tests for the ML-Readiness Scorer.
Tests scoring, grades, all dimensions, edge cases, and recommendations.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ml_readiness.scorer import ml_readiness, MLReadinessEngine


# ── Fixtures ──

@pytest.fixture
def good_ml_df():
    np.random.seed(42)
    return pd.DataFrame({
        'a': np.random.randn(500),
        'b': np.random.randn(500),
        'c': np.random.randn(500),
        'target': np.random.choice([0, 1], 500),
    })


@pytest.fixture
def poor_ml_df():
    return pd.DataFrame({
        'a': [1, None] * 50,
        'b': range(100),
    })


@pytest.fixture
def categorical_ml_df():
    return pd.DataFrame({
        'cat': ['a', 'b', 'c'] * 34,
        'num': range(102),
    })


# ═══════════════════════════════════════════════
# Basic Scoring
# ═══════════════════════════════════════════════

class TestBasicScoring:
    def test_score_basic(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100),
                           'target': np.random.choice([0, 1], 100)})
        result = ml_readiness.score(df, 'target')
        assert 'overall_score' in result
        assert 'grade' in result
        assert result['grade'] in ['A', 'B', 'C', 'D', 'F']
        assert 'dimensions' in result
        assert 'is_ml_ready' in result

    def test_score_returns_numeric(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = ml_readiness.score(df)
        assert isinstance(result['overall_score'], (int, float))
        assert 0 <= result['overall_score'] <= 100

    def test_score_is_ml_ready_boolean(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = ml_readiness.score(df)
        # is_ml_ready may be numpy bool_, use == comparison
        assert result['is_ml_ready'] in [True, False]


# ═══════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════

class TestEdgeCases:
    def test_score_empty(self):
        df = pd.DataFrame()
        result = ml_readiness.score(df)
        # Empty dataset should have a low score (completeness=0 pulls it down)
        assert result['overall_score'] < 70

    def test_score_small_dataset(self):
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        result = ml_readiness.score(df)
        # Very small dataset should have data_size score <= 30
        assert result['dimensions']['data_size']['score'] <= 30

    def test_score_single_column(self):
        df = pd.DataFrame({'a': range(100)})
        result = ml_readiness.score(df)
        # Very few features should reduce score
        assert result['dimensions']['data_size']['score'] < 100

    def test_score_with_all_null_column(self):
        df = pd.DataFrame({'a': [None] * 100, 'b': range(100)})
        result = ml_readiness.score(df)
        assert result['dimensions']['completeness']['score'] < 100

    def test_score_large_clean_dataset(self, good_ml_df):
        result = ml_readiness.score(good_ml_df, 'target')
        assert result['overall_score'] >= 60


# ═══════════════════════════════════════════════
# Completeness Dimension
# ═══════════════════════════════════════════════

class TestCompleteness:
    def test_score_with_missing(self, poor_ml_df):
        result = ml_readiness.score(poor_ml_df)
        assert result['dimensions']['completeness']['score'] < 100

    def test_completeness_perfect(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = ml_readiness.score(df)
        assert result['dimensions']['completeness']['score'] == 100

    def test_completeness_issues(self, poor_ml_df):
        result = ml_readiness.score(poor_ml_df)
        assert len(result['dimensions']['completeness']['issues']) > 0

    def test_completeness_high_missing_critical(self):
        df = pd.DataFrame({'a': [None] * 80 + [1] * 20})
        result = ml_readiness.score(df)
        critical_issues = [i for i in result['dimensions']['completeness']['issues']
                           if i.get('severity') == 'critical']
        assert len(critical_issues) > 0


# ═══════════════════════════════════════════════
# Encoding Dimension
# ═══════════════════════════════════════════════

class TestEncoding:
    def test_score_with_categoricals(self, categorical_ml_df):
        result = ml_readiness.score(categorical_ml_df)
        assert result['dimensions']['encoding_needed']['score'] < 100

    def test_no_categoricals(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = ml_readiness.score(df)
        assert result['dimensions']['encoding_needed']['score'] == 100

    def test_encoding_issues_list(self, categorical_ml_df):
        result = ml_readiness.score(categorical_ml_df)
        assert len(result['dimensions']['encoding_needed']['issues']) > 0


# ═══════════════════════════════════════════════
# Feature Quality Dimension
# ═══════════════════════════════════════════════

class TestFeatureQuality:
    def test_zero_variance_column(self):
        df = pd.DataFrame({'a': [5] * 100, 'b': range(100)})
        result = ml_readiness.score(df)
        assert result['dimensions']['feature_quality']['score'] < 100

    def test_high_cardinality_id_column(self):
        df = pd.DataFrame({'id': [f'id_{i}' for i in range(100)], 'val': range(100)})
        result = ml_readiness.score(df)
        # 'id' is object dtype with high cardinality
        issues = result['dimensions']['feature_quality']['issues']
        has_id_issue = any('ID' in i.get('message', '') or 'cardinality' in i.get('message', '').lower() for i in issues)
        assert has_id_issue


# ═══════════════════════════════════════════════
# Data Size Dimension
# ═══════════════════════════════════════════════

class TestDataSize:
    def test_very_small_dataset(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = ml_readiness.score(df)
        assert result['dimensions']['data_size']['score'] <= 30

    def test_medium_dataset(self):
        df = pd.DataFrame({'a': range(500), 'b': range(500), 'c': range(500)})
        result = ml_readiness.score(df)
        # 500 rows with 3 columns: data_size should be 70 (no -20 penalty for few features)
        assert result['dimensions']['data_size']['score'] == 70

    def test_large_dataset(self):
        df = pd.DataFrame({'a': range(2000), 'b': range(2000), 'c': range(2000)})
        result = ml_readiness.score(df)
        assert result['dimensions']['data_size']['score'] == 100


# ═══════════════════════════════════════════════
# Target Suitability
# ═══════════════════════════════════════════════

class TestTargetSuitability:
    def test_missing_target(self):
        df = pd.DataFrame({'a': range(100)})
        result = ml_readiness.score(df, 'nonexistent_col')
        assert result['dimensions']['target_suitability']['score'] == 0

    def test_target_with_missing_values(self):
        df = pd.DataFrame({'a': range(100), 'target': [1 if i < 50 else None for i in range(100)]})
        result = ml_readiness.score(df, 'target')
        assert result['dimensions']['target_suitability']['score'] < 100

    def test_target_class_imbalance(self):
        df = pd.DataFrame({
            'a': range(100),
            'target': ['A'] * 97 + ['B'] * 3,
        })
        result = ml_readiness.score(df, 'target')
        assert result['dimensions']['target_suitability']['score'] < 100

    def test_no_target(self):
        df = pd.DataFrame({'a': range(100)})
        result = ml_readiness.score(df)
        # Without target, target_suitability defaults to 100
        assert result['dimensions']['target_suitability']['score'] == 100


# ═══════════════════════════════════════════════
# Multicollinearity
# ═══════════════════════════════════════════════

class TestMulticollinearity:
    def test_highly_correlated(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100), 'c': np.random.randn(100)})
        result = ml_readiness.score(df)
        # a and b are perfectly correlated
        assert result['dimensions']['multicollinearity']['score'] < 100

    def test_no_correlation(self):
        np.random.seed(42)
        df = pd.DataFrame({'a': np.random.randn(100), 'b': np.random.randn(100)})
        result = ml_readiness.score(df)
        assert result['dimensions']['multicollinearity']['score'] == 100


# ═══════════════════════════════════════════════
# Grades
# ═══════════════════════════════════════════════

class TestGrades:
    def test_grade_A(self):
        assert MLReadinessEngine._score_to_grade(95) == 'A'

    def test_grade_B(self):
        assert MLReadinessEngine._score_to_grade(85) == 'B'

    def test_grade_C(self):
        assert MLReadinessEngine._score_to_grade(75) == 'C'

    def test_grade_D(self):
        assert MLReadinessEngine._score_to_grade(65) == 'D'

    def test_grade_F(self):
        assert MLReadinessEngine._score_to_grade(50) == 'F'

    def test_grade_boundaries(self):
        assert MLReadinessEngine._score_to_grade(90) == 'A'
        assert MLReadinessEngine._score_to_grade(89.9) == 'B'
        assert MLReadinessEngine._score_to_grade(80) == 'B'
        assert MLReadinessEngine._score_to_grade(70) == 'C'
        assert MLReadinessEngine._score_to_grade(60) == 'D'


# ═══════════════════════════════════════════════
# Recommendations
# ═══════════════════════════════════════════════

class TestRecommendations:
    def test_recommendations_for_poor_data(self, poor_ml_df):
        result = ml_readiness.score(poor_ml_df)
        assert len(result['recommendations']) > 0

    def test_imputation_recommendation(self):
        df = pd.DataFrame({'a': [None] * 50 + [1] * 50, 'b': range(100)})
        result = ml_readiness.score(df)
        actions = [r['action'] for r in result['recommendations']]
        assert 'impute_missing' in actions

    def test_encoding_recommendation(self):
        # Need 3+ categorical columns to get encoding score < 80 (100 - 3*10 = 70)
        df = pd.DataFrame({
            'cat1': ['a', 'b', 'c'] * 34,
            'cat2': ['x', 'y', 'z'] * 34,
            'cat3': ['p', 'q', 'r'] * 34,
            'num': range(102),
        })
        result = ml_readiness.score(df)
        actions = [r['action'] for r in result['recommendations']]
        assert 'encode_categoricals' in actions


# ═══════════════════════════════════════════════
# Engine Instance
# ═══════════════════════════════════════════════

class TestMLReadinessEngine:
    def test_engine_instance(self):
        assert isinstance(ml_readiness, MLReadinessEngine)

    def test_direct_engine_usage(self):
        engine = MLReadinessEngine()
        df = pd.DataFrame({'a': range(100)})
        result = engine.score(df)
        assert 'overall_score' in result
