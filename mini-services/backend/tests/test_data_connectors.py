"""
Comprehensive unit tests for Data Connectors.
Tests source listing, SQLite connections, error handling, and fetch operations.
"""

import os
import sys
import pytest
import tempfile
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from connectors.data_connectors import connectors, DataConnectorEngine


# ═══════════════════════════════════════════════
# List Sources
# ═══════════════════════════════════════════════

class TestListSources:
    def test_list_sources(self):
        sources = connectors.list_sources()
        assert len(sources) >= 5

    def test_list_sources_structure(self):
        sources = connectors.list_sources()
        for s in sources:
            assert 'type' in s
            assert 'name' in s
            assert 'required_fields' in s

    def test_list_sources_types(self):
        sources = connectors.list_sources()
        types = [s['type'] for s in sources]
        assert 'postgresql' in types
        assert 'mysql' in types
        assert 's3' in types
        assert 'sqlite' in types

    def test_sqlite_required_fields(self):
        sources = connectors.list_sources()
        sqlite_src = [s for s in sources if s['type'] == 'sqlite'][0]
        assert 'path' in sqlite_src['required_fields']


# ═══════════════════════════════════════════════
# SQLite Connection
# ═══════════════════════════════════════════════

class TestSQLiteConnection:
    def test_sqlite_connection(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.commit()
            conn.close()
            result = connectors.test_connection('sqlite', {'path': db_path})
            assert result['success']
        finally:
            os.unlink(db_path)

    def test_sqlite_connection_success_message(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.commit()
            conn.close()
            result = connectors.test_connection('sqlite', {'path': db_path})
            assert 'message' in result
        finally:
            os.unlink(db_path)

    def test_sqlite_connection_invalid_path(self):
        result = connectors.test_connection('sqlite', {'path': '/nonexistent/path/db.sqlite'})
        assert not result['success']

    def test_sqlite_fetch_data(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('CREATE TABLE users (id INTEGER, name TEXT)')
            conn.execute("INSERT INTO users VALUES (1, 'Alice')")
            conn.execute("INSERT INTO users VALUES (2, 'Bob')")
            conn.commit()
            conn.close()
            result = connectors.fetch_data('sqlite', {
                'path': db_path,
                'query': 'SELECT * FROM users',
            })
            assert result['success']
            assert result['rows'] == 2
            assert 'id' in result['columns']
        finally:
            os.unlink(db_path)

    def test_sqlite_fetch_default_query(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.commit()
            conn.close()
            result = connectors.fetch_data('sqlite', {'path': db_path})
            assert result['success']
        finally:
            os.unlink(db_path)


# ═══════════════════════════════════════════════
# Invalid Connector
# ═══════════════════════════════════════════════

class TestInvalidConnector:
    def test_invalid_connector_test(self):
        result = connectors.test_connection('nonexistent', {})
        assert not result['success']

    def test_invalid_connector_fetch(self):
        result = connectors.fetch_data('nonexistent', {})
        assert not result['success']

    def test_invalid_connector_error_message(self):
        result = connectors.test_connection('invalid_type', {})
        assert 'Unsupported' in result['error']


# ═══════════════════════════════════════════════
# PostgreSQL / MySQL / S3 (without actual servers)
# ═══════════════════════════════════════════════

class TestExternalConnectors:
    def test_postgresql_connection_fails_gracefully(self):
        result = connectors.test_connection('postgresql', {
            'host': 'nonexistent', 'port': 5432,
            'database': 'test', 'user': 'test', 'password': 'test',
        })
        assert result['success'] is False

    def test_mysql_connection_fails_gracefully(self):
        result = connectors.test_connection('mysql', {
            'host': 'nonexistent', 'port': 3306,
            'database': 'test', 'user': 'test', 'password': 'test',
        })
        assert result['success'] is False

    def test_s3_connection_fails_gracefully(self):
        result = connectors.test_connection('s3', {
            'bucket': 'nonexistent-bucket-xyz',
            'access_key': 'fake',
            'secret_key': 'fake',
        })
        assert result['success'] is False

    def test_bigquery_stub(self):
        result = connectors.test_connection('bigquery', {})
        assert result['success'] is False
        assert 'not yet implemented' in result['error'].lower()


# ═══════════════════════════════════════════════
# Engine Instance
# ═══════════════════════════════════════════════

class TestEngineInstance:
    def test_engine_instance(self):
        assert isinstance(connectors, DataConnectorEngine)
