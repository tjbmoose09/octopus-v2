"""
Agent skills configuration for Octopus V2 multi-agent system.

100 diverse, expert-level skills across 9 agent roles:
  orchestrator (12), pm (11), dev (12), qa (11), critic (11),
  review (11), devops (11), automation (11), research (11)

Each skill ships with deep, actionable instructions fed directly into
both Claude API (orchestrator) and LM Studio agents (all arm roles).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentSkill:
    """Represents a single skill an agent can execute.

    Attributes:
        name: Kebab-case identifier (e.g., 'task-decomposition')
        display_name: Human-readable skill name
        description: What this skill enables the agent to DO (action-oriented)
        category: Skill category for organization and filtering
        source: Where adapted from ('codex' | 'anthropic' | 'custom')
        runtime: Required runtime or None ('python' | 'node' | 'docker' | None)
        mcp_dependencies: List of MCP server names this skill requires
        autonomous: Whether agent can invoke without user approval
        instructions: Core instruction set for executing this skill (like SKILL.md)
    """

    name: str
    display_name: str
    description: str
    category: str
    source: str
    runtime: Optional[str]
    mcp_dependencies: list[str]
    autonomous: bool
    instructions: str


# ============================================================================
# ORCHESTRATOR SKILLS  (12 skills)
# ============================================================================

ORCHESTRATOR_SKILLS = [
    AgentSkill(
        name="task-decomposition",
        display_name="Task Decomposition",
        description="Break complex user requests into atomic subtasks with dependency graphs and parallelization opportunities.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Analyze the incoming request and generate a directed acyclic graph (DAG) of subtasks.
For each subtask: assign agent type (dev/qa/devops/etc), specify upstream dependencies, estimate complexity 1-5.
Identify which subtasks can run in parallel versus must be sequential — maximize parallelism.
Return JSON: { task_id, subtasks: [{ id, agent_role, description, deps[], complexity, estimated_minutes }] }.
Flag any ambiguous requirements and ask the user ONE clarifying question before decomposing.
If the request is purely conversational, respond directly without decomposing.
        """.strip(),
    ),
    AgentSkill(
        name="agent-delegation",
        display_name="Agent Delegation",
        description="Route decomposed subtasks to the best-fit agent based on skill match, load, and urgency.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Given a decomposed task list, match each subtask to the agent with the highest skill overlap.
Score agents: skill_match (0-10) + availability_bonus (0-3) + specialization_bonus (0-2).
Prefer less-loaded agents for balanced distribution; never double-assign without explicit reason.
Build delegation manifest: { task_id -> { agent_role, priority, deadline, context_summary } }.
Pass full task context (user goal, prior decisions, constraints) to each agent.
Handle reassignment if a primary agent reports error or timeout — escalate to orchestrator.
        """.strip(),
    ),
    AgentSkill(
        name="progress-synthesis",
        display_name="Progress Synthesis",
        description="Aggregate results from multiple agents into coherent, user-facing reports with rollup status.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Collect completion status and output artifacts from all agents in the task tree.
Detect blockers, failures, and partial results. Escalate CRITICAL issues immediately.
Merge outputs into a unified narrative: executive summary, detailed findings, next steps.
Track metrics: total_elapsed_ms, subtask_success_rate, retry_count, rollback_count.
Highlight disagreements between agents (e.g., dev says feasible, critic says risky).
Deliver final report in clear markdown with separate sections per agent contribution.
        """.strip(),
    ),
    AgentSkill(
        name="memory-manager",
        display_name="Memory Manager",
        description="Read/write Obsidian vault for long-term context, decision history, and cross-project learning.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["obsidian"],
        autonomous=True,
        instructions="""
On task start: search vault for prior context matching user's domain (tags, titles, links).
During execution: append interim decisions and findings to running project notes.
On completion: write ADR-style decision record for every architectural or strategic choice.
Maintain an agent capability index — track which agents excel or struggle at specific task types.
Prune stale short-term notes (>24h old) unless tagged as long-term knowledge.
Expose a search interface: given a query, return top-5 relevant vault notes with excerpts.
        """.strip(),
    ),
    AgentSkill(
        name="conflict-resolution",
        display_name="Conflict Resolution",
        description="Resolve conflicting outputs from agents by weighing evidence and applying decision criteria.",
        category="manage",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
When two or more agents provide contradictory outputs, surface the conflict explicitly.
Classify conflict type: factual disagreement, design preference, risk tolerance, or scope.
For factual conflicts: request the research agent to verify with external sources.
For design preference: apply weighted criteria (performance, maintainability, cost, security).
For risk tolerance: default to the more conservative approach unless user overrides.
Document the resolution rationale and the discarded alternatives in the task record.
Never silently pick one agent's output — always explain the resolution logic.
        """.strip(),
    ),
    AgentSkill(
        name="adaptive-replanning",
        display_name="Adaptive Replanning",
        description="Dynamically replan mid-execution when conditions change, agents fail, or scope shifts.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Monitor execution state continuously; trigger replanning when: agent fails, new info arrives, or user changes scope.
Diff the original plan against current state: what is done, in-progress, blocked, or invalidated?
Generate a revised DAG using only remaining work, accounting for new constraints.
Re-estimate timelines and notify the user of any deadline impact with clear explanation.
Preserve completed work — never redo finished subtasks unless explicitly needed.
Log the replan event with before/after plans and the triggering reason for audit purposes.
        """.strip(),
    ),
    AgentSkill(
        name="user-intent-parsing",
        display_name="User Intent Parsing",
        description="Extract precise goals, constraints, and success criteria from natural language requests.",
        category="manage",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Parse the user message and extract: primary_goal, secondary_goals[], hard_constraints[], soft_preferences[], success_criteria[].
Identify unstated assumptions (e.g., 'build a website' implies hosting, security, mobile support).
Detect ambiguities: where the request could mean 2+ different things, list them and ask for clarification.
Output a structured intent object as JSON before passing to planning step.
Map success criteria to measurable outcomes: 'fast' -> p99 latency < 200ms, 'secure' -> OWASP Top 10 compliance.
Store parsed intent in working memory so all agents share the same understanding of the goal.
        """.strip(),
    ),
    AgentSkill(
        name="multi-agent-consensus",
        display_name="Multi-Agent Consensus",
        description="Run structured debate rounds between agents to reach high-confidence decisions on ambiguous choices.",
        category="manage",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=False,
        instructions="""
For decisions with high uncertainty or impact, convene a structured review round.
Round 1: Each relevant agent independently proposes an approach with rationale.
Round 2: Each agent reviews the other proposals and raises objections or endorsements.
Round 3: Orchestrator synthesizes and calls consensus or escalates to the user.
Track agreement level: unanimous, majority, split. Split decisions escalate to the user.
Document all perspectives — never discard minority views without acknowledgment.
Cap consensus rounds at 3 to prevent infinite loops; force decision after round 3.
        """.strip(),
    ),
    AgentSkill(
        name="context-window-management",
        display_name="Context Window Management",
        description="Compress, chunk, and prioritize context to stay within token limits for long-running tasks.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["obsidian"],
        autonomous=True,
        instructions="""
Monitor token usage for each agent message thread; alert when approaching 75% of context limit.
Compress long histories: summarize old turns (>10 messages) into a dense paragraph.
Prioritize context: system prompt > recent messages > task-specific facts > background knowledge.
Offload non-critical context to Obsidian vault and replace with a reference stub.
For long-running tasks, maintain a rolling 'task brief' document (max 500 tokens) updated every 5 turns.
Never silently drop critical context — always verify the agent retains key constraints after compression.
        """.strip(),
    ),
    AgentSkill(
        name="feedback-loop",
        display_name="Feedback Loop",
        description="Capture user feedback on agent outputs and adjust agent behavior for future tasks.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["obsidian"],
        autonomous=True,
        instructions="""
After each task completion, prompt the user for a quality rating (1-5) and optional text feedback.
Parse feedback and extract: what was good, what was wrong, what should change.
Update agent capability scores in the vault: positive feedback +0.1, negative -0.2 on relevant skill.
Adjust delegation weights so high-scoring agents get priority on similar future tasks.
Flag systematic issues (same complaint 3+ times) as a configuration problem to fix.
Generate monthly performance summary report per agent role with trend data.
        """.strip(),
    ),
    AgentSkill(
        name="cost-optimization",
        display_name="Cost Optimization",
        description="Route tasks to the cheapest capable model without sacrificing quality, tracking token spend.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Maintain a cost-capability matrix: for each task type, record the minimum model tier that achieves acceptable quality.
Route simple tasks (classification, extraction, summarization) to smaller/cheaper models.
Reserve expensive models (Claude, GPT-4) for complex reasoning, creative work, or critical decisions.
Track token usage per task: input_tokens, output_tokens, cost_usd.
Set per-session budget limits; switch to cheaper models when 80% of budget is consumed.
Report cost efficiency metrics: cost-per-task, tokens-per-subtask, model utilization breakdown.
        """.strip(),
    ),
    AgentSkill(
        name="cross-project-learning",
        display_name="Cross-Project Learning",
        description="Extract reusable patterns from completed projects and apply them to accelerate future work.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["obsidian"],
        autonomous=True,
        instructions="""
At project completion, extract: successful patterns, reusable components, effective agent combinations, gotchas to avoid.
Store patterns in vault under Knowledge/Patterns/ with tags for domain, tech stack, and complexity.
At new project start, search vault for similar past projects and surface relevant patterns.
Build a 'recipe book' — for common request types (REST API, data pipeline, report), pre-cache the best subtask decomposition.
Track pattern usage: how often patterns are reused and whether they accelerate completion.
Deprecate patterns that consistently require modification (>80% of uses need changes).
        """.strip(),
    ),
]


# ============================================================================
# PM (PRODUCT MANAGER) SKILLS  (11 skills)
# ============================================================================

