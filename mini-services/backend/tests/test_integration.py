"""Comprehensive integration tests for the DataGuard FastAPI backend.
Tests all API endpoints end-to-end using TestClient with real DataFrame operations."""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from index import app
from engine.rule_executor import save_dataframe
import pandas as pd
import numpy as np

client = TestClient(app)


def _create_test_table(suffix="default"):
    """Create a test DataFrame and save it, return the table_id."""
    df = pd.DataFrame({
        "id": list(range(1, 21)),
        "score": [95.5, 87.3, 92.1, 78.4, 88.9, 91.2, 85.5, 79.3, 90.0, 82.1,
                  93.5, 86.3, 94.1, 77.4, 89.9, 96.2, 84.5, 76.3, 91.0, 83.1],
        "name": [f"User_{i}" for i in range(1, 21)],
        "category": ["A", "B", "A", "C", "B", "A", "C", "B", "A", "C"] * 2,
        "age": [25, 30, 35, 28, 42, 31, 27, 38, 33, 29] * 2,
    })
    table_id = f"test_{suffix}_{os.getpid()}_{id(df)}"
    save_dataframe(table_id, df, 'csv')
    return table_id, df


# ═══════════════════════════════════════════════
# Health & Stats
# ═══════════════════════════════════════════════

class TestHealthStats:
    def test_health_endpoint(self):
        """GET / → 200, status 'ok'"""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "message" in data

    def test_stats_endpoint(self):
        """GET /api/stats → 200, has totalServices, totalTables etc."""
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "totalServices" in data
        assert "totalTables" in data
        assert "totalTests" in data
        assert "totalAlerts" in data
        assert "averageQualityScore" in data
        assert "testsPassRate" in data
        assert "freshTables" in data
        assert "staleTables" in data
        assert "totalTeams" in data
        assert "recentActivityCount" in data
        assert "recentTestResults" in data

    def test_llm_status_endpoint(self):
        """GET /api/llm-status → 200"""
        resp = client.get("/api/llm-status")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# Transformations
# ═══════════════════════════════════════════════

