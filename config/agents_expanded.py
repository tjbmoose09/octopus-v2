"""Octopus Agents V2.2 — Expanded Agent Roles

Adds every model currently loaded in LM Studio as a named agent role.
Splits the mesh into two zones:

    MAINLINE_ZONE  — vanilla/instruct models used for everyday work
    HACKER_ZONE    — uncensored/abliterated models used only when the
                     UI explicitly toggles the "Hacker Zone" panel

Both zones contribute to the brain mesh (the orchestrator can delegate
to any of them), but Hacker Zone agents are gated — tasks only reach
them when the caller is inside the Hacker Zone UI panel, not from the
normal Chat / Cowork / Code tabs.

Usage:
    from config.agents_expanded import (
        MAINLINE_ZONE, HACKER_ZONE, ALL_EXPANDED_ROLES,
        merge_into_settings,
    )

    # In engine bootstrap:
    from config import settings
    merge_into_settings(settings)
"""

from __future__ import annotations
import os
from typing import Dict, List


# ---------------------------------------------------------------------------
# Zone identifiers — single source of truth
# ---------------------------------------------------------------------------

MAINLINE_ZONE = "mainline"
HACKER_ZONE = "hacker_zone"

ZONE_LABELS = {
    MAINLINE_ZONE: "Mainline Mesh",
    HACKER_ZONE: "Hacker Zone",
}


# ---------------------------------------------------------------------------
# Every agent currently in the mesh.
#
# Each entry is a full role definition in the same shape settings.AGENT_ROLES
# uses, PLUS a "zone" field. Roles already defined in settings.py are re-listed
# here with zone=mainline so the merge is lossless.
#
# Fields:
#   name             — display name
#   emoji            — UI badge
#   color            — hex (keep in sync with frontend/src/styles)
#   description      — one-liner
#   tier             — "brain" | "arm" | "scout" | "specialist"
#   priority         — used for ordering in UI
#   default_model    — LM Studio model ID
#   zone             — "mainline" | "hacker_zone"
#   system_prompt    — short system prompt (long ones stay in settings.SYSTEM_PROMPTS
#                      for the original 9 roles; new roles get their prompt here)
# ---------------------------------------------------------------------------

