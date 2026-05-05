"""Octopus Agents V2 — Agent Engine
Handles agent lifecycle, task routing, and HYBRID provider communication.

Key design:
- Orchestrator (brain) routes to Claude API when available, LM Studio otherwise
- All arm agents always route to LM Studio (local GPU)
- Uses MultiProviderClient for all LLM calls — no more direct LMStudioClient
- Graceful Obsidian memory fallback (never blocks chat on memory failure)
- Proper response format for frontend
- Daily logs (system, pipeline, conversations) saved to Obsidian daily notes
"""

import httpx
import uuid
import json
import time
import asyncio
import logging
import io
from datetime import datetime
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LM_STUDIO_API, LM_STUDIO_BASE, AGENT_ROLES, SYSTEM_PROMPTS, ORCHESTRATOR_MODEL, DEFAULT_MODEL_ASSIGNMENTS, AGENT_DOS, AGENT_DONTS, LOG_DIR, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT
from config.mcp_servers import get_servers_for_agent, MCP_AGENT_ROUTING
from config.skills import get_skills_for_agent, get_autonomous_skills, AGENT_SKILLS
from config.memory import get_memory_config, get_agent_memory_access, get_vault_path, MemoryType, MEMORY_OPERATIONS
from config.providers import get_agent_provider, get_all_providers, get_claude_config, get_lm_studio_config
from database.db import execute, fetch_all, fetch_one

# In-memory state
agent_states = {}
task_queue = asyncio.Queue()
pipeline_log = []  # Recent pipeline events for real-time display


