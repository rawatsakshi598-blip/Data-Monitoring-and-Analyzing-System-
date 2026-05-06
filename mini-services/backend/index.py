from dotenv import load_dotenv

load_dotenv()
"""
DataGuard Python Backend - FastAPI
Data Quality Monitoring API Service
Port: 3001
"""

import json
import re
import uuid
import os
import io
import time
import numpy as np
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import aiosqlite
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from models.check_result import CheckResult
from engine.rule_executor import (
    execute_rule,
    execute_profile_check,
    load_dataframe,
    save_dataframe,
)

# ── Config ──
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "custom.db")
)
CHUNKS_DIR = "/tmp/dataguard_chunks"
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_COLUMNS = 1000
MAX_ROWS = 10_000_000

# System tables used internally by DataGuard — hidden from users in SQL Playground & Local DB browser
DATAGUARD_SYSTEM_TABLES = frozenset(
    {
        "Service",
        "Table",
        "Dataset",
        "QualityRule",
        "QualityCheck",
        "ComplianceReport",
        "DQTest",
        "DQTestResult",
        "Alert",
        "Team",
        "Activity",
        "DataLineage",
        "Tag",
        "GlossaryTerm",
        "TableProfile",
        "TransformHistory",
        "Pipeline",
        "PipelineRun",
        "AutoEDARport",
        "MLReadinessScore",
        "DataContract",
        "ContractValidation",
        "ScheduledJob",
        "Connector",
        "StatisticalTest",
        "FixApproval",
        "CopilotChat",
    }
)


def gen_id():
    return uuid.uuid4().hex


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def days_ago_iso(n):
    return (datetime.utcnow() - timedelta(days=n)).isoformat() + "Z"


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""

    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def safe_json_dumps(obj, **kwargs):
    """json.dumps that handles numpy types."""
    return json.dumps(obj, cls=NumpyEncoder, **kwargs)


def _sanitize_for_json(obj):
    """Recursively convert numpy types to native Python types for FastAPI response."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _is_one_hot_encoded(df: pd.DataFrame) -> bool:
    """Detect if a DataFrame has been one-hot encoded.
    One-hot encoded DataFrames have columns like 'Unnamed: N_value' with binary 0/1 values.
    """
    oh_pattern = re.compile(r"^Unnamed:\s*\d+_(.+)$")
    oh_col_count = sum(1 for c in df.columns if oh_pattern.match(str(c)))
    return oh_col_count > len(df.columns) * 0.5 and oh_col_count > 5


def _extract_one_hot_headers(df: pd.DataFrame) -> dict:
    """Extract original column headers from a one-hot encoded DataFrame.
    Returns dict: group_number → header_name

    For one-hot encoded columns like:
      Unnamed: 0_Name, Unnamed: 0_aak, Unnamed: 0_abp  → group 0 → header 'Name'
      Unnamed: 1_Age (Years), Unnamed: 1_10, Unnamed: 1_12 → group 1 → header 'Age (Years)'

    The header is identified as the suffix that looks most like a column name
    (has spaces, parentheses, or is the longest non-numeric suffix in the group).
    """
    oh_pattern = re.compile(r"^Unnamed:\s*(\d+)_(.+)$")
    groups = {}  # group_num → list of suffixes

    for col in df.columns:
        m = oh_pattern.match(str(col))
        if m:
            group_num = m.group(1)
            suffix = m.group(2).strip()
            if group_num not in groups:
                groups[group_num] = []
            groups[group_num].append(suffix)

    headers = {}
    for group_num, suffixes in groups.items():
        # Strategy: pick the suffix that looks most like a header (not a data value)
        # Heuristics:
        #   1. Contains spaces or parentheses → likely a header
        #   2. Is NOT purely numeric → likely a header
        #   3. Is the longest non-numeric suffix
        best = None
        for s in suffixes:
            s_stripped = s.strip()
            if not s_stripped:
                continue
            # Has spaces/parens/underscores with letters → likely a header name
            has_letters = any(c.isalpha() for c in s_stripped)
            has_space_or_paren = (
                " " in s_stripped or "(" in s_stripped or ")" in s_stripped
            )
            is_numeric = (
                s_stripped.replace(".", "").replace("-", "").replace("+", "").isdigit()
            )

            if has_space_or_paren and has_letters:
                best = s_stripped
                break
            elif has_letters and not is_numeric:
                if best is None or len(s_stripped) > len(best):
                    best = s_stripped

        # Fallback: longest suffix that has any letters
        if best is None:
            for s in suffixes:
                if any(c.isalpha() for c in s):
                    if best is None or len(s.strip()) > len(best):
                        best = s.strip()

        # Last resort: use first suffix
        if best is None and suffixes:
            best = suffixes[0].strip()

        if best:
            headers[group_num] = best

    return headers


def _de_one_hot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct original columns from a one-hot encoded DataFrame.

    Converts binary columns like:
      Unnamed: 1_10=0, Unnamed: 1_12=1, Unnamed: 1_18=0  →  Age (Years)=12
      Unnamed: 2_Male=1, Unnamed: 2_Female=0              →  Sex=Male

    Returns a new DataFrame with original column names and values.
    """
    if not _is_one_hot_encoded(df):
        return df

    oh_pattern = re.compile(r"^Unnamed:\s*(\d+)_(.+)$")
    headers = _extract_one_hot_headers(df)

    # Group columns by their group number
    groups = {}  # group_num → [(col_name, value_suffix), ...]
    non_oh_cols = []  # columns that aren't one-hot encoded

    for col in df.columns:
        m = oh_pattern.match(str(col))
        if m:
            group_num = m.group(1)
            suffix = m.group(2).strip()
            if group_num not in groups:
                groups[group_num] = []
            groups[group_num].append((str(col), suffix))
        else:
            non_oh_cols.append(str(col))

    result = pd.DataFrame()

    # Copy non-one-hot columns as-is
    for col in non_oh_cols:
        result[col] = df[col].values

    # Reconstruct each group
    for group_num in sorted(groups.keys(), key=lambda x: int(x)):
        header_name = headers.get(group_num, f"Column_{group_num}")
        col_entries = groups[group_num]  # [(col_name, value_suffix), ...]

        # For each row, find which column has value 1 (or the max value)
        reconstructed = []
        col_names = [e[0] for e in col_entries]
        suffixes = [e[1] for e in col_entries]
        sub_df = df[col_names]

        for idx in range(len(df)):
            row_vals = sub_df.iloc[idx]
            # Try to find the column with value == 1 (binary one-hot)
            ones_mask = row_vals == 1
            if ones_mask.any():
                # Find which columns are 1
                ones_indices = ones_mask[ones_mask].index.tolist()
                if len(ones_indices) >= 1:
                    # Use the first column that has value 1
                    col_idx = col_names.index(ones_indices[0])
                    val_str = suffixes[col_idx]
                else:
                    val_str = None
            else:
                # No 1 found — try max value, or NaN
                try:
                    numeric_vals = pd.to_numeric(row_vals, errors="coerce")
                    max_idx = numeric_vals.idxmax()
                    if pd.notna(numeric_vals[max_idx]) and numeric_vals[max_idx] > 0:
                        col_idx = col_names.index(max_idx)
                        val_str = suffixes[col_idx]
                    else:
                        val_str = None  # Missing value
                except Exception:
                    val_str = None

            # Try to convert to numeric if possible
            if val_str is not None:
                try:
                    val = float(val_str)
                    if val == int(val):
                        val = int(val)
                    reconstructed.append(val)
                except (ValueError, TypeError):
                    reconstructed.append(val_str)
            else:
                reconstructed.append(None)

        result[header_name] = reconstructed

    # ── Post-processing: convert columns to numeric where possible ──
    # After one-hot decoding, some columns may have mixed types (e.g., header row string + numeric data)
    # Only convert if >50% of non-null values are numeric
    for col in result.columns:
        try:
            numeric_converted = pd.to_numeric(result[col], errors="coerce")
            non_null_count = result[col].notna().sum()
            numeric_count = numeric_converted.notna().sum()
            if non_null_count > 0 and numeric_count / non_null_count > 0.5:
                result[col] = numeric_converted
        except Exception:
            pass  # Keep as-is if conversion fails

    return result


def _resolve_column(
    configured_col: str, df_columns: list, de_one_hot_headers: dict = None
) -> str:
    """When a rule's configured column doesn't exist in the DataFrame, try to find the right one.
    Handles cases like:
      - 'Unnamed: 8' → look for the real header column in its group
      - Case mismatches: 'age' vs 'Age'
      - Substring matches: 'age' in 'Age_at_diagnosis'
      - One-hot encoded: 'Age (Years)' → find 'Unnamed: N_Age (Years)' header column

    If de_one_hot_headers is provided (group_num → header_name), and the configured_col
    matches a de-one-hot header name, return empty string (meaning: use de-one-hot DataFrame instead).

    Returns the resolved column name, or empty string if no match found.
    """
    if not configured_col or not df_columns:
        return ""

    # Strategy 0: If we have de-one-hot headers, and the configured column matches one,
    # signal that the de-one-hot DataFrame should be used (return empty to trigger that path)
    if de_one_hot_headers:
        for gnum, header_name in de_one_hot_headers.items():
            if header_name.strip().lower() == configured_col.strip().lower():
                return ""  # Column will exist in the de-one-hot DataFrame

    # Strategy 1: One-hot encoded match — configured col matches an Unnamed header suffix
    # e.g., configured_col="Age (Years)" matches "Unnamed: 1_Age (Years)"
    oh_pattern = re.compile(r"^Unnamed:\s*\d+_(.+)$")
    for col in df_columns:
        m = oh_pattern.match(col)
        if m and m.group(1).strip() == configured_col.strip():
            return col

    # Strategy 2: Case-insensitive exact match
    for col in df_columns:
        if col.lower() == configured_col.lower():
            return col

    # Strategy 3: Unnamed column — try to find the header column in the same group
    if re.match(r"^Unnamed:\s*\d+$", configured_col, re.IGNORECASE):
        # Can't determine the right column from an Unnamed name alone
        real_cols = [
            c for c in df_columns if not re.match(r"^Unnamed:\s*\d+$", c, re.IGNORECASE)
        ]
        if len(real_cols) == 1:
            return real_cols[0]
        return ""

    # Strategy 4: Substring match — configured_col is part of a real column name
    for col in df_columns:
        if (
            configured_col.lower() in col.lower()
            or col.lower() in configured_col.lower()
        ):
            return col

    # Strategy 5: Word-level match
    config_words = set(
        configured_col.lower()
        .replace("_", " ")
        .replace("(", "")
        .replace(")", "")
        .split()
    )
    for col in df_columns:
        col_clean = oh_pattern.sub(r"\1", col) if oh_pattern.match(col) else col
        col_words = set(
            col_clean.lower()
            .replace("_", " ")
            .replace("(", "")
            .replace(")", "")
            .split()
        )
        if config_words & col_words:  # intersection
            return col

    return ""


# ── DB Helper ──


async def query_one(db, sql, params=()):
    """Execute query and return first row as dict or None."""
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    await cursor.close()
    return dict(row) if row else None


async def query_all(db, sql, params=()):
    """Execute query and return all rows as list of dicts."""
    rows = await db.execute_fetchall(sql, params)
    return [dict(r) for r in rows]


async def query_scalar(db, sql, params=()):
    """Execute query and return single scalar value."""
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    await cursor.close()
    if row:
        return row[0]
    return 0


@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


# ── Init ──


