"""In-process background jobs with progress, so the HTTP request never blocks
while a video is downloaded/transcribed/translated (1-3 min).

Good enough for an MVP / single server. Swap for Redis + a worker to scale.
"""
from __future__ import annotations

import os
import threading
import traceback

from . import cache, limits, logs
from .pipeline import download, transcribe, translate

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _set(video_id: str, **kw) -> None:
    with _lock:
        _jobs.setdefault(video_id, {}).update(kw)


def get_status(video_id: str) -> dict:
    with _lock:
        return dict(_jobs.get(video_id, {"status": "unknown"}))


def _run(url: str, video_id: str, ip: str = "unknown") -> None:
    translation_started = False
    audio_path: str | None = None
    try:
        _set(video_id, status="downloading", progress=0)
        audio_path, info = download.download_audio(url)
        title = info.get("title", video_id)

        _set(video_id, status="transcribing", title=title)
        segments = transcribe.transcribe(audio_path)

        if not segments:
            limits.release(video_id)  # nothing was spent on Claude
            logs.log(ip, "error", video_id, "No speech detected")
            _set(video_id, status="error", error="No speech detected in audio.")
            return

        _set(video_id, status="translating", total=len(segments))

        def on_progress(done, total):
            _set(video_id, progress=round(done / total * 100))

        translation_started = True
        translated = translate.translate_segments(segments, on_progress=on_progress)
        cache.put(video_id, title, translated)
        logs.log(ip, "done", video_id, title)
        _set(video_id, status="done", progress=100)
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        if not translation_started:
            limits.release(video_id)  # failed before spending Claude tokens
        logs.log(ip, "error", video_id, str(e)[:200])
        traceback.print_exc()
        _set(video_id, status="error", error=str(e))
    finally:
        # The downloaded audio is a throwaway intermediate — only the translated
        # text is kept (in the cache). Delete it so /tmp doesn't fill up on a server.
        if audio_path:
            try:
                os.remove(audio_path)
            except OSError:
                pass


def start(url: str, video_id: str, ip: str = "unknown") -> dict:
    """Start a job if one isn't already running/done. Returns current status."""
    cached = cache.get(video_id)
    if cached:
        return {"status": "done", "progress": 100, "title": cached["title"]}
    with _lock:
        existing = _jobs.get(video_id)
        if existing and existing.get("status") not in (None, "error"):
            return dict(existing)
        _jobs[video_id] = {"status": "queued", "progress": 0}
    threading.Thread(target=_run, args=(url, video_id, ip), daemon=True).start()
    return {"status": "queued", "progress": 0}
