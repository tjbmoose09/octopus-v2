# Octopus Agents V2.1 — System Design

**Status:** Draft for review
**Author:** Claude (Cowork planning pass)
**Date:** 2026-04-22
**Scope:** Current-state diagnosis + new feature architecture (auto-compact memory, watchdogs, RAG, neural-link UI, GitHub integration)

---

## 0. TL;DR

The current V2 build is architecturally sound but has three classes of defects that make it behave like it's broken:

1. **Memory layer is in a retry death-spiral** — the Obsidian client has no circuit breaker, and the logging handler writes through the same channel that's failing, so every failure fans out into more failures.
2. **Short-term memory has no shape** — agents don't know when they're running out of context, there's no handoff protocol, and long-term facts are scattered across a flat vault.
3. **UI doesn't reflect what the system is doing** — a multi-agent mesh should *feel* alive; the current theme is a generic dashboard.

V2.1 addresses all three with a new memory architecture built on SQLite (primary) + a structured markdown tree (long-term) + an optional embeddings layer (RAG), a watchdog protocol for auto-compact/handoff, and a cyberpunk neural-link UI where brain regions pulse in response to agent activity.

---

## 1. Current-State Diagnosis

Concrete defects found in the codebase as of 2026-04-22. These block V2.1 work until stabilized.

### 1.1 Log-amplification loop (CRITICAL)

`agents/engine.py` lines 484-503. `ObsidianLogHandler.emit()` calls `memory_client.log_system()`, which calls `append_to_daily_note()`, which logs "Bootstrapping new daily note" and "save_note exception" through the same root logger. Each of those log lines re-enters the handler and spawns another failed Obsidian write. One real event fans out into 3-10 failed writes.

**Fix:** The Obsidian log handler must (a) filter out `octopus.memory` events so it can never log its own failures, (b) check `memory_client._healthy` before attempting a write, and (c) rate-limit to prevent flooding even when healthy.

### 1.2 No circuit breaker (CRITICAL)

`engine.py` lines 266-309. `self._healthy` is set by `health_check()` but never consulted by `_request()` or `save_note()`. Every call makes a 10-second-timeout network attempt. With Obsidian down, every memory write stalls for up to 10 seconds; combined with the amplification loop, agents freeze.

**Fix:** Add a 60-second health cache. All memory methods short-circuit to a local fallback when the cache is "down" and only re-probe on TTL expiry.

### 1.3 Read-modify-write on every log line (HIGH)

`engine.py` lines 390-417. `append_to_daily_note()` does `GET /vault/...` → edit in Python → `PUT /vault/...` for every pipeline event. This is O(N²) writes for N log entries and racy across concurrent agents — even with Obsidian up it would corrupt the daily note under load.

**Fix:** Buffer daily-log entries in an async queue; flush in batches every 5 seconds or every 20 entries. Daily note is the concatenation of a local markdown file + replayed buffer.

### 1.4 `print()` redirected into the root logger (MEDIUM)

`engine.py` lines 588-608. `_PrintToLogger` routes all stdout through the root logger, which has the Obsidian handler attached — so every `print("[Engine] …")` at startup becomes an Obsidian write and accelerates the log flood.

**Fix:** Either don't redirect stdout, or give `_PrintToLogger` its own logger that does NOT propagate to root.

### 1.5 Port default mismatch (LOW)

`config/memory.py` line 27 defaults to `http://localhost:27124` but `.env` correctly sets `27123`. The `.env` override wins today, but anyone running without `.env` silently talks to the wrong port.

**Fix:** Align the default to `27123` or remove the default entirely and require an env var.

### 1.6 Obsidian is a hard dependency for the logging system (ARCHITECTURAL)

The root cause under all five defects: the daily log is simultaneously a *logging sink* and a *feature that requires logging to work*. Writing to it logs, and logging writes to it. This is an inherent infinite loop the moment anything goes wrong.

**Fix:** Decouple. File logs are primary and always on. Obsidian is a mirror, opt-in, asynchronous, with bounded buffer. File logs never depend on Obsidian being reachable, and Obsidian writes never produce logs at the same level that gets mirrored back.

