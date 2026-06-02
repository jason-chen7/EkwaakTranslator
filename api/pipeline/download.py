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

# YouTube's "n-signature" challenge needs a JS runtime. yt-dlp auto-detects
# Deno if it's on PATH, so make sure the locations we install it to (see
# render.yaml / Dockerfile) are visible at runtime.
for _deno_bin in ("/opt/render/project/.deno/bin", os.path.expanduser("~/.deno/bin"), "/usr/local/bin"):
    if os.path.isdir(_deno_bin) and _deno_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _deno_bin + os.pathsep + os.environ["PATH"]

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


_cookie_tmp: str | None = None


def _resolve_cookiefile() -> str | None:
    """Return a path to a cookies.txt, writing one from YTDLP_COOKIES_CONTENT if
    provided (so cookies can live in a server env var, not the repo)."""
    global _cookie_tmp
    content = os.getenv("YTDLP_COOKIES_CONTENT")
    if content:
        if _cookie_tmp is None:
            fd, _cookie_tmp = tempfile.mkstemp(prefix="ytcookies_", suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
        return _cookie_tmp
    return os.getenv("YTDLP_COOKIES_FILE")


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

    # YouTube sometimes blocks anonymous downloads ("confirm you're not a bot"),
    # more often from datacenter IPs. Usually NOT needed for public videos.
    # Supply login cookies (throwaway account) via ONE of:
    #   YTDLP_COOKIES_CONTENT   = the cookies.txt contents (best for servers/Render)
    #   YTDLP_COOKIES_FILE      = path to a cookies.txt on disk
    #   YTDLP_COOKIES_FROM_BROWSER = firefox|chrome|edge|brave  (local only)
    cookiefile = _resolve_cookiefile()
    browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
    if cookiefile:
        opts["cookiefile"] = cookiefile
    elif browser:
        # tuple form: (browser, profile, keyring, container)
        opts["cookiesfrombrowser"] = (browser.strip().lower(), None, None, None)

    # Optional: force specific YouTube player client(s), e.g. "web" or
    # "default,web_safari". Sometimes avoids the broken "tv" path on servers.
    player_client = os.getenv("YTDLP_PLAYER_CLIENT")
    if player_client:
        opts["extractor_args"] = {
            "youtube": {"player_client": [c.strip() for c in player_client.split(",") if c.strip()]}
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    return path, info
