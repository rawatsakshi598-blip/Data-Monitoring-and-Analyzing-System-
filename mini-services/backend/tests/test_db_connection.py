"""
Test: db/connection.py
"""

import os
import sys
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import Database, gen_id, safe_json, parse_json, DB_PATH


# ── Fixtures ──


@pytest_asyncio.fixture
async def db():
    """Create a fresh in-memory database for each test."""
    database = Database(":memory:")
    await database.connect()
    await database.execute(
        """
        CREATE TABLE test_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER DEFAULT 0,
            meta TEXT DEFAULT '{}'
        )
    """
    )
    yield database
    await database.close()


# ── Connection Tests ──


@pytest.mark.asyncio
async def test_connect_creates_connection(db):
    assert db._connection is not None


@pytest.mark.asyncio
async def test_close_removes_connection(db):
    await db.close()
    assert db._connection is None


@pytest.mark.asyncio
async def test_db_path_points_to_custom_db():
    assert "custom.db" in DB_PATH
    assert os.path.isabs(DB_PATH)


# ── Insert Tests ──


@pytest.mark.asyncio
async def test_insert_single_row(db):
    await db.insert("test_items", {"id": "1", "name": "alpha", "value": 10})
    result = await db.fetch_one("SELECT * FROM test_items WHERE id = ?", ("1",))
    assert result is not None
    assert result["name"] == "alpha"
    assert result["value"] == 10


@pytest.mark.asyncio
async def test_insert_multiple_rows(db):
    for i in range(5):
        await db.insert(
            "test_items", {"id": str(i), "name": f"item_{i}", "value": i * 10}
        )
    count = await db.fetch_count("test_items")
    assert count == 5


# ── Fetch Tests ──


@pytest.mark.asyncio
async def test_fetch_one_returns_none_when_empty(db):
    result = await db.fetch_one("SELECT * FROM test_items WHERE id = ?", ("999",))
    assert result is None


@pytest.mark.asyncio
async def test_fetch_all_returns_list(db):
    await db.insert("test_items", {"id": "1", "name": "a"})
    await db.insert("test_items", {"id": "2", "name": "b"})
    results = await db.fetch_all("SELECT * FROM test_items ORDER BY name")
    assert len(results) == 2
    assert results[0]["name"] == "a"
    assert results[1]["name"] == "b"


@pytest.mark.asyncio
async def test_fetch_count_with_where(db):
    await db.insert("test_items", {"id": "1", "name": "a", "value": 5})
    await db.insert("test_items", {"id": "2", "name": "b", "value": 15})
    await db.insert("test_items", {"id": "3", "name": "c", "value": 25})
    count = await db.fetch_count("test_items", "value > ?", (10,))
    assert count == 2


# ── Update Tests ──


@pytest.mark.asyncio
async def test_update_single_field(db):
    await db.insert("test_items", {"id": "1", "name": "old", "value": 5})
    await db.update("test_items", {"name": "new", "value": 99}, "id = ?", ("1",))
    result = await db.fetch_one("SELECT * FROM test_items WHERE id = ?", ("1",))
    assert result["name"] == "new"
    assert result["value"] == 99


@pytest.mark.asyncio
async def test_update_nonexistent_row_does_not_error(db):
    await db.update("test_items", {"name": "ghost"}, "id = ?", ("999",))


# ── Delete Tests ──


@pytest.mark.asyncio
async def test_delete_row(db):
    await db.insert("test_items", {"id": "1", "name": "to_delete"})
    await db.delete("test_items", "id = ?", ("1",))
    result = await db.fetch_one("SELECT * FROM test_items WHERE id = ?", ("1",))
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_does_not_error(db):
    await db.delete("test_items", "id = ?", ("999",))


# ── Helper Function Tests ──


def test_gen_id_unique():
    ids = set()
    for _ in range(100):
        ids.add(gen_id())
    assert len(ids) == 100


def test_gen_id_with_prefix():
    uid = gen_id("rule_")
    assert uid.startswith("rule_")


def test_safe_json_dict():
    result = safe_json({"key": "value"})
    assert result == '{"key": "value"}'


def test_safe_json_list():
    result = safe_json([1, 2, 3])
    assert result == "[1, 2, 3]"


def test_safe_json_string_passthrough():
    result = safe_json("already a string")
    assert result == "already a string"


def test_parse_json_valid():
    result = parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_none_returns_default():
    result = parse_json(None)
    assert result == []


def test_parse_json_empty_returns_default():
    result = parse_json("")
    assert result == []


def test_parse_json_invalid_returns_default():
    result = parse_json("not json at all")
    assert result == []


def test_parse_json_custom_default():
    result = parse_json(None, {"fallback": True})
    assert result == {"fallback": True}


def test_parse_json_already_parsed():
    result = parse_json([1, 2, 3])
    assert result == [1, 2, 3]
