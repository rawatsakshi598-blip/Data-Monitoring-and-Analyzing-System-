"""
Statistical Tests Engine — Hypothesis testing and correlation analysis.
Tests: t-test, chi-square, ANOVA, Kolmogorov-Smirnov, Mann-Whitney U, Pearson, Spearman
"""

import pandas as pd
import numpy as np
from typing import Optional


class StatisticalTestsEngine:
    """Perform statistical hypothesis tests on data."""

    def run_test(self, test_type: str, df: pd.DataFrame, config: dict) -> dict:
        test_map = {
            "t_test": self._t_test,
            "chi_square": self._chi_square,
            "anova": self._anova,
            "ks_test": self._ks_test,
            "mann_whitney": self._mann_whitney,
            "pearson": self._pearson,
            "spearman": self._spearman,
            "normality": self._normality_test,
        }

        fn = test_map.get(test_type)
        if fn is None:
            return {"success": False, "error": f"Unknown test: {test_type}. Available: {list(test_map.keys())}"}

        try:
            return fn(df, config)
        except Exception as e:
            return {"success": False, "error": str(e), "test_type": test_type}

    def list_tests(self) -> list:
        return [
            {"type": "t_test", "name": "Independent Samples T-Test", "description": "Compare means of two groups"},
            {"type": "chi_square", "name": "Chi-Square Test", "description": "Test independence of categorical variables"},
            {"type": "anova", "name": "One-Way ANOVA", "description": "Compare means across multiple groups"},
            {"type": "ks_test", "name": "Kolmogorov-Smirnov Test", "description": "Test if data follows a distribution"},
            {"type": "mann_whitney", "name": "Mann-Whitney U Test", "description": "Non-parametric comparison of two groups"},
            {"type": "pearson", "name": "Pearson Correlation", "description": "Linear correlation between two numeric variables"},
            {"type": "spearman", "name": "Spearman Correlation", "description": "Rank correlation between two variables"},
            {"type": "normality", "name": "Normality Test", "description": "Test if data is normally distributed"},
        ]

    def _t_test(self, df, config):
        from scipy import stats
        col1 = config.get("column1", config.get("column", ""))
        col2 = config.get("column2", "")
        group_column = config.get("group_column", "")
        alpha = config.get("alpha", 0.05)

        if group_column and col1:
            groups = df[group_column].unique()
            if len(groups) != 2:
                return {"success": False, "error": "Group column must have exactly 2 categories for t-test"}
            g1 = df[df[group_column] == groups[0]][col1].dropna()
            g2 = df[df[group_column] == groups[1]][col1].dropna()
        elif col1 and col2:
            g1 = df[col1].dropna()
            g2 = df[col2].dropna()
        else:
            return {"success": False, "error": "Provide column1+column2 or column+group_column"}

        stat, p_value = stats.ttest_ind(g1, g2)
        return {
            "success": True, "test_type": "t_test",
            "statistic": round(float(stat), 6), "p_value": round(float(p_value), 6),
            "significant": p_value < alpha, "alpha": alpha,
            "group1_mean": round(float(g1.mean()), 4), "group2_mean": round(float(g2.mean()), 4),
            "group1_n": len(g1), "group2_n": len(g2),
            "conclusion": f"Means are {'significantly' if p_value < alpha else 'not significantly'} different (p={p_value:.4f})",
        }

    def _chi_square(self, df, config):
        from scipy.stats import chi2_contingency
        col1 = config.get("column1", config.get("column", ""))
        col2 = config.get("column2", "")
        alpha = config.get("alpha", 0.05)
        if not col1 or not col2:
            return {"success": False, "error": "Provide column1 and column2"}
        contingency = pd.crosstab(df[col1], df[col2])
        chi2, p_value, dof, expected = chi2_contingency(contingency)
        return {
            "success": True, "test_type": "chi_square",
            "statistic": round(float(chi2), 4), "p_value": round(float(p_value), 6),
            "degrees_of_freedom": int(dof), "significant": p_value < alpha,
            "conclusion": f"Variables are {'dependent' if p_value < alpha else 'independent'} (p={p_value:.4f})",
        }

    def _anova(self, df, config):
        from scipy.stats import f_oneway
        value_column = config.get("value_column", config.get("column", ""))
        group_column = config.get("group_column", "")
        alpha = config.get("alpha", 0.05)
        if not value_column or not group_column:
            return {"success": False, "error": "Provide value_column and group_column"}
        groups = [g[value_column].dropna() for _, g in df.groupby(group_column)]
        if len(groups) < 2:
            return {"success": False, "error": "Need at least 2 groups for ANOVA"}
        stat, p_value = f_oneway(*groups)
        return {
            "success": True, "test_type": "anova",
            "statistic": round(float(stat), 4), "p_value": round(float(p_value), 6),
            "significant": p_value < alpha, "num_groups": len(groups),
            "conclusion": f"Group means are {'significantly' if p_value < alpha else 'not significantly'} different",
        }

    def _ks_test(self, df, config):
        from scipy.stats import kstest, norm
        column = config.get("column", config.get("column1", ""))
        distribution = config.get("distribution", "norm")
        alpha = config.get("alpha", 0.05)
        if not column or column not in df.columns:
            return {"success": False, "error": "Provide a valid column name"}
        data = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(data) < 3:
            return {"success": False, "error": "Need at least 3 values"}
        stat, p_value = kstest(data, distribution)
        return {
            "success": True, "test_type": "ks_test",
            "statistic": round(float(stat), 6), "p_value": round(float(p_value), 6),
            "distribution": distribution, "significant": p_value < alpha,
            "conclusion": f"Data {'does not follow' if p_value < alpha else 'follows'} {distribution} distribution",
        }

    def _mann_whitney(self, df, config):
        from scipy.stats import mannwhitneyu
        col1 = config.get("column1", config.get("column", ""))
        col2 = config.get("column2", "")
        group_column = config.get("group_column", "")
        alpha = config.get("alpha", 0.05)
        if group_column and col1:
            groups = df[group_column].unique()
            g1 = df[df[group_column] == groups[0]][col1].dropna()
            g2 = df[df[group_column] == groups[1]][col1].dropna()
        elif col1 and col2:
            g1 = df[col1].dropna()
            g2 = df[col2].dropna()
        else:
            return {"success": False, "error": "Provide column1+column2 or column+group_column"}
        stat, p_value = mannwhitneyu(g1, g2, alternative='two-sided')
        return {
            "success": True, "test_type": "mann_whitney",
            "statistic": round(float(stat), 4), "p_value": round(float(p_value), 6),
            "significant": p_value < alpha,
            "conclusion": f"Distributions are {'significantly' if p_value < alpha else 'not significantly'} different",
        }

    def _pearson(self, df, config):
        from scipy.stats import pearsonr
        col1 = config.get("column1", config.get("column", ""))
        col2 = config.get("column2", "")
        if not col1 or not col2:
            return {"success": False, "error": "Provide column1 and column2"}
        d = df[[col1, col2]].dropna()
        corr, p_value = pearsonr(d[col1], d[col2])
        strength = ("very_strong" if abs(corr) > 0.9 else "strong" if abs(corr) > 0.7
                    else "moderate" if abs(corr) > 0.5 else "weak" if abs(corr) > 0.3 else "very_weak")
        return {
            "success": True, "test_type": "pearson",
            "correlation": round(float(corr), 6), "p_value": round(float(p_value), 6),
            "significant": p_value < 0.05, "strength": strength, "direction": "positive" if corr > 0 else "negative",
            "n": len(d),
        }

    def _spearman(self, df, config):
        from scipy.stats import spearmanr
        col1 = config.get("column1", config.get("column", ""))
        col2 = config.get("column2", "")
        if not col1 or not col2:
            return {"success": False, "error": "Provide column1 and column2"}
        d = df[[col1, col2]].dropna()
        corr, p_value = spearmanr(d[col1], d[col2])
        return {
            "success": True, "test_type": "spearman",
            "correlation": round(float(corr), 6), "p_value": round(float(p_value), 6),
            "significant": p_value < 0.05, "n": len(d),
        }

    def _normality_test(self, df, config):
        from scipy.stats import shapiro
        column = config.get("column", config.get("column1", ""))
        alpha = config.get("alpha", 0.05)
        if not column or column not in df.columns:
            return {"success": False, "error": "Provide a valid column name"}
        data = pd.to_numeric(df[column], errors='coerce').dropna()
        if len(data) < 3:
            return {"success": False, "error": "Need at least 3 values"}
        sample = data.sample(min(5000, len(data)), random_state=42)
        stat, p_value = shapiro(sample)
        return {
            "success": True, "test_type": "normality",
            "statistic": round(float(stat), 6), "p_value": round(float(p_value), 6),
            "is_normal": p_value > alpha, "alpha": alpha,
            "skewness": round(float(data.skew()), 4), "kurtosis": round(float(data.kurtosis()), 4),
            "conclusion": f"Data {'is' if p_value > alpha else 'is not'} normally distributed (p={p_value:.4f})",
        }


stat_tests = StatisticalTestsEngine()
