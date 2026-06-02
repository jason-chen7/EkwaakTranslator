"""Quick CLI to test the whole pipeline without the web app.

    python -m api.cli "https://www.youtube.com/watch?v=GwFfGw0MNSU"
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from .pipeline import download, transcribe, translate  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m api.cli <youtube-url>")
        raise SystemExit(1)
    url = sys.argv[1]

    print("⬇  downloading audio…")
    path, info = download.download_audio(url)
    print(f"   {info.get('title')}  ->  {path}")

    print("🎙  transcribing (this is the slow part on CPU)…")
    segments = transcribe.transcribe(path)
    print(f"   {len(segments)} segments")

    print("🌐  translating…")
    translated = translate.translate_segments(
        segments, on_progress=lambda d, t: print(f"   {d}/{t}", end="\r")
    )
    print()
    for s in translated:
        print(f"[{s['start']:>7.2f}] {s['zh']}")
        print(f"          → {s['en']}\n")


if __name__ == "__main__":
    main()
