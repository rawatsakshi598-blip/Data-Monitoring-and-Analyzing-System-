"""
Data Connectors — Connect to external data sources.
Supports: PostgreSQL, MySQL, S3, BigQuery (stub)
"""

import pandas as pd
from typing import Optional


class DataConnectorEngine:
    """Connect to external data sources and ingest data."""

    def test_connection(self, connector_type: str, config: dict) -> dict:
        """Test connectivity to a data source."""
        handlers = {
            "postgresql": self._test_postgresql,
            "mysql": self._test_mysql,
            "s3": self._test_s3,
            "bigquery": self._test_bigquery,
            "sqlite": self._test_sqlite,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {"success": False, "error": f"Unsupported connector: {connector_type}"}
        return fn(config)

    def fetch_data(self, connector_type: str, config: dict) -> dict:
        """Fetch data from a source and return as DataFrame info."""
        handlers = {
            "postgresql": self._fetch_postgresql,
            "mysql": self._fetch_mysql,
            "s3": self._fetch_s3,
            "sqlite": self._fetch_sqlite,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {"success": False, "error": f"Unsupported connector: {connector_type}"}
        return fn(config)

    def list_sources(self) -> list:
        return [
            {"type": "postgresql", "name": "PostgreSQL", "required_fields": ["host", "port", "database", "user", "password"]},
            {"type": "mysql", "name": "MySQL", "required_fields": ["host", "port", "database", "user", "password"]},
            {"type": "s3", "name": "Amazon S3", "required_fields": ["bucket", "key", "access_key", "secret_key"]},
            {"type": "bigquery", "name": "Google BigQuery", "required_fields": ["project_id", "dataset", "credentials"]},
            {"type": "sqlite", "name": "SQLite", "required_fields": ["path"]},
        ]

    # ── PostgreSQL ──

    def _test_postgresql(self, config):
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=config.get("host", "localhost"), port=config.get("port", 5432),
                database=config.get("database", ""), user=config.get("user", ""),
                password=config.get("password", ""), connect_timeout=5,
            )
            conn.close()
            return {"success": True, "message": "PostgreSQL connection successful"}
        except ImportError:
            return {"success": False, "error": "psycopg2 not installed. Run: pip install psycopg2-binary"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_postgresql(self, config):
        try:
            import psycopg2
            from io import StringIO
            conn = psycopg2.connect(
                host=config.get("host", "localhost"), port=config.get("port", 5432),
                database=config.get("database", ""), user=config.get("user", ""),
                password=config.get("password", ""),
            )
            query = config.get("query", "SELECT * FROM information_schema.tables LIMIT 100")
            df = pd.read_sql(query, conn)
            conn.close()
            return {"success": True, "data": df, "rows": len(df), "columns": list(df.columns)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── MySQL ──

    def _test_mysql(self, config):
        try:
            import pymysql
            conn = pymysql.connect(
                host=config.get("host", "localhost"), port=config.get("port", 3306),
                database=config.get("database", ""), user=config.get("user", ""),
                password=config.get("password", ""), connect_timeout=5,
            )
            conn.close()
            return {"success": True, "message": "MySQL connection successful"}
        except ImportError:
            return {"success": False, "error": "pymysql not installed. Run: pip install pymysql"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_mysql(self, config):
        try:
            import pymysql
            conn = pymysql.connect(
                host=config.get("host", "localhost"), port=config.get("port", 3306),
                database=config.get("database", ""), user=config.get("user", ""),
                password=config.get("password", ""),
            )
            query = config.get("query", "SELECT * FROM information_schema.tables LIMIT 100")
            df = pd.read_sql(query, conn)
            conn.close()
            return {"success": True, "data": df, "rows": len(df), "columns": list(df.columns)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── S3 ──

    def _test_s3(self, config):
        try:
            import boto3
            s3 = boto3.client('s3',
                aws_access_key_id=config.get("access_key", ""),
                aws_secret_access_key=config.get("secret_key", ""),
                region_name=config.get("region", "us-east-1"),
            )
            s3.head_bucket(Bucket=config.get("bucket", ""))
            return {"success": True, "message": "S3 connection successful"}
        except ImportError:
            return {"success": False, "error": "boto3 not installed. Run: pip install boto3"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_s3(self, config):
        try:
            import boto3
            s3 = boto3.client('s3',
                aws_access_key_id=config.get("access_key", ""),
                aws_secret_access_key=config.get("secret_key", ""),
                region_name=config.get("region", "us-east-1"),
            )
            key = config.get("key", "")
            bucket = config.get("bucket", "")
            obj = s3.get_object(Bucket=bucket, Key=key)
            import io
            if key.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            elif key.endswith('.json'):
                df = pd.read_json(io.BytesIO(obj['Body'].read()))
            elif key.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(obj['Body'].read()))
            else:
                df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            return {"success": True, "data": df, "rows": len(df), "columns": list(df.columns)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── BigQuery (stub) ──

    def _test_bigquery(self, config):
        return {"success": False, "error": "BigQuery connector not yet implemented. Use google-cloud-bigquery."}

    # ── SQLite ──

    def _test_sqlite(self, config):
        try:
            import sqlite3
            path = config.get("path", "")
            conn = sqlite3.connect(path)
            conn.execute("SELECT 1")
            conn.close()
            return {"success": True, "message": f"SQLite connection successful: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_sqlite(self, config):
        try:
            import sqlite3
            path = config.get("path", "")
            query = config.get("query", "SELECT * FROM sqlite_master LIMIT 100")
            conn = sqlite3.connect(path)
            df = pd.read_sql(query, conn)
            conn.close()
            return {"success": True, "data": df, "rows": len(df), "columns": list(df.columns)}
        except Exception as e:
            return {"success": False, "error": str(e)}


connectors = DataConnectorEngine()
