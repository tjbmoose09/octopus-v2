"""MCP Server Configuration for Octopus V2 Agent System

This module defines all available MCP (Model Context Protocol) server connections
for the multi-agent orchestration system. Servers are organized by category and
can be routed to specific agent roles.

Categories:
- CORE: Essential services (linear, notion, slack, supabase, hugging-face, vercel)
- DEV_TOOLS: Development utilities (sentry, postman, context7, figma, cloudflare, etc.)
- AUTOMATION: Workflow automation (zapier, make, ifttt, exa)
- RUNTIMES: Code execution environments (node, python, docker)
- CODE_BUILDERS: Code generation tools (gamma, magic-patterns, canva, etc.)
- RESEARCH: Research and information (tavily, scholar-gateway, consensus)
- MEMORY: Agent memory systems (obsidian)
- PRODUCTIVITY: Project management (clickup, airtable, miro, asana)
- PAYMENTS: Payment processors (stripe, paypal)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection.

    Attributes:
        name: Unique identifier for the server (e.g., 'linear', 'notion')
        description: Human-readable description of what this server provides
        transport: Protocol type ('http', 'sse', 'streamable-http', 'stdio')
        category: Category this server belongs to
        enabled: Whether this server is enabled by default
        requires_auth: Whether this server requires authentication
        url: HTTP endpoint for remote servers (None for local/spawned servers)
        command: Human-readable CLI command for setup
        spawn_command: Command to spawn local MCP servers (for transport='stdio')
        auth_url: Optional URL for authentication flow
        special_config: Optional dict for server-specific configuration
    """

    name: str
    description: str
    transport: str  # "http", "sse", "streamable-http", "stdio"
    category: str
    command: str
    enabled: bool = True
    requires_auth: bool = False
    url: Optional[str] = None
    auth_url: Optional[str] = None
    spawn_command: Optional[str] = None
    special_config: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration consistency."""
        if self.transport == "stdio" and not self.spawn_command:
            raise ValueError(f"Server {self.name} with stdio transport must have spawn_command")
        if self.transport != "stdio" and not self.url:
            raise ValueError(f"Server {self.name} with {self.transport} transport must have url")


# CORE SERVERS - Priority integration (wire these first)
CORE_SERVERS = [
    MCPServerConfig(
        name="linear",
        description="Issue tracking and project management",
        transport="http",
        url="https://mcp.linear.app/mcp",
        category="CORE",
        command="npx @anthropic/mcp-server-linear",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="notion",
        description="Documentation and workspace management",
        transport="http",
        url="https://mcp.notion.com/mcp",
        category="CORE",
        command="npx @anthropic/mcp-server-notion",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="slack",
        description="Team messaging and communication",
        transport="http",
        url="https://mcp.slack.com/mcp",
        category="CORE",
        command="npx @anthropic/mcp-server-slack",
        requires_auth=True,
        special_config={
            "client_id": "1601185624273.8899143856786",
            "callback_port": 3118,
        },
    ),
    MCPServerConfig(
        name="supabase",
        description="Database and backend services",
        transport="http",
        url="https://mcp.supabase.com/mcp",
        category="CORE",
        command="npx @anthropic/mcp-server-supabase",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="hugging-face",
        description="Model hub and ML model access",
        transport="http",
        url="https://huggingface.co/mcp",
        category="CORE",
        command="npx @anthropic/mcp-server-huggingface",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="vercel",
        description="Deployment and hosting platform",
        transport="http",
        url="https://mcp.vercel.com",
        category="CORE",
        command="npx @anthropic/mcp-server-vercel",
        requires_auth=True,
    ),
]

# DEV TOOLS SERVERS
DEV_TOOLS_SERVERS = [
    MCPServerConfig(
        name="sentry",
        description="Error tracking and monitoring",
        transport="http",
        url="https://mcp.sentry.dev/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-sentry",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="postman",
        description="API testing and documentation context",
        transport="http",
        url="https://mcp.postman.com/minimal",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-postman",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="context7",
        description="Up-to-date documentation for LLMs",
        transport="http",
        url="https://mcp.context7.com/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-context7",
        requires_auth=False,
    ),
    MCPServerConfig(
        name="figma",
        description="Design system and UI context",
        transport="http",
        url="https://mcp.figma.com/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-figma",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="cloudflare",
        description="Compute and storage services",
        transport="http",
        url="https://bindings.mcp.cloudflare.com/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-cloudflare",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="netlify",
        description="Deployment and hosting",
        transport="http",
        url="https://netlify-mcp.netlify.app/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-netlify",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="planetscale",
        description="MySQL database access and management",
        transport="http",
        url="https://mcp.pscale.dev/mcp/planetscale",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-planetscale",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="honeycomb",
        description="Observability and tracing",
        transport="http",
        url="https://mcp.honeycomb.io/mcp",
        category="DEV_TOOLS",
        command="npx @anthropic/mcp-server-honeycomb",
        requires_auth=True,
    ),
]

# AUTOMATION SERVERS
AUTOMATION_SERVERS = [
    MCPServerConfig(
        name="zapier",
        description="Workflow automation and integrations",
        transport="http",
        url="https://mcp.zapier.com/api/v1/connect",
        category="AUTOMATION",
        command="npx @anthropic/mcp-server-zapier",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="make",
        description="Scenario automation and workflows",
        transport="http",
        url="https://mcp.make.com",
        category="AUTOMATION",
        command="npx @anthropic/mcp-server-make",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="ifttt",
        description="Connect 1000+ applications and services",
        transport="http",
        url="https://ifttt.com/mcp",
        category="AUTOMATION",
        command="npx @anthropic/mcp-server-ifttt",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="exa",
        description="Web search and code documentation",
        transport="http",
        url="https://mcp.exa.ai/mcp",
        category="AUTOMATION",
        command="npx @anthropic/mcp-server-exa",
        requires_auth=True,
    ),
]

# RUNTIME SERVERS - Local execution environments (spawned, not remote)
RUNTIME_SERVERS = [
    MCPServerConfig(
        name="node-runtime",
        description="Node.js code execution environment",
        transport="stdio",
        category="RUNTIMES",
        command="npx @anthropic/mcp-server-node",
        spawn_command="npx @anthropic/mcp-server-node",
        enabled=True,
    ),
    MCPServerConfig(
        name="python-runtime",
        description="Python code execution environment",
        transport="stdio",
        category="RUNTIMES",
        command="python -m mcp_server_python",
        spawn_command="python -m mcp_server_python",
        enabled=True,
    ),
    MCPServerConfig(
        name="docker-runtime",
        description="Container execution environment",
        transport="stdio",
        category="RUNTIMES",
        command="npx @anthropic/mcp-server-docker",
        spawn_command="npx @anthropic/mcp-server-docker",
        enabled=True,
    ),
]

# CODE BUILDERS - Tools for generating and building code
CODE_BUILDERS_SERVERS = [
    MCPServerConfig(
        name="gamma",
        description="Create presentations, documents, and websites",
        transport="http",
        url="https://mcp.gamma.app/mcp",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-gamma",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="magic-patterns",
        description="Design iteration and UI generation",
        transport="http",
        url="https://mcp.magicpatterns.com/mcp",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-magic-patterns",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="canva",
        description="Design creation and graphics",
        transport="http",
        url="https://mcp.canva.com/mcp",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-canva",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="webflow",
        description="CMS and website management",
        transport="http",
        url="https://mcp.webflow.com/mcp",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-webflow",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="lucid",
        description="Diagramming and visual design",
        transport="http",
        url="https://mcp.lucid.app/mcp",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-lucid",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="sanity",
        description="Content management system",
        transport="http",
        url="https://mcp.sanity.io",
        category="CODE_BUILDERS",
        command="npx @anthropic/mcp-server-sanity",
        requires_auth=True,
    ),
]

# RESEARCH SERVERS
RESEARCH_SERVERS = [
    MCPServerConfig(
        name="tavily",
        description="Web search optimized for AI agents",
        transport="http",
        url="https://mcp.tavily.com/mcp",
        category="RESEARCH",
        command="npx @anthropic/mcp-server-tavily",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="scholar-gateway",
        description="Scholarly and academic research",
        transport="http",
        url="https://connector.scholargateway.ai/mcp",
        category="RESEARCH",
        command="npx @anthropic/mcp-server-scholar-gateway",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="consensus",
        description="Scientific research and paper analysis",
        transport="http",
        url="https://mcp.consensus.app/mcp",
        category="RESEARCH",
        command="npx @anthropic/mcp-server-consensus",
        requires_auth=True,
    ),
]

# MEMORY SERVERS - Already configured in LM Studio
MEMORY_SERVERS = [
    MCPServerConfig(
        name="obsidian",
        description="Vault memory for agent knowledge persistence",
        transport="http",
        url="http://localhost:27124",
        category="MEMORY",
        command="obsidian-mcp (configured in LM Studio)",
        requires_auth=True,
        special_config={
            "api_key_env": "OBSIDIAN_API_KEY",
        },
    ),
]

# PRODUCTIVITY SERVERS
PRODUCTIVITY_SERVERS = [
    MCPServerConfig(
        name="clickup",
        description="Project management and task tracking",
        transport="http",
        url="https://mcp.clickup.com/mcp",
        category="PRODUCTIVITY",
        command="npx @anthropic/mcp-server-clickup",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="airtable",
        description="Database and spreadsheet management",
        transport="http",
        url="https://airtable.com/mcp",  # Requires user-specific URL
        category="PRODUCTIVITY",
        command="npx @anthropic/mcp-server-airtable",
        requires_auth=True,
        enabled=False,  # Requires special setup — user must provide URL
    ),
    MCPServerConfig(
        name="miro",
        description="Collaborative whiteboarding and brainstorming",
        transport="http",
        url="https://mcp.miro.com/",
        category="PRODUCTIVITY",
        command="npx @anthropic/mcp-server-miro",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="asana",
        description="Team tasks and work management",
        transport="streamable-http",
        url="https://mcp.asana.com/v2/mcp",
        category="PRODUCTIVITY",
        command="npx @anthropic/mcp-server-asana",
        requires_auth=True,
    ),
]

# PAYMENT SERVERS
PAYMENT_SERVERS = [
    MCPServerConfig(
        name="stripe",
        description="Payment processing and billing",
        transport="http",
        url="https://mcp.stripe.com",
        category="PAYMENTS",
        command="npx @anthropic/mcp-server-stripe",
        requires_auth=True,
    ),
    MCPServerConfig(
        name="paypal",
        description="PayPal payment services",
        transport="http",
        url="https://mcp.paypal.com/mcp",
        category="PAYMENTS",
        command="npx @anthropic/mcp-server-paypal",
        requires_auth=True,
    ),
]

# Master dictionary of all MCP servers organized by category
MCP_SERVERS: Dict[str, List[MCPServerConfig]] = {
    "CORE": CORE_SERVERS,
    "DEV_TOOLS": DEV_TOOLS_SERVERS,
    "AUTOMATION": AUTOMATION_SERVERS,
    "RUNTIMES": RUNTIME_SERVERS,
    "CODE_BUILDERS": CODE_BUILDERS_SERVERS,
    "RESEARCH": RESEARCH_SERVERS,
    "MEMORY": MEMORY_SERVERS,
    "PRODUCTIVITY": PRODUCTIVITY_SERVERS,
    "PAYMENTS": PAYMENT_SERVERS,
}

# Agent role to MCP server category routing
MCP_AGENT_ROUTING: Dict[str, List[str]] = {
    "orchestrator": [
        "CORE",
        "DEV_TOOLS",
        "AUTOMATION",
        "RUNTIMES",
        "CODE_BUILDERS",
        "RESEARCH",
        "MEMORY",
        "PRODUCTIVITY",
        "PAYMENTS",
    ],
    "pm": ["CORE", "PRODUCTIVITY", "AUTOMATION", "MEMORY"],
    "dev": ["CORE", "DEV_TOOLS", "RUNTIMES", "CODE_BUILDERS", "MEMORY"],
    "qa": ["CORE", "DEV_TOOLS", "RUNTIMES", "MEMORY"],
    "critic": ["CORE", "RESEARCH", "MEMORY"],
    "review": ["CORE", "DEV_TOOLS", "MEMORY"],
    "devops": ["CORE", "DEV_TOOLS", "RUNTIMES", "AUTOMATION", "MEMORY"],
    "automation": ["CORE", "AUTOMATION", "RUNTIMES", "PRODUCTIVITY", "MEMORY"],
    "research": ["CORE", "RESEARCH", "AUTOMATION", "MEMORY"],
}


def get_servers_by_category(category: str) -> List[MCPServerConfig]:
    """Get all MCP servers in a specific category.

    Args:
        category: Category name (e.g., 'CORE', 'DEV_TOOLS', 'AUTOMATION')

    Returns:
        List of MCPServerConfig objects for that category

    Raises:
        KeyError: If category doesn't exist
    """
    if category not in MCP_SERVERS:
        raise KeyError(f"Unknown MCP server category: {category}")
    return MCP_SERVERS[category]


def get_enabled_servers() -> List[MCPServerConfig]:
    """Get all enabled MCP servers across all categories.

    Returns:
        List of enabled MCPServerConfig objects
    """
    enabled = []
    for category_servers in MCP_SERVERS.values():
        enabled.extend([s for s in category_servers if s.enabled])
    return enabled


def get_core_servers() -> List[MCPServerConfig]:
    """Get CORE and MEMORY servers (priority for initial setup).

    Returns:
        List of CORE and MEMORY MCPServerConfig objects
    """
    return get_servers_by_category("CORE") + get_servers_by_category("MEMORY")


def get_servers_for_agent(agent_role: str) -> List[MCPServerConfig]:
    """Get all MCP servers that should be available to a specific agent role.

    Args:
        agent_role: Agent role name (e.g., 'dev', 'pm', 'orchestrator')

    Returns:
        List of MCPServerConfig objects available to this agent

    Raises:
        KeyError: If agent role doesn't exist in routing
    """
    if agent_role not in MCP_AGENT_ROUTING:
        raise KeyError(f"Unknown agent role: {agent_role}")

    categories = MCP_AGENT_ROUTING[agent_role]
    servers = []
    for category in categories:
        servers.extend(get_servers_by_category(category))
    return servers


def get_servers_by_name(names: List[str]) -> List[MCPServerConfig]:
    """Get specific MCP servers by their names.

    Args:
        names: List of server names (e.g., ['linear', 'notion', 'slack'])

    Returns:
        List of MCPServerConfig objects matching the names
    """
    result = []
    all_servers = get_enabled_servers()
    server_map = {s.name: s for s in all_servers}

    for name in names:
        if name not in server_map:
            raise KeyError(f"Unknown MCP server: {name}")
        result.append(server_map[name])

    return result


if __name__ == "__main__":
    # Example usage and validation
    print("MCP Server Configuration - Octopus V2")
    print("=" * 60)

    # Show all categories and server counts
    print("\nServer Categories:")
    for category, servers in MCP_SERVERS.items():
        enabled_count = sum(1 for s in servers if s.enabled)
        print(f"  {category}: {len(servers)} servers ({enabled_count} enabled)")

    # Show core servers
    print("\nCore Servers (Priority for setup):")
    for server in get_core_servers():
        auth_str = " [AUTH REQUIRED]" if server.requires_auth else ""
        print(f"  - {server.name}: {server.description}{auth_str}")

    # Show agent routing
    print("\nAgent Role Routing:")
    for role, categories in MCP_AGENT_ROUTING.items():
        server_count = sum(
            len(MCP_SERVERS[cat]) for cat in categories if cat in MCP_SERVERS
        )
        print(f"  {role}: {len(categories)} categories ({server_count} servers)")

    # Validation
    print("\nValidation:")
    try:
        dev_servers = get_servers_for_agent("dev")
        print(f"  Dev agent has access to {len(dev_servers)} servers: OK")
    except Exception as e:
        print(f"  Error: {e}")

