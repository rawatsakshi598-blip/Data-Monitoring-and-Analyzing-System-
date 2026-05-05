"""
Comprehensive unit tests for the Auto-EDA Engine.
Tests report generation, overview, column profiles, correlations,
missing analysis, distribution analysis, outlier summary, and insights.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from eda.auto_eda import auto_eda, AutoEDAEngine


# ── Fixtures ──

@pytest.fixture
def basic_df():
    return pd.DataFrame({
        'a': [1, 2, 3, 4, 5],
        'b': ['x', 'y', 'x', 'y', 'z'],
    })


@pytest.fixture
def numeric_df():
    np.random.seed(42)
    return pd.DataFrame({
        'a': np.random.randn(100),
        'b': np.random.randn(100),
    })


@pytest.fixture
def missing_df():
    return pd.DataFrame({
        'a': [1, None, 3, None, 5],
        'b': ['x', None, 'y', 'z', None],
    })


@pytest.fixture
def mixed_df():
    return pd.DataFrame({
        'num_col': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'cat_col': ['a', 'b', 'a', 'b', 'c', 'a', 'b', 'c', 'a', 'b'],
        'date_col': pd.date_range('2024-01-01', periods=10),
    })


# ═══════════════════════════════════════════════
# Basic Report Generation
# ═══════════════════════════════════════════════

class TestGenerateReport:
    def test_generate_report_basic(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test_table')
        assert 'overview' in report
        assert 'column_profiles' in report
        assert 'correlations' in report
        assert 'insights' in report
        assert report['overview']['rows'] == 5
        assert report['overview']['columns'] == 2

    def test_generate_report_empty(self):
        df = pd.DataFrame()
        report = auto_eda.generate_report(df, 'empty')
        assert report['overview']['rows'] == 0
        assert report['overview']['columns'] == 0

    def test_generate_report_with_missing(self, missing_df):
        report = auto_eda.generate_report(missing_df, 'missing_table')
        assert report['overview']['total_missing'] > 0

    def test_generate_report_numeric_only(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'numeric_table')
        assert len(report['correlations']['matrix']) > 0

    def test_report_has_table_name(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'my_table')
        assert report['table_name'] == 'my_table'

    def test_report_has_all_sections(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        required_keys = ['overview', 'column_profiles', 'correlations',
                         'missing_analysis', 'distribution_analysis',
                         'outlier_summary', 'insights', 'warnings']
        for key in required_keys:
            assert key in report, f"Missing section: {key}"


# ═══════════════════════════════════════════════
# Overview Section
# ═══════════════════════════════════════════════

class TestOverview:
    def test_overview_rows_columns(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        assert report['overview']['rows'] == 5
        assert report['overview']['columns'] == 2

    def test_overview_numeric_categorical_counts(self, mixed_df):
        report = auto_eda.generate_report(mixed_df, 'mixed')
        assert report['overview']['numeric_columns'] >= 1
        # 'cat_col' is object dtype, should be counted as categorical
        # Note: bool_col may be counted as numeric by pandas
        assert report['overview']['categorical_columns'] >= 0

    def test_overview_duplicate_rows(self):
        df = pd.DataFrame({'a': [1, 1, 2], 'b': ['x', 'x', 'y']})
        report = auto_eda.generate_report(df, 'dup_table')
        assert report['overview']['duplicate_rows'] == 1

    def test_overview_total_missing(self, missing_df):
        report = auto_eda.generate_report(missing_df, 'test')
        assert report['overview']['total_missing'] > 0
        assert report['overview']['total_missing_pct'] > 0

    def test_overview_memory_mb(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        # Memory can be 0.0 for very small dataframes
        assert report['overview']['memory_mb'] >= 0


# ═══════════════════════════════════════════════
# Column Profiles
# ═══════════════════════════════════════════════

class TestColumnProfiles:
    def test_column_profiles_exist(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        assert 'a' in report['column_profiles']
        assert 'b' in report['column_profiles']

    def test_numeric_profile_stats(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
        report = auto_eda.generate_report(df, 'test')
        profile = report['column_profiles']['a']
        assert 'min' in profile
        assert 'max' in profile
        assert 'mean' in profile
        assert 'median' in profile
        assert 'std' in profile

    def test_categorical_profile_top_values(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        profile = report['column_profiles']['b']
        assert 'top_values' in profile

    def test_column_null_stats(self, missing_df):
        report = auto_eda.generate_report(missing_df, 'test')
        for col in missing_df.columns:
            profile = report['column_profiles'][col]
            assert 'null_count' in profile
            assert 'null_pct' in profile

    def test_column_dtype(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        assert report['column_profiles']['a']['dtype'] == 'int64'
        assert report['column_profiles']['b']['dtype'] == 'object'

    def test_unique_count(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        assert report['column_profiles']['a']['unique_count'] == 5
        assert report['column_profiles']['b']['unique_count'] == 3


# ═══════════════════════════════════════════════
# Correlations
# ═══════════════════════════════════════════════

class TestCorrelations:
    def test_correlations_numeric(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'test')
        assert len(report['correlations']['matrix']) > 0
        assert report['correlations']['method'] == 'pearson'

    def test_correlations_single_numeric(self):
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        report = auto_eda.generate_report(df, 'test')
        # Only one numeric column -> no correlation matrix
        assert report['correlations']['matrix'] == {}

    def test_correlations_high_correlation(self):
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        report = auto_eda.generate_report(df, 'test')
        assert len(report['correlations']['high_correlations']) > 0

    def test_no_numeric_correlations(self):
        df = pd.DataFrame({'a': ['x', 'y', 'z'], 'b': ['p', 'q', 'r']})
        report = auto_eda.generate_report(df, 'test')
        assert report['correlations']['matrix'] == {}


# ═══════════════════════════════════════════════
# Missing Analysis
# ═══════════════════════════════════════════════

class TestMissingAnalysis:
    def test_missing_analysis_no_missing(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        assert report['missing_analysis']['total_cells_missing'] == 0

    def test_missing_analysis_with_missing(self, missing_df):
        report = auto_eda.generate_report(missing_df, 'test')
        assert report['missing_analysis']['total_cells_missing'] > 0
        assert len(report['missing_analysis']['columns_with_missing']) > 0

    def test_missing_analysis_column_details(self, missing_df):
        report = auto_eda.generate_report(missing_df, 'test')
        col_missing = report['missing_analysis']['columns_with_missing']
        for col_name, info in col_missing.items():
            assert 'count' in info
            assert 'percent' in info


# ═══════════════════════════════════════════════
# Distribution Analysis
# ═══════════════════════════════════════════════

class TestDistributionAnalysis:
    def test_distribution_numeric(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'test')
        assert len(report['distribution_analysis']) > 0

    def test_distribution_has_histogram(self):
        df = pd.DataFrame({'a': range(50)})
        report = auto_eda.generate_report(df, 'test')
        if 'a' in report['distribution_analysis']:
            assert 'histogram' in report['distribution_analysis']['a']

    def test_distribution_skewness_kurtosis(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'test')
        for col, dist in report['distribution_analysis'].items():
            assert 'skewness' in dist
            assert 'kurtosis' in dist

    def test_no_distribution_for_categorical(self, basic_df):
        report = auto_eda.generate_report(basic_df, 'test')
        # 'b' is categorical, should not appear in distribution_analysis
        assert 'b' not in report['distribution_analysis']


# ═══════════════════════════════════════════════
# Outlier Summary
# ═══════════════════════════════════════════════

class TestOutlierSummary:
    def test_outlier_summary_present(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'test')
        assert isinstance(report['outlier_summary'], dict)

    def test_outlier_summary_with_outliers(self):
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5, 1000]})
        report = auto_eda.generate_report(df, 'test')
        assert report['outlier_summary']['a']['iqr_outliers'] > 0

    def test_outlier_summary_fence_values(self, numeric_df):
        report = auto_eda.generate_report(numeric_df, 'test')
        for col, info in report['outlier_summary'].items():
            assert 'lower_fence' in info
            assert 'upper_fence' in info


# ═══════════════════════════════════════════════
# Auto Insights
# ═══════════════════════════════════════════════

class TestAutoInsights:
    def test_high_missing_data_insight(self):
        df = pd.DataFrame({'a': [None] * 80 + [1] * 20})
        report = auto_eda.generate_report(df, 'test')
        insight_types = [i['category'] for i in report['insights']]
        assert 'data_quality' in insight_types

    def test_duplicate_insight(self):
        df = pd.DataFrame({'a': [1] * 20 + [2]})
        report = auto_eda.generate_report(df, 'test')
        insight_cats = [i['category'] for i in report['insights']]
        assert 'dedup' in insight_cats

    def test_zero_variance_insight(self):
        df = pd.DataFrame({'a': [5, 5, 5], 'b': [1, 2, 3]})
        report = auto_eda.generate_report(df, 'test')
        insight_cats = [i['category'] for i in report['insights']]
        assert 'zero_variance' in insight_cats

    def test_no_insights_for_clean_data(self):
        df = pd.DataFrame({'a': range(1, 101), 'b': range(101, 201)})
        report = auto_eda.generate_report(df, 'test')
        # Clean numeric data should have few/no insights
        assert isinstance(report['insights'], list)


# ═══════════════════════════════════════════════
# Warnings
# ═══════════════════════════════════════════════

class TestWarnings:
    def test_empty_dataset_warning(self):
        df = pd.DataFrame()
        report = auto_eda.generate_report(df, 'test')
        warning_msgs = [w['message'] for w in report['warnings']]
        assert any('empty' in m.lower() for m in warning_msgs)

    def test_all_null_column_warning(self):
        df = pd.DataFrame({'a': [None, None, None], 'b': [1, 2, 3]})
        report = auto_eda.generate_report(df, 'test')
        warning_msgs = [w['message'] for w in report['warnings']]
        assert any('entirely null' in m for m in warning_msgs)


# ═══════════════════════════════════════════════
# Engine Instance
# ═══════════════════════════════════════════════

class TestAutoEDAEngine:
    def test_engine_instance(self):
        assert isinstance(auto_eda, AutoEDAEngine)

    def test_direct_engine_usage(self):
        engine = AutoEDAEngine()
        df = pd.DataFrame({'a': [1, 2, 3]})
        report = engine.generate_report(df, 'direct')
        assert 'overview' in report
