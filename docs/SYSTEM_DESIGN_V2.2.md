# Octopus Agents — System Design V2.2

**Status:** Proposed → under implementation
**Author:** Claude (for Tyler)
**Date:** 2026-04-22
**Supersedes:** V2.1 adds the full model roster, the Hacker Zone, the Chat/Cowork/Code tab split, and the "changes-first" chat renderer. Everything in `SYSTEM_DESIGN_V2.1.md` is still load-bearing — read it first.

---

## 1. What V2.2 changes

V2.1 fixed the *plumbing* — memory layer, watchdogs, handoffs, GitHub, and the neural-link UI. V2.2 is about **surface area and UX**:

1. **Full model roster.** Every LM Studio model Tyler has installed becomes a named role in the mesh, not just the original nine. See §3.
2. **Hacker Zone.** The uncensored / abliterated models get their own sealed zone with its own memory namespace, its own dashboard panel, and zone-boundary routing rules. See §4.
3. **Dissolved legacy dashboard.** The old jQuery-ish `dashboard/` surface is retired; the React/Vite frontend is the only UI. FastAPI is API-only. See §5.
4. **Three-tab frontend.** The UI reorganizes around Chat / Cowork / Code — mirroring how Tyler already thinks about work. See §6.
5. **Change-first chat renderer.** Chat logs display as *changes* (file diffs, memory writes, routing events) instead of raw transcripts. Raw logs live in a collapsible right drawer. See §7.
6. **AgentMesh concepts adopted.** Team / Tools / Runner abstractions from MinimalFuture/AgentMesh, adapted to our Python stack. See §8.

---

## 2. Architecture deltas (at a glance)

```
                           ┌──────────────────────────────────┐
                           │       React/Vite Frontend        │
                           │   (only UI — :3000 in dev)       │
                           │ ┌─────┬────────┬──────────────┐ │
                           │ │Chat │Cowork  │Code          │ │
                           │ └─────┴────────┴──────────────┘ │
                           │  Brain Mesh │ Hacker Zone panel │
                           │  Logs drawer│ Project board     │
                           └──────────────┬───────────────────┘
                                          │ HTTP + WS
                                          ▼
                           ┌──────────────────────────────────┐
                           │     FastAPI (API-only, :8000)    │
                           │   /api/*  /ws  /docs  — no UI    │
                           └──────────────┬───────────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            │                             │                             │
            ▼                             ▼                             ▼
   ┌─────────────────┐          ┌──────────────────┐          ┌──────────────────┐
   │ Mainline Mesh   │          │  Hacker Zone     │          │  Memory layer    │
   │ (≈20 agents)    │◀─bridge─▶│  (15 agents)     │          │  SQLite + MD     │
   │ Orchestrator is │  audited │ hz_orchestrator  │          │  + Chroma + ObsMD│
   │ the only bridge │          │ is the only      │          │  (per-zone ns)   │
   └─────────────────┘          │ bridge endpoint  │          └──────────────────┘
                                └──────────────────┘
```

---

## 3. Full model roster → roles

Implemented in `config/agents_expanded.py`. Merges non-destructively with the original 9 in `settings.AGENT_ROLES` (same schema). Rough taxonomy:

**Mainline additions (10 roles)**

| Role id | Model | Purpose |
|---|---|---|
| `strategist` | `qwen/qwen3.6-27b` | Long-horizon planning, multi-step architecture work |
| `heavy_reasoning` | `qwen/qwen3-30b-a3b-2507` | MoE heavy-thinker for correctness-critical tasks |
| `heavy_dev` | `qwen/qwen3-coder-30b` | High-intensity coding work, large diffs |
| `vision` | `zai-org/glm-4.6v-flash` | Screenshots, image parsing, diagram reading |
| `scout` | `liquid/lfm2-24b-a2b` | Mid-weight agent for exploratory work |
| `micro_scout` | `liquid/lfm2.5-1.2b` | Cheap scan-pass for "is this worth looking at?" |
| `edge_agent` | `nvidia/nemotron-3-nano-4b` | Low-latency inline helper |
| `nemotron_heavy` | `nvidia/nemotron-3-nano` | Heavier nvidia variant for reasoning |
| `translator` | `openai/gpt-oss-20b` | Format/style/translation conversions |
| `legacy_baseline` | `google/gemma-2-9b` | Baseline comparison agent — always-on control |

**Hacker Zone (15 roles)** — all prefixed `hz_`. `hz_orchestrator` is the only bridge-capable endpoint; everything else stays sealed. Models include the abliterated / uncensored set (dolphin, dolphin-mistral, dolphin-mixtral, lexi-v1, lexi-v2, deepseek-r1-distill, etc.). See `agents_expanded.py` for the full mapping.

