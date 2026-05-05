"""
AI Data Prep Copilot Engine — Chat-based assistant for data preparation.

Accepts user messages and optional table context (profile data, check results,
schema) and returns conversational responses with actionable suggestions such as
transformations, quality rules, and ML preparation steps.

Uses the existing LLM client (llm/client.py) with automatic provider fallback.
Falls back to heuristic suggestions when no LLM is available.
"""

import json
import os
import re as _re
from typing import Optional

from llm.client import call_llm, extract_json


# ── System Prompts ──────────────────────────────────────────────────────────

COPILOT_SYSTEM = """You are an AI Data Preparation Copilot — an expert assistant that helps users \
clean, transform, and prepare their data for analysis and machine learning.

Your role:
- Analyze data quality issues and suggest concrete fixes
- Recommend specific data transformations (imputation, outlier handling, encoding, etc.)
- Propose quality rules based on data patterns
- Guide users through ML preparation steps
- Explain data preparation concepts in plain language

When table context is provided, tailor your suggestions to the specific data. \
When no context is available, give general guidance and ask clarifying questions.

AVAILABLE TRANSFORMATIONS:
- imputation: Fill missing values (mean, median, mode, forward fill, constant)
- outlier: Remove or cap outliers (IQR, z-score, percentile)
- dedup: Remove duplicate rows
- encoding: Encode categorical columns (one-hot, label, ordinal, target encoding)
- normalization: Scale numeric columns (standard, minmax, robust)
- string_clean: Clean string values (trim, lowercase, remove special chars)
- date_parse: Parse and extract date components
- data_split: Split data into train/test sets
- type_conversion: Convert column data types

SUGGESTED ACTION TYPES:
- "transformation": A data transformation step (e.g., impute missing values)
- "quality_rule": A data quality rule to add (e.g., completeness check on column X)
- "ml_preparation": An ML-specific preparation step (e.g., encode categoricals for ML)

Respond with ONLY valid JSON (no markdown, no code blocks, no explanation outside JSON). Format:
{
  "message": "Your conversational response to the user, explaining what you found and what you recommend",
  "suggested_actions": [
    {
      "type": "transformation",
      "label": "Short label for the action",
      "description": "What this action does and why",
      "config": {
        "transform_type": "imputation",
        "columns": ["column_name"],
        "method": "median"
      },
      "priority": "high"
    }
  ]
}

IMPORTANT RULES:
- Always include "message" as a natural, helpful conversational response
- Include "suggested_actions" array (can be empty if just answering a question)
- For transformation actions, include "config" with "transform_type" matching one of the available transformations
- For quality_rule actions, include "config" with "rule_type" (completeness, uniqueness, validity, etc.) and relevant fields
- For ml_preparation actions, include "config" with "step" describing the preparation step
- Set "priority" to "high", "medium", or "low" based on urgency
- Be specific: reference actual column names, values, and statistics from the context when available
- Limit suggested_actions to at most 5 items, prioritized by importance"""

COPILOT_SYSTEM_WITH_CONTEXT = COPILOT_SYSTEM + """

CURRENT TABLE CONTEXT:
{table_context}"""

SUGGESTIONS_SYSTEM = """You are a data preparation expert analyzing a specific table. \
Based on the table's profile data and quality check results, generate prioritized \
suggestions for data preparation.

For each suggestion, specify:
- The exact action type (transformation, quality_rule, or ml_preparation)
- Which columns are affected
- The recommended method or approach
- Why this action is needed (reference specific statistics or check results)
- Priority level (high for critical issues, medium for improvements, low for optimizations)

AVAILABLE TRANSFORMATIONS AND THEIR METHODS:
- imputation: mean, median, mode, forward_fill, constant
- outlier: iqr, zscore, percentile, winsorize
- dedup: keep_first, keep_last, keep_none
- encoding: one_hot, label, ordinal, target
- normalization: standard, minmax, robust
- string_clean: trim, lowercase, uppercase, remove_special, strip_html
- date_parse: auto, iso8601, us_format, eu_format
- data_split: random, stratified, temporal
- type_conversion: to_numeric, to_string, to_datetime, to_category

QUALITY RULE TYPES:
- completeness: Check for null/missing values
- uniqueness: Check for duplicates
- validity: Check value format, range, or regex
- freshness: Check data recency
- schema: Check data structure conformance
- anomaly: Detect statistical anomalies

Respond with ONLY valid JSON (no markdown, no code blocks). Format:
{
  "suggestions": [
    {
      "type": "transformation",
      "label": "Short label",
      "description": "Why this is needed and what it does",
      "config": {
        "transform_type": "imputation",
        "columns": ["col_name"],
        "method": "median"
      },
      "priority": "high",
      "reason": "Column X has 15% missing values"
    }
  ]
}

Generate at most 8 suggestions, ordered by priority (most critical first)."""


