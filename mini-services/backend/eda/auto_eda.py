"""
Auto-EDA Engine — One-click exploratory data analysis.
Generates comprehensive profiling report with AI-powered insights.
"""

import pandas as pd
import numpy as np


class AutoEDAEngine:
    """Generate comprehensive EDA reports from data."""

    def generate_report(self, df: pd.DataFrame, table_name: str = "") -> dict:
        report = {
            "table_name": table_name,
            "overview": self._overview(df),
            "column_profiles": self._column_profiles(df),
            "correlations": self._correlations(df),
            "missing_analysis": self._missing_analysis(df),
            "distribution_analysis": self._distribution_analysis(df),
            "outlier_summary": self._outlier_summary(df),
            "insights": self._auto_insights(df, table_name),
            "warnings": self._warnings(df),
        }
        return report

    def _overview(self, df):
        return {
            "rows": len(df), "columns": len(df.columns),
            "numeric_columns": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": len(df.select_dtypes(include=['object', 'category', 'string']).columns),
            "datetime_columns": len(df.select_dtypes(include=['datetime64']).columns),
            "duplicate_rows": int(df.duplicated().sum()),
            "duplicate_pct": round(df.duplicated().sum() / len(df) * 100, 2) if len(df) > 0 else 0,
            "total_missing": int(df.isna().sum().sum()),
            "total_missing_pct": round(df.isna().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        }

    def _column_profiles(self, df):
        profiles = {}
        for col in df.columns:
            s = df[col]; total = len(s); nulls = int(s.isna().sum()); nn = s.dropna()
            profile = {"dtype": str(s.dtype), "null_count": nulls,
                       "null_pct": round(nulls / total * 100, 2), "unique_count": int(nn.nunique()),
                       "unique_pct": round(nn.nunique() / len(nn) * 100, 2) if len(nn) > 0 else 0}
            if pd.api.types.is_numeric_dtype(s):
                num = pd.to_numeric(nn, errors='coerce').dropna()
                if len(num) > 0:
                    profile.update({"min": float(num.min()), "max": float(num.max()),
                                    "mean": round(float(num.mean()), 4), "median": float(num.median()),
                                    "std": round(float(num.std()), 4) if len(num) > 1 else 0,
                                    "skewness": round(float(num.skew()), 4) if len(num) > 2 else 0,
                                    "kurtosis": round(float(num.kurtosis()), 4) if len(num) > 3 else 0,
                                    "q1": float(num.quantile(0.25)), "q3": float(num.quantile(0.75)),
                                    "iqr": float(num.quantile(0.75) - num.quantile(0.25))})
                    profile["distribution_hint"] = ("approximately_normal" if abs(profile["skewness"]) < 0.5 and abs(profile["kurtosis"]) < 1
                                                     else "right_skewed" if profile["skewness"] > 1
                                                     else "left_skewed" if profile["skewness"] < -1
                                                     else "moderately_skewed")
            else:
                profile["top_values"] = [{str(k): int(v)} for k, v in nn.value_counts().head(10).items()]
                profile["is_categorical"] = nn.nunique() / len(nn) < 0.05 if len(nn) > 0 else False
            profiles[col] = profile
        return profiles

    def _correlations(self, df):
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return {"matrix": {}, "high_correlations": [], "method": "pearson"}
        corr = numeric_df.corr(method='pearson')
        high_corrs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = float(corr.iloc[i, j])
                if abs(val) > 0.7:
                    high_corrs.append({"col1": corr.columns[i], "col2": corr.columns[j],
                                       "correlation": round(val, 4),
                                       "strength": "strong_positive" if val > 0 else "strong_negative"})
        return {"matrix": {col: {row: round(float(corr.loc[row, col]), 4) for row in corr.columns} for col in corr.columns},
                "high_correlations": high_corrs, "method": "pearson"}

    def _missing_analysis(self, df):
        missing = df.isna().sum()
        result = {"columns_with_missing": {}, "patterns": [], "total_cells_missing": int(missing.sum())}
        for col in df.columns:
            if missing[col] > 0:
                result["columns_with_missing"][col] = {"count": int(missing[col]),
                    "percent": round(missing[col] / len(df) * 100, 2)}
        return result

    def _distribution_analysis(self, df):
        numeric_df = df.select_dtypes(include=[np.number])
        distributions = {}
        for col in numeric_df.columns:
            s = numeric_df[col].dropna()
            if len(s) < 3: continue
            hist, bin_edges = np.histogram(s, bins=min(20, len(s) // 5 + 1))
            distributions[col] = {
                "histogram": {"counts": hist.tolist(), "bin_edges": [round(float(x), 4) for x in bin_edges]},
                "skewness": round(float(s.skew()), 4), "kurtosis": round(float(s.kurtosis()), 4),
                "is_normal": abs(float(s.skew())) < 0.5 and abs(float(s.kurtosis())) < 1,
            }
            try:
                from scipy.stats import shapiro
                stat, p_value = shapiro(s.sample(min(5000, len(s)), random_state=42))
                distributions[col]["normality_test"] = {"test": "shapiro_wilk", "statistic": round(float(stat), 6),
                    "p_value": round(float(p_value), 6), "is_normal": p_value > 0.05}
            except Exception: pass
        return distributions

    def _outlier_summary(self, df):
        numeric_df = df.select_dtypes(include=[np.number])
        outliers = {}
        for col in numeric_df.columns:
            s = numeric_df[col].dropna()
            if len(s) < 3: continue
            Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
            IQR = Q3 - Q1
            iqr_outliers = int(((s < Q1 - 1.5 * IQR) | (s > Q3 + 1.5 * IQR)).sum())
            mean, std = s.mean(), s.std()
            z_outliers = int(((s - mean).abs() / std > 3).sum()) if std > 0 else 0
            outliers[col] = {"iqr_outliers": iqr_outliers, "iqr_pct": round(iqr_outliers / len(s) * 100, 2),
                             "zscore_outliers": z_outliers, "zscore_pct": round(z_outliers / len(s) * 100, 2),
                             "lower_fence": round(float(Q1 - 1.5 * IQR), 4), "upper_fence": round(float(Q3 + 1.5 * IQR), 4)}
        return outliers

    def _auto_insights(self, df, table_name):
        insights = []
        total_cells = len(df) * len(df.columns)
        missing_pct = df.isna().sum().sum() / total_cells * 100 if total_cells > 0 else 0
        if missing_pct > 20:
            insights.append({"type": "warning", "category": "data_quality",
                             "message": f"High missing data rate: {missing_pct:.1f}% of all values are missing."})
        dup_pct = df.duplicated().sum() / len(df) * 100 if len(df) > 0 else 0
        if dup_pct > 5:
            insights.append({"type": "warning", "category": "dedup",
                             "message": f"{dup_pct:.1f}% duplicate rows detected."})
        for col in df.select_dtypes(include=['object', 'string']).columns:
            if df[col].nunique() / len(df) * 100 > 90:
                insights.append({"type": "info", "category": "cardinality",
                                 "message": f"Column '{col}' has very high cardinality — likely an ID field."})
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) >= 2:
            try:
                corr = numeric_df.corr()
                for i in range(len(corr.columns)):
                    for j in range(i+1, len(corr.columns)):
                        if abs(corr.iloc[i, j]) > 0.9:
                            insights.append({"type": "warning", "category": "multicollinearity",
                                             "message": f"Very high correlation between '{corr.columns[i]}' and '{corr.columns[j]}'."})
            except Exception: pass
        for col in df.columns:
            if df[col].nunique() <= 1:
                insights.append({"type": "warning", "category": "zero_variance",
                                 "message": f"Column '{col}' has zero variance."})
        return insights

    def _warnings(self, df):
        warnings = []
        if len(df) == 0: warnings.append({"level": "critical", "message": "Dataset is empty"})
        for col in df.columns:
            if df[col].isna().all(): warnings.append({"level": "critical", "message": f"Column '{col}' is entirely null"})
        return warnings


auto_eda = AutoEDAEngine()
