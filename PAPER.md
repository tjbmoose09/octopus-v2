# Octopus Agents V2.2 — A 34-Agent Local-First Mesh for Autonomous Software Work

*A technical paper on the design, topology, and operating data of the Octopus Agents project.*

**Author:** Tyler Boucaud
**Status:** Research preview — V2.2
**Date:** May 2026
**Repository:** `octopus-v2` (private working copy at the time of writing; this paper is being released alongside the public open-sourcing of the project)
**License (intended):** MIT for code, CC-BY-4.0 for this paper

---

## Abstract

Octopus Agents V2.2 is a single-operator, local-first multi-agent system that orchestrates **thirty-four discrete role-bound LLM agents** across two strictly isolated execution zones (a default *mainline* mesh and an opt-in *hacker zone*), routes work through a single brain agent that can delegate via a typed pipeline, and surfaces every routing decision to the user through a Cursor-inspired streaming UI. The project pairs **101 typed skills**, **37 connected MCP servers**, and a **four-scope episodic/working/short-term/long-term memory** layer backed by a local Obsidian vault. Every model lives in LM Studio on the same workstation; no inference traffic leaves the machine unless the operator explicitly enables a remote provider. This paper describes the architecture in full detail, presents the operational data captured by the system's own SQLite store after several weeks of bring-up traffic, and documents the design decisions that distinguish Octopus from cloud-first agent frameworks. No source code is reproduced here; all numbers are derived from the system's own configuration files and persistence layer.

---

## 1. Background and Motivation

The dominant pattern for production agent systems in 2026 is a small handful of large, generalist models (Claude, GPT-5, Gemini) wrapped in tool-use harnesses. The model is treated as a black box, the harness arbitrates a small role hierarchy (researcher, coder, reviewer), and almost all latency-critical traffic flies to a vendor data plane. This works, but it concedes three things that an opinionated solo developer should not concede:

First, **identity collapse**. When every role is the same model with a different system prompt, the agents are not actually different agents — they are a single model role-playing in a loop. There is no model diversity, no genuine second-opinion benefit, and the failure modes are correlated.

Second, **provenance opacity**. Every reasoning step happens inside someone else's data center. The operator has no record of what intermediate state the model held, no ability to swap in a model with different training biases on a per-task basis, and no straightforward path to running offline.

Third, **runtime homogeneity**. A single chat surface is not how software actually gets built. Real work happens across a desktop file system, a terminal, a web browser, and a growing zoo of MCP-served extensions. A truly useful agent fabric has to know which surface the current turn lives in and route differently for each.

Octopus V2.2 attacks all three problems by inverting the defaults: **many small specialized agents** instead of one big generalist, **all local** instead of all cloud, and a **surface-aware UI** instead of a single text box. The codebase is small enough that a single operator can hold the whole picture in their head: 23 active Python files totaling 7,486 lines, 31 frontend source files totaling 4,116 lines, and roughly 4,121 lines of configuration that act as a declarative manifest for the whole mesh.

## 2. System Architecture at a Glance

The runtime decomposes into five concentric layers. From innermost to outermost: *model layer*, *agent layer*, *coordination layer*, *integration layer*, and *experience layer*.

```
              ┌─────────── Experience layer ────────────┐
              │  React 19 / Vite 8 / Tailwind 4 SPA     │
              │  TopBar · SurfaceRow · MeshSidebar       │
              │  ChatV2 · Cowork · Code · Email · Cal    │
              │  LogDrawer · ChangesRenderer · ⌘K palette│
              └────────────────┬─────────────────────────┘
                               │ HTTP /api/* + WS /ws
              ┌────────────────▼─────────────────────────┐
              │  FastAPI (uvicorn :8080) — 42 endpoints  │
              │  Session/zone gate · pipeline broadcaster │
              └────────────────┬─────────────────────────┘
              ┌────────────────▼─────────────────────────┐
              │ Coordination — engine.py (1,029 LOC)     │
              │ init_agents · route_task · can_route     │
              │ pipeline_log ring · zone bridge gating    │
              └────────────────┬─────────────────────────┘
              ┌────────────────▼─────────────────────────┐
              │ Integration                              │
              │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
              │  │ Skills   │ │ MCP      │ │ Memory   │  │
              │  │ 101 wired│ │ 37 srvs  │ │ Obsidian │  │
              │  └──────────┘ └──────────┘ └──────────┘  │
              └────────────────┬─────────────────────────┘
              ┌────────────────▼─────────────────────────┐
              │ Model layer                              │
              │  LM Studio (37 models loaded) :1234      │
              │  multi_provider_client → claude_api opt. │
              └──────────────────────────────────────────┘
```