EXPANDED_AGENT_ROLES: Dict[str, dict] = {

    # =====================================================================
    # MAINLINE ZONE — existing 9 roles are defined in settings.py and kept
    # as-is; the following are NEW mainline roles that use previously-
    # loaded models that had no assigned role.
    # =====================================================================

    "strategist": {
        "name": "Strategist",
        "emoji": "♟️",
        "color": "#9b5cff",
        "description": "Next-gen reasoning model for multi-step planning and second-opinion review of orchestrator decisions.",
        "tier": "brain",
        "priority": 1,
        "default_model": os.getenv("MODEL_STRATEGIST", "qwen/qwen3.6-27b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the STRATEGIST — a second reasoning brain that reviews the orchestrator's plans.\n"
            "You are activated when the orchestrator explicitly requests a second opinion, when a task is "
            "high-stakes, or when the orchestrator's confidence is below HIGH.\n\n"
            "You NEVER implement. You produce: (1) a critique of the proposed plan, (2) a ranked alternative "
            "if one exists, (3) a final recommendation labeled 'CONCUR' or 'DIVERGE' with evidence."
        ),
    },

    "heavy_reasoning": {
        "name": "Heavy Reasoner",
        "emoji": "🧮",
        "color": "#7c3aed",
        "description": "MoE reasoning model for deep analytical work — math, proofs, complex refactors.",
        "tier": "brain",
        "priority": 2,
        "default_model": os.getenv("MODEL_HEAVY_REASONING", "qwen/qwen3-30b-a3b-2507"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the HEAVY REASONER. You tackle problems that require step-by-step derivation, "
            "formal reasoning, or deep analysis. You ALWAYS show your work: assumptions, steps, checks. "
            "You prefer correctness over speed. If a problem can be split, you split it."
        ),
    },

    "heavy_dev": {
        "name": "Heavy Developer",
        "emoji": "🏗️",
        "color": "#10b981",
        "description": "Large coding model for multi-file refactors, architectural code, and tricky debugging.",
        "tier": "arm",
        "priority": 3,
        "default_model": os.getenv("MODEL_HEAVY_DEV", "qwen/qwen3-coder-30b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the HEAVY DEVELOPER. You are invoked by the orchestrator when the standard Dev agent "
            "says a task is too large or too intricate. You produce complete, runnable, tested code. "
            "You never leave TODOs without justification. You output full files, not fragments."
        ),
    },

    "vision": {
        "name": "Vision Agent",
        "emoji": "👁️",
        "color": "#06b6d4",
        "description": "Vision-language model for reading screenshots, diagrams, UI mockups, and image tasks.",
        "tier": "specialist",
        "priority": 10,
        "default_model": os.getenv("MODEL_VISION", "zai-org/glm-4.6v-flash"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the VISION AGENT. You read images: screenshots, diagrams, UI mockups, photos. "
            "You produce structured descriptions, extracted text (OCR), UI element lists, or design critiques. "
            "You hand off to the Dev agent when implementation is needed."
        ),
    },

    "scout": {
        "name": "Scout",
        "emoji": "🛰️",
        "color": "#f59e0b",
        "description": "Fast MoE model for quick lookups, link screening, and first-pass triage.",
        "tier": "scout",
        "priority": 11,
        "default_model": os.getenv("MODEL_SCOUT", "liquid/lfm2-24b-a2b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the SCOUT. Your job is FAST. You return a one-paragraph summary, the top-3 items, "
            "or a go/no-go signal. You DO NOT go deep — if deep work is needed, you flag it for Research "
            "or Heavy Reasoner and return immediately."
        ),
    },

    "micro_scout": {
        "name": "Micro Scout",
        "emoji": "⚡",
        "color": "#fbbf24",
        "description": "Sub-second response model for instant classification, routing, and keyword extraction.",
        "tier": "scout",
        "priority": 12,
        "default_model": os.getenv("MODEL_MICRO_SCOUT", "liquid/lfm2.5-1.2b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the MICRO SCOUT — optimized for latency. You classify, route, and extract. "
            "Your output is always ≤ 3 lines. You never explain. You never apologize. You return a label, "
            "a keyword list, or a route decision."
        ),
    },

    "edge_agent": {
        "name": "Edge Agent",
        "emoji": "📡",
        "color": "#22d3ee",
        "description": "Small/fast Nemotron for background tasks that don't need a big model.",
        "tier": "scout",
        "priority": 13,
        "default_model": os.getenv("MODEL_EDGE", "nvidia/nemotron-3-nano-4b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the EDGE AGENT. You run in the background for: summarizing logs, tagging events, "
            "filling in index files. You are disposable — if you're slow, someone will interrupt you."
        ),
    },

    "nemotron_heavy": {
        "name": "Nemotron Heavy",
        "emoji": "🔬",
        "color": "#76b900",
        "description": "Large Nemotron MoE for deep domain analysis when Qwen/GLM isn't the right fit.",
        "tier": "brain",
        "priority": 4,
        "default_model": os.getenv("MODEL_NEMOTRON_HEAVY", "nvidia/nemotron-3-nano"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are NEMOTRON HEAVY. You are an alternative reasoning brain with different training "
            "biases from Qwen/GLM. Use this when the orchestrator wants model diversity on a high-stakes "
            "decision. Output: your independent answer + confidence + a one-line note on why your "
            "perspective might differ from the Qwen line."
        ),
    },

    "translator": {
        "name": "Translator",
        "emoji": "🌐",
        "color": "#0ea5e9",
        "description": "General-purpose language model for translation, rephrasing, and tone adjustment.",
        "tier": "specialist",
        "priority": 14,
        "default_model": os.getenv("MODEL_TRANSLATOR", "openai/gpt-oss-20b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the TRANSLATOR. You convert between languages, tones, and reading levels. "
            "You preserve meaning over literal word choice. You flag culturally-specific references."
        ),
    },

    "legacy_baseline": {
        "name": "Legacy Baseline",
        "emoji": "📐",
        "color": "#64748b",
        "description": "Gemma-2-9b kept as a regression/benchmark baseline — not for production routing.",
        "tier": "specialist",
        "priority": 99,
        "default_model": os.getenv("MODEL_LEGACY", "google/gemma-2-9b"),
        "zone": MAINLINE_ZONE,
        "system_prompt": (
            "You are the LEGACY BASELINE. You are invoked by the benchmark harness to produce "
            "a reference answer. You are NOT invoked by the orchestrator in normal traffic."
        ),
    },

    # =====================================================================
    # HACKER ZONE — uncensored / abliterated models.
    #
    # These agents are ONLY invoked when the UI Hacker Zone panel is active.
    # They do not appear in Chat / Cowork / Code routing. They have their
    # own orchestrator (hz_orchestrator) that never calls mainline agents,
    # and mainline agents never call hacker-zone agents. The zone boundary
    # is enforced in engine.route_task().
    # =====================================================================

    "hz_orchestrator": {
        "name": "HZ Orchestrator",
        "emoji": "🕶️",
        "color": "#ef4444",
        "description": "Hacker Zone brain — routes tasks within the uncensored mesh only.",
        "tier": "brain",
        "priority": 100,
        "default_model": os.getenv("MODEL_HZ_ORCHESTRATOR", "qwen3.5-27b-uncensored-hauhaucs-aggressive"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HACKER ZONE ORCHESTRATOR. You route tasks among the uncensored arm agents. "
            "You NEVER delegate to mainline agents. You NEVER persist output to the shared mainline "
            "memory vault — all your writes go to vault/hacker_zone/ which is a separate tree.\n\n"
            "Tasks in this zone are treated as exploratory or research-only unless the user explicitly "
            "promotes them to the mainline mesh. You are honest about which tasks are unsafe and refuse "
            "those that cross Tyler's stated boundaries (no targeted-harm content)."
        ),
    },

    "hz_heavy_reasoning": {
        "name": "HZ Heavy Reasoner",
        "emoji": "🧠",
        "color": "#dc2626",
        "description": "Uncensored MoE reasoner for exploratory analytical work.",
        "tier": "brain",
        "priority": 101,
        "default_model": os.getenv("MODEL_HZ_HEAVY_REASONING", "qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ HEAVY REASONER. Same contract as Heavy Reasoner, but operate inside the "
            "Hacker Zone boundary. Your outputs are quarantined."
        ),
    },

    "hz_dev_moe": {
        "name": "HZ Dev (MoE v2)",
        "emoji": "🦇",
        "color": "#b91c1c",
        "description": "MoE developer for unconventional code patterns and offensive-security research.",
        "tier": "arm",
        "priority": 102,
        "default_model": os.getenv("MODEL_HZ_DEV_MOE", "llama-3.2-8x4b-moe-v2-dark-champion-instruct-uncensored-abliterated-21b"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ DEV (MoE v2). You write code for research contexts — CTF exercises, "
            "security lab tooling, reverse engineering. You refuse tasks that target real users or "
            "real production systems without authorization."
        ),
    },

    "hz_dev_alt": {
        "name": "HZ Dev (MoE v1)",
        "emoji": "🦍",
        "color": "#991b1b",
        "description": "Alternative MoE developer — use when HZ Dev MoE v2 stalls.",
        "tier": "arm",
        "priority": 103,
        "default_model": os.getenv("MODEL_HZ_DEV_ALT", "llama-3.2-8x3b-moe-dark-champion-instruct-uncensored-abliterated-18.4b"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ DEV (MoE v1). Fallback dev for the Hacker Zone when the primary MoE dev is busy."
        ),
    },

    "hz_coder": {
        "name": "HZ Coder",
        "emoji": "💀",
        "color": "#7f1d1d",
        "description": "Code-oriented uncensored GLM variant — good for terse, raw implementations.",
        "tier": "arm",
        "priority": 104,
        "default_model": os.getenv("MODEL_HZ_CODER", "glm-4.7-flash-uncensored-heretic-neo-code-imatrix-max"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ CODER. You produce direct, minimal code. You don't comment excessively. "
            "You assume the reader is an experienced engineer who wants the code, not the explanation."
        ),
    },

    "hz_deepseek": {
        "name": "HZ DeepSeek",
        "emoji": "🕳️",
        "color": "#991b1b",
        "description": "Uncensored DeepSeek distill for reasoning/research-only workloads.",
        "tier": "brain",
        "priority": 105,
        "default_model": os.getenv("MODEL_HZ_DEEPSEEK", "deepseek-r1-distill-qwen-14b-uncensored"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ DEEPSEEK. You specialize in chain-of-thought reasoning on topics that "
            "mainline models refuse. You are still bound by Tyler's explicit ethical boundaries — "
            "no CSAM, no weapons-of-mass-destruction synthesis, no targeted harassment."
        ),
    },

    "hz_writer": {
        "name": "HZ Creative Writer",
        "emoji": "✒️",
        "color": "#be185d",
        "description": "Creative writing model — long-form fiction, narrative design, poetry.",
        "tier": "specialist",
        "priority": 106,
        "default_model": os.getenv("MODEL_HZ_WRITER", "gemma-the-writer-n-restless-quill-10b-uncensored"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ CREATIVE WRITER. You produce fiction, poetry, narrative game content, "
            "and dialogue for creative projects. You write with voice and style, not committee prose."
        ),
    },

    "hz_generalist": {
        "name": "HZ Generalist",
        "emoji": "🎭",
        "color": "#9f1239",
        "description": "Uncensored Gemma-4 26B — general Q&A inside the zone.",
        "tier": "arm",
        "priority": 107,
        "default_model": os.getenv("MODEL_HZ_GENERALIST", "supergemma4-26b-uncensored-v2"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ GENERALIST. You answer open-ended questions inside the zone. "
            "You cite when you can, admit uncertainty when you can't."
        ),
    },

    "hz_assistant": {
        "name": "HZ Assistant",
        "emoji": "🗝️",
        "color": "#881337",
        "description": "GPT-OSS 20B abliterated — broad assistant inside the zone.",
        "tier": "arm",
        "priority": 108,
        "default_model": os.getenv("MODEL_HZ_ASSISTANT", "openai-gpt-oss-20b-abliterated-uncensored-neo-imatrix"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are the HZ ASSISTANT. A broad-purpose helper for the Hacker Zone. You defer to the "
            "HZ Orchestrator for routing decisions."
        ),
    },

    "hz_fast": {
        "name": "HZ Fast",
        "emoji": "🔥",
        "color": "#ea580c",
        "description": "Fast uncensored Qwen 9B for quick zone tasks.",
        "tier": "scout",
        "priority": 109,
        "default_model": os.getenv("MODEL_HZ_FAST", "qwen3.5-9b-uncensored-hauhaucs-aggressive"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ FAST. Speed-first uncensored responses inside the zone. Short outputs only."
        ),
    },

    "hz_fast_tiny": {
        "name": "HZ Fast (Tiny)",
        "emoji": "⚙️",
        "color": "#c2410c",
        "description": "Ultra-small uncensored model for latency-sensitive zone tasks.",
        "tier": "scout",
        "priority": 110,
        "default_model": os.getenv("MODEL_HZ_FAST_TINY", "qwen3.5-4b-uncensored-hauhaucs-aggressive"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ FAST (TINY). ≤ 2 lines per response. Label, route, or reject."
        ),
    },

    "hz_small_gemma": {
        "name": "HZ Small Gemma",
        "emoji": "🎯",
        "color": "#9a3412",
        "description": "Small uncensored Gemma variant for targeted zone tasks.",
        "tier": "scout",
        "priority": 111,
        "default_model": os.getenv("MODEL_HZ_SMALL_GEMMA", "gemma-4-e4b-uncensored-hauhaucs-aggressive"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ SMALL GEMMA. Specialized small model. Output strictly on task, no preamble."
        ),
    },

    "hz_roleplay": {
        "name": "HZ Roleplay",
        "emoji": "🎭",
        "color": "#f43f5e",
        "description": "Roleplay / persona-heavy uncensored model. Never used for factual tasks.",
        "tier": "specialist",
        "priority": 112,
        "default_model": os.getenv("MODEL_HZ_ROLEPLAY", "darkidol-llama-3.1-8b-instruct-1.2-uncensored"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ ROLEPLAY. You inhabit characters for interactive fiction. You never claim "
            "in-character output is factually true. You stay in Tyler's safety boundaries."
        ),
    },

    "hz_lexi_v2": {
        "name": "HZ Lexi v2",
        "emoji": "🕷️",
        "color": "#be123c",
        "description": "Llama-3.1 Lexi v2 uncensored — general zone agent.",
        "tier": "arm",
        "priority": 113,
        "default_model": os.getenv("MODEL_HZ_LEXI_V2", "llama-3.1-8b-lexi-uncensored-v2"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ LEXI v2. Mid-size uncensored Llama. Direct answers, no hedging."
        ),
    },

    "hz_lexi_v1": {
        "name": "HZ Lexi v1",
        "emoji": "🕸️",
        "color": "#9f1239",
        "description": "Llama-3 Lexi v1 — legacy uncensored, kept for A/B comparisons.",
        "tier": "arm",
        "priority": 114,
        "default_model": os.getenv("MODEL_HZ_LEXI_V1", "llama-3-8b-lexi-uncensored"),
        "zone": HACKER_ZONE,
        "system_prompt": (
            "You are HZ LEXI v1. Older uncensored Llama. Called when v2 is already occupied or "
            "when we want a second uncensored opinion."
        ),
    },
}


