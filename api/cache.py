"""Tiny SQLite cache: video_id -> translated segments + metadata.

Every video is transcribed + translated only once. This is the main cost
control for a public, you-pay-the-keys deployment.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_DB = Path(__file__).with_name("cache.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS videos ("
        "  video_id TEXT PRIMARY KEY,"
        "  title TEXT,"
        "  segments TEXT,"
        "  created REAL DEFAULT (strftime('%s','now'))"
        ")"
    )
    return c


def get(video_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT title, segments FROM videos WHERE video_id=?", (video_id,)
        ).fetchone()
    if not row:
        return None
    return {"video_id": video_id, "title": row[0], "segments": json.loads(row[1])}


def put(video_id: str, title: str, segments: list[dict]) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO videos (video_id, title, segments) VALUES (?,?,?)",
            (video_id, title, json.dumps(segments, ensure_ascii=False)),
        )


def list_all() -> list[dict]:
    """List cached videos (no segment payload), sorted by link/id."""
    with _conn() as c:
        rows = c.execute(
            "SELECT video_id, title, created FROM videos ORDER BY video_id"
        ).fetchall()
    out = []
    for vid, title, created in rows:
        out.append(
            {
                "video_id": vid,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "created": created,
            }
        )
    return out


def delete(video_id: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM videos WHERE video_id=?", (video_id,))
    return cur.rowcount > 0


def clear_all() -> int:
    with _conn() as c:
        cur = c.execute("DELETE FROM videos")
    return cur.rowcount
