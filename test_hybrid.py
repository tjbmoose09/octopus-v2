"""
Octopus V2 — Hybrid Routing Test
=================================
Run this on your machine:  python test_hybrid.py

Tests:
  1. LM Studio connectivity + model listing
  2. Claude API connectivity + key validation
  3. Full hybrid pipeline: orchestrator via Claude, arm agent via LM Studio
"""

import asyncio
import os
import sys
import json
import time

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

sys.path.insert(0, str(Path(__file__).parent))

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
INFO = "\033[94mINFO\033[0m"


async def test_lm_studio():
    """Test 1: Can we reach LM Studio and list models?"""
    print("\n" + "=" * 60)
    print("TEST 1: LM Studio Connectivity")
    print("=" * 60)

    from agents.engine import lm_client

    healthy = await lm_client.health()
    print(f"  LM Studio reachable: {PASS if healthy else FAIL}")
    if not healthy:
        print(f"  URL: {lm_client.base_url}")
        print("  Make sure LM Studio is running with the server enabled.")
        return False

    models = await lm_client.list_models()
    model_list = [m.get("id", "?") for m in models.get("data", [])]
    chat_models = [m for m in model_list if "embed" not in m.lower()]
    print(f"  Models loaded: {len(chat_models)}")
    for m in chat_models[:5]:
        print(f"    - {m}")
    if len(chat_models) > 5:
        print(f"    ... and {len(chat_models) - 5} more")

    print(f"  LM Studio: {PASS}")
    return True


async def test_claude_api():
    """Test 2: Is the Claude API key valid?"""
    print("\n" + "=" * 60)
    print("TEST 2: Claude API Key Validation")
    print("=" * 60)

    from config.providers import get_claude_config, _claude_api_available
    cfg = get_claude_config()

    available = _claude_api_available()
    print(f"  API key configured: {PASS if available else FAIL}")
    if not available:
        print("  ANTHROPIC_API_KEY is missing or still the placeholder.")
        return False

    print(f"  Model: {cfg.default_model}")
    print(f"  URL: {cfg.base_url}")

    # Send a tiny test request
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{cfg.base_url}/v1/messages",
                headers={
                    "x-api-key": cfg.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": cfg.default_model,
                    "max_tokens": 50,
                    "messages": [{"role": "user", "content": "Say 'hybrid test OK' and nothing else."}],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("content", [{}])[0].get("text", "")
                print(f"  Claude responded: \"{text.strip()}\"")
                print(f"  Claude API: {PASS}")
                return True
            else:
                print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
                print(f"  Claude API: {FAIL}")
                return False
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Claude API: {FAIL}")
        return False


async def test_provider_routing():
    """Test 3: Does the routing table assign correctly?"""
    print("\n" + "=" * 60)
    print("TEST 3: Hybrid Provider Routing")
    print("=" * 60)

    from config.providers import get_agent_provider, _claude_api_available

    if not _claude_api_available():
        print(f"  Skipped (no Claude API key)")
        return False

    routing = {}
    for role in ["orchestrator", "pm", "dev", "qa", "critic", "review", "devops", "automation", "research"]:
        provider = get_agent_provider(role)
        routing[role] = provider
        tag = "CLAUDE API" if provider == "claude_api" else "LM STUDIO"
        print(f"  {role:>14s} -> {tag}")

    orch_ok = routing["orchestrator"] == "claude_api"
    arms_ok = all(v == "lm_studio" for k, v in routing.items() if k != "orchestrator")

    print(f"\n  Orchestrator -> Claude: {PASS if orch_ok else FAIL}")
    print(f"  All arms -> LM Studio: {PASS if arms_ok else FAIL}")
    return orch_ok and arms_ok


async def test_hybrid_pipeline():
    """Test 4: Send a real task through the hybrid pipeline."""
    print("\n" + "=" * 60)
    print("TEST 4: Live Hybrid Pipeline (Orchestrator + Arm Agent)")
    print("=" * 60)

    from database.db import init_db
    from agents.engine import init_agents, assign_models, init_multi_provider, send_to_agent

    # Bootstrap
    await init_db()
    await init_agents()
    await assign_models()
    multi = await init_multi_provider()

    print(f"\n  {INFO} Sending task to ORCHESTRATOR (should use Claude API)...")
    t0 = time.time()
    orch_result = await send_to_agent("orchestrator", "Say 'I am Claude, the orchestrator brain.' and nothing else.")
    t1 = time.time()

    if "error" in orch_result:
        print(f"  Orchestrator: {FAIL} -> {orch_result['error'][:200]}")
        return False

    orch_text = orch_result.get("content", "")[:200]
    orch_provider = orch_result.get("provider", "unknown")
    print(f"  Provider used: {orch_provider}")
    print(f"  Response: \"{orch_text}\"")
    print(f"  Time: {(t1 - t0) * 1000:.0f}ms")
    print(f"  Orchestrator via Claude: {PASS if 'claude' in orch_provider else FAIL}")

    print(f"\n  {INFO} Sending task to DEV agent (should use LM Studio)...")
    t0 = time.time()
    dev_result = await send_to_agent("dev", "Write a Python one-liner that prints 'hello from LM Studio'. Output ONLY the code, nothing else.")
    t1 = time.time()

    if "error" in dev_result:
        print(f"  Dev agent: {FAIL} -> {dev_result['error'][:200]}")
        return False

    dev_text = dev_result.get("content", "")[:200]
    dev_provider = dev_result.get("provider", "unknown")
    print(f"  Provider used: {dev_provider}")
    print(f"  Response: \"{dev_text}\"")
    print(f"  Time: {(t1 - t0) * 1000:.0f}ms")
    print(f"  Dev via LM Studio: {PASS if 'lm_studio' in dev_provider else FAIL}")

    await multi.close()
    return "claude" in orch_provider and "lm_studio" in dev_provider


async def main():
    print("\n" + "#" * 60)
    print("#  OCTOPUS V2 — HYBRID ROUTING TEST")
    print("#" * 60)

    results = {}
    results["LM Studio"] = await test_lm_studio()
    results["Claude API"] = await test_claude_api()
    results["Routing"] = await test_provider_routing()

    if results["LM Studio"] and results["Claude API"]:
        results["Pipeline"] = await test_hybrid_pipeline()
    else:
        print(f"\n  Skipping pipeline test — need both providers online.")
        results["Pipeline"] = False

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, ok in results.items():
        print(f"  {name:>15s}: {PASS if ok else FAIL}")
        if not ok:
            all_pass = False

    if all_pass:
        print(f"\n  ALL TESTS PASSED — Hybrid mode is LIVE!")
        print(f"  Claude handles orchestration, LM Studio handles the arms.")
    else:
        print(f"\n  Some tests failed. Check the output above.")

    print()


if __name__ == "__main__":
    asyncio.run(main())
