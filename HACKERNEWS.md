# Hacker News submission

Hacker News doesn't render Markdown — submissions are plain text with a single URL. Below are three submission variants of decreasing length, plus a planned first-comment follow-up. Pick whichever variant matches your read of the audience and paste the body into the "title" / "url" / "text" fields on news.ycombinator.com/submit.

---

## Recommended title (≤80 chars)

```
Show HN: Octopus Agents – a 34-agent local-first mesh running on one workstation
```

Char count: 79. Stays under HN's 80-char title limit. Uses "Show HN:" because this is your own work and you want feedback.

## URL

Use the GitHub release URL once `gh release create v2.2.0` has run, e.g.:

```
https://github.com/<your-username>/octopus-v2/releases/tag/v2.2.0
```

If you'd rather point at the paper directly, use the raw GitHub URL for `PAPER.md`:

```
https://github.com/<your-username>/octopus-v2/blob/main/PAPER.md
```

For Show HN, the release URL is the better choice — it's the canonical landing page, has the tag, and surfaces both the announcement body and the paper attachment.

---

## Submission body — variant A (recommended, ~120 words)

```
I've been building Octopus Agents for several months as a solo project and just
cut V2.2. It's a 34-agent local-first multi-agent system that runs entirely on
one workstation — every model is a different LM Studio checkpoint, no vendor
cloud, no API keys required for the default config.

The interesting design choices, in order of how unusual they are:

- 34 agents in a strict 1:1 mapping to 34 distinct local models, not one
  big model in many costumes
- A second quarantined sub-mesh ("hacker zone") for uncensored / abliterated
  models, with its own brain and a hard isolation boundary
- 101 typed skills with autonomy flags, 37 MCP servers wired with
  per-agent allowlists, 4-scope memory backed by an Obsidian vault
- Cursor-inspired surface row: Desktop / Terminal / Web / Extension as
  first-class execution contexts
- Live mesh sidebar visualization where tentacles pulse on routing events

Full technical paper (no code, just stats and design rationale, ~6,000 words)
is in PAPER.md. Open issues, roadmap, and findings are honest. Pull requests
welcome.
```

## Submission body — variant B (shorter, ~60 words, leaner)

```
A 34-agent local-first multi-agent mesh running on one workstation. Every agent
is a different LM Studio model — 34 roles in 1:1 mapping with 34 distinct
checkpoints, deliberately, because heterogeneous models genuinely disagree.
Includes a quarantined sub-mesh for uncensored models, 101 typed skills, 37
MCP servers, a 4-scope Obsidian memory layer, and a live mesh visualization.
Full design paper in repo (no code, just stats and rationale).
```

## Submission body — variant C (minimal, dryest)

```
34 role-bound LLM agents on one workstation. 1:1 model mapping (34 distinct
LM Studio checkpoints). Two strictly isolated zones (mainline + opt-in
"hacker zone"). 101 typed skills, 37 MCP servers, four-scope memory backed by
Obsidian. React UI with live mesh viz. Local-first by construction. Paper
in PAPER.md — no code, just stats.
```

---

## Planned first comment (post immediately after submitting)

HN convention: drop a self-comment within 30 seconds of posting that frames
context, declares conflict-of-interest if any, and answers the obvious first
question. Helps the post survive its first hour.

```
Author here — happy to answer anything about the design choices.

A few things I'd flag up front, since the paper is honest about them:

1. The benchmark `quality_score` field is currently a stub — every captured
   run scored 35.0 because the evaluator hasn't been written yet. Real
   LLM-as-judge is the next benchmark task.

2. The 25 expanded roles route correctly but don't yet have wired skill or
   MCP allowlists. They run inference but can't autonomously call tools.
   They're latent capacity until V2.3.

3. The "hacker zone" naming is deliberate. The point is not edge cases or
   exploits — it's that some of the locally-loaded models are uncensored /
   abliterated variants useful for research, creative writing, and CTF-style
   work, and I wanted a hard isolation boundary so accidentally routing
   to them from a normal chat is impossible.

4. No CI yet. Coming.

Most-asked question I expect: "Why 34 agents instead of one?"
Short answer: because heterogeneous models trained on different data at
different scales by different vendors actually disagree, and the disagreement
is useful when an operator is deciding whether to ship a plan. Same prompt
to qwen3.6-27b vs nvidia/nemotron-3-nano produces audibly different reasoning
traces — Qwen tends to mathematicize, Nemotron tends to enumerate. With one
big model the disagreement is gone, and you've conceded the only reason to
run more than one process.
```

---

## After-submission checklist

1. Submit during a low-volume window — Tue/Wed/Thu 8–10am Pacific is the conventional sweet spot.
2. Drop the first-comment follow-up within ~30 seconds.
3. Don't ask friends to upvote — HN detects vote rings and will dead the post.
4. Reply to every comment within an hour for the first 90 minutes; HN ranks by velocity.
5. If a "Show HN" doesn't get traction in 4 hours, don't repost — submissions can only be promoted once and reposting marks you as desperate.

---

## Optional: Lobste.rs / r/LocalLLaMA / r/MachineLearning cross-posts

Three other places this post will land well:

- **Lobste.rs** — same submission shape but tagged `ai`, `programming`, and ideally a third tag like `practices` or `release`. Lobste.rs is more design-conscious than HN; lean on the "1:1 model mapping" and "zone isolation" angles.
- **r/LocalLLaMA** — title and body should foreground LM Studio specifically. They care about local inference. Lead with "34 different LM Studio models on one workstation" and post the banner.
- **r/MachineLearning** — only if you remove the Show HN framing and pitch it as a systems paper. Their `[P]` (project) flair fits, but the audience is more academic; mention the paper's stats focus and the open evaluator-design problem (the stub `quality_score`) explicitly.

Don't cross-post all four simultaneously. Stagger by 24–48 hours per platform.
