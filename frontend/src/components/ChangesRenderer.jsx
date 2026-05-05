// Octopus V2.2 — turn-grouped change timeline.
// Eats a flat event list (whatever the backend's pipeline_log emits) and
// groups them by task_id (= turn). Each turn becomes a card with a spine
// of dots; each event is a row styled by kind. Collapses long plan /
// diff / command payloads. Zone-tinted spine on the left.

import { useState, useMemo } from "react";
import cx from "../lib/cx.js";
import {
  ListChecks, Share2, FileDiff, Database, Terminal,
  Radio, MessageSquare, ChevronDown, ChevronRight,
} from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { kindMeta } from "../lib/theme";
import { groupByTurn } from "../hooks/useLiveLog.js";

const ICON = {
  plan: ListChecks, routing: Share2, file_diff: FileDiff,
  memory_write: Database, command: Terminal, bridge: Radio, reply: MessageSquare,
};

export default function ChangesRenderer({ events, focusRole }) {
  const { theme } = useZone();

  const turns = useMemo(() => {
    const list = events || [];
    const filtered = focusRole
      ? list.filter((e) => e.from_agent === focusRole || e.to_agent === focusRole)
      : list;
    return groupByTurn(filtered);
  }, [events, focusRole]);

  if (turns.length === 0) {
    return (
      <div className="px-4 py-10 text-center">
        <div className="mono caps mb-2" style={{ color: "var(--fg-3)" }}>No turns yet</div>
        <div className="text-sm" style={{ color: "var(--fg-2)" }}>
          Send a message to the mesh to see plan / routing / file_diff / memory /
          command / bridge / reply events streamed here.
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-3 py-3">
      {turns.map((t) => (
        <TurnCard key={t.id} turn={t} theme={theme} />
      ))}
    </div>
  );
}

function TurnCard({ turn, theme }) {
  return (
    <article
      className="uui-card overflow-hidden"
      style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}
    >
      <header
        className="flex items-center justify-between border-b px-3 py-2"
        style={{ borderColor: "var(--line-1)", background: "var(--bg-2)" }}
      >
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full anim-breathe"
                style={{ background: theme.accent, boxShadow: `0 0 8px ${theme.glow}` }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Turn</span>
          <span className="mono text-xs" style={{ color: "var(--fg-1)" }}>{turn.id}</span>
        </div>
        <span className="mono text-[11px]" style={{ color: "var(--fg-3)" }}>
          {formatTs(turn.startedAt)} · {turn.events.length} events
        </span>
      </header>

      <div className="relative pl-10 pr-3 py-2">
        {/* Spine */}
        <div className="absolute left-5 top-2 bottom-2 w-px"
             style={{ background: `linear-gradient(180deg, ${theme.accent} 0%, transparent 100%)` }} />
        <ul className="flex flex-col gap-2">
          {turn.events.map((e, i) => (
            <EventRow key={i} evt={e} theme={theme} />
          ))}
        </ul>
      </div>
    </article>
  );
}

function EventRow({ evt, theme }) {
  const [open, setOpen] = useState(false);
  const meta = kindMeta(evt.event_type);
  const Icon = ICON[evt.event_type] || MessageSquare;
  const payload = String(evt.message || evt.payload || "").trim();
  const isLong = payload.length > 140;

  return (
    <li className="relative">
      {/* Node on the spine */}
      <span
        className="absolute -left-[22px] top-1.5 grid h-4 w-4 place-items-center rounded-full"
        style={{ background: meta.color + "33", border: `1px solid ${meta.color}`, boxShadow: `0 0 8px ${meta.color}55` }}
      >
        <Icon size={10} style={{ color: meta.color }} />
      </span>

      <div className="flex items-center gap-2 text-sm">
        <span className="mono caps" style={{ color: meta.color }}>{meta.label}</span>
        {(evt.from_agent || evt.to_agent) && (
          <span className="text-xs" style={{ color: "var(--fg-3)" }}>
            {evt.from_agent || "?"} <span className="mono">→</span> {evt.to_agent || "?"}
          </span>
        )}
        <span className="ml-auto mono text-[11px]" style={{ color: "var(--fg-3)" }}>
          {formatTs(evt.timestamp)}
        </span>
      </div>

      {payload && (
        <div className="mt-1">
          {isLong ? (
            <button
              onClick={() => setOpen((v) => !v)}
              className="flex items-center gap-1 text-[12px]"
              style={{ color: "var(--fg-2)" }}
            >
              {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <span>{open ? "Hide" : "Show"} payload ({payload.length} chars)</span>
            </button>
          ) : null}
          <div
            className={cx(
              "mono text-[12px] whitespace-pre-wrap rounded-md px-2 py-1.5",
              isLong && !open && "line-clamp-2"
            )}
            style={{
              background: "var(--bg-0)",
              color: "var(--fg-1)",
              border: "1px solid var(--line-1)",
              maxHeight: isLong && !open ? 48 : "none",
              overflow: isLong && !open ? "hidden" : "auto",
            }}
          >
            {payload}
          </div>
        </div>
      )}
    </li>
  );
}

function formatTs(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (_) { return String(iso).slice(11, 19); }
}
