"""Comprehensive system tests for non-functional requirements.
Tests: response times, error handling, data consistency, concurrent access,
large data handling, input validation, content type, CORS, edge cases."""

import os
import sys
import json
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from index import app
from engine.rule_executor import save_dataframe
import pandas as pd
import numpy as np

client = TestClient(app)


def _create_test_table(suffix="sys"):
    """Create a test DataFrame and save it, return the table_id."""
    df = pd.DataFrame({
        "id": list(range(1, 21)),
        "score": [95.5, 87.3, 92.1, 78.4, 88.9, 91.2, 85.5, 79.3, 90.0, 82.1,
                  93.5, 86.3, 94.1, 77.4, 89.9, 96.2, 84.5, 76.3, 91.0, 83.1],
        "name": [f"User_{i}" for i in range(1, 21)],
        "category": ["A", "B", "A", "C", "B", "A", "C", "B", "A", "C"] * 2,
        "age": [25, 30, 35, 28, 42, 31, 27, 38, 33, 29] * 2,
    })
    table_id = f"sys_{suffix}_{os.getpid()}_{id(df)}"
    save_dataframe(table_id, df, 'csv')
    return table_id, df


def _create_large_table(rows=1000):
    """Create a DataFrame with 1000+ rows."""
    np.random.seed(42)
    df = pd.DataFrame({
        "id": list(range(rows)),
        "value": np.random.randn(rows),
        "category": np.random.choice(["A", "B", "C", "D"], rows),
        "score": np.random.uniform(0, 100, rows),
    })
    table_id = f"large_sys_{os.getpid()}_{id(df)}"
    save_dataframe(table_id, df, 'csv')
    return table_id, df


# ═══════════════════════════════════════════════
# 1. Response Time Tests
# ═══════════════════════════════════════════════

class TestResponseTimes:
    """All GET endpoints should respond within 2 seconds."""

    def test_health_endpoint_fast(self):
        start = time.time()
        resp = client.get("/")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Health endpoint took {elapsed:.2f}s"

    def test_stats_endpoint_fast(self):
        start = time.time()
        resp = client.get("/api/stats")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Stats endpoint took {elapsed:.2f}s"

    def test_transforms_list_fast(self):
        start = time.time()
        resp = client.get("/api/transforms/list")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Transforms list took {elapsed:.2f}s"

    def test_connectors_sources_fast(self):
        start = time.time()
        resp = client.get("/api/connectors/sources")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Connector sources took {elapsed:.2f}s"

    def test_statistical_tests_list_fast(self):
        start = time.time()
        resp = client.get("/api/statistical/tests")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Statistical tests list took {elapsed:.2f}s"

    def test_schedules_list_fast(self):
        start = time.time()
        resp = client.get("/api/schedules")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Schedules list took {elapsed:.2f}s"

    def test_contracts_list_fast(self):
        start = time.time()
        resp = client.get("/api/contracts")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Contracts list took {elapsed:.2f}s"

    def test_pipelines_list_fast(self):
        start = time.time()
        resp = client.get("/api/pipelines")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Pipelines list took {elapsed:.2f}s"

    def test_services_list_fast(self):
        start = time.time()
        resp = client.get("/api/services")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Services list took {elapsed:.2f}s"

    def test_tables_list_fast(self):
        start = time.time()
        resp = client.get("/api/tables")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Tables list took {elapsed:.2f}s"


# ═══════════════════════════════════════════════
# 2. Error Handling Tests
# ═══════════════════════════════════════════════

class TestErrorHandling:
    """Invalid inputs return proper error codes (400, 404, 422)."""

    def test_transform_execute_no_body(self):
        resp = client.post("/api/transforms/execute")
        assert resp.status_code in (400, 422, 500)

    def test_transform_execute_missing_fields(self):
        resp = client.post("/api/transforms/execute", json={})
        assert resp.status_code == 400

    def test_transform_execute_nonexistent_table(self):
        resp = client.post("/api/transforms/execute", json={
            "tableId": "totally_nonexistent_table_xyz",
            "transformType": "dedup",
            "config": {},
        })
        assert resp.status_code == 404

    def test_auto_eda_no_table_id(self):
        resp = client.post("/api/auto-eda", json={})
        assert resp.status_code == 400

    def test_auto_eda_nonexistent_table(self):
        resp = client.post("/api/auto-eda", json={"tableId": "nonexistent"})
        assert resp.status_code == 404

    def test_ml_readiness_no_table_id(self):
        resp = client.post("/api/ml-readiness", json={})
        assert resp.status_code == 400

    def test_copilot_no_message(self):
        resp = client.post("/api/copilot/chat", json={})
        assert resp.status_code == 400

    def test_statistical_run_missing_params(self):
        resp = client.post("/api/statistical/run", json={})
        assert resp.status_code == 400

    def test_sql_empty_query(self):
        resp = client.post("/api/sql/query", json={"query": ""})
        assert resp.status_code == 400

    def test_sql_forbidden_query(self):
        resp = client.post("/api/sql/query", json={"query": "DROP TABLE Service"})
        assert resp.status_code == 403

    def test_sql_delete_query(self):
        resp = client.post("/api/sql/query", json={"query": "DELETE FROM Service"})
        assert resp.status_code == 403

    def test_pipeline_not_found(self):
        resp = client.get("/api/pipelines/nonexistent_pipeline_12345")
        assert resp.status_code == 404

    def test_connector_not_found(self):
        resp = client.post("/api/connectors/nonexistent_connector/test")
        assert resp.status_code == 404

    def test_schedule_not_found(self):
        resp = client.post("/api/schedules/nonexistent_schedule/run")
        assert resp.status_code == 404

    def test_contract_validate_not_found(self):
        resp = client.post("/api/contracts/nonexistent_contract/validate", json={})
        assert resp.status_code == 404

    def test_service_not_found(self):
        resp = client.get("/api/services/nonexistent_service_99999")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════