---

## 2. V2.1 Memory Architecture

Six tiers, each with a clear contract, clear storage backend, and clear failure mode. No single component can take down the system.

### Tier 1 — Working Memory (in-flight task state)

**Purpose:** Shared state between agents during active task execution. What the PM is currently planning, what the Dev is currently writing, what the orchestrator is routing.

**Storage:** In-process dict + SQLite `working_memory` table (write-through).

**Lifetime:** Bounded by task lifecycle. Evicted when task completes or fails.

**Read/write:** Synchronous, sub-millisecond. No network.

```sql
CREATE TABLE working_memory (
  task_id        TEXT NOT NULL,
  key            TEXT NOT NULL,
  value_json     TEXT NOT NULL,
  writer_agent   TEXT NOT NULL,
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (task_id, key)
);
```

### Tier 2 — Short-Term Memory (rolling per-agent context)

**Purpose:** Each agent's conversation window — recent messages, recent tool calls, recent intermediate outputs. This is where the auto-compact cycle lives.

**Storage:** SQLite `agent_context` table, one row per message with a token-count column.

**Lifetime:** Rolling window bounded by token budget per agent (e.g., 32K for dev, 128K for orchestrator). Older entries get summarized into a single "earlier context" block; oldest get archived into Tier 5 (episodic).