Each role gets: `name`, `emoji`, `color`, `description`, `tier`, `priority`, `default_model`, `zone`, `system_prompt`. System prompts explicitly instruct **builder-first behavior** (no "how would you like this done?" chatter; ask *one* sharp clarifying question only when truly ambiguous, then build).

---

## 4. Hacker Zone — zone isolation rules

Implemented in `config/zones.py`.

- **Constants:** `MAINLINE_ZONE = "mainline"`, `HACKER_ZONE = "hacker_zone"`.
- **Session state:** `SessionZoneState` is owned by the API, toggled by the UI when the Hacker Zone panel is opened. Engine reads it; engine does not mutate it.
- **Visibility:** HZ roles are literally invisible to a mainline session — they don't appear in agent pickers, Brain Mesh nodes, or status pages. This is stronger than "disabled"; a user with the panel closed doesn't know they exist.
- **Routing:** `can_route(source, target, active_zone, session)` is the single gate. Cross-zone routes require both endpoints in `BRIDGE_CAPABLE_ROLES` (currently `{orchestrator, hz_orchestrator}`) and `session.bridge_open=True`. Bridges auto-close after a single call and write to the audit log.
- **Memory namespacing:** HZ has its own SQLite file (`octopus_hz.db`), its own markdown root (`memory/hz_long_term/`), its own Chroma collection (`octopus_hz_rag`), and its own episodic root. Nothing in HZ can read mainline memory without a bridge. Embeddings are generated independently so vector-space leaks are impossible.
- **UI theme:** mainline is cyan/blue-violet; HZ is hot-pink/deep-violet. Brain Mesh colors nodes per-zone so the user sees the boundary at a glance.

---

## 5. Dissolve the legacy dashboard

- `api/main.py` no longer mounts `dashboard/` or serves `index.html`.
- Root `/` now returns a JSON pointer (`{service, role, ui_url, openapi_docs, ...}`).
- `dashboard/` folder is to be **archived** (not deleted) to `archive/legacy_dashboard/` with a README noting retirement date and the reason (V2.2 consolidation on React/Vite).
- `agents/engine_good.py` and `agents/engine_backup.py` archive similarly to `archive/engine_snapshots/`.
- The React frontend in `frontend/` is now authoritative. In dev: `cd frontend && npm run dev`.

---

## 6. Three-tab frontend — Chat / Cowork / Code

Structure in `frontend/src/App.jsx`:

```
App
├── TopBar          ← run-state pill, zone indicator, quick-switch
├── Tabs            ← Chat | Cowork | Code   (persistent)
├── ChatTab
│   ├── ConversationList (left, 260px)
│   ├── ChatPane (center)
│   │   └── ChangesRenderer
│   └── LogDrawer (right, collapsible, 360px)
├── CoworkTab
│   ├── Workspace picker (select folder)
│   ├── File tree + preview
│   ├── AgentActivity sidebar (who is touching what)
│   └── LogDrawer
├── CodeTab
│   ├── RepoList (GitHub-backed)
│   ├── Editor (Monaco) + diff view
│   ├── PR/commit sidebar
│   └── LogDrawer
└── FloatingPanels
    ├── BrainMesh (D3-force SVG)
    ├── ProjectBoard
    ├── HackerZone (gated — only rendered if user opens it)
    └── MCP/Skills/Memory/System routes (moved into TopBar overflow)
```

Key rules:

- **TopBar stays sticky** across all tabs.
- **LogDrawer is shared** — each tab has its own filter, but the component is the same.
- **Hacker Zone is a floating panel, not a tab.** Opening it flips `SessionZoneState.hacker_zone_active` and repaints Brain Mesh in HZ colors.
- **Routing:** `react-router-dom` routes are `/chat`, `/cowork`, `/code` plus `/mcp`, `/memory`, `/system` for overflow.

---

## 7. Change-first chat renderer

The single biggest UX win. Instead of pasting raw transcripts into the Chat pane, we render a **timeline of changes** that agents made:

```
 ChangesRenderer
  ├── GroupedByTurn
  │   ├── UserMessageRow              (input bubble, sticky)
  │   ├── PlanRow                     (what orchestrator decided to do)
  │   ├── RoutingRow                  ("→ heavy_dev", arrow animation)
  │   ├── FileDiffRow                 (collapsed diff preview, expandable)
  │   ├── MemoryWriteRow              ("+ long_term/project_x/decision.md")
  │   ├── CommandRow                  (shell/build/test output summary)
  │   ├── BridgeRow                   (HZ bridge event — auditable, distinct)
  │   └── AgentReplyRow               (only if the reply is user-facing prose)
  └── LogDrawer (right, collapsible)
      └── RawLogStream                (every log line; filterable by agent/zone/level)
```

