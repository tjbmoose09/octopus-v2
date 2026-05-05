# Releasing Octopus Agents V2.2 — a 34-agent local-first mesh

I'm open-sourcing **Octopus Agents V2.2**, the multi-agent system I've been building solo for the last several months. The full technical paper is in `PAPER.md` in the repository; this post is the short version for people who want to know whether it's worth a read.

## What it is

Octopus is a single-operator agent fabric that runs **34 role-bound LLM agents** entirely on your own workstation. No vendor cloud, no inference round-trip outside your LAN, no API keys required to use the default configuration. Every agent is a different model; the orchestrator delegates across the mesh; every routing decision lands on disk.

## What's in the box

- **34 agents** in a 1:1 mapping to 34 distinct LM Studio models, split across **19 mainline** roles and **15 hacker-zone** roles in their own quarantined sub-mesh.
- **101 typed skills** across 9 active roles, with explicit autonomy flags.
- **37 MCP servers** registered (36 enabled), routed per agent.
- **Four memory scopes** (short_term, working, long_term, episodic) backed by an Obsidian local REST plugin.
- **42-endpoint FastAPI backend** + WebSocket pipeline stream.
- **React 19 / Vite 8 / Tailwind 4 SPA** with a Cursor-inspired surface row, a live octopus-tentacle mesh visualization, a ⌘K command palette, and zone-aware route guards.
- **Hard zone isolation** with an explicit bridge protocol — uncensored / abliterated models cannot reach mainline agents without a written reason logged for audit.
- **Defensive boot** — missing skill or MCP entries downgrade gracefully rather than killing startup.
- **Persistent everything** — every routing event is in SQLite, forever, queryable as a pure data export.

## What makes it unusual

Most agent frameworks pick one big model and three or four roles. Octopus picks 34 roles and runs them on 34 different checkpoints, deliberately, because heterogeneous models genuinely produce different reasoning traces and the disagreement is useful. Most frameworks live in a vendor cloud; Octopus runs every model on the same workstation as the UI. Most frameworks collapse all execution into one chat box; Octopus surfaces Desktop / Terminal / Web / Extension as first-class.

## Numbers, in case you came for numbers

| Metric | Value |
|---|---:|
| Agent roles | 34 |
| LM Studio models loaded | 37 |
| Skills wired | 101 |
| MCP servers | 37 (36 enabled) |
| Memory access policies | 9 |
| FastAPI routes | 42 |
| Active Python LOC | 7,486 |
| Frontend LOC | 4,116 |
| Configuration LOC | 4,121 |
| Total source surface | ~15,720 LOC |
| Pipeline events recorded | 156 |
| Tasks recorded | 21 |
| Benchmark runs | 90 |

All numbers are the system's own self-reported metrics, queried directly from `database/octopus.db` and the merged `AGENT_ROLES` registry. No estimates.

## What's not in the box yet

I'd rather be honest than launch something with hidden caveats. Open issues, all on the V2.3 list:

- The benchmark `quality_score` is a stub — every captured run scored 35.0 because the evaluator hasn't been written yet. Coming.
- Email is wired into the UI but the Gmail MCP connector isn't built yet — `inbox` returns a placeholder, `compose` returns 503.
- The 25 expanded roles route correctly and run inference, but they don't yet have skill or MCP allowlists. They are latent capacity until V2.3 fills them out.
- The surface row (Desktop / Terminal / Web / Extension) is currently observable but advisory — clicking it changes a chip and a hint, but downstream pages don't yet branch on it.
- No CI yet. A small GitHub Actions workflow is overdue.

## Read the paper

The 18-section technical paper in `PAPER.md` covers the full architecture: zone isolation protocol, model resolution, skills system, MCP routing, memory architecture, persistence schema, frontend layout, observability surfaces, captured operating data, findings, and open issues. It runs about 6,000 words and contains no source code — just stats, design rationale, and the empirical record from the system's own database.

## How to run it

```
git clone <repo>
cd octopus-v2
python run.py             # backend on :8080
cd frontend && npm run dev  # frontend on :3000
```

You'll need [LM Studio](https://lmstudio.ai/) running locally on `:1234` with at least the models in `DEFAULT_MODEL_ASSIGNMENTS` loaded — the project ships with 34 declared model IDs, but graceful fuzzy resolution means you don't need every single one to start.

## License

- Code: MIT
- This paper: CC-BY-4.0

## Contributing

Issues, pull requests, and forks all welcome. The project is opinionated but not closed; there's a roadmap in the paper, and most of the "not yet" items in the list above are good first issues for someone who wants to dig in. I am especially interested in:

- A real benchmark scorer (LLM-as-judge with a rubric)
- Skill palettes for the expanded mainline roles (strategist, heavy_reasoning, vision, scout, etc.)
- Skill palettes for the hacker-zone roles
- Provider adapters beyond LM Studio and Claude (Ollama, llama.cpp, vLLM)
- A proper CI workflow

If you read the paper and have notes, the best place for them is a discussion thread on the repo or an issue tagged `paper`.

— Tyler
