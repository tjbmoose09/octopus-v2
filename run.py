#!/usr/bin/env python3
"""
Octopus Agents V2 - Agent Mesh System

  Start LM Studio first, then run this script.
  Backend:   http://localhost:8080
  Frontend:  http://localhost:3000 (npm run dev)

"""

import sys
import os
import subprocess

# Ensure we're in the right directory
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

# Clear stale __pycache__ so config changes take effect immediately
import shutil
for dirpath, dirnames, filenames in os.walk(ROOT):
    if '__pycache__' in dirnames:
        cache_dir = os.path.join(dirpath, '__pycache__')
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass


def check_dependencies():
    """Check and install required packages."""
    required = [
        'fastapi', 'uvicorn', 'httpx', 'aiosqlite',
        'psutil', 'pydantic', 'python-dotenv',
    ]
    missing = []
    for pkg in required:
        import_name = pkg.replace('-', '_')
        if import_name == 'python_dotenv':
            import_name = 'dotenv'
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[Setup] Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', *missing, '--quiet'
        ])
        print("[Setup] Dependencies installed.")


def validate_configs():
    """Validate all configuration modules load correctly."""
    print("[Config] Validating configuration modules...")

    from config.settings import (
        HOST, PORT, ORCHESTRATOR_MODEL, AGENT_ROLES,
        AGENT_DOS, AGENT_DONTS, DEFAULT_MODEL_ASSIGNMENTS,
    )
    print(f"  Settings:  {len(AGENT_ROLES)} agent roles")
    print(f"  Rules:     {len(AGENT_DOS)} DOs, {len(AGENT_DONTS)} DON'Ts")
    print(f"  Models:")
    for role, model_id in DEFAULT_MODEL_ASSIGNMENTS.items():
        print(f"    {role:15s} -> {model_id}")

    from config.providers import get_all_providers, DEFAULT_AGENT_PROVIDERS
    providers = get_all_providers()
    print(f"  Providers: {len(providers)} active ({', '.join(providers.keys())})")

    from config.mcp_servers import MCP_SERVERS, get_enabled_servers, MCP_AGENT_ROUTING
    total = sum(len(s) for s in MCP_SERVERS.values())
    enabled = len(get_enabled_servers())
    print(f"  MCP:       {total} servers ({enabled} enabled), {len(MCP_AGENT_ROUTING)} agent routes")

    from config.skills import AGENT_SKILLS
    total_skills = sum(len(v) for v in AGENT_SKILLS.values())
    print(f"  Skills:    {total_skills} skills across {len(AGENT_SKILLS)} agents")

    from config.memory import get_memory_config, AGENT_MEMORY_ACCESS
    mem = get_memory_config()
    print(f"  Memory:    Obsidian @ {mem.obsidian_url} (vault: {mem.vault_name})")
    print(f"  Access:    {len(AGENT_MEMORY_ACCESS)} agent memory policies")

    print("[Config] All modules valid.\n")
    return HOST, PORT


async def check_memory_connection():
    """Check if Obsidian MCP server is reachable."""
    from agents.engine import memory_client
    healthy = await memory_client.health_check()
    if healthy:
        print("[Memory] Obsidian MCP server: CONNECTED")
    else:
        print("[Memory] Obsidian MCP server: NOT REACHABLE (memory features will be limited)")
    return healthy


async def check_lm_studio():
    """Check if LM Studio is running and has models loaded."""
    import httpx
    from config.settings import LM_STUDIO_BASE
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{LM_STUDIO_BASE}/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                if models:
                    model_names = [m.get("id", "unknown") for m in models]
                    print(f"[LM Studio] Connected — {len(models)} model(s) loaded:")
                    for name in model_names:
                        print(f"  - {name}")
                    return True
                else:
                    print("[LM Studio] Connected but NO MODELS LOADED")
                    print("  Load a model in LM Studio before sending tasks to agents.")
                    return True
            else:
                print(f"[LM Studio] Unexpected response: {resp.status_code}")
                return False
    except Exception:
        print("[LM Studio] NOT REACHABLE at http://localhost:1234")
        print("  Start LM Studio server: lms server start")
        return False


def main():
    print(__doc__)

    # Step 1: Dependencies
    check_dependencies()

    # Step 2: Validate configs
    HOST, PORT = validate_configs()

    # Step 3: Pre-flight checks (async)
    import asyncio

    async def preflight():
        await check_lm_studio()
        await check_memory_connection()

    asyncio.run(preflight())

    # Step 4: Start server
    import uvicorn
    from config.settings import ORCHESTRATOR_MODEL

    print(f"\n[Octopus V2] Starting server on http://{HOST}:{PORT}")
    print(f"[Octopus V2] Orchestrator model: {ORCHESTRATOR_MODEL}")
    print(f"[Octopus V2] Frontend: cd frontend && npm run dev")
    print(f"[Octopus V2] Press Ctrl+C to stop\n")

    uvicorn.run(
        "api.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
