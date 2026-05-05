"""Octopus Agents V2 — Model Provider Configuration

Supports multiple backends:
  1. LM Studio (local) — OpenAI-compatible /v1/chat/completions endpoint
  2. Claude API (cloud)  — Anthropic direct API
  3. OpenAI-compatible   — Any server exposing /v1/chat/completions

Offloading strategy:
  - Heavy/complex tasks  -> Claude API (cloud)
  - Routine/simple tasks -> LM Studio (local)
  - Configurable per-agent role via AGENT_PROVIDER_MAP
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ProviderType(Enum):
    LM_STUDIO = "lm_studio"
    CLAUDE_API = "claude_api"
    OPENAI_COMPAT = "openai_compat"


@dataclass
class ProviderConfig:
    """Configuration for a single model provider."""
    name: str
    provider_type: ProviderType
    base_url: str
    api_key: str
    default_model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 120.0
    enabled: bool = True
    supports_streaming: bool = True
    supports_tool_use: bool = False
    context_window: int = 32768
    priority: int = 1  # Lower = preferred for offloading


# ---------------------------------------------------------------------------
# Environment-driven provider configs
# ---------------------------------------------------------------------------

def get_lm_studio_config() -> ProviderConfig:
    """LM Studio local server config."""
    return ProviderConfig(
        name="lm_studio",
        provider_type=ProviderType.LM_STUDIO,
        base_url=os.getenv("LM_STUDIO_URL", "http://localhost:1234"),
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
        default_model=os.getenv("LM_STUDIO_MODEL", ""),
        max_tokens=int(os.getenv("LM_STUDIO_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("LM_STUDIO_TEMPERATURE", "0.7")),
        timeout=float(os.getenv("LM_STUDIO_TIMEOUT", "120")),
        supports_streaming=True,
        supports_tool_use=False,
        context_window=int(os.getenv("LM_STUDIO_CONTEXT_WINDOW", "32768")),
        priority=1,  # Prefer local first
    )


def get_claude_config() -> ProviderConfig:
    """Anthropic Claude API config."""
    return ProviderConfig(
        name="claude_api",
        provider_type=ProviderType.CLAUDE_API,
        base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        default_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8192")),
        temperature=float(os.getenv("CLAUDE_TEMPERATURE", "0.7")),
        timeout=float(os.getenv("CLAUDE_TIMEOUT", "180")),
        supports_streaming=True,
        supports_tool_use=True,
        context_window=200000,
        priority=2,  # Fallback / heavy tasks
    )


def get_openai_compat_config() -> ProviderConfig:
    """Any OpenAI-compatible endpoint (vLLM, LocalAI, etc.)."""
    return ProviderConfig(
        name="openai_compat",
        provider_type=ProviderType.OPENAI_COMPAT,
        base_url=os.getenv("OPENAI_COMPAT_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("OPENAI_COMPAT_API_KEY", "none"),
        default_model=os.getenv("OPENAI_COMPAT_MODEL", ""),
        max_tokens=int(os.getenv("OPENAI_COMPAT_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("OPENAI_COMPAT_TEMPERATURE", "0.7")),
        timeout=float(os.getenv("OPENAI_COMPAT_TIMEOUT", "120")),
        supports_streaming=True,
        supports_tool_use=False,
        context_window=int(os.getenv("OPENAI_COMPAT_CONTEXT_WINDOW", "32768")),
        priority=3,
    )


# ---------------------------------------------------------------------------
# Agent -> Provider routing
# ---------------------------------------------------------------------------

# HYBRID STRATEGY:
#   - Brain tier (orchestrator) -> Claude API  (smarter planning & delegation)
#   - Arm tier (all workers)    -> LM Studio   (local GPU, fast, free)
#
# If ANTHROPIC_API_KEY is missing or placeholder, everything falls back to lm_studio.
# Override any role with env: AGENT_PROVIDER_<ROLE>=lm_studio|claude_api|openai_compat

_HYBRID_AGENT_PROVIDERS = {
    "orchestrator": "claude_api",   # Brain -- Claude handles planning & synthesis
    "pm":          "lm_studio",     # Arm -- local
    "dev":         "lm_studio",     # Arm -- local
    "qa":          "lm_studio",     # Arm -- local
    "critic":      "lm_studio",     # Arm -- local
    "review":      "lm_studio",     # Arm -- local
    "devops":      "lm_studio",     # Arm -- local
    "automation":  "lm_studio",     # Arm -- local
    "research":    "lm_studio",     # Arm -- local
}

_LOCAL_ONLY_PROVIDERS = {role: "lm_studio" for role in _HYBRID_AGENT_PROVIDERS}


def _claude_api_available() -> bool:
    """Check if a real Anthropic API key is configured (not the placeholder)."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and key != "sk-ant-your-key-here"


def _get_default_providers() -> dict:
    """Return the correct provider map based on whether Claude API is available."""
    if _claude_api_available():
        return _HYBRID_AGENT_PROVIDERS
    return _LOCAL_ONLY_PROVIDERS

DEFAULT_AGENT_PROVIDERS = _get_default_providers()


def get_agent_provider(role: str) -> str:
    """Get the provider name for a given agent role.
    Check env override first, then fall back to defaults.
    Re-evaluates availability each call so hot-reloading .env works."""
    env_key = f"AGENT_PROVIDER_{role.upper()}"
    env_val = os.getenv(env_key)
    if env_val:
        return env_val
    defaults = _get_default_providers()
    return defaults.get(role, "lm_studio")


# ---------------------------------------------------------------------------
# Recommended models per GPU tier
# ---------------------------------------------------------------------------

RECOMMENDED_MODELS = {
    "8gb": [
        {"id": "qwen3-8b", "name": "Qwen 3 8B", "vram": "~6GB", "use": "General coding, fast responses"},
        {"id": "deepseek-coder-v2-lite", "name": "DeepSeek Coder V2 Lite", "vram": "~7GB", "use": "Code generation"},
        {"id": "llama-3.3-8b", "name": "Llama 3.3 8B", "vram": "~6GB", "use": "General purpose"},
    ],
    "16gb": [
        {"id": "qwen3-14b", "name": "Qwen 3 14B", "vram": "~12GB", "use": "Strong coding, multilingual"},
        {"id": "deepseek-coder-v2", "name": "DeepSeek Coder V2 16B", "vram": "~14GB", "use": "Best code gen at this tier"},
        {"id": "codestral-22b-q4", "name": "Codestral 22B Q4", "vram": "~14GB", "use": "Excellent code completion"},
    ],
    "24gb": [
        {"id": "qwen2.5-coder-32b-q4", "name": "Qwen 2.5 Coder 32B Q4", "vram": "~20GB", "use": "Best local coding model"},
        {"id": "deepseek-r1-distill-32b", "name": "DeepSeek R1 Distill 32B", "vram": "~22GB", "use": "Strong reasoning + code"},
        {"id": "codestral-22b", "name": "Codestral 22B Full", "vram": "~16GB", "use": "Fast code completion, room for context"},
    ],
}


def get_all_providers() -> dict:
    """Return all configured providers."""
    providers = {}
    lm = get_lm_studio_config()
    if lm.api_key and lm.base_url:
        providers["lm_studio"] = lm
    claude = get_claude_config()
    if claude.api_key:
        providers["claude_api"] = claude
    openai = get_openai_compat_config()
    if openai.base_url and openai.api_key != "none":
        providers["openai_compat"] = openai
    return providers