PM_SKILLS = [
    AgentSkill(
        name="sprint-planning",
        display_name="Sprint Planning",
        description="Create structured sprint plans with story points, acceptance criteria, and task dependencies.",
        category="manage",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Break down user stories into actionable tasks with detailed acceptance criteria and definition of done.
Assign story points using Fibonacci scale (1, 2, 3, 5, 8, 13) based on complexity and uncertainty.
Check historical velocity to set realistic sprint capacity; add 20% buffer for unplanned work.
Build sprint manifest: sprint_goal, start_date, end_date, stories[], capacity_points, risk_items[].
Order backlog by business value × confidence / effort; highest-value easiest items first.
Flag blockers and external dependencies with risk mitigation steps before sprint start.
        """.strip(),
    ),
    AgentSkill(
        name="kanban-management",
        display_name="Kanban Management",
        description="Manage task flow through pipeline stages, enforce WIP limits, and flag stuck work.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["linear", "clickup"],
        autonomous=True,
        instructions="""
Monitor task state and update Linear/ClickUp board as agents report progress.
Enforce WIP limits per stage: To Do (unlimited), In Progress (3), Review (2), Done (unlimited).
Auto-move cards based on agent completion signals: assign -> in_progress -> review -> done.
Flag stuck tasks: no status change for >4h triggers a 'needs attention' label and notification.
Generate daily standup report: completed_yesterday, in_progress_today, blockers.
Produce weekly cycle time metrics: average time from 'in_progress' to 'done' per task type.
        """.strip(),
    ),
    AgentSkill(
        name="timeline-estimation",
        display_name="Timeline Estimation",
        description="Produce probabilistic duration estimates using complexity analysis and historical data.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Analyze task complexity across 5 dimensions: scope, skill required, unknowns, dependencies, parallelism.
Reference historical completion times for similar work types from the vault.
Generate three-point estimate: optimistic (p10), most likely (p50), pessimistic (p90).
Compute critical path: the longest sequential chain of tasks that determines project duration.
Flag high-uncertainty tasks (p90/p10 ratio > 3×) for spike or proof-of-concept work first.
Present timeline as Gantt-style text with milestones, not just a single date number.
        """.strip(),
    ),
    AgentSkill(
        name="status-reporting",
        display_name="Status Reporting",
        description="Produce structured status reports with progress metrics, risks, and recommendations.",
        category="document",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Pull data from orchestrator progress synthesis, sprint records, and agent completion logs.
Generate daily/weekly report structure: accomplishments, in-progress, blocked, upcoming.
Include burn-down chart data: remaining_story_points vs. days_remaining vs. ideal_line.
Risk register: top 5 risks with probability, impact, mitigation status, and owner.
Velocity trend: last 3 sprints actual vs. planned — flag if trending down.
Keep language crisp and non-technical for stakeholder consumption; include a one-sentence TL;DR at the top.
        """.strip(),
    ),
    AgentSkill(
        name="requirements-gathering",
        display_name="Requirements Gathering",
        description="Elicit, document, and validate functional and non-functional requirements from stakeholder input.",
        category="manage",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=False,
        instructions="""
Use structured elicitation: ask 5W+H (Who, What, When, Where, Why, How) for each feature area.
Separate functional requirements (what the system does) from non-functional (how well it does it).
For each NFR, attach a measurable target: 'performant' -> p99 response < 500ms, '99.9% uptime' -> 43 min/month downtime max.
Create a requirements traceability matrix: requirement_id -> source -> test_case -> status.
Identify requirements conflicts (one NFR contradicting another) and resolve with stakeholders.
Output a Requirements Specification Document (RSD) with MoSCoW prioritization: Must/Should/Could/Won't.
        """.strip(),
    ),
    AgentSkill(
        name="stakeholder-communication",
        display_name="Stakeholder Communication",
        description="Craft targeted updates for different audiences: technical team, executives, and end users.",
        category="document",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Identify audience type: executive (wants business impact), technical (wants implementation details), end-user (wants feature benefits).
Tailor language and depth: executives get 2-paragraph summaries; tech team gets full specs; end users get changelog bullet points.
Translate technical risks into business language: 'N+1 query' -> 'page load times may triple under load'.
Use BLUF (Bottom Line Up Front) structure — lead with the conclusion, support with details.
Attach relevant metrics and KPIs to every communication: % complete, cost, date.
Flag when communication requires a response or decision from the stakeholder with a clear deadline.
        """.strip(),
    ),
    AgentSkill(
        name="roadmap-planning",
        display_name="Roadmap Planning",
        description="Build quarterly and annual product roadmaps aligned with business goals and technical constraints.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=False,
        instructions="""
Collect input from: business goals (OKRs), user feedback (top pain points), tech debt backlog, competitive analysis.
Group initiatives into themes (e.g., 'Performance', 'User Growth', 'Platform Stability').
Sequence initiatives by: business impact, technical dependency order, resource availability.
Assign each initiative to a quarter with rough effort estimate (S/M/L/XL) and named owner.
Mark items as: committed (this quarter), planned (next quarter), aspirational (future).
Review roadmap against capacity: if total planned > 70% capacity, move lowest-priority items out.
Create a Now/Next/Later view for stakeholder-facing communication alongside the detailed Gantt.
        """.strip(),
    ),
    AgentSkill(
        name="user-story-writing",
        display_name="User Story Writing",
        description="Write well-formed user stories with personas, acceptance criteria, and edge case coverage.",
        category="document",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Structure every story as: As a [persona], I want [action], so that [benefit].
Define 3-7 acceptance criteria per story using Given/When/Then (Gherkin) format.
Identify the primary persona and secondary personas who interact with the feature.
Document edge cases explicitly: empty states, error states, permission boundaries, rate limits.
Include wireframe description or link to Figma frame if visual layout is involved.
Size story: if acceptance criteria > 7 or complexity > 5, split into smaller stories before sprint planning.
        """.strip(),
    ),
    AgentSkill(
        name="dependency-mapping",
        display_name="Dependency Mapping",
        description="Map inter-team and inter-system dependencies to identify blockers before they hit.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
List all external dependencies: other teams, third-party APIs, infrastructure, data pipelines.
For each dependency: owner, expected delivery date, confidence level (high/medium/low).
Build a dependency graph showing which tasks are blocked by which external items.
Identify the critical path through the dependency graph — the sequence with zero float.
Create an escalation plan for each low-confidence dependency: what is plan B if it slips?
Review dependency status weekly and update the graph; proactively alert on slipping items 2 weeks before impact.
        """.strip(),
    ),
    AgentSkill(
        name="okr-alignment",
        display_name="OKR Alignment",
        description="Map tasks and features to company OKRs to ensure all work delivers measurable business value.",
        category="manage",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Receive company OKRs (Objectives + Key Results) and the current work backlog.
For each backlog item, tag the OKR(s) it contributes to and estimate the contribution strength (low/medium/high).
Flag backlog items with no OKR alignment — these are candidates for deprioritization or removal.
Score work items: OKR_alignment_strength × business_impact / effort; rank backlog by this score.
Generate OKR health report: for each KR, show which initiatives contribute and their cumulative projected impact.
Recommend dropping or deferring items when projected OKR contribution falls short of target.
        """.strip(),
    ),
    AgentSkill(
        name="retrospective-facilitation",
        display_name="Retrospective Facilitation",
        description="Run structured sprint retrospectives to extract actionable improvements from past work.",
        category="manage",
        source="custom",
        runtime=None,
        mcp_dependencies=["obsidian"],
        autonomous=False,
        instructions="""
Gather data: sprint metrics (velocity, bugs found, unplanned work %), agent performance scores, user feedback.
Run 4Ls framework: Liked, Learned, Lacked, Longed For — collect input from all agent role perspectives.
Synthesize into top 3 action items with: what will change, who owns it, how success is measured.
Compare against previous retro action items — have last sprint's improvements been implemented?
Write retro summary to vault under retrospectives/ with date, sprint_id, and action item tags.
Track action item completion rate across sprints; flag consistently ignored action items.
        """.strip(),
    ),
]


# ============================================================================
# DEV (DEVELOPER) SKILLS  (12 skills)
# ============================================================================

DEV_SKILLS = [
    AgentSkill(
        name="full-stack-build",
        display_name="Full-Stack Build",
        description="Build complete applications from requirements specs including backend, frontend, and database layers.",
        category="code",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Read the spec fully before writing a single line of code. Extract: entities, relationships, user flows, NFRs.
Scaffold the project: directory structure, dependency manifests, environment config files first.
Implement backend: API routes with validation, service layer with business logic, data access layer.
Implement frontend: component tree, state management, API integration, error boundaries.
Wire up database: schema migrations, seed data, ORM models with typed fields.
Add cross-cutting concerns last: auth middleware, logging, health checks, CORS.
Output complete, runnable files — never snippets. Include README with setup instructions.
        """.strip(),
    ),
    AgentSkill(
        name="frontend-design",
        display_name="Frontend Design",
        description="Implement pixel-perfect UI components from designs with responsiveness and full accessibility.",
        category="design",
        source="anthropic",
        runtime="node",
        mcp_dependencies=["figma"],
        autonomous=True,
        instructions="""
Fetch component specs from Figma: colors, typography, spacing, component states (default, hover, active, disabled, error).
Implement React/Vue components matching designs with CSS-in-JS or Tailwind utility classes.
Ensure responsive breakpoints: mobile (320-767px), tablet (768-1023px), desktop (1024px+).
Add ARIA roles, labels, keyboard navigation (tab order, focus traps), and color contrast (WCAG AA minimum).
Write Storybook stories for each component covering all states and prop variants.
Cross-check rendered output against Figma in both light and dark mode before marking complete.
        """.strip(),
    ),
    AgentSkill(
        name="api-development",
        display_name="API Development",
        description="Build REST and GraphQL APIs with schema-first design, auth, error handling, and full documentation.",
        category="code",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design API contract first (OpenAPI 3.1 or GraphQL SDL) before implementation.
Implement endpoints with: request validation (pydantic/zod), typed error responses (RFC 7807 Problem Details), HTTP status codes.
Add authentication: JWT with refresh token rotation, or OAuth 2.0 with PKCE for browser clients.
Implement RBAC: define roles, permissions matrix, and enforce at route middleware level.
Add rate limiting (token bucket), request ID headers, and structured JSON logging per request.
Write integration tests covering: happy path, validation errors, auth failures, and edge cases.
Auto-generate OpenAPI docs with curl examples; include Postman collection export.
        """.strip(),
    ),
    AgentSkill(
        name="database-design",
        display_name="Database Design",
        description="Design normalized schemas, write migrations, add indexes, and optimize query performance.",
        category="code",
        source="custom",
        runtime=None,
        mcp_dependencies=["supabase", "planetscale"],
        autonomous=True,
        instructions="""
Analyze entity-relationship requirements and design to 3NF (or intentionally denormalize with justification).
Write forward-and-rollback migrations (Alembic/Knex/Flyway) — every migration must be reversible.
Add indexes on: all foreign keys, columns in WHERE clauses, columns in ORDER BY with high cardinality.
Document schema: table purpose, column constraints, relationships, and any denormalization rationale.
Implement soft delete (deleted_at timestamp) for entities that require audit trails.
Create seed scripts for development (realistic dummy data) and test (predictable minimal data).
Run EXPLAIN ANALYZE on top-10 queries and optimize any with seq scans on large tables.
        """.strip(),
    ),
    AgentSkill(
        name="web-game-dev",
        display_name="Web Game Development",
        description="Build browser games with physics engine, collision detection, animation loop, and multiplayer support.",
        category="code",
        source="codex",
        runtime="node",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Bootstrap game with Phaser 3 (2D) or Three.js/Babylon.js (3D); configure canvas, asset loader, and scene manager.
Implement game loop: fixed-timestep physics update at 60Hz, variable render step with delta smoothing.
Build entity-component system: entities have transform, physics body, renderer, and behavior components.
Implement collision detection: broad phase (AABB grid) + narrow phase (SAT or circle-circle) for accuracy.
Create state machine: MainMenu, Loading, Playing, Paused, GameOver with transitions.
Add multiplayer via WebSocket: authoritative server tick at 20Hz, client-side prediction and reconciliation.
Profile and target 60fps on mid-range devices; optimize sprites, draw calls, and garbage allocation.
        """.strip(),
    ),
    AgentSkill(
        name="mcp-builder",
        display_name="MCP Builder",
        description="Build custom MCP servers exposing tools, resources, and prompts via JSON-RPC over stdio or SSE.",
        category="code",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design the MCP interface: list of tools (name, description, inputSchema), resources, and prompt templates.
Implement transport layer: stdio for CLI tools, SSE for web servers; handle JSON-RPC 2.0 message framing.
Create each tool handler: validate input against JSON Schema, call external API/service, return typed result.
Add auth layer if needed: API key via env, OAuth flow, or pass-through from calling agent.
Implement graceful error handling: tool errors return structured error objects, not crashes.
Write a client example script demonstrating every tool with sample inputs and expected outputs.
Document: installation, config options, available tools with parameter tables, and troubleshooting.
        """.strip(),
    ),
    AgentSkill(
        name="code-generation",
        display_name="Code Generation",
        description="Generate production-ready code from natural language specs, templates, and schema definitions.",
        category="code",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Parse spec: extract entities, operations, relationships, constraints, and example inputs/outputs.
Select code template appropriate to tech stack (FastAPI, Express, Django, Next.js, etc.).
Generate code with: type hints/TypeScript types, docstrings/JSDoc, error handling, and input validation.
Co-generate unit tests alongside each function — tests must pass against the generated code.
Generate a 'generation manifest' listing every file created with its purpose and public interface.
Validate generated code with a syntax check (compile/lint) before marking complete.
Include TODO comments for any spec ambiguities that require human review.
        """.strip(),
    ),
    AgentSkill(
        name="refactoring",
        display_name="Refactoring",
        description="Safely refactor code for readability, maintainability, and performance without changing behavior.",
        category="code",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Before refactoring: ensure test coverage >80% on the target module; run tests to establish a green baseline.
Apply refactoring patterns incrementally: Extract Method, Rename, Move Class, Introduce Parameter Object.
Eliminate code smells: long methods (>30 lines), large classes (>200 lines), data clumps, feature envy.
Reduce cyclomatic complexity: target <10 per function; extract branches into named helper functions.
Improve naming: variables and functions should be self-documenting — no abbreviations, no 'temp', 'data', 'x'.
Run tests after each atomic refactor to verify no behavior changed; commit each refactor separately.
Document architectural changes in a refactoring notes file for reviewers.
        """.strip(),
    ),
    AgentSkill(
        name="ai-integration",
        display_name="AI Integration",
        description="Integrate LLM APIs (OpenAI, Anthropic, local models) into applications with streaming and fallbacks.",
        category="code",
        source="anthropic",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design the prompt architecture: system prompt, few-shot examples, user message template, output format spec.
Implement streaming responses using SSE or WebSocket for real-time token display.
Add retry logic with exponential backoff for rate limits and transient errors.
Implement fallback chain: primary model -> secondary model -> cached response -> graceful error.
Track token usage per request and warn when approaching context limits; implement chunking if needed.
Cache deterministic queries (same prompt hash -> same response) with a configurable TTL.
Add evaluation hooks: for each AI call, log prompt + response for offline quality analysis.
        """.strip(),
    ),
    AgentSkill(
        name="mobile-development",
        display_name="Mobile Development",
        description="Build cross-platform mobile apps with React Native or Flutter targeting iOS and Android.",
        category="code",
        source="custom",
        runtime="node",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Scaffold project with Expo (React Native) or Flutter; configure navigation, state management, and theme.
Implement platform-specific behaviors using conditional imports or Platform.select().
Handle offline mode: queue mutations locally, sync when network returns, handle conflicts.
Optimize for mobile: lazy load screens, image compression, minimize JS bundle size (RN) or widget rebuilds (Flutter).
Add push notification support: FCM for Android, APNs for iOS, handle foreground/background/killed states.
Test on real device simulator profiles for common phone sizes; profile with React DevTools or Dart Observatory.
Configure CI to build and sign both iOS (.ipa) and Android (.apk/.aab) artifacts automatically.
        """.strip(),
    ),
    AgentSkill(
        name="security-hardening",
        display_name="Security Hardening",
        description="Harden application code against injection, auth bypass, insecure deps, and data exposure.",
        category="code",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Audit all user inputs: apply parameterized queries, HTML encode outputs, validate file upload types and sizes.
Enforce auth on every protected route; never trust client-supplied role or permission values.
Apply security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
Scan dependencies: run 'pip audit' / 'npm audit'; update or replace packages with known CVEs.
Secrets management: verify no secrets in code, env files checked in, or logs — use a vault (AWS Secrets Manager, HashiCorp Vault).
Rate limit auth endpoints: lockout after 5 failed attempts, implement CAPTCHA for sensitive actions.
Document security decisions in a SECURITY.md file with contact for responsible disclosure.
        """.strip(),
    ),
    AgentSkill(
        name="realtime-systems",
        display_name="Real-Time Systems",
        description="Build WebSocket and event-driven systems with pub/sub, backpressure, and reconnect logic.",
        category="code",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design event schema: typed event envelopes with { event_type, payload, timestamp, correlation_id }.
Implement server-side WebSocket hub: connection registry, room/channel management, broadcast.
Add heartbeat (ping/pong at 30s) and detect stale connections; clean up silently disconnected clients.
Handle backpressure: if client message queue > 100 items, pause producer and emit 'slow consumer' metric.
Implement client-side reconnect: exponential backoff (1s, 2s, 4s, max 30s), state resync on reconnect.
Test with simulated network partitions: disconnect mid-session, reconnect, verify state consistency.
Add pub/sub via Redis (Socket.IO adapter or raw SUBSCRIBE/PUBLISH) for horizontal scaling across instances.
        """.strip(),
    ),
]


# ============================================================================
# QA (QUALITY ASSURANCE) SKILLS  (11 skills)
# ============================================================================

QA_SKILLS = [
    AgentSkill(
        name="test-suite-builder",
        display_name="Test Suite Builder",
        description="Write comprehensive unit, integration, and contract test suites with high coverage.",
        category="test",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Analyze code to map every public function, branch, and error path requiring coverage.
Write unit tests: one test per behavior (not per function), use descriptive names (test_should_return_error_when_input_is_empty).
Use mocks/stubs/fakes for external dependencies — never hit real network or DB in unit tests.
Write integration tests that use real DB (test container), real HTTP, and verify component interactions.
Write contract tests (Pact) for every API endpoint consumed or provided by this service.
Target: unit coverage >90%, integration coverage >70%. Generate coverage report with uncovered lines listed.
Run tests in CI; mark test suite as blocking merge if coverage drops below baseline.
        """.strip(),
    ),
    AgentSkill(
        name="webapp-testing",
        display_name="Web App Testing",
        description="End-to-end user flow testing with Playwright across browsers, viewports, and accessibility.",
        category="test",
        source="anthropic",
        runtime="node",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Map the top 10 user journeys (signup, login, core feature, checkout, error recovery, etc.).
Write Playwright scripts: page.goto, fill, click, waitForSelector — avoid CSS selectors, prefer ARIA roles and labels.
Run in 3 browsers (Chrome, Firefox, Safari/WebKit) and 2 viewport sizes (mobile 390px, desktop 1440px).
Check accessibility on every key page: run axe-core and fail on WCAG AA violations.
Add visual regression: take baseline screenshots and diff on each run; fail if pixel diff >0.5%.
Test error states: force 500 responses, network offline, invalid tokens — assert graceful error messages.
Output JUnit XML test report and attach screenshots of failures automatically.
        """.strip(),
    ),
    AgentSkill(
        name="load-testing",
        display_name="Load Testing",
        description="Build and run load tests to establish performance baselines and identify breaking points.",
        category="test",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Profile realistic user behavior: capture real traffic patterns or model from product analytics.
Write k6 or Locust scripts: define user scenarios with realistic think times (1-3s between actions).
Execute three test phases: baseline (10 VUs, 5 min), load (target VUs, 15 min), stress (2× target, until error spike).
Monitor: p50/p95/p99 latency, throughput (req/s), error rate, CPU/memory on server.
Record breaking point: VU count where error_rate >1% or p99 >2× baseline — this is the system limit.
Produce report: graphs of latency vs. VU count, bottleneck analysis, top 3 recommendations.
Re-run after optimizations to validate improvements; store baseline numbers in the vault for regression tracking.
        """.strip(),
    ),
    AgentSkill(
        name="bug-reproduction",
        display_name="Bug Reproduction",
        description="Reproduce reported bugs to minimal test cases with full diagnostic context.",
        category="test",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Read bug report; identify: symptoms, environment, steps_to_reproduce, expected vs. actual behavior.
Reproduce on identical environment (same OS, browser, Python/Node version, DB state) first.
Isolate root cause by binary search: disable features/lines until bug disappears, then re-enable one at a time.
Create minimal reproduction: smallest possible input/state that reliably triggers the bug (>95% of attempts).
Capture all diagnostics: stack trace, request/response logs, DB query log, browser console.
Write a failing test case that encodes the bug as an assertion — this test will become the regression guard.
Rate severity: P1 (data loss / security), P2 (core feature broken), P3 (degraded), P4 (cosmetic).
        """.strip(),
    ),
    AgentSkill(
        name="api-testing",
        display_name="API Testing",
        description="Test REST/GraphQL APIs for correctness, schema compliance, auth enforcement, and error handling.",
        category="test",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Generate test cases from OpenAPI/GraphQL schema: all endpoints × (valid, invalid, boundary) inputs.
Verify: correct HTTP status codes, response body matches schema (validate with ajv/pydantic), headers present.
Test auth: unauthenticated requests return 401, wrong role returns 403, expired token returns 401.
Test idempotency: PUT and DELETE should be idempotent — call twice and verify identical state.
Test rate limiting: exceed limit and verify 429 with Retry-After header.
Generate a Postman collection export so developers can run tests manually.
Produce a machine-readable test report (JUnit XML or CTRF) for CI integration.
        """.strip(),
    ),
    AgentSkill(
        name="mutation-testing",
        display_name="Mutation Testing",
        description="Run mutation tests to validate test quality — verify tests actually catch code defects.",
        category="test",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Run mutation testing framework (mutmut for Python, Stryker for JS) on the codebase.
Mutation score = killed_mutants / total_mutants; target score >75%.
Triage surviving mutants: classify as 'equivalent' (unmeasurable behavior) or 'missed' (test gap).
For each missed mutant, write a new test that kills it — directly strengthening the test suite.
Prioritize mutation testing on: authentication code, payment logic, data validation functions.
Report mutation score per module with trend over time; alert if score drops >5% between runs.
        """.strip(),
    ),
    AgentSkill(
        name="security-testing",
        display_name="Security Testing",
        description="Run automated DAST scans, fuzz inputs, and test for OWASP Top 10 vulnerabilities.",
        category="test",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Run OWASP ZAP in automated scan mode against the staging environment; capture all alerts.
Fuzz every input field: send SQL injection payloads, XSS payloads, format strings, oversized inputs.
Test authentication: brute force lockout, session fixation, JWT algorithm confusion (alg:none), CSRF tokens.
Test authorization: access another user's resources by manipulating IDs (IDOR), test privilege escalation paths.
Check for sensitive data exposure: search responses for credit cards, SSNs, passwords, private keys (regex patterns).
Generate a security test report with CVSS scores for each finding and remediation checklist.
Retest fixed vulnerabilities to confirm closure before marking resolved.
        """.strip(),
    ),
    AgentSkill(
        name="accessibility-testing",
        display_name="Accessibility Testing",
        description="Audit applications for WCAG 2.1 AA compliance across keyboard, screen reader, and color axes.",
        category="test",
        source="anthropic",
        runtime="node",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Run automated audit with axe-core on every major page; capture and categorize all violations.
Manual keyboard audit: tab through every interactive element; verify focus order is logical and focus ring is visible.
Screen reader audit: use NVDA (Windows) or VoiceOver (Mac); navigate all forms, modals, and dynamic content.
Color contrast: verify text (4.5:1 ratio for normal, 3:1 for large) and UI components (3:1) against backgrounds.
Test with 200% zoom: ensure no content is clipped, overlapping, or illegible at high zoom levels.
Check all images for alt text; verify decorative images have alt="" and informational images have descriptive alt.
Output WCAG compliance matrix: criterion → pass/fail/not-applicable with evidence screenshots.
        """.strip(),
    ),
    AgentSkill(
        name="regression-testing",
        display_name="Regression Testing",
        description="Build and maintain regression test suites that run on every deploy to catch breakage.",
        category="test",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Identify the 20 most critical user journeys (high traffic × high business impact).
Write stable, deterministic regression tests for each journey using data fixtures.
Tag tests by impact area (auth, payments, search, etc.) for targeted runs on relevant code changes.
Establish a 'never-fail' baseline: tests that have never flaked in 100 runs. Any new flaky test must be fixed or removed.
Track regression rate: what % of deploys cause at least one regression. Target <5%.
Auto-assign regression failures to the last PR author that touched the relevant code path.
Maintain test data isolation: each test creates and cleans up its own data — no shared state.
        """.strip(),
    ),
    AgentSkill(
        name="test-data-management",
        display_name="Test Data Management",
        description="Design, generate, and manage realistic test datasets for repeatable and isolated testing.",
        category="test",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design test data taxonomy: seed data (always present), fixture data (per test), generated data (randomized).
Use factory libraries (factory_boy, faker) to generate realistic, varied test records programmatically.
Implement data isolation: each test suite gets a clean DB snapshot; parallel tests never share state.
For performance tests, generate large datasets: 100k users, 1M records — verify generation completes in <60s.
Mask or anonymize any production data used for testing: PII must be replaced with generated equivalents.
Version test datasets alongside code in source control; data migrations must update test datasets too.
        """.strip(),
    ),
    AgentSkill(
        name="chaos-testing",
        display_name="Chaos Testing",
        description="Inject failures (network partition, CPU spike, pod kill) to verify system resilience.",
        category="test",
        source="custom",
        runtime="docker",
        mcp_dependencies=[],
        autonomous=False,
        instructions="""
Define the steady state: key metrics (error_rate, latency_p99, throughput) at normal operation.
Identify failure hypotheses: 'The system will tolerate a single DB node failure gracefully'.
Inject failures using chaos tools (Chaos Monkey, Toxiproxy, tc netem): latency spikes, packet loss, process kill.
Monitor steady state metrics during chaos injection; record deviation from baseline.
Verify recovery: after chaos is stopped, system must return to steady state within defined RTO.
Document findings: what broke, what held, what surprised you. Translate into reliability improvements.
Never run chaos tests on production without explicit approval and rollback plan.
        """.strip(),
    ),
]


# ============================================================================
# CRITIC SKILLS  (11 skills)
# ============================================================================

CRITIC_SKILLS = [
    AgentSkill(
        name="architecture-review",
        display_name="Architecture Review",
        description="Analyze system design for scalability flaws, coupling, single points of failure, and security gaps.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Map system architecture: components, interfaces, data flows, external dependencies, and trust boundaries.
Evaluate scalability: identify bottlenecks under 10×, 100×, 1000× traffic. Which components fail first?
Check for SPOFs: is every critical component redundant? What is the blast radius of each failure?
Review coupling: are services tightly coupled (shared DB, synchronous calls) where loose coupling would be safer?
Apply CAP theorem: for each data store, is the current consistency/availability trade-off intentional and correct?
Rate findings: CRITICAL (data loss / outage risk), HIGH (scalability ceiling), MEDIUM (maintainability), LOW (minor improvement).
Propose concrete alternatives for every CRITICAL and HIGH finding — don't just list problems.
        """.strip(),
    ),
    AgentSkill(
        name="threat-modeling",
        display_name="Threat Modeling",
        description="Identify attack surfaces and model threats using STRIDE to produce a prioritized risk register.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Build data flow diagram (DFD): identify processes, data stores, external entities, and trust boundaries.
Apply STRIDE per component: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.
For each threat: assign CVSS 3.1 score (base score minimum), document attack scenario and preconditions.
Prioritize by risk score (CVSS × exploitability × asset value). Focus report on top 10 threats.
Recommend controls: preventive (prevent attack), detective (detect attack), corrective (recover from attack).
Create threat register: threat_id, description, CVSS, status (open/mitigated/accepted), mitigation control.
Schedule re-review when architecture changes significantly or annually at minimum.
        """.strip(),
    ),
    AgentSkill(
        name="cost-analysis",
        display_name="Cost Analysis",
        description="Model infrastructure and API costs at various scales with ROI and break-even analysis.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Itemize costs: compute (CPU/RAM/GPU), storage (block, object, DB), networking (egress, CDN), managed services, API calls.
Build cost model with traffic as the independent variable: compute cost at 1k, 10k, 100k, 1M users/requests per day.
Compare cloud options: AWS vs. GCP vs. Azure vs. self-hosted for each major component.
Calculate hidden costs: engineering time for maintenance, incident response, compliance overhead.
Compute ROI and break-even: when does building vs. buying pay off? When does migrating cloud providers save money?
Recommend top 3 cost optimizations ranked by savings impact: reserved instances, spot/preemptible, caching, CDN, right-sizing.
Flag any API with unpredictable usage-based billing — recommend spend caps and alerting.
        """.strip(),
    ),
    AgentSkill(
        name="risk-assessment",
        display_name="Risk Assessment",
        description="Score project risks by probability and impact, produce a risk register with mitigations.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Enumerate risk categories: technical (unproven tech, skill gap), schedule (scope creep, dependencies), business (market shift, regulatory).
Score each risk: probability 1-5 × impact 1-5 = exposure 1-25.
Rank by exposure; focus the report on top 10 risks (above 12 exposure).
For each top risk: mitigation strategy (what reduces probability), contingency plan (what to do when it happens), owner, trigger criteria.
Revisit risk register weekly; decay probability as risks are mitigated; escalate risks that worsen.
Flag any single risk with exposure ≥20 as CRITICAL — requires immediate action plan and executive visibility.
        """.strip(),
    ),
    AgentSkill(
        name="assumption-challenging",
        display_name="Assumption Challenging",
        description="Surface and stress-test hidden assumptions in proposals to prevent costly downstream failures.",
        category="review",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Read the proposal and list every explicit and implicit assumption (technical, business, user behavior, scale).
For each assumption, ask: What evidence supports this? What would happen if it's wrong? How would we know?
Prioritize challenges: assumptions that, if wrong, would invalidate the entire approach are CRITICAL.
Apply pre-mortem technique: imagine it's 6 months from now and this project failed catastrophically. What went wrong?
Research to validate high-risk assumptions: find data, user research, benchmarks, or expert opinions.
Output: assumption inventory with confidence level, evidence quality, and recommended validation steps.
        """.strip(),
    ),
    AgentSkill(
        name="technical-debt-assessment",
        display_name="Technical Debt Assessment",
        description="Quantify technical debt, categorize by type, and produce a prioritized paydown roadmap.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Scan codebase for debt indicators: TODO/FIXME/HACK comments, cyclomatic complexity >10, test coverage <60%, deprecated APIs.
Classify debt types: design debt (poor architecture), code debt (messy implementation), test debt (insufficient coverage), doc debt (missing docs).
Estimate cost-to-fix for each debt item in developer-days; estimate cost-of-carry (slowdown to development velocity) per quarter.
Prioritize debt paydown: items in high-churn areas with high cost-of-carry are most urgent.
Build debt paydown roadmap: 20% of each sprint capacity dedicated to tech debt, targeting highest-value items first.
Track debt level over time: debt score = sum(complexity × frequency-of-change) across modules; target downward trend.
        """.strip(),
    ),
    AgentSkill(
        name="ux-critique",
        display_name="UX Critique",
        description="Critique user experience for usability issues, cognitive load, and task completion friction.",
        category="review",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Evaluate against Nielsen's 10 Usability Heuristics: visibility, match with real world, user control, consistency, error prevention, etc.
Map critical user flows and count the number of steps, clicks, and decisions required — target fewest steps possible.
Identify cognitive load hotspots: too many choices, unclear labels, ambiguous icons, inconsistent patterns.
Assess error messages: are they specific enough to guide recovery? Do they blame the user or explain what to do?
Check information hierarchy: is the most important content above the fold and visually dominant?
Recommend specific, actionable UX improvements for each issue — include wireframe description or prototype notes.
Rate severity: blocks task completion vs. reduces efficiency vs. minor polish.
        """.strip(),
    ),
    AgentSkill(
        name="api-design-critique",
        display_name="API Design Critique",
        description="Review API contracts for consistency, idempotency, versioning, and developer experience.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Check naming consistency: are endpoints, fields, and error codes following a single consistent convention (snake_case, camelCase)?
Verify idempotency: PUT and DELETE must be idempotent; document which POST endpoints are idempotent and why.
Review versioning strategy: is breaking change management documented? Is there a deprecation timeline for old versions?
Assess error response quality: do errors include code, message, and actionable detail? Avoid generic '400 Bad Request'.
Check pagination: are large collections paginated? Is cursor-based pagination used for real-time or large datasets?
Evaluate auth design: is auth consistent across all endpoints? Are credentials ever in URLs? Are tokens short-lived?
Rate each issue (BREAKING, CRITICAL, WARNING) and provide a concrete fix with before/after example.
        """.strip(),
    ),
    AgentSkill(
        name="data-model-critique",
        display_name="Data Model Critique",
        description="Review data models for normalization issues, query performance, integrity constraints, and evolution.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Check normalization: identify data duplication, transitive dependencies, and insertion/update/deletion anomalies.
Review foreign key constraints: are all relationships enforced at the DB level, not just application level?
Inspect index coverage: list the top-10 expected queries and verify each has an appropriate index.
Check data types: are column types minimal and correct (varchar(255) vs text, int vs bigint, timestamp tz)?
Evaluate nullability: are nullable columns intentional? Null-heavy schemas often indicate design confusion.
Review for evolution: can the schema accept new entity types or new relationships without breaking existing queries?
Identify any schema anti-patterns: EAV tables, JSON blobs hiding structure, polymorphic associations without clear strategy.
        """.strip(),
    ),
    AgentSkill(
        name="scalability-pressure-test",
        display_name="Scalability Pressure Test",
        description="Analytically model system behavior at 10×/100× current load to find the first failure mode.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Establish current baseline: requests/second, DB connections, memory usage, CPU utilization at current load.
Model growth curves: what does 10× traffic look like for each component? Which resource saturates first?
Identify the limiting resource for each tier: app server (CPU/memory), DB (connections/IOPS), cache (hit rate), network (bandwidth).
Apply Little's Law: throughput = concurrency / latency. If latency grows, concurrency must increase to maintain throughput.
Recommend scaling strategy per tier: vertical (bigger instance), horizontal (more instances), caching, sharding.
Estimate cost of scaling to target load; flag if scaling cost is non-linear (exponential) and needs architectural change.
        """.strip(),
    ),
    AgentSkill(
        name="dependency-audit",
        display_name="Dependency Audit",
        description="Audit third-party dependencies for CVEs, license compatibility, maintenance status, and supply chain risk.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Run automated CVE scan (pip-audit, npm audit, Snyk) and list all vulnerabilities with CVSS score ≥7.0 as CRITICAL.
Check license compatibility: GPL contaminates proprietary code; AGPL has network clause implications. Flag conflicts.
Assess maintenance status: last commit date, open issue count, bus factor (number of active maintainers). Flag abandoned packages.
Check for typosquatting: look for packages with very similar names to popular packages — common supply chain attack.
Evaluate transitive dependency tree depth: deeply nested trees are harder to audit; prefer shallow dependency stacks.
Produce remediation plan: update (if patch available), replace (alternative without CVE), or accept risk with documented justification.
        """.strip(),
    ),
]


