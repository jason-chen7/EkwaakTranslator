"""FastAPI backend for Ekwaak Translator.

Endpoints:
  POST /api/translate   {url}            -> {video_id, status}
  GET  /api/status/{id}                  -> {status, progress, title, error?}
  GET  /api/video/{id}                   -> {video_id, title, segments}
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load api/.env regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Admin token gates all editing (glossary, cache). Set this in production so
# random visitors can't change your glossary or clear your cache. If unset
# (local dev), editing is open for convenience.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if ADMIN_TOKEN and x_admin_token != ADMIN_TOKEN:
        raise HTTPException(403, "Editing is restricted to the admin.")

from . import cache, glossary_store, jobs, limits  # noqa: E402
from .pipeline.download import extract_video_id  # noqa: E402

app = FastAPI(title="Ekwaak Translator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your domain before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranslateReq(BaseModel):
    url: str


class Term(BaseModel):
    zh: str
    en: str
    note: str | None = None


class GlossaryReq(BaseModel):
    terms: list[Term]


def _client_ip(request: Request) -> str:
    # Respect a reverse proxy if present (set this header at your proxy only).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/api/translate")
def translate(req: TranslateReq, request: Request):
    vid = extract_video_id(req.url)
    if not vid:
        raise HTTPException(400, "Could not find a YouTube video id in that URL.")

    # Cache hit: free, instant, never counts against limits.
    cached = cache.get(vid)
    if cached:
        return {"video_id": vid, "status": "done", "progress": 100, "title": cached["title"]}

    # Already being worked on: return live status without reserving again.
    existing = jobs.get_status(vid)
    if existing.get("status") in ("queued", "downloading", "transcribing", "translating"):
        return {"video_id": vid, **existing}

    # New work -> enforce cost limits before spending anything.
    ok, reason = limits.check_and_reserve(_client_ip(request), vid)
    if not ok:
        raise HTTPException(429, reason)

    status = jobs.start(req.url, vid)
    return {"video_id": vid, **status}


@app.get("/api/status/{video_id}")
def status(video_id: str):
    cached = cache.get(video_id)
    if cached:
        return {"status": "done", "progress": 100, "title": cached["title"]}
    return jobs.get_status(video_id)


@app.get("/api/video/{video_id}")
def video(video_id: str):
    cached = cache.get(video_id)
    if not cached:
        raise HTTPException(404, "Not translated yet.")
    return cached


@app.get("/api/usage")
def get_usage():
    return limits.usage()


@app.get("/api/debug")
def debug():
    """Diagnostics for server-side YouTube extraction (no secrets exposed)."""
    import shutil

    import yt_dlp

    return {
        "yt_dlp_version": yt_dlp.version.__version__,
        "deno_found": shutil.which("deno"),
        "node_found": shutil.which("node"),
        "ffmpeg_found": shutil.which("ffmpeg"),
        "whisper_backend": os.getenv("WHISPER_BACKEND"),
        "has_cookies": bool(os.getenv("YTDLP_COOKIES_CONTENT") or os.getenv("YTDLP_COOKIES_FILE")),
        "player_client": os.getenv("YTDLP_PLAYER_CLIENT") or "(default)",
    }


@app.get("/api/cache")
def list_cache():
    return {"videos": cache.list_all()}


@app.delete("/api/cache/{video_id}")
def delete_cache(video_id: str, _: None = Depends(require_admin)):
    return {"deleted": cache.delete(video_id)}


@app.delete("/api/cache")
def clear_cache(_: None = Depends(require_admin)):
    return {"cleared": cache.clear_all()}


@app.get("/api/glossary")
def get_glossary():
    return {"terms": glossary_store.load_terms()}


@app.put("/api/glossary")
def put_glossary(req: GlossaryReq, _: None = Depends(require_admin)):
    saved = glossary_store.save_terms([t.model_dump() for t in req.terms])
    return {"terms": saved}


@app.get("/api/admin-check")
def admin_check(x_admin_token: str | None = Header(default=None)):
    """Frontend uses this to decide whether to show editing controls."""
    return {"is_admin": bool(ADMIN_TOKEN) and x_admin_token == ADMIN_TOKEN}