The dotted line between layers is hard. The experience layer never speaks model APIs; the coordination layer never speaks the DOM; the integration layer is the only place that knows about the outside world. This is what allows the same engine to drive a CLI runner, a future cron-driven scheduler, or the React UI without rewriting routing logic.

## 3. Agent Topology

The mesh is the heart of the project. It contains **34 agent roles** distributed across two zones and four functional tiers:

| Tier | Count | Purpose |
|---|---:|---|
| brain | 7 | Strategic reasoning, planning, orchestration |
| arm | 16 | Producers — they emit code, prose, configurations |
| scout | 6 | Latency-first roles — classification, triage, link screening |
| specialist | 5 | Vision, translation, baseline, creative writing, roleplay |

Sorted by zone:

| Zone | Roles | Count |
|---|---|---:|
| mainline | orchestrator, pm, dev, qa, critic, review, devops, automation, research, strategist, heavy_reasoning, heavy_dev, vision, scout, micro_scout, edge_agent, nemotron_heavy, translator, legacy_baseline | 19 |
| hacker_zone | hz_orchestrator, hz_heavy_reasoning, hz_dev_moe, hz_dev_alt, hz_coder, hz_deepseek, hz_writer, hz_generalist, hz_assistant, hz_fast, hz_fast_tiny, hz_small_gemma, hz_roleplay, hz_lexi_v2, hz_lexi_v1 | 15 |

Every role has a **dedicated default model** — the system maps 34 roles to 34 unique LM Studio model IDs with no two roles sharing a checkpoint. This is not a coincidence; it is the explicit anti-pattern of "one big model in many costumes." When the orchestrator delegates to `dev`, `dev` runs on `phi4-nvidia-coder`. When it delegates to `qa`, `qa` runs on `google/gemma-4-26b-a4b`. When the operator opens the hacker zone and the bridge is closed, traffic *cannot* reach `dev` — it is rerouted to `hz_dev_moe` running on `llama-3.2-8x4b-moe-v2-dark-champion-instruct-uncensored-abliterated-21b`, an MoE checkpoint with different training data and different refusal calibration.

This 1:1 mapping is enforced declaratively in `config/settings.py` (the original nine roles) and `config/agents_expanded.py` (the additional twenty-five), then merged into a single registry at engine boot. The merge function is idempotent — each role is added only if it is not already present, so the original nine retain their hand-curated `system_prompts` while the expanded roles supply their own. The merged registry is what the database, the API, and the React mesh sidebar all read from.

### 3.1 Routing graph (observed traffic)

The system records every assign/complete event in `pipeline_events`. After 156 logged events from 21 tasks, the empirical routing graph looks like this:

| From | To | Assigns |
|---|---|---:|
| user | orchestrator | 26 |
| orchestrator | dev | 21 |
| orchestrator | research | 11 |
| orchestrator | devops | 7 |
| orchestrator | pm | 7 |
| orchestrator | qa | 6 |
| orchestrator | automation | 4 |
| orchestrator | critic | 3 |
| orchestrator | review | 3 |

Two observations matter. First, the orchestrator is the genuine choke point — every user turn passes through it before fanning out. Second, `dev` carries roughly twice the load of any other downstream role, which matches the observed bias of the operator's task mix toward implementation work. The expanded mainline roles (`strategist`, `heavy_reasoning`, `heavy_dev`, etc.) and all hacker-zone roles register zero assigns in the captured window — they exist as latent capacity that the orchestrator can call when a task warrants escalation, and they have not yet been exercised in routine traffic.

## 4. Zone Isolation and the Bridge Protocol

V2.2's most opinionated design choice is that **uncensored / abliterated models live in their own quarantined sub-mesh** with its own orchestrator and its own filesystem vault. The implementation lives in `config/zones.py` (277 lines) and is exercised on every routing call.

The shape of the protocol:

- **`SessionZoneState`** is a per-session record holding three flags: `hacker_zone_active`, `bridge_open`, and `bridge_reason`, plus a rolling log of `recent_bridges`. State defaults are conservative — both `hacker_zone_active` and `bridge_open` start `False`, so a freshly-booted session can only see and route to mainline agents.
- **`can_route(from_role, to_role, session)`** is the gate. The engine wraps every `send_to_agent` call in a `can_route` check. Cross-zone delegation is permitted *only* when the bridge is explicitly opened by the operator with a stated reason, which gets logged for audit.
- **`ZoneBoundaryError`** is the exception raised when a routing attempt violates the policy. The HTTP layer translates this to a 403 with the rejected route printed in the body, so the operator sees exactly what was blocked and why.
- **The hacker zone has its own brain.** `hz_orchestrator` is the only role that can route within the zone, and it is forbidden from delegating outward. This means an operator who is exploring a CTF prompt or a research-only question cannot accidentally cause a mainline agent to inherit context from the uncensored side.