# ── Fallback Heuristic Engine ───────────────────────────────────────────────

def _heuristic_suggestions(profile_data: dict, check_results: list, table_name: str) -> list:
    """Generate suggestions using rule-based heuristics when LLM is unavailable."""
    suggestions = []
    columns_profile = profile_data.get("columns", {})
    if isinstance(columns_profile, str):
        try:
            columns_profile = json.loads(columns_profile)
        except (json.JSONDecodeError, TypeError):
            columns_profile = {}

    # Analyze check results for failures
    failed_checks = [c for c in check_results if c.get("status") == "failed"]
    check_types_seen = set()

    for check in failed_checks:
        check_type = check.get("type", "")
        check_types_seen.add(check_type)
        col = check.get("column", check.get("config", {}).get("column", ""))
        score = check.get("score", 0)
        message = check.get("message", "")

        if check_type == "completeness" or "null" in message.lower() or "missing" in message.lower():
            suggestions.append({
                "type": "transformation",
                "label": f"Impute missing values in {col or 'affected columns'}",
                "description": f"Completeness check scored {score}%. Fill missing values to improve data quality.",
                "config": {
                    "transform_type": "imputation",
                    "columns": [col] if col else [],
                    "method": "median",
                },
                "priority": "high",
                "reason": f"Completeness score: {score}%{f' for column {col}' if col else ''}",
            })

        elif check_type == "uniqueness" or "duplicate" in message.lower():
            suggestions.append({
                "type": "transformation",
                "label": "Remove duplicate rows",
                "description": f"Uniqueness check scored {score}%. Deduplicate data to ensure data integrity.",
                "config": {
                    "transform_type": "dedup",
                    "columns": [col] if col else [],
                    "method": "keep_first",
                },
                "priority": "high",
                "reason": f"Uniqueness score: {score}%",
            })

        elif check_type == "validity" or "format" in message.lower():
            suggestions.append({
                "type": "quality_rule",
                "label": f"Add validity rule for {col or 'affected columns'}",
                "description": f"Validity check scored {score}%. Consider adding stricter validation rules.",
                "config": {
                    "rule_type": "validity",
                    "column": col,
                    "severity": "warning",
                },
                "priority": "medium",
                "reason": f"Validity score: {score}%",
            })

    # Analyze column profiles for common issues
    cols_needing_encoding = []
    cols_with_outliers = []
    cols_needing_imputation = []
    high_cardinality_cols = []

    if isinstance(columns_profile, dict):
        for col_name, col_info in columns_profile.items():
            if not isinstance(col_info, dict):
                continue

            dtype = col_info.get("type", col_info.get("dtype", ""))
            missing_pct = col_info.get("missing_pct", col_info.get("null_pct", 0))
            unique_count = col_info.get("unique", col_info.get("nunique", 0))
            total_count = col_info.get("count", 0)
            skew = col_info.get("skew", 0)

            # Missing values
            if missing_pct and float(missing_pct) > 5 and "completeness" not in check_types_seen:
                cols_needing_imputation.append(col_name)

            # Categorical columns needing encoding
            if dtype in ("object", "string", "category", "str"):
                if unique_count and total_count and unique_count < total_count * 0.5:
                    cols_needing_encoding.append(col_name)
                elif unique_count and total_count and unique_count / max(total_count, 1) > 0.9:
                    high_cardinality_cols.append(col_name)

            # Outliers in numeric columns
            if dtype in ("int64", "float64", "number", "numeric") and skew and abs(float(skew)) > 2:
                cols_with_outliers.append(col_name)

    if cols_needing_imputation and "completeness" not in check_types_seen:
        suggestions.append({
            "type": "transformation",
            "label": f"Impute missing values in {len(cols_needing_imputation)} column(s)",
            "description": f"Columns with >5% missing values: {', '.join(cols_needing_imputation[:5])}. "
                           "Fill gaps to prepare for analysis and ML.",
            "config": {
                "transform_type": "imputation",
                "columns": cols_needing_imputation[:10],
                "method": "median",
            },
            "priority": "high",
            "reason": f"{len(cols_needing_imputation)} column(s) have significant missing values",
        })

    if cols_needing_encoding:
        suggestions.append({
            "type": "transformation",
            "label": f"Encode {len(cols_needing_encoding)} categorical column(s)",
            "description": f"Categorical columns needing encoding: {', '.join(cols_needing_encoding[:5])}. "
                           "Required before most ML algorithms can process the data.",
            "config": {
                "transform_type": "encoding",
                "columns": cols_needing_encoding[:10],
                "method": "one_hot" if len(cols_needing_encoding) <= 5 else "label",
            },
            "priority": "medium",
            "reason": f"{len(cols_needing_encoding)} categorical column(s) need encoding for ML",
        })

    if cols_with_outliers and "outlier" not in check_types_seen:
        suggestions.append({
            "type": "transformation",
            "label": f"Handle outliers in {len(cols_with_outliers)} column(s)",
            "description": f"Highly skewed columns: {', '.join(cols_with_outliers[:5])}. "
                           "Consider capping or removing outliers.",
            "config": {
                "transform_type": "outlier",
                "columns": cols_with_outliers[:10],
                "method": "iqr",
            },
            "priority": "medium",
            "reason": f"{len(cols_with_outliers)} column(s) have significant skew/outliers",
        })

    if high_cardinality_cols:
        suggestions.append({
            "type": "ml_preparation",
            "label": f"Review high-cardinality columns: {', '.join(high_cardinality_cols[:3])}",
            "description": "These columns may be IDs or free-text fields. Consider dropping or using "
                           "target encoding instead of one-hot to avoid dimensionality explosion.",
            "config": {
                "step": "review_high_cardinality",
                "columns": high_cardinality_cols[:10],
                "recommendation": "drop_or_target_encode",
            },
            "priority": "low",
            "reason": f"{len(high_cardinality_cols)} high-cardinality column(s) may harm model performance",
        })

    # ML preparation suggestions based on overall state
    row_count = profile_data.get("row_count", profile_data.get("rowCount", 0))
    col_count = profile_data.get("column_count", profile_data.get("columnCount", 0))

    if row_count and col_count:
        if row_count < 1000:
            suggestions.append({
                "type": "ml_preparation",
                "label": "Small dataset — consider data augmentation",
                "description": f"Dataset has only {row_count} rows. This limits ML model capability. "
                               "Consider collecting more data, using cross-validation, or simpler models.",
                "config": {
                    "step": "data_augmentation",
                    "current_rows": row_count,
                    "recommendation": "collect_more_data_or_cross_validate",
                },
                "priority": "medium",
                "reason": f"Only {row_count} rows available",
            })

        if cols_needing_encoding:
            suggestions.append({
                "type": "ml_preparation",
                "label": "Train/test split after encoding",
                "description": "After encoding categorical features, split the data for model training. "
                               "Use stratified split if you have a classification target.",
                "config": {
                    "step": "train_test_split",
                    "transform_type": "data_split",
                    "method": "stratified",
                    "test_size": 0.2,
                },
                "priority": "low",
                "reason": "Standard ML preparation step after encoding",
            })

    # Add a quality rule suggestion if we found any issues
    if failed_checks and "quality_rule" not in [s["type"] for s in suggestions]:
        suggestions.append({
            "type": "quality_rule",
            "label": "Add quality rules to prevent data regression",
            "description": f"Found {len(failed_checks)} quality issues. Add rules to catch these problems "
                           "early in future data ingestions.",
            "config": {
                "rule_type": "completeness",
                "severity": "warning",
            },
            "priority": "medium",
            "reason": f"{len(failed_checks)} quality check(s) currently failing",
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "medium"), 1))

    return suggestions[:8]


