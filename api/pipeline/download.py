"""Download audio-only from a YouTube URL using yt-dlp.

We deliberately do NOT post-process to mp3/wav, so ffmpeg is not required:
yt-dlp grabs the best audio-only stream (m4a/webm) and Whisper/PyAV decode it
directly.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yt_dlp

_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([0-9A-Za-z_-]{11})")


def extract_video_id(url: str) -> str | None:
    """Pull the 11-char YouTube video id out of any common URL form."""
    m = _ID_RE.search(url)
    if m:
        return m.group(1)
    # bare id passed in directly
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url.strip()):
        return url.strip()
    return None


def download_audio(url: str, out_dir: str | None = None) -> tuple[str, dict]:
    """Download best audio-only stream. Returns (path, info_dict)."""
    out_dir = out_dir or tempfile.gettempdir()
    outtmpl = str(Path(out_dir) / "%(id)s.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    # YouTube increasingly blocks anonymous downloads ("confirm you're not a
    # bot"). Borrow login cookies to get past it. Configure ONE of:
    #   YTDLP_COOKIES_FROM_BROWSER=firefox|chrome|edge|brave|chromium
    #   YTDLP_COOKIES_FILE=C:\path\to\cookies.txt   (Netscape cookie export)
    browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
    cookiefile = os.getenv("YTDLP_COOKIES_FILE")
    if browser:
        # tuple form: (browser, profile, keyring, container)
        opts["cookiesfrombrowser"] = (browser.strip().lower(), None, None, None)
    elif cookiefile:
        opts["cookiefile"] = cookiefile

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    return path, info
