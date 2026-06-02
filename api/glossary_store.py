"""Read/write access to the Clash of Clans slang glossary.

Single source of truth for both the translation prompt and the admin UI.
Stored as JSON on disk so it's trivially editable and version-controllable.
"""
from __future__ import annotations

import json
from pathlib import Path

_PATH = Path(__file__).parent / "pipeline" / "glossary.json"


def _read_raw() -> dict:
    return json.loads(_PATH.read_text(encoding="utf-8"))


def load_terms() -> list[dict]:
    """Return the list of {zh, en, note} terms."""
    return _read_raw().get("terms", [])


def save_terms(terms: list[dict]) -> list[dict]:
    """Replace the whole term list. Normalizes + drops empty rows."""
    clean: list[dict] = []
    for t in terms:
        zh = (t.get("zh") or "").strip()
        en = (t.get("en") or "").strip()
        if not zh or not en:
            continue  # a term needs both sides
        entry = {"zh": zh, "en": en}
        note = (t.get("note") or "").strip()
        if note:
            entry["note"] = note
        clean.append(entry)

    data = _read_raw()
    data["terms"] = clean
    _PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return clean


def as_prompt_text() -> str:
    """Render the glossary as the bullet list injected into the system prompt."""
    lines = []
    for t in load_terms():
        note = f"  ({t['note']})" if t.get("note") else ""
        lines.append(f"- {t['zh']} = {t['en']}{note}")
    return "\n".join(lines)
