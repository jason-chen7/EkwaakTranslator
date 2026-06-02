import { useEffect, useRef } from "react";
import type { Segment } from "../api";

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

type Props = {
  segments: Segment[];
  currentTime: number;
  onSeek: (t: number) => void;
  showOriginal: boolean;
};

export default function Transcript({ segments, currentTime, onSeek, showOriginal }: Props) {
  const activeIdx = segments.findIndex(
    (s) => currentTime >= s.start && currentTime < s.end
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeIdx]);

  return (
    <div className="transcript" ref={containerRef}>
      {segments.map((s, i) => (
        <div
          key={i}
          ref={i === activeIdx ? activeRef : undefined}
          className={"line" + (i === activeIdx ? " active" : "")}
          onClick={() => onSeek(s.start)}
        >
          <span className="ts">{fmt(s.start)}</span>
          <div className="text">
            <div className="en">{s.en}</div>
            {showOriginal && <div className="zh">{s.zh}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