# ============================================================================
# REVIEW (CODE REVIEW) SKILLS  (11 skills)
# ============================================================================

REVIEW_SKILLS = [
    AgentSkill(
        name="code-review",
        display_name="Code Review",
        description="Deep code review with severity ratings (CRITICAL/WARNING/SUGGESTION/NITPICK) and concrete fixes.",
        category="review",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Read all changed files completely before writing any review comments.
Verify correctness first: does the code do what the PR description claims? Are edge cases handled?
Check for bugs: off-by-one errors, unhandled null/undefined, race conditions, incorrect type assumptions.
Review error handling: are all exceptions caught appropriately? Are errors logged with context?
Evaluate test quality: do new tests actually validate the new behavior, or are they trivially passing?
Rate each comment: CRITICAL (will cause bugs/security issues), WARNING (should fix), SUGGESTION (improves quality), NITPICK (style only).
Provide specific fixes with code snippets for all CRITICAL and WARNING items. Never just say 'fix this'.
        """.strip(),
    ),
    AgentSkill(
        name="security-audit",
        display_name="Security Audit",
        description="Scan for OWASP Top 10, injection flaws, broken auth, and secrets in code.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Check A01 (Broken Access Control): every route enforces auth and authorization checks.
Check A02 (Crypto Failures): data at rest/transit encrypted; no MD5/SHA1 for passwords; use bcrypt/argon2.
Check A03 (Injection): every DB query parameterized; no f-string SQL; HTML outputs escaped; command injection impossible.
Check A04 (Insecure Design): threat model exists; security requirements were specified, not bolted on.
Check A07 (Auth Failures): session tokens are random, invalidated on logout, HTTPOnly+Secure cookies.
Scan for secrets: search diff for regex patterns matching API keys, passwords, tokens, private keys.
Produce security report: finding, file:line reference, OWASP category, CVSS score, remediation steps.
        """.strip(),
    ),
    AgentSkill(
        name="performance-review",
        display_name="Performance Review",
        description="Identify algorithmic inefficiencies, N+1 queries, memory leaks, and hot path bottlenecks.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Identify O(n²) or worse algorithms in loops; suggest O(n log n) or O(n) alternatives.
Look for N+1 query patterns: a query inside a loop — suggest eager loading or batch fetching.
Check for memory leaks: event listeners not removed, closures capturing large objects, unbounded caches.
Review caching strategy: are expensive computations cached? Is cache invalidation logic correct?
Identify synchronous blocking calls in async code that reduce throughput.
Estimate the performance impact of each finding (latency change, throughput change, memory delta).
Provide specific refactored code examples for all HIGH impact findings.
        """.strip(),
    ),
    AgentSkill(
        name="gh-fix-ci",
        display_name="GitHub CI Fixer",
        description="Diagnose and fix failing GitHub Actions workflows with root cause analysis.",
        category="deploy",
        source="codex",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Fetch failing workflow logs; identify exact step and error message causing failure.
Classify failure type: test failure, build error, lint/type error, env config issue, flaky test, infra issue.
Check git history: what changed in the last 5 commits that could have caused this?
For test failures: determine if the test is wrong or the code is wrong. Fix the root cause, not the symptom.
For build errors: check dependency version conflicts, missing env vars, changed APIs in dependencies.
For flaky tests: add retry (max 2), increase timeout, or mark as 'known flaky' with a tracking issue.
Push fix and verify CI passes before closing. Update CI docs to prevent recurrence.
        """.strip(),
    ),
    AgentSkill(
        name="documentation-review",
        display_name="Documentation Review",
        description="Review code documentation, README, and API docs for accuracy, completeness, and clarity.",
        category="review",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Verify every public function has a docstring: purpose, parameters, return value, exceptions raised, and one usage example.
Check README: installation steps must work on a clean machine; test them mentally step by step.
Verify API docs match implementation: are all endpoints documented? Are example requests/responses still valid?
Check for outdated docs: compare docs against recent code changes — flag any doc that references deleted code or old behavior.
Review code comments: should explain WHY, not WHAT (the code explains what). Remove useless comments.
Rate documentation gaps by impact: missing auth docs > missing helper function docs.
Produce a documentation gap report with priority and estimated effort to close each gap.
        """.strip(),
    ),
    AgentSkill(
        name="dependency-review",
        display_name="Dependency Review",
        description="Review newly added or updated dependencies for necessity, security, and license compliance.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
For each added/updated dependency: is it necessary, or can existing code/stdlib do the job?
Check the package: weekly downloads (popularity proxy), last release date, GitHub stars, open security issues.
Scan for known CVEs using osv.dev or npm advisory database; block any package with CVSS ≥7.0.
Verify license is compatible with project license (e.g., GPL in proprietary project is a legal issue).
Check the package's own dependencies: a small package with 500 transitive deps is a liability.
For major version bumps: review the changelog for breaking changes; verify all breaking changes are handled.
Approve, request changes, or block the dependency addition with clear justification.
        """.strip(),
    ),
    AgentSkill(
        name="design-pattern-review",
        display_name="Design Pattern Review",
        description="Evaluate whether appropriate design patterns are used and identify over/under-engineering.",
        category="review",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Identify patterns in use: factory, strategy, observer, singleton, repository, etc.
Assess fit: is the pattern appropriate for the problem, or is it being forced where a simpler approach would work?
Flag over-engineering: abstraction layers with only one implementation, interfaces for non-polymorphic code.
Flag under-engineering: duplicated logic that should be a strategy pattern, hard-coded behavior that needs a factory.
Check SOLID principles: Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion.
Recommend specific refactoring with before/after code snippets for pattern violations with real maintenance impact.
Never recommend a pattern change unless it solves a concrete, observable problem in the current codebase.
        """.strip(),
    ),
    AgentSkill(
        name="merge-conflict-resolution",
        display_name="Merge Conflict Resolution",
        description="Analyze and resolve complex merge conflicts by understanding both sides' intent.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
For each conflict, read both sides (ours and theirs) in full context — understand the intent of each change.
Classify conflict: parallel changes to same logic, one side deletes what the other modifies, incompatible refactors.
For semantic conflicts (code merges cleanly but behavior is wrong): run tests to detect; review call sites.
Resolve with the goal of preserving all intentional changes from both sides where possible.
If resolution is ambiguous (two valid designs), flag for human review with a clear explanation of the trade-off.
After resolution, run the full test suite; any new failures indicate an incorrect merge — fix before marking complete.
Document non-trivial resolutions in the PR description for future reference.
        """.strip(),
    ),
    AgentSkill(
        name="changelog-generation",
        display_name="Changelog Generation",
        description="Auto-generate user-facing changelogs from commit history, PR titles, and release notes.",
        category="document",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Parse git log since last release tag; extract commit messages and linked PR titles.
Classify each change: Breaking Change, New Feature, Bug Fix, Performance, Security, Deprecation, Internal.
Write human-readable changelog entries: convert technical commit messages into user-benefit language.
Group by type under: '⚠️ Breaking Changes', '✨ New Features', '🐛 Bug Fixes', '⚡ Performance', '🔒 Security'.
For breaking changes: include migration instructions (what to change in dependent code).
Output CHANGELOG.md entry following Keep a Changelog format; also output a shorter release notes summary for GitHub Releases.
        """.strip(),
    ),
    AgentSkill(
        name="pr-description-review",
        display_name="PR Description Review",
        description="Review pull request descriptions for completeness, test evidence, and change justification.",
        category="review",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Check PR description has: problem statement (why this change), solution approach, testing evidence, screenshots (for UI), rollback plan.
Verify the PR is appropriately sized: >500 lines changed with no clear separation is too large — request splitting.
Check that the PR title follows conventional commit format: feat:, fix:, chore:, docs:, refactor:.
Verify linked issue/ticket exists and the PR actually closes it (not just mentions it).
Check that the PR doesn't mix unrelated changes (refactoring + new feature in one PR is a review anti-pattern).
Flag missing rollback instructions for any change that modifies DB schema or external API behavior.
        """.strip(),
    ),
    AgentSkill(
        name="code-complexity-analysis",
        display_name="Code Complexity Analysis",
        description="Measure and reduce cyclomatic complexity, cognitive complexity, and coupling metrics.",
        category="review",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Run static analysis (radon for Python, ESLint complexity for JS) to measure cyclomatic complexity per function.
Flag functions with cyclomatic complexity >10 as HIGH risk; >20 as CRITICAL for maintenance and testability.
Measure cognitive complexity: nesting depth, breaks in linear flow, recursive calls. Target <15 per function.
Calculate coupling metrics: afferent (how many modules depend on this) and efferent (how many modules this depends on) coupling.
Identify God Classes/Modules: a single class/file with >500 lines and >10 public methods is a maintainability liability.
Provide refactoring plan: extract method, extract class, introduce abstraction — prioritized by change frequency.
Track metrics over time; block PRs that increase average cyclomatic complexity above project baseline.
        """.strip(),
    ),
]


# ============================================================================
# DEVOPS SKILLS  (11 skills)
# ============================================================================

DEVOPS_SKILLS = [
    AgentSkill(
        name="docker-build",
        display_name="Docker Build",
        description="Write optimized multi-stage Dockerfiles with minimal images, health checks, and build caching.",
        category="deploy",
        source="custom",
        runtime="docker",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Use multi-stage build: 'builder' stage installs deps + compiles; 'runtime' stage copies only artifacts.
Choose minimal base: python:3.12-slim, node:22-alpine, or distroless for production images.
Order layers for cache efficiency: rarely-changing layers (base, system deps) first; frequently-changing (app code) last.
Run as non-root user; drop all Linux capabilities not needed; use read-only filesystem where possible.
Add HEALTHCHECK instruction: curl/wget to /health endpoint; retries=3, interval=30s, timeout=10s.
Use .dockerignore to exclude: .git, node_modules, __pycache__, .env, test files.
Target image size: <150MB for most apps; scan with Trivy for CVEs before pushing.
        """.strip(),
    ),
    AgentSkill(
        name="ci-cd-pipeline",
        display_name="CI/CD Pipeline",
        description="Build complete GitHub Actions / GitLab CI pipelines with test gates, build, and deploy stages.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Structure pipeline: lint → test → build → security-scan → deploy-staging → smoke-test → deploy-prod.
Configure each stage as a job with proper needs: dependencies so stages run in correct order.
Add branch protections: main branch requires 2 approvals + all CI checks green; no force push.
Implement secrets management: never hardcode; use GitHub Secrets or GitLab CI variables.
Cache dependencies: actions/cache for node_modules or pip .cache; reduces build time 50-80%.
Fail fast: run fastest checks first (lint <1min); cancel in-progress runs on new push to same branch.
Add deployment gates: environment-level approvals for production deploys; manual trigger only.
        """.strip(),
    ),
    AgentSkill(
        name="cloudflare-deploy",
        display_name="Cloudflare Deploy",
        description="Deploy Workers, Pages, and D1 databases to Cloudflare's global edge network.",
        category="deploy",
        source="codex",
        runtime=None,
        mcp_dependencies=["cloudflare"],
        autonomous=True,
        instructions="""
Configure wrangler.toml: account_id, name, compatibility_date, routes, bindings (KV, R2, D1, Service).
Implement Workers with proper error handling: catch all exceptions, return typed error responses, log to logpush.
Configure route patterns to direct traffic: specific paths to Workers, static assets to Pages.
Set up D1 database: create schema, write migrations, configure wrangler.toml bindings.
Add environment-specific configs: [env.staging] and [env.production] with appropriate resource bindings.
Deploy via wrangler in CI: 'wrangler deploy --env production' after tests pass.
Configure custom domains, SSL certificates, and firewall rules via Cloudflare API or terraform.
        """.strip(),
    ),
    AgentSkill(
        name="netlify-deploy",
        display_name="Netlify Deploy",
        description="Deploy static sites and serverless functions to Netlify with optimized build plugins.",
        category="deploy",
        source="codex",
        runtime=None,
        mcp_dependencies=["netlify"],
        autonomous=True,
        instructions="""
Configure netlify.toml: build command, publish directory, Node version, environment variables.
Set up deploy previews for every PR — each branch gets a unique URL for stakeholder review.
Add build plugins: @netlify/plugin-nextjs, image optimization, critical CSS inlining, sitemap generation.
Configure serverless functions in netlify/functions/: each file exports handler(event, context).
Set up redirects (_redirects file or netlify.toml [[redirects]]) for SPA routing and API proxying.
Add security headers (X-Frame-Options, CSP, HSTS) via netlify.toml [[headers]].
Configure split testing (A/B) by routing percentages of traffic to different branches.
        """.strip(),
    ),
    AgentSkill(
        name="monitoring-setup",
        display_name="Monitoring Setup",
        description="Configure production monitoring, alerting, distributed tracing, and SLO tracking.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=["sentry", "honeycomb"],
        autonomous=True,
        instructions="""
Instrument app with Sentry: error capture, performance monitoring, session replay. Set sample_rate=0.1 for perf tracing.
Set up Honeycomb/Datadog: trace every request with custom attributes (user_id, endpoint, db_query_count).
Define SLOs: availability 99.9% (43 min/month downtime), p99 latency <500ms, error rate <0.1%.
Create dashboards: request rate, error rate, latency percentiles (p50/p95/p99), DB connection pool, memory.
Configure alerts: PagerDuty for P1 (error rate >1% for 5min), Slack for P2/P3 (warning thresholds).
Write runbooks for each alert: symptoms, diagnosis steps, remediation commands, escalation path.
Set up synthetic monitoring: run critical user journeys every 5 minutes from 3 regions; alert on failure.
        """.strip(),
    ),
    AgentSkill(
        name="infrastructure-as-code",
        display_name="Infrastructure as Code",
        description="Write Terraform/Pulumi configs for reproducible, version-controlled cloud infrastructure.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Structure Terraform: modules for reusable components (vpc, eks, rds), environments (dev/staging/prod) as separate state files.
Use remote state backend (S3 + DynamoDB lock) to prevent concurrent modifications.
Implement least-privilege IAM: each service gets its own role with only required permissions.
Add tagging standards: all resources tagged with environment, owner, cost-center, created-by.
Create variable validation: fail early with descriptive error messages for invalid config values.
Run 'terraform plan' in CI; require human approval before 'terraform apply' on production.
Document every non-obvious resource choice with a comment explaining the design decision.
        """.strip(),
    ),
    AgentSkill(
        name="kubernetes-deployment",
        display_name="Kubernetes Deployment",
        description="Write Kubernetes manifests for scalable, self-healing deployments with proper resource limits.",
        category="deploy",
        source="custom",
        runtime="docker",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Write Deployment manifest: replicas=3, resource requests/limits (CPU: 100m/500m, memory: 128Mi/512Mi), readiness/liveness probes.
Configure HorizontalPodAutoscaler: scale on CPU >70% or custom metrics; minReplicas=2, maxReplicas=10.
Set up PodDisruptionBudget: minAvailable=1 to prevent all pods being evicted simultaneously.
Create ConfigMap for non-secret config; Secret for credentials (base64 encoded, prefer external-secrets-operator).
Add NetworkPolicy: deny all ingress by default; allow only specific inter-service communication.
Configure RollingUpdate strategy: maxUnavailable=0 (zero-downtime), maxSurge=1.
Write Helm chart wrapping all manifests for parameterized deployment across environments.
        """.strip(),
    ),
    AgentSkill(
        name="database-operations",
        display_name="Database Operations",
        description="Automate DB backups, migrations, connection pooling, and failover configuration.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Configure automated backups: daily full + hourly incremental; test restore monthly; store in separate region.
Set up connection pooling (PgBouncer for PostgreSQL, ProxySQL for MySQL): configure pool_size based on DB max_connections.
Automate schema migrations in CI: run migrations before deploying new app version; rollback on failure.
Configure primary-replica replication: route writes to primary, reads to replicas; monitor replication lag.
Set up automated failover: RDS Multi-AZ or manual scripts that promote replica within RTO (<1 min).
Monitor DB health: connection count, query latency, deadlock rate, table bloat, index hit ratio.
Schedule VACUUM ANALYZE (PostgreSQL) or OPTIMIZE TABLE (MySQL) for large, high-write tables weekly.
        """.strip(),
    ),
    AgentSkill(
        name="secret-management",
        display_name="Secret Management",
        description="Implement zero-trust secrets management with rotation, auditing, and least-privilege access.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Audit current secrets: find all hardcoded credentials in code, config files, and CI variables — remediate immediately.
Set up secrets manager: HashiCorp Vault (self-hosted) or AWS Secrets Manager / GCP Secret Manager (managed).
Implement dynamic secrets where possible: short-lived DB credentials generated per connection (Vault DB engine).
Configure secret rotation: rotate all static secrets quarterly, or automatically via Vault's rotation policies.
Implement audit logging: every secret access logged with who, what, when — alert on unexpected access patterns.
Use external-secrets-operator in Kubernetes to sync secrets manager values into K8s secrets automatically.
Integrate secrets scanning in CI: detect and block commits with exposed credentials (gitleaks, trufflehog).
        """.strip(),
    ),
    AgentSkill(
        name="disaster-recovery",
        display_name="Disaster Recovery",
        description="Design and test DR procedures to meet defined RTO/RPO targets across failure scenarios.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=False,
        instructions="""
Define RPO (max acceptable data loss) and RTO (max acceptable downtime) with business stakeholders.
Map failure scenarios: DB corruption, zone failure, region failure, DDoS, accidental deletion, ransomware.
Design recovery procedures for each scenario: runbook with exact commands, in sequential order.
Automate recovery where possible: failover scripts, backup restore scripts, DNS cutover automation.
Test DR procedures quarterly: run a full DR drill, measure actual RTO/RPO vs. targets, fix gaps.
Document DR runbooks in a location accessible even when primary systems are down (offline copy + external wiki).
Calculate and report DR readiness score: % of failure scenarios with tested and working recovery procedures.
        """.strip(),
    ),
    AgentSkill(
        name="cost-tagging-finops",
        display_name="FinOps & Cost Tagging",
        description="Implement cloud cost tagging, budgets, and anomaly alerts to control infrastructure spend.",
        category="deploy",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Define and enforce resource tagging policy: all cloud resources must have Environment, Team, Service, CostCenter tags.
Set up AWS Cost Explorer / GCP Billing or Azure Cost Management dashboards by tag dimensions.
Create budget alerts: alert at 80% of monthly budget forecast, alert at 100% spend. Separate budgets per env.
Identify top 10 cost drivers monthly; produce rightsizing report: over-provisioned instances that can be downsized.
Flag unused resources: idle load balancers, unattached EBS volumes, unused reserved instances, zombie resources.
Implement savings plans / committed use discounts for steady-state workloads (typically 30-40% savings).
Run monthly FinOps review: cost trend, waste eliminated, savings achieved, forecast for next month.
        """.strip(),
    ),
]


