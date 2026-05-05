# Legacy Dashboard (retired — pre-V2.2)

This folder preserves the single-file, FastAPI-served HTML dashboard that
predated the V2.2 UI restructure.

## Why it was retired

V2.2 consolidates the UI into a single React/Vite surface at
`frontend/` with three top-level tabs (**Chat**, **Cowork**, **Code**),
a persistent `TopBar`, a shared `LogDrawer`, and a turn-grouped
`ChangesRenderer` — none of which were expressible in a single
self-contained HTML file.

The legacy dashboard:

- embedded styles, scripts, and markup inline,
- polled `/api/*` from a FastAPI static-mount at `/`,
- had no persistent router state, no log filtering, no zone awareness,
- predated the Hacker Zone panel, the bridge audit log, and the change
  timeline (plan / routing / file_diff / memory_write / command /
  bridge / reply events).

See `docs/SYSTEM_DESIGN_V2.2.md` for the replacement design.

## Where the UI lives now

- Dev:  `cd frontend && npm run dev` → http://localhost:3000
- API:  FastAPI at http://localhost:8080 (or `OCTOPUS_PORT`) — **API-only**,
  no static-file mount. Root `/` returns a JSON pointer.

## Can I still run this?

Opening `index.html` directly in a browser will *fetch* the FastAPI endpoints
if the backend is running, but most of the UX assumes the old 9-agent
roster and has no concept of zones. It is preserved for reference only,
not as a supported surface. Do not wire it back into `api/main.py`.

Retired: V2.2 (see `docs/CHANGELOG_V2.2.md` once Phase F lands).
