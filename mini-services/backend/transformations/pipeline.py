"""
Pipeline Engine — DAG-based transformation pipeline builder.
Supports chaining transformations, conditional branching, and versioning.
"""

import json
import uuid
import time
from datetime import datetime
from typing import Optional
from transformations import get_transformer
from transformations.history import TransformHistory
from engine.rule_executor import load_dataframe, save_dataframe
import pandas as pd


class PipelineStep:
    """A single step in a pipeline."""

    def __init__(self, step_id: str, transform_type: str, config: dict,
                 name: str = "", condition: str = None, next_step: str = None):
        self.id = step_id
        self.transform_type = transform_type
        self.config = config
        self.name = name or f"{transform_type}_{step_id[:6]}"
        self.condition = condition  # e.g., "check_passed", "score > 80"
        self.next_step = next_step  # Override default next step for branching


class Pipeline:
    """A DAG of transformation steps."""

    def __init__(self, pipeline_id: str, name: str, description: str = ""):
        self.id = pipeline_id
        self.name = name
        self.description = description
        self.steps: list[PipelineStep] = []
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.version = 1

    def add_step(self, transform_type: str, config: dict, name: str = "",
                 condition: str = None, next_step: str = None) -> str:
        step_id = uuid.uuid4().hex[:12]
        step = PipelineStep(step_id, transform_type, config, name, condition, next_step)
        self.steps.append(step)
        return step_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "id": s.id, "transform_type": s.transform_type,
                    "config": s.config, "name": s.name,
                    "condition": s.condition, "next_step": s.next_step,
                }
                for s in self.steps
            ],
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Pipeline':
        p = cls(data["id"], data["name"], data.get("description", ""))
        p.created_at = data.get("created_at", p.created_at)
        p.version = data.get("version", 1)
        for step_data in data.get("steps", []):
            step = PipelineStep(
                step_data["id"], step_data["transform_type"], step_data.get("config", {}),
                step_data.get("name", ""), step_data.get("condition"),
                step_data.get("next_step"),
            )
            p.steps.append(step)
        return p


class PipelineExecutor:
    """Execute a pipeline of transformations."""

    def __init__(self, table_id: str):
        self.table_id = table_id
        self.history = TransformHistory(table_id)
        self.execution_log = []

    def execute(self, pipeline: Pipeline, df: pd.DataFrame = None) -> dict:
        """Execute a pipeline and return results."""
        if df is None:
            df = load_dataframe(self.table_id)

        if df is None:
            return {"success": False, "error": "No data found for table"}

        current_df = df.copy()
        total_duration = 0
        step_results = []

        for i, step in enumerate(pipeline.steps):
            # Check condition
            if step.condition and not self._evaluate_condition(step.condition, step_results):
                step_results.append({
                    "step_id": step.id, "step_name": step.name,
                    "status": "skipped", "reason": f"Condition not met: {step.condition}",
                })
                continue

            # Save snapshot before transformation
            snapshot_id = self.history.save_snapshot(
                current_df, step.transform_type, step.config,
                {"step_index": i, "step_name": step.name}
            )

            # Execute transformation
            try:
                transformer = get_transformer(step.transform_type)
                result = transformer.transform(current_df, step.config)

                step_results.append({
                    "step_id": step.id,
                    "step_name": step.name,
                    "status": "success" if result.success else "failed",
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                    "rows_affected": result.rows_affected,
                    "columns_affected": result.columns_affected,
                    "details": result.details,
                    "snapshot_id": snapshot_id,
                })

                if result.success:
                    current_df = result.df
                    # Save intermediate result
                    save_dataframe(self.table_id, current_df)

                total_duration += result.duration_ms

            except Exception as e:
                step_results.append({
                    "step_id": step.id, "step_name": step.name,
                    "status": "error", "message": str(e),
                    "snapshot_id": snapshot_id,
                })
                # Stop pipeline on error
                break

            # Handle branching
            if step.next_step:
                # Find the next step by ID
                next_idx = next((j for j, s in enumerate(pipeline.steps) if s.id == step.next_step), None)
                if next_idx is not None and next_idx != i + 1:
                    # Continue from the branched step
                    pass  # For now, linear execution; branching is a future enhancement

        # Save final result
        save_dataframe(self.table_id, current_df)

        return {
            "success": any(r.get("status") == "success" for r in step_results),
            "pipeline_id": pipeline.id,
            "pipeline_name": pipeline.name,
            "total_steps": len(pipeline.steps),
            "completed_steps": sum(1 for r in step_results if r.get("status") == "success"),
            "skipped_steps": sum(1 for r in step_results if r.get("status") == "skipped"),
            "failed_steps": sum(1 for r in step_results if r.get("status") in ("failed", "error")),
            "total_duration_ms": total_duration,
            "step_results": step_results,
            "final_shape": list(current_df.shape),
        }

    def _evaluate_condition(self, condition: str, step_results: list) -> bool:
        """Evaluate simple conditions based on previous step results."""
        if not step_results:
            return condition != "check_passed"

        last_result = step_results[-1]

        if condition == "check_passed":
            return last_result.get("status") == "success"
        elif condition == "check_failed":
            return last_result.get("status") == "failed"
        elif condition.startswith("score > "):
            threshold = float(condition.split(">")[1].strip())
            score = last_result.get("details", {}).get("score", 0)
            return score > threshold
        elif condition == "always":
            return True

        return True  # Default: execute the step