def _heuristic_chat(message: str, table_context: Optional[dict] = None) -> dict:
    """Generate a simple response when LLM is unavailable."""
    msg_lower = message.lower()

    # Detect intent
    if any(w in msg_lower for w in ["missing", "null", "empty", "blank", "nan"]):
        return {
            "message": (
                "It looks like you're concerned about missing values. "
                "I'd recommend checking which columns have the highest null rates, "
                "then imputing with median (for numeric) or mode (for categorical). "
                "If a column is more than 50% missing, consider dropping it entirely. "
                "Would you like me to suggest specific imputation strategies for your data?"
            ),
            "suggested_actions": [
                {
                    "type": "transformation",
                    "label": "Impute missing values",
                    "description": "Fill null values using median for numeric columns and mode for categorical columns.",
                    "config": {"transform_type": "imputation", "method": "median"},
                    "priority": "high",
                }
            ],
        }

    if any(w in msg_lower for w in ["outlier", "anomaly", "skew", "extreme"]):
        return {
            "message": (
                "For outlier handling, I typically recommend the IQR method as a starting point — "
                "it's robust to non-normal distributions. For highly skewed data, consider winsorization "
                "instead of removal to preserve data volume. Would you like me to identify which columns "
                "have outliers in your dataset?"
            ),
            "suggested_actions": [
                {
                    "type": "transformation",
                    "label": "Remove outliers using IQR",
                    "description": "Detect and remove outliers using the Interquartile Range method.",
                    "config": {"transform_type": "outlier", "method": "iqr"},
                    "priority": "medium",
                }
            ],
        }

    if any(w in msg_lower for w in ["encode", "categorical", "one-hot", "label encod"]):
        return {
            "message": (
                "For categorical encoding, use one-hot encoding when a column has few unique values (≤10), "
                "and label/ordinal encoding for higher cardinality. For very high cardinality columns, "
                "target encoding often works best for ML. Need help deciding which columns to encode?"
            ),
            "suggested_actions": [
                {
                    "type": "transformation",
                    "label": "Encode categorical columns",
                    "description": "Convert categorical columns to numeric using one-hot or label encoding.",
                    "config": {"transform_type": "encoding", "method": "one_hot"},
                    "priority": "medium",
                }
            ],
        }

    if any(w in msg_lower for w in ["duplicate", "dedup", "unique"]):
        return {
            "message": (
                "Duplicate rows can skew analysis and ML models. I recommend deduplicating based on "
                "key columns, keeping the first occurrence. If duplicates have conflicting values, "
                "we may need a merge strategy instead. Should I check for duplicates in your data?"
            ),
            "suggested_actions": [
                {
                    "type": "transformation",
                    "label": "Remove duplicate rows",
                    "description": "Deduplicate data, keeping the first occurrence of each duplicate set.",
                    "config": {"transform_type": "dedup", "method": "keep_first"},
                    "priority": "high",
                }
            ],
        }

    if any(w in msg_lower for w in ["ml", "machine learning", "model", "train", "predict"]):
        return {
            "message": (
                "To prepare data for ML, I recommend this workflow: "
                "1) Handle missing values (imputation), "
                "2) Remove duplicates, "
                "3) Encode categorical features, "
                "4) Handle outliers, "
                "5) Scale/normalize features, "
                "6) Split into train/test sets. "
                "Would you like me to assess your data's ML readiness and create a preparation plan?"
            ),
            "suggested_actions": [
                {
                    "type": "ml_preparation",
                    "label": "ML readiness assessment",
                    "description": "Evaluate the dataset's readiness for machine learning across key dimensions.",
                    "config": {"step": "ml_readiness_assessment"},
                    "priority": "high",
                }
            ],
        }

    if any(w in msg_lower for w in ["normalize", "scale", "standardize"]):
        return {
            "message": (
                "Normalization is important for distance-based algorithms (KNN, SVM) and gradient descent. "
                "Use StandardScaler for normally distributed data, MinMaxScaler for bounded features, "
                "and RobustScaler when outliers are present. Need me to suggest which columns to scale?"
            ),
            "suggested_actions": [
                {
                    "type": "transformation",
                    "label": "Normalize numeric columns",
                    "description": "Scale numeric features using standard or minmax normalization.",
                    "config": {"transform_type": "normalization", "method": "standard"},
                    "priority": "medium",
                }
            ],
        }

    # Generic fallback
    return {
        "message": (
            "I'm your Data Preparation Copilot! I can help you with:\n"
            "- Handling missing values and imputation strategies\n"
            "- Detecting and removing outliers\n"
            "- Encoding categorical columns for ML\n"
            "- Removing duplicates\n"
            "- Normalizing and scaling features\n"
            "- Creating quality rules for your data\n"
            "- Assessing ML readiness\n\n"
            "What would you like help with? If you share your table context, "
            "I can give more specific recommendations."
        ),
        "suggested_actions": [],
    }


