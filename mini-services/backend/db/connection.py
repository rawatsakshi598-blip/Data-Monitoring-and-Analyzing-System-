"""
Database Connection Manager
Uses aiosqlite for async SQLite (MVP)
Easy to swap to asyncpg for PostgreSQL later
"""

import aiosqlite
import json
import os
from typing import Any, Optional
from contextlib import asynccontextmanager


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "db", "custom.db")
DB_PATH = os.path.abspath(DB_PATH)


class Database:
    """Async database wrapper for SQLite."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA journal_mode=WAL")
            await self._connection.execute("PRAGMA foreign_keys=ON")

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def execute(self, sql: str, params: tuple = ()) -> None:
        if self._connection is None:
            await self.connect()
        await self._connection.execute(sql, params)
        await self._connection.commit()

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        if self._connection is None:
            await self.connect()
        cursor = await self._connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        if self._connection is None:
            await self.connect()
        cursor = await self._connection.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_count(
        self, table: str, where: str = "1=1", params: tuple = ()
    ) -> int:
        result = await self.fetch_one(
            f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}", params
        )
        return result["cnt"] if result else 0

    async def insert(self, table: str, data: dict) -> None:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = tuple(data.values())
        await self.execute(
            f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values
        )

    async def update(
        self, table: str, data: dict, where: str, params: tuple = ()
    ) -> None:
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = tuple(data.values()) + params
        await self.execute(f"UPDATE {table} SET {set_clause} WHERE {where}", values)

    async def delete(self, table: str, where: str, params: tuple = ()) -> None:
        await self.execute(f"DELETE FROM {table} WHERE {where}", params)


# Global database instance
db = Database()


@asynccontextmanager
async def get_db():
    """Context manager for database access."""
    await db.connect()
    try:
        yield db
    finally:
        pass  # Keep connection alive for reuse


def gen_id(prefix: str = "") -> str:
    """Generate a unique ID using uuid4."""
    import uuid
    uid = uuid.uuid4().hex
    return f"{prefix}{uid}" if prefix else uid


def safe_json(value: Any) -> str:
    """Convert value to JSON string safely."""
    if isinstance(value, str):
        return value
    return json.dumps(value)


def parse_json(value: Optional[str], default: Any = None) -> Any:
    """Parse JSON string safely."""
    if not value:
        return default or []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default or []
