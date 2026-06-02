"""Transcribe audio to timestamped Chinese segments.

Two backends, chosen by the WHISPER_BACKEND env var:
  - "local"  (default): faster-whisper, runs on your machine, free.
  - "openai": OpenAI Whisper API, fast, needs OPENAI_API_KEY.

Both return a list of {"start": float, "end": float, "zh": str}.
"""
from __future__ import annotations

import os

Segment = dict  # {"start": float, "end": float, "zh": str}


def transcribe(audio_path: str) -> list[Segment]:
    backend = os.getenv("WHISPER_BACKEND", "local").lower()
    if backend == "openai":
        return _transcribe_openai(audio_path)
    return _transcribe_local(audio_path)


def _transcribe_local(audio_path: str) -> list[Segment]:
    from faster_whisper import WhisperModel

    model_size = os.getenv("WHISPER_MODEL", "small")  # tiny|base|small|medium|large-v3
    device = os.getenv("WHISPER_DEVICE", "cpu")        # "cuda" if you have an NVIDIA GPU
    compute = os.getenv("WHISPER_COMPUTE", "int8")     # int8 (cpu) | float16 (gpu)

    model = WhisperModel(model_size, device=device, compute_type=compute)
    segments, _info = model.transcribe(
        audio_path,
        language="zh",
        vad_filter=True,  # skip silence -> fewer empty/duplicate lines
    )
    out: list[Segment] = []
    for s in segments:
        text = s.text.strip()
        if text:
            out.append({"start": round(s.start, 2), "end": round(s.end, 2), "zh": text})
    return out


def _transcribe_openai(audio_path: str) -> list[Segment]:
    from openai import OpenAI

    client = OpenAI()
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="zh",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    out: list[Segment] = []
    for s in resp.segments or []:
        text = (s.text or "").strip()
        if text:
            out.append({"start": round(s.start, 2), "end": round(s.end, 2), "zh": text})
    return out
