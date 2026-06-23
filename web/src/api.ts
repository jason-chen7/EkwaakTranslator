// In dev, VITE_API_BASE is unset -> calls are relative ("/api/...") and the
// Vite proxy forwards them to the local FastAPI server.
// In production (Netlify), set VITE_API_BASE to your deployed backend URL,
// e.g. https://ekwaak-api.onrender.com
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

// Admin token (for editing the glossary / cache) is stored locally and sent as
// a header. It's set once via a #admin=TOKEN URL fragment.
export function setAdminToken(t: string) {
  localStorage.setItem("ekwaak_admin", t);
}
export function clearAdminToken() {
  localStorage.removeItem("ekwaak_admin");
}
export function hasAdminToken(): boolean {
  return !!localStorage.getItem("ekwaak_admin");
}
function adminHeaders(): Record<string, string> {
  const t = localStorage.getItem("ekwaak_admin");
  return t ? { "X-Admin-Token": t } : {};
}
export async function checkAdmin(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/api/admin-check`, { headers: adminHeaders() });
    return (await r.json()).is_admin === true;
  } catch {
    return false;
  }
}

export type Segment = { start: number; end: number; zh: string; en: string };
export type Status = {
  status: "queued" | "downloading" | "transcribing" | "translating" | "done" | "error" | "unknown";
  progress?: number;
  title?: string;
  error?: string;
};

export async function startTranslate(url: string): Promise<{ video_id: string } & Status> {
  const r = await fetch(`${API_BASE}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Request failed");
  return r.json();
}

export async function getStatus(videoId: string): Promise<Status> {
  const r = await fetch(`${API_BASE}/api/status/${videoId}`);
  return r.json();
}

export async function getVideo(
  videoId: string
): Promise<{ video_id: string; title: string; segments: Segment[] }> {
  const r = await fetch(`${API_BASE}/api/video/${videoId}`);
  if (!r.ok) throw new Error("Not ready");
  return r.json();
}

export type Usage = {
  daily_used: number;
  daily_limit: number;
  daily_remaining: number;
  window_minutes: number;
  window_max: number;
};

export async function getUsage(): Promise<Usage> {
  const r = await fetch(`${API_BASE}/api/usage`);
  return r.json();
}

export type CachedVideo = { video_id: string; title: string; url: string; created: number };

export async function listCache(): Promise<CachedVideo[]> {
  const r = await fetch(`${API_BASE}/api/cache`);
  return (await r.json()).videos;
}

export async function deleteCached(videoId: string): Promise<void> {
  await fetch(`${API_BASE}/api/cache/${videoId}`, {
    method: "DELETE",
    headers: adminHeaders(),
  });
}

export async function clearCache(): Promise<number> {
  const r = await fetch(`${API_BASE}/api/cache`, {
    method: "DELETE",
    headers: adminHeaders(),
  });
  return (await r.json()).cleared;
}

export async function retranslateCached(videoId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/cache/${videoId}/retranslate`, {
    method: "POST",
    headers: adminHeaders(),
  });
  if (r.status === 403) throw new Error("Admin only.");
  if (!r.ok) throw new Error("Re-translate failed");
}

export type LogEntry = {
  ts: number;
  ip: string;
  video_id: string | null;
  event: string;
  detail: string | null;
};

export async function getLogs(): Promise<LogEntry[]> {
  const r = await fetch(`${API_BASE}/api/logs`, { headers: adminHeaders() });
  return (await r.json()).logs;
}

export type Stats = {
  total_requests: number;
  requests_24h: number;
  unique_ips: number;
  new_translations: number;
  cache_hits: number;
  errors: number;
  cache_hit_rate: number;
  top_videos: { video_id: string; count: number }[];
};

export async function getStats(): Promise<Stats> {
  const r = await fetch(`${API_BASE}/api/stats`, { headers: adminHeaders() });
  return r.json();
}

export type CookieStatus = { set: boolean; updated: number | null; lines: number };

export async function getCookieStatus(): Promise<CookieStatus> {
  const r = await fetch(`${API_BASE}/api/cookies`, { headers: adminHeaders() });
  return r.json();
}

export async function saveCookies(cookies: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/cookies`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...adminHeaders() },
    body: JSON.stringify({ cookies }),
  });
  if (r.status === 403) throw new Error("Admin only.");
  if (!r.ok) throw new Error("Save failed");
}

export type Term = { zh: string; en: string; note?: string };

export async function getGlossary(): Promise<Term[]> {
  const r = await fetch(`${API_BASE}/api/glossary`);
  return (await r.json()).terms;
}

export async function saveGlossary(terms: Term[]): Promise<Term[]> {
  const r = await fetch(`${API_BASE}/api/glossary`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...adminHeaders() },
    body: JSON.stringify({ terms }),
  });
  if (r.status === 403) throw new Error("Editing is admin-only.");
  if (!r.ok) throw new Error("Save failed");
  return (await r.json()).terms;
}
