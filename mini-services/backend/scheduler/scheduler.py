"""
Scheduler Engine — Schedule quality checks and pipeline runs.
Uses APScheduler for cron-based scheduling with smart alerting.
"""

import json
import uuid
import os
import time
from datetime import datetime


SCHEDULES_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'schedules.json'))
os.makedirs(os.path.dirname(SCHEDULES_FILE), exist_ok=True)


class SchedulerEngine:
    """Manage scheduled quality checks and pipeline runs."""

    def __init__(self):
        self.schedules = self._load_schedules()

    def _load_schedules(self) -> list:
        if os.path.exists(SCHEDULES_FILE):
            try:
                with open(SCHEDULES_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_schedules(self):
        with open(SCHEDULES_FILE, 'w') as f:
            json.dump(self.schedules, f, indent=2, default=str)

    def create_schedule(self, config: dict) -> dict:
        schedule_id = uuid.uuid4().hex[:12]
        schedule = {
            "id": schedule_id,
            "name": config.get("name", f"Schedule_{schedule_id}"),
            "type": config.get("type", "check"),  # check, pipeline, eda
            "target_id": config.get("target_id", ""),  # ruleId, pipelineId, tableId
            "cron": config.get("cron", "0 9 * * *"),  # default: daily at 9am
            "interval": config.get("interval", ""),  # alternative: "5m", "1h", "1d"
            "enabled": config.get("enabled", True),
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "failure_count": 0,
            "alert_on_failure": config.get("alert_on_failure", True),
            "alert_channels": config.get("alert_channels", ["in_app"]),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "config": config,
        }
        self.schedules.append(schedule)
        self._save_schedules()
        return schedule

    def list_schedules(self) -> list:
        return self.schedules

    def get_schedule(self, schedule_id: str) -> dict | None:
        for s in self.schedules:
            if s["id"] == schedule_id:
                return s
        return None

    def update_schedule(self, schedule_id: str, updates: dict) -> dict | None:
        for s in self.schedules:
            if s["id"] == schedule_id:
                for k, v in updates.items():
                    if k in ('name', 'cron', 'interval', 'enabled', 'alert_on_failure', 'alert_channels', 'config'):
                        s[k] = v
                self._save_schedules()
                return s
        return None

    def delete_schedule(self, schedule_id: str) -> bool:
        before = len(self.schedules)
        self.schedules = [s for s in self.schedules if s["id"] != schedule_id]
        self._save_schedules()
        return len(self.schedules) < before

    def record_run(self, schedule_id: str, success: bool, result_summary: dict = None):
        for s in self.schedules:
            if s["id"] == schedule_id:
                s["last_run"] = datetime.utcnow().isoformat() + "Z"
                s["run_count"] = s.get("run_count", 0) + 1
                if not success:
                    s["failure_count"] = s.get("failure_count", 0) + 1
                if result_summary:
                    s["last_result"] = result_summary
                self._save_schedules()
                return

    def get_due_schedules(self) -> list:
        """Get schedules that are due to run (simplified cron check)."""
        now = datetime.utcnow()
        due = []
        for s in self.schedules:
            if not s.get("enabled", True):
                continue
            # Simple interval-based check
            last_run = s.get("last_run")
            interval = s.get("interval", "")
            if interval and last_run:
                last = datetime.fromisoformat(last_run.replace('Z', ''))
                delta = now - last
                if interval.endswith('m'):
                    minutes = int(interval[:-1])
                    if delta.total_seconds() < minutes * 60:
                        continue
                elif interval.endswith('h'):
                    hours = int(interval[:-1])
                    if delta.total_seconds() < hours * 3600:
                        continue
                elif interval.endswith('d'):
                    days = int(interval[:-1])
                    if delta.total_seconds() < days * 86400:
                        continue
            due.append(s)
        return due


scheduler = SchedulerEngine()