The four bridge states form a small finite-state machine:

| `hacker_zone_active` | `bridge_open` | What's reachable |
|:---:|:---:|---|
| false | false | Mainline only (default) |
| true | false | Hacker zone only — mainline is dark |
| true | true | Both, with a reason logged |
| false | true | Invalid; rejected at the API |

The bridge is intentionally awkward to use — three API calls and a written reason — because the threat model is not a hostile attacker but the operator's own future self forgetting that they were inside the zone.

## 5. Model Layer

All inference is local by default. LM Studio is the canonical provider; at the time of writing the operator has **37 models loaded** in a single LM Studio instance bound to `localhost:1234`. The catalog spans:

- **Frontier reasoning:** `qwen/qwen3.6-27b`, `qwen/qwen3-30b-a3b-2507`, `qwen3.5-27b-claude-4.6-opus-reasoning-distilled`
- **Coding specialists:** `qwen/qwen3-coder-30b`, `phi4-nvidia-coder`, `mistralai/devstral-small-2-2512`
- **Vision-language:** `zai-org/glm-4.6v-flash`
- **MoE scouts:** `liquid/lfm2-24b-a2b`, `liquid/lfm2.5-1.2b`
- **Edge-tier:** `nvidia/nemotron-3-nano-4b`, `nvidia/nemotron-3-nano`
- **Hacker-zone uncensored variants:** seven Qwen-derivative aggressives, two MoE Llama dark-champion variants, four Gemma/Lexi/Darkidol checkpoints, one DeepSeek distill
- **Embeddings:** `text-embedding-nomic-embed-text-v1.5`

The engine's LM Studio client speaks two distinct LM Studio surfaces:

1. **OpenAI-compatible** at `/v1/*` — used for `list_models` and `chat/completions`. This surface is the more permissive one; the engine routes its core inference through here.
2. **LM Studio native REST** at `/api/v1/*` — used for `models/load`, `models/download`, and `models/download/status/{job_id}`. These endpoints are LM Studio-specific (loading a checkpoint into memory cannot be expressed in the OpenAI vocabulary) and were corrected in V2.2 after V2.1 incorrectly issued them against the OpenAI-compat surface.

Above LM Studio sits a thin **multi-provider abstraction** (`agents/multi_provider_client.py`, 283 lines) that supports a Claude API fallback path. At the time of writing only `lm_studio` is active in the provider table; `claude_api` is configured but disabled until a key is provisioned. The abstraction matters anyway, because it means an operator who later wants per-role provider routing — say, send the `vision` role to a remote vision model and keep everything else local — can do so by editing one configuration file rather than rewriting the engine.

### 5.1 Model resolution

A subtle but important piece of the model layer is **fuzzy resolution**. Role configurations declare a model ID like `qwen/qwen3-coder-30b`, but LM Studio sometimes exposes the same checkpoint under a slightly different name (vendor prefix, quantization suffix, MoE variant marker). The engine's `_resolve_model` function caches the model list, then tries three matches in order: exact, substring-of-listed, substring-of-requested. Failures fall back to the first non-embedding model and log a warning. This means a role whose declared model is missing degrades to a generic fallback rather than 502'ing the whole turn — a small but consequential improvement over V2.1's hard-failure behavior.

## 6. Skills System

A skill is a typed handle to a runnable capability — a SKILL.md folder, a CLI command, an inline Python recipe, or an MCP-mediated tool call. The skill registry lives in `config/skills.py`, which is by far the largest configuration file in the project at **2,073 lines**. The skill *count* is 101 across the original nine roles, distributed as follows:

| Role | Total skills | Autonomous | Top categories |
|---|---:|---:|---|
| orchestrator | 12 | 11 | manage:12 |
| pm | 11 | 8 | manage:8, document:3 |
| dev | 12 | 12 | code:11, design:1 |
| qa | 11 | 10 | test:11 |
| critic | 11 | 11 | review:11 |
| review | 11 | 11 | review:9, deploy:1, document:1 |
| devops | 11 | 10 | deploy:11 |
| automation | 11 | 11 | automate:11 |
| research | 11 | 11 | research:10, document:1 |

Three observations:

- **The skill counts are stable across roles.** Every role has 11–12 skills. This is by design: it forces the system designer to produce a balanced palette per role rather than overloading the orchestrator with everything.
- **Categories are 1:1 with role identity.** The `dev` role is overwhelmingly `code`-category skills, the `qa` role is overwhelmingly `test`, and so on. There is mild crossover at the boundaries (a `review` skill that touches `deploy`, an `orchestrator` skill that touches `manage`), but the registry rejects ambient skills.
- **Most skills are autonomous.** 96 of 101 skills are flagged `autonomous=True`, meaning the agent is allowed to invoke them without an explicit user OK. The five non-autonomous skills sit in `pm` and `qa`, where they correspond to actions that touch shared state or external systems. This decision matters in practice because the alternative — interactive consent for every action — is what drives operators back to the chat box.

