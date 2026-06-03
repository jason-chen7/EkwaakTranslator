"""Video cache: video_id -> translated segments + metadata.

Every video is transcribed + translated only once. Backed by SQLite (local) or
Postgres (prod) via db.py.
"""
from __future__ import annotations

import json
import time

from . import db


def get(video_id: str) -> dict | None:
    with db.connect() as c:
        row = c.execute(
            db.q("SELECT title, segments FROM videos WHERE video_id=?"), (video_id,)
        ).fetchone()
    if not row:
        return None
    return {"video_id": video_id, "title": row[0], "segments": json.loads(row[1])}


def put(video_id: str, title: str, segments: list[dict]) -> None:
    seg = json.dumps(segments, ensure_ascii=False)
    created = time.time()
    with db.connect() as c:
        if db.IS_PG:
            c.execute(
                "INSERT INTO videos (video_id, title, segments, created) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT (video_id) DO UPDATE SET "
                "title=EXCLUDED.title, segments=EXCLUDED.segments, created=EXCLUDED.created",
                (video_id, title, seg, created),
            )
        else:
            c.execute(
                "INSERT OR REPLACE INTO videos (video_id, title, segments, created) "
                "VALUES (?,?,?,?)",
                (video_id, title, seg, created),
            )


def list_all() -> list[dict]:
    """List cached videos (no segment payload), sorted by link/id."""
    with db.connect() as c:
        rows = c.execute(
            "SELECT video_id, title, created FROM videos ORDER BY video_id"
        ).fetchall()
    return [
        {
            "video_id": vid,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "created": created,
        }
        for vid, title, created in rows
    ]


def delete(video_id: str) -> bool:
    with db.connect() as c:
        cur = c.execute(db.q("DELETE FROM videos WHERE video_id=?"), (video_id,))
        n = cur.rowcount
    return n > 0


def clear_all() -> int:
    with db.connect() as c:
        cur = c.execute("DELETE FROM videos")
        n = cur.rowcount
    return n
