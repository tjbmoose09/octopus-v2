// Octopus V2.2 — thin typed fetchers for /api/*.
// All URLs are relative so the Vite proxy handles origin rewriting in dev
// and the same bundle works when served behind any reverse proxy in prod.

export const API = {
  agents:   () => get("/api/agents"),
  status:   () => get("/api/status"),
  pipeline: () => get("/api/pipeline"),
  system:   () => get("/api/system"),
  tasks:    () => get("/api/tasks"),

  // Phase C new endpoints
  sessionZone: (active, reason) =>
    post("/api/session/zone", { hacker_zone_active: !!active, reason: reason || null }),
  openBridge:  (reason) =>
    post("/api/session/bridge/open", { reason: reason || "" }),
  closeBridge: () =>
    post("/api/session/bridge/close", {}),

  // Chat / run
  send: (agent, task) => post("/api/send", { agent, task }),

  // Email / Calendar (Phase C workflow)
  emailInbox:   (limit) => get(`/api/email/inbox?limit=${limit || 25}`),
  emailCompose: (payload) => post("/api/email/compose", payload),
  emailTriage:  (messageId) => post("/api/email/triage", { message_id: messageId }),
  calendarList: (start, end) => get(`/api/calendar/events?start=${start}&end=${end}`),
  calendarAdd:  (evt) => post("/api/calendar/events", evt),
  calendarDel:  (id) => del(`/api/calendar/events/${id}`),
};

async function get(path) {
  const r = await fetch(path, { headers: { Accept: "application/json" } });
  return parse(r, path);
}

async function post(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return parse(r, path);
}

async function del(path) {
  const r = await fetch(path, { method: "DELETE" });
  return parse(r, path);
}

async function parse(r, path) {
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json())?.detail || ""; } catch (_) { /* ignore */ }
    return { error: `${r.status} ${r.statusText}${detail ? `: ${detail}` : ""}`, path };
  }
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("application/json")) return r.json();
  return { text: await r.text() };
}
