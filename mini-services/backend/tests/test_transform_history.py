"""
Comprehensive unit tests for the Transform History module.
Tests snapshot saving, rollback, history retrieval, and cleanup.
"""

import os
import sys
import pytest
import pandas as pd
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from transformations.history import TransformHistory, HISTORY_DIR


# ── Fixtures ──

@pytest.fixture
def history():
    """Create a TransformHistory with a unique table ID for test isolation."""
    import time
    table_id = f"test_table_{int(time.time() * 1000)}"
    hist = TransformHistory(table_id)
    yield hist
    # Cleanup
    if os.path.exists(hist.history_dir):
        shutil.rmtree(hist.history_dir)


@pytest.fixture
def sample_df():
    return pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})


@pytest.fixture
def modified_df():
    return pd.DataFrame({'a': [1, 2, 3, 4], 'b': ['x', 'y', 'z', 'w']})


@pytest.fixture
def populated_history(sample_df, modified_df):
    """Create a history with multiple snapshots."""
    import time
    table_id = f"test_table_pop_{int(time.time() * 1000)}"
    hist = TransformHistory(table_id)
    hist.save_snapshot(sample_df, 'initial', {}, {})
    time.sleep(0.01)  # Ensure unique snapshot IDs
    hist.save_snapshot(modified_df, 'dedup', {'method': 'exact'}, {'rows_affected': 1})
    yield hist
    if os.path.exists(hist.history_dir):
        shutil.rmtree(hist.history_dir)


# ═══════════════════════════════════════════════
# Save Snapshot
# ═══════════════════════════════════════════════

class TestSaveSnapshot:
    def test_save_snapshot(self, history, sample_df):
        snap_id = history.save_snapshot(sample_df, 'imputation', {'method': 'mean'}, {})
        assert snap_id is not None
        assert snap_id.startswith('snap_')

    def test_save_snapshot_creates_file(self, history, sample_df):
        snap_id = history.save_snapshot(sample_df, 'imputation', {'method': 'mean'}, {})
        snap_path = os.path.join(history.history_dir, f"{snap_id}.csv")
        assert os.path.exists(snap_path)

    def test_save_snapshot_updates_manifest(self, history, sample_df):
        history.save_snapshot(sample_df, 'test', {}, {})
        assert len(history.manifest) == 1

    def test_save_multiple_snapshots(self, history, sample_df, modified_df):
        history.save_snapshot(sample_df, 'step1', {}, {})
        history.save_snapshot(modified_df, 'step2', {}, {})
        assert len(history.manifest) == 2

    def test_snapshot_entry_fields(self, history, sample_df):
        snap_id = history.save_snapshot(sample_df, 'imputation', {'method': 'mean'},
                                         {'rows_affected': 5})
        entry = history.manifest[-1]
        assert entry['id'] == snap_id
        assert entry['transform_type'] == 'imputation'
        assert 'timestamp' in entry
        assert entry['rows'] == 3
        assert list(entry['columns']) == ['a', 'b']


# ═══════════════════════════════════════════════
# Rollback
# ═══════════════════════════════════════════════

class TestRollback:
    def test_rollback_last(self, populated_history, modified_df):
        result = populated_history.rollback_last()
        assert result is not None
        # rollback_last returns the LAST entry's snapshot, which is modified_df (4 rows)
        assert len(result) == 4

    def test_rollback_last_removes_entry(self, populated_history):
        initial_count = len(populated_history.manifest)
        populated_history.rollback_last()
        assert len(populated_history.manifest) == initial_count - 1

    def test_rollback_specific_snapshot(self, populated_history, sample_df):
        snap_id = populated_history.manifest[0]['id']
        result = populated_history.rollback(snap_id)
        assert result is not None
        assert len(result) == 3  # sample_df

    def test_rollback_nonexistent_snapshot(self, populated_history):
        result = populated_history.rollback('nonexistent_snap_id')
        assert result is None

    def test_rollback_empty_history(self, history):
        result = history.rollback_last()
        assert result is None

    def test_rollback_twice_returns_earlier_state(self, populated_history, sample_df):
        # Rollback twice to get back to the first snapshot
        populated_history.rollback_last()
        result = populated_history.rollback_last()
        assert result is not None
        assert len(result) == 3  # sample_df


# ═══════════════════════════════════════════════
# Get History
# ═══════════════════════════════════════════════

