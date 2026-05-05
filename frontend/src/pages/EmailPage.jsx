// Octopus V2.2 — /email page.
// Gmail-connected triage surface. Three-pane Cursor layout: thread list on
// the left, full thread on the right, and an "Agent" rail that can triage
// the selected thread with the orchestrator (summary + priority + draft
// reply) without leaving the page.
//
// The backend endpoints (/api/email/*) are expected to proxy to the user's
// Gmail MCP connector. If the backend hasn't wired them yet the page
// degrades gracefully — it still renders the empty state + compose form,
// and a clearly-labeled "Connect Gmail" CTA that calls the same endpoint
// to trigger an OAuth flow on the server side.

import { useEffect, useMemo, useState } from "react";
import {
  Mail, Inbox, Star, Archive, Send, Sparkles,
  RefreshCw, AlertCircle, PenSquare, ChevronRight, X,
} from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { API } from "../lib/api";

const FOLDERS = [
  { id: "inbox",   label: "Inbox",    icon: Inbox,    limit: 25 },
  { id: "starred", label: "Starred",  icon: Star,     limit: 25 },
  { id: "sent",    label: "Sent",     icon: Send,     limit: 25 },
  { id: "archive", label: "Archive",  icon: Archive,  limit: 50 },
];

export default function EmailPage() {
  const { theme } = useZone();
  const [folder, setFolder] = useState("inbox");
  const [threads, setThreads] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [composing, setComposing] = useState(false);
  const [triage, setTriage] = useState({}); // { [threadId]: { summary, priority, reply } }

  useEffect(() => { void refresh(); }, [folder]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await API.emailInbox(FOLDERS.find((f) => f.id === folder)?.limit || 25);
      if (res?.error) { setError(res.error); setThreads([]); }
      else setThreads(res?.threads || res?.messages || []);
    } finally {
      setLoading(false);
    }
  }

  async function triageSelected() {
    const t = threads.find((x) => x.id === selectedId);
    if (!t) return;
    setTriage((s) => ({ ...s, [t.id]: { ...(s[t.id] || {}), running: true } }));
    const res = await API.emailTriage(t.id);
    setTriage((s) => ({
      ...s,
      [t.id]: {
        running: false,
        summary:  res?.summary  || res?.response || "(no summary)",
        priority: res?.priority || "P3",
        reply:    res?.reply    || res?.draft || "",
        error:    res?.error    || null,
      },
    }));
  }

  const selected = useMemo(
    () => threads.find((t) => t.id === selectedId) || null,
    [threads, selectedId]
  );
  const selTriage = selected ? triage[selected.id] : null;

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "200px 1fr 380px" }}>
      {/* Folders */}
      <section className="flex min-h-0 flex-col border-r"
               style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3"
             style={{ borderColor: "var(--line-1)" }}>
          <Mail size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Gmail</span>
        </div>
        <div className="px-2 py-2">
          <button
            onClick={() => setComposing(true)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm transition-all"
            style={{
              background: theme.accent,
              color: "#05070d",
              boxShadow: `0 0 14px -4px ${theme.glow}`,
            }}
          >
            <PenSquare size={14} /> Compose
          </button>
        </div>
        <ul className="scrollbar-thin flex-1 overflow-y-auto px-1 py-1">
          {FOLDERS.map((f) => {
            const Icon = f.icon;
            const active = folder === f.id;
            return (
              <li key={f.id}>
                <button
                  onClick={() => { setFolder(f.id); setSelectedId(null); }}
                  className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm"
                  style={{
                    background: active ? "var(--accent-soft)" : "transparent",
                    color: active ? "var(--fg-0)" : "var(--fg-1)",
                  }}
                >
                  <Icon size={14} style={{ color: active ? theme.accent : "var(--fg-3)" }} />
                  <span>{f.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="border-t px-3 py-2 mono text-[10px]" style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}>
          {threads.length} threads · {loading ? "syncing…" : "up-to-date"}
        </div>
      </section>

      {/* Thread list */}
      <section className="flex min-h-0 flex-col border-r" style={{ borderColor: "var(--line-1)" }}>
        <div className="flex items-center gap-2 border-b px-4 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>
            {FOLDERS.find((f) => f.id === folder)?.label}
          </span>
          <button
            onClick={refresh}
            disabled={loading}
            className="ml-auto flex items-center gap-1 rounded-md border px-2 py-0.5 mono text-[11px] disabled:opacity-50"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
          >
            <RefreshCw size={11} className={loading ? "animate-spin" : ""} /> refresh
          </button>
        </div>
        {composing && (
          <Composer
            theme={theme}
            onClose={() => setComposing(false)}
            onSent={async () => { setComposing(false); await refresh(); }}
          />
        )}

        {error && (
          <div className="m-3 flex items-start gap-2 rounded-lg border px-3 py-2 text-sm"
               style={{ borderColor: "#ff5a7855", background: "#ff5a7815", color: "var(--fg-1)" }}>
            <AlertCircle size={14} style={{ color: "#ff5a78", marginTop: 2 }} />
            <div className="flex-1">
              <div className="mono caps text-[11px]" style={{ color: "#ff5a78" }}>Gmail not ready</div>
              <div className="text-[12.5px]" style={{ color: "var(--fg-1)" }}>{error}</div>
              <div className="mt-1 mono text-[11px]" style={{ color: "var(--fg-3)" }}>
                Wire <code>/api/email/inbox</code> to your Gmail MCP and this list will fill in.
              </div>
            </div>
          </div>
        )}

        <ul className="scrollbar-thin flex-1 overflow-y-auto">
          {threads.length === 0 && !loading && !error && (
            <li className="px-6 py-10 text-center text-sm" style={{ color: "var(--fg-3)" }}>
              Your inbox is empty for this view.
            </li>
          )}
          {threads.map((t) => {
            const active = selectedId === t.id;
            const unread = !!t.unread;
            const tPri = triage[t.id]?.priority;
            return (
              <li key={t.id}>
                <button
                  onClick={() => setSelectedId(t.id)}
                  className="flex w-full items-start gap-3 border-b px-4 py-3 text-left text-sm"
                  style={{
                    background: active ? "var(--accent-soft)" : "transparent",
                    borderColor: "var(--line-1)",
                    color: "var(--fg-1)",
                  }}
                >
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full"
                        style={{ background: unread ? theme.accent : "transparent",
                                 border: `1px solid ${unread ? theme.accent : "var(--line-2)"}` }} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className={unread ? "font-semibold" : ""} style={{ color: "var(--fg-0)" }}>
                        {t.from || t.sender || "(unknown sender)"}
                      </span>
                      {tPri && <PriorityBadge priority={tPri} />}
                      <span className="ml-auto mono text-[10px]" style={{ color: "var(--fg-3)" }}>
                        {formatDate(t.date || t.received_at)}
                      </span>
                    </div>
                    <div className="truncate" style={{ color: "var(--fg-1)" }}>
                      {t.subject || "(no subject)"}
                    </div>
                    <div className="truncate text-[12px]" style={{ color: "var(--fg-3)" }}>
                      {t.snippet || t.preview || ""}
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Right: thread + agent rail */}
      <aside className="flex min-h-0 flex-col" style={{ background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <Sparkles size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>Thread · Agent</span>
          {selected && (
            <button
              onClick={() => setSelectedId(null)}
              className="ml-auto rounded border px-1 py-0.5 mono text-[10px]"
              style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}
            >
              <X size={10} />
            </button>
          )}
        </div>

        {!selected ? (
          <EmptyAgentRail theme={theme} />
        ) : (
          <div className="scrollbar-thin flex-1 overflow-y-auto">
            <div className="border-b px-4 py-3" style={{ borderColor: "var(--line-1)" }}>
              <div className="text-sm font-semibold" style={{ color: "var(--fg-0)" }}>
                {selected.subject || "(no subject)"}
              </div>
              <div className="mono text-[11px]" style={{ color: "var(--fg-3)" }}>
                {selected.from || selected.sender} · {formatDate(selected.date || selected.received_at)}
              </div>
            </div>
            <div className="px-4 py-3 text-[13px] whitespace-pre-wrap"
                 style={{ color: "var(--fg-1)" }}>
              {selected.body || selected.snippet || "(message body unavailable)"}
            </div>

            <div className="border-t px-4 py-3" style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
              <button
                onClick={triageSelected}
                disabled={!!selTriage?.running}
                className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm disabled:opacity-60"
                style={{
                  background: theme.accent,
                  color: "#05070d",
                  boxShadow: `0 0 14px -4px ${theme.glow}`,
                }}
              >
                <Sparkles size={14} />
                {selTriage?.running ? "Orchestrator is reading…" : "Triage with orchestrator"}
              </button>

              {selTriage && !selTriage.running && (
                <div className="mt-3 space-y-3">
                  {selTriage.error && (
                    <div className="rounded-md border px-2 py-1.5 mono text-[11px]"
                         style={{ borderColor: "#ff5a7855", color: "#ff8aa0" }}>
                      {selTriage.error}
                    </div>
                  )}
                  {selTriage.priority && (
                    <Row label="Priority"><PriorityBadge priority={selTriage.priority} /></Row>
                  )}
                  {selTriage.summary && (
                    <Row label="Summary">
                      <div className="text-[12.5px]" style={{ color: "var(--fg-1)" }}>
                        {selTriage.summary}
                      </div>
                    </Row>
                  )}
                  {selTriage.reply && (
                    <Row label="Draft reply">
                      <div className="uui-card" style={{ background: "var(--bg-0)", borderColor: "var(--line-1)" }}>
                        <div className="flex items-center gap-2 border-b px-3 py-1.5"
                             style={{ borderColor: "var(--line-1)" }}>
                          <span className="mono caps text-[10px]" style={{ color: "var(--fg-3)" }}>draft</span>
                          <button
                            className="ml-auto rounded border px-1.5 py-0.5 mono text-[10px]"
                            style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
                            onClick={() => navigator.clipboard.writeText(selTriage.reply)}
                          >copy</button>
                        </div>
                        <pre className="mono whitespace-pre-wrap px-3 py-2 text-[12px]"
                             style={{ color: "var(--fg-0)" }}>{selTriage.reply}</pre>
                      </div>
                    </Row>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function EmptyAgentRail({ theme }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-2xl"
           style={{ background: `linear-gradient(135deg, ${theme.accent} 0%, ${theme.edgeColor} 100%)`,
                    boxShadow: `0 0 22px -6px ${theme.glow}` }}>
        <Sparkles size={18} className="text-white" />
      </div>
      <div className="mb-1 text-sm font-semibold" style={{ color: "var(--fg-0)" }}>
        Pick a thread.
      </div>
      <div className="text-xs" style={{ color: "var(--fg-2)" }}>
        The orchestrator will summarize it, assign a priority and draft a reply — you decide whether to send.
      </div>
      <ul className="mt-4 space-y-1.5 text-left text-[11px]" style={{ color: "var(--fg-3)" }}>
        <li className="flex items-center gap-1"><ChevronRight size={10} /> P0/P1 = reply today</li>
        <li className="flex items-center gap-1"><ChevronRight size={10} /> P2 = reply this week</li>
        <li className="flex items-center gap-1"><ChevronRight size={10} /> P3 = archive or FYI</li>
      </ul>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div>
      <div className="mb-1 mono caps text-[10px]" style={{ color: "var(--fg-3)" }}>{label}</div>
      {children}
    </div>
  );
}

function PriorityBadge({ priority }) {
  const colors = {
    P0: "#ff5a78", P1: "#ffb84a", P2: "#6ab7ff", P3: "#8a93a6",
  };
  const c = colors[priority] || "#8a93a6";
  return (
    <span className="mono caps rounded border px-1.5 py-0.5 text-[10px]"
          style={{ borderColor: c + "88", color: c, background: c + "15" }}>
      {priority}
    </span>
  );
}

function Composer({ theme, onClose, onSent }) {
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState(null);

  async function send() {
    if (!to.trim() || !subject.trim()) return;
    setSending(true); setErr(null);
    const r = await API.emailCompose({ to, subject, body });
    setSending(false);
    if (r?.error) setErr(r.error);
    else onSent?.();
  }

  return (
    <div className="border-b px-4 py-3" style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
      <div className="terminal-card">
        <div className="bar">
          <span className="dot r" /><span className="dot y" /><span className="dot g" />
          <span className="ml-2 mono caps">New message</span>
          <button onClick={onClose} className="ml-auto mono text-[11px]"
                  style={{ color: "var(--fg-3)" }}><X size={11} /></button>
        </div>
        <div className="flex flex-col gap-2 p-3">
          <LabeledInput label="to"      value={to}      onChange={setTo}      placeholder="someone@example.com" />
          <LabeledInput label="subject" value={subject} onChange={setSubject} placeholder="Subject line" />
          <textarea
            rows={5}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your message…"
            className="mono w-full rounded-md border bg-transparent p-2 text-[12.5px] outline-none"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-0)" }}
          />
          {err && (
            <div className="mono text-[11px]" style={{ color: "#ff8aa0" }}>{err}</div>
          )}
          <div className="flex items-center gap-2">
            <button
              onClick={send}
              disabled={sending || !to.trim() || !subject.trim()}
              className="flex items-center gap-1 rounded-md px-3 py-1 text-[12px] disabled:opacity-40"
              style={{
                background: theme.accent,
                color: "#05070d",
                boxShadow: `0 0 10px -3px ${theme.glow}`,
              }}
            >
              {sending ? "Sending…" : "Send"} <Send size={11} />
            </button>
            <button
              onClick={onClose}
              className="mono caps rounded border px-2 py-0.5 text-[10px]"
              style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
            >Cancel</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function LabeledInput({ label, value, onChange, placeholder }) {
  return (
    <div className="flex items-center gap-2 border-b px-0 py-1"
         style={{ borderColor: "var(--line-1)" }}>
      <span className="mono caps w-14 shrink-0 text-[10px]" style={{ color: "var(--fg-3)" }}>{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mono flex-1 bg-transparent text-[12.5px] outline-none"
        style={{ color: "var(--fg-0)" }}
      />
    </div>
  );
}

function formatDate(v) {
  if (!v) return "—";
  try {
    const d = new Date(v);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    return sameDay ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                   : d.toLocaleDateString([], { month: "short", day: "numeric" });
  } catch (_) { return String(v).slice(0, 10); }
}