async def init_db():
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    async with get_db() as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS Service (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                serviceType TEXT DEFAULT 'database', platform TEXT DEFAULT 'postgresql',
                connectionUrl TEXT, status TEXT DEFAULT 'active', owner TEXT,
                ingestionDate TEXT, lastIngested TEXT,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS "Table" (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, fullyQualifiedName TEXT, description TEXT,
                database TEXT, schema TEXT, serviceId TEXT,
                columns TEXT DEFAULT '[]', columnCount INTEGER DEFAULT 0, rowCount INTEGER DEFAULT 0,
                qualityScore REAL DEFAULT 100.0, freshnessStatus TEXT DEFAULT 'fresh',
                lastProfiled TEXT, tier TEXT DEFAULT 'T2',
                tags TEXT DEFAULT '[]', owners TEXT DEFAULT '[]',
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Dataset (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                type TEXT DEFAULT 'postgresql', connectionInfo TEXT, status TEXT DEFAULT 'active',
                rowCount INTEGER DEFAULT 0, columnCount INTEGER DEFAULT 0, qualityScore REAL DEFAULT 100.0,
                lastChecked TEXT, createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS QualityRule (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, type TEXT, dimension TEXT,
                severity TEXT DEFAULT 'error', config TEXT DEFAULT '{}', enabled INTEGER DEFAULT 1,
                schedule TEXT DEFAULT 'manual', lastTriggered TEXT, datasetId TEXT,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS QualityCheck (
                id TEXT PRIMARY KEY, ruleId TEXT, datasetId TEXT, status TEXT DEFAULT 'passed',
                score REAL DEFAULT 100.0, recordsChecked INTEGER DEFAULT 0, recordsFailed INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0, failures TEXT DEFAULT '[]', createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS ComplianceReport (
                id TEXT PRIMARY KEY, framework TEXT, datasetId TEXT, status TEXT DEFAULT 'pass',
                findings TEXT DEFAULT '[]', score REAL DEFAULT 100.0, createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS DQTest (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, tableId TEXT, description TEXT,
                status TEXT DEFAULT 'success', testType TEXT, config TEXT DEFAULT '{}',
                enabled INTEGER DEFAULT 1, lastRunAt TEXT,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS DQTestResult (
                id TEXT PRIMARY KEY, testId TEXT, status TEXT DEFAULT 'passed',
                score REAL DEFAULT 100.0, recordsChecked INTEGER DEFAULT 0, recordsFailed INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0, result TEXT DEFAULT '{}',
                timestamp TEXT DEFAULT (datetime('now')), createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Alert (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, message TEXT,
                severity TEXT DEFAULT 'error', alertType TEXT, source TEXT,
                status TEXT DEFAULT 'active', assignedTo TEXT, resolvedAt TEXT,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Team (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, displayName TEXT, description TEXT,
                email TEXT, slack TEXT,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Activity (
                id TEXT PRIMARY KEY, entityType TEXT, entityId TEXT, entityName TEXT,
                action TEXT, description TEXT, tags TEXT DEFAULT '[]',
                timestamp TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS DataLineage (
                id TEXT PRIMARY KEY, fromTableId TEXT, toTableId TEXT,
                edgeType TEXT DEFAULT 'data_flow', description TEXT,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Tag (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, displayName TEXT, description TEXT,
                color TEXT DEFAULT '#6366f1', tagFQN TEXT, usageCount INTEGER DEFAULT 0,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS GlossaryTerm (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, qualifiedName TEXT, description TEXT,
                definition TEXT, category TEXT, status TEXT DEFAULT 'draft',
                reviewers TEXT DEFAULT '[]', tags TEXT DEFAULT '[]',
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS TableProfile (
                id TEXT PRIMARY KEY, tableId TEXT,
                profileData TEXT DEFAULT '{}', rowCount INTEGER DEFAULT 0, duration INTEGER DEFAULT 0,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS TransformHistory (
                id TEXT PRIMARY KEY, tableId TEXT NOT NULL, snapshotId TEXT,
                transformType TEXT, config TEXT DEFAULT '{}', resultSummary TEXT DEFAULT '{}',
                rowsAffected INTEGER DEFAULT 0, columnsAffected TEXT DEFAULT '[]',
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Pipeline (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                steps TEXT DEFAULT '[]', version INTEGER DEFAULT 1,
                tableId TEXT, status TEXT DEFAULT 'draft',
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS PipelineRun (
                id TEXT PRIMARY KEY, pipelineId TEXT, tableId TEXT,
                status TEXT DEFAULT 'running', totalSteps INTEGER DEFAULT 0,
                completedSteps INTEGER DEFAULT 0, failedSteps INTEGER DEFAULT 0,
                totalDurationMs INTEGER DEFAULT 0, stepResults TEXT DEFAULT '[]',
                finalShape TEXT DEFAULT '[]',
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS AutoEDARport (
                id TEXT PRIMARY KEY, tableId TEXT, tableName TEXT,
                overview TEXT DEFAULT '{}', columnProfiles TEXT DEFAULT '{}',
                correlations TEXT DEFAULT '{}', missingAnalysis TEXT DEFAULT '{}',
                distributionAnalysis TEXT DEFAULT '{}', outlierSummary TEXT DEFAULT '{}',
                insights TEXT DEFAULT '[]', warnings TEXT DEFAULT '[]',
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS MLReadinessScore (
                id TEXT PRIMARY KEY, tableId TEXT, tableName TEXT,
                overallScore REAL DEFAULT 0, grade TEXT DEFAULT 'F',
                dimensions TEXT DEFAULT '{}', issues TEXT DEFAULT '[]',
                recommendations TEXT DEFAULT '[]', isMLReady INTEGER DEFAULT 0,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS DataContract (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                contractDef TEXT DEFAULT '{}', tableId TEXT,
                lastValidated TEXT, lastScore REAL DEFAULT 100.0,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS ContractValidation (
                id TEXT PRIMARY KEY, contractId TEXT, tableId TEXT,
                valid INTEGER DEFAULT 1, score REAL DEFAULT 100.0,
                violations TEXT DEFAULT '[]', totalChecks INTEGER DEFAULT 0,
                passedChecks INTEGER DEFAULT 0, failedChecks INTEGER DEFAULT 0,
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS ScheduledJob (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT DEFAULT 'check',
                targetId TEXT, cron TEXT DEFAULT '0 9 * * *',
                interval TEXT, enabled INTEGER DEFAULT 1,
                lastRun TEXT, nextRun TEXT, runCount INTEGER DEFAULT 0,
                failureCount INTEGER DEFAULT 0, alertOnFailure INTEGER DEFAULT 1,
                alertChannels TEXT DEFAULT '["in_app"]', config TEXT DEFAULT '{}',
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS Connector (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
                config TEXT DEFAULT '{}', status TEXT DEFAULT 'inactive',
                lastTested TEXT, lastError TEXT,
                createdAt TEXT DEFAULT (datetime('now')), updatedAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS StatisticalTest (
                id TEXT PRIMARY KEY, tableId TEXT, testType TEXT,
                config TEXT DEFAULT '{}', result TEXT DEFAULT '{}',
                createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS FixApproval (
                id TEXT PRIMARY KEY, tableId TEXT NOT NULL, checkId TEXT,
                fixType TEXT, fixConfig TEXT DEFAULT '{}', proposedBy TEXT DEFAULT 'ai',
                status TEXT DEFAULT 'pending', appliedAt TEXT, rolledBackAt TEXT,
                resultSummary TEXT DEFAULT '{}', createdAt TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS CopilotChat (
                id TEXT PRIMARY KEY, tableId TEXT, role TEXT, content TEXT,
                metadata TEXT DEFAULT '{}', createdAt TEXT DEFAULT (datetime('now'))
            );
        """
        )
        # ── Migrations: add columns that may be missing from older schemas ──
        migrations = [
            ("Service", "ingestionDate", "TEXT"),
            ("Service", "lastIngested", "TEXT"),
        ]
        for table, col, col_type in migrations:
            cursor = await db.execute(f"PRAGMA table_info([{table}])")
            rows = await cursor.fetchall()
            existing = {r[1] for r in rows}
            if col not in existing:
                await db.execute(f"ALTER TABLE [{table}] ADD COLUMN [{col}] {col_type}")
                print(f"[DB] Migration: added {table}.{col}")
        await db.commit()
    print(f"[DB] Initialized at {DB_PATH}")


# ── App ──


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield


app = FastAPI(title="DataGuard API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════


@app.get("/")
async def health():
    from config import get_llm_status

    return {
        "message": "DataGuard Python Backend",
        "status": "ok",
        "llm": get_llm_status(),
    }


@app.get("/api/llm-status")
async def llm_status():
    from config import get_llm_status

    return get_llm_status()


# ═══════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════
# FIND this in your index.py (around line 363-429):
# @app.get("/api/stats")
# async def get_stats():
#     ...the whole function...
#
# REPLACE it with the code below:
# ═══════════════════════════════════════════════


@app.get("/api/stats")
async def get_stats():
    import traceback

    try:
        async with get_db() as db:
            total_services = await query_scalar(db, "SELECT COUNT(*) FROM Service")
            total_tables = await query_scalar(db, 'SELECT COUNT(*) FROM "Table"')
            total_tests = await query_scalar(db, "SELECT COUNT(*) FROM QualityRule")
            total_alerts = await query_scalar(
                db, "SELECT COUNT(*) FROM Alert WHERE status='active'"
            )
            total_teams = await query_scalar(db, "SELECT COUNT(*) FROM Team")

            # ── Quality Score: prefer real QualityCheck scores over fake Table.qualityScore ──
            scores_rows = await query_all(db, 'SELECT qualityScore FROM "Table"')
            scores = [
                r["qualityScore"] for r in scores_rows if r["qualityScore"] is not None
            ]
            # Also try to get real scores from QualityCheck
            check_scores_rows = await query_all(db, "SELECT score FROM QualityCheck")
            real_check_scores = [
                r["score"] for r in check_scores_rows if r["score"] is not None
            ]
            # Use QualityCheck scores if available (more accurate), otherwise fall back to Table.qualityScore
            if real_check_scores:
                avg_score = round(sum(real_check_scores) / len(real_check_scores), 1)
            elif scores:
                avg_score = round(sum(scores) / len(scores), 1)
            else:
                avg_score = 0

            # ── Test Pass Rate: from QualityCheck (real data), not DQTest (always empty) ──
            check_status_rows = await query_all(db, "SELECT status FROM QualityCheck")
            check_statuses = [r["status"] for r in check_status_rows]
            if check_statuses:
                passed_checks = check_statuses.count("passed")
                pass_rate = round((passed_checks / len(check_statuses)) * 100, 1)
            else:
                # Fallback: check DQTest if it has data
                test_rows = await query_all(db, "SELECT status FROM DQTest")
                test_statuses = [r["status"] for r in test_rows]
                passed = test_statuses.count("success")
                pass_rate = (
                    round((passed / len(test_statuses)) * 100, 1)
                    if test_statuses
                    else 0
                )

            fresh = await query_scalar(
                db, 'SELECT COUNT(*) FROM "Table" WHERE freshnessStatus="fresh"'
            )
            stale = await query_scalar(
                db, 'SELECT COUNT(*) FROM "Table" WHERE freshnessStatus="stale"'
            )

            cutoff = days_ago_iso(1)
            recent_act = await query_scalar(
                db, "SELECT COUNT(*) FROM Activity WHERE timestamp >= ?", (cutoff,)
            )

            # ── Recent Test Results chart: from QualityCheck (real data), not DQTestResult (always empty) ──
            # Try QualityCheck first
            recent_checks = await query_all(
                db,
                "SELECT createdAt, status FROM QualityCheck ORDER BY createdAt DESC LIMIT 1000",
            )
            chart_data = {}
            for r in recent_checks:
                ts_val = r["createdAt"]
                if isinstance(ts_val, (int, float)):
                    ts = (
                        datetime.utcfromtimestamp(ts_val / 1000).strftime("%Y-%m-%d")
                        if ts_val > 1e12
                        else datetime.utcfromtimestamp(ts_val).strftime("%Y-%m-%d")
                    )
                elif ts_val:
                    ts = str(ts_val)[:10]
                else:
                    ts = "unknown"
                if ts not in chart_data:
                    chart_data[ts] = {"passed": 0, "failed": 0}
                if r["status"] == "passed":
                    chart_data[ts]["passed"] += 1
                else:
                    chart_data[ts]["failed"] += 1

            # Fallback: also check DQTestResult if QualityCheck was empty
            if not chart_data:
                recent_results = await query_all(
                    db,
                    "SELECT timestamp, status FROM DQTestResult ORDER BY timestamp DESC LIMIT 1000",
                )
                for r in recent_results:
                    ts_val = r["timestamp"]
                    if isinstance(ts_val, (int, float)):
                        ts = (
                            datetime.utcfromtimestamp(ts_val / 1000).strftime(
                                "%Y-%m-%d"
                            )
                            if ts_val > 1e12
                            else datetime.utcfromtimestamp(ts_val).strftime("%Y-%m-%d")
                        )
                    elif ts_val:
                        ts = str(ts_val)[:10]
                    else:
                        ts = "unknown"
                    if ts not in chart_data:
                        chart_data[ts] = {"passed": 0, "failed": 0}
                    if r["status"] == "passed":
                        chart_data[ts]["passed"] += 1
                    else:
                        chart_data[ts]["failed"] += 1

            recent_test_results = sorted(
                [
                    {"date": k, "passed": v["passed"], "failed": v["failed"]}
                    for k, v in chart_data.items()
                ],
                key=lambda x: x["date"],
            )[-14:]

            # ── Failed tests & total: from QualityCheck (real data) ──
            total_results = await query_scalar(db, "SELECT COUNT(*) FROM QualityCheck")
            failed_tests = await query_scalar(
                db, "SELECT COUNT(*) FROM QualityCheck WHERE status='failed'"
            )
            # Fallback to DQTestResult if QualityCheck is empty
            if total_results == 0:
                total_results = await query_scalar(
                    db, "SELECT COUNT(*) FROM DQTestResult"
                )
                failed_tests = await query_scalar(
                    db, "SELECT COUNT(*) FROM DQTestResult WHERE status='failed'"
                )

            return {
                "totalServices": int(total_services),
                "totalTables": int(total_tables),
                "totalTests": int(total_tests),
                "totalAlerts": int(total_alerts),
                "averageQualityScore": avg_score,
                "testsPassRate": pass_rate,
                "freshTables": int(fresh),
                "staleTables": int(stale),
                "totalTeams": int(total_teams),
                "recentActivityCount": int(recent_act),
                "recentTestResults": recent_test_results,
                "failedTests": int(failed_tests),
                "totalDQTestResults": int(total_results),
            }
    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "totalServices": 0,
            "totalTables": 0,
            "totalTests": 0,
            "totalAlerts": 0,
            "averageQualityScore": 0,
            "testsPassRate": 0,
            "freshTables": 0,
            "staleTables": 0,
            "totalTeams": 0,
            "recentActivityCount": 0,
            "recentTestResults": [],
            "failedTests": 0,
            "totalDQTestResults": 0,
        }


# ═══════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════


@app.get("/api/services")
async def list_services():
    try:
        async with get_db() as db:
            services = await query_all(db, "SELECT * FROM Service ORDER BY name ASC")
            for s in services:
                s["_count"] = {
                    "tables": await query_scalar(
                        db, 'SELECT COUNT(*) FROM "Table" WHERE serviceId=?', (s["id"],)
                    )
                }
            return services
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/services")
async def create_service(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        sid = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Service (id, name, description, serviceType, platform, connectionUrl, status, owner, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sid,
                    body.get("name", ""),
                    body.get("description"),
                    body.get("serviceType", "database"),
                    body.get("platform", "postgresql"),
                    body.get("connectionUrl"),
                    body.get("status", "active"),
                    body.get("owner"),
                    now,
                    now,
                ),
            )
            return {"id": sid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/services/{sid}")
async def get_service(sid: str):
    try:
        async with get_db() as db:
            s = await query_one(db, "SELECT * FROM Service WHERE id=?", (sid,))
            if not s:
                return JSONResponse(status_code=404, content={"error": "Not found"})
            s["tables"] = await query_all(
                db,
                'SELECT id, name, fullyQualifiedName, columnCount, rowCount, qualityScore, freshnessStatus FROM "Table" WHERE serviceId=? LIMIT 20',
                (sid,),
            )
            s["_count"] = {
                "tables": await query_scalar(
                    db, 'SELECT COUNT(*) FROM "Table" WHERE serviceId=?', (sid,)
                )
            }
            return s
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/services/{sid}")
async def update_service(sid: str, request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            for k, v in body.items():
                if k in (
                    "name",
                    "description",
                    "serviceType",
                    "platform",
                    "connectionUrl",
                    "status",
                    "owner",
                ):
                    await db.execute(
                        f'UPDATE Service SET "{k}"=?, updatedAt=? WHERE id=?',
                        (v, now, sid),
                    )
            return {"message": "Updated", "id": sid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/services/{sid}")
async def delete_service(sid: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM Service WHERE id=?", (sid,))
            return {"message": "Deleted", "id": sid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# TABLES
# ═══════════════════════════════════════════════


@app.get("/api/tables")
async def list_tables(
    serviceId: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "name",
    limit: Optional[int] = 100,
):
    try:
        async with get_db() as db:
            where, params = [], []
            if serviceId:
                where.append("serviceId=?")
                params.append(serviceId)
            if search:
                where.append("(name LIKE ? OR fullyQualifiedName LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            w = ("WHERE " + " AND ".join(where)) if where else ""
            order = {
                "qualityScore": "qualityScore DESC",
                "rowCount": "rowCount DESC",
            }.get(sort, "name ASC")
            rows = await query_all(
                db,
                f'SELECT * FROM "Table" {w} ORDER BY {order} LIMIT ?',
                (*params, limit),
            )
            for r in rows:
                svc = await query_one(
                    db,
                    "SELECT name, platform FROM Service WHERE id=?",
                    (r["serviceId"],),
                )
                r["service"] = (
                    svc if svc else {"name": "Unknown", "platform": "unknown"}
                )
                r["_count"] = {
                    "tests": await query_scalar(
                        db, "SELECT COUNT(*) FROM DQTest WHERE tableId=?", (r["id"],)
                    )
                }
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tables/fixed")
async def list_fixed_tables():
    """List all _fixed tables (auto-fixed copies created by the copilot)."""
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                """SELECT * FROM "Table" WHERE name LIKE '%_fixed%' ORDER BY createdAt DESC""",
            )
            for r in rows:
                svc = await query_one(
                    db,
                    "SELECT name, platform FROM Service WHERE id=?",
                    (r["serviceId"],),
                )
                r["service"] = (
                    svc if svc else {"name": "Unknown", "platform": "unknown"}
                )
                r["_count"] = {
                    "tests": await query_scalar(
                        db, "SELECT COUNT(*) FROM DQTest WHERE tableId=?", (r["id"],)
                    )
                }
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/table-data/{tid}")
async def get_table_data(tid: str, limit: int = 50):
    """Get actual data rows for a table (for preview).
    Tries CSV file first, then falls back to uploaded_data.db SQLite."""
    try:
        # Resolve name to UUID if needed, also fetch metadata
        resolved_id = tid
        tbl_meta = None
        try:
            async with get_db() as db:
                tbl_meta = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tid,))
                if not tbl_meta:
                    tbl_meta = await query_one(db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tid,))
                if tbl_meta:
                    resolved_id = tbl_meta['id']
        except Exception:
            pass

        safe_limit = max(1, min(limit, 10000))
        table_name = tbl_meta['name'] if tbl_meta else tid
        fqn = tbl_meta.get('fullyQualifiedName', table_name) if tbl_meta else table_name

        # ── ATTEMPT 1: Load from CSV file (fastest) ──
        df = load_dataframe(resolved_id)
        if df is not None:
            preview = df.head(safe_limit)
            total_rows = len(df)
            result_columns = list(df.columns.astype(str))

            col_defs = []
            for idx, col_name in enumerate(result_columns):
                dtype_str = str(df[col_name].dtype)
                if 'int' in dtype_str:
                    ctype = 'INTEGER'
                elif 'float' in dtype_str:
                    ctype = 'REAL'
                elif 'bool' in dtype_str:
                    ctype = 'BOOLEAN'
                else:
                    ctype = 'TEXT'
                col_defs.append({
                    "cid": idx,
                    "name": str(col_name),
                    "type": ctype,
                    "notnull": False,
                    "defaultValue": None,
                    "primaryKey": False,
                })

            return {
                "id": resolved_id,
                "name": table_name,
                "fullyQualifiedName": fqn,
                "columns": col_defs,
                "resultColumns": result_columns,
                "rows": _sanitize_for_json(preview.to_dict(orient='records')),
                "rowCount": len(preview),
                "totalRows": total_rows,
                "totalColumns": len(df.columns),
                "truncated": len(preview) >= safe_limit and total_rows > safe_limit,
            }

        # ── ATTEMPT 2: Load from uploaded_data.db SQLite (fallback) ──
        # Sanitize table name the same way _csv_to_sqlite does
        safe_table = "".join(c if c.isalnum() or c == '_' else '_' for c in str(table_name))
        if not safe_table or safe_table[0].isdigit():
            safe_table = 't_' + safe_table

        if os.path.exists(UPLOADED_DB_PATH):
            import aiosqlite as _asl
            try:
                async with _asl.connect(UPLOADED_DB_PATH) as sdb:
                    sdb.row_factory = _asl.Row
                    cur = await sdb.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (safe_table,)
                    )
                    if await cur.fetchone():
                        await cur.close()
                        cur2 = await sdb.execute(f'PRAGMA table_info("{safe_table}")')
                        cols = await cur2.fetchall()
                        col_defs = []
                        for col in cols:
                            col_defs.append({
                                "cid": col['cid'],
                                "name": col['name'],
                                "type": col['type'],
                                "notnull": bool(col['notnull']),
                                "defaultValue": col['dflt_value'],
                                "primaryKey": bool(col['pk']),
                            })
                        await cur2.close()

                        cur3 = await sdb.execute(f'SELECT COUNT(*) as cnt FROM "{safe_table}"')
                        total_row = await cur3.fetchone()
                        total_rows = total_row['cnt'] if total_row else 0
                        await cur3.close()

                        cur4 = await sdb.execute(f'SELECT * FROM "{safe_table}" LIMIT ?', (safe_limit,))
                        rows_raw = await cur4.fetchall()
                        result_columns = [desc[0] for desc in cur4.description] if cur4.description else [c['name'] for c in col_defs]
                        rows = [_sanitize_for_json(dict(row)) for row in rows_raw]
                        await cur4.close()

                        return {
                            "id": resolved_id,
                            "name": table_name,
                            "fullyQualifiedName": fqn,
                            "columns": col_defs,
                            "resultColumns": result_columns,
                            "rows": rows,
                            "rowCount": len(rows),
                            "totalRows": total_rows,
                            "truncated": len(rows) >= safe_limit and total_rows > safe_limit,
                        }
                    await cur.close()
            except Exception:
                pass  # Fall through to error

        return JSONResponse(status_code=404, content={"error": "No data found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/tables/{tid}")
async def get_table(tid: str):
    try:
        async with get_db() as db:
            t = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tid,))
            if not t:
                return JSONResponse(status_code=404, content={"error": "Not found"})
            t["service"] = await query_one(
                db,
                "SELECT id, name, platform FROM Service WHERE id=?",
                (t["serviceId"],),
            )
            tests = await query_all(db, "SELECT * FROM DQTest WHERE tableId=?", (tid,))
            for test in tests:
                test["results"] = await query_all(
                    db,
                    "SELECT * FROM DQTestResult WHERE testId=? ORDER BY timestamp DESC LIMIT 1",
                    (test["id"],),
                )
            t["tests"] = tests
            t["profiles"] = await query_all(
                db,
                "SELECT * FROM TableProfile WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (tid,),
            )
            return t
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/tables/{tid}")
async def delete_table(tid: str):
    try:
        async with get_db() as db:
            t = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tid,))
            if not t:
                return JSONResponse(status_code=404, content={"error": "Not found"})
            # Delete associated data
            await db.execute(
                "DELETE FROM DQTestResult WHERE testId IN (SELECT id FROM DQTest WHERE tableId=?)",
                (tid,),
            )
            await db.execute("DELETE FROM DQTest WHERE tableId=?", (tid,))
            await db.execute("DELETE FROM TableProfile WHERE tableId=?", (tid,))
            await db.execute("DELETE FROM TransformHistory WHERE tableId=?", (tid,))
            await db.execute(
                "DELETE FROM Activity WHERE entityId=? AND entityType='table'", (tid,)
            )
            await db.execute('DELETE FROM "Table" WHERE id=?', (tid,))
        # Also delete the CSV data file
        try:
            import glob

            for f in glob.glob(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", f"{tid}.*")
            ):
                os.remove(f)
        except Exception:
            pass
        return {"message": "Deleted", "id": tid, "name": t["name"]}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# QUALITY TESTS & RESULTS
# ═══════════════════════════════════════════════


@app.get("/api/quality")
async def list_quality(tableId: Optional[str] = None, status: Optional[str] = None):
    try:
        async with get_db() as db:
            where, params = [], []
            if tableId:
                where.append("tableId=?")
                params.append(tableId)
            if status:
                where.append("status=?")
                params.append(status)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db, f"SELECT * FROM DQTest {w} ORDER BY name", (*params,)
            )
            for r in rows:
                tbl = await query_one(
                    db, 'SELECT name FROM "Table" WHERE id=?', (r["tableId"],)
                )
                r["table"] = {"name": tbl["name"]} if tbl else {"name": "Unknown"}
                r["results"] = await query_all(
                    db,
                    "SELECT * FROM DQTestResult WHERE testId=? ORDER BY timestamp DESC LIMIT 1",
                    (r["id"],),
                )
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/quality/results")
async def quality_results(
    testId: Optional[str] = None, limit: Optional[int] = 100, days: Optional[int] = 14
):
    try:
        async with get_db() as db:
            cutoff = days_ago_iso(days)
            params = [cutoff]
            where = "WHERE timestamp >= ?"
            if testId:
                where += " AND testId=?"
                params.append(testId)
            rows = await query_all(
                db,
                f"SELECT * FROM DQTestResult {where} ORDER BY timestamp DESC LIMIT ?",
                (*params, limit),
            )
            for r in rows:
                test = await query_one(
                    db, "SELECT name FROM DQTest WHERE id=?", (r["testId"],)
                )
                r["test"] = {"name": test["name"]} if test else {"name": "Unknown"}
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# RULES
# ═══════════════════════════════════════════════


@app.get("/api/rules")
async def list_rules(datasetId: Optional[str] = None, enabled: Optional[str] = None):
    try:
        async with get_db() as db:
            where, params = [], []
            if datasetId:
                where.append("datasetId=?")
                params.append(datasetId)
            if enabled is not None:
                where.append("enabled=?")
                params.append(1 if enabled == "true" else 0)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db, f"SELECT * FROM QualityRule {w} ORDER BY createdAt DESC", (*params,)
            )
            for r in rows:
                ds = await query_one(
                    db, "SELECT name FROM Dataset WHERE id=?", (r["datasetId"],)
                )
                r["dataset"] = {"name": ds["name"]} if ds else None
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/rules")
async def create_rule(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        rid = gen_id()
        config = (
            json.dumps(body.get("config", {}))
            if isinstance(body.get("config"), dict)
            else body.get("config", "{}")
        )
        async with get_db() as db:
            await db.execute(
                """INSERT INTO QualityRule (id,name,description,type,dimension,severity,config,enabled,schedule,datasetId,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rid,
                    body.get("name"),
                    body.get("description"),
                    body.get("type"),
                    body.get("dimension"),
                    body.get("severity", "error"),
                    config,
                    1 if body.get("enabled", True) else 0,
                    body.get("schedule", "manual"),
                    body.get("datasetId"),
                    now,
                    now,
                ),
            )
            return {"id": rid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/rules/{rid}")
async def update_rule(rid: str, request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            for k, v in body.items():
                if k in (
                    "name",
                    "description",
                    "type",
                    "dimension",
                    "severity",
                    "enabled",
                    "schedule",
                    "datasetId",
                ):
                    val = 1 if k == "enabled" and v else v
                    await db.execute(
                        f'UPDATE QualityRule SET "{k}"=?, updatedAt=? WHERE id=?',
                        (val, now, rid),
                    )
            return {"message": "Updated", "id": rid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/rules/{rid}")
async def delete_rule(rid: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM QualityRule WHERE id=?", (rid,))
            return {"message": "Deleted", "id": rid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════


@app.get("/api/checks")
async def list_checks(
    datasetId: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = 100,
):
    try:
        async with get_db() as db:
            where, params = [], []
            if datasetId:
                # Resolve datasetId to find checks by all possible IDs
                possible_ids = set()
                possible_ids.add(datasetId)

                # Check Dataset table
                ds = await query_one(
                    db, "SELECT id, name FROM Dataset WHERE id=?", (datasetId,)
                )
                if ds:
                    possible_ids.add(ds["id"])
                    possible_ids.add(ds["name"])
                    tbl = await query_one(
                        db, 'SELECT id FROM "Table" WHERE name=? LIMIT 1', (ds["name"],)
                    )
                    if tbl:
                        possible_ids.add(tbl["id"])

                # Check Table table
                tbl = await query_one(
                    db, 'SELECT id, name FROM "Table" WHERE id=?', (datasetId,)
                )
                if tbl:
                    possible_ids.add(tbl["id"])
                    possible_ids.add(tbl["name"])
                    ds2 = await query_one(
                        db, "SELECT id FROM Dataset WHERE name=?", (tbl["name"],)
                    )
                    if ds2:
                        possible_ids.add(ds2["id"])

                # Table name as datasetId
                if datasetId and len(datasetId) < 64:
                    possible_ids.add(datasetId)

                placeholders = ",".join("?" * len(possible_ids))
                where.append(f"datasetId IN ({placeholders})")
                params.extend(possible_ids)
            if status:
                where.append("status=?")
                params.append(status)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db,
                f"SELECT * FROM QualityCheck {w} ORDER BY createdAt DESC LIMIT ?",
                (*params, min(limit, 500)),
            )
            for r in rows:
                rule = await query_one(
                    db, "SELECT name FROM QualityRule WHERE id=?", (r["ruleId"],)
                )
                r["rule"] = {"name": rule["name"]} if rule else {"name": "Unknown"}
                # Resolve dataset name from either Dataset or Table
                ds = await query_one(
                    db, "SELECT name FROM Dataset WHERE id=?", (r["datasetId"],)
                )
                if ds:
                    r["dataset"] = {"name": ds["name"]}
                else:
                    tbl = await query_one(
                        db, 'SELECT name FROM "Table" WHERE id=?', (r["datasetId"],)
                    )
                    if tbl:
                        r["dataset"] = {"name": tbl["name"]}
                    else:
                        # Maybe the datasetId IS the name
                        r["dataset"] = {
                            "name": (
                                r["datasetId"]
                                if r["datasetId"] and len(r["datasetId"]) < 64
                                else "Unknown"
                            )
                        }
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/run-check")
async def run_check(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            rule = await query_one(
                db, "SELECT * FROM QualityRule WHERE id=?", (body.get("ruleId"),)
            )
            if not rule:
                return JSONResponse(
                    status_code=404, content={"error": "Rule not found"}
                )
            dataset = await query_one(
                db, "SELECT * FROM Dataset WHERE id=?", (rule["datasetId"],)
            )

            # Try to find a table matching this dataset
            table = None
            if dataset:
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (dataset["name"],)
                )

            # Also try: if datasetId doesn't match a Dataset, try matching a Table directly
            # (this handles the case where datasetId is a Table ID or a table name from uploaded_data.db)
            if not dataset and rule["datasetId"]:
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=? LIMIT 1', (rule["datasetId"],)
                )
                if not table:
                    table = await query_one(
                        db,
                        'SELECT * FROM "Table" WHERE name=? LIMIT 1',
                        (rule["datasetId"],),
                    )

            # Try REAL execution first
            result = None
            if table:
                df = load_dataframe(table["id"])
                if df is not None:
                    # ── De-one-hot: if the DataFrame is one-hot encoded, reconstruct original columns ──
                    de_one_hot_headers = None
                    if _is_one_hot_encoded(df):
                        de_one_hot_headers = _extract_one_hot_headers(df)
                        df = _de_one_hot_dataframe(df)
                        print(
                            f"[run-check] De-one-hot encoded DataFrame: {len(de_one_hot_headers)} original columns reconstructed"
                        )

                    # ── Column resolution: if rule's column doesn't exist, try to find the right one ──
                    rule_dict = dict(rule)
                    config_raw = rule_dict.get("config", {})
                    if isinstance(config_raw, str):
                        try:
                            config_raw = json.loads(config_raw)
                        except Exception:
                            config_raw = {}
                    configured_col = config_raw.get("column", "")

                    if configured_col and configured_col not in df.columns:
                        # The rule references a column that doesn't exist — try to resolve it
                        resolved_col = _resolve_column(
                            configured_col, df.columns.tolist(), de_one_hot_headers
                        )
                        if resolved_col:
                            # Patch the rule config with the resolved column name
                            config_raw["column"] = resolved_col
                            rule_dict["config"] = (
                                json.dumps(config_raw)
                                if isinstance(rule_dict.get("config"), str)
                                else config_raw
                            )
                            print(
                                f"[run-check] Resolved column '{configured_col}' → '{resolved_col}' for rule '{rule['name']}'"
                            )
                        elif de_one_hot_headers:
                            # Column might exist in de-one-hot headers under different casing/spacing
                            # Try fuzzy match against de-one-hot header names
                            for gnum, hname in de_one_hot_headers.items():
                                if configured_col.lower().replace(" ", "").replace(
                                    "(", ""
                                ).replace(")", "") == hname.lower().replace(
                                    " ", ""
                                ).replace(
                                    "(", ""
                                ).replace(
                                    ")", ""
                                ):
                                    config_raw["column"] = hname
                                    rule_dict["config"] = (
                                        json.dumps(config_raw)
                                        if isinstance(rule_dict.get("config"), str)
                                        else config_raw
                                    )
                                    print(
                                        f"[run-check] Fuzzy-resolved column '{configured_col}' → '{hname}' for rule '{rule['name']}'"
                                    )
                                    break

                    try:
                        result = execute_rule(rule_dict, df, table.get("name", ""))
                    except Exception as e:
                        print(f"[run-check] Error executing rule: {e}")
                        result = None

            # If still no result, try loading from uploaded_data.db by dataset name
            if result is None:
                ds_name = (
                    dataset["name"]
                    if dataset
                    else (rule["datasetId"] if rule["datasetId"] else None)
                )
                if ds_name and os.path.exists(UPLOADED_DB_PATH):
                    try:
                        import sqlite3 as _sq

                        conn = _sq.connect(UPLOADED_DB_PATH)
                        # Sanitize table name
                        safe_table_name = "".join(
                            c if c.isalnum() or c == "_" else "_" for c in str(ds_name)
                        )
                        if not safe_table_name or safe_table_name[0].isdigit():
                            safe_table_name = "t_" + safe_table_name
                        # Check if table exists
                        cur = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (safe_table_name,),
                        )
                        if cur.fetchone():
                            df = pd.read_sql_query(
                                f'SELECT * FROM "{safe_table_name}"', conn
                            )
                            if len(df) > 0:
                                # De-one-hot if needed
                                de_one_hot_headers2 = None
                                if _is_one_hot_encoded(df):
                                    de_one_hot_headers2 = _extract_one_hot_headers(df)
                                    df = _de_one_hot_dataframe(df)
                                    print(
                                        f"[run-check] De-one-hot (uploaded_data.db): {len(de_one_hot_headers2)} columns reconstructed"
                                    )

                                # Column resolution for uploaded_data.db path too
                                rule_dict2 = dict(rule)
                                config_raw2 = rule_dict2.get("config", {})
                                if isinstance(config_raw2, str):
                                    try:
                                        config_raw2 = json.loads(config_raw2)
                                    except Exception:
                                        config_raw2 = {}
                                configured_col2 = config_raw2.get("column", "")
                                if (
                                    configured_col2
                                    and configured_col2 not in df.columns
                                ):
                                    resolved_col2 = _resolve_column(
                                        configured_col2,
                                        df.columns.tolist(),
                                        de_one_hot_headers2,
                                    )
                                    if resolved_col2:
                                        config_raw2["column"] = resolved_col2
                                        rule_dict2["config"] = (
                                            json.dumps(config_raw2)
                                            if isinstance(rule_dict2.get("config"), str)
                                            else config_raw2
                                        )
                                        print(
                                            f"[run-check] Resolved column '{configured_col2}' → '{resolved_col2}' (uploaded_data.db)"
                                        )
                                    elif de_one_hot_headers2:
                                        for gnum, hname in de_one_hot_headers2.items():
                                            if configured_col2.lower().replace(
                                                " ", ""
                                            ).replace("(", "").replace(
                                                ")", ""
                                            ) == hname.lower().replace(
                                                " ", ""
                                            ).replace(
                                                "(", ""
                                            ).replace(
                                                ")", ""
                                            ):
                                                config_raw2["column"] = hname
                                                rule_dict2["config"] = (
                                                    json.dumps(config_raw2)
                                                    if isinstance(
                                                        rule_dict2.get("config"), str
                                                    )
                                                    else config_raw2
                                                )
                                                print(
                                                    f"[run-check] Fuzzy-resolved column '{configured_col2}' → '{hname}' (uploaded_data.db)"
                                                )
                                                break
                                result = execute_rule(rule_dict2, df, ds_name)
                        cur.close()
                        conn.close()
                    except Exception:
                        pass  # Non-critical

            # Fallback: profile-based estimation
            if result is None and table:
                profile_row = await query_one(
                    db,
                    "SELECT * FROM TableProfile WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                    (table["id"],),
                )
                if profile_row:
                    try:
                        profile_data = (
                            json.loads(profile_row["profileData"])
                            if isinstance(profile_row["profileData"], str)
                            else profile_row["profileData"]
                        )
                        profile_data["_rowCount"] = profile_row["rowCount"]
                        result = execute_profile_check(
                            dict(rule), profile_data, table.get("name", "")
                        )
                    except Exception:
                        pass

            # Last resort: use random (legacy behavior)
            if result is None:
                import random

                passed = random.random() < 0.8
                score = round(
                    random.uniform(70, 100) if passed else random.uniform(0, 60), 1
                )
                records = random.randint(100, 50000)
                failed = 0 if passed else random.randint(1, max(1, int(records * 0.1)))
                duration = random.randint(50, 5000)
                result = CheckResult(
                    rule_id=rule["id"],
                    table_name="",
                    column_name="",
                    status="passed" if passed else "failed",
                    score=score,
                    records_checked=records,
                    records_failed=failed,
                    duration=duration,
                    failures=[],
                    message=f"Simulated check (no data available): score={score}",
                    pass_rate=score,
                    metric_value=score,
                    threshold_value=0,
                    failed_samples=[],
                )
                # Import needed

            # Store check result
            check_id = gen_id()
            await db.execute(
                """INSERT INTO QualityCheck (id,ruleId,datasetId,status,score,recordsChecked,recordsFailed,duration,failures,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    check_id,
                    rule["id"],
                    rule["datasetId"],
                    result.status,
                    result.score,
                    result.records_checked,
                    result.records_failed,
                    result.duration,
                    json.dumps(result.failures),
                    now,
                ),
            )

            # Create alert if failed
            alert_created = False
            if result.status == "failed":
                aid = gen_id()
                await db.execute(
                    """INSERT INTO Alert (id,title,message,severity,alertType,source,status,createdAt)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        aid,
                        f"Check failed: {rule['name']}",
                        result.message,
                        rule.get("severity", "error"),
                        "test_failure",
                        dataset["name"] if dataset else "Unknown",
                        "active",
                        now,
                    ),
                )
                alert_created = True

            await db.execute(
                "UPDATE QualityRule SET lastTriggered=? WHERE id=?", (now, rule["id"])
            )

            # Recalculate dataset quality score
            if dataset:
                checks = await query_all(
                    db,
                    "SELECT score FROM QualityCheck WHERE datasetId=? ORDER BY createdAt DESC LIMIT 10",
                    (rule["datasetId"],),
                )
                sc = [c["score"] for c in checks if c["score"] is not None]
                avg = round(sum(sc) / len(sc), 1) if sc else 100.0
                await db.execute(
                    "UPDATE Dataset SET qualityScore=?, lastChecked=? WHERE id=?",
                    (avg, now, rule["datasetId"]),
                )

            return {
                "check": {
                    "id": check_id,
                    "status": result.status,
                    "score": result.score,
                    "recordsChecked": result.records_checked,
                    "recordsFailed": result.records_failed,
                    "duration": result.duration,
                    "createdAt": now,
                    "message": result.message,
                },
                "ruleName": rule["name"],
                "datasetName": dataset["name"] if dataset else "Unknown",
                "alertCreated": alert_created,
                "executionMode": (
                    "real"
                    if table and load_dataframe(table["id"]) is not None
                    else (
                        "profile"
                        if result and "Profile" in getattr(result, "message", "")
                        else "simulated"
                    )
                ),
            }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# LINEAGE
# ═══════════════════════════════════════════════


@app.get("/api/lineage")
async def list_lineage():
    try:
        async with get_db() as db:
            rows = await query_all(
                db, "SELECT * FROM DataLineage ORDER BY createdAt DESC"
            )
            for r in rows:
                ft = await query_one(
                    db,
                    'SELECT name, fullyQualifiedName FROM "Table" WHERE id=?',
                    (r["fromTableId"],),
                )
                tt = await query_one(
                    db,
                    'SELECT name, fullyQualifiedName FROM "Table" WHERE id=?',
                    (r["toTableId"],),
                )
                r["fromTable"] = ft
                r["toTable"] = tt
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════


@app.get("/api/alerts")
async def list_alerts(status: Optional[str] = None, severity: Optional[str] = None):
    try:
        async with get_db() as db:
            where, params = [], []
            if status:
                where.append("status=?")
                params.append(status)
            if severity:
                where.append("severity=?")
                params.append(severity)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            return await query_all(
                db, f"SELECT * FROM Alert {w} ORDER BY createdAt DESC", (*params,)
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/alerts")
async def update_alert(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            sets, vals = [], []
            if "status" in body:
                sets.append("status=?")
                vals.append(body["status"])
            if body.get("status") == "resolved":
                sets.append("resolvedAt=?")
                vals.append(now)
            if "assignedTo" in body:
                sets.append("assignedTo=?")
                vals.append(body["assignedTo"])
            if not sets:
                return {"message": "Nothing to update"}
            vals.append(body.get("id"))
            await db.execute(f'UPDATE Alert SET {", ".join(sets)} WHERE id=?', (*vals,))
            return {"message": "Updated"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# TAGS, GLOSSARY, TEAMS, ACTIVITY, SEARCH, COMPLIANCE
# ═══════════════════════════════════════════════


@app.get("/api/tags")
async def list_tags():
    try:
        async with get_db() as db:
            return await query_all(db, "SELECT * FROM Tag ORDER BY name")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/tags")
async def create_tag(request: Request):
    try:
        body = await request.json()
        tid = gen_id()
        now = now_iso()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Tag (id,name,displayName,description,color,tagFQN,usageCount,createdAt)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    tid,
                    body.get("name"),
                    body.get("displayName"),
                    body.get("description"),
                    body.get("color", "#6366f1"),
                    body.get("tagFQN"),
                    0,
                    now,
                ),
            )
            return {"id": tid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/glossary")
async def list_glossary():
    try:
        async with get_db() as db:
            return await query_all(db, "SELECT * FROM GlossaryTerm ORDER BY name")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/glossary")
async def create_glossary(request: Request):
    try:
        body = await request.json()
        gid = gen_id()
        now = now_iso()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO GlossaryTerm (id,name,qualifiedName,description,definition,category,status,reviewers,tags,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    gid,
                    body.get("name"),
                    body.get("qualifiedName", body.get("name", "")),
                    body.get("description"),
                    body.get("definition"),
                    body.get("category"),
                    body.get("status", "draft"),
                    json.dumps(body.get("reviewers", [])),
                    json.dumps(body.get("tags", [])),
                    now,
                    now,
                ),
            )
            return {"id": gid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/teams")
async def list_teams():
    try:
        async with get_db() as db:
            return await query_all(db, "SELECT * FROM Team ORDER BY name")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/activity")
async def list_activity(entityType: Optional[str] = None, limit: Optional[int] = 50):
    try:
        async with get_db() as db:
            if entityType:
                return await query_all(
                    db,
                    "SELECT * FROM Activity WHERE entityType=? ORDER BY timestamp DESC LIMIT ?",
                    (entityType, limit),
                )
            return await query_all(
                db, "SELECT * FROM Activity ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/search")
async def search(q: str = Query("")):
    try:
        if not q.strip():
            return {"tables": [], "services": [], "glossary": []}
        p = f"%{q}%"
        async with get_db() as db:
            return {
                "tables": await query_all(
                    db,
                    'SELECT * FROM "Table" WHERE name LIKE ? OR fullyQualifiedName LIKE ? LIMIT 10',
                    (p, p),
                ),
                "services": await query_all(
                    db,
                    "SELECT * FROM Service WHERE name LIKE ? OR description LIKE ? OR platform LIKE ? LIMIT 10",
                    (p, p, p),
                ),
                "glossary": await query_all(
                    db,
                    "SELECT * FROM GlossaryTerm WHERE name LIKE ? OR description LIKE ? LIMIT 10",
                    (p, p),
                ),
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/compliance")
async def list_compliance():
    try:
        async with get_db() as db:
            rows = await query_all(
                db, "SELECT * FROM ComplianceReport ORDER BY createdAt DESC"
            )
            for r in rows:
                ds = await query_one(
                    db, "SELECT name FROM Dataset WHERE id=?", (r["datasetId"],)
                )
                r["datasetName"] = ds["name"] if ds else "Unknown"
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# DATASETS
# ═══════════════════════════════════════════════


@app.get("/api/datasets")
async def list_datasets():
    """List all datasets. Uses Table entries as the PRIMARY source (since /api/tables
    always works), then enriches with Dataset-specific metadata. Also includes tables
    from uploaded_data.db that aren't in either metadata table."""
    try:
        async with get_db() as db:
            # ── Step 1: Load all Dataset entries into a lookup by name ──
            ds_rows = await query_all(
                db, "SELECT * FROM Dataset ORDER BY qualityScore ASC"
            )
            ds_by_name = {}
            for r in ds_rows:
                try:
                    r["_count"] = {
                        "rules": await query_scalar(
                            db,
                            "SELECT COUNT(*) FROM QualityRule WHERE datasetId=?",
                            (r["id"],),
                        )
                    }
                except Exception:
                    r["_count"] = {"rules": 0}
                ds_by_name[r["name"]] = r

            # ── Step 2: Build result using Table entries as the PRIMARY source ──
            # This ensures ALL uploaded tables appear in dropdowns, even if they
            # lack a corresponding Dataset entry.
            result = []
            seen_names = set()

            table_rows = await query_all(db, 'SELECT * FROM "Table" ORDER BY name ASC')
            for t in table_rows:
                tname = t["name"]
                seen_names.add(tname)

                # If a Dataset entry exists for this table name, use it (it has richer metadata)
                if tname in ds_by_name:
                    ds = ds_by_name[tname]
                    # Ensure the Table ID is available for auto-fix propose lookups
                    ds["tableId"] = t["id"]
                    result.append(ds)
                else:
                    # No Dataset entry — create a synthetic one from the Table metadata
                    try:
                        rule_count = await query_scalar(
                            db,
                            "SELECT COUNT(*) FROM QualityRule WHERE datasetId=?",
                            (t["id"],),
                        )
                    except Exception:
                        rule_count = 0
                    result.append(
                        {
                            "id": t["id"],
                            "name": tname,
                            "description": t.get("description", ""),
                            "type": "sqlite",
                            "connectionInfo": json.dumps(
                                {"db": "uploaded_data", "table": tname}
                            ),
                            "status": "active",
                            "rowCount": t.get("rowCount", 0) or 0,
                            "columnCount": t.get("columnCount", 0) or 0,
                            "qualityScore": t.get("qualityScore", 100.0) or 100.0,
                            "lastChecked": None,
                            "createdAt": t.get("createdAt", ""),
                            "updatedAt": t.get("updatedAt", ""),
                            "_count": {"rules": rule_count},
                            "tableId": t["id"],
                        }
                    )

            # ── Step 3: Add any Dataset entries that don't have a matching Table ──
            for ds_name, ds in ds_by_name.items():
                if ds_name not in seen_names:
                    ds["tableId"] = None
                    result.append(ds)
                    seen_names.add(ds_name)

            # ── Step 4: Also include tables from uploaded_data.db if not already listed ──
            try:
                import sqlite3 as _sq

                if os.path.exists(UPLOADED_DB_PATH):
                    conn = _sq.connect(UPLOADED_DB_PATH)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY name"
                    )
                    sqlite_tables = [
                        r[0]
                        for r in cur.fetchall()
                        if r[0] not in DATAGUARD_SYSTEM_TABLES
                    ]
                    cur.close()
                    conn.close()
                    for st_name in sqlite_tables:
                        if st_name not in seen_names:
                            # Try to get row/column counts from uploaded_data.db
                            row_count = 0
                            col_count = 0
                            try:
                                c2 = _sq.connect(UPLOADED_DB_PATH)
                                cu2 = c2.cursor()
                                cu2.execute(f'SELECT COUNT(*) FROM "{st_name}"')
                                row_count = cu2.fetchone()[0]
                                cu2.execute(f'PRAGMA table_info("{st_name}")')
                                col_count = len(cu2.fetchall())
                                cu2.close()
                                c2.close()
                            except Exception:
                                pass
                            result.append(
                                {
                                    "id": st_name,
                                    "name": st_name,
                                    "description": "SQLite table from uploaded_data.db",
                                    "type": "sqlite",
                                    "connectionInfo": json.dumps(
                                        {"db": "uploaded_data", "table": st_name}
                                    ),
                                    "status": "active",
                                    "rowCount": row_count,
                                    "columnCount": col_count,
                                    "qualityScore": 100.0,
                                    "lastChecked": None,
                                    "createdAt": "",
                                    "updatedAt": "",
                                    "_count": {"rules": 0},
                                    "tableId": None,
                                }
                            )
                            seen_names.add(st_name)
            except Exception:
                pass  # Non-critical

            # Sort by name for consistent display
            result.sort(key=lambda x: x.get("name", ""))
            return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/datasets")
async def create_dataset(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        did = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Dataset (id,name,description,type,connectionInfo,status,rowCount,columnCount,qualityScore,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    did,
                    body.get("name"),
                    body.get("description"),
                    body.get("type", "postgresql"),
                    body.get("connectionInfo"),
                    body.get("status", "active"),
                    body.get("rowCount", 0),
                    body.get("columnCount", 0),
                    body.get("qualityScore", 100.0),
                    now,
                    now,
                ),
            )
            return {"id": did, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/datasets/{did}")
async def get_dataset(did: str):
    try:
        async with get_db() as db:
            d = await query_one(db, "SELECT * FROM Dataset WHERE id=?", (did,))
            if not d:
                return JSONResponse(status_code=404, content={"error": "Not found"})
            d["rules"] = await query_all(
                db,
                "SELECT * FROM QualityRule WHERE datasetId=? ORDER BY createdAt DESC",
                (did,),
            )
            return d
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/datasets/{did}")
async def update_dataset(did: str, request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            for k, v in body.items():
                if k in (
                    "name",
                    "description",
                    "type",
                    "status",
                    "connectionInfo",
                    "rowCount",
                    "columnCount",
                ):
                    await db.execute(
                        f'UPDATE Dataset SET "{k}"=?, updatedAt=? WHERE id=?',
                        (v, now, did),
                    )
            return {"message": "Updated", "id": did}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/datasets/{did}")
async def delete_dataset(did: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM Dataset WHERE id=?", (did,))
            return {"message": "Deleted", "id": did}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# NL RULE (AI-powered)
# ═══════════════════════════════════════════════


@app.post("/api/nl-rule")
async def create_nl_rule(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        dataset_id = body.get("datasetId")
        now = now_iso()

        # ── Resolve dataset_id: might be a Dataset UUID, Table UUID, or table name ──
        table = None
        dataset = None
        canonical_dataset_id = dataset_id

        async with get_db() as db:
            # Try as Dataset UUID first
            dataset = await query_one(
                db, "SELECT id, name FROM Dataset WHERE id=?", (dataset_id,)
            )
            if dataset:
                canonical_dataset_id = dataset["id"]
                table = await query_one(
                    db,
                    'SELECT id, name, columns FROM "Table" WHERE name=? LIMIT 1',
                    (dataset["name"],),
                )

            # Try as Table UUID
            if not table:
                table = await query_one(
                    db,
                    'SELECT id, name, columns FROM "Table" WHERE id=?',
                    (dataset_id,),
                )
            if table and not dataset:
                ds = await query_one(
                    db, "SELECT id, name FROM Dataset WHERE name=?", (table["name"],)
                )
                if ds:
                    dataset = ds
                    canonical_dataset_id = ds["id"]

            # Try as table name
            if not table:
                table = await query_one(
                    db,
                    'SELECT id, name, columns FROM "Table" WHERE name=? LIMIT 1',
                    (dataset_id,),
                )
            if not dataset:
                dataset = await query_one(
                    db, "SELECT id, name FROM Dataset WHERE name=?", (dataset_id,)
                )

            if not dataset and not table:
                return JSONResponse(
                    status_code=404, content={"error": "Dataset not found"}
                )

            # Determine canonical_dataset_id
            if dataset:
                canonical_dataset_id = dataset["id"]
            elif table:
                canonical_dataset_id = table["id"]

            # Resolve table name and columns for rule generation
            table_name = ""
            columns_info = ""
            if table:
                table_name = table["name"]
                columns_info = table.get("columns", "")
            elif dataset:
                t = await query_one(
                    db,
                    'SELECT columns FROM "Table" WHERE name=? LIMIT 1',
                    (dataset["name"],),
                )
                if t:
                    columns_info = t["columns"]
                    table_name = dataset["name"]

        # ── Enrich columns_info with actual DataFrame columns if available ──
        # The stored columns may have "Unnamed: X" from pandas; the real CSV may have different names
        if table:
            df = load_dataframe(table["id"])
            if df is not None:
                if _is_one_hot_encoded(df):
                    # One-hot encoded DataFrame — extract just the real header names
                    headers = _extract_one_hot_headers(df)
                    enriched_cols = []
                    for group_num in sorted(headers.keys(), key=lambda x: int(x)):
                        header_name = headers[group_num]
                        # Infer type from the de-one-hot reconstructed column
                        de_one_hot_df = _de_one_hot_dataframe(df)
                        col_type = "string"
                        if header_name in de_one_hot_df.columns:
                            dtype_str = str(de_one_hot_df[header_name].dtype)
                            if "int" in dtype_str:
                                col_type = "integer"
                            elif "float" in dtype_str:
                                col_type = "float"
                            elif "datetime" in dtype_str:
                                col_type = "datetime"
                            elif "bool" in dtype_str:
                                col_type = "boolean"
                        enriched_cols.append(
                            {
                                "name": header_name,
                                "type": col_type,
                                "nullable": (
                                    bool(de_one_hot_df[header_name].isna().any())
                                    if header_name in de_one_hot_df.columns
                                    else False
                                ),
                                "note": "reconstructed from one-hot encoded data",
                            }
                        )
                    columns_info = json.dumps(enriched_cols)
                    print(
                        f"[nl-rule] Detected one-hot encoded DataFrame → extracted {len(enriched_cols)} original headers: {[c['name'] for c in enriched_cols]}"
                    )
                else:
                    # Normal DataFrame — use real column names, but skip Unnamed: N columns
                    real_cols = df.columns.tolist()
                    try:
                        stored_cols = json.loads(columns_info) if columns_info else []
                    except Exception:
                        stored_cols = []

                    stored_by_name = {}
                    for c in stored_cols:
                        if isinstance(c, dict) and c.get("name"):
                            stored_by_name[c["name"]] = c

                    enriched_cols = []
                    for col_name in real_cols:
                        # Skip standalone Unnamed: N columns (no header suffix)
                        if re.match(r"^Unnamed:\s*\d+$", col_name.strip()):
                            continue
                        # Skip one-hot encoded column names (shouldn't be here if _is_one_hot_encoded was False, but just in case)
                        if re.match(r"^Unnamed:\s*\d+_", col_name.strip()):
                            continue
                        if col_name in stored_by_name:
                            enriched_cols.append(stored_by_name[col_name])
                        else:
                            dtype_str = str(df[col_name].dtype)
                            if "int" in dtype_str:
                                col_type = "integer"
                            elif "float" in dtype_str:
                                col_type = "float"
                            elif "datetime" in dtype_str:
                                col_type = "datetime"
                            elif "bool" in dtype_str:
                                col_type = "boolean"
                            else:
                                col_type = "string"
                            enriched_cols.append(
                                {
                                    "name": col_name,
                                    "type": col_type,
                                    "nullable": bool(df[col_name].isna().any()),
                                }
                            )

                    columns_info = json.dumps(enriched_cols)
                    print(
                        f"[nl-rule] Enriched columns from DataFrame: {[c.get('name','') for c in enriched_cols[:20]]}{'...' if len(enriched_cols) > 20 else ''}"
                    )

                # ── Cap columns_info to prevent LLM 413 errors ──
                # If still too many columns, keep only the first 30
                try:
                    cols_list = (
                        json.loads(columns_info)
                        if isinstance(columns_info, str)
                        else columns_info
                    )
                    if isinstance(cols_list, list) and len(cols_list) > 30:
                        print(
                            f"[nl-rule] Capping columns from {len(cols_list)} to 30 for LLM"
                        )
                        cols_list = cols_list[:30]
                        columns_info = json.dumps(cols_list)
                except Exception:
                    pass

        # Use real LLM generator (falls back to keywords if no API key)
        from llm.rule_generator import generate as generate_rule

        rule_data = generate_rule(
            prompt, canonical_dataset_id, table_name, columns_info
        )

        rid = gen_id()
        config_json = (
            json.dumps(rule_data.get("config", {}))
            if isinstance(rule_data.get("config"), dict)
            else rule_data.get("config", "{}")
        )
        async with get_db() as db:
            await db.execute(
                """INSERT INTO QualityRule (id,name,description,type,dimension,severity,config,enabled,schedule,datasetId,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rid,
                    rule_data.get("name", f"Rule: {prompt[:60]}"),
                    rule_data.get("description", ""),
                    rule_data.get("type", "validity"),
                    rule_data.get("dimension", "validity"),
                    rule_data.get("severity", "warning"),
                    config_json,
                    1,
                    "manual",
                    canonical_dataset_id,
                    now,
                    now,
                ),
            )

        rule_data["id"] = rid
        return rule_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# INGEST (File Upload with Pandas)
# ═══════════════════════════════════════════════


def detect_col_type(series):
    non_null = series.dropna()
    if len(non_null) == 0:
        return "string"
    s_lower = non_null.astype(str).str.lower().str.strip()
    bool_set = {"true", "false", "yes", "no", "0", "1", "t", "f", "y", "n"}
    if all(v in bool_set for v in s_lower):
        return "boolean"
    try:
        num = pd.to_numeric(non_null, errors="coerce").dropna()
        if len(num) == len(non_null):
            return "integer" if all(float(v) == int(v) for v in num) else "float"
    except:
        pass
    try:
        dt = pd.to_datetime(non_null, errors="coerce", format="mixed")
        if dt.dropna().shape[0] > len(non_null) * 0.8:
            return "datetime"
    except:
        pass
    return "string"


def profile_col(series, col_type):
    total = len(series)
    null_count = int(series.isna().sum())
    null_pct = round((null_count / total) * 100, 2) if total > 0 else 0
    non_null = series.dropna()
    p = {
        "nullCount": null_count,
        "nullPercent": null_pct,
        "uniqueCount": int(non_null.nunique()),
        "distinctCount": int(non_null.value_counts().eq(1).sum()),
    }
    if col_type in ("integer", "float"):
        num = pd.to_numeric(non_null, errors="coerce").dropna()
        if len(num) > 0:
            p.update(
                {
                    "min": float(num.min()),
                    "max": float(num.max()),
                    "mean": round(float(num.mean()), 2),
                    "median": round(float(num.median()), 2),
                    "stddev": round(float(num.std()), 2) if len(num) > 1 else 0,
                }
            )
    if col_type == "string":
        lens = non_null.astype(str).str.len()
        if len(lens) > 0:
            p.update({"minLength": int(lens.min()), "maxLength": int(lens.max())})
    return p


# ═══════════════════════════════════════════════════════════════
# CSV/Excel → SQLite Auto-Conversion
# When a user uploads a CSV/Excel file, we automatically create
# a SQLite table so the data becomes queryable from SQL Playground.
# ═══════════════════════════════════════════════════════════════

UPLOADED_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "uploaded_data.db")
)
UPLOADED_DB_NAME = "uploaded_data"


def _csv_to_sqlite(table_name: str, df: pd.DataFrame, columns_def: list) -> dict:
    """Convert a DataFrame into a SQLite table in the uploaded_data.db database.

    - Sanitizes table/column names for SQLite compatibility
    - Maps pandas dtypes to SQLite types
    - Creates the table (DROP IF EXISTS to handle re-uploads)
    - Inserts all rows in batches
    - Returns info about the created table
    """
    import sqlite3 as _sq

    db_dir = os.path.dirname(UPLOADED_DB_PATH)
    os.makedirs(db_dir, exist_ok=True)

    # Sanitize table name: only alphanumeric + underscore
    safe_table = "".join(c if c.isalnum() or c == "_" else "_" for c in str(table_name))
    if not safe_table or safe_table[0].isdigit():
        safe_table = "t_" + safe_table

    # Build column definitions for CREATE TABLE
    # Map detected column types to SQLite types
    type_map = {
        "integer": "INTEGER",
        "float": "REAL",
        "boolean": "INTEGER",  # SQLite has no BOOLEAN
        "datetime": "TEXT",  # SQLite has no DATETIME
        "string": "TEXT",
    }

    col_names = list(df.columns.astype(str))
    col_type_map = {}
    for col_def in columns_def:
        col_type_map[col_def["name"]] = type_map.get(col_def["type"], "TEXT")

    # Sanitize column names for SQLite
    safe_cols = []
    for cn in col_names:
        sc = "".join(c if c.isalnum() or c == "_" else "_" for c in str(cn))
        if not sc or sc[0].isdigit():
            sc = "col_" + sc
        safe_cols.append(sc)

    # Build CREATE TABLE statement
    col_defs_sql = []
    for i, (orig_name, safe_name) in enumerate(zip(col_names, safe_cols)):
        sqlite_type = col_type_map.get(orig_name, "TEXT")
        col_defs_sql.append(f'"{safe_name}" {sqlite_type}')

    create_sql = (
        f'CREATE TABLE IF NOT EXISTS "{safe_table}" ({", ".join(col_defs_sql)})'
    )

    # Connect to uploaded_data.db and insert data
    conn = _sq.connect(UPLOADED_DB_PATH)
    try:
        # Drop existing table if it was previously created by an upload with the same name
        conn.execute(f'DROP TABLE IF EXISTS "{safe_table}"')
        conn.execute(create_sql)

        # Prepare data rows — replace NaN/None with SQL NULL
        placeholders = ", ".join(["?"] * len(safe_cols))
        cols_sql = ", ".join(f'"{sc}"' for sc in safe_cols)
        insert_sql = f'INSERT INTO "{safe_table}" ({cols_sql}) VALUES ({placeholders})'

        rows_to_insert = []
        for _, row in df.iterrows():
            vals = []
            for val in row:
                if pd.isna(val):
                    vals.append(None)
                elif isinstance(val, bool):
                    vals.append(1 if val else 0)
                elif isinstance(val, (np.bool_,)):
                    vals.append(1 if val else 0)
                elif isinstance(val, (np.integer,)):
                    vals.append(int(val))
                elif isinstance(val, (np.floating,)):
                    vals.append(float(val))
                elif isinstance(val, (int, float)):
                    vals.append(val)
                else:
                    vals.append(str(val) if not isinstance(val, str) else val)
            rows_to_insert.append(tuple(vals))

        # Insert in batches of 1000 for performance
        batch_size = 1000
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i : i + batch_size]
            conn.executemany(insert_sql, batch)

        conn.commit()

        return {
            "database": UPLOADED_DB_NAME,
            "table": safe_table,
            "rowsInserted": len(rows_to_insert),
            "columnsCreated": len(safe_cols),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.post("/api/ingest")
async def ingest_file(
    file: UploadFile = File(None),
    fileName: Optional[str] = Form(None),
    tableName: Optional[str] = Form(None),
    serviceName: Optional[str] = Form(None),
    chunkIndex: Optional[int] = Form(None),
    totalChunks: Optional[int] = Form(None),
    fileId: Optional[str] = Form(None),
):
    try:
        if not file:
            return JSONResponse(
                status_code=400, content={"success": False, "error": "No file provided"}
            )
        content = await file.read()
        file_name = fileName or file.filename or "upload.csv"
        if len(content) > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": f"File too large: {len(content)/1024/1024:.1f}MB",
                },
            )
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in ("csv", "json", "xlsx", "xls"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Unsupported: .{ext}"},
            )

        # Chunked upload
        if chunkIndex is not None and totalChunks is not None and fileId:
            os.makedirs(CHUNKS_DIR, exist_ok=True)
            with open(
                os.path.join(CHUNKS_DIR, f"{fileId}_chunk_{chunkIndex}"), "wb"
            ) as f:
                f.write(content)
            if chunkIndex < totalChunks - 1:
                return {
                    "success": True,
                    "chunk": {
                        "chunkIndex": chunkIndex,
                        "totalChunks": totalChunks,
                        "status": "received",
                    },
                }
            assembled = b""
            for i in range(totalChunks):
                cp = os.path.join(CHUNKS_DIR, f"{fileId}_chunk_{i}")
                if not os.path.exists(cp):
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "error": f"Missing chunk {i}"},
                    )
                with open(cp, "rb") as f:
                    assembled += f.read()
                os.remove(cp)
            content = assembled

        # Parse with pandas
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        elif ext == "json":
            df = pd.read_json(io.BytesIO(content))
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return JSONResponse(
                status_code=400, content={"success": False, "error": "Unsupported"}
            )

        if len(df.columns) > MAX_COLUMNS:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Too many columns: {len(df.columns)}",
                },
            )
        # Save DataFrame for real quality checks
        os.makedirs(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            ),
            exist_ok=True,
        )

        columns_def = []
        profile_data = {}
        for col in df.columns:
            ct = detect_col_type(df[col])
            columns_def.append(
                {
                    "name": str(col),
                    "type": ct,
                    "nullable": bool(df[col].isna().any()),
                    "description": "",
                    "tags": [],
                }
            )
            profile_data[str(col)] = profile_col(df[col], ct)

        base_name = tableName or (
            file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        )
        svc_name = serviceName or "File Uploads"
        now = now_iso()

        async with get_db() as db:
            existing = await query_one(
                db,
                "SELECT id FROM Service WHERE name=? AND serviceType='storage' AND platform='file_upload'",
                (svc_name,),
            )
            if existing:
                svc_id = existing["id"]
                await db.execute(
                    "UPDATE Service SET lastIngested=? WHERE id=?", (now, svc_id)
                )
            else:
                svc_id = gen_id()
                await db.execute(
                    """INSERT INTO Service (id,name,description,serviceType,platform,status,ingestionDate,lastIngested,createdAt,updatedAt)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        svc_id,
                        svc_name,
                        "File upload storage service",
                        "storage",
                        "file_upload",
                        "active",
                        now,
                        now,
                        now,
                        now,
                    ),
                )

            tbl_id = gen_id()
            await db.execute(
                """INSERT INTO "Table" (id,name,fullyQualifiedName,description,serviceId,columns,columnCount,rowCount,qualityScore,freshnessStatus,lastProfiled,tier,tags,owners,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tbl_id,
                    base_name,
                    f"file_uploads.{base_name}",
                    f"Ingested from {file_name}",
                    svc_id,
                    json.dumps(columns_def),
                    len(columns_def),
                    len(df),
                    100.0,
                    "fresh",
                    now,
                    2,
                    "[]",
                    "[]",
                    now,
                    now,
                ),
            )

            # ── Also create a Dataset entry so it appears in Quality Checks / Rules / Auto-Fix dropdowns ──
            ds_id = gen_id()
            await db.execute(
                """INSERT OR IGNORE INTO Dataset (id,name,description,type,connectionInfo,status,rowCount,columnCount,qualityScore,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ds_id,
                    base_name,
                    f"Ingested from {file_name}",
                    "sqlite",
                    json.dumps({"db": "uploaded_data", "table": base_name}),
                    "active",
                    len(df),
                    len(columns_def),
                    100.0,
                    now,
                    now,
                ),
            )

            # Save data file for real check execution
            try:
                save_dataframe(tbl_id, df, "csv")
            except Exception:
                pass  # Non-critical — checks will use profile fallback

            # ═══════════════════════════════════════════════════
            # AUTO-CONVERT: Insert uploaded data into SQLite
            # so it becomes queryable from SQL Playground
            # ═══════════════════════════════════════════════════
            sqlite_info = None
            try:
                sqlite_info = _csv_to_sqlite(base_name, df, columns_def)
            except Exception as sqlite_err:
                import traceback as _tb

                _tb.print_exc()
                # Non-critical — data is still saved as CSV

            prof_id = gen_id()
            await db.execute(
                "INSERT INTO TableProfile (id,tableId,profileData,rowCount,duration,createdAt) VALUES (?,?,?,?,?,?)",
                (prof_id, tbl_id, json.dumps(profile_data), len(df), 0, now),
            )

            await db.execute(
                """INSERT INTO Activity (id,entityType,entityId,entityName,action,description,tags,timestamp)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    gen_id(),
                    "table",
                    tbl_id,
                    f"file_uploads.{base_name}",
                    "ingested",
                    f'Ingested "{base_name}" from {file_name} ({len(df)} rows, {len(columns_def)} cols)',
                    json.dumps(["file-upload", ext]),
                    now,
                ),
            )

        return {
            "success": True,
            "message": f'File "{file_name}" ingested successfully.',
            "service": {"id": svc_id, "name": svc_name},
            "table": {
                "id": tbl_id,
                "name": base_name,
                "fullyQualifiedName": f"file_uploads.{base_name}",
                "columnCount": len(columns_def),
                "rowCount": len(df),
                "qualityScore": 100.0,
                "freshnessStatus": "fresh",
            },
            "columns": columns_def,
            "profile": {
                "id": prof_id,
                "rowCount": len(df),
                "duration": 0,
                "columnStats": profile_data,
            },
            "sqliteConversion": sqlite_info,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


# ═══════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════


@app.post("/api/profile")
async def profile_table(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})
        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data file found for table"}
            )
        from profiling.profiler import DataProfiler

        prof = DataProfiler()
        result = prof.profile(df)
        now = now_iso()
        async with get_db() as db:
            await db.execute(
                "INSERT INTO TableProfile (id,tableId,profileData,rowCount,duration,createdAt) VALUES (?,?,?,?,?,?)",
                (
                    gen_id(),
                    table_id,
                    safe_json_dumps(result),
                    len(df),
                    result.get("_duration", 0),
                    now,
                ),
            )
            await db.execute(
                'UPDATE "Table" SET lastProfiled=? WHERE id=?', (now, table_id)
            )
        return {"success": True, "profile": result, "rowCount": len(df)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# AI ENDPOINTS
# ═══════════════════════════════════════════════


@app.post("/api/ai/generate-rule")
async def ai_generate_rule(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        dataset_id = body.get("datasetId")
        from llm.rule_generator import RuleGenerator

        gen = RuleGenerator()
        rule = gen.generate(prompt, dataset_id)
        return {"success": True, "rule": rule}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ai/generate-report")
async def ai_generate_report(request: Request):
    try:
        body = await request.json()
        dataset_id = body.get("datasetId")
        async with get_db() as db:
            # ── Resolve dataset_id to find matching QualityChecks ──
            # The datasetId might be a Dataset UUID, a Table UUID, or a table name
            # We need to find checks by all possible IDs that could have been stored

            # Collect all possible dataset IDs that match this selection
            possible_dataset_ids = set()
            possible_dataset_ids.add(dataset_id)

            # Check if it's a Table UUID — if so, also look up the corresponding Dataset UUID
            tbl = await query_one(
                db, 'SELECT name FROM "Table" WHERE id=?', (dataset_id,)
            )
            if tbl:
                tname = tbl["name"]
                # Find Dataset entries with the same name
                ds = await query_one(
                    db, "SELECT id FROM Dataset WHERE name=?", (tname,)
                )
                if ds:
                    possible_dataset_ids.add(ds["id"])
                # The table name itself might be stored as datasetId
                possible_dataset_ids.add(tname)

            # Check if it's a Dataset UUID — if so, also look up the corresponding Table UUID
            ds = await query_one(
                db, "SELECT id, name FROM Dataset WHERE id=?", (dataset_id,)
            )
            if ds:
                # Find Table entries with the same name
                tbl2 = await query_one(
                    db, 'SELECT id FROM "Table" WHERE name=? LIMIT 1', (ds["name"],)
                )
                if tbl2:
                    possible_dataset_ids.add(tbl2["id"])
                possible_dataset_ids.add(ds["name"])

            # Also try direct name lookup (datasetId might be a table name string)
            if dataset_id and len(dataset_id) < 64:  # Likely a name, not a UUID
                possible_dataset_ids.add(dataset_id)

            # Build query with multiple possible datasetIds
            placeholders = ",".join("?" * len(possible_dataset_ids))
            checks = await query_all(
                db,
                f"SELECT * FROM QualityCheck WHERE datasetId IN ({placeholders}) ORDER BY createdAt DESC LIMIT 50",
                tuple(possible_dataset_ids),
            )

            # Get dataset info for the report
            ds_info = await query_one(
                db, "SELECT * FROM Dataset WHERE id=?", (dataset_id,)
            )
            if not ds_info:
                # Try by name
                ds_info = await query_one(
                    db, "SELECT * FROM Dataset WHERE name=?", (dataset_id,)
                )
            if not ds_info:
                # Try looking for Table with this ID and create a synthetic dataset
                tbl_info = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (dataset_id,)
                )
                if tbl_info:
                    ds_info = {
                        "id": tbl_info["id"],
                        "name": tbl_info["name"],
                        "description": tbl_info.get("description", ""),
                        "type": "sqlite",
                        "status": "active",
                        "rowCount": tbl_info.get("rowCount", 0),
                        "columnCount": tbl_info.get("columnCount", 0),
                        "qualityScore": tbl_info.get("qualityScore", 100.0),
                    }
                else:
                    ds_info = {"name": dataset_id}

        from llm.report_generator import ReportGenerator

        gen = ReportGenerator()
        report = gen.generate(ds_info or {}, checks)
        return {"success": True, "report": report}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ai/generate-fix")
async def ai_generate_fix(request: Request):
    try:
        body = await request.json()
        rule_name = body.get("ruleName", "")
        check_result = body.get("checkResult", {})
        from llm.fix_generator import FixGenerator

        gen = FixGenerator()
        fix = gen.generate(rule_name, check_result)
        return {"success": True, "fix": fix}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/run-rules")
async def run_all_rules(request: Request):
    try:
        body = await request.json()
        dataset_id = body.get("datasetId")
        now = now_iso()
        results = []
        async with get_db() as db:
            # ── Resolve dataset_id: it might be a Dataset UUID, Table UUID, or table name ──
            # Collect all possible IDs to search for rules
            possible_rule_dataset_ids = set()
            possible_rule_dataset_ids.add(dataset_id)

            # Find the table (by UUID or by name)
            table = None
            dataset = None

            # Try as Dataset UUID first
            dataset = await query_one(
                db, "SELECT * FROM Dataset WHERE id=?", (dataset_id,)
            )
            if dataset:
                possible_rule_dataset_ids.add(dataset["id"])
                possible_rule_dataset_ids.add(dataset["name"])
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (dataset["name"],)
                )
                if table:
                    possible_rule_dataset_ids.add(table["id"])

            # Try as Table UUID
            if not table:
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (dataset_id,)
                )
            if table:
                possible_rule_dataset_ids.add(table["id"])
                possible_rule_dataset_ids.add(table["name"])
                ds = await query_one(
                    db, "SELECT id FROM Dataset WHERE name=?", (table["name"],)
                )
                if ds:
                    dataset = ds
                    possible_rule_dataset_ids.add(ds["id"])

            # Try as table name
            if not table:
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (dataset_id,)
                )
            if not dataset:
                dataset = await query_one(
                    db, "SELECT * FROM Dataset WHERE name=?", (dataset_id,)
                )

            # Fetch rules using all possible dataset IDs
            placeholders = ",".join("?" * len(possible_rule_dataset_ids))
            rules = await query_all(
                db,
                f"SELECT * FROM QualityRule WHERE datasetId IN ({placeholders}) AND enabled=1",
                tuple(possible_rule_dataset_ids),
            )

            # Determine the canonical dataset_id for storing check results
            # Use the Dataset UUID if available, otherwise use the Table UUID, or the original dataset_id
            canonical_dataset_id = dataset_id
            if dataset:
                canonical_dataset_id = dataset["id"]
            elif table:
                canonical_dataset_id = table["id"]

            for rule in rules:
                result = None
                if table:
                    df = load_dataframe(table["id"])
                    if df is not None:
                        # ── De-one-hot: if DataFrame is one-hot encoded, reconstruct original columns ──
                        de_one_hot_headers = None
                        if _is_one_hot_encoded(df):
                            de_one_hot_headers = _extract_one_hot_headers(df)
                            df = _de_one_hot_dataframe(df)

                        # ── Column resolution ──
                        rule_dict = dict(rule)
                        config_raw = rule_dict.get("config", {})
                        if isinstance(config_raw, str):
                            try:
                                config_raw = json.loads(config_raw)
                            except Exception:
                                config_raw = {}
                        configured_col = config_raw.get("column", "")

                        if configured_col and configured_col not in df.columns:
                            resolved_col = _resolve_column(
                                configured_col, df.columns.tolist(), de_one_hot_headers
                            )
                            if resolved_col:
                                config_raw["column"] = resolved_col
                                rule_dict["config"] = (
                                    json.dumps(config_raw)
                                    if isinstance(rule_dict.get("config"), str)
                                    else config_raw
                                )
                            elif de_one_hot_headers:
                                for gnum, hname in de_one_hot_headers.items():
                                    if configured_col.lower().replace(" ", "").replace(
                                        "(", ""
                                    ).replace(")", "") == hname.lower().replace(
                                        " ", ""
                                    ).replace(
                                        "(", ""
                                    ).replace(
                                        ")", ""
                                    ):
                                        config_raw["column"] = hname
                                        rule_dict["config"] = (
                                            json.dumps(config_raw)
                                            if isinstance(rule_dict.get("config"), str)
                                            else config_raw
                                        )
                                        break

                        try:
                            result = execute_rule(rule_dict, df, table.get("name", ""))
                        except Exception:
                            pass
                if result is None and table:
                    profile_row = await query_one(
                        db,
                        "SELECT * FROM TableProfile WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                        (table["id"],),
                    )
                    if profile_row:
                        try:
                            pd2 = (
                                json.loads(profile_row["profileData"])
                                if isinstance(profile_row["profileData"], str)
                                else profile_row["profileData"]
                            )
                            pd2["_rowCount"] = profile_row["rowCount"]
                            result = execute_profile_check(
                                dict(rule), pd2, table.get("name", "")
                            )
                        except Exception:
                            pass
                if result:
                    check_id = gen_id()
                    await db.execute(
                        "INSERT INTO QualityCheck (id,ruleId,datasetId,status,score,recordsChecked,recordsFailed,duration,failures,createdAt) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            check_id,
                            rule["id"],
                            canonical_dataset_id,
                            result.status,
                            result.score,
                            result.records_checked,
                            result.records_failed,
                            result.duration,
                            json.dumps(result.failures),
                            now,
                        ),
                    )
                    if result.status == "failed":
                        await db.execute(
                            "INSERT INTO Alert (id,title,message,severity,alertType,source,status,createdAt) VALUES (?,?,?,?,?,?,?,?)",
                            (
                                gen_id(),
                                f"Check failed: {rule['name']}",
                                result.message,
                                rule.get("severity", "error"),
                                "test_failure",
                                (
                                    dataset["name"]
                                    if dataset
                                    else (table["name"] if table else "Unknown")
                                ),
                                "active",
                                now,
                            ),
                        )
                    results.append(
                        {
                            "rule": rule["name"],
                            "status": result.status,
                            "score": result.score,
                        }
                    )
            # Update lastTriggered for all matching rules
            for rule in rules:
                await db.execute(
                    "UPDATE QualityRule SET lastTriggered=? WHERE id=?",
                    (now, rule["id"]),
                )
        return {
            "success": True,
            "results": results,
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "passed"),
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# TRANSFORMATION PIPELINE BUILDER (P0)
# ═══════════════════════════════════════════════


@app.get("/api/transforms/list")
async def list_transforms():
    try:
        from transformations import list_transformers

        return list_transformers()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/transforms/execute")
async def execute_transform(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        transform_type = body.get("transformType")
        config = body.get("config", {})
        save_copy = body.get("saveCopy", False)
        if not table_id or not transform_type:
            return JSONResponse(
                status_code=400, content={"error": "tableId and transformType required"}
            )

        # Resolve table name to UUID if needed
        resolved_id = table_id
        try:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (table_id,)
                )
                if not tbl:
                    # Try by name
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (table_id,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
        except Exception:
            pass

        from transformations import get_transformer
        from transformations.history import TransformHistory

        df = load_dataframe(resolved_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        history = TransformHistory(resolved_id)
        snapshot_id = history.save_snapshot(
            df, transform_type, config, {"source": "api_execute"}
        )

        transformer = get_transformer(transform_type)
        result = transformer.transform(df, config)

        new_table_id = None
        new_table_name = None
        save_copy_error = None

        if result.success:
            if save_copy:
                # Create a _fixed copy — do NOT overwrite original
                try:
                    async with get_db() as db:
                        orig = await query_one(
                            db, 'SELECT * FROM "Table" WHERE id=?', (resolved_id,)
                        )
                        base_name = (orig["name"] if orig else table_id) or table_id
                        # Strip any existing _fixed suffix to avoid chains
                        base_name = re.sub(r"_fixed(_v\d+)?$", "", base_name)

                        # Find existing _fixed versions to determine next version
                        existing_fixed = await query_all(
                            db,
                            'SELECT name FROM "Table" WHERE name LIKE ?',
                            (f"{base_name}_fixed%",),
                        )
                        existing_names = [r["name"] for r in existing_fixed]

                        if f"{base_name}_fixed" not in existing_names:
                            fixed_name = f"{base_name}_fixed"
                        else:
                            v = 2
                            while f"{base_name}_fixed_v{v}" in existing_names:
                                v += 1
                            fixed_name = f"{base_name}_fixed_v{v}"

                        new_table_id = gen_id()
                        new_table_name = fixed_name
                        now = now_iso()

                        # Build columns definition for the fixed table
                        columns_def = []
                        for col in result.df.columns:
                            ct = "string"
                            if pd.api.types.is_numeric_dtype(result.df[col]):
                                ct = "number"
                            elif pd.api.types.is_datetime64_any_dtype(result.df[col]):
                                ct = "datetime"
                            columns_def.append({"name": str(col), "type": ct})

                        svc_id = orig["serviceId"] if orig else None

                        await db.execute(
                            """INSERT INTO "Table" (id,name,fullyQualifiedName,description,serviceId,columns,columnCount,rowCount,qualityScore,freshnessStatus,lastProfiled,tier,tags,owners,createdAt,updatedAt)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                new_table_id,
                                fixed_name,
                                f"file_uploads.{fixed_name}",
                                f"Auto-fixed copy of {base_name} ({transform_type})",
                                svc_id,
                                json.dumps(columns_def),
                                len(columns_def),
                                len(result.df),
                                100.0,
                                "fresh",
                                now,
                                2,
                                "[]",
                                "[]",
                                now,
                                now,
                            ),
                        )

                        # Save the fixed DataFrame to CSV
                        save_dataframe(new_table_id, result.df, "csv")

                        print(
                            f"[FIX] Created fixed copy: {fixed_name} (id={new_table_id}) from {base_name}"
                        )

                        # Record activity
                        await db.execute(
                            """INSERT INTO Activity (id,entityType,entityId,entityName,action,description,tags,timestamp)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (
                                gen_id(),
                                "table",
                                new_table_id,
                                fixed_name,
                                "auto_fix",
                                f"Created fixed copy from {base_name}: {transform_type}",
                                json.dumps([transform_type]),
                                now,
                            ),
                        )

                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    save_copy_error = str(e)
                    new_table_id = None
                    new_table_name = None
                    print(f"[FIX] Failed to create fixed copy: {e}")
            else:
                # Overwrite original when saveCopy is false
                save_dataframe(resolved_id, result.df, "csv")

        now = now_iso()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO TransformHistory (id,tableId,snapshotId,transformType,config,resultSummary,rowsAffected,columnsAffected,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    gen_id(),
                    resolved_id,
                    snapshot_id,
                    transform_type,
                    json.dumps(config),
                    json.dumps({"success": result.success, "message": result.message}),
                    result.rows_affected,
                    json.dumps(result.columns_affected),
                    now,
                ),
            )

        response = {
            "success": result.success,
            "message": result.message,
            "duration_ms": result.duration_ms,
            "rows_affected": result.rows_affected,
            "columns_affected": result.columns_affected,
            "details": result.details,
            "snapshot_id": snapshot_id,
        }
        if new_table_id:
            response["newTableId"] = new_table_id
            response["newTableName"] = new_table_name
        if save_copy_error:
            response["saveCopyError"] = save_copy_error
        if save_copy and not new_table_id and result.success:
            response["message"] += f" (WARNING: saveCopy failed — {save_copy_error})"
        return response
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/transforms/execute-batch")
async def execute_transform_batch(request: Request):
    """Execute multiple transforms in sequence on a single DataFrame, creating ONE _fixed copy.
    This is used by Auto-Fix All to avoid creating multiple partial _fixed files.
    Request body: { tableId, transforms: [{transformType, config}, ...], saveCopy: true }
    """
    try:
        body = await request.json()
        table_id = body.get("tableId")
        transforms = body.get("transforms", [])
        save_copy = body.get("saveCopy", True)

        if not table_id or not transforms:
            return JSONResponse(
                status_code=400, content={"error": "tableId and transforms[] required"}
            )

        # Resolve table name to UUID if needed
        resolved_id = table_id
        try:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (table_id,)
                )
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (table_id,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
        except Exception:
            pass

        from transformations import get_transformer
        from transformations.history import TransformHistory

        df = load_dataframe(resolved_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        history = TransformHistory(resolved_id)
        current_df = df.copy()
        total_rows_affected = 0
        total_duration = 0
        step_results = []
        all_success = True
        columns_affected_list = []

        for i, tdef in enumerate(transforms):
            transform_type = tdef.get("transformType")
            config = tdef.get("config", {})
            if not transform_type:
                continue

            snapshot_id = history.save_snapshot(
                current_df,
                transform_type,
                config,
                {"source": "batch_execute", "step": i},
            )

            try:
                transformer = get_transformer(transform_type)
                result = transformer.transform(current_df, config)

                step_info = {
                    "transformType": transform_type,
                    "success": result.success,
                    "message": result.message,
                    "rows_affected": result.rows_affected,
                    "duration_ms": result.duration_ms,
                }
                step_results.append(step_info)

                if result.success:
                    current_df = result.df
                    total_rows_affected += result.rows_affected
                    if result.columns_affected:
                        columns_affected_list.extend(
                            result.columns_affected
                            if isinstance(result.columns_affected, list)
                            else [result.columns_affected]
                        )
                else:
                    all_success = False

                total_duration += result.duration_ms

                # Record transform history for each step
                now_h = now_iso()
                async with get_db() as db:
                    await db.execute(
                        """INSERT INTO TransformHistory (id,tableId,snapshotId,transformType,config,resultSummary,rowsAffected,columnsAffected,createdAt)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            gen_id(),
                            resolved_id,
                            snapshot_id,
                            transform_type,
                            json.dumps(config),
                            json.dumps(
                                {"success": result.success, "message": result.message}
                            ),
                            result.rows_affected,
                            json.dumps(result.columns_affected),
                            now_h,
                        ),
                    )

            except Exception as e:
                step_results.append(
                    {
                        "transformType": transform_type,
                        "success": False,
                        "message": str(e),
                        "rows_affected": 0,
                    }
                )
                all_success = False
                break

        # Now create ONE _fixed copy with the final DataFrame
        new_table_id = None
        new_table_name = None
        save_copy_error = None

        if save_copy and all_success:
            try:
                async with get_db() as db:
                    orig = await query_one(
                        db, 'SELECT * FROM "Table" WHERE id=?', (resolved_id,)
                    )
                    base_name = (orig["name"] if orig else table_id) or table_id
                    # Strip any existing _fixed suffix
                    base_name = re.sub(r"_fixed(_v\d+)?$", "", base_name)

                    # Find existing _fixed versions
                    existing_fixed = await query_all(
                        db,
                        'SELECT name FROM "Table" WHERE name LIKE ?',
                        (f"{base_name}_fixed%",),
                    )
                    existing_names = [r["name"] for r in existing_fixed]

                    if f"{base_name}_fixed" not in existing_names:
                        fixed_name = f"{base_name}_fixed"
                    else:
                        v = 2
                        while f"{base_name}_fixed_v{v}" in existing_names:
                            v += 1
                        fixed_name = f"{base_name}_fixed_v{v}"

                    new_table_id = gen_id()
                    new_table_name = fixed_name
                    now = now_iso()

                    columns_def = []
                    for col in current_df.columns:
                        ct = "string"
                        if pd.api.types.is_numeric_dtype(current_df[col]):
                            ct = "number"
                        elif pd.api.types.is_datetime64_any_dtype(current_df[col]):
                            ct = "datetime"
                        columns_def.append({"name": str(col), "type": ct})

                    svc_id = orig["serviceId"] if orig else None
                    applied_types = ", ".join(
                        t.get("transformType", "") for t in transforms
                    )

                    await db.execute(
                        """INSERT INTO "Table" (id,name,fullyQualifiedName,description,serviceId,columns,columnCount,rowCount,qualityScore,freshnessStatus,lastProfiled,tier,tags,owners,createdAt,updatedAt)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            new_table_id,
                            fixed_name,
                            f"file_uploads.{fixed_name}",
                            f"Auto-fixed copy of {base_name} (batch: {applied_types})",
                            svc_id,
                            json.dumps(columns_def),
                            len(columns_def),
                            len(current_df),
                            100.0,
                            "fresh",
                            now,
                            2,
                            "[]",
                            "[]",
                            now,
                            now,
                        ),
                    )

                    save_dataframe(new_table_id, current_df, "csv")

                    print(
                        f"[FIX-BATCH] Created fixed copy: {fixed_name} (id={new_table_id}) from {base_name} with {len(transforms)} transforms"
                    )

                    await db.execute(
                        """INSERT INTO Activity (id,entityType,entityId,entityName,action,description,tags,timestamp)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            gen_id(),
                            "table",
                            new_table_id,
                            fixed_name,
                            "auto_fix_batch",
                            f"Batch-fixed {base_name}: {applied_types}",
                            json.dumps(
                                [t.get("transformType", "") for t in transforms]
                            ),
                            now,
                        ),
                    )

            except Exception as e:
                import traceback

                traceback.print_exc()
                save_copy_error = str(e)
                new_table_id = None
                new_table_name = None
                print(f"[FIX-BATCH] Failed to create fixed copy: {e}")

        response = {
            "success": all_success,
            "message": f"Batch: {len(transforms)} transforms applied ({sum(1 for s in step_results if s.get('success'))} succeeded)",
            "duration_ms": total_duration,
            "rows_affected": total_rows_affected,
            "step_results": step_results,
        }
        if new_table_id:
            response["newTableId"] = new_table_id
            response["newTableName"] = new_table_name
        if save_copy_error:
            response["saveCopyError"] = save_copy_error
        return response

    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/transforms/history/{tableId}")
async def get_transform_history(tableId: str, limit: int = 50):
    try:
        from transformations.history import TransformHistory

        history = TransformHistory(tableId)
        return history.get_history(limit=limit)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/transforms/rollback")
async def rollback_transform(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        snapshot_id = body.get("snapshotId")
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})

        from transformations.history import TransformHistory

        history = TransformHistory(table_id)

        if snapshot_id:
            df = history.rollback(snapshot_id)
        else:
            df = history.rollback_last()

        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No snapshot found to rollback to"}
            )

        save_dataframe(table_id, df, "csv")
        return {
            "success": True,
            "message": "Rolled back successfully",
            "rows": len(df),
            "columns": list(df.columns),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# PIPELINE CRUD & EXECUTION (P0)
# ═══════════════════════════════════════════════


@app.get("/api/pipelines")
async def list_pipelines(tableId: Optional[str] = None):
    try:
        async with get_db() as db:
            where, params = [], []
            if tableId:
                where.append("tableId=?")
                params.append(tableId)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db, f"SELECT * FROM Pipeline {w} ORDER BY createdAt DESC", (*params,)
            )
            for r in rows:
                # Ensure steps is always a list — never None/null
                raw_steps = r.get("steps")
                if isinstance(raw_steps, str):
                    try:
                        r["steps"] = json.loads(raw_steps)
                    except (json.JSONDecodeError, TypeError):
                        r["steps"] = []
                elif isinstance(raw_steps, list):
                    r["steps"] = raw_steps
                else:
                    r["steps"] = []
                # Add runCount as top-level field (frontend expects this)
                run_count = await query_scalar(
                    db,
                    "SELECT COUNT(*) FROM PipelineRun WHERE pipelineId=?",
                    (r["id"],),
                )
                r["runCount"] = int(run_count) if run_count else 0
                r["_count"] = {"runs": r["runCount"]}
                # Enrich with table name
                if r.get("tableId"):
                    tbl = await query_one(
                        db, 'SELECT name FROM "Table" WHERE id=?', (r["tableId"],)
                    )
                    r["tableName"] = tbl["name"] if tbl else r["tableId"]
                else:
                    r["tableName"] = None
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/pipelines")
async def create_pipeline(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        pid = gen_id()
        steps = (
            json.dumps(body.get("steps", []))
            if isinstance(body.get("steps"), list)
            else body.get("steps", "[]")
        )
        # Accept both tableId and tableName; resolve name to ID if needed
        table_id = body.get("tableId") or body.get("tableName")
        if table_id and not body.get("tableId"):
            # Try to resolve table name to UUID
            try:
                async with get_db() as db:
                    tbl = await query_one(
                        db, 'SELECT id FROM "Table" WHERE name=? LIMIT 1', (table_id,)
                    )
                    if tbl:
                        table_id = tbl["id"]
            except Exception:
                pass
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Pipeline (id,name,description,steps,version,tableId,status,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    pid,
                    body.get("name", "Untitled Pipeline"),
                    body.get("description", ""),
                    steps,
                    body.get("version", 1),
                    table_id,
                    body.get("status", "draft"),
                    now,
                    now,
                ),
            )
            return {
                "id": pid,
                "name": body.get("name", "Untitled Pipeline"),
                "description": body.get("description", ""),
                "steps": (
                    body.get("steps", [])
                    if isinstance(body.get("steps"), list)
                    else json.loads(steps)
                ),
                "version": body.get("version", 1),
                "tableId": table_id,
                "status": body.get("status", "draft"),
                "createdAt": now,
                "updatedAt": now,
                "runCount": 0,
                "tableName": None,
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/pipelines/runs")
async def get_all_pipeline_runs(limit: int = 50):
    """Get runs across ALL pipelines (for the Run History tab)."""
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                "SELECT * FROM PipelineRun ORDER BY createdAt DESC LIMIT ?",
                (limit,),
            )
            for r in rows:
                r["stepResults"] = (
                    json.loads(r["stepResults"])
                    if isinstance(r.get("stepResults"), str)
                    else r.get("stepResults", [])
                )
                r["finalShape"] = (
                    json.loads(r["finalShape"])
                    if isinstance(r.get("finalShape"), str)
                    else r.get("finalShape", [])
                )
                # Enrich with pipeline name
                p = await query_one(
                    db, "SELECT name FROM Pipeline WHERE id=?", (r.get("pipelineId"),)
                )
                r["pipelineName"] = p["name"] if p else "Unknown"
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/pipelines/{pid}")
async def get_pipeline(pid: str):
    try:
        async with get_db() as db:
            p = await query_one(db, "SELECT * FROM Pipeline WHERE id=?", (pid,))
            if not p:
                return JSONResponse(
                    status_code=404, content={"error": "Pipeline not found"}
                )
            # Ensure steps is always a list — never None/null
            raw_steps = p.get("steps")
            if isinstance(raw_steps, str):
                try:
                    p["steps"] = json.loads(raw_steps)
                except (json.JSONDecodeError, TypeError):
                    p["steps"] = []
            elif isinstance(raw_steps, list):
                p["steps"] = raw_steps
            else:
                p["steps"] = []
            # Add runCount as top-level field
            run_count = await query_scalar(
                db, "SELECT COUNT(*) FROM PipelineRun WHERE pipelineId=?", (pid,)
            )
            p["runCount"] = int(run_count) if run_count else 0
            # Enrich with table name
            if p.get("tableId"):
                tbl = await query_one(
                    db, 'SELECT name FROM "Table" WHERE id=?', (p["tableId"],)
                )
                p["tableName"] = tbl["name"] if tbl else p["tableId"]
            p["runs"] = await query_all(
                db,
                "SELECT * FROM PipelineRun WHERE pipelineId=? ORDER BY createdAt DESC LIMIT 10",
                (pid,),
            )
            return p
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/pipelines/{pid}")
async def update_pipeline(pid: str, request: Request):
    try:
        body = await request.json()
        now = now_iso()
        async with get_db() as db:
            for k, v in body.items():
                if k in ("name", "description", "status", "tableId"):
                    await db.execute(
                        f'UPDATE Pipeline SET "{k}"=?, updatedAt=? WHERE id=?',
                        (v, now, pid),
                    )
                elif k == "steps":
                    val = json.dumps(v) if isinstance(v, list) else v
                    await db.execute(
                        "UPDATE Pipeline SET steps=?, updatedAt=? WHERE id=?",
                        (val, now, pid),
                    )
                elif k == "version":
                    await db.execute(
                        "UPDATE Pipeline SET version=?, updatedAt=? WHERE id=?",
                        (v, now, pid),
                    )
            return {"message": "Updated", "id": pid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/pipelines/{pid}")
async def delete_pipeline(pid: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM PipelineRun WHERE pipelineId=?", (pid,))
            await db.execute("DELETE FROM Pipeline WHERE id=?", (pid,))
            return {"message": "Deleted", "id": pid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/pipelines/{pid}/run")
async def run_pipeline(pid: str, request: Request):
    try:
        # Safely parse body — may be empty
        body = {}
        try:
            ct = request.headers.get("content-type", "")
            if ct.startswith("application/json"):
                body = await request.json()
        except Exception:
            body = {}

        now = now_iso()
        async with get_db() as db:
            p = await query_one(db, "SELECT * FROM Pipeline WHERE id=?", (pid,))
            if not p:
                return JSONResponse(
                    status_code=404, content={"error": "Pipeline not found"}
                )

            table_id = body.get("tableId") or p.get("tableId")
            if not table_id:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "tableId required (set on pipeline or pass in body)"
                    },
                )

            # Resolve table name to UUID if needed
            try:
                tbl = await query_one(
                    db, 'SELECT id FROM "Table" WHERE id=?', (table_id,)
                )
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT id FROM "Table" WHERE name=? LIMIT 1', (table_id,)
                    )
                if tbl:
                    table_id = tbl["id"]
            except Exception:
                pass

            # Ensure steps is always a list
            raw_steps = p.get("steps")
            if isinstance(raw_steps, str):
                try:
                    steps_data = json.loads(raw_steps)
                except (json.JSONDecodeError, TypeError):
                    steps_data = []
            elif isinstance(raw_steps, list):
                steps_data = raw_steps
            else:
                steps_data = []

        # Mark pipeline as running (for cancellation support)
        _running_pipelines[pid] = True

        # Create a "running" PipelineRun record immediately so UI can show progress
        run_id = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO PipelineRun (id,pipelineId,tableId,status,totalSteps,completedSteps,failedSteps,totalDurationMs,stepResults,finalShape,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    pid,
                    table_id,
                    "running",
                    len(steps_data),
                    0,
                    0,
                    0,
                    "[]",
                    "[]",
                    now,
                ),
            )
            await db.execute(
                "UPDATE Pipeline SET status='running', updatedAt=? WHERE id=?",
                (now, pid),
            )

        from transformations.pipeline import Pipeline, PipelineExecutor

        pipeline = Pipeline(p["id"], p["name"], p.get("description", ""))
        pipeline.steps = []
        for step_data in steps_data:
            from transformations.pipeline import PipelineStep

            step = PipelineStep(
                step_data.get("id", gen_id()[:12]),
                step_data.get("transform_type") or step_data.get("type", ""),
                step_data.get("config", {}),
                step_data.get("name", ""),
                step_data.get("condition"),
                step_data.get("next_step"),
            )
            pipeline.steps.append(step)

        executor = PipelineExecutor(table_id)
        result = executor.execute(pipeline)

        # Check if pipeline was cancelled during execution
        was_cancelled = not _running_pipelines.get(pid, True)

        # Update PipelineRun with final results
        final_status = (
            "cancelled"
            if was_cancelled
            else ("completed" if result.get("success") else "failed")
        )
        async with get_db() as db:
            await db.execute(
                """UPDATE PipelineRun SET status=?, totalSteps=?, completedSteps=?, failedSteps=?,
                   totalDurationMs=?, stepResults=?, finalShape=? WHERE id=?""",
                (
                    final_status,
                    result.get("total_steps", len(steps_data)),
                    result.get("completed_steps", 0),
                    result.get("failed_steps", 0),
                    result.get("total_duration_ms", 0),
                    safe_json_dumps(result.get("step_results", [])),
                    safe_json_dumps(result.get("final_shape", [])),
                    run_id,
                ),
            )
            await db.execute(
                "UPDATE Pipeline SET status=?, updatedAt=? WHERE id=?",
                (
                    (
                        final_status
                        if was_cancelled
                        else ("active" if result.get("success") else "failed")
                    ),
                    now,
                    pid,
                ),
            )

        # Cleanup
        _running_pipelines.pop(pid, None)

        result["run_id"] = run_id
        result["status"] = final_status
        return result
    except Exception as e:
        _running_pipelines.pop(pid, None)
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/pipelines/{pid}/runs")
async def get_pipeline_runs(pid: str, limit: int = 20):
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                "SELECT * FROM PipelineRun WHERE pipelineId=? ORDER BY createdAt DESC LIMIT ?",
                (pid, limit),
            )
            for r in rows:
                r["stepResults"] = (
                    json.loads(r["stepResults"])
                    if isinstance(r.get("stepResults"), str)
                    else r.get("stepResults", [])
                )
                r["finalShape"] = (
                    json.loads(r["finalShape"])
                    if isinstance(r.get("finalShape"), str)
                    else r.get("finalShape", [])
                )
                # Enrich with pipeline name
                p = await query_one(
                    db, "SELECT name FROM Pipeline WHERE id=?", (r.get("pipelineId"),)
                )
                r["pipelineName"] = p["name"] if p else "Unknown"
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Track in-flight pipeline runs for cancellation
_running_pipelines: dict[str, bool] = {}


@app.delete("/api/pipelines/{pid}/run")
async def cancel_pipeline_run(pid: str):
    """Cancel a running pipeline."""
    try:
        _running_pipelines[pid] = False  # Signal cancellation
        async with get_db() as db:
            # Mark any 'running' runs as 'cancelled'
            await db.execute(
                "UPDATE PipelineRun SET status='cancelled' WHERE pipelineId=? AND status='running'",
                (pid,),
            )
            await db.execute(
                "UPDATE Pipeline SET status='cancelled', updatedAt=? WHERE id=?",
                (now_iso(), pid),
            )
        return {"message": "Pipeline run cancelled", "pipelineId": pid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# AUTO-EDA (P0)
# ═══════════════════════════════════════════════


@app.post("/api/auto-eda")
async def generate_auto_eda(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})

        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        async with get_db() as db:
            tbl = await query_one(
                db, 'SELECT name FROM "Table" WHERE id=?', (table_id,)
            )
            table_name = tbl["name"] if tbl else table_id

        from eda.auto_eda import auto_eda

        report = auto_eda.generate_report(df, table_name)

        now = now_iso()
        report_id = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO AutoEDARport (id,tableId,tableName,overview,columnProfiles,correlations,missingAnalysis,distributionAnalysis,outlierSummary,insights,warnings,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    report_id,
                    table_id,
                    table_name,
                    safe_json_dumps(report.get("overview", {})),
                    safe_json_dumps(report.get("column_profiles", {})),
                    safe_json_dumps(report.get("correlations", {})),
                    safe_json_dumps(report.get("missing_analysis", {})),
                    safe_json_dumps(report.get("distribution_analysis", {})),
                    safe_json_dumps(report.get("outlier_summary", {})),
                    safe_json_dumps(report.get("insights", [])),
                    safe_json_dumps(report.get("warnings", [])),
                    now,
                ),
            )

        report["id"] = report_id
        return _sanitize_for_json(report)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


def _format_eda_response(raw: dict, table_name: str) -> dict:
    """Transform the EDA engine's raw output into the shape the frontend expects.

    Frontend expects: tableName, totalRows, totalColumns, memoryUsage, duplicateRows,
    duplicatePct, numericCols, categoricalCols, datetimeCols, booleanCols, overallMissing,
    columnProfiles (array), correlations (array of {col1,col2,value}), insights (array with severity).
    """
    overview = raw.get("overview", {})
    raw_profiles = raw.get("column_profiles", {})
    raw_corrs = raw.get("correlations", {})
    raw_insights = raw.get("insights", [])
    raw_warnings = raw.get("warnings", [])

    # ── Column profiles → flat array ──
    col_profiles = []
    for col_name, p in raw_profiles.items():
        dtype = str(p.get("dtype", ""))
        if p.get("is_categorical") or dtype.startswith(
            ("object", "string", "category")
        ):
            col_type = "categorical"
        elif "int" in dtype or "float" in dtype:
            col_type = "numeric"
        elif "date" in dtype:
            col_type = "datetime"
        elif "bool" in dtype:
            col_type = "boolean"
        else:
            col_type = "categorical" if p.get("unique_pct", 100) < 20 else "categorical"

        profile = {
            "name": col_name,
            "type": col_type,
            "missingCount": p.get("null_count", 0),
            "missingPct": p.get("null_pct", 0),
            "uniqueCount": p.get("unique_count", 0),
            "totalCount": overview.get("rows", 0),
        }
        if col_type == "numeric":
            profile.update(
                {
                    "mean": p.get("mean"),
                    "std": p.get("std"),
                    "min": p.get("min"),
                    "max": p.get("max"),
                    "median": p.get("median"),
                }
            )
        top_vals = p.get("top_values", [])
        if top_vals:
            profile["topValues"] = [
                {
                    "value": str(list(tv.keys())[0]),
                    "count": list(tv.values())[0],
                    "pct": round(
                        list(tv.values())[0] / max(overview.get("rows", 1), 1) * 100, 1
                    ),
                }
                for tv in top_vals[:10]
            ]
        col_profiles.append(profile)

    # ── Correlations → flat array ──
    corr_list = []
    for hc in raw_corrs.get("high_correlations", []):
        corr_list.append(
            {"col1": hc["col1"], "col2": hc["col2"], "value": hc["correlation"]}
        )
    # Also add moderate correlations from matrix
    matrix = raw_corrs.get("matrix", {})
    existing_pairs = {(c["col1"], c["col2"]) for c in corr_list}
    for col1, row_vals in matrix.items():
        for col2, val in row_vals.items():
            if col1 >= col2:
                continue
            pair = (col1, col2)
            if pair not in existing_pairs and abs(val) > 0.3:
                corr_list.append({"col1": col1, "col2": col2, "value": val})
    corr_list.sort(key=lambda c: abs(c["value"]), reverse=True)

    # ── Insights + warnings → unified list with severity ──
    insights = []
    for ins in raw_insights:
        cat = ins.get("category", ins.get("type", "info"))
        severity = (
            "warning"
            if ins.get("type") == "warning"
            else "critical" if ins.get("type") == "critical" else "info"
        )
        insights.append(
            {"type": cat, "message": ins.get("message", ""), "severity": severity}
        )
    for w in raw_warnings:
        insights.append(
            {
                "type": "warning",
                "message": w.get("message", ""),
                "severity": "critical" if w.get("level") == "critical" else "warning",
            }
        )

    # ── Overview fields ──
    total_missing_pct = overview.get("total_missing_pct", 0)

    return {
        "tableName": table_name,
        "totalRows": overview.get("rows", 0),
        "totalColumns": overview.get("columns", 0),
        "memoryUsage": f"{overview.get('memory_mb', 0)} MB",
        "duplicateRows": overview.get("duplicate_rows", 0),
        "duplicatePct": overview.get("duplicate_pct", 0),
        "numericCols": overview.get("numeric_columns", 0),
        "categoricalCols": overview.get("categorical_columns", 0),
        "datetimeCols": overview.get("datetime_columns", 0),
        "booleanCols": 0,
        "overallMissing": round(total_missing_pct, 1),
        "columnProfiles": col_profiles,
        "correlations": corr_list,
        "insights": insights,
    }


@app.get("/api/auto-eda/{tableId}")
async def get_auto_eda(tableId: str):
    try:
        # Resolve tableId (could be name or UUID)
        resolved_id = tableId
        table_name = tableId
        try:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (tableId,)
                )
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tableId,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
                    table_name = tbl["name"]
        except Exception:
            pass

        # Check for cached report
        async with get_db() as db:
            row = await query_one(
                db,
                "SELECT * FROM AutoEDARport WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (resolved_id,),
            )
            if row:
                for key in (
                    "overview",
                    "columnProfiles",
                    "correlations",
                    "missingAnalysis",
                    "distributionAnalysis",
                    "outlierSummary",
                    "insights",
                    "warnings",
                ):
                    if isinstance(row.get(key), str):
                        try:
                            row[key] = json.loads(row[key])
                        except Exception:
                            pass
                # Reconstruct raw engine output from DB row
                raw = {
                    "overview": row.get("overview", {}),
                    "column_profiles": row.get("columnProfiles", {}),
                    "correlations": row.get("correlations", {}),
                    "missing_analysis": row.get("missingAnalysis", {}),
                    "distribution_analysis": row.get("distributionAnalysis", {}),
                    "outlier_summary": row.get("outlierSummary", {}),
                    "insights": row.get("insights", []),
                    "warnings": row.get("warnings", []),
                }
                return _sanitize_for_json(
                    _format_eda_response(raw, row.get("tableName", table_name))
                )

        # No cached result — compute it now
        df = load_dataframe(resolved_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        from eda.auto_eda import auto_eda

        report = auto_eda.generate_report(df, table_name)

        # Cache the result
        now = now_iso()
        report_id = gen_id()
        try:
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO AutoEDARport (id,tableId,tableName,overview,columnProfiles,correlations,missingAnalysis,distributionAnalysis,outlierSummary,insights,warnings,createdAt)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        report_id,
                        resolved_id,
                        table_name,
                        safe_json_dumps(report.get("overview", {})),
                        safe_json_dumps(report.get("column_profiles", {})),
                        safe_json_dumps(report.get("correlations", {})),
                        safe_json_dumps(report.get("missing_analysis", {})),
                        safe_json_dumps(report.get("distribution_analysis", {})),
                        safe_json_dumps(report.get("outlier_summary", {})),
                        safe_json_dumps(report.get("insights", [])),
                        safe_json_dumps(report.get("warnings", [])),
                        now,
                    ),
                )
        except Exception as e:
            print(f"[AUTO-EDA] Failed to cache report: {e}")

        return _sanitize_for_json(_format_eda_response(report, table_name))
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# AUTO-EXECUTE FIXES WITH APPROVAL WORKFLOW (P0)
# ═══════════════════════════════════════════════


@app.post("/api/auto-fix/propose")
async def propose_auto_fix(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        check_id = body.get("checkId")
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})

        async with get_db() as db:
            # ── Resolve table_id to a table name for flexible matching ──
            # table_id might be a UUID (from Table.id) or a name string
            table_name = None
            tbl = await query_one(
                db, 'SELECT name FROM "Table" WHERE id=?', (table_id,)
            )
            if tbl:
                table_name = tbl["name"]
            else:
                # Maybe it's a name, not an ID
                tbl = await query_one(
                    db, 'SELECT id, name FROM "Table" WHERE name=? LIMIT 1', (table_id,)
                )
                if tbl:
                    table_name = tbl["name"]
                    table_id = tbl["id"]
                else:
                    # Last resort: use the table_id as the name directly
                    table_name = table_id

            # ── Find failed checks using MULTIPLE strategies ──
            # Strategy 1: Join through Dataset → Table by name
            failed_checks = await query_all(
                db,
                """SELECT qc.* FROM QualityCheck qc
                   JOIN QualityRule qr ON qc.ruleId = qr.id
                   JOIN Dataset ds ON qr.datasetId = ds.id
                   JOIN "Table" t ON t.name = ds.name
                   WHERE t.id=? AND qc.status='failed'
                   ORDER BY qc.createdAt DESC LIMIT 10""",
                (table_id,),
            )

            # Strategy 2: If no results, try matching by table name directly on QualityRule.datasetId
            if not failed_checks:
                # The datasetId might be the Table's ID (not a Dataset UUID)
                failed_checks = await query_all(
                    db,
                    """SELECT qc.* FROM QualityCheck qc
                       JOIN QualityRule qr ON qc.ruleId = qr.id
                       WHERE qr.datasetId=? AND qc.status='failed'
                       ORDER BY qc.createdAt DESC LIMIT 10""",
                    (table_id,),
                )

            # Strategy 3: If still no results, try matching by table name as datasetId
            if not failed_checks and table_name:
                failed_checks = await query_all(
                    db,
                    """SELECT qc.* FROM QualityCheck qc
                       JOIN QualityRule qr ON qc.ruleId = qr.id
                       WHERE qr.datasetId=? AND qc.status='failed'
                       ORDER BY qc.createdAt DESC LIMIT 10""",
                    (table_name,),
                )

            # Strategy 4: Also try looking for a Dataset with matching name
            if not failed_checks and table_name:
                ds = await query_one(
                    db, "SELECT id FROM Dataset WHERE name=?", (table_name,)
                )
                if ds:
                    failed_checks = await query_all(
                        db,
                        """SELECT qc.* FROM QualityCheck qc
                           JOIN QualityRule qr ON qc.ruleId = qr.id
                           WHERE qr.datasetId=? AND qc.status='failed'
                           ORDER BY qc.createdAt DESC LIMIT 10""",
                        (ds["id"],),
                    )

            if check_id:
                check = await query_one(
                    db, "SELECT * FROM QualityCheck WHERE id=?", (check_id,)
                )
                if check:
                    failed_checks = [check]

            if not failed_checks:
                return {
                    "proposals": [],
                    "message": f"No failed checks found for table '{table_name}'. Run quality checks first.",
                }

        proposals = []
        for check in failed_checks:
            async with get_db() as db:
                rule = await query_one(
                    db, "SELECT name FROM QualityRule WHERE id=?", (check["ruleId"],)
                )
                rule_name = rule["name"] if rule else "Unknown"

            from llm.fix_generator import generate as generate_fix

            fix_data = generate_fix(
                rule_name,
                {
                    "status": check.get("status"),
                    "score": check.get("score"),
                    "recordsFailed": check.get("recordsFailed"),
                    "failures": check.get("failures"),
                },
            )

            # Determine the best transform type from the fix
            fix_type = "imputation"
            fix_config = {}
            explanation = fix_data.get("explanation", "")
            if "duplicate" in explanation.lower():
                fix_type = "dedup"
            elif "outlier" in explanation.lower():
                fix_type = "outlier"
            elif "encod" in explanation.lower():
                fix_type = "encoding"
            elif "normaliz" in explanation.lower() or "scale" in explanation.lower():
                fix_type = "normalization"
            elif "string" in explanation.lower() or "clean" in explanation.lower():
                fix_type = "string_clean"
            elif "date" in explanation.lower() or "parse" in explanation.lower():
                fix_type = "date_parse"
            elif "type" in explanation.lower() or "cast" in explanation.lower():
                fix_type = "type_conversion"

            now = now_iso()
            fix_id = gen_id()
            fix_config_json = json.dumps(fix_config)
            # Store rich metadata in resultSummary so the list endpoint can display it
            result_summary = json.dumps(
                {
                    "explanation": explanation,
                    "fixCode": fix_data.get("fix_code", ""),
                    "message": f"Quality issue: {check.get('ruleName', rule_name)}",
                    "confidence": 0.75,
                    "rows_affected": check.get("recordsFailed", 0) or 0,
                    "generationMethod": fix_data.get("generationMethod", "template"),
                }
            )
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO FixApproval (id,tableId,checkId,fixType,fixConfig,proposedBy,status,resultSummary,createdAt)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        fix_id,
                        table_id,
                        check.get("id"),
                        fix_type,
                        fix_config_json,
                        "ai",
                        "pending",
                        result_summary,
                        now,
                    ),
                )

            proposals.append(
                {
                    "id": fix_id,
                    "tableId": table_id,
                    "checkId": check.get("id"),
                    "fixType": fix_type,
                    "fixConfig": fix_config,
                    "explanation": explanation,
                    "fixCode": fix_data.get("fix_code", ""),
                    "generationMethod": fix_data.get("generationMethod", "template"),
                    "status": "pending",
                    "createdAt": now,
                }
            )

        return {"proposals": proposals}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/auto-fix/pending")
async def get_pending_fixes(
    tableId: Optional[str] = None, status: Optional[str] = None
):
    """List fix proposals. ?status=pending|approved|applied|rejected|failed or omit for all.
    Maps backend 'pending' to frontend 'proposed' status."""
    try:
        async with get_db() as db:
            where_clauses = []
            params = []
            if tableId:
                where_clauses.append("tableId=?")
                params.append(tableId)
            if status and status != "all":
                # Frontend sends 'proposed', backend stores 'pending'
                backend_status = "pending" if status == "proposed" else status
                where_clauses.append("status=?")
                params.append(backend_status)

            where_sql = (
                (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            )
            rows = await query_all(
                db,
                f"SELECT * FROM FixApproval{where_sql} ORDER BY createdAt DESC",
                tuple(params),
            )

            all_rows = []
            for row in rows:
                # Enrich with table name from metadata — try UUID lookup first, then name fallback
                table_name = ""
                if row.get("tableId"):
                    tbl = await query_one(
                        db, 'SELECT name FROM "Table" WHERE id=?', (row["tableId"],)
                    )
                    if tbl:
                        table_name = tbl["name"]
                    else:
                        # Maybe tableId is a name string (from uploaded_data.db backfill)
                        tbl2 = await query_one(
                            db,
                            'SELECT name FROM "Table" WHERE name=? LIMIT 1',
                            (row["tableId"],),
                        )
                        if tbl2:
                            table_name = tbl2["name"]
                        else:
                            table_name = str(row["tableId"])

                # Parse fixConfig
                fix_config = {}
                try:
                    fix_config = (
                        json.loads(row["fixConfig"])
                        if isinstance(row.get("fixConfig"), str)
                        else (row.get("fixConfig") or {})
                    )
                except Exception:
                    fix_config = {}

                # Parse resultSummary
                result_summary = {}
                try:
                    result_summary = (
                        json.loads(row["resultSummary"])
                        if isinstance(row.get("resultSummary"), str)
                        else (row.get("resultSummary") or {})
                    )
                except Exception:
                    result_summary = {}

                # Map backend status → frontend status
                raw_status = row.get("status", "pending")
                frontend_status = "proposed" if raw_status == "pending" else raw_status

                # Confidence
                confidence = result_summary.get("confidence", 0.75)
                if not isinstance(confidence, (int, float)):
                    try:
                        confidence = float(confidence)
                    except Exception:
                        confidence = 0.75

                # Row counts
                affected_rows = (
                    result_summary.get(
                        "rows_affected", result_summary.get("recordsFailed", 0)
                    )
                    or 0
                )
                total_rows = (
                    result_summary.get(
                        "total_rows", result_summary.get("recordsTotal", 0)
                    )
                    or 0
                )

                all_rows.append(
                    {
                        "id": row["id"],
                        "tableName": table_name,
                        "columnName": fix_config.get(
                            "column", fix_config.get("columnName", "")
                        ),
                        "issueType": row.get("fixType", "unknown"),
                        "issueDescription": result_summary.get(
                            "message", f"Quality issue: {row.get('fixType', 'unknown')}"
                        ),
                        "fixType": row.get("fixType", "imputation"),
                        "fixDescription": result_summary.get(
                            "explanation",
                            f"Apply {row.get('fixType', 'imputation')} fix",
                        ),
                        "fixDetails": result_summary.get(
                            "fixCode",
                            json.dumps(fix_config, indent=2) if fix_config else "",
                        ),
                        "confidence": confidence,
                        "affectedRows": affected_rows,
                        "totalRows": total_rows,
                        "status": frontend_status,
                        "proposedAt": row.get("createdAt", ""),
                        "resolvedAt": row.get("appliedAt")
                        or row.get("rolledBackAt")
                        or None,
                        "resolvedBy": row.get("proposedBy", "ai"),
                        "rejectionReason": result_summary.get("rejectionReason", None),
                        "tableId": row.get("tableId", ""),
                        "checkId": row.get("checkId", ""),
                        "fixConfig": fix_config,
                    }
                )

            return {"fixes": all_rows}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/auto-fix/{fix_id}/approve")
async def approve_fix(fix_id: str):
    """Approve a fix proposal (sets status to 'approved'). The fix is actually applied via /apply."""
    try:
        now = now_iso()
        async with get_db() as db:
            fix = await query_one(db, "SELECT * FROM FixApproval WHERE id=?", (fix_id,))
            if not fix:
                return JSONResponse(
                    status_code=404, content={"error": "Fix proposal not found"}
                )
            if fix["status"] not in ("pending",):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": f"Fix is already {fix['status']}, cannot approve"
                    },
                )
            await db.execute(
                "UPDATE FixApproval SET status='approved', resultSummary=? WHERE id=?",
                (json.dumps({"approved": True, "approvedAt": now}), fix_id),
            )
        return {
            "success": True,
            "message": "Fix approved. Use /apply to execute it.",
            "id": fix_id,
            "status": "approved",
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/auto-fix/{fix_id}/reject")
async def reject_fix(fix_id: str, request: Request):
    try:
        now = now_iso()
        body = {}
        try:
            body = await request.json()
        except Exception:
            body = {}
        reason = body.get("reason", "")

        async with get_db() as db:
            fix = await query_one(db, "SELECT * FROM FixApproval WHERE id=?", (fix_id,))
            if not fix:
                return JSONResponse(
                    status_code=404, content={"error": "Fix proposal not found"}
                )
            if fix["status"] not in ("pending", "approved"):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Fix is {fix['status']}, cannot reject"},
                )
            result_summary = {"rejected": True, "rejectedAt": now}
            if reason:
                result_summary["rejectionReason"] = reason
            await db.execute(
                "UPDATE FixApproval SET status='rejected', rolledBackAt=?, resultSummary=? WHERE id=?",
                (now, json.dumps(result_summary), fix_id),
            )
        return {"success": True, "message": "Fix rejected", "id": fix_id}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# DATA CONNECTORS (P1)
# ═══════════════════════════════════════════════


@app.get("/api/connectors/sources")
async def list_connector_sources():
    try:
        from connectors.data_connectors import connectors

        return connectors.list_sources()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/connectors")
async def list_connectors():
    try:
        async with get_db() as db:
            rows = await query_all(
                db, "SELECT * FROM Connector ORDER BY createdAt DESC"
            )
            for r in rows:
                # Parse config JSON to extract host/port/database for frontend
                config = r.get("config", "{}")
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except (json.JSONDecodeError, TypeError):
                        config = {}
                r["host"] = config.get("host", "")
                r["port"] = config.get("port")
                r["database"] = config.get("database", "")
                r["username"] = config.get("username", "")
                r["tablesCount"] = config.get("tablesCount", 0)
                r["lastSync"] = r.get(
                    "lastTested"
                )  # Map lastTested → lastSync for frontend
                # Map backend status to frontend status
                backend_status = r.get("status", "inactive")
                if backend_status == "active":
                    r["status"] = "connected"
                elif backend_status == "error":
                    r["status"] = "error"
                else:
                    r["status"] = "disconnected"
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/connectors")
async def create_connector(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        cid = gen_id()
        connector_type = body.get("type", "postgresql")
        # Store connection details inside config JSON
        config = {
            "host": body.get("host", ""),
            "port": body.get("port"),
            "database": body.get("database", ""),
            "username": body.get("username", ""),
            "password": body.get("password", ""),
            "tablesCount": 0,
        }
        # Merge any extra config from body
        if isinstance(body.get("config"), dict):
            config.update(body["config"])

        # For local_sqlite, auto-test on creation
        initial_status = "inactive"
        frontend_status = "disconnected"
        tables_count = 0
        if connector_type == "local_sqlite":
            try:
                from connectors.data_connectors import connectors as conn_engine

                test_result = conn_engine.test_connection("local_sqlite", config)
                if test_result.get("success"):
                    initial_status = "active"
                    frontend_status = "connected"
                    tables_count = test_result.get("tablesCount", 0)
                    config["tablesCount"] = tables_count
            except Exception:
                pass

        config_json = json.dumps(config)
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Connector (id,name,type,config,status,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    cid,
                    body.get("name"),
                    connector_type,
                    config_json,
                    initial_status,
                    now,
                    now,
                ),
            )
            return {
                "id": cid,
                "name": body.get("name"),
                "type": connector_type,
                "host": config.get("host", ""),
                "port": config.get("port"),
                "database": config.get("database", ""),
                "status": frontend_status,
                "tablesCount": tables_count,
                "lastSync": now if frontend_status == "connected" else None,
                "createdAt": now,
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/connectors/{cid}/test")
async def test_connector(cid: str):
    try:
        async with get_db() as db:
            conn = await query_one(db, "SELECT * FROM Connector WHERE id=?", (cid,))
            if not conn:
                return JSONResponse(
                    status_code=404, content={"error": "Connector not found"}
                )
            config = (
                json.loads(conn["config"])
                if isinstance(conn["config"], str)
                else conn.get("config", {})
            )

        from connectors.data_connectors import connectors as conn_engine

        result = conn_engine.test_connection(conn["type"], config)
        now = now_iso()

        db_status = "active" if result.get("success") else "error"
        frontend_status = "connected" if result.get("success") else "error"
        error = result.get("error", "")

        # Update tablesCount in config if provided by the test
        tables_count = result.get("tablesCount")
        if tables_count is not None:
            config["tablesCount"] = tables_count
            config_json = json.dumps(config)
            async with get_db() as db:
                await db.execute(
                    "UPDATE Connector SET status=?, lastTested=?, lastError=?, config=?, updatedAt=? WHERE id=?",
                    (db_status, now, error if error else None, config_json, now, cid),
                )
        else:
            async with get_db() as db:
                await db.execute(
                    "UPDATE Connector SET status=?, lastTested=?, lastError=?, updatedAt=? WHERE id=?",
                    (db_status, now, error if error else None, now, cid),
                )

        # Return frontend-compatible status
        result["status"] = frontend_status
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/connectors/{cid}/fetch")
async def fetch_connector_data(cid: str, request: Request):
    try:
        body = (
            await request.json()
            if request.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        async with get_db() as db:
            conn = await query_one(db, "SELECT * FROM Connector WHERE id=?", (cid,))
            if not conn:
                return JSONResponse(
                    status_code=404, content={"error": "Connector not found"}
                )
            config = (
                json.loads(conn["config"])
                if isinstance(conn["config"], str)
                else conn.get("config", {})
            )
            # Merge any override config from request body
            if body.get("config"):
                override = body["config"]
                if isinstance(override, dict):
                    config.update(override)

        from connectors.data_connectors import connectors as conn_engine

        result = conn_engine.fetch_data(conn["type"], config)

        if result.get("success") and result.get("data") is not None:
            df = result.pop("data")
            # Save as a new table
            tbl_id = gen_id()
            save_dataframe(tbl_id, df, "csv")
            result["tableId"] = tbl_id
            result["rows"] = len(df)
            result["columns"] = list(df.columns)

        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/connectors/{cid}/tables")
async def list_connector_tables(cid: str):
    try:
        async with get_db() as db:
            conn = await query_one(db, "SELECT * FROM Connector WHERE id=?", (cid,))
            if not conn:
                return JSONResponse(
                    status_code=404, content={"error": "Connector not found"}
                )
            config = (
                json.loads(conn["config"])
                if isinstance(conn["config"], str)
                else conn.get("config", {})
            )

        from connectors.data_connectors import connectors as conn_engine

        result = conn_engine.list_tables(conn["type"], config)

        # Update tablesCount in config
        tables = result.get("tables", [])
        if tables:
            config["tablesCount"] = len(tables)
            config_json = json.dumps(config)
            async with get_db() as db:
                await db.execute(
                    "UPDATE Connector SET config=?, updatedAt=? WHERE id=?",
                    (config_json, now_iso(), cid),
                )

        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/connectors/{cid}/tables/{table_name:path}")
async def get_connector_table_data(cid: str, table_name: str, limit: int = 100):
    try:
        async with get_db() as db:
            conn = await query_one(db, "SELECT * FROM Connector WHERE id=?", (cid,))
            if not conn:
                return JSONResponse(
                    status_code=404, content={"error": "Connector not found"}
                )
            config = (
                json.loads(conn["config"])
                if isinstance(conn["config"], str)
                else conn.get("config", {})
            )

        from connectors.data_connectors import connectors as conn_engine

        result = conn_engine.get_table_data(conn["type"], config, table_name, limit)

        # Ensure rows are JSON serializable (convert numpy types etc.)
        if "rows" in result:
            safe_rows = []
            for row in result["rows"]:
                safe_row = {}
                for k, v in row.items():
                    if v is None:
                        safe_row[k] = None
                    elif hasattr(v, "item"):  # numpy types
                        safe_row[k] = v.item()
                    elif isinstance(v, (bytes, bytearray)):
                        safe_row[k] = v.hex()
                    else:
                        try:
                            json.dumps(v)
                            safe_row[k] = v
                        except (TypeError, ValueError):
                            safe_row[k] = str(v)
                safe_rows.append(safe_row)
            result["rows"] = safe_rows

        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/connectors/{cid}")
async def delete_connector(cid: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM Connector WHERE id=?", (cid,))
            return {"message": "Deleted", "id": cid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# SCHEDULED JOBS (P1)
# ═══════════════════════════════════════════════


@app.get("/api/schedules")
async def list_schedules():
    try:
        async with get_db() as db:
            return await query_all(
                db, "SELECT * FROM ScheduledJob ORDER BY createdAt DESC"
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/schedules")
async def create_schedule(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        sid = gen_id()
        config = (
            json.dumps(body.get("config", {}))
            if isinstance(body.get("config"), dict)
            else body.get("config", "{}")
        )
        alert_channels = (
            json.dumps(body.get("alertChannels", ["in_app"]))
            if isinstance(body.get("alertChannels"), list)
            else body.get("alertChannels", '["in_app"]')
        )
        async with get_db() as db:
            await db.execute(
                """INSERT INTO ScheduledJob (id,name,type,targetId,cron,interval,enabled,alertOnFailure,alertChannels,config,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sid,
                    body.get("name"),
                    body.get("type", "check"),
                    body.get("targetId"),
                    body.get("cron", "0 9 * * *"),
                    body.get("interval"),
                    1 if body.get("enabled", True) else 0,
                    1 if body.get("alertOnFailure", True) else 0,
                    alert_channels,
                    config,
                    now,
                ),
            )
            return {"id": sid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/schedules/{sid}")
async def update_schedule(sid: str, request: Request):
    try:
        body = await request.json()
        async with get_db() as db:
            for k, v in body.items():
                if k in ("name", "type", "targetId", "cron", "interval"):
                    await db.execute(
                        f'UPDATE ScheduledJob SET "{k}"=? WHERE id=?', (v, sid)
                    )
                elif k == "enabled":
                    await db.execute(
                        "UPDATE ScheduledJob SET enabled=? WHERE id=?",
                        (1 if v else 0, sid),
                    )
                elif k == "alertOnFailure":
                    await db.execute(
                        "UPDATE ScheduledJob SET alertOnFailure=? WHERE id=?",
                        (1 if v else 0, sid),
                    )
                elif k == "config":
                    val = json.dumps(v) if isinstance(v, dict) else v
                    await db.execute(
                        "UPDATE ScheduledJob SET config=? WHERE id=?", (val, sid)
                    )
                elif k == "alertChannels":
                    val = json.dumps(v) if isinstance(v, list) else v
                    await db.execute(
                        "UPDATE ScheduledJob SET alertChannels=? WHERE id=?", (val, sid)
                    )
            return {"message": "Updated", "id": sid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/schedules/{sid}")
async def delete_schedule(sid: str):
    try:
        async with get_db() as db:
            await db.execute("DELETE FROM ScheduledJob WHERE id=?", (sid,))
            return {"message": "Deleted", "id": sid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/schedules/{sid}/run")
async def run_schedule(sid: str):
    try:
        now = now_iso()
        async with get_db() as db:
            job = await query_one(db, "SELECT * FROM ScheduledJob WHERE id=?", (sid,))
            if not job:
                return JSONResponse(
                    status_code=404, content={"error": "Scheduled job not found"}
                )

            await db.execute(
                "UPDATE ScheduledJob SET lastRun=?, runCount=runCount+1 WHERE id=?",
                (now, sid),
            )

        return {
            "success": True,
            "message": f"Job '{job['name']}' triggered",
            "jobId": sid,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# ML-READINESS SCORE (P1)
# ═══════════════════════════════════════════════


@app.post("/api/ml-readiness")
async def score_ml_readiness(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        target_column = body.get("targetColumn", "")
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})

        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        async with get_db() as db:
            tbl = await query_one(
                db, 'SELECT name FROM "Table" WHERE id=?', (table_id,)
            )
            table_name = tbl["name"] if tbl else table_id

        from ml_readiness.scorer import ml_readiness

        result = ml_readiness.score(df, target_column)

        now = now_iso()
        score_id = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO MLReadinessScore (id,tableId,tableName,overallScore,grade,dimensions,issues,recommendations,isMLReady,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    score_id,
                    table_id,
                    table_name,
                    result.get("overall_score", 0),
                    result.get("grade", "F"),
                    safe_json_dumps(result.get("dimensions", {})),
                    safe_json_dumps(result.get("issues", [])),
                    safe_json_dumps(result.get("recommendations", [])),
                    1 if result.get("is_ml_ready") else 0,
                    now,
                ),
            )

        result["id"] = score_id
        return _sanitize_for_json(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


def _format_ml_readiness_response(
    raw_result: dict, table_name: str, score_id: str
) -> dict:
    """Transform the ML scorer's raw output into the format the frontend expects.

    Scorer returns: overall_score, grade, dimensions={name: {score, issues, ...}}, issues, recommendations
    Frontend expects: overallScore, overallGrade, dimensions={name: number}, issues with title/description/impact/recommendation, recommendations with id/expectedImprovement/effort
    """
    # Flatten dimensions from {name: {score, issues, extras}} → {name: score}
    # Also rename keys to match frontend expectations
    dim_key_map = {
        "encoding_needed": "encoding",
        "target_suitability": "target_suitability",  # frontend may not display this
    }
    flat_dimensions = {}
    for dim_name, dim_data in raw_result.get("dimensions", {}).items():
        frontend_key = dim_key_map.get(dim_name, dim_name)
        if isinstance(dim_data, dict):
            flat_dimensions[frontend_key] = dim_data.get("score", 0)
        else:
            flat_dimensions[frontend_key] = dim_data

    # Format issues with all required frontend fields
    formatted_issues = []
    for i, issue in enumerate(raw_result.get("issues", [])):
        formatted_issues.append(
            {
                "id": f"issue-{score_id[:8]}-{i}",
                "dimension": issue.get("dimension", ""),
                "severity": issue.get("severity", "info"),
                "title": (
                    issue.get("message", "")[:80]
                    if issue.get("message")
                    else "Issue detected"
                ),
                "description": issue.get("message", ""),
                "impact": f"Affects {issue.get('dimension', 'data quality')} score",
                "recommendation": issue.get("message", ""),
            }
        )

    # Format recommendations with all required frontend fields
    formatted_recs = []
    for i, rec in enumerate(raw_result.get("recommendations", [])):
        formatted_recs.append(
            {
                "id": f"rec-{score_id[:8]}-{i}",
                "priority": rec.get("priority", "medium"),
                "action": rec.get("action", ""),
                "message": rec.get("message", ""),
                "expectedImprovement": 5 if rec.get("priority") == "high" else 3,
                "effort": "Low" if rec.get("priority") == "high" else "Medium",
            }
        )

    return {
        "id": score_id,
        "tableName": table_name,
        "overallScore": raw_result.get("overall_score", 0),
        "overallGrade": raw_result.get("grade", "F"),
        "dimensions": flat_dimensions,
        "issues": formatted_issues,
        "recommendations": formatted_recs,
        "isMLReady": raw_result.get("is_ml_ready", False),
        "totalIssues": raw_result.get("total_issues", 0),
        "criticalIssues": raw_result.get("critical_issues", 0),
    }


@app.get("/api/ml-readiness/{tableId}")
async def get_ml_readiness(tableId: str):
    try:
        async with get_db() as db:
            row = await query_one(
                db,
                "SELECT * FROM MLReadinessScore WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (tableId,),
            )
            if row:
                for key in ("dimensions", "issues", "recommendations"):
                    if isinstance(row.get(key), str):
                        try:
                            row[key] = json.loads(row[key])
                        except Exception:
                            pass
                # Format for frontend
                return _sanitize_for_json(
                    _format_ml_readiness_response(
                        {
                            "overall_score": row.get("overallScore", 0),
                            "grade": row.get("grade", "F"),
                            "dimensions": row.get("dimensions", {}),
                            "issues": row.get("issues", []),
                            "recommendations": row.get("recommendations", []),
                            "is_ml_ready": bool(row.get("isMLReady", 0)),
                        },
                        row.get("tableName", tableId),
                        row.get("id", ""),
                    )
                )

        # No cached result — compute it now
        # First resolve tableId (could be name or UUID)
        resolved_id = tableId
        table_name = tableId
        try:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (tableId,)
                )
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tableId,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
                    table_name = tbl["name"]
        except Exception:
            pass

        df = load_dataframe(resolved_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        from ml_readiness.scorer import ml_readiness

        result = ml_readiness.score(df, "")

        now = now_iso()
        score_id = gen_id()
        try:
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO MLReadinessScore (id,tableId,tableName,overallScore,grade,dimensions,issues,recommendations,isMLReady,createdAt)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        score_id,
                        resolved_id,
                        table_name,
                        result.get("overall_score", 0),
                        result.get("grade", "F"),
                        safe_json_dumps(result.get("dimensions", {})),
                        safe_json_dumps(result.get("issues", [])),
                        safe_json_dumps(result.get("recommendations", [])),
                        1 if result.get("is_ml_ready") else 0,
                        now,
                    ),
                )
        except Exception as e:
            print(f"[ML-READINESS] Failed to cache score: {e}")

        # Format for frontend
        return _sanitize_for_json(
            _format_ml_readiness_response(result, table_name, score_id)
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# AI DATA PREP COPILOT (P1)
# ═══════════════════════════════════════════════


@app.post("/api/copilot/chat")
async def copilot_chat(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId", "")
        message = body.get("message", "")
        if not message:
            return JSONResponse(status_code=400, content={"error": "message required"})

        # Build context from table data
        context_parts = []
        if table_id:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (table_id,)
                )
                if tbl:
                    context_parts.append(
                        f"Table: {tbl.get('name', 'Unknown')} ({tbl.get('rowCount', 0)} rows, {tbl.get('columnCount', 0)} columns)"
                    )
                    context_parts.append(
                        f"Quality Score: {tbl.get('qualityScore', 100)}"
                    )
                    try:
                        cols = (
                            json.loads(tbl.get("columns", "[]"))
                            if isinstance(tbl.get("columns"), str)
                            else tbl.get("columns", [])
                        )
                        if cols:
                            col_summary = ", ".join(
                                [
                                    f"{c.get('name','?')}({c.get('type','?')})"
                                    for c in cols[:20]
                                ]
                            )
                            context_parts.append(f"Columns: {col_summary}")
                    except Exception:
                        pass

                # Recent check results
                profile = await query_one(
                    db,
                    "SELECT profileData FROM TableProfile WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                    (table_id,),
                )
                if profile and profile.get("profileData"):
                    try:
                        pd_data = (
                            json.loads(profile["profileData"])
                            if isinstance(profile["profileData"], str)
                            else profile["profileData"]
                        )
                        context_parts.append(
                            f"Profile summary: {json.dumps(pd_data)[:500]}"
                        )
                    except Exception:
                        pass

        system_prompt = (
            "You are DataGuard AI Copilot, an expert data preparation assistant. "
            "Help users understand their data quality issues, suggest transformations, "
            "recommend fixes, and guide them through data preparation workflows. "
            "Be concise, practical, and action-oriented. When suggesting transformations, "
            "reference the available transformers: imputation, outlier, dedup, encoding, "
            "normalization, string_clean, date_parse, data_split, type_conversion."
        )
        user_prompt = (
            f"Context:\n{chr(10).join(context_parts)}\n\nUser question: {message}"
            if context_parts
            else message
        )

        # Store user message
        now = now_iso()
        user_msg_id = gen_id()
        async with get_db() as db:
            await db.execute(
                "INSERT INTO CopilotChat (id,tableId,role,content,metadata,createdAt) VALUES (?,?,?,?,?,?)",
                (
                    user_msg_id,
                    table_id,
                    "user",
                    message,
                    json.dumps({"tableId": table_id}),
                    now,
                ),
            )

        # Call LLM
        from llm.client import call_llm

        response_text = None
        try:
            response_text = call_llm(
                system_prompt, user_prompt, temperature=0.4, max_tokens=2048
            )
        except Exception:
            pass

        if not response_text:
            # Fallback response when LLM is not available
            response_text = (
                "I'm currently unable to connect to the AI service. "
                "Here are some general tips:\n"
                "1. Check for missing values and consider imputation\n"
                "2. Remove duplicate rows if any\n"
                "3. Handle outliers using IQR or z-score methods\n"
                "4. Encode categorical columns before ML training\n"
                "5. Normalize/scale numeric features\n"
                "Please try again later for AI-powered suggestions."
            )

        # Store assistant response
        asst_msg_id = gen_id()
        async with get_db() as db:
            await db.execute(
                "INSERT INTO CopilotChat (id,tableId,role,content,metadata,createdAt) VALUES (?,?,?,?,?,?)",
                (asst_msg_id, table_id, "assistant", response_text, "{}", now),
            )

        return {
            "response": response_text,
            "tableId": table_id,
            "messageId": asst_msg_id,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/copilot/suggestions/{tableId}")
async def copilot_suggestions(tableId: str):
    try:
        suggestions = []

        # Resolve table name to UUID if needed
        resolved_id = tableId
        try:
            async with get_db() as db:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE id=?', (tableId,)
                )
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tableId,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
        except Exception:
            pass

        df = load_dataframe(resolved_id)
        async with get_db() as db:
            tbl = await query_one(
                db, 'SELECT * FROM "Table" WHERE id=?', (resolved_id,)
            )

        if df is not None:
            # Missing values suggestion — include ALL columns with missing data
            missing_cols = [
                (
                    col,
                    int(df[col].isna().sum()),
                    round(df[col].isna().sum() / len(df) * 100, 1),
                )
                for col in df.columns
                if df[col].isna().sum() > 0
            ]
            if missing_cols:
                top_missing = sorted(missing_cols, key=lambda x: x[2], reverse=True)[:3]
                suggestions.append(
                    {
                        "type": "imputation",
                        "priority": "high",
                        "title": "Fill missing values",
                        "description": f"Found {len(missing_cols)} columns with missing data. Top: {', '.join(f'{c} ({p}%)' for c, _, p in top_missing)}",
                        "action": "imputation",
                        "config": {
                            "columns": [c for c, _, _ in missing_cols],
                            "method": "mode",
                        },
                    }
                )

            # Duplicates suggestion
            dup_count = int(df.duplicated().sum())
            if dup_count > 0:
                suggestions.append(
                    {
                        "type": "dedup",
                        "priority": "medium",
                        "title": f"Remove {dup_count} duplicate rows",
                        "description": f"{dup_count} duplicate rows detected ({round(dup_count/len(df)*100, 1)}% of data)",
                        "action": "dedup",
                        "config": {},
                    }
                )

            # Outlier suggestion — filter out binary/low-cardinality columns
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            outlier_cols = []
            for col in numeric_cols:
                s = df[col].dropna()
                n_unique = s.nunique()
                # Skip binary columns (2 or fewer unique values like one-hot encoded 0/1)
                # and columns with very low cardinality (likely encoded)
                if n_unique <= 2:
                    continue
                if len(s) > 10:
                    Q1, Q3 = s.quantile(0.25), s.quantile(0.75)
                    IQR = Q3 - Q1
                    if IQR == 0:
                        continue  # No spread, skip
                    outlier_count = int(
                        ((s < Q1 - 1.5 * IQR) | (s > Q3 + 1.5 * IQR)).sum()
                    )
                    if outlier_count > len(s) * 0.05:
                        outlier_cols.append(col)
            if outlier_cols:
                suggestions.append(
                    {
                        "type": "outlier",
                        "priority": "medium",
                        "title": "Handle outliers",
                        "description": f"Outliers detected in: {', '.join(outlier_cols[:5])}",
                        "action": "outlier",
                        "config": {"columns": outlier_cols[:5], "method": "iqr_cap"},
                    }
                )

            # Encoding suggestion — use "one_hot" (matches EncodingTransformer.supported_methods)
            cat_cols = df.select_dtypes(
                include=["object", "category", "string"]
            ).columns.tolist()
            if cat_cols:
                suggestions.append(
                    {
                        "type": "encoding",
                        "priority": "medium",
                        "title": f"Encode {len(cat_cols)} categorical columns",
                        "description": f"Categorical columns need encoding: {', '.join(cat_cols[:5])}",
                        "action": "encoding",
                        "config": {"columns": cat_cols, "method": "one_hot"},
                    }
                )

        if not suggestions:
            suggestions.append(
                {
                    "type": "info",
                    "priority": "low",
                    "title": "Data looks good!",
                    "description": "No major issues detected. Consider running a full profile or ML readiness check for deeper analysis.",
                    "action": "profile",
                    "config": {},
                }
            )

        return {
            "tableId": tableId,
            "resolvedId": resolved_id,
            "suggestions": suggestions,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# STATISTICAL TESTS (P2)
# ═══════════════════════════════════════════════


@app.get("/api/statistical/tests")
async def list_statistical_tests(
    tableId: Optional[str] = None, limit: Optional[int] = 100
):
    """List all statistical tests. Tries module first, falls back to DB query."""
    try:
        from statistical.tests import stat_tests

        module_result = stat_tests.list_tests()
        if module_result is not None:
            return module_result
    except Exception:
        pass
    # Fallback: query StatisticalTest table directly
    try:
        async with get_db() as db:
            where, params = [], []
            if tableId:
                where.append("tableId=?")
                params.append(tableId)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db,
                f"SELECT * FROM StatisticalTest {w} ORDER BY createdAt DESC LIMIT ?",
                (*params, min(limit, 500)),
            )
            for r in rows:
                if isinstance(r.get("config"), str):
                    try:
                        r["config"] = json.loads(r["config"])
                    except Exception:
                        pass
                if isinstance(r.get("result"), str):
                    try:
                        r["result"] = json.loads(r["result"])
                    except Exception:
                        pass
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/statistical/run")
async def run_statistical_test(request: Request):
    try:
        body = await request.json()
        table_id = body.get("tableId")
        test_type = body.get("testType", "generic")
        config = body.get("config", {})
        if not table_id:
            return JSONResponse(status_code=400, content={"error": "tableId required"})

        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        # Try module first, fallback to basic statistical summary
        result = None
        try:
            from statistical.tests import stat_tests

            result = stat_tests.run_test(test_type, df, config)
        except Exception:
            pass

        if result is None:
            # Fallback: basic statistical summary
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            result = {
                "testType": test_type,
                "tableId": table_id,
                "summary": {
                    "rowCount": len(df),
                    "columnCount": len(df.columns),
                    "numericColumns": numeric_cols,
                },
                "status": "completed",
            }
            if numeric_cols:
                stats = {}
                for col in numeric_cols[:20]:
                    s = df[col].dropna()
                    stats[col] = _sanitize_for_json(
                        {
                            "mean": float(s.mean()) if len(s) > 0 else None,
                            "std": float(s.std()) if len(s) > 1 else None,
                            "min": float(s.min()) if len(s) > 0 else None,
                            "max": float(s.max()) if len(s) > 0 else None,
                            "median": float(s.median()) if len(s) > 0 else None,
                        }
                    )
                result["descriptiveStats"] = stats

        now = now_iso()
        test_id = gen_id()
        config_json = json.dumps(config) if isinstance(config, dict) else str(config)
        result_json = safe_json_dumps(result)
        async with get_db() as db:
            await db.execute(
                """INSERT INTO StatisticalTest (id,tableId,testType,config,result,createdAt)
                VALUES (?,?,?,?,?,?)""",
                (test_id, table_id, test_type, config_json, result_json, now),
            )

        result["id"] = test_id
        return _sanitize_for_json(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/statistical/results/{tableId}")
async def get_statistical_results(tableId: str, limit: int = 20):
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                "SELECT * FROM StatisticalTest WHERE tableId=? ORDER BY createdAt DESC LIMIT ?",
                (tableId, limit),
            )
            for r in rows:
                if isinstance(r.get("config"), str):
                    try:
                        r["config"] = json.loads(r["config"])
                    except:
                        pass
                if isinstance(r.get("result"), str):
                    try:
                        r["result"] = json.loads(r["result"])
                    except:
                        pass
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# DATA CONTRACTS (P2)
# ═══════════════════════════════════════════════


@app.get("/api/contracts")
async def list_contracts():
    try:
        async with get_db() as db:
            rows = await query_all(
                db, "SELECT * FROM DataContract ORDER BY createdAt DESC"
            )
            for r in rows:
                if isinstance(r.get("contractDef"), str):
                    try:
                        r["contractDef"] = json.loads(r["contractDef"])
                    except:
                        pass
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/contracts")
async def create_contract(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        cid = gen_id()
        contract_def = (
            json.dumps(body.get("contractDef", {}))
            if isinstance(body.get("contractDef"), dict)
            else body.get("contractDef", "{}")
        )
        async with get_db() as db:
            await db.execute(
                """INSERT INTO DataContract (id,name,description,contractDef,tableId,lastScore,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?,?)""",
                (
                    cid,
                    body.get("name"),
                    body.get("description"),
                    contract_def,
                    body.get("tableId"),
                    100.0,
                    now,
                    now,
                ),
            )
            return {"id": cid, "name": body.get("name")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/contracts/{cid}/validate")
async def validate_contract(cid: str, request: Request):
    try:
        body = (
            await request.json()
            if request.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        async with get_db() as db:
            contract = await query_one(
                db, "SELECT * FROM DataContract WHERE id=?", (cid,)
            )
            if not contract:
                return JSONResponse(
                    status_code=404, content={"error": "Contract not found"}
                )

            table_id = body.get("tableId") or contract.get("tableId")
            contract_def = (
                json.loads(contract["contractDef"])
                if isinstance(contract["contractDef"], str)
                else contract.get("contractDef", {})
            )

        if not table_id:
            return JSONResponse(
                status_code=400,
                content={"error": "tableId required (set on contract or pass in body)"},
            )

        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        from contracts.validator import data_contracts

        result = data_contracts.validate(df, contract_def)

        now = now_iso()
        val_id = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO ContractValidation (id,contractId,tableId,valid,score,violations,totalChecks,passedChecks,failedChecks,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    val_id,
                    cid,
                    table_id,
                    1 if result.get("valid") else 0,
                    result.get("score", 100.0),
                    safe_json_dumps(result.get("violations", [])),
                    result.get("total_checks", 0),
                    result.get("passed_checks", 0),
                    result.get("failed_checks", 0),
                    now,
                ),
            )
            await db.execute(
                "UPDATE DataContract SET lastValidated=?, lastScore=?, updatedAt=? WHERE id=?",
                (now, result.get("score", 100.0), now, cid),
            )

        result["id"] = val_id
        result["contractId"] = cid
        result["tableId"] = table_id
        return _sanitize_for_json(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/contracts/{cid}/validations")
async def get_contract_validations(cid: str, limit: int = 20):
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                "SELECT * FROM ContractValidation WHERE contractId=? ORDER BY createdAt DESC LIMIT ?",
                (cid, limit),
            )
            for r in rows:
                if isinstance(r.get("violations"), str):
                    try:
                        r["violations"] = json.loads(r["violations"])
                    except:
                        pass
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/contracts/{cid}")
async def delete_contract(cid: str):
    try:
        async with get_db() as db:
            await db.execute(
                "DELETE FROM ContractValidation WHERE contractId=?", (cid,)
            )
            await db.execute("DELETE FROM DataContract WHERE id=?", (cid,))
            return {"message": "Deleted", "id": cid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# QUALITY TREND FORECASTING (P2)
# ═══════════════════════════════════════════════


def _generate_profile_scores(tbl, days=14):
    """Generate synthetic quality score history from table profile data.
    Used as fallback when there aren't enough QualityCheck records."""
    import random

    base_score = tbl.get("qualityScore", 100.0) if tbl else 100.0
    if base_score is None or base_score == 0:
        # No real score yet — estimate from profile data
        base_score = 85.0
    base_score = float(base_score)
    # Clamp base score to reasonable range
    base_score = max(20, min(100, base_score))
    freshness = tbl.get("freshnessStatus", "fresh") if tbl else "fresh"
    row_count = tbl.get("rowCount", 0) if tbl else 0
    col_count = tbl.get("columnCount", 0) if tbl else 0
    # Adjust base score based on data characteristics
    if row_count > 0 and col_count > 0:
        base_score = max(base_score, 70.0)
    # Fresh tables tend to have higher scores; stale tables tend to degrade
    if freshness == "stale":
        drift = -0.8
    else:
        drift = -0.15
    now = datetime.utcnow()
    scores = []
    for i in range(days):
        day = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        noise = random.uniform(-1.5, 1.5)
        day_score = base_score + drift * (i - days // 2) + noise
        day_score = max(10, min(100, round(day_score, 1)))
        scores.append({"date": day, "score": day_score})
    return scores


def _build_forecast_response(
    table_id, table_name, historical_scores, periods=7, method="quality_checks"
):
    """Build a unified forecast response from historical scores using the forecasting engine."""
    from forecasting.engine import quality_forecast

    # Clamp all historical scores to 0-100 before forecasting
    for h in historical_scores:
        h["score"] = max(0, min(100, float(h["score"])))
    result = quality_forecast.forecast(historical_scores, periods=periods)
    result["tableId"] = table_id
    result["tableName"] = table_name
    result["method"] = method
    result["historical"] = historical_scores
    # Fix numpy types that FastAPI can't serialize
    if "will_degrade" in result:
        result["will_degrade"] = bool(result["will_degrade"])
    if "current_score" in result:
        result["current_score"] = max(0, min(100, float(result["current_score"])))
    if "predicted_score_7d" in result:
        result["predicted_score_7d"] = max(
            0, min(100, float(result["predicted_score_7d"]))
        )
    if "predicted_change" in result:
        result["predicted_change"] = float(result["predicted_change"])
    # Clamp all forecast points to 0-100 range
    for key in ("exponential_smoothing", "linear_trend"):
        if key in result.get("forecasts", {}):
            for pt in result["forecasts"][key]:
                if "predicted_score" in pt:
                    pt["predicted_score"] = max(
                        0, min(100, float(pt["predicted_score"]))
                    )
    return result


@app.post("/api/forecast/{tableId}")
async def generate_forecast(tableId: str, request: Request):
    try:
        body = (
            await request.json()
            if request.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        periods = body.get("periods", 7)

        async with get_db() as db:
            # Resolve table ID or name
            tbl = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tableId,))
            if not tbl:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tableId,)
                )
            if not tbl:
                return JSONResponse(
                    status_code=404, content={"error": f"Table '{tableId}' not found"}
                )
            resolved_id = tbl["id"]
            table_name = tbl["name"]

            # 1) Try QualityCheck history
            checks = await query_all(
                db,
                """SELECT qc.createdAt, qc.score FROM QualityCheck qc
                   JOIN QualityRule qr ON qc.ruleId = qr.id
                   JOIN Dataset ds ON qr.datasetId = ds.id
                   JOIN "Table" t ON t.name = ds.name
                   WHERE t.id=? ORDER BY qc.createdAt ASC LIMIT 100""",
                (resolved_id,),
            )

            # 2) Try DQTestResult history
            if len(checks) < 3:
                test_results = await query_all(
                    db,
                    """SELECT dtr.timestamp as createdAt, dtr.score FROM DQTestResult dtr
                       JOIN DQTest dt ON dtr.testId = dt.id
                       WHERE dt.tableId=? ORDER BY dtr.timestamp ASC LIMIT 100""",
                    (resolved_id,),
                )
                if len(test_results) >= 3:
                    checks = test_results

        # Build historical scores
        if len(checks) >= 3:
            historical_scores = []
            for c in checks:
                ts = c.get("createdAt", c.get("timestamp", ""))
                date_str = (
                    ts[:10] if isinstance(ts, str) and len(ts) >= 10 else str(ts)[:10]
                )
                historical_scores.append(
                    {"date": date_str, "score": c.get("score", 100)}
                )
            result = _build_forecast_response(
                resolved_id, table_name, historical_scores, periods, "quality_checks"
            )
        else:
            # 3) Fallback: generate from profile + table metadata
            historical_scores = _generate_profile_scores(tbl, days=14)
            result = _build_forecast_response(
                resolved_id, table_name, historical_scores, periods, "profile_estimate"
            )
            result["note"] = (
                "Forecast based on table profile estimates. Run quality checks for more accurate predictions."
            )

        # Update table quality score
        now = now_iso()
        async with get_db() as db:
            await db.execute(
                'UPDATE "Table" SET qualityScore=?, updatedAt=? WHERE id=?',
                (
                    historical_scores[-1]["score"] if historical_scores else 100,
                    now,
                    resolved_id,
                ),
            )

        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/forecast/{tableId}")
async def get_forecast(tableId: str, periods: int = 7):
    """Get forecast data for a table — resolves name or UUID, uses QualityCheck history,
    falls back to DQTestResult, then profile-based estimation."""
    try:
        async with get_db() as db:
            # Resolve table ID or name
            tbl = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tableId,))
            if not tbl:
                tbl = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tableId,)
                )
            if not tbl:
                return JSONResponse(
                    status_code=404, content={"error": f"Table '{tableId}' not found"}
                )
            resolved_id = tbl["id"]
            table_name = tbl["name"]

            # 1) Try QualityCheck history
            checks = await query_all(
                db,
                """SELECT qc.createdAt, qc.score FROM QualityCheck qc
                   JOIN QualityRule qr ON qc.ruleId = qr.id
                   JOIN Dataset ds ON qr.datasetId = ds.id
                   JOIN "Table" t ON t.name = ds.name
                   WHERE t.id=? ORDER BY qc.createdAt ASC LIMIT 100""",
                (resolved_id,),
            )

            # 2) Try DQTestResult history
            if len(checks) < 3:
                test_results = await query_all(
                    db,
                    """SELECT dtr.timestamp as createdAt, dtr.score FROM DQTestResult dtr
                       JOIN DQTest dt ON dtr.testId = dt.id
                       WHERE dt.tableId=? ORDER BY dtr.timestamp ASC LIMIT 100""",
                    (resolved_id,),
                )
                if len(test_results) >= 3:
                    checks = test_results

        # Build historical scores
        if len(checks) >= 3:
            historical_scores = []
            for c in checks:
                ts = c.get("createdAt", c.get("timestamp", ""))
                date_str = (
                    ts[:10] if isinstance(ts, str) and len(ts) >= 10 else str(ts)[:10]
                )
                historical_scores.append(
                    {"date": date_str, "score": c.get("score", 100)}
                )
            result = _build_forecast_response(
                resolved_id, table_name, historical_scores, periods, "quality_checks"
            )
            return result

        # 3) Profile-based estimation fallback
        historical_scores = _generate_profile_scores(tbl, days=14)
        result = _build_forecast_response(
            resolved_id, table_name, historical_scores, periods, "profile_estimate"
        )
        result["note"] = (
            "Forecast based on table profile estimates. Run quality checks for more accurate predictions."
        )
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/forecast/{tableId}")
async def get_forecast(tableId: str, periods: int = 7):
    """Get forecast data for a table. Tries forecasting module first, falls back to pandas SMA on table data, or empty result."""
    try:
        async with get_db() as db:
            tbl = await query_one(db, 'SELECT name FROM "Table" WHERE id=?', (tableId,))
            table_name = tbl["name"] if tbl else tableId

        # Try forecasting module with historical check data
        try:
            async with get_db() as db:
                checks = await query_all(
                    db,
                    """SELECT qc.createdAt, qc.score FROM QualityCheck qc
                       JOIN QualityRule qr ON qc.ruleId = qr.id
                       JOIN Dataset ds ON qr.datasetId = ds.id
                       JOIN "Table" t ON t.name = ds.name
                       WHERE t.id=? ORDER BY qc.createdAt ASC LIMIT 100""",
                    (tableId,),
                )

            if len(checks) < 3:
                async with get_db() as db:
                    test_results = await query_all(
                        db,
                        """SELECT dtr.timestamp as createdAt, dtr.score FROM DQTestResult dtr
                           JOIN DQTest dt ON dtr.testId = dt.id
                           WHERE dt.tableId=? ORDER BY dtr.timestamp ASC LIMIT 100""",
                        (tableId,),
                    )
                    if len(test_results) >= 3:
                        checks = test_results

            if len(checks) >= 3:
                historical_scores = []
                for c in checks:
                    ts = c.get("createdAt", c.get("timestamp", ""))
                    if isinstance(ts, str) and len(ts) >= 10:
                        date_str = ts[:10]
                    else:
                        date_str = str(ts)[:10]
                    historical_scores.append(
                        {"date": date_str, "score": c.get("score", 100)}
                    )

                from forecasting.engine import quality_forecast

                result = quality_forecast.forecast(historical_scores, periods=periods)
                result["tableId"] = tableId
                result["tableName"] = table_name
                return result
        except Exception:
            pass  # Fall through to pandas SMA fallback

        # Fallback: simple moving average using pandas on actual table data
        df = load_dataframe(tableId)
        if df is None or len(df) == 0:
            return {
                "tableId": tableId,
                "tableName": table_name,
                "forecast": [],
                "message": "No data available for forecasting",
            }

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            return {
                "tableId": tableId,
                "tableName": table_name,
                "forecast": [],
                "message": "No numeric columns available for forecasting",
            }

        forecast_col = numeric_cols[0]
        series = df[forecast_col].dropna()

        if len(series) < 3:
            return {
                "tableId": tableId,
                "tableName": table_name,
                "forecast": [],
                "message": "Not enough data points for forecasting (need at least 3)",
            }

        window = min(3, len(series))
        sma = series.rolling(window=window).mean().dropna()
        last_sma = float(sma.iloc[-1]) if len(sma) > 0 else float(series.iloc[-1])

        forecast_points = []
        if len(sma) >= 2:
            trend = (float(sma.iloc[-1]) - float(sma.iloc[0])) / len(sma)
        else:
            trend = 0

        base_date = datetime.utcnow()
        historical = []
        for i, val in enumerate(sma.tail(14)):
            date = (base_date - timedelta(days=14 - i)).strftime("%Y-%m-%d")
            historical.append({"date": date, "value": _sanitize_for_json(val)})

        for i in range(1, periods + 1):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            predicted = last_sma + trend * i
            forecast_points.append(
                {
                    "date": date,
                    "predicted": round(float(predicted), 2),
                    "lower": round(float(predicted * 0.95), 2),
                    "upper": round(float(predicted * 1.05), 2),
                }
            )

        return _sanitize_for_json(
            {
                "tableId": tableId,
                "tableName": table_name,
                "column": forecast_col,
                "method": "simple_moving_average",
                "window": window,
                "historical": historical,
                "forecast": forecast_points,
                "lastValue": float(series.iloc[-1]),
                "trend": round(float(trend), 4),
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# SQL PLAYGROUND (P3) — Multi-Database Support
# ═══════════════════════════════════════════════

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "db"))


def _resolve_db_path(database: str) -> str:
    """Resolve a database name to its full file path. Only .db files in DB_DIR allowed."""
    if not database:
        return DB_PATH
    # Sanitize: only allow alphanumeric, underscore, hyphen
    safe_name = "".join(c for c in database if c.isalnum() or c in ("_", "-"))
    if not safe_name:
        return DB_PATH
    candidate = os.path.join(DB_DIR, f"{safe_name}.db")
    # Ensure the resolved path is still inside DB_DIR (no path traversal)
    if os.path.abspath(candidate).startswith(os.path.abspath(DB_DIR)):
        if os.path.exists(candidate):
            return candidate
        # Special case: if database is 'uploaded_data' and the file doesn't exist yet,
        # create an empty database so the user can query it
        if safe_name == "uploaded_data":
            os.makedirs(DB_DIR, exist_ok=True)
            import sqlite3 as _sq

            conn = _sq.connect(candidate)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO _meta (key, value) VALUES (?, ?)",
                ("created_by", "dataguard"),
            )
            conn.commit()
            conn.close()
            return candidate
    return DB_PATH


@app.get("/api/sql/databases")
async def list_databases():
    """List all available SQLite databases in the db/ directory."""
    try:
        databases = []
        os.makedirs(DB_DIR, exist_ok=True)
        for fname in sorted(os.listdir(DB_DIR)):
            if fname.endswith(".db"):
                db_path = os.path.join(DB_DIR, fname)
                db_name = fname[:-3]  # strip .db
                size_bytes = os.path.getsize(db_path)
                # Get table count and names
                try:
                    import sqlite3 as _sq

                    conn = _sq.connect(db_path)
                    cur = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY name"
                    )
                    tables = [
                        r[0]
                        for r in cur.fetchall()
                        if r[0] not in DATAGUARD_SYSTEM_TABLES
                    ]
                    conn.close()
                except Exception:
                    tables = []
                # Skip databases that only contain system tables
                if not tables and db_name == "custom":
                    continue
                databases.append(
                    {
                        "name": db_name,
                        "fileName": fname,
                        "sizeBytes": size_bytes,
                        "sizeMB": round(size_bytes / (1024 * 1024), 2),
                        "tableCount": len(tables),
                        "tables": tables,
                    }
                )
        return {"databases": databases, "total": len(databases)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/sql/tables")
async def list_sql_tables(database: str = ""):
    """List tables and their schemas for a given database."""
    try:
        db_path = _resolve_db_path(database)
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get all tables
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY name"
            )
            table_names = [
                r["name"]
                for r in await cursor.fetchall()
                if r["name"] not in DATAGUARD_SYSTEM_TABLES
            ]
            await cursor.close()

            tables = []
            for tname in table_names:
                # Get column info
                cur2 = await db.execute(f'PRAGMA table_info("{tname}")')
                cols = await cur2.fetchall()
                columns = []
                for col in cols:
                    columns.append(
                        {
                            "cid": col["cid"],
                            "name": col["name"],
                            "type": col["type"],
                            "notnull": bool(col["notnull"]),
                            "defaultValue": col["dflt_value"],
                            "primaryKey": bool(col["pk"]),
                        }
                    )
                await cur2.close()

                # Get row count
                cur3 = await db.execute(f'SELECT COUNT(*) as cnt FROM "{tname}"')
                row = await cur3.fetchone()
                row_count = row["cnt"] if row else 0
                await cur3.close()

                tables.append(
                    {
                        "name": tname,
                        "columns": columns,
                        "columnCount": len(columns),
                        "rowCount": row_count,
                    }
                )

            db_name = os.path.basename(db_path).replace(".db", "")
            return {"database": db_name, "tables": tables, "total": len(tables)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/sql/table-preview")
async def preview_table_data(database: str = "", table: str = "", limit: int = 50):
    """Preview actual row data for a specific table in a database.
    Returns columns info + first N rows of data."""
    try:
        if not table:
            return JSONResponse(
                status_code=400, content={"error": "table parameter is required"}
            )

        # Block access to DataGuard internal system tables
        if table in DATAGUARD_SYSTEM_TABLES:
            return JSONResponse(
                status_code=404, content={"error": f"Table '{table}' not found"}
            )

        db_path = _resolve_db_path(database)
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Verify table exists
            cur = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=? AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\'",
                (table,),
            )
            if not await cur.fetchone():
                await cur.close()
                return JSONResponse(
                    status_code=404, content={"error": f"Table '{table}' not found"}
                )
            await cur.close()

            # Get column info
            cur2 = await db.execute(f'PRAGMA table_info("{table}")')
            cols = await cur2.fetchall()
            columns = []
            for col in cols:
                columns.append(
                    {
                        "cid": col["cid"],
                        "name": col["name"],
                        "type": col["type"],
                        "notnull": bool(col["notnull"]),
                        "defaultValue": col["dflt_value"],
                        "primaryKey": bool(col["pk"]),
                    }
                )
            await cur2.close()

            # Get total row count
            cur3 = await db.execute(f'SELECT COUNT(*) as cnt FROM "{table}"')
            total_row = await cur3.fetchone()
            total_rows = total_row["cnt"] if total_row else 0
            await cur3.close()

            # Get actual data rows (limited)
            safe_limit = max(1, min(limit, 10000))
            cur4 = await db.execute(f'SELECT * FROM "{table}" LIMIT ?', (safe_limit,))
            rows_raw = await cur4.fetchall()
            result_columns = (
                [desc[0] for desc in cur4.description]
                if cur4.description
                else [c["name"] for c in columns]
            )
            rows = [_sanitize_for_json(dict(row)) for row in rows_raw]
            await cur4.close()

            db_name = os.path.basename(db_path).replace(".db", "")
            return {
                "database": db_name,
                "table": table,
                "columns": columns,
                "resultColumns": result_columns,
                "rows": rows,
                "rowCount": len(rows),
                "totalRows": total_rows,
                "truncated": len(rows) >= safe_limit,
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/sql/all-tables-preview")
async def all_tables_preview(database: str = "", limit: int = 20):
    """Preview data for ALL tables in a database. Returns a map of table name → {columns, rows, totalRows}."""
    try:
        db_path = _resolve_db_path(database)
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get all tables
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY name"
            )
            table_names = [
                r["name"]
                for r in await cursor.fetchall()
                if r["name"] not in DATAGUARD_SYSTEM_TABLES
            ]
            await cursor.close()

            safe_limit = max(1, min(limit, 100))
            tables_data = []

            for tname in table_names:
                # Column info
                cur2 = await db.execute(f'PRAGMA table_info("{tname}")')
                cols = await cur2.fetchall()
                columns = []
                for col in cols:
                    columns.append(
                        {
                            "cid": col["cid"],
                            "name": col["name"],
                            "type": col["type"],
                            "notnull": bool(col["notnull"]),
                            "defaultValue": col["dflt_value"],
                            "primaryKey": bool(col["pk"]),
                        }
                    )
                await cur2.close()

                # Total rows
                cur3 = await db.execute(f'SELECT COUNT(*) as cnt FROM "{tname}"')
                total_row = await cur3.fetchone()
                total_rows = total_row["cnt"] if total_row else 0
                await cur3.close()

                # Sample data rows
                cur4 = await db.execute(
                    f'SELECT * FROM "{tname}" LIMIT ?', (safe_limit,)
                )
                rows_raw = await cur4.fetchall()
                result_columns = (
                    [desc[0] for desc in cur4.description] if cur4.description else []
                )
                rows = [_sanitize_for_json(dict(row)) for row in rows_raw]
                await cur4.close()

                tables_data.append(
                    {
                        "name": tname,
                        "columns": columns,
                        "resultColumns": result_columns,
                        "rows": rows,
                        "rowCount": len(rows),
                        "totalRows": total_rows,
                        "truncated": len(rows) >= safe_limit,
                    }
                )

            db_name = os.path.basename(db_path).replace(".db", "")
            return {
                "database": db_name,
                "tables": tables_data,
                "total": len(tables_data),
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# UPLOADED TABLE DATA PREVIEW
# Reads data from CSV files saved by the ingest endpoint,
# NOT from SQLite tables (which only hold metadata).
# ═══════════════════════════════════════════════


@app.get("/api/uploaded-tables-preview")
async def uploaded_tables_preview(limit: int = 50):
    """Preview data for ALL user-uploaded tables. Reads from CSV files."""
    try:
        async with get_db() as db:
            rows = await query_all(
                db,
                'SELECT id, name, fullyQualifiedName, columnCount, rowCount, columns FROM "Table" ORDER BY name',
            )

        safe_limit = max(1, min(limit, 10000))
        tables_data = []

        for tbl in rows:
            table_id = tbl["id"]
            table_name = tbl["name"]
            total_rows = tbl["rowCount"] or 0
            col_count = tbl["columnCount"] or 0

            # Parse column definitions from metadata
            col_defs = []
            try:
                col_defs = (
                    json.loads(tbl["columns"])
                    if isinstance(tbl["columns"], str)
                    else (tbl["columns"] or [])
                )
            except Exception:
                col_defs = []

            columns = []
            for idx, col in enumerate(col_defs):
                columns.append(
                    {
                        "cid": idx,
                        "name": col.get("name", f"col_{idx}"),
                        "type": col.get("type", "TEXT"),
                        "notnull": not col.get("nullable", True),
                        "defaultValue": None,
                        "primaryKey": False,
                    }
                )

            # Try to load actual data from CSV files
            df = load_dataframe(table_id)
            data_rows = []
            result_columns = [c["name"] for c in columns]

            if df is not None and len(df) > 0:
                # Use actual column names from DataFrame
                result_columns = list(df.columns.astype(str))
                # Rebuild columns info from DataFrame
                columns = []
                for idx, col_name in enumerate(result_columns):
                    dtype_str = str(df[col_name].dtype)
                    if "int" in dtype_str:
                        ctype = "INTEGER"
                    elif "float" in dtype_str:
                        ctype = "REAL"
                    elif "bool" in dtype_str:
                        ctype = "BOOLEAN"
                    else:
                        ctype = "TEXT"
                    columns.append(
                        {
                            "cid": idx,
                            "name": str(col_name),
                            "type": ctype,
                            "notnull": False,
                            "defaultValue": None,
                            "primaryKey": False,
                        }
                    )

                sample_df = df.head(safe_limit)
                total_rows = len(df)
                data_rows = _sanitize_for_json(sample_df.to_dict(orient="records"))

            tables_data.append(
                {
                    "id": table_id,
                    "name": table_name,
                    "fullyQualifiedName": tbl.get("fullyQualifiedName", table_name),
                    "columns": columns,
                    "resultColumns": result_columns,
                    "rows": data_rows,
                    "rowCount": len(data_rows),
                    "totalRows": total_rows,
                    "truncated": len(data_rows) >= safe_limit
                    and total_rows > safe_limit,
                }
            )

        return {"tables": tables_data, "total": len(tables_data)}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/sql/query")
async def execute_sql_query(request: Request):
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        database = body.get("database", "").strip()
        if not query:
            return JSONResponse(status_code=400, content={"error": "query required"})

        # Resolve which database to query
        db_path = _resolve_db_path(database)

        # Basic safety: only allow SELECT statements
        upper_query = query.strip().upper()
        if (
            not upper_query.startswith("SELECT")
            and not upper_query.startswith("PRAGMA")
            and not upper_query.startswith("WITH")
        ):
            return JSONResponse(
                status_code=403,
                content={"error": "Only SELECT / PRAGMA / WITH queries are allowed"},
            )

        # Block dangerous operations
        forbidden = [
            "DROP",
            "DELETE",
            "INSERT",
            "UPDATE",
            "ALTER",
            "CREATE",
            "ATTACH",
            "DETACH",
        ]
        for word in forbidden:
            if word in upper_query.split():
                return JSONResponse(
                    status_code=403,
                    content={"error": f"{word} operations are not allowed"},
                )

        # Block queries referencing DataGuard internal system tables
        # Only check names that appear after FROM or JOIN (as SQL table references)
        # to avoid false positives with SQL keywords like TABLE, TAG etc.
        _from_join_pattern = re.compile(
            r'(?:FROM|JOIN)\s+["\']?(\w+)["\']?', re.IGNORECASE
        )
        for match in _from_join_pattern.finditer(query):
            referenced_table = match.group(1)
            if referenced_table in DATAGUARD_SYSTEM_TABLES:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": f"Access to internal table '{referenced_table}' is not allowed"
                    },
                )

        start_time = time.time()
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query)
            rows = await cursor.fetchmany(1000)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            result = [_sanitize_for_json(dict(row)) for row in rows]
            await cursor.close()
        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        db_name = os.path.basename(db_path).replace(".db", "")
        return {
            "success": True,
            "columns": columns,
            "rows": result,
            "rowCount": len(result),
            "truncated": len(result) >= 1000,
            "database": db_name,
            "executionTimeMs": elapsed_ms,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── AI Natural Language → SQL ─────────────────────────────────────────────────

NL2SQL_SYSTEM = """You are an expert SQL assistant for a SQLite database. Your job is to convert the user's natural language question into a valid SQLite SQL query.

RULES:
1. Generate ONLY a single valid SQLite SELECT query
2. Use the exact table and column names from the provided schema
3. Add appropriate WHERE, JOIN, GROUP BY, ORDER BY, LIMIT clauses as needed
4. Use SQLite syntax (not MySQL/PostgreSQL)
5. For text matching, use LIKE with '%' wildcards for partial matches
6. For dates, SQLite uses string comparison (format: YYYY-MM-DD)
7. Always add LIMIT 100 if the user doesn't specify a row limit
8. If the question is ambiguous, make reasonable assumptions
9. Only generate SELECT queries — never INSERT, UPDATE, DELETE, DROP, etc.
10. If you cannot generate a valid query, respond with: {"error": "reason"}

CRITICAL RULES FOR COLUMN MAPPING:
11. Column names may be generic (e.g. Unnamed_0, Unnamed_1, etc.). Infer each column's ROLE from the sample rows and distinct values provided in the schema. For example, if a column contains values like 'm','f' it likely represents sex/gender; if it contains numbers 18-80 it likely represents age.
12. When the user mentions a concept like "sex", "gender", "age", "name", etc. you must map it to the correct column by examining sample data and distinct values — NOT by matching the concept word to column names.
13. NEVER use a concept word (like 'Sex', 'Age', 'Name') as a literal value in a WHERE clause. For example, if user asks for "m sex", the correct SQL is WHERE column_name = 'm' (where column_name is the column that contains m/f values), NOT WHERE column_name = 'Sex'.
14. Use case-insensitive matching for text values in WHERE clauses: use LOWER(column) = LOWER('value') or column LIKE 'value' (SQLite LIKE is case-insensitive for ASCII by default). This handles cases where user says 'M' but data stores 'm'.
15. When multiple sample rows are provided, examine ALL of them to understand the data patterns before generating the query.

RESPONSE FORMAT — respond with ONLY valid JSON:
{"sql": "YOUR SQL QUERY HERE", "explanation": "Brief explanation of what the query does"}

DO NOT wrap the JSON in markdown code blocks. DO NOT add any text before or after the JSON."""


def _build_schema_context(
    database: str, max_tables: int = 10, max_chars: int = 8000
) -> str:
    """Build a compact schema description for the LLM prompt.
    Includes multiple sample rows AND distinct values for low-cardinality columns
    so the LLM can infer column roles even when names are generic (e.g. Unnamed_0).
    Limits output size to avoid HTTP 413 errors with token-limited LLMs.
    """
    db_path = _resolve_db_path(database)
    schema_parts = []
    total_chars = 0
    try:
        import sqlite3 as _sq

        conn = _sq.connect(db_path)
        # Get all tables
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\' ORDER BY name"
        )
        table_names = [
            r[0] for r in cur.fetchall() if r[0] not in DATAGUARD_SYSTEM_TABLES
        ]
        # Limit the number of tables to avoid huge prompts
        tables_to_process = table_names[:max_tables]

        for tname in tables_to_process:
            # Get columns
            cur2 = conn.execute(f'PRAGMA table_info("{tname}")')
            cols = cur2.fetchall()
            col_names_list = []
            col_descs = []
            for col in cols:
                col_name = col[1]
                col_type = col[2] or "ANY"
                pk = " PRIMARY KEY" if col[5] else ""
                nn = " NOT NULL" if col[3] else ""
                col_descs.append(f"{col_name}({col_type}){pk}{nn}")
                col_names_list.append(col_name)
            cur2.close()

            # Get 3 sample rows (reduced from 5 to save space)
            sample_lines = []
            try:
                cur3 = conn.execute(f'SELECT * FROM "{tname}" LIMIT 3')
                rows = cur3.fetchall()
                if rows:
                    col_names = [d[0] for d in cur3.description]
                    for i, row in enumerate(rows):
                        sample_pairs = [
                            f"{c}={v}" for c, v in zip(col_names, row) if v is not None
                        ]
                        sample_lines.append(
                            f"  Row{i+1}: {', '.join(sample_pairs[:10])}"
                        )
                cur3.close()
            except Exception:
                pass
            sample_str = (
                "\n".join(sample_lines) if sample_lines else "  (no sample data)"
            )

            # Get distinct values for low-cardinality columns (<=15 unique values)
            distinct_lines = []
            try:
                for cname in col_names_list:
                    try:
                        cur_d = conn.execute(
                            f'SELECT DISTINCT "{cname}" FROM "{tname}" LIMIT 16'
                        )
                        distinct_vals = [
                            str(r[0]) for r in cur_d.fetchall() if r[0] is not None
                        ]
                        cur_d.close()
                        if 0 < len(distinct_vals) <= 15:
                            vals_str = ", ".join(distinct_vals[:10])
                            distinct_lines.append(f"  {cname}=[{vals_str}]")
                    except Exception:
                        pass
            except Exception:
                pass
            distinct_str = " | ".join(distinct_lines) if distinct_lines else ""

            # Get row count
            try:
                cur4 = conn.execute(f'SELECT COUNT(*) FROM "{tname}"')
                cnt = cur4.fetchone()[0]
                cur4.close()
                count_str = f"  (~{cnt} rows)"
            except Exception:
                count_str = ""

            # Build compact format
            table_header = f"TABLE {tname} ({', '.join(col_descs[:15])}){count_str}"
            table_block = f"{table_header}\nSample:\n{sample_str}"
            if distinct_str:
                table_block += f"\nValueHints: {distinct_str}"

            # Check size limit
            if total_chars + len(table_block) > max_chars:
                remaining = len(table_names) - len(schema_parts)
                if remaining > 0:
                    schema_parts.append(
                        f"... and {remaining} more tables (truncated to fit context limit)"
                    )
                break

            schema_parts.append(table_block)
            total_chars += len(table_block)

        conn.close()
    except Exception as e:
        schema_parts.append(f"Error reading schema: {e}")

    return "\n\n".join(schema_parts)


def _keyword_nl2sql(question: str, database: str) -> dict:
    """Fallback: simple keyword-based NL→SQL when no LLM available.
    Now inspects column distinct values across ALL tables to find the best match,
    and builds smart WHERE clauses with column semantic inference.
    """
    q = question.lower().strip()
    db_path = _resolve_db_path(database)

    # Semantic mapping: value -> list of concept words that give context
    semantic_map = {
        "m": ["sex", "gender", "male"],
        "f": ["sex", "gender", "female"],
        "male": ["sex", "gender"],
        "female": ["sex", "gender"],
        "hindu": ["religion", "faith", "community"],
        "muslim": ["religion", "faith", "community"],
        "christian": ["religion", "faith", "community"],
        "sikh": ["religion", "faith", "community"],
        "buddhist": ["religion", "faith", "community"],
        "jain": ["religion", "faith", "community"],
        "h": ["religion", "hindu"],
        "yes": ["yes", "true", "1"],
        "no": ["no", "false", "0"],
    }

    def _infer_column_category(values):
        """Return the most likely category for a column based on its distinct values."""
        category_scores = {}
        for v in values:
            hints = semantic_map.get(v.lower(), [])
            for hint in hints:
                category_scores[hint] = category_scores.get(hint, 0) + 1
        if not category_scores:
            return None
        return max(category_scores, key=category_scores.get)

    def _score_column_match(cname, distinct_vals, question_lower):
        """Score how well a column matches the user's question (0 = no match, higher = better)."""
        score = 0
        for val in distinct_vals:
            val_lower = val.lower()
            if len(val_lower) <= 2:
                hints = semantic_map.get(val_lower, [])
                for hint in hints:
                    if hint in question_lower:
                        col_category = _infer_column_category(distinct_vals)
                        # Check category alignment with question
                        question_categories = set()
                        for word in question_lower.split():
                            for h_key, h_vals in semantic_map.items():
                                if word in h_vals:
                                    question_categories.update(h_vals)
                        if question_categories and col_category:
                            if col_category in question_categories:
                                score += 10  # Strong match with category alignment
                            else:
                                score += 1  # Weak match, wrong category
                        elif hint in question_lower:
                            score += 5  # Moderate match without category context
            else:
                if val_lower in question_lower.split() or val_lower in question_lower:
                    score += 8  # Direct value match
        # Bonus: if column name contains a keyword from the question
        cname_lower = cname.lower()
        for word in question_lower.split():
            if len(word) > 2 and word in cname_lower:
                score += 3
        return score

    # Get table names AND column/value info for ALL tables
    table_names = []
    table_col_info = {}  # {table_name: [(col_name, [distinct_vals])]}
    table_scores = {}  # {table_name: total_relevance_score}
    try:
        import sqlite3 as _sq

        conn = _sq.connect(db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\'"
        )
        table_names = [r[0] for r in cur.fetchall()]
        for tname in table_names:
            col_info = []
            table_score = 0
            try:
                cur2 = conn.execute(f'PRAGMA table_info("{tname}")')
                cols = cur2.fetchall()
                cur2.close()
                for col in cols:
                    cname = col[1]
                    try:
                        cur_d = conn.execute(
                            f'SELECT DISTINCT "{cname}" FROM "{tname}" LIMIT 16'
                        )
                        distinct_vals = [
                            str(r[0]) for r in cur_d.fetchall() if r[0] is not None
                        ]
                        cur_d.close()
                        if 0 < len(distinct_vals) <= 15:
                            col_info.append((cname, distinct_vals))
                            # Score this column's relevance to the question
                            col_score = _score_column_match(cname, distinct_vals, q)
                            table_score += col_score
                    except Exception:
                        pass
            except Exception:
                pass
            table_col_info[tname] = col_info
            # Also score by table name matching
            tname_lower = tname.lower()
            for word in q.split():
                if len(word) > 2 and word in tname_lower:
                    table_score += 5
            table_scores[tname] = table_score
        conn.close()
    except Exception:
        pass

    # Pick the BEST table: highest score wins, with name match as tiebreaker
    target_table = ""
    if table_scores:
        max_score = max(table_scores.values())
        if max_score > 0:
            # Pick the table with the highest relevance score
            best_tables = [t for t, s in table_scores.items() if s == max_score]
            target_table = best_tables[0]
        else:
            # No semantic match found — try to find table by name mention
            for tname in table_names:
                if tname.lower() in q:
                    target_table = tname
                    break
            # If still no match, use the first table
            if not target_table and table_names:
                target_table = table_names[0]
    elif table_names:
        target_table = table_names[0]

    if not target_table:
        return {
            "error": "No tables found in the selected database",
            "sql": "",
            "explanation": "",
            "generationMethod": "keyword",
        }

    # Build a basic query based on keywords
    sql = f'SELECT * FROM "{target_table}" LIMIT 100'
    explanation = f"Shows all rows from the {target_table} table (limited to 100 rows)."

    conditions = []

    # Detect common patterns
    if "count" in q or "how many" in q or "number of" in q:
        if "by" in q or "per" in q or "each" in q or "group" in q:
            sql = (
                f'SELECT *, COUNT(*) as count FROM "{target_table}" GROUP BY * LIMIT 50'
            )
            explanation = f"Counts records in {target_table}, grouped by values."
        else:
            sql = f'SELECT COUNT(*) as total_count FROM "{target_table}"'
            explanation = f"Counts total rows in {target_table}."
    elif "top" in q or "highest" in q or "maximum" in q or "most" in q or "best" in q:
        sql = f'SELECT * FROM "{target_table}" ORDER BY rowid DESC LIMIT 10'
        explanation = f"Shows the top records from {target_table}, ordered by rowid."
    elif "average" in q or "avg" in q or "mean" in q:
        sql = f'SELECT *, AVG(*) as avg_value FROM "{target_table}" LIMIT 50'
        explanation = f"Calculates averages for {target_table}."
    elif "distinct" in q or "unique" in q or "different" in q:
        sql = f'SELECT DISTINCT * FROM "{target_table}" LIMIT 100'
        explanation = f"Shows unique records from {target_table}."

    # Smart WHERE clause: scan columns for matching values from the user's question
    col_info = table_col_info.get(target_table, [])

    for cname, distinct_vals in col_info:
        matched_val = None
        col_category = _infer_column_category(distinct_vals)
        for val in distinct_vals:
            val_lower = val.lower()
            if len(val_lower) <= 2:
                # Short values are ambiguous — require semantic hint
                hints = semantic_map.get(val_lower, [])
                for hint in hints:
                    if hint in q:
                        if col_category and hint in semantic_map.get(val_lower, []):
                            question_categories = set()
                            for word in q.split():
                                for h_key, h_vals in semantic_map.items():
                                    if word in h_vals:
                                        question_categories.update(h_vals)
                            if question_categories:
                                if col_category in question_categories:
                                    matched_val = val
                                    break
                            else:
                                matched_val = val
                                break
                if matched_val:
                    break
            else:
                # Longer values can be matched directly
                if val_lower in q.split() or val_lower in q:
                    matched_val = val
                    break
        if matched_val is not None:
            # Use case-insensitive matching with LOWER()
            escaped_val = matched_val.replace("'", "''")
            conditions.append(f"LOWER(\"{cname}\") = LOWER('{escaped_val}')")

    # Also try to add WHERE clause for numeric values in the question
    for word in q.split():
        if word.isdigit():
            conditions.append(f'CAST(rowid AS TEXT) LIKE "%{word}%"')

    # Apply conditions to the SQL
    if conditions:
        where_clause = " AND ".join(conditions)
        base_upper = sql.upper()
        if "LIMIT" in base_upper:
            limit_idx = base_upper.rfind("LIMIT")
            sql = sql[:limit_idx].rstrip() + f" WHERE {where_clause} " + sql[limit_idx:]
        else:
            sql = sql + f" WHERE {where_clause}"
        explanation = f"Filters {target_table} where {where_clause}"

    return {
        "sql": sql,
        "explanation": explanation,
        "generationMethod": "keyword",
        "note": "This is a basic query generated without AI. Configure LLM_API_KEY for smarter results.",
    }


@app.post("/api/sql/ai-query")
async def ai_nl_to_sql(request: Request):
    """Convert natural language question to SQL using LLM."""
    try:
        body = await request.json()
        question = body.get("question", "").strip()
        database = body.get("database", "").strip()

        if not question:
            return JSONResponse(
                status_code=400, content={"error": "question is required"}
            )

        # Check if LLM is available
        api_key = os.environ.get("LLM_API_KEY", "")
        if not api_key:
            # Fallback to keyword-based generation
            result = _keyword_nl2sql(question, database or "custom")
            return result

        # Build schema context for the LLM
        schema_context = _build_schema_context(database or "custom")

        user_prompt = f"""DATABASE SCHEMA:
{schema_context}

USER'S QUESTION: {question}

Generate a SQLite SQL query that answers this question. Respond with ONLY valid JSON: {{"sql": "...", "explanation": "..."}}"""

        from llm.client import call_llm, extract_json

        response = call_llm(
            NL2SQL_SYSTEM, user_prompt, temperature=0.1, max_tokens=2048
        )

        if response:
            data = extract_json(response)
            if data and isinstance(data, dict) and data.get("sql"):
                # Validate: only allow SELECT queries
                sql = data["sql"].strip()
                upper_sql = sql.upper()
                if not upper_sql.startswith("SELECT") and not upper_sql.startswith(
                    "WITH"
                ):
                    return {
                        "error": "Generated query is not a SELECT statement",
                        "sql": "",
                        "explanation": data.get("explanation", ""),
                        "generationMethod": "llm",
                    }
                return {
                    "sql": sql,
                    "explanation": data.get("explanation", ""),
                    "generationMethod": "llm",
                }

            # LLM responded but no valid JSON — try to extract SQL from raw text
            # Look for SQL-like patterns
            import re

            sql_match = re.search(
                r"(SELECT\s+.*?;)", response, re.IGNORECASE | re.DOTALL
            )
            if not sql_match:
                sql_match = re.search(
                    r"(SELECT\s+.*?)$", response, re.IGNORECASE | re.DOTALL
                )
            if sql_match:
                extracted_sql = sql_match.group(1).strip().rstrip(";")
                return {
                    "sql": extracted_sql,
                    "explanation": "Generated from AI (extracted from response)",
                    "generationMethod": "llm",
                }

        # LLM failed — fall back to keyword
        result = _keyword_nl2sql(question, database or "custom")
        result["note"] = (
            "LLM was unavailable; using keyword-based fallback. Check LLM configuration."
        )
        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# ADDITIONAL MISSING ENDPOINTS
# ═══════════════════════════════════════════════


@app.get("/api/anomaly")
async def list_anomalies(tableId: Optional[str] = None, limit: Optional[int] = 100):
    """Return anomaly detection results from StatisticalTest table where testType contains 'anomaly'."""
    try:
        async with get_db() as db:
            where, params = [], []
            where.append("testType LIKE ?")
            params.append("%anomaly%")
            if tableId:
                where.append("tableId=?")
                params.append(tableId)
            w = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await query_all(
                db,
                f"SELECT * FROM StatisticalTest {w} ORDER BY createdAt DESC LIMIT ?",
                (*params, min(limit, 500)),
            )
            for r in rows:
                if isinstance(r.get("config"), str):
                    try:
                        r["config"] = json.loads(r["config"])
                    except Exception:
                        pass
                if isinstance(r.get("result"), str):
                    try:
                        r["result"] = json.loads(r["result"])
                    except Exception:
                        pass
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/profile")
async def get_profile(tableId: str = Query(...)):
    """Get profile for a table by tableId query param. Query TableProfile table."""
    try:
        async with get_db() as db:
            row = await query_one(
                db,
                "SELECT * FROM TableProfile WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (tableId,),
            )
            if not row:
                return JSONResponse(
                    status_code=404, content={"error": "No profile found for table"}
                )
            if isinstance(row.get("profileData"), str):
                try:
                    row["profileData"] = json.loads(row["profileData"])
                except Exception:
                    pass
            return row
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/auto-fix/{fix_id}/apply")
async def apply_fix(fix_id: str):
    """Apply an approved fix — actually executes the transform and saves the result."""
    try:
        async with get_db() as db:
            fix = await query_one(db, "SELECT * FROM FixApproval WHERE id=?", (fix_id,))
            if not fix:
                return JSONResponse(
                    status_code=404, content={"error": "Fix proposal not found"}
                )
            if fix["status"] not in ("pending", "approved"):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": f"Fix cannot be applied, current status: {fix['status']}"
                    },
                )

            table_id = fix["tableId"]
            fix_type = fix["fixType"]
            fix_config = (
                json.loads(fix["fixConfig"])
                if isinstance(fix.get("fixConfig"), str)
                else (fix.get("fixConfig") or {})
            )

        # Try to load the dataframe and execute the transform
        try:
            df = load_dataframe(table_id)
        except Exception:
            df = None

        now = now_iso()

        if df is not None and not df.empty:
            try:
                from transformations import get_transformer

                transformer = get_transformer(fix_type)
                result = transformer.transform(df, fix_config)

                if result.success:
                    save_dataframe(table_id, result.df, "csv")
                    async with get_db() as db:
                        await db.execute(
                            "UPDATE FixApproval SET status='applied', appliedAt=?, resultSummary=? WHERE id=?",
                            (
                                now,
                                json.dumps(
                                    {
                                        "success": True,
                                        "message": result.message or "Fix applied",
                                        "rows_affected": getattr(
                                            result, "rows_affected", len(df)
                                        ),
                                        "columns_affected": getattr(
                                            result, "columns_affected", []
                                        ),
                                        "confidence": 0.85,
                                    }
                                ),
                                fix_id,
                            ),
                        )
                    return {
                        "success": True,
                        "message": "Fix applied successfully",
                        "rows_affected": getattr(result, "rows_affected", len(df)),
                        "id": fix_id,
                        "appliedAt": now,
                    }
                else:
                    async with get_db() as db:
                        await db.execute(
                            "UPDATE FixApproval SET status='failed', appliedAt=?, resultSummary=? WHERE id=?",
                            (
                                now,
                                json.dumps(
                                    {
                                        "success": False,
                                        "message": result.message or "Transform failed",
                                    }
                                ),
                                fix_id,
                            ),
                        )
                    return {
                        "success": False,
                        "message": f"Fix failed: {result.message}",
                        "id": fix_id,
                    }
            except Exception as te:
                import traceback

                traceback.print_exc()
                async with get_db() as db:
                    await db.execute(
                        "UPDATE FixApproval SET status='failed', appliedAt=?, resultSummary=? WHERE id=?",
                        (
                            now,
                            json.dumps({"success": False, "message": str(te)}),
                            fix_id,
                        ),
                    )
                return {
                    "success": False,
                    "message": f"Fix execution error: {str(te)}",
                    "id": fix_id,
                }
        else:
            # No data to transform — just mark as applied (status-only update)
            async with get_db() as db:
                await db.execute(
                    "UPDATE FixApproval SET status='applied', appliedAt=?, resultSummary=? WHERE id=?",
                    (
                        now,
                        json.dumps(
                            {
                                "success": True,
                                "message": "Marked as applied (no data to transform)",
                            }
                        ),
                        fix_id,
                    ),
                )
            return {
                "success": True,
                "message": "Fix applied (status updated)",
                "id": fix_id,
                "appliedAt": now,
            }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  DataGuard Python Backend (FastAPI) on port 3001")
    print(f"  Database: {DB_PATH}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=3001)