class TestGetHistory:
    def test_get_history(self, populated_history):
        history = populated_history.get_history()
        assert len(history) >= 1

    def test_get_history_limit(self, history, sample_df):
        for i in range(10):
            history.save_snapshot(sample_df, f'step_{i}', {}, {})
        result = history.get_history(limit=5)
        assert len(result) == 5

    def test_get_history_empty(self, history):
        result = history.get_history()
        assert result == []

    def test_get_history_returns_latest(self, history, sample_df, modified_df):
        history.save_snapshot(sample_df, 'step1', {}, {})
        history.save_snapshot(modified_df, 'step2', {}, {})
        result = history.get_history(limit=1)
        assert result[0]['transform_type'] == 'step2'


# ═══════════════════════════════════════════════
# Get Snapshot Info
# ═══════════════════════════════════════════════

class TestGetSnapshotInfo:
    def test_get_snapshot_info(self, history, sample_df):
        snap_id = history.save_snapshot(sample_df, 'imputation', {'method': 'mean'},
                                         {'rows_affected': 5})
        info = history.get_snapshot_info(snap_id)
        assert info is not None
        assert info['transform_type'] == 'imputation'
        assert info['rows'] == 3

    def test_get_snapshot_info_nonexistent(self, history):
        info = history.get_snapshot_info('nonexistent')
        assert info is None


# ═══════════════════════════════════════════════
# Clear History
# ═══════════════════════════════════════════════

class TestClearHistory:
    def test_clear_history(self, populated_history):
        populated_history.clear_history()
        assert len(populated_history.manifest) == 0

    def test_clear_history_removes_files(self, populated_history):
        populated_history.clear_history()
        # Directory should still exist but be empty
        assert os.path.exists(populated_history.history_dir)
        files = os.listdir(populated_history.history_dir)
        # Only manifest.json should remain (or it's also cleared)
        csv_files = [f for f in files if f.endswith('.csv')]
        assert len(csv_files) == 0

    def test_clear_history_on_empty(self, history):
        history.clear_history()
        assert len(history.manifest) == 0


# ═══════════════════════════════════════════════
# Data Integrity
# ═══════════════════════════════════════════════

class TestDataIntegrity:
    def test_rollback_restores_data(self, history, sample_df, modified_df):
        import time
        history.save_snapshot(sample_df, 'original', {}, {})
        time.sleep(0.01)  # Ensure unique snapshot IDs
        history.save_snapshot(modified_df, 'modified', {}, {})

        # First rollback returns the last snapshot (modified_df)
        result = history.rollback_last()
        assert len(result) == 4  # modified_df has 4 rows

        # Second rollback returns the first snapshot (sample_df)
        result2 = history.rollback_last()
        assert len(result2) == 3  # sample_df has 3 rows
        assert list(result2['a']) == [1, 2, 3]

    def test_multiple_rollbacks(self, history):
        df1 = pd.DataFrame({'a': [1], 'b': ['x']})
        df2 = pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']})
        df3 = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})

        import time
        history.save_snapshot(df1, 'step1', {}, {})
        time.sleep(0.01)
        history.save_snapshot(df2, 'step2', {}, {})
        time.sleep(0.01)
        history.save_snapshot(df3, 'step3', {}, {})

        # Rollback returns the last snapshot each time
        result1 = history.rollback_last()
        assert len(result1) == 3  # df3

        result2 = history.rollback_last()
        assert len(result2) == 2  # df2

        result3 = history.rollback_last()
        assert len(result3) == 1  # df1


# ═══════════════════════════════════════════════
# Persistence
# ═══════════════════════════════════════════════

class TestPersistence:
    def test_manifest_persists(self, history, sample_df):
        history.save_snapshot(sample_df, 'test', {}, {})
        table_id = history.table_id

        # Create a new history instance with the same table_id
        hist2 = TransformHistory(table_id)
        assert len(hist2.manifest) == 1
        assert hist2.manifest[0]['transform_type'] == 'test'

        # Cleanup
        if os.path.exists(hist2.history_dir):
            shutil.rmtree(hist2.history_dir)

    def test_history_dir_creation(self):
        import time
        table_id = f"test_persist_{int(time.time() * 1000)}"
        hist = TransformHistory(table_id)
        assert os.path.exists(hist.history_dir)
        # Cleanup
        if os.path.exists(hist.history_dir):
            shutil.rmtree(hist.history_dir)