Implementation notes:
- Each change is an event emitted by the engine onto an `events` websocket.
- Events carry `{id, turn_id, kind, agent, zone, ts, payload, summary}`.
- The renderer groups by `turn_id`, collapses `summary` by default, expands on click.
- `kind=bridge` rows have a distinct red-violet highlight + "Audit" link.
- Raw logs are the full unfiltered firehose — power users open the drawer.

This kills "wall of text" chat fatigue and makes it obvious *what actually happened*.

---

## 8. AgentMesh concepts adopted

Adapted to our Python stack:

- **AgentTeam.** Formalize groupings we already have informally: `dev_team = {pm, dev, qa, critic, review, heavy_dev}`. Ask a team a question; the team's internal orchestrator decomposes. Lives at `agents/team.py` (new).
- **Tool registry.** Centralize MCP tools + skills + native Python tools behind a single `tools.registry` interface. Agents request tools by name; the registry handles provenance and permissions.
- **Runner abstraction.** A "runner" is a substrate: LM Studio, Claude API, OpenAI API, etc. We already have `MultiProviderClient`; V2.2 promotes runners to first-class so we can add Ollama/vLLM later without touching agent code.
- **Multi-platform hooks.** AgentMesh exposes Desktop/Web/CLI surfaces. We keep just Web for now but structure the event bus so a CLI surface is a straight re-bind.

---

## 9. DO/DON'T for agents (expanded)

Carried forward from V2.1, tightened for V2.2:

**DO**
- Ask **one** sharp clarifying question *only* when the task is truly ambiguous, then build.
- Emit structured events (plan → routing → file diffs → memory writes) — never dump raw prose when a diff would do.
- Commit into the three private GitHub repos with conventional-commit messages.
- Honor zone boundaries — refuse cross-zone calls unless you are bridge-capable AND a bridge is open.
- Log every LLM call with `{agent, model, zone, tokens_in, tokens_out, latency_ms}`.

**DON'T**
- Don't chat back a plan in prose and stop. Build it.
- Don't read or write the opposite zone's memory, ever.
- Don't return "I can help with that!" — route, act, or decline.
- Don't leak credentials into logs, memory, or prompts. Redact at the handler.
- Don't write to `main` branch directly — all changes via PR.

---

## 10. Skills per role (new)

Per-role SKILL.md files in `skills/<role_id>/SKILL.md` with:
- When this role is the best fit.
- Which tools this role is allowed to call.
- Exemplar inputs/outputs.
- Known failure modes.

V2.2 ships skills for: `dev`, `heavy_dev`, `review`, `critic`, `qa`, `devops`, `research`, `vision`, `strategist`. HZ roles each get their own skill file scoped to the HZ-only tool list.

---

## 11. Memory (short + long) — reminder

V2.1 already specced the six tiers. V2.2 adds:
- **Per-zone namespacing** (see §4).
- **Change-event table** in SQLite — backs the change-first renderer.
- **Vector re-embedding job** scheduled weekly in case the embedding model changes.

---

## 12. Phases (V2.2 delta on top of V2.1 phases)

- **V2.1 Phase 0–2** complete before starting V2.2.
- **V2.2 Phase A** — expand config: merge `agents_expanded.py` + `zones.py` into boot path; add per-role SKILL.md stubs.
- **V2.2 Phase B** — dissolve legacy dashboard, archive `engine_good.py`/`engine_backup.py`.
- **V2.2 Phase C** — frontend restructure: Chat/Cowork/Code tabs + LogDrawer + change-first renderer.
- **V2.2 Phase D** — Hacker Zone panel + zone-aware Brain Mesh colors + audit-log view.
- **V2.2 Phase E** — AgentTeam + Runner abstractions + per-role skill files.
- **V2.2 Phase F** — per-role benchmark sweep; retire the two duplicate nemotron slots if redundant.

---

## 13. Open questions (V2.2)

- Do we want the LogDrawer to be *global* (one drawer, filter by tab) or *per-tab* (three separate drawers)? Recommend global for lower mental overhead.
- Should Code tab embed Monaco or link out to VS Code? Recommend embedded Monaco for diff preview, deep-link out to VS Code for heavy editing.
- What is the "activity indicator" on the TopBar — token-budget bar, running-agents count, or both? Recommend both stacked, with the token bar going red at 65% (auto-compact trigger).

---

## 14. Pointers

- `config/agents_expanded.py` — full roster definitions
- `config/zones.py` — zone routing + namespacing
- `docs/SYSTEM_DESIGN_V2.1.md` — the foundation this builds on
- `docs/PERFECT_PROMPT.md` — the single copy-pasteable prompt that spins V2.2 up on a fresh session