class LMStudioClient:
    """Client for LM Studio — uses OpenAI-compatible /v1/ endpoints."""

    def __init__(self, base_url: str = LM_STUDIO_BASE):
        # Normalize: always use /v1 for OpenAI-compat
        self.base_url = base_url.rstrip("/")
        self.v1_url = f"{self.base_url}/v1"
        self.client = httpx.AsyncClient(timeout=120.0)
        self._model_cache = []     # List of model ID strings
        self._cache_time = 0

    async def list_models(self):
        """GET /v1/models — list available models."""
        try:
            resp = await self.client.get(f"{self.v1_url}/models")
            resp.raise_for_status()
            data = resp.json()
            if "data" in data and isinstance(data["data"], list):
                self._model_cache = [m.get("id", "") for m in data["data"] if m.get("id")]
                self._cache_time = time.time()
                print(f"[LMStudio] Found {len(self._model_cache)} models: {self._model_cache}")
            return data
        except httpx.ConnectError:
            return {"error": f"Cannot connect to LM Studio at {self.v1_url}. Is the server running?", "data": []}
        except Exception as e:
            return {"error": str(e), "data": []}

    async def _resolve_model(self, model: str) -> str:
        """Resolve a short model name to a full LM Studio model ID."""
        if time.time() - self._cache_time > 60 or not self._model_cache:
            await self.list_models()
        if not self._model_cache:
            return model
        chat_models = [mid for mid in self._model_cache if "embed" not in mid.lower()]
        if not chat_models:
            chat_models = self._model_cache
        if model in chat_models:
            return model
        for mid in chat_models:
            if model.lower() in mid.lower():
                print(f"[LMStudio] Resolved '{model}' -> '{mid}'")
                return mid
        for mid in chat_models:
            if mid.lower() in model.lower():
                print(f"[LMStudio] Resolved '{model}' -> '{mid}' (reverse)")
                return mid
        fallback = chat_models[0]
        print(f"[LMStudio] WARNING: '{model}' not found. Falling back to '{fallback}'")
        return fallback

    async def chat(self, model: str, messages: list, temperature: float = 0.7, max_tokens: int = 4096):
        """POST /v1/chat/completions — OpenAI-compatible chat."""
        try:
            resolved_model = await self._resolve_model(model)
            body = {
                "model": resolved_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            resp = await self.client.post(f"{self.v1_url}/chat/completions", json=body)
            resp.raise_for_status()
            data = resp.json()
            if "choices" not in data:
                content = data.get("content", data.get("response", data.get("output", str(data))))
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", str(block)) for block in content if isinstance(block, dict)
                    ) or str(content)
                data = {
                    "choices": [{"message": {"content": str(content), "role": "assistant"}}],
                    "usage": data.get("usage", {}),
                    "model": resolved_model,
                }
            return data
        except httpx.ConnectError:
            return {"error": f"Cannot connect to LM Studio at {self.v1_url}. Is it running?"}
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:300] if e.response else "unknown"
            return {"error": f"LM Studio returned {e.response.status_code}: {error_text}"}
        except Exception as e:
            return {"error": str(e)}

    async def load_model(self, model: str):
        """POST /v1/models/load — load a model into memory."""
        try:
            resp = await self.client.post(f"{self.v1_url}/models/load", json={"model": model})
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def download_model(self, model: str):
        """POST /v1/models/download — download a model."""
        try:
            resp = await self.client.post(f"{self.v1_url}/models/download", json={"model": model})
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def download_status(self, job_id: str):
        """GET /v1/models/download/status/:job_id — check download progress."""
        try:
            resp = await self.client.get(f"{self.v1_url}/models/download/status/{job_id}")
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def health(self) -> bool:
        """Quick connectivity check."""
        try:
            resp = await self.client.get(f"{self.v1_url}/models", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False


lm_client = LMStudioClient()

# ---------------------------------------------------------------------------
# Multi-provider client — shared instance used by send_to_agent()
# Initialized lazily via init_multi_provider() called from api/main.py lifespan
# ---------------------------------------------------------------------------
from agents.multi_provider_client import MultiProviderClient

_multi_client: Optional[MultiProviderClient] = None


def format_response(response_text: str) -> str:
    """Format response text for better readability and user experience."""
    if not response_text:
        return ""

    # Clean up markdown formatting
    lines = response_text.split('\n')
    formatted_lines = []

    for line in lines:
        stripped = line.strip()

        # Convert markdown headers to bold with extra spacing
        if stripped.startswith('# '):
            formatted_lines.append(f"**{stripped[2:].strip()}**")
            formatted_lines.append("")
        elif stripped.startswith('## '):
            formatted_lines.append(f"***{stripped[3:].strip()}***")
            formatted_lines.append("")
        elif stripped.startswith('### '):
            formatted_lines.append(f"__{stripped[4:].strip()}__")
            formatted_lines.append("")
        # Convert bullet points to better format
        elif stripped.startswith('- ') or stripped.startswith('* '):
            formatted_lines.append(f"• {stripped[2:].strip()}")
        # Convert code blocks to indented blocks with line breaks
        elif stripped.startswith('```') and len(stripped) > 3:
            formatted_lines.append("")
            formatted_lines.append("```\n")
        elif stripped.endswith('```'):
            formatted_lines.append("\n```")
            formatted_lines.append("")
        # Handle lists of items with proper spacing
        elif stripped.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
            formatted_lines.append(f"  {stripped}")
        else:
            formatted_lines.append(stripped)

    # Clean up extra empty lines
    result = '\n'.join(formatted_lines)
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')

    return result.strip()


async def init_multi_provider():
    """Initialize the shared MultiProviderClient. Call once at startup."""
    global _multi_client
    _multi_client = MultiProviderClient()
    await _multi_client.init()

    # Log which providers are active
    status = await _multi_client.get_status()
    for name, info in status.items():
        tag = "ACTIVE" if info.get("healthy") else "DOWN"
        print(f"[Engine] Provider {name}: {tag} ({info.get('url', '?')})")

    # Log the hybrid routing table
    providers = get_all_providers()
    claude_available = "claude_api" in providers
    print(f"[Engine] Hybrid mode: Claude API {'AVAILABLE' if claude_available else 'NOT CONFIGURED (all agents -> LM Studio)'}")
    for role in AGENT_ROLES:
        prov = get_agent_provider(role)
        print(f"[Engine]   {role:>14s} -> {prov}")

    return _multi_client


def get_multi_client() -> MultiProviderClient:
    """Get the shared MultiProviderClient. Raises if not initialized."""
    if _multi_client is None:
        raise RuntimeError("MultiProviderClient not initialized")
    return _multi_client


class ObsidianMemoryClient:
    """Client for Obsidian MCP memory operations.

    All methods are fail-safe — they log errors but never raise exceptions.
    """

    def __init__(self):
        self.config = get_memory_config()
        self.base_url = self.config.obsidian_url
        self.api_key = self.config.obsidian_api_key
        self._auth_header = {"Authorization": f"Bearer {self.api_key}"}
        # JSON headers for search/API endpoints
        self.headers = {
            **self._auth_header,
            "Content-Type": "application/json",
        }
        # Markdown headers for vault PUT (note saving)
        self._md_headers = {
            **self._auth_header,
            "Content-Type": "text/markdown",
        }
        self._healthy = None

    async def _request(self, method, path, **kwargs):
        """Safe HTTP request wrapper — never raises.

        Uses JSON headers for POST (search), auth-only for GET.
        For vault PUTs, use save_note() directly instead.
        """
        try:
            # Use JSON headers for POST requests, auth-only for GET
            headers = self.headers if method == "post" else self._auth_header
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await getattr(client, method)(
                    f"{self.base_url}{path}",
                    headers=headers,
                    **kwargs
                )
                return resp
        except Exception as e:
            logging.getLogger("octopus.memory").warning(
                f"[Memory] Obsidian request failed: {method.upper()} {path} -> {e}"
            )
            return None

    async def save_note(self, path: str, content: str) -> dict:
        """Save a markdown note to the Obsidian vault.

        Uses Content-Type: text/markdown as required by the Obsidian Local REST API.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(
                    f"{self.base_url}/vault/{path}",
                    headers=self._md_headers,
                    content=content.encode("utf-8"),
                )
                if resp.status_code in (200, 201, 204):
                    logging.getLogger("octopus.memory").info(f"[Memory] Saved note: {path}")
                    return {"status": "saved", "path": path}
                else:
                    err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logging.getLogger("octopus.memory").warning(f"[Memory] Failed to save {path} — {err}")
                    return {"status": "error", "path": path, "error": err}
        except Exception as e:
            logging.getLogger("octopus.memory").warning(f"[Memory] save_note({path}) exception: {e}")
            return {"status": "error", "error": str(e)}

    async def read_note(self, path: str) -> dict:
        resp = await self._request("get", f"/vault/{path}")
        if resp and resp.status_code == 200:
            return {"status": "found", "content": resp.text}
        code = resp.status_code if resp else "no response"
        logging.getLogger("octopus.memory").debug(f"[Memory] read_note({path}) -> {code}")
        return {"status": "not_found", "path": path}

    async def search_vault(self, query: str) -> dict:
        resp = await self._request("post", "/search/simple/", json={"query": query})
        if resp and resp.status_code == 200:
            try:
                return {"status": "ok", "results": resp.json()}
            except Exception:
                pass
        return {"status": "ok", "results": []}

    async def save_chat_history(self, agent_role: str, task_id: str, messages: list) -> dict:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = f"Memory/ChatHistory/{agent_role}/{date_str}_{task_id}.md"
        content = f"# Chat History: {agent_role} -- Task {task_id}\n"
        content += f"**Date:** {date_str}\n\n"
        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("content", "")
            content += f"### {role.upper()}\n{text}\n\n"
        return await self.save_note(path, content)

    async def save_task_context(self, task_id: str, context: dict) -> dict:
        path = f"Memory/ShortTerm/{task_id}.md"
        content = f"# Task Context: {task_id}\n\n```json\n{json.dumps(context, indent=2)}\n```\n"
        return await self.save_note(path, content)

    async def save_solution(self, category: str, title: str, solution: str) -> dict:
        path = f"Memory/LongTerm/Solutions/{category}/{title}.md"
        return await self.save_note(path, solution)

    async def update_working_state(self, task_id: str, state: dict) -> dict:
        path = f"Memory/WorkingState/{task_id}_state.md"
        content = f"# Working State: {task_id}\n\n```json\n{json.dumps(state, indent=2)}\n```\n"
        return await self.save_note(path, content)

    async def health_check(self) -> bool:
        resp = await self._request("get", "/")
        healthy = resp is not None and resp.status_code == 200
        self._healthy = healthy
        status = "CONNECTED" if healthy else "DISCONNECTED"
        code = resp.status_code if resp else "no response"
        logging.getLogger("octopus.memory").info(
            f"[Memory] Obsidian health: {status} (HTTP {code}) at {self.base_url}"
        )
        return healthy

    # ------------------------------------------------------------------
    # Daily note logging helpers
    # ------------------------------------------------------------------

    def _daily_note_path(self, section: str = "Logs") -> str:
        """Return the vault path for today's daily log note."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"Logs/Daily/{date_str}.md"

    async def _read_daily_note(self) -> str:
        """Read today's daily note content, or return a blank template."""
        path = self._daily_note_path()
        resp = await self._request("get", f"/vault/{path}")
        if resp and resp.status_code == 200:
            return resp.text
        # Bootstrap new daily note
        date_str = datetime.now().strftime("%Y-%m-%d")
        template = (
            f"# Octopus V2 — Daily Log {date_str}\n\n"
            "## System\n\n"
            "## Pipeline\n\n"
            "## Conversations\n\n"
        )
        logging.getLogger("octopus.memory").info(f"[Memory] Bootstrapping new daily note: {path}")
        return template

    async def append_to_daily_note(self, section: str, entry: str) -> None:
        """Append a log entry under the given section heading in today's daily note.

        `section` should be one of: 'System', 'Pipeline', 'Conversations'
        `entry`   is a markdown-formatted string (no trailing newline required).
        """
        path = self._daily_note_path()
        content = await self._read_daily_note()

        heading = f"## {section}"
        if heading in content:
            # Insert entry just before the NEXT ## heading (or at end)
            parts = content.split(heading, 1)
            before = parts[0] + heading
            rest = parts[1]
            # Find next section boundary
            next_section_idx = rest.find("\n## ", 1)
            if next_section_idx == -1:
                # Append at end of section (end of file)
                rest = rest.rstrip("\n") + f"\n{entry}\n"
            else:
                rest = rest[:next_section_idx] + f"\n{entry}" + rest[next_section_idx:]
            content = before + rest
        else:
            # Section not found — append section + entry at end
            content = content.rstrip("\n") + f"\n\n{heading}\n\n{entry}\n"

        await self.save_note(path, content)

    async def log_system(self, message: str) -> None:
        """Append a system/console log line to today's daily note."""
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"- `{ts}` {message}"
        try:
            await self.append_to_daily_note("System", entry)
        except Exception:
            pass

    async def log_pipeline_event(self, event: dict) -> None:
        """Append a pipeline event to today's daily note + file log."""
        ts = event.get("timestamp", datetime.now().isoformat())[:19].replace("T", " ")
        from_a = event.get("from_agent", "?")
        to_a = event.get("to_agent", "?")
        etype = event.get("event_type", "?")
        msg = event.get("message", "")[:120]
        task_id = event.get("task_id", "?")

        # File log (always works)
        logging.getLogger("octopus.pipeline").info(
            f"[{etype.upper()}] {task_id} | {from_a} -> {to_a} | {msg}"
        )

        # Obsidian daily note
        entry = f"- `{ts}` **{etype}** `{task_id}` {from_a} → {to_a}: {msg}"
        try:
            await self.append_to_daily_note("Pipeline", entry)
        except Exception:
            pass

    async def log_conversation(self, agent_role: str, task_id: str,
                               user_msg: str, assistant_msg: str,
                               provider: str = "", elapsed_ms: float = 0) -> None:
        """Append a full agent conversation to today's daily note + file log."""
        ts = datetime.now().strftime("%H:%M:%S")
        provider_info = f" via {provider}" if provider else ""
        elapsed_info = f" ({elapsed_ms:.0f} ms)" if elapsed_ms else ""

        # File log (always works)
        logging.getLogger("octopus.conversations").info(
            f"[{agent_role}]{provider_info}{elapsed_info} task={task_id}\n"
            f"  USER: {user_msg[:500]}\n"
            f"  AGENT: {assistant_msg[:1000]}"
        )

        # Obsidian daily note
        provider_md = f" via *{provider}*" if provider else ""
        entry = (
            f"\n### `{ts}` [{agent_role}]{provider_md}{elapsed_info} — Task `{task_id}`\n\n"
            f"**User:** {user_msg[:300]}\n\n"
            f"**Agent:** {assistant_msg[:500]}\n"
        )
        try:
            await self.append_to_daily_note("Conversations", entry)
        except Exception:
            pass


memory_client = ObsidianMemoryClient()


# ---------------------------------------------------------------------------
# Logging handler — redirects Python logging (and print via redirect) to Obsidian
# ---------------------------------------------------------------------------

class ObsidianLogHandler(logging.Handler):
    """A logging.Handler that asynchronously appends records to today's Obsidian daily note."""

    def __init__(self, client: "ObsidianMemoryClient"):
        super().__init__()
        self._client = client
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self._client.log_system(msg), self._loop
                )
        except Exception:
            pass


