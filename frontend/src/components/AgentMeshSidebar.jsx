// Octopus V2.2 — left sidebar, live octopus-tentacle viz.
// Orchestrator = central core. Each agent is a tentacle tip; edges pulse
// when a routing event targets that agent. Click an agent to scope the
// ChangesRenderer to that role. Zone-aware colors come from useZone().

import { useEffect, useMemo, useRef, useState } from "react";
import cx from "../lib/cx.js";
import { Activity, Dot } from "lucide-react";
import { API } from "../lib/api";
import { useZone } from "../hooks/useZone.jsx";
import { useLiveLog } from "../hooks/useLiveLog.js";

export default function AgentMeshSidebar({ focus, onFocus }) {
  const { theme, zone } = useZone();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const { events } = useLiveLog();
  const svgRef = useRef(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      const r = await API.agents();
      if (!alive) return;
      const list = Array.isArray(r?.agents) ? r.agents : [];
      setAgents(list);
      setLoading(false);
    }
    load();
    const id = setInterval(load, 6000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Highlight tentacles that received a routing event in the last 3 s
  const activeRoles = useMemo(() => {
    const now = Date.now();
    const hot = new Set();
    for (const e of events) {
      if (e._rx && now - e._rx < 3000) {
        if (e.to_agent) hot.add(e.to_agent);
        if (e.from_agent) hot.add(e.from_agent);
      }
    }
    return hot;
  }, [events]);

  // Filter agents by the current zone so HZ agents only appear when the
  // user has the HZ panel active.
  const visible = useMemo(() => {
    if (zone === "mainline") return agents.filter((a) => (a.zone || "mainline") === "mainline");
    return agents;
  }, [agents, zone]);

  const core = { x: 100, y: 220, r: 22 };
  const radius = 120;
  const tips = useMemo(() => {
    const n = Math.max(visible.length, 1);
    return visible.map((a, i) => {
      const angle = Math.PI * (0.15 + (i / Math.max(n - 1, 1)) * 0.7);
      return {
        ...a,
        x: core.x + Math.cos(angle) * radius,
        y: core.y - Math.sin(angle) * radius,
      };
    });
  }, [visible]);

  return (
    <aside
      className="flex h-full w-[256px] shrink-0 flex-col border-r"
      style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}
    >
      <div className="flex items-center gap-2 border-b px-3 py-2"
           style={{ borderColor: "var(--line-1)" }}>
        <Activity size={14} style={{ color: theme.accent }} />
        <span className="mono caps" style={{ color: "var(--fg-2)" }}>Mesh</span>
        <span className="ml-auto mono caps" style={{ color: "var(--fg-3)" }}>
          {loading ? "…" : `${visible.length} agents`}
        </span>
      </div>

      <svg ref={svgRef} viewBox="0 0 200 440" className="w-full" style={{ height: 260 }}>
        <defs>
          <radialGradient id="coreGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={theme.accent} stopOpacity="0.9" />
            <stop offset="100%" stopColor={theme.accent} stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Tentacle edges */}
        {tips.map((t) => {
          const hot = activeRoles.has(t.role);
          const mid1 = { x: core.x + (t.x - core.x) * 0.45, y: core.y + (t.y - core.y) * 0.2 - 20 };
          const mid2 = { x: core.x + (t.x - core.x) * 0.75, y: core.y + (t.y - core.y) * 0.8 + 10 };
          const d = `M ${core.x} ${core.y} C ${mid1.x} ${mid1.y}, ${mid2.x} ${mid2.y}, ${t.x} ${t.y}`;
          return (
            <g key={`e-${t.role}`}>
              <path d={d} fill="none"
                    stroke={theme.edgeColor}
                    strokeOpacity={hot ? 0.95 : 0.35}
                    strokeWidth={hot ? 2 : 1.25}
                    strokeDasharray={hot ? "6 6" : "0"}
                    className={hot ? "anim-pulse" : ""} />
            </g>
          );
        })}

        {/* Core halo */}
        <circle cx={core.x} cy={core.y} r="44" fill="url(#coreGrad)" />
        <circle cx={core.x} cy={core.y} r={core.r}
                fill={theme.surface} stroke={theme.accent} strokeWidth="1.5" />
        <text x={core.x} y={core.y + 4} textAnchor="middle" fontSize="10"
              fontFamily="ui-monospace" fill={theme.accent}>CORE</text>

        {/* Tentacle tips */}
        {tips.map((t) => {
          const hot = activeRoles.has(t.role);
          const isFocus = focus === t.role;
          return (
            <g key={`n-${t.role}`} className="cursor-pointer"
               onClick={() => onFocus?.(isFocus ? null : t.role)}>
              <circle cx={t.x} cy={t.y} r={isFocus ? 9 : 6}
                      fill={t.emoji ? theme.surface : "var(--bg-2)"}
                      stroke={hot || isFocus ? theme.accent : "var(--line-2)"}
                      strokeWidth={isFocus ? 2 : 1} />
              <text x={t.x} y={t.y + 3} textAnchor="middle" fontSize="9"
                    fontFamily="ui-monospace"
                    fill={isFocus ? theme.accent : "var(--fg-2)"}>{t.emoji || "•"}</text>
            </g>
          );
        })}
      </svg>

      {/* Agent list with click-to-focus */}
      <ul className="scrollbar-thin flex-1 overflow-y-auto px-1 py-1">
        {visible.map((a) => {
          const hot = activeRoles.has(a.role);
          const isFocus = focus === a.role;
          return (
            <li key={a.role}>
              <button
                onClick={() => onFocus?.(isFocus ? null : a.role)}
                className={cx(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
                )}
                style={{
                  background: isFocus ? "var(--accent-soft)" : "transparent",
                  color: "var(--fg-1)",
                }}
              >
                <span className="text-base">{a.emoji || "•"}</span>
                <span className="flex-1 truncate">{a.name || a.role}</span>
                <span className={cx("h-1.5 w-1.5 rounded-full",
                  hot ? "" : "opacity-40")}
                  style={{ background: a.status === "busy" ? "#ffb84a"
                         : hot ? theme.accent : "#3ce28f" }} />
              </button>
            </li>
          );
        })}
        {!loading && visible.length === 0 && (
          <li className="px-2 py-4 text-xs" style={{ color: "var(--fg-3)" }}>
            No agents registered yet.
          </li>
        )}
      </ul>

      <div className="border-t px-3 py-2 text-[11px]"
           style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}>
        <span className="mono caps">Focus:</span>{" "}
        <span style={{ color: focus ? theme.accent : "var(--fg-2)" }}>
          {focus || "all agents"}
        </span>
      </div>
    </aside>
  );
}
