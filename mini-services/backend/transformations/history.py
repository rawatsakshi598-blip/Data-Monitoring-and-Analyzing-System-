"""
Transformation History — Track all transformations with full rollback capability.
Stores snapshots of data before each transformation for undo operations.
"""

import os
import json
import time
import pandas as pd
from datetime import datetime

HISTORY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'history'))
os.makedirs(HISTORY_DIR, exist_ok=True)


class TransformHistory:
    """Track and manage transformation history with rollback support."""

    def __init__(self, table_id: str):
        self.table_id = table_id
        self.history_dir = os.path.join(HISTORY_DIR, table_id)
        os.makedirs(self.history_dir, exist_ok=True)
        self.manifest_path = os.path.join(self.history_dir, 'manifest.json')
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> list:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_manifest(self):
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2, default=str)

    def save_snapshot(self, df: pd.DataFrame, transform_type: str, config: dict, result_summary: dict) -> str:
        """Save a snapshot before transformation for rollback."""
        snapshot_id = f"snap_{int(time.time() * 1000)}"
        snapshot_path = os.path.join(self.history_dir, f"{snapshot_id}.csv")
        df.to_csv(snapshot_path, index=False)

        entry = {
            "id": snapshot_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "transform_type": transform_type,
            "config": config,
            "result_summary": result_summary,
            "snapshot_path": snapshot_path,
            "rows": len(df),
            "columns": list(df.columns),
        }

        self.manifest.append(entry)
        self._save_manifest()
        return snapshot_id

    def rollback(self, snapshot_id: str) -> pd.DataFrame | None:
        """Rollback to a specific snapshot."""
        for entry in reversed(self.manifest):
            if entry["id"] == snapshot_id:
                path = entry["snapshot_path"]
                if os.path.exists(path):
                    return pd.read_csv(path)
        return None

    def rollback_last(self) -> pd.DataFrame | None:
        """Rollback to the previous state (undo last transformation)."""
        if len(self.manifest) < 1:
            return None
        last_entry = self.manifest[-1]
        path = last_entry["snapshot_path"]
        if os.path.exists(path):
            # Remove the last entry from manifest
            self.manifest.pop()
            self._save_manifest()
            return pd.read_csv(path)
        return None

    def get_history(self, limit: int = 50) -> list:
        """Get transformation history."""
        return self.manifest[-limit:]

    def clear_history(self):
        """Clear all history snapshots."""
        import shutil
        if os.path.exists(self.history_dir):
            shutil.rmtree(self.history_dir)
            os.makedirs(self.history_dir, exist_ok=True)
        self.manifest = []
        self._save_manifest()

    def get_snapshot_info(self, snapshot_id: str) -> dict | None:
        """Get info about a specific snapshot."""
        for entry in self.manifest:
            if entry["id"] == snapshot_id:
                return entry
        return None
