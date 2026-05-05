"""Unit tests for SchedulerEngine."""

import os, sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scheduler.scheduler import SchedulerEngine


class TestScheduler:
    def setup_method(self):
        self.engine = SchedulerEngine()
        # Clean up any existing schedules for test isolation
        self.engine.schedules = []
        self.engine._save_schedules()

    def test_create_schedule(self):
        schedule = self.engine.create_schedule({
            "name": "Daily Check",
            "type": "check",
            "target_id": "table_1",
            "cron": "0 9 * * *",
        })
        assert schedule["id"]
        assert schedule["name"] == "Daily Check"
        assert schedule["type"] == "check"
        assert schedule["enabled"] is True

    def test_list_schedules(self):
        self.engine.create_schedule({"name": "S1"})
        self.engine.create_schedule({"name": "S2"})
        schedules = self.engine.list_schedules()
        assert len(schedules) == 2

    def test_get_schedule(self):
        s = self.engine.create_schedule({"name": "FindMe"})
        found = self.engine.get_schedule(s["id"])
        assert found is not None
        assert found["name"] == "FindMe"

    def test_get_schedule_not_found(self):
        found = self.engine.get_schedule("nonexistent")
        assert found is None

    def test_update_schedule(self):
        s = self.engine.create_schedule({"name": "Original", "cron": "0 9 * * *"})
        updated = self.engine.update_schedule(s["id"], {"name": "Updated", "cron": "0 12 * * *"})
        assert updated["name"] == "Updated"
        assert updated["cron"] == "0 12 * * *"

    def test_update_schedule_not_found(self):
        result = self.engine.update_schedule("nonexistent", {"name": "X"})
        assert result is None

    def test_update_schedule_partial(self):
        s = self.engine.create_schedule({"name": "Original", "cron": "0 9 * * *"})
        updated = self.engine.update_schedule(s["id"], {"name": "NewName"})
        assert updated["name"] == "NewName"
        assert updated["cron"] == "0 9 * * *"  # unchanged

    def test_delete_schedule(self):
        s = self.engine.create_schedule({"name": "ToDelete"})
        result = self.engine.delete_schedule(s["id"])
        assert result is True
        assert self.engine.get_schedule(s["id"]) is None

    def test_delete_schedule_not_found(self):
        result = self.engine.delete_schedule("nonexistent")
        assert result is False

    def test_record_run(self):
        s = self.engine.create_schedule({"name": "RunTest"})
        self.engine.record_run(s["id"], success=True, result_summary={"score": 95.0})
        updated = self.engine.get_schedule(s["id"])
        assert updated["run_count"] == 1
        assert updated["last_run"] is not None
        assert updated["failure_count"] == 0

    def test_record_run_failure(self):
        s = self.engine.create_schedule({"name": "FailTest"})
        self.engine.record_run(s["id"], success=False, result_summary={"error": "timeout"})
        updated = self.engine.get_schedule(s["id"])
        assert updated["run_count"] == 1
        assert updated["failure_count"] == 1

    def test_record_run_multiple(self):
        s = self.engine.create_schedule({"name": "MultiRun"})
        self.engine.record_run(s["id"], success=True)
        self.engine.record_run(s["id"], success=True)
        self.engine.record_run(s["id"], success=False)
        updated = self.engine.get_schedule(s["id"])
        assert updated["run_count"] == 3
        assert updated["failure_count"] == 1

    def test_get_due_schedules_enabled(self):
        s = self.engine.create_schedule({"name": "Due", "enabled": True})
        due = self.engine.get_due_schedules()
        assert len(due) >= 1
        assert any(d["id"] == s["id"] for d in due)

    def test_get_due_schedules_disabled(self):
        s = self.engine.create_schedule({"name": "Disabled", "enabled": False})
        due = self.engine.get_due_schedules()
        assert not any(d["id"] == s["id"] for d in due)

    def test_schedule_default_values(self):
        s = self.engine.create_schedule({"name": "Defaults"})
        assert s["cron"] == "0 9 * * *"
        assert s["type"] == "check"
        assert s["enabled"] is True
        assert s["run_count"] == 0
        assert s["failure_count"] == 0

    def test_schedule_with_interval(self):
        s = self.engine.create_schedule({"name": "Interval", "interval": "5m"})
        assert s["interval"] == "5m"

    def test_create_schedule_persists(self):
        """Verify data persists across engine instances."""
        s = self.engine.create_schedule({"name": "Persist"})
        # Create new engine instance
        engine2 = SchedulerEngine()
        found = engine2.get_schedule(s["id"])
        assert found is not None
        assert found["name"] == "Persist"
        # Cleanup
        engine2.delete_schedule(s["id"])
