"""Octopus V2 — Memory System Integration Test

Run from the project root:
    python tests/test_memory_obsidian.py

Prerequisites:
  - Obsidian is running with the Local REST API plugin enabled
  - API key matches the one in config/memory.py
  - The vault 'OctopusMemory' (or whatever OBSIDIAN_VAULT is set to) exists

This script tests EVERY memory path: STM, LTM, episodic, working state,
daily logs, chat logs, and verifies they appear in the vault.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.engine import ObsidianMemoryClient
from config.memory import get_memory_config

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0
errors = []


def report(test_name: str, success: bool, detail: str = ""):
    global passed, failed
    if success:
        passed += 1
        print(f"  {GREEN}✓ PASS{RESET} {test_name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        errors.append((test_name, detail))
        print(f"  {RED}✗ FAIL{RESET} {test_name}" + (f" — {detail}" if detail else ""))


async def run_tests():
    global passed, failed

    config = get_memory_config()
    print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}  Octopus V2 — Memory System Integration Tests{RESET}")
    print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════{RESET}")
    print(f"\n  Obsidian URL:  {config.obsidian_url}")
    print(f"  Vault:         {config.vault_name}")
    print(f"  API Key:       {config.obsidian_api_key[:12]}...")
    print()

    client = ObsidianMemoryClient()
    test_task_id = f"memtest-{datetime.now().strftime('%H%M%S')}"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ──────────────────────────────────────────────────
    # 1. HEALTH CHECK
    # ──────────────────────────────────────────────────
    print(f"{BOLD}[1/8] Health Check{RESET}")
    healthy = await client.health_check()
    report("Obsidian REST API reachable", healthy,
           f"{config.obsidian_url}" if healthy else
           "Cannot connect! Is Obsidian running with Local REST API plugin?")

    if not healthy:
        print(f"\n{RED}{BOLD}  ⚠ Obsidian is not reachable. Cannot continue tests.{RESET}")
        print(f"  Make sure:")
        print(f"    1. Obsidian is open")
        print(f"    2. 'Local REST API' community plugin is installed and enabled")
        print(f"    3. The API key in the plugin matches: {config.obsidian_api_key[:20]}...")
        print(f"    4. The plugin is listening on port 27124")
        return

    # ──────────────────────────────────────────────────
    # 2. SHORT-TERM MEMORY (STM)
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[2/8] Short-Term Memory (STM){RESET}")
    stm_context = {
        "task_id": test_task_id,
        "description": "Memory integration test task",
        "assigned_to": "dev",
        "created_at": ts,
        "test": True,
    }
    result = await client.save_task_context(test_task_id, stm_context)
    report("Save STM task context", result.get("status") == "saved",
           f"Path: Memory/ShortTerm/{test_task_id}.md | Result: {result}")

    # Read it back
    readback = await client.read_note(f"Memory/ShortTerm/{test_task_id}.md")
    report("Read back STM context", readback.get("status") == "found",
           f"Found: {len(readback.get('content', ''))} chars" if readback.get("status") == "found"
           else f"Result: {readback}")

    # ──────────────────────────────────────────────────
    # 3. LONG-TERM MEMORY (LTM)
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[3/8] Long-Term Memory (LTM){RESET}")
    solution_content = f"""# Solution: Memory Test Pattern
**Category:** testing
**Date:** {ts}
**Task:** {test_task_id}

## Problem
Memory system was not writing to Obsidian vault due to Content-Type mismatch.

## Solution
Changed Content-Type from `application/json` to `text/markdown` for vault PUT requests.

