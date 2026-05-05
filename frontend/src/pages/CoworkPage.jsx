// Octopus V2.2 — /cowork page.
// Multi-agent collaborative surface. A shared artifact canvas on the
// left (text/markdown/tasks) and a stack of agent "threads" on the right
// showing who's doing what. Each thread surfaces its own ChangesRenderer
// scoped to that agent.

import { useEffect, useState } from "react";
import { Users, FileText, CheckSquare, PenSquare } from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { useLiveLog, groupByTurn } from "../hooks/useLiveLog.js";
import ChangesRenderer from "../components/ChangesRenderer.jsx";
import { API } from "../lib/api";

export default function CoworkPage({ focusRole, onFocusRole }) {
  const { theme } = useZone();
  const [doc, setDoc] = useState(INITIAL_DOC);
  const [agents, setAgents] = useState([]);
  const { events } = useLiveLog();

  useEffect(() => {
    let alive = true;
    API.agents().then((r) => { if (alive) setAgents(r?.agents || []); });
    return () => { alive = false; };
  }, []);

  const threads = groupByTurn(events).slice(-6).reverse();

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "1.3fr 1fr" }}>
      {/* Left: shared doc canvas */}
      <section className="flex min-h-0 flex-col border-r" style={{ borderColor: "var(--line-1)" }}>
        <div className="flex items-center gap-2 border-b px-4 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <Users size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Shared canvas</span>
          <span className="ml-auto mono text-[11px]" style={{ color: "var(--fg-3)" }}>
            auto-saves to memory/working_state
          </span>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
          <CanvasCard icon={FileText} title="Spec">
            <textarea
              value={doc.spec}
              onChange={(e) => setDoc({ ...doc, spec: e.target.value })}
              className="mono w-full resize-y bg-transparent outline-none"
              style={{ color: "var(--fg-0)", minHeight: 160 }}
            />
          </CanvasCard>
          <CanvasCard icon={CheckSquare} title="Tasks">
            <TaskList tasks={doc.tasks} onChange={(tasks) => setDoc({ ...doc, tasks })} theme={theme} />
          </CanvasCard>
          <CanvasCard icon={PenSquare} title="Notes">
            <textarea
              value={doc.notes}
              onChange={(e) => setDoc({ ...doc, notes: e.target.value })}
              className="mono w-full resize-y bg-transparent outline-none"
              style={{ color: "var(--fg-0)", minHeight: 100 }}
            />
          </CanvasCard>
        </div>
      </section>

      {/* Right: agent threads */}
      <aside className="flex min-h-0 flex-col" style={{ background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Agent threads</span>
          <span className="ml-auto mono text-[11px]" style={{ color: "var(--fg-3)" }}>
            last 6 turns · {agents.length} agents
          </span>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto">
          {threads.length === 0 ? (
            <div className="px-4 py-10 text-sm" style={{ color: "var(--fg-3)" }}>
              When agents collaborate on this canvas, each turn will render as its
              own thread here with plan / routing / diff / reply events.
            </div>
          ) : (
            <ChangesRenderer events={events} focusRole={focusRole} />
          )}
        </div>
      </aside>
    </div>
  );
}

const INITIAL_DOC = {
  spec: "# What we're building\n\nDescribe the outcome. The orchestrator reads this and fans out to arms.\n",
  tasks: [
    { id: 1, text: "Draft the spec", done: true },
    { id: 2, text: "Route to dev + qa", done: false },
    { id: 3, text: "Commit + PR", done: false },
  ],
  notes: "",
};

function CanvasCard({ icon: Icon, title, children }) {
  return (
    <div className="uui-card mb-3" style={{ background: "var(--bg-1)", borderColor: "var(--line-1)" }}>
      <div className="flex items-center gap-2 border-b px-3 py-1.5"
           style={{ borderColor: "var(--line-1)" }}>
        <Icon size={12} style={{ color: "var(--fg-3)" }} />
        <span className="mono caps" style={{ color: "var(--fg-2)" }}>{title}</span>
      </div>
      <div className="px-3 py-2 text-sm">{children}</div>
    </div>
  );
}

function TaskList({ tasks, onChange, theme }) {
  function toggle(id) {
    onChange(tasks.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));
  }
  function add(text) {
    const id = Math.max(0, ...tasks.map((t) => t.id)) + 1;
    onChange([...tasks, { id, text, done: false }]);
  }
  const [draft, setDraft] = useState("");
  return (
    <div>
      <ul className="flex flex-col gap-1">
        {tasks.map((t) => (
          <li key={t.id} className="flex items-center gap-2">
            <button
              onClick={() => toggle(t.id)}
              className="grid h-4 w-4 place-items-center rounded border"
              style={{
                background: t.done ? theme.accent : "transparent",
                borderColor: t.done ? theme.accent : "var(--line-2)",
              }}
              aria-label="toggle"
            >
              {t.done && <span className="mono text-[9px]" style={{ color: "#05070d" }}>✓</span>}
            </button>
            <span className={t.done ? "line-through" : ""}
                  style={{ color: t.done ? "var(--fg-3)" : "var(--fg-0)" }}>{t.text}</span>
          </li>
        ))}
      </ul>
      <div className="mt-2 flex items-center gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && draft.trim()) { add(draft.trim()); setDraft(""); }
          }}
          placeholder="+ add task… (enter)"
          className="mono flex-1 rounded-md border bg-transparent px-2 py-1 text-xs outline-none"
          style={{ borderColor: "var(--line-1)", color: "var(--fg-1)" }}
        />
      </div>
    </div>
  );
}
