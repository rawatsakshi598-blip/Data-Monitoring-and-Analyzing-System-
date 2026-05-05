"""
Comprehensive unit tests for the Statistical Tests Engine.
Tests all 8 statistical tests, error handling, and edge cases.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from statistical.tests import stat_tests, StatisticalTestsEngine


# ── Fixtures ──

@pytest.fixture
def two_group_df():
    np.random.seed(42)
    return pd.DataFrame({
        'group': ['A'] * 50 + ['B'] * 50,
        'value': list(np.random.normal(0, 1, 50)) + list(np.random.normal(1, 1, 50)),
    })


@pytest.fixture
def correlated_df():
    np.random.seed(42)
    a = np.random.randn(100)
    b = a + np.random.normal(0, 0.5, 100)
    return pd.DataFrame({'a': a, 'b': b})


@pytest.fixture
def categorical_df():
    return pd.DataFrame({
        'cat1': ['a', 'b', 'a', 'b'] * 25,
        'cat2': ['x', 'y', 'y', 'x'] * 25,
    })


@pytest.fixture
def normal_df():
    np.random.seed(42)
    return pd.DataFrame({'value': np.random.normal(0, 1, 200)})


# ═══════════════════════════════════════════════
# List Tests
# ═══════════════════════════════════════════════

class TestListTests:
    def test_list_tests(self):
        tests = stat_tests.list_tests()
        assert len(tests) == 8

    def test_list_tests_structure(self):
        tests = stat_tests.list_tests()
        for t in tests:
            assert 'type' in t
            assert 'name' in t
            assert 'description' in t

    def test_list_tests_types(self):
        tests = stat_tests.list_tests()
        types = [t['type'] for t in tests]
        expected = ['t_test', 'chi_square', 'anova', 'ks_test',
                    'mann_whitney', 'pearson', 'spearman', 'normality']
        for t in expected:
            assert t in types


# ═══════════════════════════════════════════════
# T-Test
# ═══════════════════════════════════════════════

class TestTTest:
    def test_t_test_with_groups(self, two_group_df):
        result = stat_tests.run_test('t_test', two_group_df,
                                     {'column': 'value', 'group_column': 'group'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result
        assert result['p_value'] < 0.05  # Groups have different means

    def test_t_test_two_columns(self):
        df = pd.DataFrame({'a': np.random.normal(0, 1, 50),
                           'b': np.random.normal(5, 1, 50)})
        result = stat_tests.run_test('t_test', df, {'column1': 'a', 'column2': 'b'})
        assert result['success']
        assert result['significant'] == True

    def test_t_test_missing_config(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('t_test', df, {})
        assert result['success'] is False

    def test_t_test_group_means(self, two_group_df):
        result = stat_tests.run_test('t_test', two_group_df,
                                     {'column': 'value', 'group_column': 'group'})
        assert result['success']
        assert 'group1_mean' in result
        assert 'group2_mean' in result

    def test_t_test_conclusion(self, two_group_df):
        result = stat_tests.run_test('t_test', two_group_df,
                                     {'column': 'value', 'group_column': 'group'})
        assert 'conclusion' in result


# ═══════════════════════════════════════════════
# Pearson Correlation
# ═══════════════════════════════════════════════

class TestPearson:
    def test_pearson_correlated(self, correlated_df):
        result = stat_tests.run_test('pearson', correlated_df,
                                     {'column1': 'a', 'column2': 'b'})
        assert result['success']
        assert 'correlation' in result
        assert result['correlation'] > 0.7  # Strong positive correlation

    def test_pearson_direction(self, correlated_df):
        result = stat_tests.run_test('pearson', correlated_df,
                                     {'column1': 'a', 'column2': 'b'})
        assert result['direction'] == 'positive'

    def test_pearson_missing_columns(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('pearson', df, {'column1': 'a'})
        assert result['success'] is False

    def test_pearson_strength(self, correlated_df):
        result = stat_tests.run_test('pearson', correlated_df,
                                     {'column1': 'a', 'column2': 'b'})
        assert result['strength'] in ['very_strong', 'strong', 'moderate', 'weak', 'very_weak']

    def test_pearson_uncorrelated(self):
        np.random.seed(42)
        df = pd.DataFrame({'a': np.random.randn(200), 'b': np.random.randn(200)})
        result = stat_tests.run_test('pearson', df, {'column1': 'a', 'column2': 'b'})
        assert result['success']
        assert abs(result['correlation']) < 0.3


# ═══════════════════════════════════════════════
# Chi-Square
# ═══════════════════════════════════════════════

class TestChiSquare:
    def test_chi_square(self, categorical_df):
        result = stat_tests.run_test('chi_square', categorical_df,
                                     {'column1': 'cat1', 'column2': 'cat2'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'degrees_of_freedom' in result

    def test_chi_square_missing_columns(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('chi_square', df, {'column1': 'a'})
        assert result['success'] is False

    def test_chi_square_conclusion(self, categorical_df):
        result = stat_tests.run_test('chi_square', categorical_df,
                                     {'column1': 'cat1', 'column2': 'cat2'})
        assert 'conclusion' in result


# ═══════════════════════════════════════════════
# ANOVA
# ═══════════════════════════════════════════════

class TestAnova:
    def test_anova(self, two_group_df):
        result = stat_tests.run_test('anova', two_group_df,
                                     {'value_column': 'value', 'group_column': 'group'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result

    def test_anova_missing_config(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('anova', df, {})
        assert result['success'] is False

    def test_anova_three_groups(self):
        df = pd.DataFrame({
            'group': ['A'] * 30 + ['B'] * 30 + ['C'] * 30,
            'value': list(np.random.normal(0, 1, 30)) +
                     list(np.random.normal(2, 1, 30)) +
                     list(np.random.normal(5, 1, 30)),
        })
        result = stat_tests.run_test('anova', df,
                                     {'value_column': 'value', 'group_column': 'group'})
        assert result['success']
        assert result['num_groups'] == 3


# ═══════════════════════════════════════════════
# KS Test
# ═══════════════════════════════════════════════

class TestKSTest:
    def test_ks_test(self, normal_df):
        result = stat_tests.run_test('ks_test', normal_df, {'column': 'value'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result

    def test_ks_test_missing_column(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('ks_test', df, {'column': 'nonexistent'})
        assert result['success'] is False

    def test_ks_test_conclusion(self, normal_df):
        result = stat_tests.run_test('ks_test', normal_df, {'column': 'value'})
        assert 'conclusion' in result


# ═══════════════════════════════════════════════
# Mann-Whitney U
# ═══════════════════════════════════════════════

class TestMannWhitney:
    def test_mann_whitney_with_groups(self, two_group_df):
        result = stat_tests.run_test('mann_whitney', two_group_df,
                                     {'column': 'value', 'group_column': 'group'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result

    def test_mann_whitney_two_columns(self):
        df = pd.DataFrame({'a': range(50), 'b': range(50, 100)})
        result = stat_tests.run_test('mann_whitney', df,
                                     {'column1': 'a', 'column2': 'b'})
        assert result['success']

    def test_mann_whitney_missing_config(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('mann_whitney', df, {})
        assert result['success'] is False


# ═══════════════════════════════════════════════
# Spearman
# ═══════════════════════════════════════════════

class TestSpearman:
    def test_spearman(self, correlated_df):
        result = stat_tests.run_test('spearman', correlated_df,
                                     {'column1': 'a', 'column2': 'b'})
        assert result['success']
        assert 'correlation' in result

    def test_spearman_missing_columns(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('spearman', df, {'column1': 'a'})
        assert result['success'] is False


# ═══════════════════════════════════════════════
# Normality Test
# ═══════════════════════════════════════════════

class TestNormality:
    def test_normality(self, normal_df):
        result = stat_tests.run_test('normality', normal_df, {'column': 'value'})
        assert result['success']
        assert 'statistic' in result
        assert 'p_value' in result
        assert 'is_normal' in result

    def test_normality_skewness_kurtosis(self, normal_df):
        result = stat_tests.run_test('normality', normal_df, {'column': 'value'})
        assert 'skewness' in result
        assert 'kurtosis' in result

    def test_normality_missing_column(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = stat_tests.run_test('normality', df, {'column': 'nonexistent'})
        assert result['success'] is False


# ═══════════════════════════════════════════════
# Error Handling
# ═══════════════════════════════════════════════

class TestErrorHandling:
    def test_invalid_test(self):
        result = stat_tests.run_test('invalid', pd.DataFrame(), {})
        assert result['success'] is False
        assert 'error' in result

    def test_error_message_includes_available(self):
        result = stat_tests.run_test('nonexistent_test', pd.DataFrame(), {})
        assert 'Available' in result['error'] or 'Unknown' in result['error']


# ═══════════════════════════════════════════════
# Engine Instance
# ═══════════════════════════════════════════════

class TestEngineInstance:
    def test_engine_instance(self):
        assert isinstance(stat_tests, StatisticalTestsEngine)

    def test_direct_engine_usage(self):
        engine = StatisticalTestsEngine()
        df = pd.DataFrame({'a': np.random.randn(50), 'b': np.random.randn(50)})
        result = engine.run_test('pearson', df, {'column1': 'a', 'column2': 'b'})
        assert result['success']
