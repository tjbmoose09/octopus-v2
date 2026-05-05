"""Octopus Agents V2 — Multi-Provider LLM Client

Routes requests to the correct backend based on provider config:
  - LM Studio:    OpenAI-compatible /v1/chat/completions
  - Claude API:   Anthropic /v1/messages
  - OpenAI compat: Generic /v1/chat/completions

Supports automatic failover: if local model is down, fall back to cloud.
"""

import httpx
import json
import time
import asyncio
from typing import Optional
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.providers import (
    ProviderConfig, ProviderType, get_all_providers,
    get_agent_provider, get_lm_studio_config, get_claude_config,
)


class MultiProviderClient:
    """Unified LLM client that routes to the right backend."""

    def __init__(self):
        self.clients: dict[str, httpx.AsyncClient] = {}
        self.providers: dict[str, ProviderConfig] = {}
        self.health_cache: dict[str, dict] = {}  # provider -> {healthy, checked_at}
        self._lock = asyncio.Lock()

    async def init(self):
        """Initialize provider connections."""
        self.providers = get_all_providers()
        for name, cfg in self.providers.items():
            self.clients[name] = httpx.AsyncClient(
                timeout=cfg.timeout,
                headers=self._build_headers(cfg),
            )
            print(f"[MultiProvider] Registered: {name} -> {cfg.base_url}")

    def _build_headers(self, cfg: ProviderConfig) -> dict:
        """Build auth headers based on provider type."""
        if cfg.provider_type == ProviderType.CLAUDE_API:
            return {
                "x-api-key": cfg.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        else:
            # OpenAI-compatible (LM Studio and others)
            return {
                "Authorization": f"Bearer {cfg.api_key}",
                "content-type": "application/json",
            }

    async def health_check(self, provider_name: str) -> bool:
        """Check if a provider is reachable. Caches for 30 seconds."""
        cached = self.health_cache.get(provider_name)
        if cached and (time.time() - cached["checked_at"]) < 30:
            return cached["healthy"]

        cfg = self.providers.get(provider_name)
        if not cfg:
            return False

        try:
            client = self.clients[provider_name]
            if cfg.provider_type == ProviderType.CLAUDE_API:
                # Claude API doesn't have a simple health endpoint,
                # so we just check TCP connectivity
                resp = await client.get(f"{cfg.base_url}/v1/messages", timeout=5.0)
                healthy = resp.status_code in (200, 401, 405)  # Any response = reachable
            else:
                # All OpenAI-compatible providers (including LM Studio) use /v1/models
                resp = await client.get(f"{cfg.base_url}/v1/models", timeout=5.0)
                healthy = resp.status_code == 200
        except Exception:
            healthy = False

        self.health_cache[provider_name] = {"healthy": healthy, "checked_at": time.time()}
        return healthy

    async def chat(
        self,
        provider_name: str,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        fallback: bool = True,
    ) -> dict:
        """Send a chat completion to the specified provider.

        If fallback=True and the primary provider is down, tries the next
        available provider by priority.
        """
        # Try primary provider
        result = await self._send(provider_name, model, messages, temperature, max_tokens)
        if "error" not in result:
            return result

        if not fallback:
            return result

        # Fallback: try other providers in priority order
        sorted_providers = sorted(
            self.providers.items(),
            key=lambda x: x[1].priority,
        )
        for name, cfg in sorted_providers:
            if name == provider_name:
                continue
            if not cfg.enabled:
                continue
            if not await self.health_check(name):
                continue

            print(f"[MultiProvider] Falling back from {provider_name} -> {name}")
            fallback_result = await self._send(
                name, cfg.default_model, messages, temperature, max_tokens
            )
            if "error" not in fallback_result:
                fallback_result["_fallback_from"] = provider_name
                fallback_result["_fallback_to"] = name
                return fallback_result

        return result  # Return original error if all fallbacks fail

    async def _send(
        self,
        provider_name: str,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Send request to a specific provider."""
        cfg = self.providers.get(provider_name)
        if not cfg:
            return {"error": f"Provider '{provider_name}' not configured"}

        client = self.clients.get(provider_name)
        if not client:
            return {"error": f"No client for provider '{provider_name}'"}

        start = time.time()

        try:
            if cfg.provider_type == ProviderType.CLAUDE_API:
                return await self._send_claude(client, cfg, model, messages, temperature, max_tokens, start)
            else:
                return await self._send_openai(client, cfg, model, messages, temperature, max_tokens, start)
        except httpx.ConnectError:
            return {"error": f"Cannot connect to {provider_name} at {cfg.base_url}"}
        except httpx.TimeoutException:
            return {"error": f"Timeout calling {provider_name} ({cfg.timeout}s)"}
        except Exception as e:
            return {"error": f"{provider_name} error: {str(e)}"}

    async def _send_openai(
        self, client, cfg, model, messages, temperature, max_tokens, start
    ) -> dict:
        """Send to LM Studio or OpenAI-compatible endpoint.
        Both use the standard OpenAI /v1/chat/completions format."""
        # All providers use OpenAI-compatible format (LM Studio supports it natively)
        url = f"{cfg.base_url}/v1/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.time() - start) * 1000

        # Normalize response — LM Studio native returns different structure
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
        else:
            content = data.get("content", data.get("response", data.get("output", "")))
            if isinstance(content, list):
                content = "".join(
                    block.get("text", str(block)) for block in content if isinstance(block, dict)
                ) or str(content)

        return {
            "provider": cfg.name,
            "model": model,
            "content": content,
            "usage": data.get("usage", {}),
            "elapsed_ms": round(elapsed, 1),
        }

    async def _send_claude(
        self, client, cfg, model, messages, temperature, max_tokens, start
    ) -> dict:
        """Anthropic Messages API request."""
        # Convert messages: extract system prompt
        system_content = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content += msg["content"] + "\n"
            else:
                user_messages.append(msg)

        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_content.strip():
            body["system"] = system_content.strip()

        resp = await client.post(f"{cfg.base_url}/v1/messages", json=body)
        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.time() - start) * 1000

        # Extract content from Claude response format
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block["text"]

        return {
            "provider": cfg.name,
            "model": model,
            "content": content,
            "usage": data.get("usage", {}),
            "elapsed_ms": round(elapsed, 1),
        }

    async def list_models(self, provider_name: str = "lm_studio") -> dict:
        """List available models from a provider."""
        cfg = self.providers.get(provider_name)
        if not cfg:
            return {"error": f"Provider '{provider_name}' not found", "data": []}

        client = self.clients.get(provider_name)
        try:
            if cfg.provider_type == ProviderType.CLAUDE_API:
                # Claude doesn't have a model listing endpoint in the same way
                return {"data": [
                    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6"},
                    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
                    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"},
                ]}
            else:
                resp = await client.get(f"{cfg.base_url}/v1/models", timeout=10.0)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {"error": str(e), "data": []}

    async def get_status(self) -> dict:
        """Get status of all providers."""
        status = {}
        for name, cfg in self.providers.items():
            healthy = await self.health_check(name)
            status[name] = {
                "url": cfg.base_url,
                "type": cfg.provider_type.value,
                "model": cfg.default_model,
                "healthy": healthy,
                "priority": cfg.priority,
                "enabled": cfg.enabled,
            }
        return status

    async def close(self):
        """Close all HTTP clients."""
        for client in self.clients.values():
            await client.aclose()