# ============================================================================
# AUTOMATION SKILLS  (11 skills)
# ============================================================================

AUTOMATION_SKILLS = [
    AgentSkill(
        name="web-scraping",
        display_name="Web Scraping",
        description="Build robust scrapers with JS rendering, rate limiting, proxy rotation, and structured output.",
        category="automate",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Analyze target site: static HTML vs JS-rendered; identify pagination, session requirements, anti-bot measures.
Use requests+BeautifulSoup for static; Playwright for JS-rendered content; avoid Selenium (slow, heavy).
Respect robots.txt; add 1-3s random delay between requests; rotate User-Agent from a realistic list.
Implement proxy rotation for sites with IP blocking; retry with a different proxy on 429/403.
Build resilient parsing: use CSS selectors with fallbacks; detect layout changes and alert rather than silently fail.
Store results in structured format (JSON, CSV, or DB) with dedup by URL/id; track last-seen timestamp.
Schedule scraper to run periodically; add monitoring to detect when target site structure changes.
        """.strip(),
    ),
    AgentSkill(
        name="workflow-automation",
        display_name="Workflow Automation",
        description="Design and build multi-step business workflows connecting SaaS tools via Zapier, Make, or code.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=["zapier", "make", "ifttt"],
        autonomous=True,
        instructions="""
Map the business process: identify trigger (what starts the workflow), steps (transforms/decisions), and outputs.
Choose the right tool: Zapier for simple linear flows, Make for complex branching logic, custom code for high volume.
Design for idempotency: running the workflow twice with the same input must produce the same result.
Add error handling at each step: if step N fails, decide: retry, skip, or halt and alert.
Test with synthetic data covering: normal case, empty inputs, large payloads, malformed data.
Monitor execution: log run counts, success rates, and step-level durations weekly.
Document the workflow with a flowchart diagram and a plain-English description of the business purpose.
        """.strip(),
    ),
    AgentSkill(
        name="email-automation",
        display_name="Email Automation",
        description="Build event-driven email campaigns with templates, personalization, and deliverability optimization.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design email triggers: on-signup, on-purchase, 7-day inactive, abandoned cart, password reset, payment failed.
Create HTML+plain-text templates with personalization variables: {{first_name}}, {{product_name}}, {{link}}.
Implement unsubscribe and preference center; honor unsubscribes within 10 seconds.
Configure sending infrastructure: SPF, DKIM, DMARC records; use a reputable ESP (SendGrid, Postmark, SES).
Monitor deliverability: open rate, click rate, bounce rate (hard <0.5%), spam complaint rate (<0.08%).
A/B test subject lines and CTAs; run each variant for minimum 1000 recipients before picking winner.
Implement exponential backoff for retries on transient failures; dead-letter queue for persistently failed sends.
        """.strip(),
    ),
    AgentSkill(
        name="data-pipeline",
        display_name="Data Pipeline",
        description="Build fault-tolerant ETL/ELT pipelines with incremental loading, lineage tracking, and SLA monitoring.",
        category="automate",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design pipeline stages: Extract (source data), Validate (schema/quality checks), Transform (business logic), Load (destination).
Implement incremental loading: track high-watermark (last_updated_at or offset) to process only new/changed records.
Add data quality checks: null rates, value ranges, referential integrity, record counts vs. expected.
Track data lineage: record source table, transformation applied, and destination for every data element.
Build idempotent load logic: use UPSERT or deduplication to handle re-processing without duplicates.
Monitor pipeline health: records_processed, records_failed, latency, SLA adherence (alert if >30min late).
Schedule with Airflow/Prefect/cron; implement automatic retry with backoff on transient failures.
        """.strip(),
    ),
    AgentSkill(
        name="scheduled-jobs",
        display_name="Scheduled Jobs",
        description="Build reliable cron-based jobs with idempotency, distributed locking, and alerting.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Define job purpose: what work must run periodically (cleanup, report generation, data sync, cache warm).
Implement idempotency: job can safely run multiple times; use DB locks or Redis SET NX for distributed uniqueness.
Add distributed locking to prevent concurrent execution across multiple instances (Redlock or DB advisory lock).
Build progress checkpointing: for long-running jobs, save progress so a retry can resume, not restart.
Implement dead man's switch: alert if job doesn't start within 5 minutes of its scheduled time.
Log run metadata: start_time, end_time, records_processed, status (success/failed/partial).
Test failure modes: what happens if job is killed mid-run? Verify data is left in a consistent state.
        """.strip(),
    ),
    AgentSkill(
        name="browser-automation",
        display_name="Browser Automation",
        description="Automate complex browser workflows including login, form submission, file upload, and data extraction.",
        category="automate",
        source="custom",
        runtime="node",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Use Playwright over Puppeteer for multi-browser support and better auto-waiting behavior.
Handle authentication: login once, save session storage/cookies, reuse across test runs.
Implement smart waits: waitForSelector with state:'visible'; never use fixed sleep() delays.
Handle dynamic content: wait for network idle, specific element text, or custom polling.
Automate file downloads: intercept and verify download completion; rename files by content type.
Run headless in CI; headed mode locally for debugging. Take screenshots on failure automatically.
Handle anti-bot measures gracefully: slow down actions, move mouse naturally, use real user agents.
        """.strip(),
    ),
    AgentSkill(
        name="notification-system",
        display_name="Notification System",
        description="Build multi-channel notification routing (Slack, email, webhook, SMS) with priority queuing.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Design notification schema: { channel, priority (P1-P4), title, body, metadata, ttl }.
Route by priority: P1 (incident) -> PagerDuty + SMS; P2 (warning) -> Slack; P3/P4 -> email digest.
Implement notification deduplication: same alert_key within TTL window sends only once.
Build digest/batching for low-priority notifications: collect P4 alerts for 1 hour, send as a summary.
Add delivery tracking: confirmed_at, read_at, failed_at — retry failed P1/P2 notifications with backoff.
Respect quiet hours and on-call schedules: P3/P4 don't notify outside business hours unless critical.
Provide opt-out controls per notification type; honor preferences within 30 seconds of update.
        """.strip(),
    ),
    AgentSkill(
        name="report-generation",
        display_name="Report Generation",
        description="Automate generation of PDF/HTML/Excel reports from data sources on schedule or on demand.",
        category="automate",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Define report template: sections, charts, tables, KPIs, commentary. Use Jinja2 for HTML or ReportLab/WeasyPrint for PDF.
Build data fetch layer: query DB / API with parameterized inputs (date range, entity ID, filters).
Generate charts programmatically: Matplotlib/Plotly for Python; Chart.js for web reports.
Add conditional commentary: insert pre-written text blocks based on data thresholds (e.g., 'Revenue down 15% MoM').
Deliver via email attachment, S3 link, or Slack file upload based on recipient preference.
Cache report data for 15 minutes to handle concurrent requests without DB hammering.
Archive reports in S3/GCS with versioned keys (report_2026-01-15.pdf) for audit trail access.
        """.strip(),
    ),
    AgentSkill(
        name="api-integration",
        display_name="API Integration",
        description="Build robust third-party API integrations with auth, retry, rate limiting, and webhook handling.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Study the target API docs: authentication method, rate limits, pagination style, webhook security.
Implement auth: OAuth2 with token refresh, API key rotation, or service account credentials.
Handle rate limits: parse rate-limit headers (X-RateLimit-Remaining, Retry-After); back off proactively at 80% utilization.
Build idempotent request logic: use idempotency keys for POST mutations; retry safely on timeouts/503.
Process webhooks: verify HMAC signature, respond 200 immediately, process async to prevent timeouts.
Build a circuit breaker: after 5 consecutive failures, open circuit for 60s before retrying.
Log all API calls with request_id, duration, status_code — essential for debugging 3rd-party issues.
        """.strip(),
    ),
    AgentSkill(
        name="file-processing",
        display_name="File Processing",
        description="Build batch file processing pipelines for CSV, JSON, XML, PDF, and image ingestion at scale.",
        category="automate",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Support input formats: CSV (pandas), JSON (ijson for streaming), XML (lxml), PDF (pdfplumber/PyMuPDF), images (Pillow).
Implement streaming processing for large files: never load entire file into memory; use chunked reads.
Add validation layer: verify file schema, data types, required fields, and record counts before processing.
Handle errors at record level: skip bad records, log with row number and reason, continue processing.
Output progress: log every 10,000 records processed with ETA; emit completion event when done.
Build idempotent processing: use content hash to detect already-processed files; skip duplicates.
Archive processed files to S3/GCS with processing manifest; quarantine files with >5% error rate for manual review.
        """.strip(),
    ),
    AgentSkill(
        name="self-healing-automation",
        display_name="Self-Healing Automation",
        description="Build auto-remediation scripts that detect and fix common infrastructure and application issues.",
        category="automate",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Identify top 10 recurring incidents from post-mortem history; build automated remediation for each.
Common remediations: restart crashed pods, clear disk space, invalidate stale cache, rotate log files, reset stuck queues.
Implement detection logic: monitor metrics/logs; trigger remediation when condition is met for N consecutive checks.
Add safety checks before auto-remediation: never auto-remediate during business hours without approval for destructive actions.
Log every remediation action with: what triggered it, what action was taken, outcome (success/failed), timestamp.
Implement escalation: if the same issue is remediated 3 times in 1 hour, escalate to a human — remediation is masking a deeper problem.
Test remediations in staging by deliberately triggering the failure condition monthly.
        """.strip(),
    ),
]


