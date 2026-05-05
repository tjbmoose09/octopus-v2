// Octopus V2.2 — /calendar page.
// A month grid + day rail for planning. Events round-trip through
// /api/calendar/events (backend is expected to fall through to Google
// Calendar if connected, or to the local agent memory store if not).
//
// The page also wires up a browser Notification reminder loop: for every
// event whose start is within the next 10 minutes, we request permission
// and fire a one-shot notification when the clock crosses the 10/5/1-min
// boundary. Uses an in-memory Set to avoid double-firing within a session.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarDays, ChevronLeft, ChevronRight, Plus, Bell, BellOff,
  X, Sparkles, Clock,
} from "lucide-react";
import { useZone } from "../hooks/useZone.jsx";
import { API } from "../lib/api";

export default function CalendarPage() {
  const { theme } = useZone();
  const [cursor, setCursor] = useState(startOfMonth(new Date()));
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(todayISO());
  const [creating, setCreating] = useState(null); // { date } | null
  const [notifGranted, setNotifGranted] = useState(
    typeof Notification !== "undefined" && Notification.permission === "granted"
  );

  // Load for the visible month (±1 day buffer to catch boundaries).
  useEffect(() => {
    const start = new Date(cursor); start.setDate(start.getDate() - 2);
    const end   = new Date(cursor); end.setMonth(end.getMonth() + 1); end.setDate(end.getDate() + 2);
    void load(start.toISOString(), end.toISOString());
  }, [cursor]);

  async function load(start, end) {
    setLoading(true); setError(null);
    const res = await API.calendarList(start, end);
    setLoading(false);
    if (res?.error) { setError(res.error); setEvents([]); }
    else setEvents(res?.events || []);
  }

  async function addEvent(evt) {
    const r = await API.calendarAdd(evt);
    if (r?.error) { setError(r.error); return; }
    setCreating(null);
    await load(
      new Date(cursor).toISOString(),
      (() => { const d = new Date(cursor); d.setMonth(d.getMonth() + 1); return d.toISOString(); })()
    );
  }

  async function delEvent(id) {
    await API.calendarDel(id);
    setEvents((xs) => xs.filter((e) => e.id !== id));
  }

  // Notification scheduler — polls every 30s, checks upcoming window.
  const firedRef = useRef(new Set());
  useEffect(() => {
    if (!notifGranted) return;
    const id = setInterval(() => {
      const now = Date.now();
      for (const e of events) {
        const start = +new Date(e.start || e.date);
        if (!isFinite(start)) continue;
        const mins = Math.round((start - now) / 60000);
        for (const boundary of [10, 5, 1]) {
          if (mins === boundary) {
            const key = `${e.id}:${boundary}`;
            if (!firedRef.current.has(key)) {
              firedRef.current.add(key);
              try {
                new Notification(`${e.title || "Event"} in ${boundary} min`, {
                  body: e.description || e.location || "",
                  silent: false,
                });
              } catch (_) { /* ignore */ }
            }
          }
        }
      }
    }, 30_000);
    return () => clearInterval(id);
  }, [events, notifGranted]);

  async function requestNotif() {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    setNotifGranted(perm === "granted");
  }

  const days = useMemo(() => buildMonthGrid(cursor), [cursor]);
  const byDay = useMemo(() => groupByDay(events), [events]);
  const selEvents = (byDay.get(selected) || []).slice().sort((a, b) => +new Date(a.start) - +new Date(b.start));

  return (
    <div className="grid h-full" style={{ gridTemplateColumns: "1fr 360px" }}>
      {/* Left: month */}
      <section className="flex min-h-0 flex-col border-r" style={{ borderColor: "var(--line-1)" }}>
        <div className="flex items-center gap-3 border-b px-4 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <CalendarDays size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>
            {cursor.toLocaleString([], { month: "long", year: "numeric" })}
          </span>
          <div className="ml-auto flex items-center gap-1">
            <IconBtn onClick={() => setCursor(shiftMonth(cursor, -1))}><ChevronLeft size={14} /></IconBtn>
            <button
              onClick={() => setCursor(startOfMonth(new Date()))}
              className="mono caps rounded border px-2 py-0.5 text-[10px]"
              style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
            >today</button>
            <IconBtn onClick={() => setCursor(shiftMonth(cursor, 1))}><ChevronRight size={14} /></IconBtn>

            <div className="mx-2 h-4 w-px" style={{ background: "var(--line-1)" }} />

            <button
              onClick={notifGranted ? null : requestNotif}
              className="flex items-center gap-1 rounded border px-2 py-0.5 mono text-[10px]"
              style={{
                borderColor: notifGranted ? theme.accent : "var(--line-1)",
                color: notifGranted ? theme.accent : "var(--fg-2)",
              }}
              title={notifGranted ? "Reminders on" : "Enable reminders"}
            >
              {notifGranted ? <Bell size={11} /> : <BellOff size={11} />}
              {notifGranted ? "reminders on" : "enable reminders"}
            </button>
          </div>
        </div>

        {error && (
          <div className="m-3 rounded-lg border px-3 py-2 text-[12.5px]"
               style={{ borderColor: "#ff5a7855", background: "#ff5a7815", color: "var(--fg-1)" }}>
            <div className="mono caps text-[10px]" style={{ color: "#ff5a78" }}>Calendar offline</div>
            {error}
            <div className="mt-1 mono text-[11px]" style={{ color: "var(--fg-3)" }}>
              Wire <code>/api/calendar/events</code> (GET / POST / DELETE) and this grid will hydrate.
            </div>
          </div>
        )}

        {/* Weekday header */}
        <div className="grid grid-cols-7 border-b" style={{ borderColor: "var(--line-1)" }}>
          {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map((d) => (
            <div key={d} className="mono caps px-3 py-2 text-[10px]" style={{ color: "var(--fg-3)" }}>{d}</div>
          ))}
        </div>

        {/* Day cells */}
        <div className="grid grid-cols-7 flex-1 overflow-hidden"
             style={{ gridTemplateRows: `repeat(${Math.ceil(days.length/7)}, minmax(0,1fr))` }}>
          {days.map((d) => {
            const iso = d.iso;
            const isSel = iso === selected;
            const isTod = iso === todayISO();
            const dayEvents = byDay.get(iso) || [];
            return (
              <button
                key={iso}
                onClick={() => setSelected(iso)}
                onDoubleClick={() => setCreating({ date: iso })}
                className="flex min-h-0 flex-col gap-1 border-b border-r px-2 py-1.5 text-left text-[12px]"
                style={{
                  borderColor: "var(--line-1)",
                  background: isSel ? "var(--accent-soft)" : d.inMonth ? "var(--bg-0)" : "var(--bg-1)",
                  color: d.inMonth ? "var(--fg-1)" : "var(--fg-3)",
                }}
              >
                <div className="flex items-center gap-1">
                  <span
                    className={isTod ? "grid h-5 w-5 place-items-center rounded-full" : ""}
                    style={isTod ? {
                      background: theme.accent, color: "#05070d", fontWeight: 600,
                    } : {}}
                  >{d.date.getDate()}</span>
                  {dayEvents.length > 0 && (
                    <span className="ml-auto mono text-[9px]" style={{ color: "var(--fg-3)" }}>
                      ×{dayEvents.length}
                    </span>
                  )}
                </div>
                <div className="flex flex-col gap-0.5 overflow-hidden">
                  {dayEvents.slice(0, 3).map((e) => (
                    <div
                      key={e.id}
                      className="truncate rounded px-1 py-0.5 mono text-[10px]"
                      style={{
                        background: (e.color || theme.accent) + "22",
                        color: e.color || theme.accent,
                        border: `1px solid ${(e.color || theme.accent)}55`,
                      }}
                    >
                      {formatTime(e.start)} {e.title}
                    </div>
                  ))}
                  {dayEvents.length > 3 && (
                    <span className="mono text-[9px]" style={{ color: "var(--fg-3)" }}>
                      +{dayEvents.length - 3} more
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Right: day detail + quick add */}
      <aside className="flex min-h-0 flex-col" style={{ background: "var(--bg-0)" }}>
        <div className="flex items-center gap-2 border-b px-3 py-3"
             style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
          <Sparkles size={14} style={{ color: theme.accent }} />
          <span className="mono caps" style={{ color: "var(--fg-2)" }}>
            {new Date(selected).toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" })}
          </span>
          <button
            onClick={() => setCreating({ date: selected })}
            className="ml-auto flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px]"
            style={{ background: theme.accent, color: "#05070d" }}
          >
            <Plus size={11} /> event
          </button>
        </div>

        {creating && (
          <EventComposer
            theme={theme}
            date={creating.date}
            onCancel={() => setCreating(null)}
            onSave={addEvent}
          />
        )}

        <div className="scrollbar-thin flex-1 overflow-y-auto px-4 py-3">
          {selEvents.length === 0 && !creating && (
            <div className="py-10 text-center text-sm" style={{ color: "var(--fg-3)" }}>
              Nothing scheduled. Double-click a day to add something.
            </div>
          )}
          <ul className="flex flex-col gap-3">
            {selEvents.map((e) => (
              <li key={e.id} className="uui-card"
                  style={{ background: "var(--bg-1)", borderColor: "var(--line-1)" }}>
                <div className="flex items-center gap-2 border-b px-3 py-1.5"
                     style={{ borderColor: "var(--line-1)" }}>
                  <span className="h-2 w-2 rounded-full"
                        style={{ background: e.color || theme.accent }} />
                  <span className="mono caps text-[10px]" style={{ color: "var(--fg-3)" }}>
                    {formatTime(e.start)}
                    {e.end ? ` – ${formatTime(e.end)}` : ""}
                  </span>
                  <button
                    onClick={() => delEvent(e.id)}
                    className="ml-auto rounded border px-1 py-0.5 mono text-[10px]"
                    style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}
                    title="Delete"
                  ><X size={10} /></button>
                </div>
                <div className="px-3 py-2">
                  <div className="text-sm font-semibold" style={{ color: "var(--fg-0)" }}>
                    {e.title}
                  </div>
                  {e.location && (
                    <div className="mono text-[11px]" style={{ color: "var(--fg-3)" }}>@ {e.location}</div>
                  )}
                  {e.description && (
                    <div className="mt-1 text-[12.5px] whitespace-pre-wrap" style={{ color: "var(--fg-1)" }}>
                      {e.description}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="border-t px-3 py-2 mono text-[10px]" style={{ borderColor: "var(--line-1)", color: "var(--fg-3)" }}>
          <Clock size={10} className="mr-1 inline" />
          {loading ? "syncing…" : `${events.length} events in view`}
        </div>
      </aside>
    </div>
  );
}

function EventComposer({ theme, date, onCancel, onSave }) {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState(`${date}T09:00`);
  const [end, setEnd]     = useState(`${date}T10:00`);
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");

  return (
    <div className="border-b p-3" style={{ borderColor: "var(--line-1)", background: "var(--bg-1)" }}>
      <div className="terminal-card">
        <div className="bar">
          <span className="dot r" /><span className="dot y" /><span className="dot g" />
          <span className="ml-2 mono caps">New event</span>
          <button onClick={onCancel} className="ml-auto mono text-[11px]"
                  style={{ color: "var(--fg-3)" }}><X size={11} /></button>
        </div>
        <div className="flex flex-col gap-2 p-3 text-[12.5px]">
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="mono rounded-md border bg-transparent px-2 py-1 outline-none"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-0)" }}
          />
          <div className="grid grid-cols-2 gap-2">
            <LabeledDateTime label="start" value={start} onChange={setStart} />
            <LabeledDateTime label="end"   value={end}   onChange={setEnd}   />
          </div>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Location (optional)"
            className="mono rounded-md border bg-transparent px-2 py-1 outline-none"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-1)" }}
          />
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Notes (optional)"
            className="mono rounded-md border bg-transparent px-2 py-1 outline-none"
            style={{ borderColor: "var(--line-1)", color: "var(--fg-1)" }}
          />
          <div className="flex items-center gap-2">
            <button
              onClick={() => title.trim() && onSave({
                title: title.trim(),
                start: new Date(start).toISOString(),
                end:   new Date(end).toISOString(),
                location, description,
              })}
              disabled={!title.trim()}
              className="rounded-md px-3 py-1 text-[12px] disabled:opacity-40"
              style={{
                background: theme.accent, color: "#05070d",
                boxShadow: `0 0 10px -3px ${theme.glow}`,
              }}
            >Save</button>
            <button onClick={onCancel}
                    className="mono caps rounded border px-2 py-0.5 text-[10px]"
                    style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}>Cancel</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function LabeledDateTime({ label, value, onChange }) {
  return (
    <label className="flex flex-col gap-0.5">
      <span className="mono caps text-[10px]" style={{ color: "var(--fg-3)" }}>{label}</span>
      <input
        type="datetime-local"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mono rounded-md border bg-transparent px-2 py-1 text-[12px] outline-none"
        style={{ borderColor: "var(--line-1)", color: "var(--fg-0)" }}
      />
    </label>
  );
}

function IconBtn({ children, onClick }) {
  return (
    <button
      onClick={onClick}
      className="grid h-6 w-6 place-items-center rounded border"
      style={{ borderColor: "var(--line-1)", color: "var(--fg-2)" }}
    >{children}</button>
  );
}

function startOfMonth(d) { const x = new Date(d); x.setDate(1); x.setHours(0,0,0,0); return x; }
function shiftMonth(d, n) { const x = new Date(d); x.setMonth(x.getMonth() + n); return x; }
function todayISO() { const d = new Date(); return isoDate(d); }
function isoDate(d) {
  const y = d.getFullYear(); const m = String(d.getMonth()+1).padStart(2,"0"); const dd = String(d.getDate()).padStart(2,"0");
  return `${y}-${m}-${dd}`;
}
function formatTime(v) {
  if (!v) return "";
  try { return new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
  catch (_) { return ""; }
}

function buildMonthGrid(cursor) {
  // Sunday-first 6x7 grid including spill-over.
  const first = startOfMonth(cursor);
  const lead = first.getDay(); // 0=Sun
  const grid = [];
  const start = new Date(first); start.setDate(first.getDate() - lead);
  for (let i = 0; i < 42; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i);
    grid.push({ date: d, iso: isoDate(d), inMonth: d.getMonth() === cursor.getMonth() });
  }
  return grid;
}

function groupByDay(events) {
  const m = new Map();
  for (const e of events) {
    const key = isoDate(new Date(e.start || e.date));
    if (!m.has(key)) m.set(key, []);
    m.get(key).push(e);
  }
  return m;
}
