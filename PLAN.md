# Ekwaak Translator — Build Plan

A web app that translates a Chinese Clash of Clans YouTuber's videos into casual,
slang-aware English. Paste a YouTube URL → the video embeds and plays → a synced
translated-transcript panel scrolls alongside it. Click any line to seek the video.

> Reference video: https://www.youtube.com/watch?v=GwFfGw0MNSU

---

## 1. Decisions locked in

| Decision | Choice |
|---|---|
| Output | Web app: embedded player + synced translated transcript panel |
| Hosting | Public website, **you host the API keys** (users just paste a URL) |
| Scope | Reusable tool — works on any video from his channel |
| Transcription | **Whisper** (local `faster-whisper` for dev, swappable to API in prod) |
| Translation | **Claude** — `claude-sonnet-4-6` default, `claude-opus-4-8` optional |
| Strategy | Build a working **local MVP first**, then deploy the same code |

---

## 2. How it works (the pipeline)

```
  URL ──▶ extract video_id ──▶ cache hit? ──yes──▶ return segments instantly
                                   │ no
                                   ▼
        yt-dlp (download audio) ──▶ Whisper (timestamped 中文 segments)
                                   │
                                   ▼
        Claude (translate each segment, COC persona + glossary, casual tone)
                                   │
                                   ▼
        store in cache DB  ──▶  return [{start, end, zh, en}]  ──▶  UI renders
```

Because every video is **cached by its YouTube video ID**, each video is only
ever transcribed + translated **once**, no matter how many people watch it. That
is the single most important cost-control lever for a "you pay the keys" site.

---

## 3. The translation quality engine (the part you care about)

This is where an LLM beats Google Translate. Three pieces:

1. **Persona system prompt** — "You are translating a Chinese Clash of Clans
   creator's commentary for an English-speaking gamer audience. Keep it casual,
   punchy, and natural — the way a gamer actually talks. Preserve hype and jokes."

2. **A COC slang glossary** (`glossary.json`) injected into the prompt — a living
   list of terms we grow over time. Seed examples:

   | 中文 | English | Note |
   |---|---|---|
   | 大本 / 本 | Town Hall (TH) | "九本" = TH9 |
   | 三星 | three-star | full destruction |
   | 流派 | army comp / strategy | |
   | 偷油 | farming / loot-stealing | |
   | 鱼塘 | dead base | easy loot |
   | 部落 / 部落战 | clan / clan war | |
   | 飞天龙 / 龙流 | dragon spam | |
   | 猪骑 | hog riders | |

3. **Context windows** — segments are translated in small batches (~20 lines /
   ~60s at a time) so Claude disambiguates slang from surrounding context, while
   returning a **1:1 mapping** back to each timestamped segment (validated by
   count) so the subtitles stay perfectly aligned.

The system prompt + glossary block is **prompt-cached** so we don't re-pay for it
on every batch — a real cost saver across a long video.

---

## 4. Tech stack

**Frontend** — `web/`
- React + Vite + TypeScript
- Tailwind CSS for styling
- YouTube IFrame Player API (track `currentTime`, highlight/scroll active line,
  click-to-seek)

**Backend** — `api/`
- Python 3.13 + FastAPI (Python because the Whisper / yt-dlp ecosystem lives here)
- `yt-dlp` + `ffmpeg` for audio extraction
- `faster-whisper` (large-v3) for transcription — behind a `Transcriber`
  interface so we can swap to the OpenAI Whisper API in production
