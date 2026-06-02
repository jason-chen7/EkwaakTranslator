import { useEffect, useState } from "react";
import { clearCache, deleteCached, listCache, type CachedVideo } from "../api";

export default function CachePanel() {
  const [videos, setVideos] = useState<CachedVideo[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) return <div className="cachepanel">Loading cache…</div>;

  return (
    <div className="cachepanel">
      <div className="cache-bar">
        <span className="count">{videos.length} cached videos</span>
        <button className="refresh" onClick={refresh}>Refresh</button>
        <button className="clear" onClick={onClearAll} disabled={!videos.length}>
          Clear all
        </button>
      </div>
      <p className="hint">
        Cached videos are free to replay and don't count against the daily limit.
        After a big glossary update, <b>Clear all</b> so videos re-translate with the new vocab.
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
              <button className="del" onClick={() => onDelete(v.video_id)} title="Delete">✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