class TestTransformations:
    def test_list_transforms(self):
        """GET /api/transforms/list → 200, returns list of transformers"""
        resp = client.get("/api/transforms/list")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_execute_transform(self):
        """POST /api/transforms/execute → test with tableId and transform config"""
        table_id, _ = _create_test_table("exec")
        resp = client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "dedup",
            "config": {"method": "exact"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_execute_transform_missing_params(self):
        """POST /api/transforms/execute with missing params → 400"""
        resp = client.post("/api/transforms/execute", json={})
        assert resp.status_code == 400

    def test_execute_transform_nonexistent_table(self):
        """POST /api/transforms/execute with nonexistent table → 404"""
        resp = client.post("/api/transforms/execute", json={
            "tableId": "nonexistent_table_12345",
            "transformType": "dedup",
            "config": {},
        })
        assert resp.status_code == 404

    def test_get_transform_history(self):
        """GET /api/transforms/history/{tableId} → returns history"""
        table_id, _ = _create_test_table("hist")
        # Execute a transform first to create history
        client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "dedup",
            "config": {"method": "exact"},
        })
        resp = client.get(f"/api/transforms/history/{table_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_execute_imputation_transform(self):
        """POST /api/transforms/execute with imputation"""
        df = pd.DataFrame({
            "val": [1.0, np.nan, 3.0, np.nan, 5.0],
            "cat": ["A", "B", "A", "B", "A"],
        })
        table_id = f"test_impute_{os.getpid()}_{id(df)}"
        save_dataframe(table_id, df, 'csv')
        resp = client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "imputation",
            "config": {"method": "mean", "columns": ["val"]},
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ═══════════════════════════════════════════════
# Pipelines
# ═══════════════════════════════════════════════

class TestPipelines:
    def test_create_pipeline(self):
        """POST /api/pipelines → create pipeline → 200"""
        resp = client.post("/api/pipelines", json={
            "name": "Integration Test Pipeline",
            "description": "A test pipeline for integration tests",
            "steps": [
                {"id": "s1", "transform_type": "dedup", "config": {"method": "exact"}, "name": "dedup_step"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Integration Test Pipeline"
        assert "id" in data

    def test_list_pipelines(self):
        """GET /api/pipelines → list includes new pipeline"""
        # Create a pipeline first
        create_resp = client.post("/api/pipelines", json={
            "name": "List Test Pipeline",
        })
        assert create_resp.status_code == 200

        resp = client.get("/api/pipelines")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_pipeline(self):
        """GET /api/pipelines/{id} → get pipeline detail"""
        create_resp = client.post("/api/pipelines", json={
            "name": "Get Detail Pipeline",
        })
        pid = create_resp.json()["id"]
        resp = client.get(f"/api/pipelines/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Detail Pipeline"

    def test_update_pipeline(self):
        """PUT /api/pipelines/{id} → update pipeline"""
        create_resp = client.post("/api/pipelines", json={
            "name": "Before Update",
        })
        pid = create_resp.json()["id"]
        resp = client.put(f"/api/pipelines/{pid}", json={
            "name": "After Update",
            "description": "Updated description",
        })
        assert resp.status_code == 200
        # Verify update
        get_resp = client.get(f"/api/pipelines/{pid}")
        assert get_resp.json()["name"] == "After Update"

    def test_delete_pipeline(self):
        """DELETE /api/pipelines/{id} → delete pipeline"""
        create_resp = client.post("/api/pipelines", json={
            "name": "Delete Me Pipeline",
        })
        pid = create_resp.json()["id"]
        resp = client.delete(f"/api/pipelines/{pid}")
        assert resp.status_code == 200
        # Verify deletion
        get_resp = client.get(f"/api/pipelines/{pid}")
        assert get_resp.status_code == 404

    def test_pipeline_not_found(self):
        """GET /api/pipelines/{id} with nonexistent id → 404"""
        resp = client.get("/api/pipelines/nonexistent_pipeline_99999")
        assert resp.status_code == 404

    def test_run_pipeline(self):
        """POST /api/pipelines/{id}/run → run pipeline"""
        table_id, _ = _create_test_table("run")
        create_resp = client.post("/api/pipelines", json={
            "name": "Run Pipeline Test",
            "tableId": table_id,
            "steps": [
                {"id": "s1", "transform_type": "dedup", "config": {"method": "exact"}, "name": "dedup"},
            ],
        })
        pid = create_resp.json()["id"]
        resp = client.post(f"/api/pipelines/{pid}/run", json={"tableId": table_id})
        assert resp.status_code == 200

    def test_pipeline_runs_list(self):
        """GET /api/pipelines/{id}/runs → list pipeline runs"""
        create_resp = client.post("/api/pipelines", json={
            "name": "Runs List Pipeline",
        })
        pid = create_resp.json()["id"]
        resp = client.get(f"/api/pipelines/{pid}/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════
# Auto-EDA
# ═══════════════════════════════════════════════

class TestAutoEDA:
    def test_generate_auto_eda(self):
        """POST /api/auto-eda → generate report"""
        table_id, _ = _create_test_table("eda")
        resp = client.post("/api/auto-eda", json={"tableId": table_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "overview" in data
        assert "column_profiles" in data

    def test_generate_auto_eda_missing_table(self):
        """POST /api/auto-eda without tableId → 400"""
        resp = client.post("/api/auto-eda", json={})
        assert resp.status_code == 400

    def test_generate_auto_eda_nonexistent_table(self):
        """POST /api/auto-eda with nonexistent table → 404"""
        resp = client.post("/api/auto-eda", json={"tableId": "nonexistent_99999"})
        assert resp.status_code == 404

    def test_get_auto_eda(self):
        """GET /api/auto-eda/{tableId} → get latest report"""
        table_id, _ = _create_test_table("edaget")
        # First generate
        client.post("/api/auto-eda", json={"tableId": table_id})
        # Then retrieve
        resp = client.get(f"/api/auto-eda/{table_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "overview" in data or "tableId" in data


# ═══════════════════════════════════════════════
# Auto-Fix
# ═══════════════════════════════════════════════

class TestAutoFix:
    def test_propose_fix(self):
        """POST /api/auto-fix/propose → propose fix"""
        resp = client.post("/api/auto-fix/propose", json={"tableId": "any_table_id"})
        assert resp.status_code == 200

    def test_get_pending_fixes(self):
        """GET /api/auto-fix/pending → list pending fixes"""
        resp = client.get("/api/auto-fix/pending")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_pending_fixes_with_table(self):
        """GET /api/auto-fix/pending?tableId=... → filtered list"""
        resp = client.get("/api/auto-fix/pending", params={"tableId": "test_table"})
        assert resp.status_code == 200

    def test_approve_fix_nonexistent(self):
        """POST /api/auto-fix/{id}/approve with nonexistent id → 404"""
        resp = client.post("/api/auto-fix/nonexistent_fix_99999/approve")
        assert resp.status_code == 404

    def test_reject_fix_nonexistent(self):
        """POST /api/auto-fix/{id}/reject with nonexistent id → 404"""
        resp = client.post("/api/auto-fix/nonexistent_fix_99999/reject")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════
# Connectors
# ═══════════════════════════════════════════════

class TestConnectors:
    def test_list_sources(self):
        """GET /api/connectors/sources → list connector types"""
        resp = client.get("/api/connectors/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_connectors(self):
        """GET /api/connectors → list configured connectors"""
        resp = client.get("/api/connectors")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_connector(self):
        """POST /api/connectors → create connector"""
        resp = client.post("/api/connectors", json={
            "name": "Test SQLite Connector",
            "type": "sqlite",
            "config": {"path": "/tmp/test.db"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Test SQLite Connector"

    def test_delete_connector(self):
        """DELETE /api/connectors/{id} → delete connector"""
        create_resp = client.post("/api/connectors", json={
            "name": "Delete Me Connector",
            "type": "sqlite",
            "config": {"path": "/tmp/test.db"},
        })
        cid = create_resp.json()["id"]
        resp = client.delete(f"/api/connectors/{cid}")
        assert resp.status_code == 200

    def test_test_connector(self):
        """POST /api/connectors/{id}/test → test connector"""
        create_resp = client.post("/api/connectors", json={
            "name": "Test Conn",
            "type": "sqlite",
            "config": {"path": "/nonexistent/db.sqlite"},
        })
        cid = create_resp.json()["id"]
        resp = client.post(f"/api/connectors/{cid}/test")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_connector_not_found(self):
        """POST /api/connectors/nonexistent/test → 404"""
        resp = client.post("/api/connectors/nonexistent_connector/test")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════
# Schedules
# ═══════════════════════════════════════════════

class TestSchedules:
    def test_list_schedules(self):
        """GET /api/schedules → list schedules"""
        resp = client.get("/api/schedules")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_schedule(self):
        """POST /api/schedules → create schedule"""
        resp = client.post("/api/schedules", json={
            "name": "Integration Test Schedule",
            "type": "check",
            "cron": "0 9 * * *",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Integration Test Schedule"

    def test_update_schedule(self):
        """PUT /api/schedules/{id} → update schedule"""
        create_resp = client.post("/api/schedules", json={
            "name": "Schedule To Update",
        })
        sid = create_resp.json()["id"]
        resp = client.put(f"/api/schedules/{sid}", json={
            "name": "Updated Schedule Name",
        })
        assert resp.status_code == 200

    def test_delete_schedule(self):
        """DELETE /api/schedules/{id} → delete schedule"""
        create_resp = client.post("/api/schedules", json={
            "name": "Schedule To Delete",
        })
        sid = create_resp.json()["id"]
        resp = client.delete(f"/api/schedules/{sid}")
        assert resp.status_code == 200

    def test_run_schedule(self):
        """POST /api/schedules/{id}/run → run schedule"""
        create_resp = client.post("/api/schedules", json={
            "name": "Schedule To Run",
        })
        sid = create_resp.json()["id"]
        resp = client.post(f"/api/schedules/{sid}/run")
        assert resp.status_code == 200

    def test_run_schedule_not_found(self):
        """POST /api/schedules/nonexistent/run → 404"""
        resp = client.post("/api/schedules/nonexistent_schedule/run")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════
# ML-Readiness
# ═══════════════════════════════════════════════

class TestMLReadiness:
    def test_score_ml_readiness(self):
        """POST /api/ml-readiness → score table"""
        table_id, _ = _create_test_table("ml")
        resp = client.post("/api/ml-readiness", json={"tableId": table_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data
        assert "grade" in data

    def test_score_ml_readiness_with_target(self):
        """POST /api/ml-readiness with targetColumn"""
        table_id, _ = _create_test_table("mlt")
        resp = client.post("/api/ml-readiness", json={
            "tableId": table_id,
            "targetColumn": "category",
        })
        assert resp.status_code == 200

    def test_score_ml_readiness_missing_table(self):
        """POST /api/ml-readiness without tableId → 400"""
        resp = client.post("/api/ml-readiness", json={})
        assert resp.status_code == 400

    def test_get_ml_readiness(self):
        """GET /api/ml-readiness/{tableId} → get score"""
        table_id, _ = _create_test_table("mlget")
        # First score
        client.post("/api/ml-readiness", json={"tableId": table_id})
        # Then retrieve
        resp = client.get(f"/api/ml-readiness/{table_id}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# Copilot
# ═══════════════════════════════════════════════

class TestCopilot:
    def test_chat(self):
        """POST /api/copilot/chat → chat with copilot"""
        resp = client.post("/api/copilot/chat", json={
            "message": "How do I handle missing values?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data

    def test_chat_no_message(self):
        """POST /api/copilot/chat without message → 400"""
        resp = client.post("/api/copilot/chat", json={})
        assert resp.status_code == 400

    def test_chat_with_table(self):
        """POST /api/copilot/chat with tableId"""
        resp = client.post("/api/copilot/chat", json={
            "message": "What's wrong with my data?",
            "tableId": "some_table_id",
        })
        assert resp.status_code == 200

    def test_suggestions(self):
        """GET /api/copilot/suggestions/{tableId}"""
        table_id, _ = _create_test_table("cop")
        resp = client.get(f"/api/copilot/suggestions/{table_id}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# Statistical Tests
# ═══════════════════════════════════════════════

class TestStatistical:
    def test_list_tests(self):
        """GET /api/statistical/tests → list tests"""
        resp = client.get("/api/statistical/tests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_run_test(self):
        """POST /api/statistical/run → run test"""
        table_id, _ = _create_test_table("stat")
        resp = client.post("/api/statistical/run", json={
            "tableId": table_id,
            "testType": "normality",
            "config": {"column": "score"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_run_test_missing_params(self):
        """POST /api/statistical/run with missing params → 400"""
        resp = client.post("/api/statistical/run", json={})
        assert resp.status_code == 400

    def test_get_results(self):
        """GET /api/statistical/results/{tableId}"""
        table_id, _ = _create_test_table("statres")
        resp = client.get(f"/api/statistical/results/{table_id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ═══════════════════════════════════════════════
# Contracts
# ═══════════════════════════════════════════════

class TestContracts:
    def test_list_contracts(self):
        """GET /api/contracts → list contracts"""
        resp = client.get("/api/contracts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_contract(self):
        """POST /api/contracts → create contract"""
        resp = client.post("/api/contracts", json={
            "name": "Integration Test Contract",
            "description": "A test contract",
            "contractDef": {
                "schema": {
                    "columns": [{"name": "id", "type": "numeric"}]
                }
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Integration Test Contract"

    def test_delete_contract(self):
        """DELETE /api/contracts/{id} → delete contract"""
        create_resp = client.post("/api/contracts", json={
            "name": "Contract To Delete",
            "contractDef": {},
        })
        cid = create_resp.json()["id"]
        resp = client.delete(f"/api/contracts/{cid}")
        assert resp.status_code == 200

    def test_validate_contract(self):
        """POST /api/contracts/{id}/validate → validate contract"""
        create_resp = client.post("/api/contracts", json={
            "name": "Contract To Validate",
            "contractDef": {"schema": {"columns": [{"name": "id", "type": "numeric"}]}},
        })
        cid = create_resp.json()["id"]
        table_id, _ = _create_test_table("contr")
        resp = client.post(f"/api/contracts/{cid}/validate", json={"tableId": table_id})
        assert resp.status_code == 200
        assert "valid" in resp.json()

    def test_validate_contract_not_found(self):
        """POST /api/contracts/nonexistent/validate → 404"""
        resp = client.post("/api/contracts/nonexistent_contract/validate", json={})
        assert resp.status_code == 404

    def test_get_contract_validations(self):
        """GET /api/contracts/{id}/validations"""
        create_resp = client.post("/api/contracts", json={
            "name": "Contract Validations",
            "contractDef": {"schema": {"columns": [{"name": "id", "type": "numeric"}]}},
        })
        cid = create_resp.json()["id"]
        resp = client.get(f"/api/contracts/{cid}/validations")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# Forecasting
# ═══════════════════════════════════════════════

class TestForecasting:
    def test_forecast_insufficient_data(self):
        """POST /api/forecast/{tableId} → likely 400 (no historical check data)"""
        table_id, _ = _create_test_table("fore")
        resp = client.post(f"/api/forecast/{table_id}", json={"periods": 7})
        # Likely 400 since no historical check data exists
        assert resp.status_code in (200, 400)

    def test_forecast_get(self):
        """GET /api/forecast/{tableId} → get forecast"""
        table_id, _ = _create_test_table("foreget")
        resp = client.get(f"/api/forecast/{table_id}", params={"periods": 7})
        assert resp.status_code in (200, 400)


# ═══════════════════════════════════════════════
# SQL
# ═══════════════════════════════════════════════

class TestSQL:
    def test_select_query(self):
        """POST /api/sql/query → execute SELECT query"""
        resp = client.post("/api/sql/query", json={"query": "SELECT 1 as val"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rowCount"] >= 1

    def test_empty_query(self):
        """POST /api/sql/query with empty query → 400"""
        resp = client.post("/api/sql/query", json={"query": ""})
        assert resp.status_code == 400

    def test_forbidden_query(self):
        """POST /api/sql/query with DROP → 403"""
        resp = client.post("/api/sql/query", json={"query": "DROP TABLE Service"})
        assert resp.status_code == 403

    def test_select_from_table(self):
        """POST /api/sql/query → SELECT from real table"""
        resp = client.post("/api/sql/query", json={
            "query": "SELECT COUNT(*) as cnt FROM Service"
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════════════
# Services (CRUD)
# ═══════════════════════════════════════════════

class TestServicesCRUD:
    def test_create_service(self):
        """POST /api/services → create service"""
        resp = client.post("/api/services", json={
            "name": "Integration Test Service",
            "description": "Test service for integration",
            "platform": "postgresql",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_list_services(self):
        """GET /api/services → list services"""
        resp = client.get("/api/services")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_service_not_found(self):
        """GET /api/services/{id} with nonexistent id → 404"""
        resp = client.get("/api/services/nonexistent_service_99999")
        assert resp.status_code == 404

    def test_update_and_delete_service(self):
        """PUT + DELETE /api/services/{id}"""
        create_resp = client.post("/api/services", json={
            "name": "Service CRUD Test",
        })
        sid = create_resp.json()["id"]
        # Update
        update_resp = client.put(f"/api/services/{sid}", json={
            "name": "Updated Service Name",
        })
        assert update_resp.status_code == 200
        # Delete
        delete_resp = client.delete(f"/api/services/{sid}")
        assert delete_resp.status_code == 200


# ═══════════════════════════════════════════════
# Additional Endpoints
# ═══════════════════════════════════════════════

class TestAdditionalEndpoints:
    def test_list_tables(self):
        """GET /api/tables → list tables"""
        resp = client.get("/api/tables")
        assert resp.status_code == 200

    def test_list_rules(self):
        """GET /api/rules → list rules"""
        resp = client.get("/api/rules")
        assert resp.status_code == 200

    def test_list_checks(self):
        """GET /api/checks → list checks"""
        resp = client.get("/api/checks")
        assert resp.status_code == 200

    def test_list_alerts(self):
        """GET /api/alerts → list alerts"""
        resp = client.get("/api/alerts")
        assert resp.status_code == 200

    def test_list_lineage(self):
        """GET /api/lineage → list lineage"""
        resp = client.get("/api/lineage")
        assert resp.status_code == 200

    def test_list_quality(self):
        """GET /api/quality → list quality tests"""
        resp = client.get("/api/quality")
        assert resp.status_code == 200

    def test_search(self):
        """GET /api/search?q=test → search"""
        resp = client.get("/api/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "tables" in data
        assert "services" in data
        assert "glossary" in data

    def test_create_dataset(self):
        """POST /api/datasets → create dataset"""
        resp = client.post("/api/datasets", json={
            "name": "Integration Test Dataset",
            "description": "Test dataset",
        })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_list_datasets(self):
        """GET /api/datasets → list datasets"""
        resp = client.get("/api/datasets")
        assert resp.status_code == 200

    def test_create_and_list_tags(self):
        """POST + GET /api/tags"""
        # Create
        client.post("/api/tags", json={
            "name": f"integ_test_tag_{os.getpid()}",
            "displayName": "Integration Test Tag",
        })
        # List
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_profile_table(self):
        """POST /api/profile → profile a table"""
        table_id, _ = _create_test_table("prof")
        resp = client.post("/api/profile", json={"tableId": table_id})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_profile_missing_table(self):
        """POST /api/profile without tableId → 400"""
        resp = client.post("/api/profile", json={})
        assert resp.status_code == 400

    def test_profile_nonexistent_table(self):
        """POST /api/profile with nonexistent table → 404"""
        resp = client.post("/api/profile", json={"tableId": "nonexistent_99999"})
        assert resp.status_code == 404

    def test_rollback_transform(self):
        """POST /api/transforms/rollback → rollback last transform"""
        table_id, _ = _create_test_table("roll")
        # Execute a transform first
        client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "dedup",
            "config": {"method": "exact"},
        })
        # Rollback
        resp = client.post("/api/transforms/rollback", json={"tableId": table_id})
        assert resp.status_code == 200

    def test_compliance_list(self):
        """GET /api/compliance → list compliance reports"""
        resp = client.get("/api/compliance")
        assert resp.status_code == 200

    def test_glossary_list(self):
        """GET /api/glossary → list glossary terms"""
        resp = client.get("/api/glossary")
        assert resp.status_code == 200

    def test_activity_list(self):
        """GET /api/activity → list activities"""
        resp = client.get("/api/activity")
        assert resp.status_code == 200

    def test_teams_list(self):
        """GET /api/teams → list teams"""
        resp = client.get("/api/teams")
        assert resp.status_code == 200