**The auto-compact cycle (implements Tyler's 65% handoff idea):**

```
┌─────────────────────────────────────────────────────┐
│ On every agent turn:                                │
│                                                     │
│   1. Sum tokens in short-term for this agent        │
│   2. If tokens > 65% of agent's budget:             │
│        a. Watchdog triggers                         │
│        b. Agent is asked to write a HANDOFF NOTE:   │
│           - Goal state                              │
│           - What has been completed                 │
│           - What is still pending                   │
│           - Open questions / blockers               │
│           - Relevant file paths and IDs             │
│        c. Handoff note is saved to Tier 3           │
│           (long-term/handoffs/{task_id}.md)         │
│        d. Older short-term entries are archived to  │
│           Tier 5 (episodic) and summarized to a     │
│           single "prior context" block              │
│        e. Next turn begins with: handoff note +     │
│           summary + fresh context capacity          │
└─────────────────────────────────────────────────────┘
```

The critical property: the handoff note is the *resume point*. Any agent (same one next turn, or a replacement one) can read `handoffs/{task_id}.md` and know exactly where to pick up.

**Why 65%:** Leaves 35% headroom so the agent has budget to actually *write* the handoff without hitting context exhaustion mid-sentence.

### Tier 3 — Long-Term Structured Memory (the topic tree)

**Purpose:** Persistent, human-readable facts organized by topic. The agents' institutional knowledge.

**Storage:** Local markdown tree at `<repo-root>/vault/long_term/`. Optional Obsidian mirror.

**Structure:**

```
vault/
├── memory.md                    ← Top-level facts file (Tyler's preferences, project axioms)
├── INDEX.md                     ← Auto-generated index of all topic folders
├── handoffs/                    ← Agent handoff notes (Tier 2 spillover)
│   └── {task_id}.md
├── long_term/
│   ├── INDEX.md
│   ├── coding/
│   │   ├── INDEX.md
│   │   ├── python/
│   │   │   ├── INDEX.md
│   │   │   ├── fastapi_patterns.md
│   │   │   └── sqlite_gotchas.md
│   │   ├── react/
│   │   └── sql/
│   ├── user_preferences/
│   │   ├── communication_style.md
│   │   └── decision_patterns.md
│   ├── project_context/
│   │   ├── octopus_architecture.md
│   │   └── lm_studio_models.md
│   └── solutions/
│       └── {category}/{title}.md
└── chat_logs/
    └── {yyyy-mm-dd}/
        └── {task_id}.md
```

**Index mechanics:** Each folder has an auto-maintained `INDEX.md` listing direct children + a one-line description. Agents read `INDEX.md` first to decide which branch to descend. This scales — an agent never has to scan 5,000 files, it descends the topic tree like a filesystem.

**Write contract:** When an agent learns something worth keeping (discovered a gotcha, found a pattern, made a decision), it calls `memory.save_fact(path="coding/python/fastapi_patterns.md", content=...)`. The memory layer:
1. Writes the file.
2. Appends a one-liner to the parent `INDEX.md`.
3. Enqueues for RAG embedding (Tier 4).
4. Enqueues for Obsidian mirror (Tier 6).

**Agent discoverability:** Before doing anything domain-specific, agents call `memory.browse_topic("coding/python/")` which returns the INDEX so they can read existing knowledge before repeating work.

### Tier 4 — RAG / Semantic Memory

**Purpose:** "Find me notes similar to X" across the entire vault, including images. This is what makes the tree *searchable* instead of just *browsable*.

**Storage:** SQLite (with `sqlite-vec` extension) or a dedicated local vector DB — recommend **ChromaDB** in local mode, single directory, no server needed.

**Embedding model choice — DECIDED (2026-04-22):**

| Use case | Selected | Rationale |
|----------|----------|-----------|
| Text (md, txt, code) | **Qwen3-Embedding-4B** (to be downloaded into LM Studio) | Qwen family consistency with the rest of the stack, 4B params = good speed/quality balance for Tyler's setup, ~2560-dim. Configurable to 0.6B (faster) or 8B (higher quality) via `EMBEDDING_MODEL` env var. |
| Images | Local CLIP (`clip-vit-base-patch32` via ONNX) — deferred to V2.2 | Local-free, no Gemini dependency. Wired in later when multimodal is needed. |
| Audio/video | Deferred to V2.2 — not needed for launch |

**Setup step for Tyler:** Download `Qwen3-Embedding-4B` from Hugging Face into LM Studio before Phase 3. The existing `text-embedding-nomic-embed-text-v1.5` can be kept as a fallback provider — the embedding interface is pluggable, so you can switch with a single config flag.

**Pluggability:** The embedding provider is configured in `config/memory.py` via an `EMBEDDING_MODEL` env var so you can swap providers without touching agent code. Variants that will work out of the box: `qwen3-embedding-4b` (default), `qwen3-embedding-0.6b`, `qwen3-embedding-8b`, `nomic-embed-text-v1.5`.

**Query interface:**

```python
memory.semantic_search(
    query="how did we handle FastAPI startup hooks?",
    top_k=5,
    modality="text",         # or "image", "any"
    scope="long_term/coding/",  # optional subtree filter
)
```

### Tier 5 — Episodic Memory (daily logs & chat history)

**Purpose:** Time-stamped append-only record of what happened. For debugging, audits, and replay.

**Storage:** Local markdown files at `vault/chat_logs/{yyyy-mm-dd}/{task_id}.md`. Rotated daily notes at `vault/daily_notes/{yyyy-mm-dd}.md`. File-based rotating logs at `database/LLM/*.log` (already working).

**Write discipline:** Buffered async queue → flush every 5s or 20 entries. Never blocks the agent path. Never re-enters the logging system.

### Tier 6 — Obsidian Mirror (optional, async, off by default)

**Purpose:** Give you a pretty UI for browsing long-term memory in Obsidian. Not the source of truth.

**Mechanics:**
- Disabled by default (`OBSIDIAN_ENABLED=false`).
- When enabled, runs as a background task that watches the local vault for changes and mirrors them to Obsidian's REST API.
- Has a circuit breaker with 60s TTL. If Obsidian is unreachable, mirroring pauses silently.
- Never produces INFO-level logs that could re-enter the logging pipeline. Warnings only, written to `obsidian_mirror.log` exclusively.
- Has a bounded queue (max 1000 pending). If full, oldest mirror events are dropped with a single WARN line per 100 drops.

This means: **Obsidian going down cannot break the system**. It just means the Obsidian copy is stale until Obsidian is back.

---

## 3. The Watchdog Pattern

Per Tyler's "watchdogs and sub dogs" concept — a hierarchy of lightweight monitors that watch agents and fire events when thresholds are hit. Not full agents (they don't run LLM calls); they're small Python coroutines.

### Primary watchdog (one per active agent)