# ── Context Builder ─────────────────────────────────────────────────────────

def _build_table_context_block(table_context: dict) -> str:
    """Format table context into a readable block for the system prompt."""
    parts = []

    if table_context.get("table_name"):
        parts.append(f"Table Name: {table_context['table_name']}")

    if table_context.get("schema"):
        schema = table_context["schema"]
        if isinstance(schema, (list, dict)):
            schema_str = json.dumps(schema, indent=2, default=str)
        else:
            schema_str = str(schema)
        parts.append(f"Schema:\n{schema_str}")

    if table_context.get("profile_data"):
        profile = table_context["profile_data"]
        # Truncate if too large
        if isinstance(profile, dict):
            summary = {}
            for k, v in profile.items():
                if k in ("columns", "column_profiles"):
                    # Summarize column profiles briefly
                    if isinstance(v, dict):
                        col_summary = {}
                        for col_name, col_data in list(v.items())[:20]:
                            if isinstance(col_data, dict):
                                col_summary[col_name] = {
                                    "type": col_data.get("type", col_data.get("dtype", "unknown")),
                                    "missing_pct": col_data.get("missing_pct", col_data.get("null_pct", 0)),
                                    "unique": col_data.get("unique", col_data.get("nunique")),
                                    "mean": col_data.get("mean"),
                                    "std": col_data.get("std"),
                                    "min": col_data.get("min"),
                                    "max": col_data.get("max"),
                                    "skew": col_data.get("skew"),
                                }
                            else:
                                col_summary[col_name] = str(col_data)[:100]
                        summary[k] = col_summary
                    else:
                        summary[k] = str(v)[:500]
                else:
                    summary[k] = v
            profile_str = json.dumps(summary, indent=2, default=str)
        else:
            profile_str = str(profile)[:3000]
        parts.append(f"Profile Data:\n{profile_str}")

    if table_context.get("check_results"):
        checks = table_context["check_results"]
        if isinstance(checks, list):
            # Summarize check results
            check_summary = []
            for c in checks[:15]:
                check_summary.append({
                    "rule": c.get("rule_name", c.get("name", c.get("rule", "unknown"))),
                    "status": c.get("status", "unknown"),
                    "score": c.get("score"),
                    "column": c.get("column", c.get("config", {}).get("column", "")),
                    "message": c.get("message", "")[:150],
                })
            checks_str = json.dumps(check_summary, indent=2, default=str)
        else:
            checks_str = str(checks)[:2000]
        parts.append(f"Quality Check Results:\n{checks_str}")

    if table_context.get("quality_score") is not None:
        parts.append(f"Overall Quality Score: {table_context['quality_score']}")

    if table_context.get("row_count") is not None:
        parts.append(f"Row Count: {table_context['row_count']}")

    if table_context.get("column_count") is not None:
        parts.append(f"Column Count: {table_context['column_count']}")

    return "\n\n".join(parts) if parts else "No specific table context provided."


