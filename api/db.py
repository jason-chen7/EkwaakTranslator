"""Database layer — SQLite locally, Postgres (e.g. Supabase) in production.

Set DATABASE_URL to a Postgres connection string and the app uses Postgres so
cache / logs / usage persist across redeploys. With it unset, it falls back to
a local SQLite file (great for dev; ephemeral on hosts like Render).

Modules write SQL with '?' placeholders and call db.q() to adapt them.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg  # noqa: F401  (installed via requirements when used)


def _sqlite_path() -> Path:
    p = Path(os.getenv("DB_PATH") or Path(__file__).with_name("cache.db"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def connect():
    """A new connection. `with connect() as c:` commits on success."""
    if IS_PG:
        conn = psycopg.connect(DATABASE_URL)
        conn.prepare_threshold = None  # safe with Supabase's transaction pooler
        return conn
    return sqlite3.connect(_sqlite_path())


def q(sql: str) -> str:
    """Adapt '?' placeholders to Postgres '%s'."""
    return sql.replace("?", "%s") if IS_PG else sql


_SCHEMA_SQLITE = [
    "CREATE TABLE IF NOT EXISTS videos ("
    " video_id TEXT PRIMARY KEY, title TEXT, segments TEXT, created REAL)",
    "CREATE TABLE IF NOT EXISTS usage_events ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, ip TEXT, video_id TEXT)",
    "CREATE TABLE IF NOT EXISTS logs ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, ip TEXT, video_id TEXT,"
    " event TEXT, detail TEXT)",
    "CREATE TABLE IF NOT EXISTS app_settings ("
    " key TEXT PRIMARY KEY, value TEXT, updated REAL)",
]
_SCHEMA_PG = [
    "CREATE TABLE IF NOT EXISTS videos ("
    " video_id TEXT PRIMARY KEY, title TEXT, segments TEXT, created DOUBLE PRECISION)",
    "CREATE TABLE IF NOT EXISTS usage_events ("
    " id BIGSERIAL PRIMARY KEY, ts DOUBLE PRECISION, ip TEXT, video_id TEXT)",
    "CREATE TABLE IF NOT EXISTS logs ("
    " id BIGSERIAL PRIMARY KEY, ts DOUBLE PRECISION, ip TEXT, video_id TEXT,"
    " event TEXT, detail TEXT)",
    "CREATE TABLE IF NOT EXISTS app_settings ("
    " key TEXT PRIMARY KEY, value TEXT, updated DOUBLE PRECISION)",
]


def init() -> None:
    schema = _SCHEMA_PG if IS_PG else _SCHEMA_SQLITE
    with connect() as c:
        for stmt in schema:
            c.execute(stmt)


init()