_obsidian_log_handler: Optional[ObsidianLogHandler] = None


def setup_file_logging() -> None:
    """Set up file-based logging to database/LLM/ with rotating log files.

    Creates separate log files for different concerns:
      - octopus.log        — all system logs (INFO+)
      - memory.log         — memory/Obsidian operations only
      - pipeline.log       — agent delegation and task events
      - conversations.log  — full agent conversations
      - errors.log         — WARNING+ only (quick error triage)
    """
    from logging.handlers import RotatingFileHandler

    os.makedirs(LOG_DIR, exist_ok=True)

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    def _add_file_handler(logger_name: str, filename: str, log_level=None):
        """Add a rotating file handler to a named logger."""
        fh = RotatingFileHandler(
            os.path.join(LOG_DIR, filename),
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        fh.setLevel(log_level or level)
        target = logging.getLogger(logger_name) if logger_name else root_logger
        target.addHandler(fh)
        return fh

    # 1. Main log — everything INFO+
    _add_file_handler("", "octopus.log")

    # 2. Memory log — only octopus.memory messages
    _add_file_handler("octopus.memory", "memory.log")

    # 3. Pipeline log — agent task events
    _add_file_handler("octopus.pipeline", "pipeline.log")

    # 4. Conversations log — full agent chat exchanges
    _add_file_handler("octopus.conversations", "conversations.log")

    # 5. Errors log — WARNING+ from everything (quick triage)
    _add_file_handler("", "errors.log", log_level=logging.WARNING)

    # Also add a StreamHandler to stderr so console still works
    console = logging.StreamHandler(sys.__stderr__)
    console.setFormatter(formatter)
    console.setLevel(level)
    root_logger.addHandler(console)

    logging.getLogger("octopus.memory").info(
        f"[Logging] File logging initialized -> {LOG_DIR}"
    )


def setup_obsidian_logging() -> None:
    """Install the Obsidian log handler on the root logger and redirect print().

    Also initializes file-based logging to database/LLM/.
    """
    global _obsidian_log_handler

    # --- File-based logging (always works, even if Obsidian is down) ---
    setup_file_logging()

    # --- Obsidian daily-note logging ---
    _obsidian_log_handler = ObsidianLogHandler(memory_client)
    _obsidian_log_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _obsidian_log_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.addHandler(_obsidian_log_handler)

    # Redirect built-in print() calls to the Python logging system
    class _PrintToLogger(io.TextIOBase):
        def __init__(self, logger: logging.Logger):
            self._logger = logger
            self._buf = ""

        def write(self, s: str) -> int:
            self._buf += s
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if line.strip():
                    self._logger.info(line)
            return len(s)

        def flush(self) -> None:
            if self._buf.strip():
                self._logger.info(self._buf)
                self._buf = ""

    _print_logger = logging.getLogger("octopus.print")
    sys.stdout = _PrintToLogger(_print_logger)
    print("[Logger] File logging + Obsidian daily log handler installed")


def attach_obsidian_log_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Attach the running event loop to the Obsidian log handler."""
    if _obsidian_log_handler:
        _obsidian_log_handler.set_loop(loop)


async def init_agents():
    """Initialize all 9 agents in the database."""
    for role, info in AGENT_ROLES.items():
        agent_id = f"agent-{role}"
        existing = await fetch_one("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if not existing:
            await execute(
                "INSERT INTO agents (id, role, name, status) VALUES (?, ?, ?, ?)",
                (agent_id, role, info["name"], "idle"),
            )
        agent_states[agent_id] = {
            "role": role,
            "status": "idle",
            "current_task": None,
            "model": info.get("default_model"),
        }
        agent_states[agent_id]["skills"] = [s.name for s in get_skills_for_agent(role)]
        agent_states[agent_id]["mcp_servers"] = [s.name for s in get_servers_for_agent(role)]
        agent_states[agent_id]["memory_access"] = [m.value for m in get_agent_memory_access(role)]
    print(f"[Engine] Initialized {len(AGENT_ROLES)} agents")


async def assign_models():
    """Load model assignments from config and DB. Config always wins."""
    for role, model_id in DEFAULT_MODEL_ASSIGNMENTS.items():
        if model_id:
            await execute(
                "INSERT OR REPLACE INTO model_assignments (role, model_id, benchmark_score) VALUES (?, ?, ?)",
                (role, model_id, 0),
            )
            print(f"[Engine] Assigned {role} -> {model_id}")

    assignments = await fetch_all("SELECT role, model_id FROM model_assignments")
    for a in assignments:
        agent_id = f"agent-{a['role']}"
        if agent_id in agent_states:
            agent_states[agent_id]["model"] = a["model_id"]

    for role, model_id in DEFAULT_MODEL_ASSIGNMENTS.items():
        agent_id = f"agent-{role}"
        if agent_id in agent_states and model_id:
            agent_states[agent_id]["model"] = model_id
            await execute(
                "INSERT OR REPLACE INTO model_assignments (role, model_id, benchmark_score) VALUES (?, ?, ?)",
                (role, model_id, 0),
            )

    return {a["role"]: a["model_id"] for a in assignments}


async def send_to_agent(role: str, task_description: str, task_id: Optional[str] = None) -> dict:
    """Send a task to a specific agent via the correct provider (Claude API or LM Studio)."""
    agent_id = f"agent-{role}"
    state = agent_states.get(agent_id)
    if not state:
        return {"error": f"Agent {role} not found"}

    # Determine which provider this role uses
    provider_name = get_agent_provider(role)

    # Pick the right model for the provider
    if provider_name == "claude_api":
        claude_cfg = get_claude_config()
        model = claude_cfg.default_model  # e.g. "claude-sonnet-4-6"
    else:
        model = state.get("model") or DEFAULT_MODEL_ASSIGNMENTS.get(role)

    if not model:
        return {"error": f"No model assigned to {role}. Check config/settings.py MODEL_ASSIGNMENTS."}

    if not task_id:
        task_id = str(uuid.uuid4())[:8]

    # Update state
    state["status"] = "busy"
    state["current_task"] = task_id
    await execute("UPDATE agents SET status = 'busy', last_active = ? WHERE id = ?",
                  (datetime.now().isoformat(), agent_id))

    # Try to load working context (non-blocking, ignore failures)
    context_block = ""
    try:
        working_context = await memory_client.read_note(f"Memory/WorkingState/{task_id}_state.md")
        if working_context.get("status") == "found":
            context_block = f"\n\n## WORKING CONTEXT\n{working_context['content']}"
    except Exception:
        pass

    # Build enhanced system prompt
    dos_block = "\n".join(f"- {d}" for d in AGENT_DOS)
    donts_block = "\n".join(f"- {d}" for d in AGENT_DONTS)
    skills_block = ", ".join(agent_states[agent_id].get("skills", []))

    system_prompt = SYSTEM_PROMPTS.get(role, "You are a helpful assistant.")
    enhanced_system = f"""{system_prompt}

## YOUR SKILLS
{skills_block}

## RULES
### DO:
{dos_block}

### DON'T:
{donts_block}
{context_block}"""

    messages = [
        {"role": "system", "content": enhanced_system},
        {"role": "user", "content": task_description},
    ]

    # Log pipeline event
    event = {
        "task_id": task_id,
        "from_agent": "orchestrator" if role != "orchestrator" else "user",
        "to_agent": role,
        "event_type": "assign",
        "timestamp": datetime.now().isoformat(),
        "message": task_description[:100],
    }
    pipeline_log.append(event)
    if len(pipeline_log) > 200:
        pipeline_log.pop(0)

    await execute(
        "INSERT INTO pipeline_events (task_id, from_agent, to_agent, event_type, data) VALUES (?, ?, ?, ?, ?)",
        (task_id, event["from_agent"], role, "assign", json.dumps(event)),
    )

    # Log pipeline assignment event to Obsidian daily note (fire-and-forget)
    try:
        asyncio.create_task(memory_client.log_pipeline_event(event))
    except Exception as e:
        logging.getLogger("octopus.memory").warning(f"[Memory] Failed to log pipeline assign: {e}")

    # -----------------------------------------------------------------------
    # Route to the correct provider (Claude API or LM Studio)
    # -----------------------------------------------------------------------
    start_time = time.time()

    try:
        multi = get_multi_client()
        result = await multi.chat(
            provider_name=provider_name,
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
            fallback=True,
        )
        if "error" not in result:
            actual_provider = result.get("provider", provider_name)
            fallback_info = ""
            if result.get("_fallback_from"):
                fallback_info = f" (fallback: {result['_fallback_from']} -> {result['_fallback_to']})"
            print(f"[Engine] {role} answered via {actual_provider}{fallback_info} in {result.get('elapsed_ms', 0):.0f}ms")
            result = {
                "choices": [{"message": {"content": result["content"], "role": "assistant"}}],
                "usage": result.get("usage", {}),
                "model": model,
                "provider": actual_provider,
            }
    except RuntimeError:
        print(f"[Engine] WARNING: MultiProviderClient not ready, falling back to direct LM Studio for {role}")
        result = await lm_client.chat(model, messages)

    elapsed = (time.time() - start_time) * 1000

    # Update state back to idle
    state["status"] = "idle"
    state["current_task"] = None
    await execute("UPDATE agents SET status = 'idle', last_active = ? WHERE id = ?",
                  (datetime.now().isoformat(), agent_id))

    if "error" in result:
        fail_event = {**event, "event_type": "fail", "message": result["error"][:200]}
        pipeline_log.append(fail_event)
        # Log failure event to Obsidian daily note
        try:
            asyncio.create_task(memory_client.log_pipeline_event(fail_event))
        except Exception as e:
            logging.getLogger("octopus.memory").warning(f"[Memory] Failed to log pipeline fail: {e}")
        return {"error": result["error"], "task_id": task_id, "agent": role, "elapsed_ms": elapsed, "provider": provider_name}

    # Extract response
    try:
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
    except (KeyError, IndexError):
        content = str(result)
        usage = {}

    # Log completion
    complete_event = {
        "task_id": task_id,
        "from_agent": role,
        "to_agent": "orchestrator" if role != "orchestrator" else "user",
        "event_type": "complete",
        "timestamp": datetime.now().isoformat(),
        "message": content[:100],
    }
    pipeline_log.append(complete_event)
    await execute(
        "INSERT INTO pipeline_events (task_id, from_agent, to_agent, event_type, data) VALUES (?, ?, ?, ?, ?)",
        (task_id, role, complete_event["to_agent"], "complete", json.dumps(complete_event)),
    )

    # Log completion pipeline event to Obsidian daily note
    try:
        asyncio.create_task(memory_client.log_pipeline_event(complete_event))
    except Exception as e:
        logging.getLogger("octopus.memory").warning(f"[Memory] Failed to log pipeline complete: {e}")

    # Store message
    await execute(
        "INSERT INTO messages (task_id, from_agent, to_agent, role, content) VALUES (?, ?, ?, ?, ?)",
        (task_id, role, "orchestrator", "assistant", content),
    )

    # Save chat history to memory (fire-and-forget)
    try:
        asyncio.create_task(memory_client.save_chat_history(role, task_id, [
            {"role": "user", "content": task_description},
            {"role": "assistant", "content": content}
        ]))
        asyncio.create_task(memory_client.log_conversation(
            agent_role=role,
