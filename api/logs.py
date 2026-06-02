"""Lightweight request/usage logging (IP, video, event, time).

Stored in the same SQLite DB. Admin-only to read. Note: on a host with an
ephemeral filesystem (e.g. Render free tier) this resets on redeploy/restart;
attach a persistent disk or external DB to keep history long-term.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_DB = Path(__file__).with_name("cache.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS logs ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  ts REAL, ip TEXT, video_id TEXT, event TEXT, detail TEXT"
        ")"
    )
    return c


def log(ip: str, event: str, video_id: str | None = None, detail: str | None = None) -> None:
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO logs (ts, ip, video_id, event, detail) VALUES (?,?,?,?,?)",
                (time.time(), ip, video_id, event, detail),
            )
    except Exception:  # logging must never break the request
        pass


def recent(limit: int = 200) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, ip, video_id, event, detail FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {"ts": r[0], "ip": r[1], "video_id": r[2], "event": r[3], "detail": r[4]}
        for r in rows
    ]


def stats() -> dict:
    now = time.time()
    day_ago = now - 86400
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM logs WHERE event='request'").fetchone()[0]
        uniq_ips = c.execute("SELECT COUNT(DISTINCT ip) FROM logs").fetchone()[0]
        new_jobs = c.execute("SELECT COUNT(*) FROM logs WHERE event='new'").fetchone()[0]
        cache_hits = c.execute("SELECT COUNT(*) FROM logs WHERE event='cache_hit'").fetchone()[0]
        errors = c.execute("SELECT COUNT(*) FROM logs WHERE event='error'").fetchone()[0]
        today = c.execute(
            "SELECT COUNT(*) FROM logs WHERE event='request' AND ts>=?", (day_ago,)
        ).fetchone()[0]
        top = c.execute(
            "SELECT video_id, COUNT(*) c FROM logs WHERE video_id IS NOT NULL "
            "GROUP BY video_id ORDER BY c DESC LIMIT 10"
        ).fetchall()
    served = cache_hits + new_jobs
    return {
        "total_requests": total,
        "requests_24h": today,
        "unique_ips": uniq_ips,
        "new_translations": new_jobs,
        "cache_hits": cache_hits,
        "errors": errors,
        "cache_hit_rate": round(cache_hits / served * 100) if served else 0,
        "top_videos": [{"video_id": v, "count": c} for v, c in top],
    }
