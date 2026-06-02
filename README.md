# 🏰 Ekwaak Translator

Translate a Chinese Clash of Clans YouTuber's videos into casual, slang-aware
English. Paste a YouTube URL → the video embeds and plays → a synced
translated-transcript panel scrolls alongside it. Click any line to seek.

Pipeline: `yt-dlp` (audio) → **Whisper** (timestamped 中文) → **Claude**
(casual translation w/ a Clash of Clans glossary) → cached JSON → synced UI.

## Quick start (local)

### 1. Backend
```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then put your ANTHROPIC_API_KEY in .env
```

Test the pipeline straight from the command line first:
```powershell
python -m api.cli "https://www.youtube.com/watch?v=GwFfGw0MNSU"
```

Run the API server:
```powershell
uvicorn api.main:app --reload --port 8000
```

### 2. Frontend
```powershell
cd web
npm install
npm run dev
```
Open the printed URL (usually http://localhost:5173).

## Configuration (`api/.env`)
| Var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | required |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | translation model |
| `WHISPER_BACKEND` | `local` | `local` (free) or `openai` (fast, needs key) |
| `WHISPER_MODEL` | `small` | `tiny`→`large-v3`; bigger = better + slower |
| `WHISPER_DEVICE` | `cpu` | set `cuda` if you have an NVIDIA GPU |
| `OPENAI_API_KEY` | — | only if `WHISPER_BACKEND=openai` |
| `DAILY_NEW_VIDEO_LIMIT` | `15` | global cap on new translations/day (UTC). ~$2/day ceiling |
| `RATE_LIMIT_WINDOW_MIN` | `20` | per-visitor rate-limit window (minutes) |
| `RATE_LIMIT_PER_WINDOW` | `2` | max new videos per visitor per window |

## Cost controls
- Only **new** videos (cache misses) count against the limits. Resubmitting a
  cached link is free, instant, and never counts.
- **Daily cap** (`DAILY_NEW_VIDEO_LIMIT`) is the hard ceiling. At ~$0.10–0.15
  per new video, 15/day ≈ under $2/day.
- **Per-visitor rate limit** stops one person draining the budget.
- The **Cache** tab lists every translated video by link; delete one or
  **Clear all** (do this after a big glossary update so videos re-translate
  with the new vocab).

## Growing the slang dictionary
Edit [`api/pipeline/glossary.json`](api/pipeline/glossary.json) — add
`{ "zh": "…", "en": "…", "note": "…" }` entries. They're injected straight into
the translation prompt, so new slang takes effect on the next translation.

## Notes
- Every video is cached by its YouTube id, so it's only ever translated once.
- Server-side audio download via yt-dlp is against YouTube's ToS; fine locally,
  consider the risk before running a public service.
