// Octopus V2.2 — /chat page.
// Cursor-inspired single conversation: ThinkingStream at top, user input
// pinned to the bottom, ChangesRenderer in a right rail showing each
// turn's plan/routing/file_diff/... events for the same task.

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Plus, Sparkles } from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { useLiveLog } from "../hooks/useLiveLog.js";
import ThinkingStream from "../components/ThinkingStream.jsx";
import ChangesRenderer from "../components/ChangesRenderer.jsx";
import { API } from "../lib/api";

export default function ChatV2({ focusRole, onFocusRole }) {
  const { theme, isHacker } = useZone();
  const { events } = useLiveLog();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const endRef = useRef(null);

  const visibleEvents = useMemo(() => {
    if (!currentTaskId) return events;
    return events.filter((e) => e.task_id === currentTaskId);
  }, [events, currentTaskId]);

  // Build a Cursor-style status line view for the in-flight turn.
  const statusLines = useMemo(() => buildStatusLines(visibleEvents), [visibleEvents]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, running]);

  async function send() {
    const t = input.trim();
    if (!t || running) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: t, at: Date.now() }]);
    setRunning(true);
    const target = focusRole || (isHacker ? "hz_orchestrator" : "orchestrator");
    const res = await API.send(target, t);
    if (res?.task_id) setCurrentTaskId(res.task_id);
    const reply = res?.response || res?.content || res?.error || "(no reply)";
    setMessages((m) => [...m, { role: "assistant", agent: target, content: reply, at: Date.now() }]);
    setRunning(false);
  }

  function newTurn() {
    setMessages([]);
    setCurrentTaskId(null);
  }

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "1fr 380px" }}>
      {/* Left: conversation */}
      <section className="flex min-h-0 flex-col border-r" style={{ borderColor: "var(--line-1)" }}>
        <div className="flex items-center justify-between border-b px-4 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <div className="flex items-center gap-2">
            <Sparkles size={14} style={{ color: theme.accent }} />
            <span className="mono caps" style={{ color: "var(--fg-2)" }}>Chat</span>
            <span className="mono text-xs" style={{ color: "var(--fg-3)" }}>
              target: {focusRole || (isHacker ? "hz_orchestrator" : "orchestrator")}
            </span>
          </div>
          <button
            onClick={newTurn}
            className="flex items-center gap-1 rounded-md border px-2 py-1 text-xs"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-2)", background: "var(--bg-2)" }}
          >
            <Plus size={12} /> New turn
          </button>
        </div>

        <div className="scrollbar-thin flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 && !running && (
            <Welcome />
          )}
          <ul className="flex flex-col gap-4">
            {messages.map((m, i) => (
              <li key={i} className={m.role === "user" ? "flex justify-end" : ""}>
                <Bubble role={m.role} agent={m.agent} text={m.content} />
              </li>
            ))}
            {running && (
              <li>
                <div className="uui-card anim-slide-up"
                     style={{ background: "var(--bg-1)", borderColor: "var(--line-1)" }}>
                  <div className="flex items-center gap-2 border-b px-3 py-1.5"
                       style={{ borderColor: "var(--line-1)" }}>
                    <span className="h-2 w-2 rounded-full anim-breathe"
                          style={{ background: theme.accent, boxShadow: `0 0 8px ${theme.glow}` }} />
                    <span className="mono caps" style={{ color: "var(--fg-2)" }}>Cursor Agent</span>
                    <span className="ml-auto mono text-[11px]" style={{ color: "var(--fg-3)" }}>
                      {currentTaskId ? `task ${currentTaskId}` : "starting…"}
                    </span>
                  </div>
                  <ThinkingStream lines={statusLines} running={true} />
                </div>
              </li>
            )}
            <li ref={endRef} />
          </ul>
        </div>

        <Composer value={input} onChange={setInput} onSend={send} running={running} />
      </section>

      {/* Right: changes */}
      <aside className="flex min-h-0 flex-col" style={{ background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Changes</span>
          <span className="mono text-[11px]" style={{ color: "var(--fg-3)" }}>
            plan / route / diff / memory / cmd / bridge / reply
          </span>
          {focusRole && (
            <button
              onClick={() => onFocusRole?.(null)}
              className="ml-auto mono caps rounded border px-1.5 py-0.5 text-[10px]"
              style={{ color: theme.accent, borderColor: theme.accent }}
            >
              Focus: {focusRole} ✕
            </button>
          )}
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto">
          <ChangesRenderer events={visibleEvents} focusRole={focusRole} />
        </div>
      </aside>
    </div>
  );
}

