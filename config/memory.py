"""Octopus Agents V2 — Memory Configuration

Integrates Obsidian MCP server for short-term and long-term agent memory.
The Obsidian vault acts as persistent storage for:
  - Chat histories per agent and per task
  - Task context and decisions made
  - Long-term knowledge base (patterns, solutions, user preferences)
  - Agent state snapshots for recovery
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class MemoryType(Enum):
    SHORT_TERM = "short_term"    # Current task context, expires after task completion
    LONG_TERM = "long_term"      # Persistent knowledge, patterns, solutions
    EPISODIC = "episodic"        # Chat histories, interaction logs
    WORKING = "working"          # Active task state, shared between agents


@dataclass
class MemoryConfig:
    """Obsidian MCP memory configuration."""
    obsidian_url: str = os.getenv("OBSIDIAN_URL", "http://localhost:27124")
    obsidian_api_key: str = os.getenv("OBSIDIAN_API_KEY", "")
    vault_name: str = os.getenv("OBSIDIAN_VAULT", "OctopusMemory")

    # Vault folder structure for organized memory
    folders: dict = field(default_factory=lambda: {
        "short_term": "Memory/ShortTerm",
        "long_term": "Memory/LongTerm",
        "episodic": "Memory/ChatHistory",
        "working": "Memory/WorkingState",
        "agents": "Agents",           # Per-agent notes/state
        "tasks": "Tasks",             # Per-task context
        "knowledge": "Knowledge",      # Learned patterns and solutions
        "user_prefs": "UserPreferences",  # User preferences and feedback
        "daily_logs": "Logs/Daily",   # Daily notes: system, pipeline, conversations
        "chat_logs": "chat_logs",     # Chat logs for user interaction history
    })

    # Memory retention policies
    short_term_ttl_hours: int = 24      # Short-term memories expire after 24h
    max_working_memory_items: int = 50   # Cap active working memory
    auto_summarize_threshold: int = 100  # Auto-summarize after N messages in a chat


@dataclass
class AgentMemoryState:
    """Tracks what an agent remembers for a given context."""
    agent_role: str
    current_task_id: Optional[str] = None
    short_term: list = field(default_factory=list)   # Recent context items
    working_context: dict = field(default_factory=dict)  # Active task data


# Memory operations the agents can perform via Obsidian MCP
MEMORY_OPERATIONS = {
    "save_context": {
        "description": "Save current task context to short-term memory",
        "vault_path": "Memory/ShortTerm/{task_id}.md",
        "auto": True,  # Happens automatically on task start
    },
    "recall_context": {
        "description": "Recall context from a previous task or conversation",
        "vault_path": "Memory/ShortTerm/{query}.md",
        "auto": False,
    },
    "save_solution": {
        "description": "Save a successful solution pattern to long-term memory",
        "vault_path": "Memory/LongTerm/Solutions/{category}/{title}.md",
        "auto": True,  # Auto-save on task completion
    },
    "save_chat_history": {
        "description": "Persist chat messages to episodic memory",
        "vault_path": "Memory/ChatHistory/{agent_role}/{date}_{task_id}.md",
        "auto": True,
    },
    "update_working_state": {
        "description": "Update shared working memory that other agents can read",
        "vault_path": "Memory/WorkingState/{task_id}_state.md",
        "auto": True,
    },
    "search_knowledge": {
        "description": "Search long-term knowledge base for relevant patterns",
        "vault_path": "Knowledge/**/*.md",
        "auto": False,
    },
    "save_user_preference": {
        "description": "Record a user preference or feedback for future reference",
        "vault_path": "UserPreferences/{category}.md",
        "auto": False,
    },
    "agent_checkpoint": {
        "description": "Save agent state for crash recovery",
        "vault_path": "Agents/{agent_role}/checkpoint_{timestamp}.md",
        "auto": True,
    },
}

# Which memory types each agent role can access
AGENT_MEMORY_ACCESS = {
    "orchestrator": [MemoryType.SHORT_TERM, MemoryType.LONG_TERM, MemoryType.EPISODIC, MemoryType.WORKING],
    "pm":           [MemoryType.SHORT_TERM, MemoryType.WORKING, MemoryType.EPISODIC],
    "dev":          [MemoryType.SHORT_TERM, MemoryType.LONG_TERM, MemoryType.WORKING],
    "qa":           [MemoryType.SHORT_TERM, MemoryType.WORKING],
    "critic":       [MemoryType.SHORT_TERM, MemoryType.LONG_TERM],
    "review":       [MemoryType.SHORT_TERM, MemoryType.LONG_TERM],
    "devops":       [MemoryType.SHORT_TERM, MemoryType.WORKING],
    "automation":   [MemoryType.SHORT_TERM, MemoryType.WORKING],
    "research":     [MemoryType.SHORT_TERM, MemoryType.LONG_TERM, MemoryType.EPISODIC],
}


def get_memory_config() -> MemoryConfig:
    """Get the memory configuration."""
    return MemoryConfig()


def get_agent_memory_access(role: str) -> list[MemoryType]:
    """Get which memory types an agent can access."""
    return AGENT_MEMORY_ACCESS.get(role, [MemoryType.SHORT_TERM])


def get_vault_path(operation: str, **kwargs) -> str:
    """Build the vault path for a memory operation, filling in template vars."""
    op = MEMORY_OPERATIONS.get(operation)
    if not op:
        raise ValueError(f"Unknown memory operation: {operation}")
    return op["vault_path"].format(**kwargs)
