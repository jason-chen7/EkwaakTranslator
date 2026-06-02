"""Translate Chinese segments to casual, slang-aware English with Claude.

Key design points:
  - A gamer-persona system prompt + the COC glossary are sent as a single
    cached block (prompt caching) so we don't re-pay for them on every batch.
  - Segments are translated in batches with surrounding context, but each one
    is returned 1:1 by index so subtitle timing stays aligned.
"""
from __future__ import annotations

import json
import os

import anthropic

from .. import glossary_store

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
BATCH_SIZE = int(os.getenv("TRANSLATE_BATCH", "25"))


SYSTEM_PROMPT = """You are translating the commentary of a Chinese Clash of Clans \
YouTuber into English for an English-speaking gamer audience.

Style rules:
- Keep it CASUAL and natural — the way a gamer actually talks, not a textbook.
- Preserve hype, jokes, and personality. Short punchy lines are good.
- Translate Clash of Clans slang using the glossary below; infer meaning from \
context when a term isn't listed.
- Don't over-explain. Don't add notes. Just give the natural English line.
- If a segment is filler (uh, um, 那个) keep it brief or natural.

Clash of Clans glossary (Chinese = English):
{glossary}
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


def _translate_batch(client, system_blocks, batch: list[dict]) -> list[str]:
    numbered = "\n".join(f"[{i}] {seg['zh']}" for i, seg in enumerate(batch))
    user = (
        "Translate each numbered Chinese line into one casual English line.\n"
        "Return ONLY a JSON array of strings, in the same order, same length "
        f"({len(batch)} items). No keys, no commentary.\n\n" + numbered
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    # tolerate ```json fences
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("[") :]
    arr = json.loads(text[text.find("[") : text.rfind("]") + 1])
    if len(arr) != len(batch):
        # fall back: pad/truncate so alignment never crashes the app
        arr = (arr + [""] * len(batch))[: len(batch)]
    return [str(x) for x in arr]


def translate_segments(segments: list[dict], on_progress=None) -> list[dict]:
    """Add an 'en' field to each {start,end,zh} segment."""
    if not segments:
        return []
    glossary = glossary_store.as_prompt_text()
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT.format(glossary=glossary),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    client = _client()
    out: list[dict] = []
    total = len(segments)
    for i in range(0, total, BATCH_SIZE):
        batch = segments[i : i + BATCH_SIZE]
        ens = _translate_batch(client, system_blocks, batch)
        for seg, en in zip(batch, ens):
            out.append({**seg, "en": en})
        if on_progress:
            on_progress(min(i + BATCH_SIZE, total), total)
    return out