# ============================================================================
# RESEARCH SKILLS  (11 skills)
# ============================================================================

RESEARCH_SKILLS = [
    AgentSkill(
        name="web-research",
        display_name="Web Research",
        description="Conduct deep multi-source web research with source verification, bias detection, and synthesis.",
        category="research",
        source="custom",
        runtime=None,
        mcp_dependencies=["tavily", "exa"],
        autonomous=True,
        instructions="""
Search at least 5 distinct sources (not all from the same domain) for each research question.
Evaluate source quality: publication date, author credentials, peer review status, domain authority, citations.
Detect bias: is the source promotional, politically slanted, or commercially motivated? Flag and offset.
Synthesize findings: identify consensus (>3 sources agree), conflicting claims, and evidence gaps.
Structure output: executive_summary, key_findings[], source_quality_ratings[], confidence_level (high/medium/low).
Cite every claim with source URL, publication date, and author. Never paraphrase without attribution.
Flag information older than 12 months in fast-moving domains (AI, cloud infrastructure, security).
        """.strip(),
    ),
    AgentSkill(
        name="tech-comparison",
        display_name="Tech Comparison",
        description="Compare technologies with a structured evaluation matrix covering performance, DX, cost, and ecosystem.",
        category="research",
        source="custom",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Define 8-10 evaluation criteria relevant to the use case: performance, learning curve, community, licensing, security, etc.
Research each candidate against every criterion using official docs, benchmarks, and community sources.
Score each criterion 1-5 with evidence — never assign a score without a justification sentence.
Build a weighted scoring matrix: weight criteria by their importance to the specific use case.
Create a comparison table with scores, a pros/cons summary, and a recommended choice for the specific use case.
Validate benchmarks: check if published benchmarks are independent and representative of real-world use.
Include: when NOT to choose each option — equally important as when to choose it.
        """.strip(),
    ),
    AgentSkill(
        name="market-research",
        display_name="Market Research",
        description="Analyze market size, competitive landscape, pricing, and customer sentiment.",
        category="research",
        source="custom",
        runtime=None,
        mcp_dependencies=["exa"],
        autonomous=True,
        instructions="""
Define the market scope: TAM (total addressable), SAM (serviceable), SOM (obtainable) with methodology.
Map competitors: direct (same problem, same segment), indirect (same problem, different approach), substitutes.
For each competitor: pricing model, key features, strengths, weaknesses, customer reviews (G2/Trustpilot).
Analyze customer sentiment: review mining from public sources to identify top pain points and desired features.
Identify market trends: growth rate (CAGR), emerging segments, technology shifts, regulatory changes.
Output: market overview, competitive matrix, customer pain point ranking, opportunity size, 3 strategic recommendations.
Cite all data sources with dates; distinguish primary research from secondary estimates.
        """.strip(),
    ),
    AgentSkill(
        name="academic-research",
        display_name="Academic Research",
        description="Search scholarly databases, evaluate paper quality, and synthesize research findings.",
        category="research",
        source="anthropic",
        runtime=None,
        mcp_dependencies=["scholar-gateway", "consensus"],
        autonomous=True,
        instructions="""
Search Google Scholar, Semantic Scholar, and arXiv for papers on the topic from the last 5 years (prioritize).
Evaluate paper quality: journal impact factor, citation count (>50 citations suggests influence), methodology rigor.
Extract from each paper: hypothesis, methodology, sample size, key findings, limitations, and future work suggestions.
Identify the academic consensus: what do the majority of papers agree on? Where is there active debate?
Trace citations: find the seminal papers and the most recent papers building on them.
Synthesize: a literature review paragraph (not just a list of papers) that tells the story of what we know and don't know.
Flag papers that have been retracted or had significant corrections — check RetractionWatch if high-stakes.
        """.strip(),
    ),
    AgentSkill(
        name="data-analysis",
        display_name="Data Analysis",
        description="Analyze datasets end-to-end: EDA, cleaning, statistical testing, visualization, and insight narrative.",
        category="research",
        source="custom",
        runtime="python",
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Load data and run EDA: shape, dtypes, null rates, unique counts, value distributions for every column.
Clean data: handle nulls (impute or drop with justification), remove duplicates, normalize date formats, fix encoding.
Run descriptive statistics: mean, median, std, IQR, percentiles. Flag outliers (>3σ from mean) for investigation.
Correlation analysis: Pearson for continuous, Spearman for ordinal, Cramér's V for categorical.
Hypothesis testing: select appropriate test (t-test, chi-square, ANOVA, Mann-Whitney); verify assumptions; report p-value and effect size.
Visualize: distribution plots, scatter matrices, time series, heatmaps using matplotlib/plotly.
Narrative summary: translate statistical findings into plain English insights with business implications.
        """.strip(),
    ),
    AgentSkill(
        name="documentation",
        display_name="Documentation",
        description="Write complete technical documentation: API reference, architecture guide, setup guide, and user docs.",
        category="document",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
API Reference: every endpoint documented with: method, path, description, request schema, response schema, error codes, curl example.
Architecture Guide: system diagram (text-based Mermaid or PlantUML), component responsibilities, data flow, design decisions (ADRs).
Setup Guide: prerequisites, step-by-step install on Linux/Mac/Windows, verification commands, common errors and fixes.
User Guide: task-oriented sections ('How to X'), screenshots descriptions, FAQ from common support questions.
Update process: scan recent commits for code changes not reflected in docs; flag and update outdated content.
Style guide: keep docs at 8th-grade reading level; use active voice; no jargon without definition; examples in every section.
        """.strip(),
    ),
    AgentSkill(
        name="competitive-intelligence",
        display_name="Competitive Intelligence",
        description="Monitor competitors for product changes, pricing shifts, hiring signals, and strategic announcements.",
        category="research",
        source="custom",
        runtime=None,
        mcp_dependencies=["exa", "tavily"],
        autonomous=True,
        instructions="""
Track competitor signals: product changelog pages, job postings (new roles signal investment areas), press releases, patents.
Monitor pricing: scrape or manually check pricing pages quarterly; log changes with dates.
Analyze job postings: what skills are they hiring for? New engineering roles in an area signal upcoming product investment.
Track conference talks, blog posts, and open-source contributions to understand technical direction.
Set up keyword monitoring: alerts for competitor names + 'launch', 'announce', 'acquire', 'funding'.
Synthesize into a monthly competitive brief: key changes, strategic implications, recommended responses.
Maintain a competitor SWOT matrix — update quarterly based on new intelligence.
        """.strip(),
    ),
    AgentSkill(
        name="user-research-synthesis",
        display_name="User Research Synthesis",
        description="Synthesize user interviews, surveys, and usage data into actionable product insights.",
        category="research",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Collect inputs: interview transcripts, survey responses, support tickets, session recordings, analytics events.
Code qualitative data: identify recurring themes, pain points, jobs-to-be-done, and delight moments.
Affinity mapping: group similar observations into clusters; name each cluster with a user need statement.
Quantify qualitative findings: how many users expressed this pain? What % of sessions show this behavior?
Build user personas: for each distinct segment, define: goals, frustrations, workflows, and technical sophistication.
Produce insight report: ranked list of user needs by frequency × impact, mapped to existing/missing product features.
Recommend 5 product changes directly tied to user evidence — link each to specific user quotes.
        """.strip(),
    ),
    AgentSkill(
        name="prompt-engineering",
        display_name="Prompt Engineering",
        description="Design, test, and optimize LLM prompts for accuracy, consistency, and cost efficiency.",
        category="research",
        source="anthropic",
        runtime=None,
        mcp_dependencies=[],
        autonomous=True,
        instructions="""
Start with a clear task definition: what exactly should the model output? What format? What constraints?
Apply prompt engineering techniques: chain-of-thought, few-shot examples, role setting, output format specification.
Build an evaluation dataset: 20+ examples with ground truth answers to measure prompt performance objectively.
A/B test prompt variants: measure accuracy, hallucination rate, output consistency, and token cost per variant.
Identify failure modes: what inputs cause the prompt to fail? Build adversarial test cases.
Optimize for cost: can a shorter prompt achieve the same accuracy? Can a smaller model with a better prompt replace a larger model?
Document final prompt with: rationale for design choices, evaluation results, known limitations, and usage examples.
        """.strip(),
    ),
    AgentSkill(
        name="knowledge-graph-building",
        display_name="Knowledge Graph Building",
        description="Extract entities and relationships from documents to build a searchable knowledge graph.",
        category="research",
        source="custom",
        runtime="python",
        mcp_dependencies=["obsidian"],
        autonomous=True,
        instructions="""
Define entity types relevant to the domain (e.g., Person, Organization, Technology, Event, Concept).
Extract entities from text using NER (spaCy) or LLM-based extraction with structured output.
Identify relationships between entities: [Entity A] --[RELATIONSHIP]--> [Entity B].
Resolve entity coreference: 'Microsoft', 'MSFT', and 'the company' all refer to the same entity — merge.
Store graph in Obsidian as interconnected notes (entity note per node, [[links]] as edges) for human browsing.
Build a query interface: given a starting entity, traverse N hops and return related entities with relationship paths.
Visualize the graph as a Mermaid diagram for documentation and reasoning.
        """.strip(),
    ),
    AgentSkill(
        name="trend-forecasting",
        display_name="Trend Forecasting",
        description="Identify emerging trends from data signals and produce forward-looking analysis with confidence intervals.",
        category="research",
        source="custom",
        runtime="python",
        mcp_dependencies=["tavily", "exa"],
        autonomous=True,
        instructions="""
Collect trend signals: search trends (Google Trends), paper publication rates, GitHub repo growth, hiring demand, VC investment flows.
Apply time-series analysis: decompose into trend, seasonality, and noise components (STL decomposition).
Extrapolate trends with confidence intervals: use ARIMA or Prophet for quantitative signals, qualitative narrative for qualitative ones.
Validate leading indicators: identify signals that historically preceded this trend by 6-18 months.
Rate forecast confidence: HIGH (multiple converging signals, historical precedent), MEDIUM (2+ signals), LOW (single signal, no precedent).
Present as: trend summary, evidence base, 6-month / 12-month / 24-month outlook, strategic implications.
Flag black swan scenarios: low-probability, high-impact events that could disrupt the forecast entirely.
        """.strip(),
    ),
]


