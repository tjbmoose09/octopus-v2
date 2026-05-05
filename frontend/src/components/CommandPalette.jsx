// Octopus V2.2 — ⌘K command palette (Untitled UI-inspired).
// Jumps to routes, toggles zone, opens drawer, triggers orchestrator runs.

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Command, MessageSquare, Users, Code2, Mail, CalendarDays,
  Brain, Zap, FolderKanban, Wrench, GitBranch, Database, Cpu,
  Shield, ArrowRight,
} from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { ZONES } from "../lib/theme";

const ITEMS = [
  { id: "go:chat",     label: "Go to Chat",     icon: MessageSquare, path: "/chat" },
  { id: "go:cowork",   label: "Go to Cowork",   icon: Users,         path: "/cowork" },
  { id: "go:code",     label: "Go to Code",     icon: Code2,         path: "/code" },
  { id: "go:email",    label: "Go to Email",    icon: Mail,          path: "/email" },
  { id: "go:calendar", label: "Go to Calendar", icon: CalendarDays,  path: "/calendar" },
  { id: "go:agents",   label: "Legacy: Agents", icon: Brain,         path: "/overflow/agents" },
  { id: "go:pipeline", label: "Legacy: Pipeline", icon: Zap,         path: "/overflow/pipeline" },
  { id: "go:projects", label: "Legacy: Projects", icon: FolderKanban, path: "/overflow/projects" },
  { id: "go:skills",   label: "Legacy: Skills", icon: Wrench,        path: "/overflow/skills" },
  { id: "go:mcp",      label: "Legacy: MCP",    icon: GitBranch,     path: "/overflow/mcp" },
  { id: "go:memory",   label: "Legacy: Memory", icon: Database,      path: "/overflow/memory" },
  { id: "go:system",   label: "Legacy: System", icon: Cpu,           path: "/overflow/system" },
  { id: "zone:toggle", label: "Toggle Hacker Zone", icon: Shield,    action: "zone" },
];

export default function CommandPalette({ open, onClose }) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const inputRef = useRef(null);
  const nav = useNavigate();
  const { zone, setZone } = useZone();

  useEffect(() => { if (open) { setQ(""); setIdx(0); setTimeout(() => inputRef.current?.focus(), 10); } }, [open]);

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase();
    if (!qq) return ITEMS;
    return ITEMS.filter((i) => i.label.toLowerCase().includes(qq));
  }, [q]);

  function act(item) {
    if (item.path) nav(item.path);
    if (item.action === "zone") setZone(zone === ZONES.HACKER ? ZONES.MAINLINE : ZONES.HACKER, "Command palette");
    onClose?.();
  }

  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); onClose?.(); }
    if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
    if (e.key === "Enter")     { e.preventDefault(); const it = filtered[idx]; if (it) act(it); }
  }

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[10vh]"
      style={{ background: "rgba(5,7,13,0.65)", backdropFilter: "blur(6px)" }}
      onClick={onClose}
    >
      <div
        className="uui-card w-full max-w-xl overflow-hidden anim-slide-up"
        style={{ background: "var(--bg-1)", borderColor: "var(--line-2)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b px-3 py-2"
             style={{ borderColor: "var(--line-1)" }}>
          <Command size={14} style={{ color: "var(--fg-2)" }} />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setIdx(0); }}
            onKeyDown={onKey}
            placeholder="Jump to… or run…"
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: "var(--fg-0)" }}
          />
          <kbd className="mono rounded border px-1 py-0.5 text-[10px]"
               style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}>esc</kbd>
        </div>
        <ul className="scrollbar-thin max-h-[55vh] overflow-y-auto py-1">
          {filtered.map((it, i) => {
            const Icon = it.icon;
            const active = i === idx;
            return (
              <li key={it.id}>
                <button
                  onClick={() => act(it)}
                  onMouseEnter={() => setIdx(i)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm"
                  style={{
                    background: active ? "var(--bg-2)" : "transparent",
                    color: "var(--fg-1)",
                  }}
                >
                  <Icon size={14} style={{ color: "var(--fg-3)" }} />
                  <span className="flex-1 text-left">{it.label}</span>
                  {active && <ArrowRight size={14} style={{ color: "var(--fg-3)" }} />}
                </button>
              </li>
            );
          })}
          {filtered.length === 0 && (
            <li className="px-3 py-6 text-center text-sm" style={{ color: "var(--fg-3)" }}>
              No matches.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
