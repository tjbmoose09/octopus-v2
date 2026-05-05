// Octopus V2.2 — ring-buffered /ws subscriber.
// Deduplicates quickly-repeating events (same task_id + event_type + msg
// within 50ms) so the UI doesn't flicker when the backend emits burst
// pipeline events.

import { useEffect, useRef, useState } from "react";
import { connect } from "../lib/ws";

const MAX_EVENTS = 500;

export function useLiveLog() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState({ state: "connecting" });
  const lastSig = useRef({ sig: null, ts: 0 });

  useEffect(() => {
    const c = connect(
      (evt) => {
        const now = Date.now();
        const sig = `${evt.task_id || ""}|${evt.event_type || ""}|${(evt.message || "").slice(0, 40)}`;
        if (sig === lastSig.current.sig && now - lastSig.current.ts < 50) return;
        lastSig.current = { sig, ts: now };
        setEvents((prev) => {
          const next = [...prev, { ...evt, _rx: now }];
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
        });
      },
      (s) => setStatus(s)
    );
    return () => c.close();
  }, []);

  return { events, status, clear: () => setEvents([]) };
}

// Group a flat event list by `task_id` → "turn". Orders turns by their
// first event's timestamp. Used by ChangesRenderer.
export function groupByTurn(events) {
  const turns = new Map();
  for (const e of events) {
    const id = e.task_id || "_untagged";
    if (!turns.has(id)) turns.set(id, []);
    turns.get(id).push(e);
  }
  const out = [];
  for (const [id, list] of turns.entries()) {
    const first = list[0];
    out.push({
      id,
      startedAt: first?.timestamp || new Date(first?._rx || Date.now()).toISOString(),
      events: list,
    });
  }
  out.sort((a, b) => String(a.startedAt).localeCompare(String(b.startedAt)));
  return out;
}