## Tags
#memory #testing #fix
"""
    result = await client.save_solution("testing", f"memory_test_{test_task_id}", solution_content)
    report("Save LTM solution", result.get("status") == "saved",
           f"Path: Memory/LongTerm/Solutions/testing/memory_test_{test_task_id}.md | Result: {result}")

    # Read it back
    readback = await client.read_note(f"Memory/LongTerm/Solutions/testing/memory_test_{test_task_id}.md")
    report("Read back LTM solution", readback.get("status") == "found",
           f"Found: {len(readback.get('content', ''))} chars" if readback.get("status") == "found"
           else f"Result: {readback}")

    # ──────────────────────────────────────────────────
    # 4. EPISODIC MEMORY (Chat History)
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[4/8] Episodic Memory (Chat History){RESET}")
    messages = [
        {"role": "user", "content": "Run the memory integration test"},
        {"role": "assistant", "content": f"Running memory test at {ts}. All systems nominal."},
        {"role": "user", "content": "What was the result?"},
        {"role": "assistant", "content": "STM and LTM both saved successfully to the Obsidian vault."},
    ]
    result = await client.save_chat_history("dev", test_task_id, messages)
    report("Save episodic chat history", result.get("status") == "saved",
           f"Result: {result}")

    # ──────────────────────────────────────────────────
    # 5. WORKING STATE
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[5/8] Working State{RESET}")
    working_state = {
        "task_id": test_task_id,
        "phase": "testing",
        "agents_involved": ["dev", "qa"],
        "progress": 75,
        "notes": "Memory integration test in progress",
        "timestamp": ts,
    }
    result = await client.update_working_state(test_task_id, working_state)
    report("Save working state", result.get("status") == "saved",
           f"Path: Memory/WorkingState/{test_task_id}_state.md | Result: {result}")

    # Read it back
    readback = await client.read_note(f"Memory/WorkingState/{test_task_id}_state.md")
    report("Read back working state", readback.get("status") == "found",
           f"Found: {len(readback.get('content', ''))} chars" if readback.get("status") == "found"
           else f"Result: {readback}")

    # ──────────────────────────────────────────────────
    # 6. DAILY LOG — System
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[6/8] Daily Log — System{RESET}")
    await client.log_system(f"INFO octopus.test: Memory integration test started — task {test_task_id}")
    await client.log_system(f"INFO octopus.test: STM saved successfully")
    await client.log_system(f"INFO octopus.test: LTM saved successfully")
    date_str = datetime.now().strftime("%Y-%m-%d")
    readback = await client.read_note(f"Logs/Daily/{date_str}.md")
    has_system = readback.get("status") == "found" and "Memory integration test started" in readback.get("content", "")
    report("System logs in daily note", has_system,
           f"Daily note has {len(readback.get('content', ''))} chars" if readback.get("status") == "found"
           else f"Result: {readback}")

    # ──────────────────────────────────────────────────
    # 7. DAILY LOG — Pipeline Event
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[7/8] Daily Log — Pipeline Event{RESET}")
    pipeline_event = {
        "task_id": test_task_id,
        "from_agent": "orchestrator",
        "to_agent": "dev",
        "event_type": "assign",
        "timestamp": datetime.now().isoformat(),
        "message": "Memory integration test task assigned to dev agent",
    }
    await client.log_pipeline_event(pipeline_event)
    # Re-read daily note
    readback = await client.read_note(f"Logs/Daily/{date_str}.md")
    has_pipeline = readback.get("status") == "found" and test_task_id in readback.get("content", "")
    report("Pipeline event in daily note", has_pipeline,
           "Task ID found in Pipeline section" if has_pipeline else f"Result: {readback.get('status')}")

    # ──────────────────────────────────────────────────
    # 8. DAILY LOG — Conversation
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}[8/8] Daily Log — Conversation{RESET}")
    await client.log_conversation(
        agent_role="dev",
        task_id=test_task_id,
        user_msg="Run the full memory integration test suite",
        assistant_msg="All memory types verified: STM, LTM, episodic, working state, and daily logs are all writing correctly to the Obsidian vault.",
        provider="test_harness",
        elapsed_ms=42.0,
    )
    # Re-read daily note
    readback = await client.read_note(f"Logs/Daily/{date_str}.md")
    has_convo = readback.get("status") == "found" and "test_harness" in readback.get("content", "")
    report("Conversation in daily note", has_convo,
           "Conversation found with provider info" if has_convo else f"Result: {readback.get('status')}")

    # ──────────────────────────────────────────────────
    # FINAL SUMMARY
    # ──────────────────────────────────────────────────
    print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════{RESET}")
    total = passed + failed
    if failed == 0:
        print(f"  {GREEN}{BOLD}ALL {total} TESTS PASSED ✓{RESET}")
        print(f"\n  {BOLD}Check your Obsidian vault for:{RESET}")
        print(f"    • Memory/ShortTerm/{test_task_id}.md")
        print(f"    • Memory/LongTerm/Solutions/testing/memory_test_{test_task_id}.md")
        print(f"    • Memory/ChatHistory/dev/{date_str}_{test_task_id}.md")
        print(f"    • Memory/WorkingState/{test_task_id}_state.md")
        print(f"    • Logs/Daily/{date_str}.md")
    else:
        print(f"  {RED}{BOLD}{failed} of {total} TESTS FAILED{RESET}")
        print(f"\n  {BOLD}Failures:{RESET}")
        for name, detail in errors:
            print(f"    {RED}✗{RESET} {name}: {detail}")
    print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