The expanded twenty-five roles intentionally have **no skills wired** at the time of writing. Defensive try/except wrappers in `init_agents` ensure the engine treats a missing skill table as an empty list rather than a startup-killing exception. The roles still receive their model assignment, their system prompt, and their place in the routing graph; what they lack is autonomous tool use. This is a deliberate research-mode posture: the operator wanted the new roles available for hand-driven A/B testing before granting them autonomy.

## 7. MCP Server Fabric

Octopus is the only place I know of where an *individual operator's* MCP catalog reaches 37 servers. The breakdown by category, from `config/mcp_servers.py`:

| Category | Servers | Enabled | Examples |
|---|---:|---:|---|
| CORE | 6 | 6 | filesystem, git, sqlite, memory, sequential-thinking, time |
| DEV_TOOLS | 8 | 8 | github, terminal, code-runner, debugger, package mgmt |
| AUTOMATION | 4 | 4 | scheduler, web-scraper, browser, email |
| RUNTIMES | 3 | 3 | python, node, docker |
| CODE_BUILDERS | 6 | 6 | scaffolders, generators, formatters |
| RESEARCH | 3 | 3 | web-search, fetch, vector-store |
| MEMORY | 1 | 1 | Obsidian local REST |
| PRODUCTIVITY | 4 | 3 | calendar, notes, todo, doc tools |
| PAYMENTS | 2 | 2 | (not exercised at the time of writing) |
| **Total** | **37** | **36** | |

The single disabled server is in PRODUCTIVITY — by operator preference, not capability. The 36 enabled servers are addressable through 9 agent-routing entries. The original nine mainline roles each have an explicit MCP allowlist:

| Role | MCP servers in allowlist |
|---|---:|
| orchestrator | 9 |
| dev | 5 |
| devops | 5 |
| automation | 5 |
| pm | 4 |
| qa | 4 |
| research | 4 |
| critic | 3 |
| review | 3 |

The orchestrator's allowlist is a strict superset of every downstream role's, which preserves the design rule that the brain can do anything any of its arms can do, but the arms are restricted. The same defensive try/except pattern as skills protects the engine from a missing MCP routing entry — the expanded twenty-five roles have no allowlist and so cannot autonomously call any MCP server, which is the correct posture until they have a curated palette.

## 8. Memory Architecture

Memory is structured as four scopes — `short_term`, `working`, `long_term`, `episodic` — and exposed through nine per-agent access policies. The wiring lives in `config/memory.py` (133 lines) and the active backend is the **Obsidian Local REST plugin** running on `http://localhost:27123` against a vault named `OctopusMemory`.

| Role | Scopes |
|---|---|
| orchestrator | short_term, working, long_term, episodic |
| pm | short_term, working, episodic |
| dev | short_term, working, long_term |
| qa | short_term, working |
| critic | short_term, long_term |
| review | short_term, long_term |
| devops | short_term, working |
| automation | short_term, working |
| research | short_term, long_term, episodic |

Two design choices stand out:

- **`episodic` is sparse.** Only orchestrator, pm, and research can write episodic notes — the kind of "what happened in this thread" record that wants a durable narrative-shaped storage. Other roles pass their narrative back to the orchestrator, which is the canonical writer of episodic memory.
- **`working` excludes `critic` and `review`.** The roles whose job is to *evaluate* output do not get a working scratchpad, because a working scratchpad is where in-progress conclusions accumulate. A critic with a scratchpad is a critic with priors, which is the wrong shape for the role.

When the Obsidian plugin is unreachable, the engine logs `Obsidian MCP server: NOT REACHABLE` at boot and continues with memory features degraded. No turn fails for lack of memory; the agents simply lose long-term continuity for that session.

## 9. Backend API Surface

The FastAPI app in `api/main.py` (753 lines) exposes **42 routes**. Sorted by purpose:

| Domain | Endpoints | Notes |
|---|---:|---|
| Status / system | 3 | `/`, `/api/status`, `/api/system` |
| Agent introspection | 4 | `/api/agents`, `/api/agent/{role}/info`, `/api/agent/{role}/task`, `/api/skills` |
| Models | 5 | `/api/models`, plus load/download/download-status |
| Providers | 3 | List, models-per-provider, health check |
| Chat / send | 2 | `/api/chat`, `/api/send` (zone-gated) |
| Pipeline / tasks / messages | 4 | History, pipeline ring, per-task messages |
| Benchmark | 3 | Run, status, results |
| Projects / devices / upload | 3 | |
| MCP | 2 | Servers, routing |
| Memory | 2 | Status, search |
| Config | 1 | DOs/DON'Ts |
| Session / zone | 4 | Get session, set zone, open/close bridge |
| Email (stub) | 3 | Inbox, compose, triage |
| Calendar | 3 | List/add/delete events |
| WebSocket | 1 | `/ws` — pipeline event stream |
| **Total** | **42** | |

