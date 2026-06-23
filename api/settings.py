"""Key-value app settings stored in the DB (persists across redeploys).

Used for things an admin updates at runtime — e.g. the YouTube cookies — so
they don't require a redeploy or env-var change.
"""
from __future__ import annotations

import time

from . import db


def get(key: str) -> str | None:
    with db.connect() as c:
        row = c.execute(
            db.q("SELECT value FROM app_settings WHERE key=?"), (key,)
        ).fetchone()
    return row[0] if row else None


def updated_at(key: str) -> float | None:
    with db.connect() as c:
        row = c.execute(
            db.q("SELECT updated FROM app_settings WHERE key=?"), (key,)
        ).fetchone()
    return row[0] if row else None


def set(key: str, value: str) -> None:
    now = time.time()
    with db.connect() as c:
        if db.IS_PG:
            c.execute(
                "INSERT INTO app_settings (key, value, updated) VALUES (%s,%s,%s) "
                "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated=EXCLUDED.updated",
                (key, value, now),
            )
        else:
            c.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, updated) VALUES (?,?,?)",
                (key, value, now),
            )
