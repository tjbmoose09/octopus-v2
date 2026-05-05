"""Octopus Agents V2 — Database Manager"""
import aiosqlite
import os
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db_path():
    """Resolve DB path at call time so env vars work."""
    return os.getenv("OCTOPUS_DB", str(Path(__file__).parent / "octopus.db"))


async def get_db():
    """Get async database connection."""
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database with schema."""
    path = get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = await get_db()
    try:
        schema = SCHEMA_PATH.read_text()
        await db.executescript(schema)
        await db.commit()
        print(f"[DB] Initialized at {path}")
    finally:
        await db.close()


async def execute(query: str, params: tuple = ()):
    """Execute a write query."""
    db = await get_db()
    try:
        await db.execute(query, params)
        await db.commit()
    finally:
        await db.close()


async def fetch_all(query: str, params: tuple = ()):
    """Fetch all rows."""
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def fetch_one(query: str, params: tuple = ()):
    """Fetch single row."""
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()