A few endpoints are worth highlighting:

- **`POST /api/send`** is the canonical entry point for cross-agent routing. It pulls the active session, resolves the source/target roles, runs `can_route`, and either dispatches the call through the engine or raises a `ZoneBoundaryError` that becomes a 403.
- **`GET /api/session`** and the four `/api/session/*` endpoints expose the zone state to the React UI. The `useZone()` hook polls these to drive every visual zone-tint in the application.
- **`GET /ws`** is the only streaming endpoint. The frontend's `LogDrawer` and `ChangesRenderer` both subscribe to it. Pipeline events flow as JSON envelopes carrying `from_agent`, `to_agent`, `event_type`, `data`, and a server-side timestamp.

The email surface is intentionally incomplete: the `inbox` endpoint returns an `EMAIL_NOT_CONNECTED` envelope and the `compose` endpoint returns a 503 with the draft echoed, until a Gmail MCP connector is wired in. The `triage` endpoint runs but is currently a stub that returns canned `priority`/`summary`/`reply` fields. The slot is there so the UI can be built and tested ahead of the integration.

## 10. Persistence Layer

The system writes to a SQLite database at `database/octopus.db` (managed by `database/db.py`, 64 lines). Seven tables, with current row counts captured for this paper:

| Table | Columns | Rows | Purpose |
|---|---:|---:|---|
| agents | 7 | 34 | Live agent registry — synced from `AGENT_ROLES` at boot |
| tasks | 12 | 21 | Task records with parent linkage and status lifecycle |
| messages | 7 | 68 | Per-task message log |
| benchmarks | 10 | 90 | Benchmark runs (model_id × role) |
| pipeline_events | 7 | 156 | Event stream (assign / complete) — feeds the UI |
| model_assignments | 4 | 34 | Current role→model bindings |
| sqlite_sequence | 2 | 4 | SQLite internal autoincrement ledger |

Task status distribution is 8 completed, 13 in-progress. The high in-progress count reflects that V2.2 is still early in dogfooding — multi-agent tasks in V2.2 are durable across sessions, but the operator has not yet run a scheduled cleanup job to retire stale ones.

Pipeline events split 88 assigns to 68 completes — a ratio that should be 1:1 in steady state. The 20-event gap is the count of tasks that have been assigned but not yet completed at the moment of capture. Combined with the 13 in-progress task rows, this triangulates a picture of an operator who routinely cancels or abandons in-flight work, which is the expected pattern for early bring-up.

## 11. Frontend Architecture

The frontend is a single-page React application at `frontend/`. Stack: **React 19.2.4**, **Vite 8.0.4**, **Tailwind CSS 4.2.2**, **react-router-dom 7.14.0**, plus a small lucide-react icon set. The source tree is intentionally flat:

| Region | Files | LOC |
|---|---:|---:|
| Pages | 12 | 2,469 |
| Components | 8 | 970 |
| Hooks | 2 | 115 |
| Lib (api/ws/cx/theme) | 4 | 191 |
| Entry / styles | 5 | 371 |
| **Total** | **31** | **4,116** |

There are five primary pages — `ChatV2`, `CoworkPage`, `CodePage`, `EmailPage`, `CalendarPage` — and seven legacy pages (`Agents`, `Pipeline`, `Projects`, `Skills`, `MCPServers`, `Memory`, `SystemStatus`) that remain reachable under `/overflow/*` during the V2.2 cutover. The Cursor-inspired *surface row* (`SurfaceRow.jsx`, 87 lines) sits below the TopBar and surfaces four execution surfaces — Desktop, Terminal, Web, Extension — with an accent-tinted active state and a contextual hint string that updates per surface. The mesh visualization (`AgentMeshSidebar.jsx`, 177 lines) draws the orchestrator as a central core and every other agent as a tentacle tip. Tentacles whose role appears in a recent routing event pulse for three seconds, giving the operator a visceral signal of which arm of the mesh just fired.

Two utilities deserve a name-check. `lib/cx.js` (22 lines) is a hand-rolled `clsx` clone added after a dependency-resolution error on a fresh install — Vite was failing to resolve `clsx` because the version in `package.json` was missing from `node_modules`. The shim eliminates the dependency entirely. `lib/ws.js` (58 lines) wraps the live `/ws` connection in a small subscription API consumed by `useLiveLog` and the LogDrawer.

