"""Usage limits to keep API costs bounded on a public deployment.

Only **new** translations (cache misses) are ever counted — resubmitting a
cached video is free and bypasses everything.

Two limits, both configurable via .env:
  - per-IP rate limit:  max RATE_LIMIT_PER_WINDOW new videos per
                        RATE_LIMIT_WINDOW_MIN minutes (the "20-minute" limit).
  - global daily cap:   max DAILY_NEW_VIDEO_LIMIT new videos per UTC day —
                        this is the hard cost ceiling.

State lives in SQLite so it survives a server restart.
"""
from __future__ import annotations

import os
import time

from . import db

DAILY_LIMIT = int(os.getenv("DAILY_NEW_VIDEO_LIMIT", "15"))
WINDOW_MIN = int(os.getenv("RATE_LIMIT_WINDOW_MIN", "20"))
WINDOW_MAX = int(os.getenv("RATE_LIMIT_PER_WINDOW", "2"))


def _conn():
    return db.connect()


def _day_start(now: float) -> float:
    # epoch 0 is 00:00 UTC, so this snaps to midnight UTC.
    return now - (now % 86400)


def usage() -> dict:
    now = time.time()
    with _conn() as c:
        daily = c.execute(
            db.q("SELECT COUNT(*) FROM usage_events WHERE ts >= ?"), (_day_start(now),)
        ).fetchone()[0]
    return {
        "daily_used": daily,
        "daily_limit": DAILY_LIMIT,
        "daily_remaining": max(0, DAILY_LIMIT - daily),
        "window_minutes": WINDOW_MIN,
        "window_max": WINDOW_MAX,
    }


def check_and_reserve(ip: str, video_id: str) -> tuple[bool, str | None]:
    """Atomically check both limits and, if OK, record a new-translation event."""
    now = time.time()
    with _conn() as c:
        daily = c.execute(
            db.q("SELECT COUNT(*) FROM usage_events WHERE ts >= ?"), (_day_start(now),)
        ).fetchone()[0]
        if daily >= DAILY_LIMIT:
            return False, (
                f"Daily limit reached ({DAILY_LIMIT} new videos). "
                "Cached videos still work; resets at 00:00 UTC."
            )

        window_start = now - WINDOW_MIN * 60
        recent = c.execute(
            db.q(
                "SELECT MIN(ts) FROM (SELECT ts FROM usage_events "
                "WHERE ip=? AND ts >= ? ORDER BY ts DESC LIMIT ?) sub"
            ),
            (ip, window_start, WINDOW_MAX),
        ).fetchone()[0]
        window_count = c.execute(
            db.q("SELECT COUNT(*) FROM usage_events WHERE ip=? AND ts >= ?"),
            (ip, window_start),
        ).fetchone()[0]
        if window_count >= WINDOW_MAX:
            wait_min = max(1, int((recent + WINDOW_MIN * 60 - now) / 60) + 1)
            return False, (
                f"Rate limit: {WINDOW_MAX} new videos per {WINDOW_MIN} min. "
                f"Try again in ~{wait_min} min, or pick a cached video."
            )

        c.execute(
            db.q("INSERT INTO usage_events (ts, ip, video_id) VALUES (?,?,?)"),
            (now, ip, video_id),
        )
    return True, None


def release(video_id: str) -> None:
    """Refund the most recent reservation for a video (used when a job fails
    before any Claude tokens are spent)."""
    with _conn() as c:
        row = c.execute(
            db.q("SELECT id FROM usage_events WHERE video_id=? ORDER BY ts DESC LIMIT 1"),
            (video_id,),
        ).fetchone()
        if row:
            c.execute(db.q("DELETE FROM usage_events WHERE id=?"), (row[0],))