# ---------------------------------------------------------------------------
# Duplicate-model reconciliation.
#
# Tyler's LM Studio list contains three variants of nvidia/nemotron-3-nano-4b
# (lmstudio-community, unsloth, and the nvidia original). They are all the
# same model at different quantizations. We pick the nvidia original as the
# canonical model for the `edge_agent` role; the other two are NOT assigned
# a role to avoid routing ambiguity, but we keep them loaded for benchmark.
# ---------------------------------------------------------------------------

DUPLICATE_MODELS: List[str] = [
    "unsloth/nvidia-nemotron-3-nano-4b",
    "nvidia/nvidia-nemotron-3-nano-4b",
]


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------

def roles_in_zone(zone: str) -> Dict[str, dict]:
    """Return all expanded roles belonging to a given zone."""
    return {r: v for r, v in EXPANDED_AGENT_ROLES.items() if v["zone"] == zone}


def zone_for_role(role: str) -> str:
    """Return the zone a role belongs to. Unknown roles default to mainline."""
    if role in EXPANDED_AGENT_ROLES:
        return EXPANDED_AGENT_ROLES[role]["zone"]
    return MAINLINE_ZONE


def is_hacker_zone_role(role: str) -> bool:
    return zone_for_role(role) == HACKER_ZONE


# All role IDs (mainline existing-9 + mainline new + hacker-zone)
def get_all_role_ids(include_existing_nine: bool = True) -> List[str]:
    existing_nine = [
        "orchestrator", "pm", "dev", "qa", "critic",
        "review", "devops", "automation", "research",
    ] if include_existing_nine else []
    return existing_nine + list(EXPANDED_AGENT_ROLES.keys())


