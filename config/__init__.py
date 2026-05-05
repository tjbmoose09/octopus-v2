"""Octopus V2 Configuration Package

Exports all configuration modules for the multi-agent system:
- settings: Agent roles, system prompts, DO's/DON'Ts
- providers: LM Studio, Claude API, OpenAI-compatible provider configs
- mcp_servers: MCP server definitions and agent routing
- skills: Agent skill definitions adapted from Codex + Anthropic catalogs
- memory: Obsidian MCP memory integration
"""

from .settings import (
    AGENT_ROLES,
    SYSTEM_PROMPTS,
    ORCHESTRATOR_MODEL,
    DEFAULT_MODEL_ASSIGNMENTS,
    AGENT_DOS,
    AGENT_DONTS,
    HOST,
    PORT,
    DB_PATH,
    PROVIDER_MODE,
)

from .providers import (
    ProviderType,
    ProviderConfig,
    get_all_providers,
    get_agent_provider,
    DEFAULT_AGENT_PROVIDERS,
)

from .mcp_servers import (
    MCPServerConfig,
    MCP_SERVERS,
    MCP_AGENT_ROUTING,
    get_servers_by_category,
    get_enabled_servers,
    get_core_servers,
    get_servers_for_agent,
)

from .skills import (
    AgentSkill,
    AGENT_SKILLS,
    get_skills_for_agent,
    get_autonomous_skills,
    get_skills_by_runtime,
)

from .memory import (
    MemoryType,
    MemoryConfig,
    MEMORY_OPERATIONS,
    AGENT_MEMORY_ACCESS,
    get_memory_config,
    get_agent_memory_access,
    get_vault_path,
)
