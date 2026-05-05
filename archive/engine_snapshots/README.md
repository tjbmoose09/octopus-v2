# Engine Snapshots (retired — pre-V2.2)

This folder preserves frozen copies of the agent engine variants that
predated V2.2. The canonical, supported engine is now
`agents/engine.py` — see `docs/SYSTEM_DESIGN_V2.2.md`.

## What's here

- `engine_good.py` — the last known-good pre-V2.2 engine (927 lines).
  This was the variant running before the zone-routing refactor. It has
  no `ZoneBoundaryError`, no `SessionZoneState`, no `can_route()` gate
  on `send_to_agent()`, and no awareness of `EXPANDED_AGENT_ROLES`.
- `engine_backup.py` — an older, truncated backup snapshot (845 lines,
  ends mid-statement inside `save_chat_history(...)`). Kept only as a
  historical reference point; **do not run this file**, it will raise
  a `SyntaxError` at import time.

## Why retired

V2.2 introduced:

- the mainline / Hacker Zone routing boundary (`config/zones.py`),
- the `EXPANDED_AGENT_ROLES` roster (mainline new + HZ agents),
- `send_to_agent(source_role=..., session=...)` with a `can_route()`
  pre-flight check that raises `ZoneBoundaryError` on cross-zone
  violations,
- pipeline-event emission of the V2.2 change-timeline kinds
  (`plan` / `routing` / `file_diff` / `memory_write` / `command` /
  `bridge` / `reply`), consumed by the React/Vite `ChangesRenderer`.

None of those are present in these snapshots. They're a liability in
the live tree because their names used to shadow `engine.py` in ad-hoc
imports during debugging.

## Status

- Not imported by any file in the V2.2 tree. A repo-wide grep for
  `engine_good` or `engine_backup` hits only the docs (`PERFECT_PROMPT.md`
  and `SYSTEM_DESIGN_V2.2.md`).
- The original paths (`agents/engine_good.py` and `agents/engine_backup.py`)
  have been replaced with retirement-stub modules that raise a clear
  `ImportError` if anything tries to load them; this flushes out stale
  import sites during the V2.2 rollout.
- Trailing-whitespace on a handful of lines in the source files is not
  perfectly preserved here (the file-write tool normalizes it); no code
  semantics are affected.

## How to read them

Open with any editor. They have no external ties to the current
`config/settings.py` post-merge, so running them would also fail at
import because `AGENT_ROLES` no longer has all the keys they
expected. Reference only.

Retired: V2.2 (see `docs/CHANGELOG_V2.2.md` once Phase F lands).
