import { useEffect, useState } from "react";
import { getLogs, getStats, type LogEntry, type Stats } from "../api";

const EVENT_LABEL: Record<string, string> = {
  request: "request",
  cache_hit: "cache hit",
  new: "new job",
  done: "done",
  error: "error",
  rate_limited: "rate limited",
  bad_url: "bad url",
};

function fmtTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

export default function Logs() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    Promise.all([getStats(), getLogs()]).then(([s, l]) => {
      setStats(s);
      setEntries(l);
      setLoading(false);
    });
  };

  useEffect(refresh, []);

  if (loading) return <div className="logs">Loading logs…</div>;

  return (
    <div className="logs">
      <div className="logs-bar">
        <h3>Usage & logs</h3>
        <button className="refresh" onClick={refresh}>Refresh</button>
      </div>

      {stats && (
        <div className="stat-cards">
          <div className="stat"><b>{stats.total_requests}</b><span>requests</span></div>
          <div className="stat"><b>{stats.requests_24h}</b><span>last 24h</span></div>
          <div className="stat"><b>{stats.unique_ips}</b><span>unique IPs</span></div>
          <div className="stat"><b>{stats.new_translations}</b><span>new translations</span></div>
          <div className="stat"><b>{stats.cache_hits}</b><span>cache hits</span></div>
          <div className="stat"><b>{stats.cache_hit_rate}%</b><span>cache hit rate</span></div>
          <div className="stat"><b>{stats.errors}</b><span>errors</span></div>
        </div>
      )}

      <div className="logtable">
        <div className="loghead">
          <span>Time</span>
          <span>IP</span>
          <span>Event</span>
          <span>Video</span>
          <span>Detail</span>
        </div>
        {entries.map((e, i) => (
          <div className={"logrow ev-" + e.event} key={i}>
            <span className="lt">{fmtTime(e.ts)}</span>
            <span className="lip">{e.ip}</span>
            <span className="lev">{EVENT_LABEL[e.event] ?? e.event}</span>
            <span className="lvid">
              {e.video_id ? (
                <a href={`https://youtu.be/${e.video_id}`} target="_blank" rel="noreferrer">
                  {e.video_id}
                </a>
              ) : (
                "—"
              )}
            </span>
            <span className="ldetail" title={e.detail ?? ""}>{e.detail ?? ""}</span>
          </div>
        ))}
        {entries.length === 0 && <div className="empty">No log entries yet.</div>}
      </div>
    </div>
  );
}