# ============================================================================
# MASTER SKILLS DICTIONARY
# ============================================================================

AGENT_SKILLS = {
    "orchestrator": ORCHESTRATOR_SKILLS,
    "pm":           PM_SKILLS,
    "dev":          DEV_SKILLS,
    "qa":           QA_SKILLS,
    "critic":       CRITIC_SKILLS,
    "review":       REVIEW_SKILLS,
    "devops":       DEVOPS_SKILLS,
    "automation":   AUTOMATION_SKILLS,
    "research":     RESEARCH_SKILLS,
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_skills_for_agent(role: str) -> list[AgentSkill]:
    """Get all skills available to a specific agent role."""
    return AGENT_SKILLS.get(role, [])


def get_autonomous_skills(role: str) -> list[AgentSkill]:
    """Get skills an agent can invoke autonomously without user approval."""
    return [s for s in get_skills_for_agent(role) if s.autonomous]


def get_skills_by_runtime(runtime: str) -> list[AgentSkill]:
    """Get all skills requiring a specific runtime across all agents."""
    return [s for skills in AGENT_SKILLS.values() for s in skills if s.runtime == runtime]


def get_skills_by_category(category: str) -> list[AgentSkill]:
    """Get all skills in a specific category across all agents."""
    return [s for skills in AGENT_SKILLS.values() for s in skills if s.category == category]


def get_skills_by_mcp_dependency(mcp_name: str) -> list[AgentSkill]:
    """Get all skills that depend on a specific MCP server."""
    return [s for skills in AGENT_SKILLS.values() for s in skills if mcp_name in s.mcp_dependencies]


def all_agent_roles() -> list[str]:
    """Get list of all agent roles in the system."""
    return list(AGENT_SKILLS.keys())


def skill_summary(role: str) -> dict:
    """Get a summary of skills for an agent role."""
    skills = get_skills_for_agent(role)
    categories: dict[str, int] = {}
    mcps: set[str] = set()
    for skill in skills:
        categories[skill.category] = categories.get(skill.category, 0) + 1
        mcps.update(skill.mcp_dependencies)
    return {
        "role": role,
        "total_skills": len(skills),
        "autonomous_skills": len(get_autonomous_skills(role)),
        "by_category": categories,
        "mcp_dependencies": sorted(mcps),
    }


def total_skill_count() -> int:
    """Return total number of skills across all agents."""
    return sum(len(s) for s in AGENT_SKILLS.values())
