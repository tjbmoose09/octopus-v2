// Octopus V2.2 — /code page.
// Cursor-style three-pane: file tree, editor, diff/output. The "editor"
// is read-only for now (the engine owns writes) — this surface streams
// file_diff events from /ws and lets the user eyeball what the agent
// changed. Clicking a file in the tree filters the ChangesRenderer.

import { useEffect, useMemo, useState } from "react";
import { FolderGit2, FileCode2, FileDiff, Copy } from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { useLiveLog } from "../hooks/useLiveLog.js";
import ChangesRenderer from "../components/ChangesRenderer.jsx";

export default function CodePage() {
  const { theme } = useZone();
  const { events } = useLiveLog();
  const [selected, setSelected] = useState(null);

  const files = useMemo(() => deriveFileList(events), [events]);
  const fileEvents = useMemo(
    () => (selected ? events.filter((e) => (e.message || "").includes(selected)) : events.filter((e) => e.event_type === "file_diff")),
    [events, selected]
  );

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "240px 1fr 360px" }}>
      {/* File tree */}
      <section className="flex min-h-0 flex-col border-r"
               style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-2"
             style={{ borderColor: "var(--line-1)" }}>
          <FolderGit2 size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Files</span>
          <span className="ml-auto mono text-[10px]" style={{ color: "var(--fg-3)" }}>
            from file_diff events
          </span>
        </div>
        <ul className="scrollbar-thin flex-1 overflow-y-auto px-1 py-1">
          {files.length === 0 && (
            <li className="mono px-3 py-3 text-xs" style={{ color: "var(--fg-3)" }}>
              No file changes yet.
            </li>
          )}
          {files.map((f) => {
            const active = selected === f.path;
            return (
              <li key={f.path}>
                <button
                  onClick={() => setSelected(active ? null : f.path)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px]"
                  style={{
                    background: active ? "var(--accent-soft)" : "transparent",
                    color: "var(--fg-1)",
                  }}
                >
                  <FileCode2 size={12} style={{ color: active ? theme.accent : "var(--fg-3)" }} />
                  <span className="mono truncate">{f.path}</span>
                  <span className="ml-auto mono text-[10px]" style={{ color: "var(--fg-3)" }}>×{f.count}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Editor (preview) */}
      <section className="flex min-h-0 flex-col" style={{ background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-2"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <FileDiff size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>
            {selected || "latest diff"}
          </span>
          <button
            onClick={() => navigator.clipboard.writeText(fileEvents.map((e) => e.message || "").join("\n\n"))}
            className="ml-auto flex items-center gap-1 mono rounded-md border px-2 py-0.5 text-[11px]"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
            title="Copy diff text"
          ><Copy size={11} /> copy</button>
        </div>
        <div className="scrollbar-thin flex-1 overflow-auto p-4">
          {fileEvents.length === 0 ? (
            <div className="mono text-xs" style={{ color: "var(--fg-3)" }}>
              Waiting for file_diff events…
            </div>
          ) : (
            <pre className="mono text-[12px] leading-relaxed whitespace-pre-wrap"
                 style={{ color: "var(--fg-1)" }}>
              {fileEvents.map((e, i) => colorize(e.message || "")).join("\n\n")}
            </pre>
          )}
        </div>
      </section>

      {/* Right: change timeline */}
      <aside className="flex min-h-0 flex-col border-l"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-2"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Timeline</span>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto">
          <ChangesRenderer events={events} />
        </div>
      </aside>
    </div>
  );
}

function deriveFileList(events) {
  const counts = new Map();
  for (const e of events) {
    if (e.event_type !== "file_diff") continue;
    const m = String(e.message || "").match(/([\w./-]+\.[\w]+)/);
    if (!m) continue;
    counts.set(m[1], (counts.get(m[1]) || 0) + 1);
  }
  return [...counts.entries()].map(([path, count]) => ({ path, count }));
}

function colorize(line) {
  // No syntax highlighting dependency — just a readable pre block.
  return line;
}
