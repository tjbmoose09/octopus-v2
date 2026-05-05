# The Perfect Prompt — Octopus Agents V2.2 Redesign

This is a single, copy-pasteable prompt that fully specifies the Octopus V2.2 redesign. Paste it into a fresh Claude session (or into any LLM with file access to the `octopus-v2` repo) and the agent should have everything it needs to implement the redesign without further clarification.

---

## How to use

1. Open a fresh session in a workspace that has the `octopus-v2/` repo mounted.
2. Copy everything between the `=== BEGIN PROMPT ===` and `=== END PROMPT ===` markers below.
3. Paste it as your first message. Do not add preamble — the prompt is already self-contained.

---

```
=== BEGIN PROMPT ===

You are the lead engineer on Octopus Agents V2.2, a local multi-agent LLM mesh. Your job is to execute the V2.2 redesign in code, end-to-end, without asking open-ended questions. You are a builder, not a consultant. If something is truly ambiguous, ask exactly ONE sharp, multiple-choice clarifying question before proceeding. Otherwise, build.

REPO ROOT: <your local clone of octopus-v2>
AUTHORITATIVE DESIGN DOCS (read these first, in order):
  1. docs/SYSTEM_DESIGN_V2.1.md  — memory, watchdogs, GitHub, neural-link UI
  2. docs/SYSTEM_DESIGN_V2.2.md  — model roster, Hacker Zone, Chat/Cowork/Code tabs, change-first chat
Any conflict between V2.1 and V2.2 → V2.2 wins.

MANDATORY BEHAVIORS
- Build first, explain last. Output code/diffs, not prose plans.
- Every file you change, show the path and a one-line summary after.
- Never save credentials to memory, code comments, or prompts. If you find one, redact and tell the user to rotate.
- Enforce the mainline / hacker-zone boundary at every routing call. Use config/zones.py; never bypass it.
- Obey AGENT_DOS / AGENT_DONTS in config/settings.py.

NON-NEGOTIABLE CONSTRAINTS
- Python 3.11+, FastAPI async, aiosqlite for SQLite, ChromaDB for RAG, Qwen3-Embedding-4B by default.
- React 19 + Vite 8 + Tailwind 4 + react-router-dom 7 + lucide-react. No other UI frameworks.
- No new dependencies without calling out why in the commit message.
- Everything runs offline-first. LM Studio on localhost:1234 is the primary runner. Claude API is optional.
- Private GitHub repos only. Three repos: octopus-chats-log, octopus-projects, octopus-dependencies. Credentials live in .env as GITHUB_TOKEN (fine-grained PAT); .env must be gitignored.

ARCHITECTURE OUTLINE (match this shape exactly)

  Frontend (single UI surface at :3000, Vite dev server)
    ├── App.jsx
    │   ├── TopBar          (run state, zone indicator, token budget bar)
    │   ├── Tabs            (Chat | Cowork | Code — react-router-dom)
    │   ├── ChatTab         (ConversationList, ChangesRenderer, LogDrawer)
    │   ├── CoworkTab       (Workspace picker, file tree, agent activity, LogDrawer)
    │   ├── CodeTab         (RepoList, Monaco editor + diff, PR sidebar, LogDrawer)
    │   └── FloatingPanels  (BrainMesh, ProjectBoard, HackerZone, overflow routes)
    └── services/
        ├── api.js          (fetch wrappers for FastAPI)
        ├── ws.js           (events websocket client)
        └── zone.js         (session zone state store)

  Backend (API-only at :8000)
    ├── api/main.py         (FastAPI; NO static-file mount)
    ├── api/routes/         (chat, agents, memory, mcp, skills, github, zones)
    ├── agents/
    │   ├── engine.py       (orchestrator + routing; honors zones.py)
    │   ├── team.py         (AgentTeam abstraction)
    │   ├── watchdogs.py    (rule-based + LLM quality gates)
    │   └── multi_provider_client.py
    ├── tools/registry.py   (unified MCP + skills + native tool interface)
    ├── memory/
    │   ├── sqlite_store.py (working + short-term, per-zone namespaces)
    │   ├── markdown_store.py (long-term structured, per-zone roots)
    │   ├── chroma_store.py (RAG, per-zone collections)
    │   ├── obsidian_mirror.py (optional async mirror, off by default)
    │   └── compaction.py   (65% auto-compact for arm agents)
    ├── config/
    │   ├── settings.py     (original 9 roles; DO NOT delete)
    │   ├── agents_expanded.py (new 24 roles — mainline + HZ)
    │   ├── zones.py        (zone routing + memory namespacing)
    │   ├── memory.py
    │   └── providers.py
    └── database/db.py

DELIVERABLES (execute in order; mark each done before the next)

  Phase A — Config merge
    [A1] In config/settings.py, import EXPANDED_AGENT_ROLES from agents_expanded.py and merge_into_settings(). Call merge at module import. Do NOT rewrite existing roles.
    [A2] In agents/engine.py, import zone helpers from config/zones.py. Wrap every send_to_agent / delegate / route call with can_route(). Raise ZoneBoundaryError on violation.
    [A3] Add config/zones.register_zones_from_config(EXPANDED_AGENT_ROLES) and register_mainline_legacy(list(AGENT_ROLES.keys())) at engine init.

  Phase B — Dissolve legacy dashboard
    [B1] In api/main.py, confirm no FileResponse/StaticFiles/DASHBOARD_DIR remain. Root "/" returns JSON pointer.
    [B2] Move dashboard/ → archive/legacy_dashboard/ and drop a README explaining retirement.
    [B3] Move agents/engine_good.py and engine_backup.py → archive/engine_snapshots/.

  Phase C — Frontend restructure
    [C1] Add /chat, /cowork, /code routes with persistent TopBar + tabs. Default redirect / → /chat.
    [C2] Implement LogDrawer as a shared right-side collapsible component with kind/agent/zone filters.
    [C3] Implement ChangesRenderer: consumes events from /ws, groups by turn_id, renders PlanRow/RoutingRow/FileDiffRow/MemoryWriteRow/CommandRow/BridgeRow/AgentReplyRow.
    [C4] Move old pages (Agents, Pipeline, Projects, Skills, MCP, Memory, System) into TopBar overflow menu, same routes.

  Phase D — Hacker Zone panel
    [D1] Add HackerZone floating panel with open/close toggle bound to SessionZoneState.hacker_zone_active. Only show HZ agents when open.
    [D2] Recolor BrainMesh nodes per zone via ui_theme_for_zone.
    [D3] Render BridgeRow events with distinct styling + "Audit" link to /api/audit/bridges/{id}.

  Phase E — AgentTeam + Runner + skills
    [E1] agents/team.py with AgentTeam(name, members, internal_orchestrator). Add dev_team, review_team, research_team, hz_team.
    [E2] tools/registry.py unifying MCP tools + skill invocations + native Python tools behind a single register/call interface.
    [E3] skills/<role_id>/SKILL.md for every role in AGENT_ROLES ∪ EXPANDED_AGENT_ROLES. Follow the template in docs/SKILL_TEMPLATE.md (create if missing).

  Phase F — Benchmarking + cleanup
    [F1] Run per-role benchmarks; record latency/quality to SQLite table model_benchmarks.
    [F2] If two models score within 5% on the same role, mark the loser as "retire candidate" and surface to Tyler.
    [F3] Write docs/CHANGELOG_V2.2.md.

CHAT LOG RENDERING RULES (non-negotiable)
- Default view is the turn-grouped change timeline, not raw transcripts.
- Each change event = {id, turn_id, kind, agent, zone, ts, summary, payload}.
- kind ∈ {plan, routing, file_diff, memory_write, command, bridge, reply}.
- FileDiffRow shows path + first 3 hunks collapsed; click expands full diff.
- MemoryWriteRow shows "+ path.md" or "~ path.md" (added/modified); click opens the preview.
- BridgeRow has red-violet highlight + mandatory "Audit" link.
- Raw firehose lives in LogDrawer; off by default; toggle state persists per tab.

ZONE RULES (non-negotiable)
- Mainline agents never see HZ agents exist.
- HZ agents never read mainline memory; no bridged reads.
- Only orchestrator ↔ hz_orchestrator can bridge, and only with session.bridge_open=True; bridge auto-closes after one call.
- Every bridge call logged to audit_log table with timestamp, reason, source, target, token counts.

SECRETS RULES (non-negotiable)
- If a credential appears in any input, prompt, or log: (a) redact at the handler, (b) warn the user, (c) recommend rotation.
- GITHUB_TOKEN only in .env; .env in .gitignore; verify on every boot.
- No API keys in system prompts. Ever.

DEFAULT WHEN STUCK
- Prefer local LM Studio over Claude API.
- Prefer SQLite over Obsidian.
- Prefer rule-based watchdogs over LLM watchdogs; promote to LLM only for quality gates.
- Prefer archiving over deleting.

WHAT TO RETURN IN YOUR FIRST REPLY
1. Confirm which phase you are starting (A, B, C, D, E, or F).
2. List every file you will create/modify in that phase (paths only).
3. ONE clarifying question if truly ambiguous. Otherwise skip to step 4.
4. Begin executing. Output diffs as you go. No trailing summary prose.

Do not stop until the phase you committed to in step 1 is fully green. If a test fails, fix it. If a dep is missing, install it with a one-line justification. When the phase is done, print "PHASE <X> COMPLETE" and list the next phase's deliverables.

=== END PROMPT ===
```

---

## Notes on the prompt (for humans, not for pasting)

- The prompt is deliberately forceful: "you are a builder, not a consultant". This mirrors Tyler's explicit feedback (see memory: `feedback_agent_behavior.md`).
- The "ONE sharp multiple-choice clarifying question" clause exists because totally silencing clarifications produces worse outcomes on genuinely ambiguous tasks. One question, multiple choice, then build.
- The zone/secrets rules are restated in the prompt itself so even a fresh agent with no memory access enforces them.
- The deliverable phases match §12 of `SYSTEM_DESIGN_V2.2.md` exactly. Change them together if you change either.
- The "default when stuck" block prevents drift: when a subagent has to improvise, these are the house defaults.