Runs alongside each agent's turn. Monitors:

| Signal | Threshold | Action |
|--------|-----------|--------|
| Token usage | ≥ 65% of budget | Trigger compact/handoff cycle (Tier 2) |
| Turn elapsed | ≥ agent's timeout (120s default) | Surface "agent stalled" event; orchestrator can retry or reassign |
| Error rate | ≥ 3 consecutive errors | Pause agent, escalate to orchestrator with diagnostic dump |
| Output quality | heuristic drop (e.g., agent repeats itself) | Flag for Critic review before delivery |

### Sub-watchdogs (cross-cutting)

Global monitors that aren't tied to a single agent:

- **Memory watchdog** — monitors Tier 1/2 DB health, alerts if SQLite goes read-only or if vault disk is full.
- **Provider watchdog** — monitors LM Studio + Claude API health, updates routing table on failure.
- **Budget watchdog** — tracks Claude API token spend against a daily cap; pauses cloud routing when cap is hit.
- **Handoff watchdog** — reads `handoffs/` folder and alerts if a handoff note is older than N minutes without a continuation (orphaned work).

Watchdogs write events to the `pipeline_events` table (already exists) so the UI can render them in real time.

---

## 4. UI / Theme Redesign — "Neural Link"

**Aesthetic direction from the reference screenshot:** dark (near-black with faint blue glow), central 3D neural-network brain, neon/holographic accents, scan-line texture, blue as the primary activity color with other hues for event types.

### Layout

```
┌────────────────────────────────────────────────────────────────┐
│  [Logo]  Octopus V2.1 — Neural Link                  [Status]  │
├───────────────┬────────────────────────────────┬───────────────┤
│               │                                │               │
│  Agent Mesh   │         Brain Visualization    │  Activity     │
│  (left rail)  │   (center, 60% of viewport)    │  Feed         │
│               │                                │  (right rail) │
│  • Orchestr.  │    [3D neural network brain    │               │
│  • PM         │     with 9 nodes, one per     │  • handoff    │
│  • Dev        │     agent, pulsing in blue    │    written    │
│  • QA         │     when active, other hues   │  • dev start  │
│  • Critic     │     for event types]          │  • qa pass    │
│  • Review     │                                │               │
│  • DevOps     │                                │               │
│  • Automation │                                │               │
│  • Research   │                                │               │
│               │                                │               │
├───────────────┴────────────────────────────────┴───────────────┤
│  [Chat input]  [Upload files ↑]  [Image gen 🎨]  [GitHub ⬢]  │
├────────────────────────────────────────────────────────────────┤
│  Project Board   Devices on :localhost   Skills   Memory Map   │
└────────────────────────────────────────────────────────────────┘
```

### Color language (tie visuals to system events)

| Event | Color | Animation |
|-------|-------|-----------|
| Brain / memory read | Electric blue `#00d4ff` | Pulse along affected region, 800ms ease-out |
| Memory write | Cyan `#00ffe5` | Ripple outward from the writing agent node |
| LLM call in flight | Violet `#b967ff` | Rotating glow around the node until response |
| Handoff triggered | Amber `#ffb547` | Arc animation between source and dest nodes |
| Error / fail | Red `#ff3864` | Node shakes + desaturates to gray |
| Task complete | Green `#3bf7a3` | Node flashes once, then soft idle glow |
| Idle | Dim teal `#0a3d40` | 2% ambient pulse at 3s cadence |

All colors are defined as CSS variables in `frontend/src/styles/neural.css` so the theme is swappable.

### Implementation options (ranked by effort/payoff)

1. **2D SVG + D3-force + CSS keyframes (low effort, high payoff, recommended for v2.1 launch)**
   - Nodes are SVG circles, edges are D3-force links.
   - Glow via SVG `<filter>` with `feGaussianBlur`.
   - Pulses via CSS `@keyframes` driven by a `data-state` attribute.
   - ~1-2 days of work. Ships quickly.

2. **Three.js / react-three-fiber 3D brain (high effort, maximum visual impact)**
   - True 3D neural-mesh with depth, rotation, parallax.
   - Post-processing (bloom, chromatic aberration, scan lines) via `@react-three/postprocessing`.
   - ~1-2 weeks of work. Save for v2.2 unless you want the wow factor at launch.

