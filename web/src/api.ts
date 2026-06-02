export type Segment = { start: number; end: number; zh: string; en: string };
export type Status = {
  status: "queued" | "downloading" | "transcribing" | "translating" | "done" | "error" | "unknown";
  progress?: number;
  title?: string;
  error?: string;
};

export async function startTranslate(url: string): Promise<{ video_id: string } & Status> {
  const r = await fetch("/api/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Request failed");
  return r.json();
}

export async function getStatus(videoId: string): Promise<Status> {
  const r = await fetch(`/api/status/${videoId}`);
  return r.json();
}

export async function getVideo(
  videoId: string
): Promise<{ video_id: string; title: string; segments: Segment[] }> {
  const r = await fetch(`/api/video/${videoId}`);
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
  const r = await fetch("/api/usage");
  return r.json();
}

export type CachedVideo = { video_id: string; title: string; url: string; created: number };

export async function listCache(): Promise<CachedVideo[]> {
  const r = await fetch("/api/cache");
  return (await r.json()).videos;
}

export async function deleteCached(videoId: string): Promise<void> {
  await fetch(`/api/cache/${videoId}`, { method: "DELETE" });
}

export async function clearCache(): Promise<number> {
  const r = await fetch("/api/cache", { method: "DELETE" });
  return (await r.json()).cleared;
}

export type Term = { zh: string; en: string; note?: string };

export async function getGlossary(): Promise<Term[]> {
  const r = await fetch("/api/glossary");
  return (await r.json()).terms;
}

export async function saveGlossary(terms: Term[]): Promise<Term[]> {
  const r = await fetch("/api/glossary", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms }),
  });
  if (!r.ok) throw new Error("Save failed");
  return (await r.json()).terms;
}
