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


@app.get("/api/stats")
async def get_stats():
    import traceback

    try:
        async with get_db() as db:
            total_services = await query_scalar(db, "SELECT COUNT(*) FROM Service")
            total_tables = await query_scalar(db, 'SELECT COUNT(*) FROM "Table"')
            total_tests = await query_scalar(db, "SELECT COUNT(*) FROM DQTest")
            total_alerts = await query_scalar(
                db, "SELECT COUNT(*) FROM Alert WHERE status='active'"
            )
            total_teams = await query_scalar(db, "SELECT COUNT(*) FROM Team")

            scores_rows = await query_all(db, 'SELECT qualityScore FROM "Table"')
            scores = [
                r["qualityScore"] for r in scores_rows if r["qualityScore"] is not None
            ]
            avg_score = round(sum(scores) / len(scores), 1) if scores else 100.0

            test_rows = await query_all(db, "SELECT status FROM DQTest")
            test_statuses = [r["status"] for r in test_rows]
            passed = test_statuses.count("success")
            pass_rate = (
                round((passed / len(test_statuses)) * 100, 1)
                if test_statuses
                else 100.0
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

            recent_results = await query_all(
                db,
                "SELECT timestamp, status FROM DQTestResult ORDER BY timestamp DESC LIMIT 1000",
            )
            chart_data = {}
            for r in recent_results:
                ts_val = r["timestamp"]
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
            recent_test_results = sorted(
                [
                    {"date": k, "passed": v["passed"], "failed": v["failed"]}
                    for k, v in chart_data.items()
                ],
                key=lambda x: x["date"],
            )[-14:]

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
            }
    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "totalServices": 0,
            "totalTables": 0,
            "totalTests": 0,
            "totalAlerts": 0,
            "averageQualityScore": 100.0,
            "testsPassRate": 100.0,
            "freshTables": 0,
            "staleTables": 0,
            "totalTeams": 0,
            "recentActivityCount": 0,
            "recentTestResults": [],
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
    """Get actual data rows for a table (for preview)."""
    try:
        # Resolve name to UUID if needed
        resolved_id = tid
        try:
            async with get_db() as db:
                tbl = await query_one(db, 'SELECT * FROM "Table" WHERE id=?', (tid,))
                if not tbl:
                    tbl = await query_one(
                        db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (tid,)
                    )
                if tbl:
                    resolved_id = tbl["id"]
        except Exception:
            pass

        df = load_dataframe(resolved_id)
        if df is None:
            return JSONResponse(status_code=404, content={"error": "No data found"})
        preview = df.head(limit)
        return {
            "columns": preview.columns.tolist(),
            "rows": _sanitize_for_json(preview.to_dict(orient="records")),
            "totalRows": len(df),
            "totalColumns": len(df.columns),
        }
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
                where.append("datasetId=?")
                params.append(datasetId)
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
                ds = await query_one(
                    db, "SELECT name FROM Dataset WHERE id=?", (r["datasetId"],)
                )
                r["dataset"] = {"name": ds["name"]} if ds else {"name": "Unknown"}
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

            # Try REAL execution first
            result = None
            if table:
                df = load_dataframe(table["id"])
                if df is not None:
                    try:
                        result = execute_rule(dict(rule), df, table.get("name", ""))
                    except Exception:
                        result = None

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
    try:
        async with get_db() as db:
            rows = await query_all(
                db, "SELECT * FROM Dataset ORDER BY qualityScore ASC"
            )
            for r in rows:
                r["_count"] = {
                    "rules": await query_scalar(
                        db,
                        "SELECT COUNT(*) FROM QualityRule WHERE datasetId=?",
                        (r["id"],),
                    )
                }
            return rows
    except Exception as e:
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

        async with get_db() as db:
            ds = await query_one(db, "SELECT id FROM Dataset WHERE id=?", (dataset_id,))
            if not ds:
                return JSONResponse(
                    status_code=404, content={"error": "Dataset not found"}
                )

        # Use real LLM generator (falls back to keywords if no API key)
        from llm.rule_generator import generate as generate_rule

        table_name = ""
        columns_info = ""
        async with get_db() as db:
            dataset_row = await query_one(
                db, "SELECT name FROM Dataset WHERE id=?", (dataset_id,)
            )
            if dataset_row:
                table_row = await query_one(
                    db,
                    'SELECT columns FROM "Table" WHERE name=? LIMIT 1',
                    (dataset_row["name"],),
                )
                if table_row:
                    columns_info = table_row["columns"]
                    table_name = dataset_row["name"]

        rule_data = generate_rule(prompt, dataset_id, table_name, columns_info)

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
                    dataset_id,
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
            checks = await query_all(
                db,
                "SELECT * FROM QualityCheck WHERE datasetId=? ORDER BY createdAt DESC LIMIT 20",
                (dataset_id,),
            )
            ds = await query_one(db, "SELECT * FROM Dataset WHERE id=?", (dataset_id,))
        from llm.report_generator import ReportGenerator

        gen = ReportGenerator()
        report = gen.generate(ds or {}, checks)
        return {"success": True, "report": report}
    except Exception as e:
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
            rules = await query_all(
                db,
                "SELECT * FROM QualityRule WHERE datasetId=? AND enabled=1",
                (dataset_id,),
            )
            dataset = await query_one(
                db, "SELECT * FROM Dataset WHERE id=?", (dataset_id,)
            )
            table = None
            if dataset:
                table = await query_one(
                    db, 'SELECT * FROM "Table" WHERE name=? LIMIT 1', (dataset["name"],)
                )
            for rule in rules:
                result = None
                if table:
                    df = load_dataframe(table["id"])
                    if df is not None:
                        try:
                            result = execute_rule(dict(rule), df, table.get("name", ""))
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
                            dataset_id,
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
                                dataset["name"] if dataset else "Unknown",
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
            await db.execute(
                "UPDATE QualityRule SET lastTriggered=? WHERE datasetId=?",
                (now, dataset_id),
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
                r["steps"] = (
                    json.loads(r["steps"])
                    if isinstance(r["steps"], str)
                    else r["steps"]
                )
                r["_count"] = {
                    "runs": await query_scalar(
                        db,
                        "SELECT COUNT(*) FROM PipelineRun WHERE pipelineId=?",
                        (r["id"],),
                    )
                }
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
                    body.get("tableId"),
                    body.get("status", "draft"),
                    now,
                    now,
                ),
            )
            return {"id": pid, "name": body.get("name")}
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
            p["steps"] = (
                json.loads(p["steps"]) if isinstance(p["steps"], str) else p["steps"]
            )
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
        body = (
            await request.json()
            if request.headers.get("content-type", "").startswith("application/json")
            else {}
        )
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

            steps_data = (
                json.loads(p["steps"]) if isinstance(p["steps"], str) else p["steps"]
            )

        from transformations.pipeline import Pipeline, PipelineExecutor

        pipeline = Pipeline(p["id"], p["name"], p.get("description", ""))
        pipeline.steps = []
        for step_data in steps_data:
            from transformations.pipeline import PipelineStep

            step = PipelineStep(
                step_data.get("id", gen_id()[:12]),
                step_data["transform_type"],
                step_data.get("config", {}),
                step_data.get("name", ""),
                step_data.get("condition"),
                step_data.get("next_step"),
            )
            pipeline.steps.append(step)

        executor = PipelineExecutor(table_id)
        result = executor.execute(pipeline)

        run_id = gen_id()
        async with get_db() as db:
            await db.execute(
                """INSERT INTO PipelineRun (id,pipelineId,tableId,status,totalSteps,completedSteps,failedSteps,totalDurationMs,stepResults,finalShape,createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    pid,
                    table_id,
                    "completed" if result.get("success") else "failed",
                    result.get("total_steps", 0),
                    result.get("completed_steps", 0),
                    result.get("failed_steps", 0),
                    result.get("total_duration_ms", 0),
                    safe_json_dumps(result.get("step_results", [])),
                    safe_json_dumps(result.get("final_shape", [])),
                    now,
                ),
            )
            await db.execute(
                "UPDATE Pipeline SET status='executed', updatedAt=? WHERE id=?",
                (now, pid),
            )

        result["run_id"] = run_id
        return result
    except Exception as e:
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
            return rows
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


@app.get("/api/auto-eda/{tableId}")
async def get_auto_eda(tableId: str):
    try:
        async with get_db() as db:
            row = await query_one(
                db,
                "SELECT * FROM AutoEDARport WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (tableId,),
            )
            if not row:
                return JSONResponse(
                    status_code=404, content={"error": "No EDA report found for table"}
                )
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
            return row
    except Exception as e:
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
            # Find failed checks for this table
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

            if check_id:
                check = await query_one(
                    db, "SELECT * FROM QualityCheck WHERE id=?", (check_id,)
                )
                if check:
                    failed_checks = [check]

            if not failed_checks:
                return {"proposals": [], "message": "No failed checks found to fix"}

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
                        "{}",
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
async def get_pending_fixes(tableId: Optional[str] = None):
    try:
        async with get_db() as db:
            if tableId:
                rows = await query_all(
                    db,
                    "SELECT * FROM FixApproval WHERE status='pending' AND tableId=? ORDER BY createdAt DESC",
                    (tableId,),
                )
            else:
                rows = await query_all(
                    db,
                    "SELECT * FROM FixApproval WHERE status='pending' ORDER BY createdAt DESC",
                )
            return rows
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/auto-fix/{fix_id}/approve")
async def approve_fix(fix_id: str):
    try:
        async with get_db() as db:
            fix = await query_one(db, "SELECT * FROM FixApproval WHERE id=?", (fix_id,))
            if not fix:
                return JSONResponse(
                    status_code=404, content={"error": "Fix proposal not found"}
                )
            if fix["status"] != "pending":
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Fix is already {fix['status']}"},
                )

            table_id = fix["tableId"]
            fix_type = fix["fixType"]
            fix_config = (
                json.loads(fix["fixConfig"])
                if isinstance(fix.get("fixConfig"), str)
                else fix.get("fixConfig", {})
            )

        df = load_dataframe(table_id)
        if df is None:
            return JSONResponse(
                status_code=404, content={"error": "No data found for table"}
            )

        from transformations import get_transformer

        transformer = get_transformer(fix_type)
        result = transformer.transform(df, fix_config)

        now = now_iso()
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
                                "message": result.message,
                                "rows_affected": result.rows_affected,
                            }
                        ),
                        fix_id,
                    ),
                )
            return {
                "success": True,
                "message": "Fix applied successfully",
                "rows_affected": result.rows_affected,
                "columns_affected": result.columns_affected,
                "details": result.details,
            }
        else:
            async with get_db() as db:
                await db.execute(
                    "UPDATE FixApproval SET status='failed', appliedAt=?, resultSummary=? WHERE id=?",
                    (
                        now,
                        json.dumps({"success": False, "message": result.message}),
                        fix_id,
                    ),
                )
            return {"success": False, "message": f"Fix failed: {result.message}"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/auto-fix/{fix_id}/reject")
async def reject_fix(fix_id: str):
    try:
        now = now_iso()
        async with get_db() as db:
            fix = await query_one(db, "SELECT * FROM FixApproval WHERE id=?", (fix_id,))
            if not fix:
                return JSONResponse(
                    status_code=404, content={"error": "Fix proposal not found"}
                )
            await db.execute(
                "UPDATE FixApproval SET status='rejected' WHERE id=?", (fix_id,)
            )
        return {"success": True, "message": "Fix rejected", "id": fix_id}
    except Exception as e:
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
            return await query_all(
                db, "SELECT * FROM Connector ORDER BY createdAt DESC"
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/connectors")
async def create_connector(request: Request):
    try:
        body = await request.json()
        now = now_iso()
        cid = gen_id()
        config = (
            json.dumps(body.get("config", {}))
            if isinstance(body.get("config"), dict)
            else body.get("config", "{}")
        )
        async with get_db() as db:
            await db.execute(
                """INSERT INTO Connector (id,name,type,config,status,createdAt,updatedAt)
                VALUES (?,?,?,?,?,?,?)""",
                (cid, body.get("name"), body.get("type"), config, "inactive", now, now),
            )
            return {"id": cid, "name": body.get("name")}
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

        status = "active" if result.get("success") else "error"
        error = result.get("error", "")
        async with get_db() as db:
            await db.execute(
                "UPDATE Connector SET status=?, lastTested=?, lastError=?, updatedAt=? WHERE id=?",
                (status, now, error if error else None, now, cid),
            )

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


@app.get("/api/ml-readiness/{tableId}")
async def get_ml_readiness(tableId: str):
    try:
        async with get_db() as db:
            row = await query_one(
                db,
                "SELECT * FROM MLReadinessScore WHERE tableId=? ORDER BY createdAt DESC LIMIT 1",
                (tableId,),
            )
            if not row:
                return JSONResponse(
                    status_code=404,
                    content={"error": "No ML readiness score found for table"},
                )
            for key in ("dimensions", "issues", "recommendations"):
                if isinstance(row.get(key), str):
                    try:
                        row[key] = json.loads(row[key])
                    except Exception:
                        pass
            return row
    except Exception as e:
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
            # Gather historical quality scores
            tbl = await query_one(db, 'SELECT name FROM "Table" WHERE id=?', (tableId,))
            table_name = tbl["name"] if tbl else tableId

            # Get scores from checks over time
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
            # Also try DQTestResults
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

        if len(checks) < 3:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Need at least 3 historical data points for forecasting",
                    "data_points": len(checks),
                },
            )

        historical_scores = []
        for c in checks:
            ts = c.get("createdAt", c.get("timestamp", ""))
            if isinstance(ts, str) and len(ts) >= 10:
                date_str = ts[:10]
            else:
                date_str = str(ts)[:10]
            historical_scores.append({"date": date_str, "score": c.get("score", 100)})

        from forecasting.engine import quality_forecast

        result = quality_forecast.forecast(historical_scores, periods=periods)

        # Store forecast result
        now = now_iso()
        async with get_db() as db:
            await db.execute(
                'UPDATE "Table" SET qualityScore=?, updatedAt=? WHERE id=?',
                (
                    historical_scores[-1]["score"] if historical_scores else 100,
                    now,
                    tableId,
                ),
            )

        result["tableId"] = tableId
        result["tableName"] = table_name
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
                    tables = [r[0] for r in cur.fetchall()]
                    conn.close()
                except Exception:
                    tables = []
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
            table_names = [r["name"] for r in await cursor.fetchall()]
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
            safe_limit = max(1, min(limit, 500))
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
            table_names = [r["name"] for r in await cursor.fetchall()]
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

        safe_limit = max(1, min(limit, 500))
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


@app.get("/api/table-data/{table_id}")
async def single_table_data(table_id: str, limit: int = 100):
    """Preview data for a single uploaded table by its ID. Reads from CSV files."""
    try:
        async with get_db() as db:
            tbl = await query_one(
                db,
                'SELECT id, name, fullyQualifiedName, columnCount, rowCount, columns FROM "Table" WHERE id=?',
                (table_id,),
            )
            if not tbl:
                return JSONResponse(
                    status_code=404, content={"error": f"Table '{table_id}' not found"}
                )

        safe_limit = max(1, min(limit, 1000))

        # Parse column definitions
        col_defs = []
        try:
            col_defs = (
                json.loads(tbl["columns"])
                if isinstance(tbl["columns"], str)
                else (tbl["columns"] or [])
            )
        except Exception:
            col_defs = []

        # Try to load actual data
        df = load_dataframe(table_id)
        data_rows = []
        result_columns = [c.get("name", f"col_{i}") for i, c in enumerate(col_defs)]
        total_rows = tbl["rowCount"] or 0

        if df is not None and len(df) > 0:
            result_columns = list(df.columns.astype(str))
            total_rows = len(df)

            # Rebuild columns from DataFrame
            col_defs_out = []
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
                col_defs_out.append(
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
            data_rows = _sanitize_for_json(sample_df.to_dict(orient="records"))
        else:
            col_defs_out = []
            for idx, col in enumerate(col_defs):
                col_defs_out.append(
                    {
                        "cid": idx,
                        "name": col.get("name", f"col_{idx}"),
                        "type": col.get("type", "TEXT"),
                        "notnull": not col.get("nullable", True),
                        "defaultValue": None,
                        "primaryKey": False,
                    }
                )

        return {
            "id": tbl["id"],
            "name": tbl["name"],
            "fullyQualifiedName": tbl.get("fullyQualifiedName", tbl["name"]),
            "columns": col_defs_out,
            "resultColumns": result_columns,
            "rows": data_rows,
            "rowCount": len(data_rows),
            "totalRows": total_rows,
            "truncated": len(data_rows) >= safe_limit and total_rows > safe_limit,
        }
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
        table_names = [r[0] for r in cur.fetchall()]
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
    """Apply a fix. Update FixApproval table: set status='applied', appliedAt=now."""
    try:
        now = now_iso()
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
            await db.execute(
                "UPDATE FixApproval SET status='applied', appliedAt=? WHERE id=?",
                (now, fix_id),
            )
        return {
            "success": True,
            "message": "Fix applied successfully",
            "id": fix_id,
            "appliedAt": now,
        }
    except Exception as e:
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