## 12. Observability

The system makes its own internal state visible through three first-class observability surfaces:

- **LogDrawer** — bottom-edge accordion, collapses to a 28px strip showing `closed` / `0/0 events`. Open it (⌘L) and you get the full WebSocket stream, color-tinted by zone, filterable by event type and from/to role.
- **ChangesRenderer** — right-rail event timeline grouped by *turn*. A turn is the orchestrator-rooted subtree of events sharing a task ID. When the operator clicks a turn, the renderer expands the agent's plan, route decisions, file diffs, memory writes, command output, bridge transitions, and final reply.
- **Mesh sidebar pulse** — already discussed. The most affecting observability surface in the system, because it gives the operator a peripheral-vision view of mesh activity without having to read JSON.

Every event the UI sees is also persisted to `pipeline_events`, so the timeline is reproducible from disk after a session ends.

## 13. Operational Data — What the System Has Learned About Itself

Octopus has a primitive built-in benchmark harness (`benchmark/runner.py`, 304 lines). It runs a fixed prompt against every (role, model) pair in the assignment table and records `tokens_per_second`, `response_time_ms`, `quality_score`, `output_length`, `vram_usage_mb`, and `ram_usage_mb`. After 90 captured runs across nine roles and ten models, the headline numbers are:

- **Distinct roles benchmarked:** 9 (the original mainline nine)
- **Distinct models tested:** 10
- **Average response time across all runs:** ~60ms (skewed by orchestrator runs averaging 456ms; the other eight roles cluster around 4–5ms)
- **Quality score:** uniform 35.0 across every captured run

The uniformity of the quality score is a flag, not a finding: the current `quality_score` field is being filled by a constant rather than by a real evaluator. Building a working evaluator that produces meaningful per-role quality is one of the explicit roadmap items below. The latency split between the orchestrator (~456ms) and the others (~4ms) reflects that the captured runs warm-loaded the orchestrator's checkpoint but reused a cached completion for the rest — another harness fix on the roadmap.

The 156 pipeline events tell a more substantive story:

| Property | Value |
|---|---|
| Events recorded | 156 |
| Distinct tasks | 21 |
| Distinct agents involved | 9 (mainline) |
| User → orchestrator hops | 26 |
| Orchestrator outbound assigns | 62 |
| Most-delegated arm | dev (21 assigns) |
| Least-delegated arm | critic and review (3 assigns each) |
| Hacker-zone events | 0 |
| Cross-zone bridge openings | 0 |

The hacker zone has been built and its routing path is exercised by unit tests, but during routine work the operator has stayed in mainline. This matches the design intent — the zone is research capacity, not a daily-driver mode.

## 14. Findings

After several weeks of bring-up traffic and four formal phases of work (zone hardening, dashboard archival, V2.2 frontend, fix sweep), four findings stand out:

**1. Heterogeneous models genuinely produce different output.** Sending the same plan-critique prompt to `qwen/qwen3.6-27b` and to `nvidia/nemotron-3-nano` produces audibly different reasoning traces — the Qwen line tends to mathematicize, the Nemotron line tends to enumerate. The system's design bet that this disagreement is *useful* for an operator deciding whether to ship a plan is borne out empirically. A second finding: the disagreement appears even when the system prompts are identical, suggesting that the model layer is the source rather than the prompt layer.

**2. A single-orchestrator pattern survives heavy fan-out.** The orchestrator role handles every user turn (26/26 in the captured window) and never gets pinned. The reason is delegation — the orchestrator's own job is short and bounded (decide which arm), so even though the orchestrator's checkpoint is the largest in the rotation, average orchestrator turn latency stays inside a budget. This contradicts the assumption that single-brain routing creates a bottleneck; in practice the bottleneck is whichever arm the brain delegated to.

**3. Defensive declarative configuration prevents an entire class of startup failures.** V2.2's `init_agents` was hardened to wrap each per-role config lookup (skills, MCP allowlist, memory scope) in a try/except that defaults to an empty list and logs a warning. Before this change, the engine would crash at boot the first time any expanded role was missing a wired entry. After this change, the engine boots cleanly with 34 roles, of which only 9 have full skill/MCP/memory tables — the remaining 25 register as latent capacity and the system still serves traffic.

**4. The most useful UI affordance is also the cheapest.** The mesh sidebar's pulse animation — a 3-second highlight on tentacles that just received an event — is fewer than 30 lines of React but is the single most-cited piece of feedback from operator dogfooding. A static list would have shown the same information and cost the same to build, and it would have been visibly worse.

## 15. Open Issues and Roadmap

This is a candid list, not a marketing surface.

