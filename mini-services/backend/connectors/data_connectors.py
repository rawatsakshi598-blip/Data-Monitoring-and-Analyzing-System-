"""
Data Connectors — Connect to external data sources.
Supports: PostgreSQL, MySQL, S3, BigQuery, SQLite, Local SQLite (app's own DB)
"""

import pandas as pd
import os
from typing import Optional

# System tables used internally by DataGuard — hidden from users
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


class DataConnectorEngine:
    """Connect to external data sources and ingest data."""

    # Path to the app's own SQLite database (used by local_sqlite connector)
    # Points to /db/custom.db which is the main DataGuard database
    LOCAL_DB_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..",
            "..",
            "db",
            "custom.db",
        )
    )

    def test_connection(self, connector_type: str, config: dict) -> dict:
        """Test connectivity to a data source."""
        handlers = {
            "postgresql": self._test_postgresql,
            "mysql": self._test_mysql,
            "s3": self._test_s3,
            "bigquery": self._test_bigquery,
            "sqlite": self._test_sqlite,
            "local_sqlite": self._test_local_sqlite,
            "mongodb": self._test_mongodb_stub,
            "redshift": self._test_redshift_stub,
            "snowflake": self._test_snowflake_stub,
            "api": self._test_api_stub,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {
                "success": False,
                "error": f"Unsupported connector: {connector_type}",
            }
        return fn(config)

    def fetch_data(self, connector_type: str, config: dict) -> dict:
        """Fetch data from a source and return as DataFrame info."""
        handlers = {
            "postgresql": self._fetch_postgresql,
            "mysql": self._fetch_mysql,
            "s3": self._fetch_s3,
            "sqlite": self._fetch_sqlite,
            "local_sqlite": self._fetch_local_sqlite,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {
                "success": False,
                "error": f"Fetch not supported for connector: {connector_type}",
            }
        return fn(config)

    def list_tables(self, connector_type: str, config: dict) -> dict:
        """List tables in a connected database."""
        handlers = {
            "postgresql": self._list_tables_postgresql,
            "mysql": self._list_tables_mysql,
            "sqlite": self._list_tables_sqlite,
            "local_sqlite": self._list_tables_local_sqlite,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {
                "tables": [],
                "error": f"List tables not supported for: {connector_type}",
            }
        return fn(config)

    def get_table_data(
        self, connector_type: str, config: dict, table_name: str, limit: int = 100
    ) -> dict:
        """Get data from a specific table in a connected database."""
        handlers = {
            "postgresql": self._get_table_data_postgresql,
            "mysql": self._get_table_data_mysql,
            "sqlite": self._get_table_data_sqlite,
            "local_sqlite": self._get_table_data_local_sqlite,
        }
        fn = handlers.get(connector_type)
        if fn is None:
            return {"error": f"Get table data not supported for: {connector_type}"}
        return fn(config, table_name, limit)

    def list_sources(self) -> list:
        return [
            {
                "type": "postgresql",
                "name": "PostgreSQL",
                "required_fields": ["host", "port", "database", "user", "password"],
            },
            {
                "type": "mysql",
                "name": "MySQL",
                "required_fields": ["host", "port", "database", "user", "password"],
            },
            {
                "type": "s3",
                "name": "Amazon S3",
                "required_fields": ["bucket", "key", "access_key", "secret_key"],
            },
            {
                "type": "bigquery",
                "name": "Google BigQuery",
                "required_fields": ["project_id", "dataset", "credentials"],
            },
            {"type": "sqlite", "name": "SQLite", "required_fields": ["path"]},
            {
                "type": "local_sqlite",
                "name": "Local Database (Demo)",
                "required_fields": [],
            },
        ]

    # ── PostgreSQL ──

    def _test_postgresql(self, config):
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            # Get table count
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = cur.fetchone()[0]
            conn.close()
            return {
                "success": True,
                "message": "PostgreSQL connection successful",
                "tablesCount": table_count,
            }
        except ImportError:
            return {
                "success": False,
                "error": "psycopg2 not installed. Run: pip install psycopg2-binary",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_postgresql(self, config):
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
            )
            query = config.get(
                "query", "SELECT * FROM information_schema.tables LIMIT 100"
            )
            df = pd.read_sql(query, conn)
            conn.close()
            return {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_tables_postgresql(self, config):
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            cur = conn.cursor()
            cur.execute(
                """
                SELECT table_name,
                       (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name AND c.table_schema = 'public') as col_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            )
            tables = []
            for row in cur.fetchall():
                tables.append({"name": row[0], "columns": [], "rowCount": None})
            conn.close()
            return {"tables": tables}
        except Exception as e:
            return {"tables": [], "error": str(e)}

    def _get_table_data_postgresql(self, config, table_name, limit=100):
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            # Safely quote the table name
            safe_name = table_name.replace('"', '""')
            df = pd.read_sql(f'SELECT * FROM "{safe_name}" LIMIT {int(limit)}', conn)
            # Get total count
            cur = conn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
            total = cur.fetchone()[0]
            conn.close()
            return {
                "tableName": table_name,
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "totalRows": total,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── MySQL ──

    def _test_mysql(self, config):
        try:
            import pymysql

            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"
            )
            table_count = cur.fetchone()[0]
            conn.close()
            return {
                "success": True,
                "message": "MySQL connection successful",
                "tablesCount": table_count,
            }
        except ImportError:
            return {
                "success": False,
                "error": "pymysql not installed. Run: pip install pymysql",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_mysql(self, config):
        try:
            import pymysql

            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
            )
            query = config.get(
                "query", "SELECT * FROM information_schema.tables LIMIT 100"
            )
            df = pd.read_sql(query, conn)
            conn.close()
            return {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_tables_mysql(self, config):
        try:
            import pymysql

            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            tables = [
                {"name": row[0], "columns": [], "rowCount": None}
                for row in cur.fetchall()
            ]
            conn.close()
            return {"tables": tables}
        except Exception as e:
            return {"tables": [], "error": str(e)}

    def _get_table_data_mysql(self, config, table_name, limit=100):
        try:
            import pymysql

            conn = pymysql.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                database=config.get("database", ""),
                user=config.get("username", config.get("user", "")),
                password=config.get("password", ""),
                connect_timeout=5,
            )
            safe_name = table_name.replace("`", "``")
            df = pd.read_sql(f"SELECT * FROM `{safe_name}` LIMIT {int(limit)}", conn)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM `{safe_name}`")
            total = cur.fetchone()[0]
            conn.close()
            return {
                "tableName": table_name,
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "totalRows": total,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── S3 ──

    def _test_s3(self, config):
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                aws_access_key_id=config.get("access_key", ""),
                aws_secret_access_key=config.get("secret_key", ""),
                region_name=config.get("region", "us-east-1"),
            )
            s3.head_bucket(Bucket=config.get("bucket", ""))
            return {"success": True, "message": "S3 connection successful"}
        except ImportError:
            return {
                "success": False,
                "error": "boto3 not installed. Run: pip install boto3",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_s3(self, config):
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                aws_access_key_id=config.get("access_key", ""),
                aws_secret_access_key=config.get("secret_key", ""),
                region_name=config.get("region", "us-east-1"),
            )
            key = config.get("key", "")
            bucket = config.get("bucket", "")
            obj = s3.get_object(Bucket=bucket, Key=key)
            import io

            if key.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(obj["Body"].read()))
            elif key.endswith(".json"):
                df = pd.read_json(io.BytesIO(obj["Body"].read()))
            elif key.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(obj["Body"].read()))
            else:
                df = pd.read_csv(io.BytesIO(obj["Body"].read()))
            return {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── BigQuery (stub) ──

    def _test_bigquery(self, config):
        return {
            "success": False,
            "error": "BigQuery connector not yet implemented. Use google-cloud-bigquery.",
        }

    # ── Stubs for other connector types ──

    def _test_mongodb_stub(self, config):
        return {
            "success": False,
            "error": "MongoDB connector not yet implemented. Install pymongo for MongoDB support.",
        }

    def _test_redshift_stub(self, config):
        return {
            "success": False,
            "error": "Redshift connector not yet implemented. Use psycopg2 with Redshift endpoint.",
        }

    def _test_snowflake_stub(self, config):
        return {
            "success": False,
            "error": "Snowflake connector not yet implemented. Install snowflake-connector-python.",
        }

    def _test_api_stub(self, config):
        try:
            import urllib.request

            url = config.get("host", "")
            if not url:
                return {"success": False, "error": "API URL is required"}
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {
                    "success": True,
                    "message": f"API responded with status {resp.status}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── SQLite (external file) ──

    def _test_sqlite(self, config):
        try:
            import sqlite3

            path = config.get("path", "")
            if not path:
                return {"success": False, "error": "SQLite database path is required"}
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cur.fetchone()[0]
            conn.close()
            return {
                "success": True,
                "message": f"SQLite connection successful: {path}",
                "tablesCount": table_count,
            }
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
            return {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_tables_sqlite(self, config):
        try:
            import sqlite3

            path = config.get("path", "")
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = []
            for row in cur.fetchall():
                name = row[0]
                cur2 = conn.cursor()
                try:
                    cur2.execute(f'SELECT COUNT(*) FROM "{name}"')
                    count = cur2.fetchone()[0]
                except Exception:
                    count = None
                tables.append({"name": name, "rowCount": count, "columns": []})
            conn.close()
            return {"tables": tables}
        except Exception as e:
            return {"tables": [], "error": str(e)}

    def _get_table_data_sqlite(self, config, table_name, limit=100):
        try:
            import sqlite3

            path = config.get("path", "")
            conn = sqlite3.connect(path)
            safe_name = table_name.replace('"', '""')
            df = pd.read_sql(f'SELECT * FROM "{safe_name}" LIMIT {int(limit)}', conn)
            cur = conn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
            total = cur.fetchone()[0]
            conn.close()
            return {
                "tableName": table_name,
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "totalRows": total,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Local SQLite (app's own database) ──

    def _get_local_db_path(self):
        """Get the path to the local DataGuard database."""
        path = self.LOCAL_DB_PATH
        if os.path.exists(path):
            return path
        # Try alternative locations
        alt_paths = [
            os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "..",
                    "..",
                    "db",
                    "custom.db",
                )
            ),
            os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "..",
                    "..",
                    "db",
                    "uploaded_data.db",
                )
            ),
            os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "db",
                    "dataguard.db",
                )
            ),
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                return alt
        # If no DB exists yet, return the default path (backend will create it on start)
        return path

    def _test_local_sqlite(self, config):
        try:
            import sqlite3

            path = self._get_local_db_path()
            if not os.path.exists(path):
                return {
                    "success": False,
                    "error": f"Local database not found. Start the backend first to create it. Expected path: {path}",
                }
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            table_count = cur.fetchone()[0]
            conn.close()
            # Subtract system tables from count for user-facing message
            user_table_count = table_count - len(DATAGUARD_SYSTEM_TABLES)
            return {
                "success": True,
                "message": f"Local database connected — {user_table_count} table(s) found",
                "tablesCount": user_table_count,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _fetch_local_sqlite(self, config):
        try:
            import sqlite3

            path = self._get_local_db_path()
            query = config.get(
                "query",
                "SELECT name, type FROM sqlite_master WHERE type='table' LIMIT 100",
            )
            conn = sqlite3.connect(path)
            df = pd.read_sql(query, conn)
            conn.close()
            return {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_tables_local_sqlite(self, config):
        try:
            import sqlite3

            all_tables = []
            # Check both the main DB and uploaded_data DB
            db_dir = os.path.dirname(self._get_local_db_path())
            db_files = []
            main_path = self._get_local_db_path()
            if os.path.exists(main_path):
                db_files.append(("Main DB", main_path))
            uploaded_path = os.path.join(db_dir, "uploaded_data.db")
            if os.path.exists(uploaded_path):
                db_files.append(("Uploaded Data", uploaded_path))

            if not db_files:
                return {
                    "tables": [],
                    "error": "No local databases found. Start the backend first.",
                }

            for db_label, db_path in db_files:
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    )
                    for row in cur.fetchall():
                        name = row[0]
                        # Skip DataGuard internal system tables
                        if name in DATAGUARD_SYSTEM_TABLES:
                            continue
                        # Get column info
                        try:
                            cur2 = conn.cursor()
                            cur2.execute(f'PRAGMA table_info("{name}")')
                            cols = [col_row[1] for col_row in cur2.fetchall()]
                        except Exception:
                            cols = []
                        # Get row count
                        try:
                            cur3 = conn.cursor()
                            cur3.execute(f'SELECT COUNT(*) FROM "{name}"')
                            count = cur3.fetchone()[0]
                        except Exception:
                            count = None
                        all_tables.append(
                            {
                                "name": name,
                                "schema": db_label,
                                "rowCount": count,
                                "columns": cols,
                            }
                        )
                    conn.close()
                except Exception:
                    continue

            return {"tables": all_tables}
        except Exception as e:
            return {"tables": [], "error": str(e)}

    def _get_table_data_local_sqlite(self, config, table_name, limit=100):
        try:
            import sqlite3

            # Block access to DataGuard internal system tables
            if table_name in DATAGUARD_SYSTEM_TABLES:
                return {"error": f"Table '{table_name}' not found"}
            db_dir = os.path.dirname(self._get_local_db_path())
            db_files = []
            main_path = self._get_local_db_path()
            if os.path.exists(main_path):
                db_files.append(main_path)
            uploaded_path = os.path.join(db_dir, "uploaded_data.db")
            if os.path.exists(uploaded_path):
                db_files.append(uploaded_path)

            if not db_files:
                return {"error": "No local databases found. Start the backend first."}

            # Try each DB to find the table
            for db_path in db_files:
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table_name,),
                    )
                    if cur.fetchone():
                        safe_name = table_name.replace('"', '""')
                        df = pd.read_sql(
                            f'SELECT * FROM "{safe_name}" LIMIT {int(limit)}', conn
                        )
                        try:
                            cur.execute(f'SELECT COUNT(*) FROM "{safe_name}"')
                            total = cur.fetchone()[0]
                        except Exception:
                            total = len(df)
                        conn.close()
                        return {
                            "tableName": table_name,
                            "columns": list(df.columns),
                            "rows": df.to_dict(orient="records"),
                            "totalRows": total,
                        }
                    conn.close()
                except Exception:
                    continue

            return {"error": f"Table '{table_name}' not found in any local database"}
        except Exception as e:
            return {"error": str(e)}


connectors = DataConnectorEngine()