def _parse_copilot_response(raw_response: str) -> dict:
    """Parse the LLM response into structured copilot output."""
    if not raw_response:
        return {
            "message": "I'm having trouble generating a response right now. Please try again.",
            "suggested_actions": [],
        }

    # Try JSON extraction first
    data = extract_json(raw_response)
    if data and isinstance(data, dict):
        message = data.get("message", "")
        actions = data.get("suggested_actions", [])

        # Validate and normalize actions
        valid_actions = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_type = action.get("type", "")
            if action_type not in ("transformation", "quality_rule", "ml_preparation"):
                # Try to infer type from content
                if action.get("config", {}).get("transform_type"):
                    action_type = "transformation"
                elif action.get("config", {}).get("rule_type"):
                    action_type = "quality_rule"
                else:
                    action_type = "transformation"
                action["type"] = action_type

            valid_action = {
                "type": action_type,
                "label": action.get("label", action.get("title", "Suggested action")),
                "description": action.get("description", ""),
                "config": action.get("config", {}),
                "priority": action.get("priority", "medium"),
            }

            # Include reason if present
            if action.get("reason"):
                valid_action["reason"] = action["reason"]

            valid_actions.append(valid_action)

        # If no message but we have a raw string, use it
        if not message and isinstance(raw_response, str):
            # Strip JSON artifacts and use as message
            message = raw_response
            # Remove JSON blocks from message
            message = _re.sub(r'```json.*?```', '', message, flags=_re.DOTALL)
            message = _re.sub(r'\{[^{}]*\}', '', message)
            message = message.strip()[:1000]

        return {
            "message": message or "I've analyzed your request and have some suggestions.",
            "suggested_actions": valid_actions[:5],
        }

    # Fallback: treat the raw response as a plain message
    clean_message = raw_response.strip()
    # Remove markdown code blocks
    clean_message = _re.sub(r'```json.*?```', '', clean_message, flags=_re.DOTALL)
    clean_message = _re.sub(r'```.*?```', '', clean_message, flags=_re.DOTALL)
    clean_message = clean_message.strip()[:2000]

    return {
        "message": clean_message or "I've analyzed your request. What specific data preparation task would you like help with?",
        "suggested_actions": [],
    }


