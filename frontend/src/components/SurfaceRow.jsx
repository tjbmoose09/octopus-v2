// Octopus V2.2 — Cursor-inspired "surface" row.
// Thin strip under TopBar that tells the user where the current run is
// targeting: Desktop (editor), Terminal (shell), Web (browser), or
// Extension (MCP tool). Mirrors Cursor's "Use Cursor everywhere you work"
// triptych and doubles as a filter — click a surface to scope the
// ChangesRenderer to events tagged with that surface.

import { useState } from "react";
import { Monitor, TerminalSquare, Globe, Puzzle } from "lucide-react";
import cx from "../lib/cx.js";
import { useZone } from "../hooks/useZone.jsx";

const SURFACES = [
  { id: "desktop",  label: "Desktop",   icon: Monitor,
    hint: "Editor + file tools (Read/Write/Edit)",
    status: "/ commands · @ files · shift+tab plans · desktop tools armed" },
  { id: "terminal", label: "Terminal",  icon: TerminalSquare,
    hint: "Bash sandbox, commands, pipes",
    status: "! shell · | pipes · $ commands · terminal routed to sandbox" },
  { id: "web",      label: "Web",       icon: Globe,
    hint: "Browser agent + WebFetch + WebSearch",
    status: "@ url · / search · web agent routed to browser surface" },
  { id: "ext",      label: "Extension", icon: Puzzle,
    hint: "MCP servers (Obsidian, Gmail, GitHub…)",
    status: "@ mcp · / tools · extension routed to connected servers" },
];

export default function SurfaceRow({ active, onChange }) {
  const { theme } = useZone();
  const [local, setLocal] = useState(active || "desktop");
  const selected = active ?? local;
  const current = SURFACES.find((s) => s.id === selected) ?? SURFACES[0];
  function pick(id) {
    setLocal(id);
    onChange?.(id);
  }
  return (
    <div
      className="flex items-center gap-2 border-b px-3 py-2"
      style={{ borderColor: "var(--line-1)", background: "var(--bg-0)" }}
    >
      <span className="mono caps mr-1" style={{ color: "var(--fg-3)" }}>Surface</span>
      <div
        className="flex items-center gap-1 rounded-xl border p-1"
        style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}
      >
        {SURFACES.map(({ id, label, icon: Icon, hint }) => {
          const is = selected === id;
          return (
            <button
              key={id}
              onClick={() => pick(id)}
              title={hint}
              className={cx(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs transition-all"
              )}
              style={{
                background: is ? theme.accent : "transparent",
                color: is ? "#ffffff" : "var(--fg-2)",
                border: `1px solid ${is ? theme.accent : "transparent"}`,
                boxShadow: is ? `0 0 12px -2px ${theme.glow || theme.accent}` : "none",
              }}
            >
              <Icon size={12} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-2 mono truncate"
           style={{ color: "var(--fg-3)", fontSize: 11, maxWidth: "60%" }}>
        <span
          className="rounded-md px-1.5 py-0.5"
          style={{
            background: "var(--bg-2)",
            color: theme.accent,
            border: `1px solid ${theme.accent}55`,
          }}
        >
          {current.label}
        </span>
        <span className="truncate hidden md:inline">{current.status}</span>
      </div>
    </div>
  );
}
