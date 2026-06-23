import { useEffect, useState } from "react";
import { getCookieStatus, saveCookies, type CookieStatus } from "../api";

export default function Cookies() {
  const [status, setStatus] = useState<CookieStatus | null>(null);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const refresh = () => getCookieStatus().then(setStatus).catch(() => {});
  useEffect(() => { refresh(); }, []);

  const onSave = async () => {
    setError("");
    setSaved(false);
    if (!text.trim().startsWith("# Netscape")) {
      setError("That doesn't look like a cookies.txt export (should start with '# Netscape HTTP Cookie File').");
      return;
    }
    setSaving(true);
    try {
      await saveCookies(text.trim() + "\n");
      setText("");
      setSaved(true);
      refresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="cookies">
      <h3>YouTube cookies</h3>
      <p className="hint">
        YouTube blocks the server's IP without login cookies, and they expire every
        couple of weeks. When downloads start failing with a "confirm you're not a bot"
        error, refresh them here — no redeploy needed.
      </p>

      <div className="cookie-status">
        {status?.set ? (
          <>
            <span className="ok">✓ Cookies set</span>
            <span>{status.lines} lines</span>
            {status.updated && (
              <span>updated {new Date(status.updated * 1000).toLocaleString()}</span>
            )}
          </>
        ) : (
          <span className="warn">⚠ No cookies set</span>
        )}
      </div>

      <ol className="cookie-steps">
        <li>In Brave/Chrome, signed into the throwaway YouTube account, open the <b>"Get cookies.txt LOCALLY"</b> extension on youtube.com.</li>
        <li>Click <b>Export</b>, open the file, copy everything.</li>
        <li>Paste it below and hit <b>Save cookies</b>.</li>
      </ol>

      <textarea
        className="cookie-box"
        placeholder="# Netscape HTTP Cookie File&#10;.youtube.com  TRUE  /  TRUE  ..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
      />
      {error && <div className="login-error">{error}</div>}
      <button className="cookie-save" onClick={onSave} disabled={saving || !text.trim()}>
        {saving ? "Saving…" : saved ? "✓ Saved" : "Save cookies"}
      </button>
    </div>
  );
}