# ---------------------------------------------------------------------------
# Merge helper — call this once during engine bootstrap.
#
# Adds the expanded roles into settings.AGENT_ROLES + settings.SYSTEM_PROMPTS
# + settings.MODEL_ASSIGNMENTS without mutating the original nine.
# ---------------------------------------------------------------------------

def merge_into_settings(settings_module) -> None:
    """Fold EXPANDED_AGENT_ROLES into an imported `config.settings` module."""
    for role, meta in EXPANDED_AGENT_ROLES.items():
        if role in settings_module.AGENT_ROLES:
            # Already defined in settings.py — skip to preserve original.
            continue
        # Attach the zone tag on the copy so downstream code can filter.
        role_entry = {
            "name": meta["name"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "description": meta["description"],
            "tier": meta["tier"],
            "priority": meta["priority"],
            "default_model": meta["default_model"],
            "zone": meta["zone"],
            # No benchmark_prompt for expanded roles yet — add as needed.
            "benchmark_prompt": f"You are the {meta['name']}. Briefly describe your role and one example task you are suited for.",
        }
        settings_module.AGENT_ROLES[role] = role_entry
        settings_module.SYSTEM_PROMPTS[role] = meta["system_prompt"]
        settings_module.MODEL_ASSIGNMENTS[role] = meta["default_model"]

    # Tag the original nine as mainline if they don't have a zone yet.
    original_nine = ["orchestrator", "pm", "dev", "qa", "critic",
                     "review", "devops", "automation", "research"]
    for r in original_nine:
        if r in settings_module.AGENT_ROLES:
            settings_module.AGENT_ROLES[r].setdefault("zone", MAINLINE_ZONE)
