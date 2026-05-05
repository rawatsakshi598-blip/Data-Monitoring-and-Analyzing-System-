"""
Quality Rule Models
Field names match YOUR QualityRule DB columns exactly:
  type, dimension, severity, config, enabled, schedule, datasetId
config is stored as JSON string in DB, parsed into CheckConfig here.
"""

from pydantic import BaseModel
from typing import Optional


class CheckConfig(BaseModel):
    """Configuration for a single check. Stored as JSON in the config column."""

    column: Optional[str] = None
    threshold: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    valid_values: Optional[list] = None
    regex: Optional[str] = None
    max_null_percent: Optional[float] = None


class RuleCreate(BaseModel):
    """Request to create a rule. Fields match your QualityRule table."""

    name: str
    description: str = ""
    type: str = (
        "validity"  # completeness, uniqueness, validity, freshness, volume, schema
    )
    dimension: str = (
        "validity"  # completeness, uniqueness, validity, timeliness, volume, conformity
    )
    severity: str = "warning"  # info, warning, error, critical
    config: CheckConfig = CheckConfig()  # stored as JSON string in DB
    enabled: bool = True
    schedule: str = "manual"  # manual, daily, weekly, hourly
    datasetId: Optional[str] = None


class NLRuleRequest(BaseModel):
    """Request to generate a rule from natural language."""

    prompt: str
    datasetId: Optional[str] = None
    tableName: Optional[str] = None
    columnName: Optional[str] = None
    columns_info: Optional[list[dict]] = None
