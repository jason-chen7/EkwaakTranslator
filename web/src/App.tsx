import { useCallback, useEffect, useRef, useState } from "react";
import Player from "./components/Player";
import Transcript from "./components/Transcript";
import Glossary from "./components/Glossary";
import CachePanel from "./components/CachePanel";
import {
  checkAdmin,
  getStatus,
  getUsage,
  getVideo,
  setAdminToken,
  startTranslate,
  type Segment,
  type Status,
  type Usage,
} from "./api";

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued…",
  downloading: "Downloading audio…",
  transcribing: "Transcribing speech…",
  translating: "Translating…",
};

export default function App() {
  const [url, setUrl] = useState("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [showOriginal, setShowOriginal] = useState(true);
  const [tab, setTab] = useState<"translate" | "glossary" | "cache">("translate");
  const [usage, setUsage] = useState<Usage | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const seekRef = useRef<((t: number) => void) | null>(null);

  const refreshUsage = useCallback(() => {
    getUsage().then(setUsage).catch(() => {});
  }, []);
  useEffect(() => {
    refreshUsage();
  }, [refreshUsage]);

  // Admin mode: set the token once by visiting the site with #admin=YOUR_TOKEN.
  useEffect(() => {
    const params = new URLSearchParams(location.hash.slice(1));
    const t = params.get("admin");
    if (t) {
      setAdminToken(t);
      history.replaceState(null, "", location.pathname + location.search);
    }
    checkAdmin().then(setIsAdmin);
  }, []);

  const poll = useCallback((id: string) => {
    const tick = async () => {
      const st = await getStatus(id);
      setStatus(st);
      if (st.status === "done") {
        const data = await getVideo(id);
        setSegments(data.segments);
        setTitle(data.title);
        refreshUsage();
      } else if (st.status === "error") {
        refreshUsage();
      } else {
        setTimeout(tick, 1500);
      }
    };
    tick();
  }, [refreshUsage]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSegments([]);
    setTitle("");
    try {
      const res = await startTranslate(url);
      setVideoId(res.video_id);
      setStatus(res);
      if (res.status === "done") {
        const data = await getVideo(res.video_id);
        setSegments(data.segments);
        setTitle(data.title);
      } else {
        poll(res.video_id);
      }
    } catch (err: any) {
      setStatus({ status: "error", error: err.message });
      refreshUsage();
    }
  };

  const busy =
    status != null && ["queued", "downloading", "transcribing", "translating"].includes(status.status);

  return (
    <div className="app">
      <header>
        <div className="topbar">
          <h1>Ekwaak Translator</h1>
          <nav className="tabs">
            <button
              className={tab === "translate" ? "tab active" : "tab"}
              onClick={() => setTab("translate")}
            >
              Translate
            </button>
            <button
              className={tab === "glossary" ? "tab active" : "tab"}
              onClick={() => setTab("glossary")}
            >
              Glossary
            </button>
            {isAdmin && (
              <button
                className={tab === "cache" ? "tab active" : "tab"}
                onClick={() => setTab("cache")}
              >
                Cache
              </button>
            )}
          </nav>
        </div>
        {usage && (
          <div className={"usage" + (usage.daily_remaining === 0 ? " maxed" : "")}>
            Today: {usage.daily_used}/{usage.daily_limit} new videos
            {usage.daily_remaining === 0 ? " — daily limit reached" : ` (${usage.daily_remaining} left)`}
            {" · "}cached videos are always free
          </div>
        )}
        {tab === "translate" && (
          <div className="hero">
            <div className="hero-line top">Watch Ekwaak</div>
            <form className="hero-form" onSubmit={onSubmit}>
              <input
                className="hero-input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste a YouTube URL…"
              />
              <button className="hero-btn" disabled={busy}>
                {busy ? "Working…" : "Translate"}
              </button>
            </form>
            <div className="hero-line bottom">Stop Being Shit</div>
          </div>
        )}
      </header>

      {tab === "glossary" && <Glossary editable={isAdmin} />}
      {tab === "cache" && isAdmin && <CachePanel />}

      {tab === "translate" && status?.status === "error" && (
        <div className="error">⚠ {status.error}</div>
      )}

      {tab === "translate" && busy && (
        <div className="progress">
          <div className="bar" style={{ width: `${status?.progress ?? 0}%` }} />
          <span>
            {STATUS_LABEL[status!.status]} {status?.progress ? `${status.progress}%` : ""}
          </span>
        </div>
      )}

      {tab === "translate" && videoId && segments.length > 0 && (
        <main>
          <div className="left">
            <Player
              videoId={videoId}
              onTime={setCurrentTime}
              onReady={(seek) => (seekRef.current = seek)}
            />
            <div className="meta">
              <span>{title}</span>
              <label>
                <input
                  type="checkbox"
                  checked={showOriginal}
                  onChange={(e) => setShowOriginal(e.target.checked)}
                />
                Show 中文
              </label>
            </div>
          </div>
          <Transcript
            segments={segments}
            currentTime={currentTime}
            onSeek={(t) => seekRef.current?.(t)}
            showOriginal={showOriginal}
          />
        </main>
      )}

      <footer className="footer">
        Made by <span className="discord">jyxc</span> on Discord
      </footer>
    </div>
  );
}
