import { useEffect, useState } from "react";
import {
  clearCache,
  deleteCached,
  listCache,
  retranslateCached,
  type CachedVideo,
} from "../api";

export default function CachePanel() {
  const [videos, setVideos] = useState<CachedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null); // video_id being worked on, or "all"

  const refresh = () => {
    setLoading(true);
    listCache().then((v) => {
      setVideos(v);
      setLoading(false);
    });
  };

  useEffect(refresh, []);

  const onDelete = async (id: string) => {
    await deleteCached(id);
    refresh();
  };

  const onClearAll = async () => {
    if (!confirm("Clear ALL cached videos? They'll re-translate (and re-cost) on next submit.")) return;
    await clearCache();
    refresh();
  };

  const onRetranslate = async (id: string) => {
    setBusy(id);
    try {
      await retranslateCached(id);
    } finally {
      setBusy(null);
    }
  };

  const onRetranslateAll = async () => {
    if (!confirm(`Re-translate all ${videos.length} cached videos with the current glossary?`)) return;
    setBusy("all");
    try {
      for (const v of videos) await retranslateCached(v.video_id);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="cachepanel">Loading cache…</div>;

  const working = busy !== null;

  return (
    <div className="cachepanel">
      <div className="cache-bar">
        <span className="count">{videos.length} cached videos</span>
        <button className="refresh" onClick={refresh} disabled={working}>Refresh</button>
        <button className="retranslate-all" onClick={onRetranslateAll} disabled={working || !videos.length}>
          {busy === "all" ? "Re-translating…" : "Re-translate all"}
        </button>
        <button className="clear" onClick={onClearAll} disabled={working || !videos.length}>
          Clear all
        </button>
      </div>
      <p className="hint">
        Cached videos are free to replay and don't count against the daily limit.
        <b> Re-translate</b> re-runs only the (cheap) translation step with the current
        glossary — no re-download or re-transcribe. After a big glossary update, hit
        <b> Re-translate all</b>.
      </p>

      {videos.length === 0 ? (
        <div className="empty">No videos cached yet.</div>
      ) : (
        <div className="ctable">
          {videos.map((v) => (
            <div className="crow" key={v.video_id}>
              <div className="cinfo">
                <a href={v.url} target="_blank" rel="noreferrer">{v.url}</a>
                <div className="ctitle">{v.title}</div>
              </div>
              <button
                className="retrans"
                onClick={() => onRetranslate(v.video_id)}
                disabled={working}
              >
                {busy === v.video_id ? "…" : "Re-translate"}
              </button>
              <button className="del" onClick={() => onDelete(v.video_id)} disabled={working} title="Delete">✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
