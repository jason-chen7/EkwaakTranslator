"""Central SQLite location, shared by cache / limits / logs.

By default the DB sits next to the code (fine locally). On a host with an
ephemeral filesystem (Render, etc.) set DB_PATH to a PERSISTENT location — e.g.
a mounted disk at /var/data/cache.db — so cache, logs, and usage survive
redeploys and restarts.
"""
from __future__ import annotations

import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH") or Path(__file__).with_name("cache.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
