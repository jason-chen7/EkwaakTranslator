import { useEffect, useState } from "react";
import { getGlossary, saveGlossary, type Term } from "../api";

export default function Glossary({ editable }: { editable: boolean }) {
  const [terms, setTerms] = useState<Term[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    getGlossary().then((t) => {
      setTerms(t);
      setLoading(false);
    });
  }, []);

  const update = (i: number, key: keyof Term, value: string) => {
    setTerms((prev) => prev.map((t, j) => (j === i ? { ...t, [key]: value } : t)));
    setSaved(false);
  };

  const addRow = () => {
    setTerms((prev) => [{ zh: "", en: "", note: "" }, ...prev]);
    setSaved(false);
  };

  const removeRow = (i: number) => {
    setTerms((prev) => prev.filter((_, j) => j !== i));
    setSaved(false);
  };

  const onSave = async () => {
    setSaving(true);
    const cleaned = await saveGlossary(terms);
    setTerms(cleaned);
    setSaving(false);
    setSaved(true);
  };

  if (loading) return <div className="glossary">Loading glossary…</div>;

  const shown = terms
    .map((t, i) => ({ t, i }))
    .filter(
      ({ t }) =>
        !filter ||
        t.zh.includes(filter) ||
        t.en.toLowerCase().includes(filter.toLowerCase())
    );

  return (
    <div className="glossary">
      <div className="glossary-bar">
        {editable && <button className="add" onClick={addRow}>+ Add term</button>}
        <input
          className="filter"
          placeholder="Filter…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="count">{terms.length} terms</span>
        {editable && (
          <button className="save" onClick={onSave} disabled={saving}>
            {saving ? "Saving…" : saved ? "✓ Saved" : "Save changes"}
          </button>
        )}
      </div>

      <div className={"gtable" + (editable ? "" : " readonly")}>
        <div className="ghead">
          <span>中文</span>
          <span>English</span>
          <span>Note</span>
          {editable && <span />}
        </div>
        {shown.map(({ t, i }) => (
          <div className="grow" key={i}>
            <input value={t.zh} readOnly={!editable} onChange={(e) => update(i, "zh", e.target.value)} placeholder="中文" />
            <input value={t.en} readOnly={!editable} onChange={(e) => update(i, "en", e.target.value)} placeholder="English" />
            <input value={t.note ?? ""} readOnly={!editable} onChange={(e) => update(i, "note", e.target.value)} placeholder="note" />
            {editable && <button className="del" onClick={() => removeRow(i)} title="Delete">✕</button>}
          </div>
        ))}
      </div>
      <p className="hint">
        {editable
          ? "Changes apply to the next video you translate. Empty rows are dropped on save."
          : "This is the Clash of Clans slang dictionary used for translations (read-only)."}
      </p>
    </div>
  );
}