function Welcome() {
  const { theme } = useZone();
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl"
           style={{
             background: `linear-gradient(135deg, ${theme.accent} 0%, ${theme.edgeColor} 100%)`,
             boxShadow: `0 0 32px -6px ${theme.glow}`,
           }}>
        <Sparkles size={22} className="text-white" />
      </div>
      <div className="mb-1 text-lg font-semibold" style={{ color: "var(--fg-0)" }}>
        Ready when you are.
      </div>
      <div className="mb-6 text-sm" style={{ color: "var(--fg-2)" }}>
        Delegate to the mesh. Watch plan, routing, and file changes stream on the right.
      </div>
      <div className="grid max-w-md grid-cols-2 gap-2 text-left text-xs">
        <SampleChip text="Triage my Gmail inbox for high-priority threads" />
        <SampleChip text="Plan next week in the calendar around deep-work blocks" />
        <SampleChip text="Review the zones.py diff for boundary bugs" />
        <SampleChip text="Scaffold a Vite plugin that lints our Tailwind v4 tokens" />
      </div>
    </div>
  );
}

function SampleChip({ text }) {
  return (
    <div className="pill"
         style={{ background: "var(--bg-2)", color: "var(--fg-2)", border: "1px solid var(--line-1)" }}>
      <span className="mono">{text}</span>
    </div>
  );
}

function Bubble({ role, agent, text }) {
  const { theme } = useZone();
  const isUser = role === "user";
  return (
    <div
      className={isUser ? "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm" : "uui-card anim-slide-up w-full"}
      style={isUser ? {
        background: theme.accent + "22",
        color: "var(--fg-0)",
        border: `1px solid ${theme.accent}55`,
      } : {
        background: "var(--bg-1)",
        borderColor: "var(--line-1)",
      }}
    >
      {!isUser && (
        <div className="flex items-center gap-2 border-b px-3 py-1.5"
             style={{ borderColor: "var(--line-1)" }}>
          <span className="h-2 w-2 rounded-full"
                style={{ background: theme.accent, boxShadow: `0 0 6px ${theme.glow}` }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>{agent || "assistant"}</span>
        </div>
      )}
      <div className={isUser ? "" : "px-3 py-2.5 text-sm whitespace-pre-wrap"}
           style={{ color: "var(--fg-0)" }}>
        {text}
      </div>
    </div>
  );
}

function Composer({ value, onChange, onSend, running }) {
  const { theme } = useZone();
  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
  }
  return (
    <div className="border-t px-3 py-3" style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
      <div className="terminal-card">
        <div className="bar">
          <span className="dot r" /><span className="dot y" /><span className="dot g" />
          <span className="ml-2 mono caps">Cursor Agent</span>
          <span className="ml-auto mono" style={{ color: "var(--fg-3)" }}>shift+tab to cycle</span>
        </div>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKey}
          rows={3}
          placeholder="→ Add a follow-up…  (⇧↵ for newline)"
          className="mono block w-full resize-none bg-transparent p-3 text-sm outline-none"
          style={{ color: "var(--fg-0)" }}
        />
        <div className="flex items-center gap-2 px-3 pb-2 mono text-[11px]"
             style={{ color: "var(--fg-3)" }}>
          <span>/ commands</span><span>· @ files</span><span>· ! shell</span>
          <button
            onClick={onSend}
            disabled={running || !value.trim()}
            className="ml-auto flex items-center gap-1 rounded-md px-3 py-1 text-[12px] transition-all disabled:opacity-40"
            style={{
              background: theme.accent,
              color: "#05070d",
              boxShadow: running ? "none" : `0 0 12px -2px ${theme.glow}`,
            }}
          >
            {running ? "Running…" : "Send"}
            <ArrowUp size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}

// Translate a raw event list into Cursor-style status lines.
function buildStatusLines(events) {
  if (!events?.length) return [];
  const lines = [];
  const readFiles = events.filter((e) => e.event_type === "file_diff").length;
  const plans = events.filter((e) => e.event_type === "plan").length;
  const routes = events.filter((e) => e.event_type === "routing").length;
  const commands = events.filter((e) => e.event_type === "command").length;
  const firstTs = events[0]?._rx || Date.now();
  const lastTs = events[events.length - 1]?._rx || Date.now();
  const seconds = Math.max(1, Math.round((lastTs - firstTs) / 1000));

  if (plans)    lines.push({ kind: "plan",    label: `Planned`, seconds });
  if (routes)   lines.push({ kind: "routing", label: `Routed to ${routes} agent${routes > 1 ? "s" : ""}` });
  if (readFiles)lines.push({ kind: "reading", label: `Read ${readFiles} file${readFiles > 1 ? "s" : ""}` });
  if (commands) lines.push({ kind: "command", label: `Ran ${commands} command${commands > 1 ? "s" : ""}` });
  if (!lines.length) lines.push({ kind: "thinking", label: "Thought", seconds });
  return lines;
}