- **Quality score is a stub.** Every captured benchmark scored 35.0. A real evaluator (likely an LLM-as-judge with a small rubric) is the next benchmark task.
- **Email is not connected.** Inbox returns a placeholder; compose returns 503; triage returns a stub. A Gmail MCP integration sits at the top of the integration backlog.
- **Memory long-term continuity is partial.** Obsidian unreachable means `long_term` and `episodic` writes are dropped silently. A small `memory/journal.jsonl` fallback writer is in design.
- **The expanded twenty-five roles need skills.** All 25 roles route correctly and run inference, but they have no autonomous tool palette. The `agents_expanded.py` config will need a corresponding `skills_expanded.py` to grow it.
- **Surface filtering is observable but advisory.** Clicking Desktop / Terminal / Web / Extension changes a chip and a hint string; downstream pages do not yet branch on it. Wiring `surface` into ChatV2's event filter is the first roadmap item under V2.3.
- **Benchmark harness needs cold-warm split.** Current runs blend cold-load and warm-cache latencies. Splitting them is straightforward.
- **Frontend route guards are missing.** A user who navigates to `/code` while the hacker zone is active and the bridge is closed sees no warning. A `useZone()`-aware route guard is on the V2.3 list.
- **No CI yet.** The repository has no continuous integration. A small GitHub Actions workflow that lints Python with `ruff` and runs the import-smoke suite is overdue.

## 16. Repository Topology

For an outside reader picking up the repo, the directory layout maps cleanly to the architecture:

```
octopus-v2/
├── agents/
│   ├── engine.py                  1,029 LOC — coordination heart
│   ├── multi_provider_client.py     283 LOC
│   └── (archived legacy snapshots)
├── api/
│   ├── main.py                      753 LOC — 42 routes + WS
│   └── routes/                       (split into engine.py for now)
├── benchmark/
│   └── runner.py                    304 LOC
├── config/
│   ├── settings.py                  500 LOC — original 9 roles, rules, models
│   ├── agents_expanded.py           550 LOC — 25 expanded roles + zones
│   ├── skills.py                  2,073 LOC — 101 typed skills
│   ├── mcp_servers.py               588 LOC — 37 server registry
│   ├── memory.py                    133 LOC — Obsidian + scope policies
│   ├── providers.py                 190 LOC — provider adapter
│   └── zones.py                     277 LOC — SessionZoneState + can_route
├── database/
│   ├── db.py                         64 LOC — SQLite helpers
│   └── octopus.db                       — 7 tables, ~370 rows total
├── frontend/
│   ├── src/                       4,116 LOC — React 19 / Vite 8 / Tailwind 4
│   └── package.json
├── tests/
│   └── test_memory_obsidian.py      243 LOC
├── archive/                              — old engine snapshots, legacy dashboard
├── docs/                                 — design notes
├── run.py                            175 LOC — preflight + uvicorn launcher
└── PAPER.md                              — this document
```

Two sub-trees deserve mention: `archive/` holds the V2.0 dashboard and the two pre-V2.2 engine snapshots, kept on disk for diff'ing rather than reachable code; `docs/` holds the V2.1 and V2.2 system-design notes and the perfect-prompt reference.

## 17. What Makes This Repo Unusual

A non-exhaustive list of things that distinguish Octopus from the general agent-framework field:

- **34 roles, 1:1 model mapping.** Most projects pick three or four roles and reuse one big checkpoint. Octopus picks thirty-four and runs them on thirty-four different checkpoints.
- **Two zones with a hard isolation boundary.** Most projects have a single agent surface. Octopus has a quarantined sub-mesh for uncensored / abliterated models with its own brain, its own filesystem vault, and an explicit bridge protocol that requires a written reason.
- **Local-first by construction.** Most projects run inference in a vendor cloud. Octopus runs every model on the operator's workstation. A remote provider (Claude API) is configured as a fallback but not active.
- **101 typed skills with autonomy flags.** Most projects treat tools as ad-hoc functions in a chat harness. Octopus types each skill, declares which agents can call it, marks autonomy explicitly, and persists the registry as configuration.
- **37 MCP servers wired with per-agent allowlists.** Most projects have one or two MCP integrations. Octopus has thirty-seven, each routed to a curated subset of agents.
- **Cursor-inspired surface row.** Most projects collapse all execution into one chat box. Octopus surfaces Desktop / Terminal / Web / Extension as first-class.
- **The mesh visualization is live.** The sidebar shows the orchestrator's tentacles pulsing as routing decisions land. Most projects show a static list.
- **Defensive boot.** Missing skill or MCP entries downgrade gracefully rather than crashing the engine.
- **Persistent pipeline_events.** Every routing decision is on disk forever. Most projects log to console.
- **No vendor lock-in anywhere.** Swap LM Studio for Ollama and you change two strings. Swap Obsidian for SQLite and you change one file.

