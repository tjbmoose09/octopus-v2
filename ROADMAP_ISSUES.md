# V2.3 Roadmap — Issue Templates

Each section below is a complete GitHub issue, ready to paste. Open `https://github.com/<owner>/<repo>/issues/new` for each, copy the title into the title field, and the body block into the description. Suggested labels are noted.

To bulk-create them with the `gh` CLI:

```powershell
gh issue create --title "..." --body-file ./issue1.md --label "good first issue,V2.3,benchmark"
```

(Split each block below into its own file first; this single document is for review and copy-paste.)

---

## Issue 1 — Replace stub benchmark scorer with real evaluator

**Suggested labels:** `V2.3` `benchmark` `help wanted` `good first issue`

### Title
```
Replace stub benchmark quality_score with LLM-as-judge evaluator
```

### Body

**The bug.** Every benchmark run currently records `quality_score = 35.0` regardless of model output. There is no actual evaluation happening — the field is being filled by a constant. After 90 captured runs across 9 roles and 10 models, the data is uniformly 35.0, which means the benchmark table provides no signal for model-fitness questions.

**What good looks like.** A working evaluator that:

1. Takes the per-role benchmark prompt (from `AGENT_ROLES[role].benchmark_prompt`) and the model's output.
2. Runs an LLM-as-judge call against a separate model (the orchestrator's checkpoint, or a remote Claude API call if configured) with a small rubric covering: correctness of structure, on-task adherence, refusal-rate, and presence of role-specific markers (e.g. a `dev` answer should contain runnable code; a `research` answer should contain citations).
3. Returns a score in `[0, 100]` with three sub-scores so the operator can see *why* a run scored well.
4. Persists sub-scores to `benchmarks` (schema migration: add `quality_breakdown JSON`).

**Files involved.** `benchmark/runner.py`, `database/db.py` (schema), `config/settings.py` (rubric).

**Acceptance criteria.**
- A new run produces a non-uniform `quality_score` across (role, model) pairs.
- At least three pairs score noticeably differently (e.g., `dev` × `phi4-nvidia-coder` should outscore `dev` × `liquid/lfm2.5-1.2b` by > 10 points).
- The schema migration is reversible.
- Unit tests in `tests/test_benchmark_evaluator.py` mock the judge call and verify rubric application.

**Difficulty.** Medium. The judge prompt design is the hard part; the wiring is straightforward.

---

## Issue 2 — Wire skill palettes for the 10 expanded mainline roles

**Suggested labels:** `V2.3` `skills` `help wanted`

### Title
```
Add skills to strategist / heavy_reasoning / heavy_dev / vision / scout / micro_scout / edge_agent / nemotron_heavy / translator / legacy_baseline
```

### Body

**The gap.** `init_agents` defensively defaults missing skill tables to empty lists, so the 10 expanded mainline roles register without crashing. But they have no autonomous tool palette — they can run inference and emit text, but they cannot call MCP tools or invoke skills.

**What good looks like.** `config/skills.py` grows a per-role skill list for each of the 10 expanded roles, sized 8–12 skills each (matching the existing 11–12-skill cadence on the original nine roles). Categories should align with the role's purpose:

| Role | Suggested categories |
|---|---|
| strategist | review, manage |
| heavy_reasoning | research, manage |
| heavy_dev | code, design |
| vision | research, document |
| scout | research, automate |
| micro_scout | automate |
| edge_agent | automate, document |
| nemotron_heavy | research, review |
| translator | document |
| legacy_baseline | (intentionally empty — benchmark-only) |

**Acceptance criteria.**
- Each role except `legacy_baseline` has ≥ 8 skills wired.
- `total_skill_count()` increases from 101 to ≥ 180.
- `skill_summary()` returns non-empty results for every expanded role.
- Skill IDs follow the existing snake_case convention.
- Each new skill declares `runtime`, `category`, `mcp_dependencies`, and `autonomous` fields.

**Difficulty.** Medium. The work is mostly taxonomy — deciding which skills each role *should* be able to invoke autonomously.

---

## Issue 3 — Wire skill palettes for the 15 hacker-zone roles

**Suggested labels:** `V2.3` `skills` `hacker-zone` `help wanted`

### Title
```
Add skills to the 15 hacker-zone roles (hz_orchestrator, hz_*_dev, hz_writer, etc.)
```

### Body

**The gap.** Same as issue #2, but for the hacker-zone roles. They route correctly within the zone but have no autonomous tool palette.

**What good looks like.** A new file `config/skills_hz.py` that mirrors the structure of `config/skills.py`, with 8–12 skills per role for the 15 HZ roles. Crucially:

- HZ skills cannot reference MCP servers that mainline skills depend on if those servers write to the shared filesystem. The zone boundary requires that HZ writes go to `vault/hacker_zone/` not the main `vault/`.
- HZ skills should explicitly declare a `zone="hacker_zone"` field.
- The `hz_orchestrator` role gets the largest palette and is the only HZ role allowed to delegate within the zone.

**Acceptance criteria.**
- 15 roles × ≥ 8 skills each = ≥ 120 new skills.
- Every skill declares `zone="hacker_zone"`.
- `get_skills_for_agent("hz_dev_moe")` returns a non-empty list.
- `init_agents` startup logs no warnings for HZ roles.
- A new test `tests/test_zone_skill_isolation.py` confirms a mainline agent cannot invoke an HZ skill and vice versa.

**Difficulty.** Medium-hard. Requires careful thinking about which tools should be reachable from inside the zone — many MCP servers must be excluded.

---

## Issue 4 — Wire SurfaceRow from advisory to authoritative

**Suggested labels:** `V2.3` `frontend` `routing`

### Title
```
SurfaceRow should actually filter routing — currently advisory only
```

### Body

**The bug.** Clicking Desktop / Terminal / Web / Extension in the SurfaceRow updates the right-side chip and hint string, but downstream pages (ChatV2, CoworkPage, CodePage) ignore the value. The `surface` prop is passed in but never read.

**What good looks like.**

1. ChatV2 reads `surface` and filters the ChangesRenderer event stream to only events tagged with that surface.
2. The composer's placeholder text changes per surface (e.g., "/ commands · @ files" for Desktop, "$ run · | pipe" for Terminal).
3. The orchestrator's outgoing routing call carries the surface as a hint to the engine; the engine adds it to `pipeline_events.data` so the filter has something to filter on.
4. A small badge above the composer shows the active surface and a link to clear it back to "all".

**Backend changes.**
- `engine.send_to_agent` accepts an optional `surface` arg and stamps it on the event.
- `pipeline_events.data` JSON gains a `surface` key.
- The `/api/send` endpoint accepts `surface` in the request body.

**Frontend changes.**
- `lib/api.js` `chat()` and `send()` pass surface.
- `pages/ChatV2.jsx` filters by surface.
- `components/ChangesRenderer.jsx` reads the filter prop.

**Acceptance criteria.**
- Toggling SurfaceRow visibly changes the composer hint text.
- Toggling SurfaceRow filters ChangesRenderer to events from that surface.
- Routing to non-default surfaces is recorded in `pipeline_events`.

**Difficulty.** Medium. End-to-end change touching backend, schema, frontend.

---

## Issue 5 — Connect Gmail MCP and remove email stubs

**Suggested labels:** `V2.3` `email` `mcp` `integration`

### Title
```
Wire Gmail MCP server, remove email endpoint stubs
```

### Body

**The gap.** EmailPage renders correctly but the backend returns canned data:
- `GET /api/email/inbox` → `EMAIL_NOT_CONNECTED` envelope
- `POST /api/email/compose` → 503 with the draft echoed
- `POST /api/email/triage` → stub priority / summary / reply

**What good looks like.** A working Gmail MCP server (use the existing `@modelcontextprotocol/server-gmail` or equivalent) is added to `config/mcp_servers.py` under PRODUCTIVITY, routed to the `automation` and `pm` agents. The three endpoints above are rewritten to call into the engine, which delegates to those agents.

**Acceptance criteria.**
- Inbox endpoint returns real Gmail threads (subject + snippet + sender).
- Compose endpoint creates a Gmail draft (does not send — explicit user action required).
- Triage endpoint actually calls the orchestrator and returns a real priority classification (P0–P3) with model-generated summary and draft reply.
- OAuth flow for Gmail MCP is documented in `docs/`.
- A failing Gmail connection returns a structured 503 with retry guidance, not a 502.

**Difficulty.** Medium. The MCP wiring is straightforward; the OAuth flow setup is the slow part.

---

## Issue 6 — Add Obsidian fallback for offline operation

**Suggested labels:** `V2.3` `memory` `resilience`

### Title
```
Add memory/journal.jsonl fallback when Obsidian Local REST is unreachable
```

### Body

**The gap.** When Obsidian Local REST is down (plugin off, vault closed), `long_term` and `episodic` memory writes are dropped silently. The engine logs `Obsidian MCP server: NOT REACHABLE` at boot and continues, but no fallback persistence captures what would have been written.

**What good looks like.** A jsonl-backed fallback writer that captures all memory writes when Obsidian is unreachable. The format:

```
memory/journal.jsonl
{"ts": "2026-04-23T12:00:00Z", "agent": "orchestrator", "scope": "episodic", "content": "...", "task_id": "..."}
{"ts": "2026-04-23T12:00:01Z", "agent": "research", "scope": "long_term", "content": "...", "task_id": "..."}
```

When Obsidian comes back, a small `tools/replay_journal.py` script reads the jsonl and writes each entry into the vault under the appropriate scope folder.

**Acceptance criteria.**
- With Obsidian off, a memory write produces a new line in `memory/journal.jsonl`.
- With Obsidian on, writes go to the vault as before.
- The replay script is idempotent (re-running it doesn't duplicate notes).
- `tests/test_memory_fallback.py` covers both paths.

**Difficulty.** Easy-medium. Self-contained.

---

## Issue 7 — Cold/warm split in benchmark harness

**Suggested labels:** `V2.3` `benchmark`

### Title
```
benchmark/runner.py should record cold-load and warm-cache latencies separately
```

### Body

**The bug.** Captured runs blend two very different latency regimes:
- **Cold load:** the model is being lifted from disk into VRAM. First-call latencies of ~500ms.
- **Warm cache:** the model is resident; subsequent calls return in 4–5ms (which means LM Studio is returning a cached completion, not actually inferring).

The current 90-row dataset has the orchestrator at ~456ms average and the other 8 roles at ~4ms average — neither of which is the steady-state inference latency for any of these models.

**What good looks like.**

1. The runner explicitly cold-loads each model (call `lm_client.load_model(model)`), records `cold_latency_ms`, then issues 5 warm calls and records `warm_latency_ms` (median of the 5).
2. Schema gains `cold_latency_ms` and `warm_latency_ms` columns alongside the existing `response_time_ms`.
3. The benchmark UI page shows both numbers side-by-side.

**Acceptance criteria.**
- Schema migration adds two columns; reversible.
- New benchmark runs populate both.
- The orchestrator role has cold_latency_ms ~ 500ms and warm_latency_ms ~ token-rate-bound, not 4ms.
- Old rows survive the migration with NULL in the new columns.

**Difficulty.** Easy.

---

## Issue 8 — Zone-aware route guard on the frontend

**Suggested labels:** `V2.3` `frontend` `safety`

### Title
```
Routes /chat /cowork /code should warn when zone is hacker_zone and bridge is closed
```

### Body

**The gap.** A user who has the hacker zone active but the bridge closed can still navigate to `/chat`, `/cowork`, or `/code` and try to send a message. The send fails with a 403 from the API (correct), but the frontend doesn't *anticipate* the failure — it just shows the 403 in the chat as an error.

**What good looks like.** A `<ZoneGuard>` wrapper component that wraps mainline-only routes. When mounted with `hacker_zone_active=true` and `bridge_open=false`, it renders a banner explaining the routing constraint and a "switch to mainline" button (which calls `POST /api/session/zone` with `mainline`).

**Acceptance criteria.**
- Navigating to `/chat` while in hacker zone with bridge closed shows the banner instead of the chat composer.
- The banner has a single primary action that returns the user to mainline.
- The banner does not appear when in hacker zone with bridge open.
- The hacker-zone-only routes (none yet, but `/hz/*` planned for V2.4) are unaffected.

**Difficulty.** Easy.

---

## Issue 9 — Add minimal CI

**Suggested labels:** `V2.3` `ci` `infra` `good first issue`

### Title
```
Add GitHub Actions workflow for lint + import-smoke + frontend build
```

### Body

**The gap.** No CI. Every commit relies on the operator to remember to run lint and the import-smoke locally.

**What good looks like.** A single `.github/workflows/ci.yml` that runs on every push and PR:

1. **Backend job** — Python 3.12, install requirements, `ruff check .`, `python -c "import api.main"` as smoke test, run `pytest tests/`.
2. **Frontend job** — Node 20, `npm ci`, `npm run lint`, `npm run build`.

Both jobs fail the PR if they fail.

**Acceptance criteria.**
- `.github/workflows/ci.yml` exists and runs on push.
- A trivial PR (e.g., README typo) shows green check marks.
- A PR introducing a known import error shows red.
- Build artifacts are not uploaded (we don't need them yet).

**Difficulty.** Easy.

---

## Issue 10 — Provider adapters beyond LM Studio + Claude

**Suggested labels:** `V2.3` `providers` `help wanted`

### Title
```
Add Ollama and llama.cpp providers to multi_provider_client
```

### Body

**The gap.** `agents/multi_provider_client.py` currently supports `lm_studio` (active) and `claude_api` (key-gated). LM Studio is great but not the only local-inference option. Adding Ollama and llama.cpp expands the operator's choice without breaking anything.

**What good looks like.** Two new provider classes that conform to the existing provider interface (`list_models`, `chat`, `health`). Both register themselves in `config/providers.py`. Operators can then declare `OLLAMA_BASE` or `LLAMACPP_BASE` in `.env`, set the per-role provider in `DEFAULT_AGENT_PROVIDERS`, and the engine routes accordingly.

**Acceptance criteria.**
- `config/providers.py` exposes `ollama` and `llama_cpp` provider entries.
- `multi_provider_client` can route a chat call to either.
- `.env.example` documents the two new variables.
- A new test `tests/test_providers_ollama.py` mocks the Ollama HTTP API and verifies a chat call.
- Existing LM Studio flow is unchanged.

**Difficulty.** Medium.

---

## Bulk-creation script (optional)

If you'd rather create all 10 in one shot:

```powershell
# Save each issue body to a separate file first.
# Then:
gh issue create --title "Replace stub benchmark quality_score..."  --body-file issues/01.md  --label "V2.3,benchmark,good first issue,help wanted"
gh issue create --title "Add skills to strategist / heavy_reasoning..." --body-file issues/02.md --label "V2.3,skills,help wanted"
gh issue create --title "Add skills to the 15 hacker-zone roles..." --body-file issues/03.md --label "V2.3,skills,hacker-zone,help wanted"
gh issue create --title "SurfaceRow should actually filter routing..." --body-file issues/04.md --label "V2.3,frontend,routing"
gh issue create --title "Wire Gmail MCP server, remove email endpoint stubs" --body-file issues/05.md --label "V2.3,email,mcp,integration"
gh issue create --title "Add memory/journal.jsonl fallback..." --body-file issues/06.md --label "V2.3,memory,resilience"
gh issue create --title "benchmark/runner.py should record cold-load and warm-cache..." --body-file issues/07.md --label "V2.3,benchmark"
gh issue create --title "Routes /chat /cowork /code should warn when zone is hacker_zone..." --body-file issues/08.md --label "V2.3,frontend,safety"
gh issue create --title "Add GitHub Actions workflow for lint + import-smoke + frontend build" --body-file issues/09.md --label "V2.3,ci,infra,good first issue"
gh issue create --title "Add Ollama and llama.cpp providers to multi_provider_client" --body-file issues/10.md --label "V2.3,providers,help wanted"
```

You'll need to create the labels first (one-time setup):

```powershell
gh label create "V2.3"            --color "5b8cff" --description "Slated for V2.3 release"
gh label create "hacker-zone"     --color "ef4444" --description "Pertains to the quarantined sub-mesh"
gh label create "skills"          --color "10b981" --description "Skill registry / palette work"
gh label create "mcp"             --color "f59e0b" --description "MCP server integration"
gh label create "memory"          --color "9b5cff" --description "Memory layer / Obsidian"
gh label create "providers"       --color "06b6d4" --description "Multi-provider client / adapters"
gh label create "routing"         --color "0ea5e9" --description "Engine routing logic"
gh label create "safety"          --color "be185d" --description "Operational safety / guardrails"
gh label create "infra"           --color "64748b" --description "CI / build / repo infrastructure"
gh label create "resilience"      --color "22d3ee" --description "Graceful degradation / failure handling"
```