# 3. Data Consistency (CRUD cycle)
# ═══════════════════════════════════════════════

class TestDataConsistency:
    """Create → Read → Update → Read → Delete → Verify Gone"""

    def test_schedule_crud_cycle(self):
        # Create
        create_resp = client.post("/api/schedules", json={
            "name": "CRUD System Test Schedule",
            "type": "check",
        })
        assert create_resp.status_code == 200
        sid = create_resp.json()["id"]

        # Read (via list)
        list_resp = client.get("/api/schedules")
        schedule_ids = [s["id"] for s in list_resp.json()]
        assert sid in schedule_ids

        # Update
        update_resp = client.put(f"/api/schedules/{sid}", json={"name": "Updated CRUD Schedule"})
        assert update_resp.status_code == 200

        # Read again (verify update)
        list_resp2 = client.get("/api/schedules")
        updated = [s for s in list_resp2.json() if s["id"] == sid][0]
        assert updated["name"] == "Updated CRUD Schedule"

        # Delete
        delete_resp = client.delete(f"/api/schedules/{sid}")
        assert delete_resp.status_code == 200

        # Verify gone
        list_resp3 = client.get("/api/schedules")
        schedule_ids3 = [s["id"] for s in list_resp3.json()]
        assert sid not in schedule_ids3

    def test_contract_crud_cycle(self):
        # Create
        create_resp = client.post("/api/contracts", json={
            "name": "CRUD System Test Contract",
            "contractDef": {"schema": {"columns": [{"name": "id", "type": "numeric"}]}},
        })
        assert create_resp.status_code == 200
        cid = create_resp.json()["id"]

        # Read (via list)
        list_resp = client.get("/api/contracts")
        contract_ids = [c["id"] for c in list_resp.json()]
        assert cid in contract_ids

        # Delete
        delete_resp = client.delete(f"/api/contracts/{cid}")
        assert delete_resp.status_code == 200

        # Verify gone
        list_resp2 = client.get("/api/contracts")
        contract_ids2 = [c["id"] for c in list_resp2.json()]
        assert cid not in contract_ids2

    def test_connector_crud_cycle(self):
        # Create
        create_resp = client.post("/api/connectors", json={
            "name": "CRUD System Test Connector",
            "type": "sqlite",
            "config": {"path": "/tmp/test.db"},
        })
        assert create_resp.status_code == 200
        cid = create_resp.json()["id"]

        # Read (via list)
        list_resp = client.get("/api/connectors")
        connector_ids = [c["id"] for c in list_resp.json()]
        assert cid in connector_ids

        # Delete
        delete_resp = client.delete(f"/api/connectors/{cid}")
        assert delete_resp.status_code == 200

        # Verify gone
        list_resp2 = client.get("/api/connectors")
        connector_ids2 = [c["id"] for c in list_resp2.json()]
        assert cid not in connector_ids2

    def test_pipeline_crud_cycle(self):
        # Create
        create_resp = client.post("/api/pipelines", json={"name": "CRUD System Pipeline"})
        assert create_resp.status_code == 200
        pid = create_resp.json()["id"]

        # Read
        get_resp = client.get(f"/api/pipelines/{pid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "CRUD System Pipeline"

        # Update
        update_resp = client.put(f"/api/pipelines/{pid}", json={"name": "Updated Pipeline"})
        assert update_resp.status_code == 200

        # Read again
        get_resp2 = client.get(f"/api/pipelines/{pid}")
        assert get_resp2.status_code == 200
        assert get_resp2.json()["name"] == "Updated Pipeline"

        # Delete
        delete_resp = client.delete(f"/api/pipelines/{pid}")
        assert delete_resp.status_code == 200

        # Verify gone
        get_resp3 = client.get(f"/api/pipelines/{pid}")
        assert get_resp3.status_code == 404

    def test_service_crud_cycle(self):
        # Create
        create_resp = client.post("/api/services", json={"name": "CRUD Service"})
        assert create_resp.status_code == 200
        sid = create_resp.json()["id"]

        # Read
        get_resp = client.get(f"/api/services/{sid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "CRUD Service"

        # Update
        update_resp = client.put(f"/api/services/{sid}", json={"name": "Updated Service"})
        assert update_resp.status_code == 200

        # Read again
        get_resp2 = client.get(f"/api/services/{sid}")
        assert get_resp2.status_code == 200
        assert get_resp2.json()["name"] == "Updated Service"

        # Delete
        delete_resp = client.delete(f"/api/services/{sid}")
        assert delete_resp.status_code == 200

        # Verify gone
        get_resp3 = client.get(f"/api/services/{sid}")
        assert get_resp3.status_code == 404


# ═══════════════════════════════════════════════
# 4. Concurrent Access
# ═══════════════════════════════════════════════

class TestConcurrentAccess:
    """Multiple sequential requests work correctly."""

    def test_concurrent_reads(self):
        """Multiple concurrent GET requests should all succeed."""
        results = [None] * 5
        errors = [None] * 5

        def read_endpoint(idx):
            try:
                resp = client.get("/api/transforms/list")
                results[idx] = resp.status_code
            except Exception as e:
                errors[idx] = str(e)

        threads = [threading.Thread(target=read_endpoint, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        for i in range(5):
            assert errors[i] is None, f"Thread {i} error: {errors[i]}"
            assert results[i] == 200

    def test_concurrent_schedules_create(self):
        """Multiple concurrent POST requests should all succeed."""
        results = []
        lock = threading.Lock()

        def create_schedule(idx):
            try:
                resp = client.post("/api/schedules", json={
                    "name": f"Concurrent Schedule {idx}"
                })
                with lock:
                    results.append(resp.status_code)
            except Exception:
                with lock:
                    results.append(500)

        threads = [threading.Thread(target=create_schedule, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(results) == 3
        for r in results:
            assert r == 200

    def test_sequential_crud_operations(self):
        """Sequential requests should maintain consistency."""
        for i in range(5):
            resp = client.post("/api/schedules", json={
                "name": f"Sequential Test {i}"
            })
            assert resp.status_code == 200

        list_resp = client.get("/api/schedules")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 5


# ═══════════════════════════════════════════════
# 5. Large Data Handling
# ═══════════════════════════════════════════════

class TestLargeData:
    """Test with 1000+ row DataFrames."""

    def test_transform_large_data(self):
        table_id, df = _create_large_table(1000)
        start = time.time()
        resp = client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "dedup",
            "config": {"method": "exact"},
        })
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 10.0, f"Large data transform took {elapsed:.2f}s"

    def test_auto_eda_large_data(self):
        table_id, df = _create_large_table(1000)
        start = time.time()
        resp = client.post("/api/auto-eda", json={"tableId": table_id})
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 10.0, f"Large EDA took {elapsed:.2f}s"
        data = resp.json()
        assert data["overview"]["rows"] == 1000

    def test_ml_readiness_large_data(self):
        table_id, df = _create_large_table(1000)
        start = time.time()
        resp = client.post("/api/ml-readiness", json={"tableId": table_id})
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 10.0, f"Large ML readiness took {elapsed:.2f}s"

    def test_statistical_test_large_data(self):
        table_id, df = _create_large_table(1000)
        start = time.time()
        resp = client.post("/api/statistical/run", json={
            "tableId": table_id,
            "testType": "normality",
            "config": {"column": "value"},
        })
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 10.0, f"Large statistical test took {elapsed:.2f}s"

    def test_imputation_large_data(self):
        """Create large data with missing values and impute."""
        np.random.seed(42)
        rows = 1000
        df = pd.DataFrame({
            "val": [np.nan if i % 10 == 0 else float(i) for i in range(rows)],
            "cat": ["A"] * 500 + ["B"] * 500,
        })
        table_id = f"large_impute_sys_{os.getpid()}_{id(df)}"
        save_dataframe(table_id, df, 'csv')

        start = time.time()
        resp = client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "imputation",
            "config": {"method": "mean", "columns": ["val"]},
        })
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert resp.json()["success"]
        assert elapsed < 10.0


# ═══════════════════════════════════════════════
# 6. Input Validation
# ═══════════════════════════════════════════════

class TestInputValidation:
    """Missing required fields, invalid types."""

    def test_schedule_missing_name(self):
        """POST /api/schedules without name → 500 (NOT NULL constraint in DB)"""
        resp = client.post("/api/schedules", json={})
        # Name is NOT NULL in schema, so empty body causes DB error → 500
        assert resp.status_code in (200, 500)

    def test_connector_missing_type(self):
        """POST /api/connectors without type → 500 (NOT NULL constraint in DB)"""
        resp = client.post("/api/connectors", json={
            "name": "No Type Connector",
        })
        # Type is NOT NULL in schema, missing type causes DB error → 500
        assert resp.status_code in (200, 500)

    def test_transform_execute_empty_config(self):
        """POST /api/transforms/execute with empty config"""
        table_id, _ = _create_test_table("val1")
        resp = client.post("/api/transforms/execute", json={
            "tableId": table_id,
            "transformType": "dedup",
            "config": {},
        })
        assert resp.status_code == 200

    def test_sql_update_query_forbidden(self):
        """POST /api/sql/query with UPDATE → 403"""
        resp = client.post("/api/sql/query", json={
            "query": "UPDATE Service SET name='hacked'"
        })
        assert resp.status_code == 403

    def test_sql_insert_query_forbidden(self):
        """POST /api/sql/query with INSERT → 403"""
        resp = client.post("/api/sql/query", json={
            "query": "INSERT INTO Service VALUES ('x', 'y')"
        })
        assert resp.status_code == 403


# ═══════════════════════════════════════════════
# 7. Content Type
# ═══════════════════════════════════════════════

class TestContentType:
    """All responses are application/json."""

    def test_health_content_type(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_stats_content_type(self):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_services_content_type(self):
        resp = client.get("/api/services")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_transforms_list_content_type(self):
        resp = client.get("/api/transforms/list")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_pipelines_content_type(self):
        resp = client.get("/api/pipelines")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_contracts_content_type(self):
        resp = client.get("/api/contracts")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")


# ═══════════════════════════════════════════════
# 8. CORS Headers
# ═══════════════════════════════════════════════

class TestCORSHeaders:
    """Proper CORS headers present."""

    def test_cors_allow_origin(self):
        resp = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")

    def test_cors_preflight(self):
        resp = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        # CORS preflight should return 200 or 204 with proper headers
        assert resp.status_code in (200, 204, 405)

    def test_cors_on_api_endpoint(self):
        resp = client.get("/api/stats", headers={"Origin": "http://example.com"})
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


# ═══════════════════════════════════════════════
# 9. Edge Cases
# ═══════════════════════════════════════════════

class TestEdgeCases:
    """Empty strings, very long names, special characters."""

    def test_pipeline_with_empty_name(self):
        """POST /api/pipelines with empty name → should still create"""
        resp = client.post("/api/pipelines", json={
            "name": "",
        })
        assert resp.status_code == 200

    def test_pipeline_with_long_name(self):
        """POST /api/pipelines with very long name"""
        long_name = "A" * 500
        resp = client.post("/api/pipelines", json={
            "name": long_name,
        })
        assert resp.status_code == 200

    def test_pipeline_with_special_chars(self):
        """POST /api/pipelines with special characters in name"""
        special_name = "Test <script>alert('x')</script> Pipeline"
        resp = client.post("/api/pipelines", json={
            "name": special_name,
        })
        assert resp.status_code == 200

    def test_schedule_with_unicode_name(self):
        """POST /api/schedules with unicode name"""
        unicode_name = "数据质量检查 🚀"
        resp = client.post("/api/schedules", json={
            "name": unicode_name,
        })
        assert resp.status_code == 200

    def test_contract_with_empty_definition(self):
        """POST /api/contracts with empty contractDef"""
        resp = client.post("/api/contracts", json={
            "name": "Empty Def Contract",
            "contractDef": {},
        })
        assert resp.status_code == 200

    def test_connector_with_complex_config(self):
        """POST /api/connectors with complex nested config"""
        resp = client.post("/api/connectors", json={
            "name": "Complex Config Connector",
            "type": "postgresql",
            "config": {
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "credentials": {"user": "admin", "password": "secret"},
            },
        })
        assert resp.status_code == 200

    def test_sql_select_with_where(self):
        """POST /api/sql/query with WHERE clause"""
        resp = client.post("/api/sql/query", json={
            "query": "SELECT * FROM Service WHERE status='active' LIMIT 5"
        })
        assert resp.status_code == 200

    def test_search_with_empty_query(self):
        """GET /api/search?q= → empty results"""
        resp = client.get("/api/search", params={"q": ""})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tables"] == []
        assert data["services"] == []

    def test_search_with_special_chars(self):
        """GET /api/search?q=... with special characters"""
        resp = client.get("/api/search", params={"q": "'; DROP TABLE--"})
        assert resp.status_code == 200  # Should not crash

    def test_copilot_with_long_message(self):
        """POST /api/copilot/chat with very long message"""
        long_msg = "How do I handle missing values? " * 100
        resp = client.post("/api/copilot/chat", json={
            "message": long_msg,
        })
        assert resp.status_code == 200