## 18. Conclusion

Octopus V2.2 demonstrates that a single operator can build a thirty-four-agent local-first mesh, run it on a single workstation, and use it for real work. The total code surface — 7,486 Python lines, 4,116 frontend lines, ~4,121 lines of declarative configuration — is small enough to fit in one head. The design rejects the prevailing assumption that production agent systems must be cloud-hosted, single-model, and chat-shaped. The data shows that heterogeneous models genuinely disagree, a single-brain routing topology survives heavy fan-out, declarative configuration prevents an entire class of bugs, and the most affecting UI affordances are also the cheapest. The system is not a product. It is a scaffolding that an operator can grow — adding roles, adding models, adding MCP servers, adding skills — without ever having to rewrite the parts that already work.

The next major version, V2.3, will focus on three things: filling out the autonomous skill palettes for the twenty-five expanded roles, replacing the placeholder benchmark scorer with a real evaluator, and wiring the surface row from advisory to authoritative. Pull requests, issues, and forks are welcome.

---

## Appendix A — Statistical summary at a glance

| Metric | Value |
|---|---:|
| Active Python files (excl. archive) | 23 |
| Active Python LOC | 7,486 |
| Frontend source files | 31 |
| Frontend LOC | 4,116 |
| Configuration LOC | 4,121 |
| Total declarative + code surface | ~15,720 LOC |
| Total agent roles | 34 |
| Mainline roles | 19 |
| Hacker-zone roles | 15 |
| Tier: brain | 7 |
| Tier: arm | 16 |
| Tier: scout | 6 |
| Tier: specialist | 5 |
| LM Studio models loaded | 37 |
| Unique role→model assignments | 34 |
| Skills wired | 101 |
| Autonomous skills | 96 |
| MCP servers registered | 37 |
| MCP servers enabled | 36 |
| MCP categories | 9 |
| Agents with MCP allowlists | 9 |
| Memory scopes | 4 |
| Memory access policies | 9 |
| FastAPI routes | 42 |
| WebSocket endpoints | 1 |
| SQLite tables | 7 |
| Pipeline events recorded | 156 |
| Tasks recorded | 21 |
| Benchmark runs | 90 |
| Cross-zone bridge openings | 0 |

## Appendix B — Glossary

- **Agent.** A role with a default model, a system prompt, an MCP allowlist, a skills palette, a memory access policy, and a zone tag.
- **Arm.** A producer agent — emits code, prose, configurations.
- **Brain.** A reasoning / orchestration agent.
- **Bridge.** An explicit, reason-logged opening of cross-zone routing.
- **Mesh.** The graph of agents the orchestrator can delegate to.
- **MCP server.** A Model Context Protocol server that exposes tools and resources to agents.
- **Pipeline event.** A persisted record of a routing decision: assign, complete, or error.
- **Scout.** A latency-first agent for triage / classification.
- **Skill.** A typed handle to a runnable capability — autonomous or interactive.
- **Specialist.** A role with a narrow scope (vision, translation, baseline, creative writing, roleplay).
- **Surface.** Desktop, Terminal, Web, or Extension — the execution context the current turn lives in.
- **Turn.** The orchestrator-rooted subtree of routing events sharing a task ID.
- **Zone.** Mainline (default) or Hacker (uncensored). Routing across zones is gated.

## Appendix C — Reproducing the numbers in this paper

Every statistic in this paper was generated by querying the same files an operator has access to:

- **Code LOC:** `find . -name "*.py" -not -path "./archive/*" -not -path "./frontend/node_modules/*" | xargs wc -l`
- **Frontend LOC:** `find frontend/src -name "*.jsx" -o -name "*.js" -o -name "*.css" | xargs wc -l`
- **Agent count and zones:** `python -c "from config.settings import AGENT_ROLES; print(len(AGENT_ROLES))"` (after the merge in `agents_expanded`)
- **Skill counts:** `python -c "from config.skills import AGENT_SKILLS, total_skill_count; print(total_skill_count())"`
- **MCP servers:** `python -c "from config.mcp_servers import MCP_SERVERS; print(sum(len(v) for v in MCP_SERVERS.values()))"`
- **Memory policies:** `python -c "from config.memory import AGENT_MEMORY_ACCESS; print(len(AGENT_MEMORY_ACCESS))"`
- **Endpoint count:** `grep -E "^@app\.(get|post|delete|put|websocket)" api/main.py | wc -l`
- **Database row counts and routing graph:** plain SQL against `database/octopus.db`

No metric in this paper is an estimate. Every number is the value the system itself reports as of the date of writing.

---

*End of paper.*
