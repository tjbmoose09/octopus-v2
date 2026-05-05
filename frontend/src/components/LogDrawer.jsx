// Octopus V2.2 — bottom slide-out event drawer.
// Always mounted; keyboard `L` toggles expanded/collapsed. Filters by
// event kind, by task-id substring, and by agent role. Tints to the
// active zone.

import { useEffect, useMemo, useRef, useState } from "react";
import cx from "../lib/cx.js";
import { ChevronUp, ChevronDown, X, Wifi, WifiOff, Plug } from "lucide-react";
import { kindMeta } from "../lib/theme";
import { useZone } from "../hooks/useZone.jsx";
import { useLiveLog } from "../hooks/useLiveLog.js";

const KINDS = ["plan", "routing", "file_diff", "memory_write", "command", "bridge", "reply"];

export default function LogDrawer() {
  const { theme } = useZone();
  const { events, status, clear } = useLiveLog();
  const [open, setOpen] = useState(false);
  const [filterKinds, setFilterKinds] = useState(() => new Set(KINDS));
  const [query, setQuery] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "l" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events.filter((e) => {
      if (!filterKinds.has(e.event_type) && e.event_type !== "raw") return false;
      if (!q) return true;
      const hay = `${e.task_id || ""} ${e.from_agent || ""} ${e.to_agent || ""} ${e.message || ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [events, filterKinds, query]);

  useEffect(() => {
    if (!open) return;
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [filtered.length, open]);

  function toggleKind(k) {
    setFilterKinds((prev) => {
      const n = new Set(prev);
      if (n.has(k)) n.delete(k); else n.add(k);
      return n;
    });
  }

  const connIcon = status.state === "open" ? Wifi : status.state === "connecting" ? Plug : WifiOff;
  const ConnIcon = connIcon;

  return (
    <section
      className="shrink-0 border-t"
      style={{
        borderColor: "var(--line-1)",
        background: "var(--bg-1)",
        height: open ? 280 : 36,
        transition: "height 180ms ease",
      }}
    >
      <header
        className="flex h-9 items-center gap-2 px-3 cursor-pointer select-none"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        <span className="mono caps" style={{ color: "var(--fg-2)" }}>Log</span>

        <span className="flex items-center gap-1 rounded-md border px-1.5 py-0.5 mono text-[11px]"
              style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}>
          <ConnIcon size={11} style={{
            color: status.state === "open" ? "#3ce28f" :
                   status.state === "error" ? "#ff5a78" : "#ffb84a",
          }} />
          {status.state}
        </span>

        <span className="mono text-[11px]" style={{ color: "var(--fg-3)" }}>
          {filtered.length}/{events.length} events
        </span>

        <div className="ml-auto flex items-center gap-2"
             onClick={(e) => e.stopPropagation()}>
          {open && (
            <>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="filter by id / agent / text…"
                className="mono rounded-md border px-2 py-0.5 text-[11px]"
                style={{
                  background: "var(--bg-0)",
                  color: "var(--fg-1)",
                  borderColor: "var(--line-1)",
                  width: 220,
                }}
              />
              <button
                onClick={clear}
                className="mono caps rounded border px-2 py-0.5 text-[10px]"
                style={{ color: "var(--fg-2)", borderColor: "var(--line-1)" }}
              >Clear</button>
            </>
          )}
          <kbd className="mono rounded border px-1 py-0.5 text-[10px] hidden md:inline"
               style={{ borderColor: "var(--line-2)", color: "var(--fg-3)" }}>⌘L</kbd>
        </div>
      </header>

      {open && (
        <div className="flex h-[calc(100%-36px)] flex-col">
          <div className="flex flex-wrap items-center gap-1.5 border-b px-3 py-2"
               style={{ borderColor: "var(--line-1)" }}>
            {KINDS.map((k) => {
              const meta = kindMeta(k);
              const active = filterKinds.has(k);
              return (
                <button
                  key={k}
                  onClick={() => toggleKind(k)}
                  className={cx("pill", active && "active")}
                  style={{
                    background: active ? meta.color + "22" : "var(--bg-2)",
                    color: active ? "var(--fg-0)" : "var(--fg-2)",
                    borderColor: active ? meta.color : "var(--line-1)",
                  }}
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
                  {meta.label}
                </button>
              );
            })}
          </div>

          <ul ref={listRef}
              className="scrollbar-thin flex-1 overflow-y-auto px-3 py-2 mono text-[11.5px]"
              style={{ color: "var(--fg-1)", background: "var(--bg-0)" }}>
            {filtered.map((e, i) => {
              const meta = kindMeta(e.event_type);
              return (
                <li key={i} className="grid grid-cols-[88px_110px_1fr] gap-3 py-0.5">
                  <span style={{ color: "var(--fg-3)" }}>{formatTs(e.timestamp)}</span>
                  <span style={{ color: meta.color }}>{meta.label}</span>
                  <span className="truncate">
                    <span style={{ color: "var(--fg-3)" }}>
                      {(e.from_agent || "?") + " → " + (e.to_agent || "?") + "  "}
                    </span>
                    {e.message || ""}
                  </span>
                </li>
              );
            })}
            {filtered.length === 0 && (
              <li className="px-2 py-4 text-center" style={{ color: "var(--fg-3)" }}>
                No events match the current filters.
              </li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
}

function formatTs(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleTimeString([], { hour12: false }); }
  catch (_) { return String(iso).slice(11, 19); }
}
