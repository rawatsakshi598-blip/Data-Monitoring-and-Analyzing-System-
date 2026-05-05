"""
Quality Report Models
LLM-generated reports with diagnosis and fix code.
"""

from pydantic import BaseModel
from typing import Optional


class ReportRequest(BaseModel):
    """Request to generate a quality report."""

    table_name: str
    dataset_id: Optional[str] = None
    check_results: list[dict] = []  # Summary of check results


class ReportResponse(BaseModel):
    """LLM-generated quality report."""

    id: str
    table_name: str
    dataset_id: Optional[str] = None
    overall_score: float = 0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    summary: str = ""
    diagnosis: str = ""
    action_plan: str = ""
    fix_code: str = ""
    fix_language: str = "python"
    created_at: str = ""


class FixRequest(BaseModel):
    """Request to generate fix code."""

    table_name: str
    failures: list[dict] = []  # List of failed check summaries
    columns_info: Optional[list[dict]] = None


class FixResponse(BaseModel):
    """LLM-generated fix code."""

    fix_code: str
    fix_language: str = "python"
    explanation: str = ""
