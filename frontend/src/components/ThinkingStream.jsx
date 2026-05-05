// Octopus V2.2 — Cursor-inspired "Thought 3s / Read N files / Planned 2s"
// status stream. Sits inside an assistant reply bubble and animates its
// own dots while the run is still in flight.

import { useEffect, useState } from "react";
import { Brain, BookOpen, ListChecks, Share2, Terminal, FileDiff, Radio } from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";

const ICON = {
  thinking: Brain, reading: BookOpen, plan: ListChecks,
  routing: Share2, command: Terminal, file_diff: FileDiff, bridge: Radio,
};

// A "line" shape: { kind, label, seconds?, count?, done }
export default function ThinkingStream({ lines, running, placeholder }) {
  const { theme } = useZone();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [running]);

  if (!lines?.length && !running) {
    return (
      <div className="px-3 py-2 text-xs mono" style={{ color: "var(--fg-3)" }}>
        {placeholder || "No activity yet."}
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-1 px-3 py-2">
      {lines?.map((l, i) => {
        const Icon = ICON[l.kind] || Brain;
        const ok = l.done !== false;
        return (
          <li key={i} className="flex items-center gap-2 text-[13px]">
            <span className="grid h-4 w-4 place-items-center rounded-full"
                  style={{
                    background: ok ? theme.accent + "22" : "transparent",
                    border: ok ? "none" : `1px solid var(--line-2)`,
                  }}>
              {ok ? <Icon size={10} style={{ color: theme.accent }} /> : null}
            </span>
            <span style={{ color: ok ? "var(--fg-1)" : "var(--fg-3)" }}>
              {l.label}
            </span>
            {typeof l.seconds === "number" && (
              <span className="mono" style={{ color: "var(--fg-3)" }}>
                {l.seconds}s
              </span>
            )}
          </li>
        );
      })}
      {running && (
        <li className="flex items-center gap-2 text-[13px]" style={{ color: "var(--fg-2)" }}>
          <span className="grid h-4 w-4 place-items-center">
            <span className="h-2 w-2 rounded-full anim-breathe"
                  style={{ background: theme.accent, boxShadow: `0 0 8px ${theme.glow}` }} />
          </span>
          <span className="dot-blink mono" style={{ color: "var(--fg-2)" }}>
            Thinking<span>.</span><span>.</span><span>.</span>
          </span>
        </li>
      )}
    </ul>
  );
}