3. **Hybrid (recommended long-term)**
   - Ship option 1 in v2.1. Replace the center panel with option 2 in v2.2 once the plumbing is stable.

### New dashboard fields (from Tyler's expanded spec)

| Field | Status | Notes |
|-------|--------|-------|
| GitHub connector | New panel | Section 5 of this doc |
| Devices connected to localhost (realtime) | New widget | Uses `netstat -ano` via subprocess + WebSocket to frontend; detects LM Studio, Obsidian, Octopus itself, any other local servers |
| Upload to command line (files, photos, code) | New widget | Drag-drop → uploaded into a session folder → agents can reference by path |
| Image creation | New widget | Calls best available image model (Gemini 2.5 Image, DALL-E 3, or local SDXL depending on what's configured); supports edit-by-prompt on uploaded images |
| Project board | New panel | Kanban-style board; agents push to it when they start/complete projects; mirrors to GitHub Projects |
| Memory map | New widget | Visual tree of the long-term memory structure; click a node → jump to that file |

---

## 5. GitHub Integration

Per Tyler's spec: connect agents to GitHub, post all chats into a log repo, all code into a main project repo, all dependencies into a third repo. All private.

### What needs to be set up

1. **A GitHub Personal Access Token (fine-grained, not classic)**
   - Scopes: `repo`, `workflow`, `project` (for Projects v2 access).
   - Stored in `.env` as `GITHUB_TOKEN=<token>`.
   - **SECURITY NOTE:** Do not paste raw account passwords into project instructions or memory files. Passwords give full account access; a scoped PAT is revocable and auditable. The password currently in the project instructions should be rotated on GitHub immediately and replaced with a PAT-only flow.

2. **Three private repositories (auto-created on first run if missing):**
   - `octopus-chats-log` — daily logs, chat transcripts, handoff notes. Mirrors `vault/chat_logs/` and `vault/daily_notes/`.
   - `octopus-projects` — the main code repo for agent-generated projects. One subfolder per project.
   - `octopus-dependencies` — lock files, vendor bundles, reproducible build manifests per project.

3. **The "NPS server" Tyler mentioned** — I think this is the official **GitHub MCP server** ([github.com/github/github-mcp-server](https://github.com/github/github-mcp-server)), which is an MCP server that exposes GitHub's API as tools. If that's what he meant, we:
   - Add it to `config/mcp_servers.py` as a new entry.
   - Route the `devops`, `dev`, and `review` agents to it.
   - No separate hosting — it runs alongside the agent process.

### Push cadence

- **Chats**: flush daily at midnight + on explicit "save session" command.
- **Code**: push every task completion (not every agent turn — too noisy).
- **Dependencies**: push whenever `requirements.txt` / `package.json` / lock files change.

### Commit discipline

- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Author = agent role (e.g., `Octopus Dev <dev@octopus.local>`).
- Co-authored-by trailer listing all agents that contributed to the task.
- Every commit references the originating `task_id` for traceability.

---

## 6. Dos and Don'ts — Expanded for V2.1

Current `AGENT_DOS` and `AGENT_DONTS` in `config/settings.py` are solid. Here are additions specific to the new architecture.

### New DOs

- **DO read the handoff note first.** Before any work on a task you didn't start, read `handoffs/{task_id}.md` in full.
- **DO browse the topic INDEX before exploring.** Use `memory.browse_topic(path)` before semantic search — cheap and precise.
- **DO write a handoff note when the watchdog fires.** Don't ignore the 65% signal; ignoring it truncates your next turn.
- **DO commit to GitHub at task completion.** A task isn't done until the code + chat log are pushed.
- **DO update the INDEX when you add to long-term memory.** Auto-indexing is a safety net, not a substitute for meaningful one-liner descriptions.

### New DON'Ts

- **DON'T write to Obsidian directly.** Always go through `memory.save_fact()` so the local vault stays the source of truth and Obsidian is a mirror.
- **DON'T log memory operations at INFO or higher.** Use DEBUG only. INFO logs in the memory layer re-enter the handler and can cascade.
- **DON'T bypass the watchdog by extending your own token budget.** The watchdog is protecting your quality, not limiting your capability.
- **DON'T push secrets to GitHub.** Every commit runs through a secret scanner (gitleaks) before push.
- **DON'T mutate long-term memory files owned by other agents without tagging them in the commit.** Traceability matters.

### Per-agent skill specialization (partial — full list in `config/skills.py`)

The existing skill assignments in `config/skills.py` (101 skills across 9 agents) are well-matched. One refinement for V2.1:

- **Dev**: gets `auto_compact_handoff_writer` and `handoff_reader` as top-priority skills (they run on every turn once watchdog fires).
- **Review**: gets `handoff_quality_gate` — reviews the handoff note before it's saved, because a bad handoff means the next agent starts from a bad place.
- **Orchestrator**: gets `watchdog_event_router` — decides what to do when a watchdog fires (retry, reassign, escalate, swap model).

Before fully expanding skills, a question for Tyler is included in Section 9.

---

## 7. Implementation Phases

Sequenced so each phase leaves the system in a better state than the one before. Each phase is independently deployable.

### Phase 0 — Stabilize (2-3 hours)

Purpose: Stop the log spam and the retry storm. No new features.

- Break the log loop (filter `octopus.memory` from `ObsidianLogHandler`).
- Add `_healthy` TTL cache + short-circuit to all memory methods.
- Drop timeout from 10s → 2s.
- Fix the port default.
- Don't redirect stdout through the root logger.

**Deliverable:** A clean startup with at most 1 warning line when Obsidian is down ("Obsidian mirror disabled — server unreachable"), and zero retry storms. Everything else keeps working.

### Phase 1 — Memory layer rewrite (1-2 days)

Purpose: Replace the Obsidian-primary architecture with SQLite-primary + local-markdown-primary + optional Obsidian mirror.

- New `memory/store.py` — unified MemoryStore interface with the six tiers.
- New `memory/schema.sql` — tables for `working_memory`, `agent_context`, `handoff_notes`, `embedding_index`.
- New `memory/daily_log.py` — buffered async writer, local file first.
- New `memory/obsidian_mirror.py` — optional background mirror with circuit breaker.
- Migrate `engine.py` calls from `memory_client.save_*` to `memory_store.save_*`.
- Deprecate `ObsidianMemoryClient` (keep file for one release, then remove).

**Deliverable:** Every memory operation has a local-only success path. Obsidian can be turned off entirely with zero functional impact.

### Phase 2 — Auto-compact + watchdogs (1-2 days)

- Token counter per agent turn.
- Primary watchdog that fires at 65%.
- Handoff note writer (agent skill).
- Handoff note reader (agent skill).
- Sub-watchdogs: memory, provider, budget, handoff.
- Watchdog event stream to UI via WebSocket.

**Deliverable:** Long-running tasks survive across compact cycles without context loss. The UI shows the compact event visibly.

### Phase 3 — Long-term tree + RAG (2-3 days)

- Directory structure under `vault/long_term/`.
- `INDEX.md` auto-maintenance on write.
- `memory.md` top-level facts file with seeded content (user prefs from project instructions + memory files).
- ChromaDB integration + pluggable embedding provider.
- Semantic search API + agent skill.

**Deliverable:** Agents can browse topics, search semantically, and save learnings. Tyler can `cd vault/long_term/` and read the system's brain.

### Phase 4 — GitHub integration (1 day)

- Auto-create the three private repos.
- GitHub MCP server wired in.
- Push cadence hooks on task completion + daily flush.
- Conventional-commit helper used by all agents.

**Deliverable:** Every agent action leaves a GitHub commit. Tyler's repos become the persistent record.

### Phase 5 — Neural-link UI (3-5 days)

- New theme CSS with all color variables.
- SVG neural-mesh visualization with D3-force.
- Activity pulse engine driven by the watchdog event stream.
- New dashboard panels (GitHub, devices, uploads, image gen, project board, memory map).
- Kill the old theme.

**Deliverable:** The UI you pasted in the screenshot (or close to it), running against live system events.

### Phase 6 — Image generation + file uploads (1-2 days)

- Upload widget with file/image/code support, drag-drop.
- Image generation panel with model picker (Gemini 2.5 Image / DALL-E / local SDXL).
- Image edit-by-prompt for uploaded images.

**Deliverable:** Tyler can drop a photo and say "add laser eyes" and it works.

### Phase 7 — 3D brain upgrade (optional, 1-2 weeks)

If v2.1 launches with the 2D SVG and you want the full 3D neural-mesh look later.

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Handoff notes compound — each compact cycle triples context size | MEDIUM | HIGH | Handoff notes have a hard 2KB limit; longer notes get summarized before being written |
| SQLite write contention with 9 concurrent agents | LOW | MEDIUM | WAL mode + per-table locks; already in place for `octopus.db` |
| Embedding index drifts from source files | MEDIUM | LOW | Background reconciliation job runs hourly; integrity check at startup |
| Obsidian mirror queue fills up during a long outage | LOW | LOW | Bounded queue with drop-oldest policy; full re-sync available on demand |
| GitHub PAT leaks via commit | MEDIUM | HIGH | Pre-push gitleaks hook; token is never written to any tracked file; `.env` is in `.gitignore` |
| Neural-link UI hurts performance on low-end browsers | LOW | LOW | Feature-flag the animation layer; fallback to static dashboard via query param |

---

## 9. Decisions Log (resolved 2026-04-22)

Tyler's answers to the open questions, captured here so future sessions have the authoritative decisions.

1. **Embeddings model** — Qwen embedding family. Default: `Qwen3-Embedding-4B`. Pluggable via `EMBEDDING_MODEL` env var (0.6B / 4B / 8B / nomic as fallback options). Download step required before Phase 3.

2. **Watchdog scope** — **Hybrid.** Primary watchdogs are rule-based Python monitors (cheap, always-on, fire on token/timer/error thresholds). Quality-gate watchdogs are LLM-backed and only fire on specific events — e.g., Review agent validates a handoff note before it's saved. This gets the cost-efficiency of rules + the judgment of an LLM where it matters.

3. **Phase ordering** — **Phases 0 through 2 in sequence**, then pause for review before Phase 3+. That gets Tyler: log-spam fixed → memory layer rebuilt → auto-compact/watchdogs working. ~4-5 days elapsed. UI + GitHub + RAG come after.

4. **GitHub authentication** — Tyler will rotate his password and create a fine-grained PAT himself, then drop it in `.env` as `GITHUB_TOKEN`. Claude will NOT save the password that was in project instructions to any memory file. Recommendation to Tyler: remove the password from the project-instructions text in the Cowork UI as well (since it's now been logged in the conversation), and rely solely on the `.env` PAT going forward.

### Still open (decide before their relevant phase starts)

5. **Project board source of truth** (Phase 5) — dashboard-authoritative vs. GitHub-authoritative. Recommending dashboard-authoritative with GitHub as a mirror. Re-decide at Phase 5 kickoff.

6. **Auto-compact threshold for orchestrator** (Phase 2) — 65% (same as arm agents) or 80% (orchestrator-specific, since it has bigger budget)? Recommending 80%. Re-decide at Phase 2 kickoff.

---

## 10. Glossary

- **Brain tier** — the orchestrator. One agent, big model, routes everything.
- **Arm tier** — the eight specialist agents (PM, Dev, QA, Critic, Review, DevOps, Automation, Research).
- **Handoff note** — a markdown file an agent writes at the 65% compact boundary, summarizing state so the next turn can resume cleanly.
- **Watchdog** — a lightweight monitor that fires events on threshold breaches.
- **Circuit breaker** — a TTL-based cache on a health check that prevents the client from hammering a dead endpoint.
- **Tier N memory** — see Section 2.
- **Vault** — the local markdown tree at `<repo-root>/vault/`. Source of truth for long-term memory.
- **Obsidian mirror** — an optional async sync of the vault into Obsidian's REST API for Tyler to browse in the Obsidian app.