- `anthropic` SDK for translation
- Background job processing + status polling (transcription takes 1–3 min, so the
  request can't block). MVP: FastAPI background tasks + a job table. Scale-up:
  Redis + a worker.
- SQLite cache (MVP) → Postgres (production)

**Why split frontend/backend:** the player UI is pure browser code with no
legal/cost concerns; the audio+AI pipeline must run server-side. Same split works
locally and deployed.

---

## 5. Repo structure

```
EkwaakTranslator/
├─ PLAN.md                  ← this file
├─ README.md
├─ api/
│  ├─ main.py               FastAPI app: POST /translate, GET /status/{job}, GET /video/{id}
│  ├─ pipeline/
│  │  ├─ download.py        yt-dlp audio extraction
│  │  ├─ transcribe.py      Whisper (Transcriber interface: local | api)
│  │  ├─ translate.py       Claude batched translation + alignment
│  │  └─ glossary.json      COC slang dictionary (editable)
│  ├─ cache.py              SQLite store: video_id → segments
│  ├─ jobs.py               job queue + status
│  └─ requirements.txt
└─ web/
   ├─ src/
   │  ├─ App.tsx
   │  ├─ components/
   │  │  ├─ UrlBar.tsx       paste URL + submit
   │  │  ├─ Player.tsx       YouTube IFrame wrapper
   │  │  ├─ Transcript.tsx   synced scrolling translated panel
   │  │  └─ Progress.tsx     "processing… ▓▓▓░░" state
   │  └─ api.ts              calls backend, polls status
   └─ package.json
```

---

## 6. Build phases

- **Phase 0 — Scaffold.** Create `api/` and `web/` skeletons; confirm both run.
- **Phase 1 — Backend pipeline as a CLI.** `python -m api.pipeline <url>` →
  prints `[{start,end,zh,en}]`. Proves download + Whisper + Claude end-to-end on
  the reference video *before* any UI. This is the riskiest part, so it goes first.
- **Phase 2 — Frontend player + transcript** against a static sample JSON. Nail
  the synced highlight / click-to-seek UX with no backend dependency.
- **Phase 3 — Wire them together.** Job submit + polling + SQLite caching.
- **Phase 4 — Tune.** Grow the glossary, refine tone, handle errors (no audio,
  very long videos, age-restricted, etc.), add a max-length guard.
- **Phase 5 — Deploy + protect.** Containerize; deploy frontend (Vercel/Netlify)
  + backend (Render/Railway/Fly, or a GPU box if self-hosting Whisper); add
  per-IP rate limiting and a video-length cap; store keys as host secrets.

---

## 7. Cost (you pay the keys)

Per **new** 15-minute video (cached videos cost $0 thereafter):
- Whisper: **$0** if self-hosted (`faster-whisper`), or ~**$0.09** via OpenAI API.
- Claude Sonnet 4.6 translation: ~**a few cents** (prompt caching helps).
- **≈ $0.10–0.15 per new video**, then free forever via cache.

Spend controls baked in: per-video caching, per-IP rate limiting, a max
video-length cap, and a worker concurrency limit.

---

## 8. Risks & honest caveats

1. **YouTube ToS** — server-side audio download via `yt-dlp` violates YouTube's
   Terms. Low-risk locally; for a public site it can get the server IP blocked or
   draw a takedown. Mitigations: aggressive caching (fewer calls), proxy/cookies
   in production. No fully "clean" path exists for arbitrary videos — accept the
   risk knowingly.
2. **Cost runaway** — open public access + your keys = potential bill. Rate
   limiting + caching + length cap are mandatory, not optional.
3. **Latency** — first view of a new video waits 1–3 min. The UI must show
   progress; the request cannot block.
4. **Alignment drift** — Claude must return exactly one translation per segment.
   We number segments and validate the returned count, re-batching on mismatch.
5. **Whisper hosting** — local `faster-whisper` wants a GPU for speed; on a cheap
   CPU host it's slow, which is why transcription is swappable to the API in prod.

---

## 9. Open questions to settle before Phase 5 (deploy)

- Where to host the backend? (CPU host + Whisper API  vs  GPU host + local Whisper)
- Domain name?
- Rate-limit thresholds + max video length?
- Do you want a small "growable glossary" admin view, or just edit the JSON?

These don't block Phases 0–4, so we can start building the local MVP immediately.
```