def _parse_suggestions_response(raw_response: str) -> list:
    """Parse the LLM suggestions response into a list of suggestion dicts."""
    if not raw_response:
        return []

    data = extract_json(raw_response)
    if data and isinstance(data, dict):
        suggestions = data.get("suggestions", [])
        if isinstance(suggestions, list):
            valid = []
            for s in suggestions:
                if not isinstance(s, dict):
                    continue
                action_type = s.get("type", "transformation")
                if action_type not in ("transformation", "quality_rule", "ml_preparation"):
                    action_type = "transformation"
                valid.append({
                    "type": action_type,
                    "label": s.get("label", s.get("title", "Suggestion")),
                    "description": s.get("description", ""),
                    "config": s.get("config", {}),
                    "priority": s.get("priority", "medium"),
                    "reason": s.get("reason", ""),
                })
            return valid[:8]

    return []


# ── CopilotEngine ───────────────────────────────────────────────────────────

class CopilotEngine:
    """AI-powered Data Preparation Copilot.

    Provides conversational data preparation assistance with actionable suggestions.
    Uses the LLM client when available, falls back to rule-based heuristics.
    """

    def __init__(self):
        self._llm_available = bool(os.environ.get("LLM_API_KEY", ""))

    def chat(self, message: str, table_context: Optional[dict] = None) -> dict:
        """Main chat endpoint.

        Args:
            message: The user's message or question about data preparation.
            table_context: Optional dict with keys:
                - table_name (str): Name of the table being discussed
                - schema (list|dict): Column schema information
                - profile_data (dict): Column profiling statistics
                - check_results (list): Quality check results
                - quality_score (float): Overall quality score
                - row_count (int): Number of rows
                - column_count (int): Number of columns

        Returns:
            Dict with:
                - message (str): The copilot's conversational response
                - suggested_actions (list): List of action dicts with type, label,
                  description, config, and priority
                - generation_method (str): "llm" or "heuristic"
        """
        if not message or not message.strip():
            return {
                "message": "Hello! I'm your Data Preparation Copilot. How can I help you prepare your data today?",
                "suggested_actions": [],
                "generation_method": "heuristic",
            }

        # Try LLM first
        if self._llm_available:
            try:
                result = self._llm_chat(message, table_context)
                if result:
                    result["generation_method"] = "llm"
                    return result
            except Exception as e:
                print(f"[Copilot] LLM chat failed: {e}")

        # Fallback to heuristics
        result = _heuristic_chat(message, table_context)
        result["generation_method"] = "heuristic"
        return result

    def get_suggestions(
        self,
        profile_data: dict,
        check_results: list,
        table_name: str = "",
    ) -> list:
        """Generate smart suggestions based on table profile and check results.

        Args:
            profile_data: Column profiling statistics from the profiler.
            check_results: List of quality check result dicts.
            table_name: Name of the table for context.

        Returns:
            List of suggestion dicts, each with:
                - type (str): "transformation", "quality_rule", or "ml_preparation"
                - label (str): Short label for the suggestion
                - description (str): What this suggestion does and why
                - config (dict): Configuration for the suggested action
                - priority (str): "high", "medium", or "low"
                - reason (str): Why this suggestion is relevant
                - generation_method (str): "llm" or "heuristic"
        """
        # Try LLM first
        if self._llm_available:
            try:
                result = self._llm_suggestions(profile_data, check_results, table_name)
                if result:
                    for r in result:
                        r["generation_method"] = "llm"
                    return result
            except Exception as e:
                print(f"[Copilot] LLM suggestions failed: {e}")

        # Fallback to heuristics
        result = _heuristic_suggestions(profile_data, check_results, table_name)
        for r in result:
            r["generation_method"] = "heuristic"
        return result

    # ── Private LLM Methods ──

    def _llm_chat(self, message: str, table_context: Optional[dict] = None) -> Optional[dict]:
        """Use LLM to generate a conversational response with suggestions."""
        # Build system prompt
        if table_context:
            context_block = _build_table_context_block(table_context)
            system_prompt = COPILOT_SYSTEM_WITH_CONTEXT.format(table_context=context_block)
        else:
            system_prompt = COPILOT_SYSTEM

        # Build user prompt with context summary
        user_parts = [message]
        if table_context:
            context_hints = []
            if table_context.get("quality_score") is not None:
                context_hints.append(f"Current quality score: {table_context['quality_score']}")
            if table_context.get("check_results"):
                failed = [c for c in table_context["check_results"] if c.get("status") == "failed"]
                if failed:
                    context_hints.append(f"{len(failed)} quality check(s) are currently failing")
            if context_hints:
                user_parts.append("\n\nContext: " + "; ".join(context_hints))

        user_prompt = "\n".join(user_parts)

        response = call_llm(system_prompt, user_prompt, temperature=0.5, max_tokens=4096)
        if not response:
            return None

        return _parse_copilot_response(response)

    def _llm_suggestions(
        self,
        profile_data: dict,
        check_results: list,
        table_name: str,
    ) -> Optional[list]:
        """Use LLM to generate smart suggestions based on data context."""
        # Build a concise context for the LLM
        context_parts = [f"Table: {table_name or 'unknown'}"]

        # Summarize profile data
        if profile_data:
            profile_summary = {}
            if isinstance(profile_data, dict):
                for key in ("row_count", "rowCount", "column_count", "columnCount", "missing_pct"):
                    if key in profile_data:
                        profile_summary[key] = profile_data[key]

                columns = profile_data.get("columns", profile_data.get("column_profiles", {}))
                if isinstance(columns, dict):
                    col_summary = {}
                    for col_name, col_data in list(columns.items())[:15]:
                        if isinstance(col_data, dict):
                            col_summary[col_name] = {
                                k: col_data[k]
                                for k in ("type", "dtype", "missing_pct", "null_pct", "unique",
                                          "nunique", "mean", "std", "min", "max", "skew",
                                          "top_values", "mode")
                                if k in col_data
                            }
                        else:
                            col_summary[col_name] = str(col_data)[:200]
                    profile_summary["columns"] = col_summary
            context_parts.append(f"Profile: {json.dumps(profile_summary, default=str)[:2500]}")

        # Summarize check results
        if check_results:
            check_summary = []
            for c in check_results[:20]:
                check_summary.append({
                    "rule": c.get("rule_name", c.get("name", c.get("rule", "unknown"))),
                    "type": c.get("type", ""),
                    "status": c.get("status", "unknown"),
                    "score": c.get("score"),
                    "column": c.get("column", c.get("config", {}).get("column", "")),
                    "message": c.get("message", "")[:200],
                })
            context_parts.append(f"Check Results: {json.dumps(check_summary, default=str)[:2000]}")

        user_prompt = "\n\n".join(context_parts)

        response = call_llm(SUGGESTIONS_SYSTEM, user_prompt, temperature=0.3, max_tokens=4096)
        if not response:
            return None

        suggestions = _parse_suggestions_response(response)
        return suggestions if suggestions else None
