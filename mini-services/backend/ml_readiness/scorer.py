"""
ML-Readiness Score Engine — Rate how ready a dataset is for ML.
Scores across: completeness, feature_quality, encoding_needed, distribution, target_suitability
"""

import pandas as pd
import numpy as np


class MLReadinessEngine:
    """Score how ML-ready a dataset is."""

    def score(self, df: pd.DataFrame, target_column: str = "") -> dict:
        dimensions = {
            "completeness": self._score_completeness(df),
            "feature_quality": self._score_feature_quality(df),
            "encoding_needed": self._score_encoding(df),
            "distribution": self._score_distribution(df),
            "target_suitability": self._score_target(df, target_column) if target_column else {"score": 100, "issues": []},
            "data_size": self._score_data_size(df),
            "multicollinearity": self._score_multicollinearity(df),
        }

        weights = {"completeness": 25, "feature_quality": 20, "encoding_needed": 15,
                   "distribution": 15, "target_suitability": 10, "data_size": 10, "multicollinearity": 5}

        total_weight = sum(weights.values())
        weighted_score = sum(dimensions[k]["score"] * weights[k] for k in weights) / total_weight

        all_issues = []
        for dim_name, dim_data in dimensions.items():
            for issue in dim_data.get("issues", []):
                all_issues.append({"dimension": dim_name, **issue})

        recommendations = self._generate_recommendations(dimensions)

        return {
            "overall_score": round(weighted_score, 1),
            "grade": self._score_to_grade(weighted_score),
            "dimensions": dimensions,
            "total_issues": len(all_issues),
            "critical_issues": len([i for i in all_issues if i.get("severity") == "critical"]),
            "issues": all_issues,
            "recommendations": recommendations,
            "is_ml_ready": weighted_score >= 70,
        }

    def _score_completeness(self, df):
        total_cells = len(df) * len(df.columns)
        if total_cells == 0: return {"score": 0, "issues": [{"severity": "critical", "message": "Empty dataset"}]}
        missing_pct = df.isna().sum().sum() / total_cells * 100
        score = max(0, 100 - missing_pct * 2)
        issues = []
        if missing_pct > 20:
            issues.append({"severity": "critical", "message": f"High missing rate: {missing_pct:.1f}%"})
        elif missing_pct > 5:
            issues.append({"severity": "warning", "message": f"Moderate missing rate: {missing_pct:.1f}%"})
        for col in df.columns:
            col_missing = df[col].isna().sum() / len(df) * 100
            if col_missing > 50:
                issues.append({"severity": "critical", "message": f"Column '{col}' is {col_missing:.0f}% missing"})
        return {"score": round(score, 1), "missing_pct": round(missing_pct, 2), "issues": issues}

    def _score_feature_quality(self, df):
        issues = []
        score = 100
        for col in df.columns:
            if df[col].nunique() <= 1:
                score -= 10
                issues.append({"severity": "warning", "message": f"Column '{col}' has zero variance"})
            if df[col].dtype == 'object' and df[col].nunique() / len(df) > 0.9:
                score -= 5
                issues.append({"severity": "info", "message": f"Column '{col}' looks like an ID (high cardinality)"})
        return {"score": max(0, score), "issues": issues}

    def _score_encoding(self, df):
        cat_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        if not cat_cols:
            return {"score": 100, "categorical_columns": 0, "issues": []}
        score = max(0, 100 - len(cat_cols) * 10)
        issues = [{"severity": "warning", "message": f"Column '{col}' needs encoding before ML"} for col in cat_cols]
        return {"score": score, "categorical_columns": len(cat_cols), "issues": issues}

    def _score_distribution(self, df):
        numeric_df = df.select_dtypes(include=[np.number])
        issues = []
        skewed_count = 0
        for col in numeric_df.columns:
            s = numeric_df[col].dropna()
            if len(s) > 10:
                skew = float(s.skew())
                if abs(skew) > 3:
                    skewed_count += 1
                    issues.append({"severity": "info", "message": f"Column '{col}' is highly skewed (skewness={skew:.1f})"})
        score = max(0, 100 - skewed_count * 15)
        return {"score": score, "skewed_columns": skewed_count, "issues": issues}

    def _score_target(self, df, target_column):
        if target_column not in df.columns:
            return {"score": 0, "issues": [{"severity": "critical", "message": f"Target column '{target_column}' not found"}]}
        issues = []
        score = 100
        s = df[target_column]
        if s.isna().sum() > 0:
            score -= 20
            issues.append({"severity": "warning", "message": "Target column has missing values"})
        if pd.api.types.is_numeric_dtype(s) and len(s.unique()) < 10:
            issues.append({"severity": "info", "message": "Numeric target with few unique values — consider classification instead"})
        if s.dtype == 'object':
            class_counts = s.value_counts()
            min_class_pct = class_counts.min() / len(s) * 100
            if min_class_pct < 5:
                score -= 15
                issues.append({"severity": "warning", "message": f"Severe class imbalance: minority class is {min_class_pct:.1f}%"})
        return {"score": max(0, score), "issues": issues}

    def _score_data_size(self, df):
        score = 100
        issues = []
        if len(df) < 100:
            score = 30
            issues.append({"severity": "critical", "message": f"Very small dataset ({len(df)} rows) — risk of overfitting"})
        elif len(df) < 1000:
            score = 70
            issues.append({"severity": "warning", "message": f"Small dataset ({len(df)} rows) — limited ML capability"})
        if len(df.columns) < 3:
            score -= 20
            issues.append({"severity": "warning", "message": "Very few features — limited predictive power"})
        return {"score": max(0, score), "issues": issues}

    def _score_multicollinearity(self, df):
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return {"score": 100, "issues": []}
        issues = []
        try:
            corr = numeric_df.corr()
            high_corr_count = 0
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    if abs(corr.iloc[i, j]) > 0.9:
                        high_corr_count += 1
                        issues.append({"severity": "warning",
                                       "message": f"High correlation: '{corr.columns[i]}' ↔ '{corr.columns[j]}'"})
            score = max(0, 100 - high_corr_count * 15)
        except Exception:
            score = 80
        return {"score": score, "issues": issues}

    def _generate_recommendations(self, dimensions):
        recs = []
        if dimensions["completeness"]["score"] < 80:
            recs.append({"priority": "high", "action": "impute_missing", "message": "Impute missing values before training"})
        if dimensions["encoding_needed"]["score"] < 80:
            recs.append({"priority": "high", "action": "encode_categoricals", "message": "Encode categorical columns (one-hot or label encoding)"})
        if dimensions["distribution"]["score"] < 80:
            recs.append({"priority": "medium", "action": "transform_skewed", "message": "Apply log/Box-Cox transform to skewed features"})
        if dimensions["multicollinearity"]["score"] < 80:
            recs.append({"priority": "medium", "action": "remove_correlated", "message": "Remove highly correlated features or use PCA"})
        if dimensions["data_size"]["score"] < 80:
            recs.append({"priority": "medium", "action": "collect_more_data", "message": "Collect more data or use data augmentation"})
        return recs

    @staticmethod
    def _score_to_grade(score):
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"


ml_readiness = MLReadinessEngine()
