# Octopus V2.2 — Frontend

A single React / Vite surface for the Octopus Agents mesh. Three top-level
tabs (**Chat**, **Cowork**, **Code**) plus two workflow surfaces (**Email**,
**Calendar**), all wrapped by:

- a persistent `TopBar` with primary tabs, the Hacker-Zone toggle, an
  overflow menu of pre-V2.2 pages (Agents / Pipeline / Projects / Skills /
  MCP / Memory / System) and a Cursor-style command palette launcher,
- a `SurfaceRow` (Cursor-inspired Desktop / Terminal / Web / Extension
  pills) that tells the agent mesh where the current run targets,
- a left `AgentMeshSidebar` — a live octopus-tentacle viz that pulses on
  routing events and filters the `ChangesRenderer` when an arm is clicked,
- a bottom `LogDrawer` streaming `/ws` events with filter pills and
  zone-tinted backgrounds,
- a `ChangesRenderer` that groups pipeline events by **turn** and renders
  them Cursor-style (`Thought 3s`, `Read 3 files`, `Planned 2s`,
  collapsible plan blocks, file-diff previews, bridge call receipts).

## Dev

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

`/api/*` and `/ws` are proxied to the FastAPI backend at
`http://localhost:8080`. Override with the `OCTOPUS_API_URL` env var if
your backend isn't on the default port.

## Build

```bash
npm run build        # → dist/
npm run preview
```

## Layout

```
src/
├── main.jsx                # Vite entry; installs ZoneProvider
├── App.jsx                 # BrowserRouter + shell (TopBar / SurfaceRow / Sidebar / Drawer)
├── index.css               # Tailwind v4 + V2.2 theme tokens + scrollbar
├── lib/
│   ├── api.js              # fetchers for /api/*
│   ├── ws.js               # /ws client with auto-reconnect
│   └── theme.js            # mainline / hacker-zone palette (mirrors config/zones.py)
├── hooks/
│   ├── useZone.jsx         # zone context + POST /api/session/zone
│   └── useLiveLog.js       # subscribes to /ws, ring-buffers events
├── components/
│   ├── TopBar.jsx
│   ├── SurfaceRow.jsx      # Cursor-style surface pills
│   ├── AgentMeshSidebar.jsx
│   ├── ThinkingStream.jsx  # Cursor "Thought 3s / Read N files / Planned Ns"
│   ├── ChangesRenderer.jsx # turn-grouped pipeline events
│   ├── LogDrawer.jsx       # bottom slide-out
│   ├── ZoneBadge.jsx       # HZ toggle chip
│   └── CommandPalette.jsx  # ⌘K launcher
└── pages/
    ├── ChatV2.jsx          # new chat surface (Cursor-inspired)
    ├── CoworkPage.jsx
    ├── CodePage.jsx
    ├── EmailPage.jsx       # Gmail triage + compose
    ├── CalendarPage.jsx    # month grid + event CRUD + Notification API
    ├── Agents.jsx          # (legacy, overflow route)
    ├── Pipeline.jsx        # (legacy, overflow route)
    ├── Projects.jsx        # (legacy, overflow route)
    ├── Skills.jsx          # (legacy, overflow route)
    ├── MCPServers.jsx      # (legacy, overflow route)
    ├── Memory.jsx          # (legacy, overflow route)
    └── SystemStatus.jsx    # (legacy, overflow route)
```

## Zone awareness

`src/lib/theme.js` mirrors `config/zones.py::ZONE_UI_THEME`. The
`ZoneProvider` (`src/hooks/useZone.jsx`) exposes `{ zone, setZone, theme }`
to any component; toggling the Hacker Zone badge re-tints the whole
surface (TopBar glow, LogDrawer border, ChangesRenderer spine) and calls
`POST /api/session/zone` so the backend `SessionZoneState` flips too.

## Cursor-inspired streaming

`ThinkingStream` models each agent run as a sequence of status lines —
`Thought 3s`, `Read 2 files, 1 directory`, `Planned 2s`, `→ Add a
follow-up`, `Plan (shift+tab to cycle)`. It listens to the same `/ws`
event stream the `LogDrawer` uses, but renders the events inline with the
assistant reply (vs. the drawer's flat log view).
