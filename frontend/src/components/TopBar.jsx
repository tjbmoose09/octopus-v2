// Octopus V2.2 — persistent TopBar.
// Three primary routes + two workflow routes + an overflow menu that
// holds the pre-V2.2 pages (Agents / Pipeline / Projects / Skills / MCP /
// Memory / System). Cursor-style command-palette launcher pinned on the
// right next to the Hacker-Zone badge.

import { NavLink } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import cx from "../lib/cx.js";
import {
  MessageSquare, Users, Code2, Mail, CalendarDays,
  Sparkles, MoreHorizontal, Brain, Zap, FolderKanban,
  Wrench, GitBranch, Database, Cpu, Command, Search,
} from "lucide-react";
import ZoneBadge from "./ZoneBadge.jsx";
import { useZone } from "../hooks/useZone.jsx";

const PRIMARY = [
  { path: "/chat",     icon: MessageSquare, label: "Chat" },
  { path: "/cowork",   icon: Users,         label: "Cowork" },
  { path: "/code",     icon: Code2,         label: "Code" },
];

const WORKFLOW = [
  { path: "/email",    icon: Mail,          label: "Email" },
  { path: "/calendar", icon: CalendarDays,  label: "Calendar" },
];

const OVERFLOW = [
  { path: "/overflow/agents",   icon: Brain,        label: "Agents" },
  { path: "/overflow/pipeline", icon: Zap,          label: "Pipeline" },
  { path: "/overflow/projects", icon: FolderKanban, label: "Projects" },
  { path: "/overflow/skills",   icon: Wrench,       label: "Skills" },
  { path: "/overflow/mcp",      icon: GitBranch,    label: "MCP" },
  { path: "/overflow/memory",   icon: Database,     label: "Memory" },
  { path: "/overflow/system",   icon: Cpu,          label: "System" },
];

export default function TopBar({ onOpenPalette }) {
  const { theme, isHacker } = useZone();
  return (
    <header
      className="sticky top-0 z-30 flex h-14 items-center gap-2 px-3 backdrop-blur zone-glow"
      style={{
        background: "color-mix(in oklab, var(--bg-1) 85%, transparent)",
        borderBottom: "1px solid var(--line-1)",
      }}
    >
      {/* Logo */}
      <div className="flex shrink-0 items-center gap-2 pr-3">
        <div
          className="grid h-9 w-9 place-items-center rounded-xl"
          style={{
            background: `linear-gradient(135deg, ${theme.accent} 0%, ${theme.edgeColor} 100%)`,
            boxShadow: `0 0 16px -4px ${theme.glow}`,
          }}
        >
          <Sparkles size={18} className="text-white" />
        </div>
        <div className="hidden md:block leading-tight">
          <div className="text-sm font-semibold tracking-tight" style={{ color: "var(--fg-0)" }}>
            Octopus <span style={{ color: theme.accent }}>V2.2</span>
          </div>
          <div className="mono caps" style={{ color: "var(--fg-3)" }}>{theme.label}</div>
        </div>
      </div>

      {/* Primary tabs */}
      <nav className="flex items-center gap-1 rounded-xl border p-1"
           style={{ borderColor: "var(--line-1)", background: "var(--bg-2)" }}>
        {PRIMARY.map(({ path, icon: Icon, label }) => (
          <TabLink key={path} to={path} Icon={Icon} label={label} />
        ))}
      </nav>

      {/* Workflow tabs */}
      <nav className="flex items-center gap-1 rounded-xl border p-1"
           style={{ borderColor: "var(--line-1)", background: "var(--bg-2)" }}>
        {WORKFLOW.map(({ path, icon: Icon, label }) => (
          <TabLink key={path} to={path} Icon={Icon} label={label} tone="soft" />
        ))}
      </nav>

      {/* Overflow */}
      <OverflowMenu />

      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={onOpenPalette}
          className="group flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs transition-colors"
          style={{ borderColor: "var(--line-1)", background: "var(--bg-2)", color: "var(--fg-2)" }}
          title="Command palette (⌘K)"
        >
          <Search size={13} />
          <span>Search or run…</span>
          <kbd className="mono rounded border px-1 py-0.5 text-[10px]"
               style={{ borderColor: "var(--line-2)", color: "var(--fg-3)" }}>⌘K</kbd>
        </button>
        <ZoneBadge />
      </div>
    </header>
  );
}

function TabLink({ to, Icon, label, tone }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cx(
          "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-all",
          isActive
            ? "shadow-sm"
            : "hover:bg-[color-mix(in_oklab,var(--bg-3)_60%,transparent)] text-[color:var(--fg-2)]"
        )
      }
      style={({ isActive }) =>
        isActive
          ? {
              background: tone === "soft" ? "var(--bg-3)" : "var(--accent-soft)",
              color: "var(--fg-0)",
              border: `1px solid ${tone === "soft" ? "var(--line-2)" : "var(--accent)"}`,
            }
          : undefined
      }
    >
      <Icon size={14} />
      <span>{label}</span>
    </NavLink>
  );
}

function OverflowMenu() {
  const [open, setOpen] = useState(false);
  const wrap = useRef(null);
  useEffect(() => {
    function away(e) { if (wrap.current && !wrap.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, []);
  return (
    <div className="relative" ref={wrap}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm transition-colors"
        style={{ borderColor: "var(--line-1)", background: "var(--bg-2)", color: "var(--fg-2)" }}
        title="Legacy & deeper tools"
      >
        <MoreHorizontal size={16} />
      </button>
      {open && (
        <div
          className="absolute left-0 top-11 w-64 rounded-xl border p-2 shadow-2xl anim-slide-up"
          style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}
          onClick={() => setOpen(false)}
        >
          <div className="mono caps px-2 pb-1" style={{ color: "var(--fg-3)" }}>Legacy tools</div>
          <ul className="flex flex-col gap-0.5">
            {OVERFLOW.map(({ path, icon: Icon, label }) => (
              <li key={path}>
                <NavLink
                  to={path}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[color-mix(in_oklab,var(--bg-3)_70%,transparent)]"
                  style={{ color: "var(--fg-1)" }}
                >
                  <Icon size={14} style={{ color: "var(--fg-3)" }} />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
