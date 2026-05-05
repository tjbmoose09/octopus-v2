"""Octopus Agents V2 — FastAPI Application"""

import asyncio
import json
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

# Fix imports
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from database.db import init_db, fetch_all, fetch_one, execute
from agents.engine import (
    init_agents, assign_models, send_to_agent,
    agent_states, pipeline_log, lm_client, get_agent_info, get_memory_status, memory_client,
    init_multi_provider, get_multi_client,
    setup_obsidian_logging, attach_obsidian_log_loop,
)
from agents.multi_provider_client import MultiProviderClient
from benchmark.runner import benchmark_runner
from config.settings import AGENT_ROLES, HOST, PORT
from config.providers import (
    get_all_providers, get_agent_provider, RECOMMENDED_MODELS, ProviderType
)
from config.zones import (
    SessionZoneState, ZoneBoundaryError,
    get_active_zone, ui_theme_for_zone, zone_bridge_allowed,
)

# multi_client is now owned by engine.py — we get a reference after init
multi_client: Optional[MultiProviderClient] = None

# ---------------------------------------------------------------------------
# V2.2 session state — single-user desktop app, so one in-memory SessionZoneState
# is enough. If we ever go multi-user we'll key this by auth token.
# ---------------------------------------------------------------------------
_SESSION: SessionZoneState = SessionZoneState()


def get_session() -> SessionZoneState:
    """Accessor so engine and routes pull the same live state object."""
    return _SESSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    global multi_client
    await init_db()
    await init_agents()
    await assign_models()
    # Initialize the shared multi-provider client (used by engine.send_to_agent)
    multi_client = await init_multi_provider()
    # Set up Obsidian daily-note logging (system logs, pipeline events, conversations)
    setup_obsidian_logging()
    attach_obsidian_log_loop(asyncio.get_event_loop())
    print(f"[Octopus V2] Ready at http://{HOST}:{PORT}")
    yield
    if multi_client:
        await multi_client.close()
    print("[Octopus V2] Shutting down")


app = FastAPI(title="Octopus Agents V2", lifespan=lifespan)

# NOTE (V2.2): The legacy ``dashboard/`` static mount has been retired.
# The React/Vite frontend (``frontend/``) is now the single UI surface.
# In dev: ``npm run dev`` inside ``frontend/`` → http://localhost:3000
# In prod: the built assets are served by the frontend's own server (e.g.
# Vite preview, nginx, or Electron shell). This FastAPI app is API-only.


# === Pydantic Models ===

class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = None  # If None, goes to orchestrator


class BenchmarkRequest(BaseModel):
    models: Optional[list] = None
    roles: Optional[list] = None


# === Routes ===

@app.get("/")
async def root():
    """API root — the UI lives on the Vite frontend, not here.

    Returns a JSON pointer so developers hitting the bare API host
    immediately understand where the UI is and where the OpenAPI docs are.
    """
    return JSONResponse({
        "service": "Octopus Agents V2",
        "role": "API server",
        "ui_url": "http://localhost:3000",  # Vite dev server
        "openapi_docs": "/docs",
        "websocket": "/ws",
        "status_endpoint": "/api/status",
    })


@app.get("/api/status")
async def get_status():
    """Overall system status."""
    lm_healthy = await lm_client.health()
    models = []
    lm_error = None
    if lm_healthy:
        models_resp = await lm_client.list_models()
        models = models_resp.get("data", [])
        lm_error = models_resp.get("error")
    else:
        lm_error = f"Cannot reach LM Studio at {lm_client.base_url}"

    return {
        "status": "online",
        "lm_studio_connected": lm_healthy and len(models) > 0,
        "lm_studio_url": lm_client.base_url,
        "lm_studio_error": lm_error,
        "models_available": len(models),
        "models": [m.get("id", "unknown") for m in models],
        "agents": len(agent_states),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/agents")
async def get_agents():
    """Get all agents with their current state."""
    agents = []
    for role, info in AGENT_ROLES.items():
        agent_id = f"agent-{role}"
        state = agent_states.get(agent_id, {})
        db_agent = await fetch_one("SELECT * FROM agents WHERE id = ?", (agent_id,))
        assignment = await fetch_one("SELECT model_id, benchmark_score FROM model_assignments WHERE role = ?", (role,))

        agents.append({
            "id": agent_id,
            "role": role,
            "name": info["name"],
            "emoji": info["emoji"],
            "color": info["color"],
            "description": info["description"],
            "tier": info["tier"],
            "status": state.get("status", "offline"),
            "current_task": state.get("current_task"),
            "model": assignment["model_id"] if assignment else None,
            "benchmark_score": assignment["benchmark_score"] if assignment else None,
            "last_active": db_agent["last_active"] if db_agent else None,
        })
    return {"agents": agents}


@app.get("/api/models")
async def get_models():
    """Proxy to LM Studio — list models."""
    return await lm_client.list_models()


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Send a message. If agent specified, direct to that agent. Otherwise orchestrate."""
    try:
        if req.agent:
            result = await send_to_agent(req.agent, req.message)
        else:
            result = await orchestrate(req.message)
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Chat failed: {str(e)}"},
        )


async def orchestrate(message: str) -> dict:
    """Route a user message through the orchestrator agent.

    The orchestrator analyses the request, decides which sub-agents to involve,
    and returns a synthesised response.  For now this is a single-turn call to
    the orchestrator role; multi-step delegation will be layered on top later.
    """
    # Step 1 — let the orchestrator think about the task
    orch_result = await send_to_agent("orchestrator", message)

    if "error" in orch_result:
        return orch_result  # propagate error as-is; frontend handles data.error

    return {
        "task_id": orch_result.get("task_id"),
        "agent": "orchestrator",
        "orchestrator_response": orch_result.get("response") or orch_result.get("content", ""),
        "response": orch_result.get("response") or orch_result.get("content", ""),
        "content": orch_result.get("content", ""),
        "model": orch_result.get("model"),
        "provider": orch_result.get("provider"),
        "elapsed_ms": orch_result.get("elapsed_ms"),
        "usage": orch_result.get("usage", {}),
    }


@app.post("/api/agent/{role}/task")
async def assign_task(role: str, req: ChatRequest):
    """Send a task directly to a specific agent."""
    if role not in AGENT_ROLES:
        raise HTTPException(404, f"Unknown role: {role}")
    return await send_to_agent(role, req.message)


@app.get("/api/pipeline")
async def get_pipeline():
    """Get recent pipeline events."""
    return {"events": pipeline_log[-50:]}


@app.get("/api/pipeline/history")
async def get_pipeline_history():
    """Get pipeline events from DB."""
    events = await fetch_all(
        "SELECT * FROM pipeline_events ORDER BY timestamp DESC LIMIT 100"
    )
    return {"events": events}


@app.get("/api/tasks")
async def get_tasks():
    """Get all tasks."""
    tasks = await fetch_all("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50")
    return {"tasks": tasks}


@app.get("/api/messages/{task_id}")
async def get_messages(task_id: str):
    """Get messages for a task."""
    messages = await fetch_all(
        "SELECT * FROM messages WHERE task_id = ? ORDER BY timestamp", (task_id,)
    )
    return {"messages": messages}


# === Benchmark Endpoints ===

@app.post("/api/benchmark/run")
async def run_benchmark():
    """Start a full benchmark run."""
    if benchmark_runner.status == "running":
        return {"status": "already_running", "progress": benchmark_runner.progress}

    # Run in background
    asyncio.create_task(_run_benchmark_bg())
    return {"status": "started", "message": "Benchmark started. Poll /api/benchmark/status for progress."}


async def _run_benchmark_bg():
    result = await benchmark_runner.run_full_benchmark()
    # Update agent model assignments
    await assign_models()


@app.get("/api/benchmark/status")
async def benchmark_status():
    """Get current benchmark progress."""
    return {
        "status": benchmark_runner.status,
        "progress": benchmark_runner.progress,
        "results": benchmark_runner.results if benchmark_runner.status == "complete" else [],
    }


@app.get("/api/benchmark/results")
async def benchmark_results():
    """Get benchmark results and assignments."""
    results = await fetch_all("SELECT * FROM benchmarks ORDER BY timestamp DESC")
    assignments = await fetch_all("SELECT * FROM model_assignments")
    return {"results": results, "assignments": assignments}


@app.get("/api/system")
async def system_info():
    """Get system resource info."""
    return benchmark_runner.get_system_info()


# === Provider Management Endpoints ===

@app.get("/api/providers")
async def get_providers():
    """Get all configured providers and their status.
    Returns flat dict { name: { healthy, model } } for the SystemStatus frontend."""
    try:
        status = await multi_client.get_status()
    except Exception:
        status = {}

    # Build a flat dict the frontend can iterate over
    flat = {}
    if isinstance(status, dict):
        for name, info in status.items():
            if isinstance(info, dict):
                flat[name] = info
            else:
                flat[name] = {"healthy": False, "model": str(info)}

    # Always include LM Studio status
    lm_healthy = await lm_client.health()
    flat["LM Studio"] = {
        "healthy": lm_healthy,
        "model": AGENT_ROLES.get("orchestrator", {}).get("default_model", ""),
    }

    # Include Obsidian memory status
    mem_healthy = await memory_client.health_check()
    flat["Obsidian Memory"] = {
        "healthy": mem_healthy,
        "model": "obsidian-mcp",
    }

    return flat


@app.get("/api/providers/{provider_name}/models")
async def get_provider_models(provider_name: str):
    """List models available from a specific provider."""
    return await multi_client.list_models(provider_name)


@app.get("/api/providers/{provider_name}/health")
async def provider_health(provider_name: str):
    """Health check a specific provider."""
    healthy = await multi_client.health_check(provider_name)
    return {"provider": provider_name, "healthy": healthy}


# === Project Board Endpoints ===

@app.get("/api/projects")
async def get_projects():
    """Get all projects on the board."""
    projects = await fetch_all("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100")
    # Group by status for kanban
    board = {"backlog": [], "in_progress": [], "review": [], "completed": [], "failed": []}
    for p in projects:
        status = p.get("status", "pending")
        if status in ("pending", "blocked"):
            board["backlog"].append(p)
        elif status == "in_progress":
            board["in_progress"].append(p)
        elif status == "review":
            board["review"].append(p)
        elif status == "completed":
            board["completed"].append(p)
        elif status == "failed":
            board["failed"].append(p)
    return {"board": board, "total": len(projects)}


# === File Upload Endpoint ===

@app.post("/api/upload")
async def upload_file():
    """Placeholder for file upload — returns upload instructions."""
    return {
        "message": "Upload endpoint ready. Use multipart/form-data to upload files.",
        "supported": ["py", "js", "ts", "html", "css", "json", "txt", "md", "png", "jpg", "csv"],
    }


# === Device Discovery Endpoint ===

@app.get("/api/devices")
async def get_devices():
    """Discover devices on localhost network."""
    import subprocess
    devices = []
    try:
        # ARP table scan for local network
        result = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if "(" in line and ")" in line:
                parts = line.split()
                hostname = parts[0] if not parts[0].startswith("(") else "unknown"
                ip = line.split("(")[1].split(")")[0] if "(" in line else ""
                mac = ""
                for p in parts:
                    if len(p) == 17 and ":" in p:
                        mac = p
                        break
                if ip:
                    devices.append({
                        "hostname": hostname,
                        "ip": ip,
                        "mac": mac,
                        "status": "online",
                    })
    except Exception as e:
        devices.append({"error": str(e)})

    # Always include localhost
    devices.insert(0, {
        "hostname": "localhost (this machine)",
        "ip": "127.0.0.1",
        "mac": "local",
        "status": "online",
    })
    return {"devices": devices, "count": len(devices)}


# === LM Studio Model Management ===

@app.post("/api/models/load")
async def load_model_endpoint(body: dict):
    """Load a model into LM Studio."""
    model = body.get("model", "")
    if not model:
        raise HTTPException(400, "model field required")
    return await lm_client.load_model(model)


@app.post("/api/models/download")
async def download_model_endpoint(body: dict):
    """Download a model in LM Studio."""
    model = body.get("model", "")
    if not model:
        raise HTTPException(400, "model field required")
    return await lm_client.download_model(model)


@app.get("/api/models/download/status/{job_id}")
async def download_status_endpoint(job_id: str):
    """Check model download status."""
    return await lm_client.download_status(job_id)


# === Skills & MCP Endpoints ===

@app.get("/api/agent/{role}/info")
async def agent_info(role: str):
    """Get full agent info including skills, MCP access, memory."""
    try:
        info = await get_agent_info(role)
        return info
    except KeyError:
        return JSONResponse(status_code=404, content={"error": f"Unknown agent role: {role}"})


@app.get("/api/skills")
async def list_all_skills():
    """List all skills across all agents."""
    from config.skills import AGENT_SKILLS
    result = {}
    for role, skills in AGENT_SKILLS.items():
        result[role] = [{"name": s.name, "display_name": s.display_name, "description": s.description, "category": s.category, "source": s.source, "runtime": s.runtime, "autonomous": s.autonomous} for s in skills]
    return result


@app.get("/api/mcp/servers")
async def list_mcp_servers():
    """List all configured MCP servers."""
    from config.mcp_servers import MCP_SERVERS
    result = {}
    for category, servers in MCP_SERVERS.items():
        result[category] = [{"name": s.name, "description": s.description, "transport": s.transport, "url": s.url, "enabled": s.enabled, "requires_auth": s.requires_auth} for s in servers]
    return result


@app.get("/api/mcp/routing")
async def mcp_routing():
    """Get agent-to-MCP server routing map."""
    from config.mcp_servers import MCP_AGENT_ROUTING
    return MCP_AGENT_ROUTING


@app.get("/api/memory/status")
async def memory_status():
    """Get Obsidian memory system status."""
    return await get_memory_status()


@app.post("/api/memory/search")
async def memory_search(body: dict):
    """Search the memory vault."""
    query = body.get("query", "")
    if not query:
        return JSONResponse(status_code=400, content={"error": "query is required"})
    return await memory_client.search_vault(query)


@app.get("/api/config/dos-donts")
async def get_dos_donts():
    """Get agent behavior rules."""
    from config.settings import AGENT_DOS, AGENT_DONTS
    return {"dos": AGENT_DOS, "donts": AGENT_DONTS}


# === V2.2 Session / Zone Endpoints ===========================================
# These back the frontend's useZone() hook. The UI keeps its own optimistic
# copy in localStorage and POSTs here so the engine's can_route() check sees
# the same state. Also exposes a one-shot bridge so the orchestrator can
# cross the mainline ↔ hacker-zone boundary for audited cooperation.

class SessionZoneReq(BaseModel):
    hacker_zone_active: bool
    reason: Optional[str] = None


class BridgeOpenReq(BaseModel):
    reason: Optional[str] = ""


def _zone_snapshot() -> dict:
    """Serializable view of the live SessionZoneState."""
    s = get_session()
    active = get_active_zone(s)
    return {
        "active_zone": active,
        "hacker_zone_active": s.hacker_zone_active,
        "bridge_open": s.bridge_open,
        "bridge_reason": s.bridge_reason,
        "recent_bridges": list(s.recent_bridges),
        "theme": ui_theme_for_zone(active),
    }


@app.get("/api/session")
async def session_state():
    """Current zone/bridge state — the frontend hook polls this on load."""
    return _zone_snapshot()


@app.post("/api/session/zone")
async def set_session_zone(req: SessionZoneReq):
    """Toggle whether the Hacker Zone panel is active for this session.

    Mainline is the safe default. Flipping to hacker_zone_active=True makes
    HZ agents visible + routable and also swaps the engine's memory namespace
    on the next task. The UI already re-themes optimistically; this endpoint
    is what actually makes can_route() allow HZ targets.
    """
    s = get_session()
    s.hacker_zone_active = bool(req.hacker_zone_active)
    # Flipping zones always closes any open bridge — callers must re-open it
    # explicitly so the audit log captures the crossover.
    if s.bridge_open:
        s.close_bridge()
    return _zone_snapshot()


@app.post("/api/session/bridge/open")
async def open_bridge(req: BridgeOpenReq):
    """Open a one-shot bridge so the orchestrator can call the opposite zone."""
    get_session().open_bridge(req.reason or "manual bridge")
    return _zone_snapshot()


@app.post("/api/session/bridge/close")
async def close_bridge():
    """Close the bridge (safe even if it wasn't open)."""
    get_session().close_bridge()
    return _zone_snapshot()


# === V2.2 /api/send — the ChatV2 page dispatches here ========================
# Thin wrapper over send_to_agent that threads the live SessionZoneState so
# zone enforcement is honored.

class SendReq(BaseModel):
    agent: Optional[str] = None
    task: str


@app.post("/api/send")
async def send(req: SendReq):
    target = (req.agent or "orchestrator").strip()
    try:
        result = await send_to_agent(target, req.task, session=get_session())
    except ZoneBoundaryError as e:
        return JSONResponse(status_code=403, content={
            "error": str(e),
            "kind": "zone_boundary",
            "zone": _zone_snapshot(),
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    return result


# === V2.2 Workflow stubs: Email + Calendar ===================================
# These are intentionally lightweight. Email endpoints return a structured
# "not-connected" payload the UI renders gracefully (see EmailPage.jsx's
# error banner). Calendar events are persisted to a JSON file so the
# /calendar page works end-to-end in dev without any external integration.

import uuid as _uuid

EMAIL_NOT_CONNECTED = {
    "threads": [],
    "messages": [],
    "connected": False,
    "error": (
        "Gmail is not connected to the backend yet. Connect a Gmail MCP server "
        "in config/mcp_servers.py and wire /api/email/* to it to populate this "
        "inbox."
    ),
}


@app.get("/api/email/inbox")
async def email_inbox(limit: int = 25):
    # TODO: wire to Gmail MCP connector once available. For now the UI
    # degrades gracefully to an empty inbox + the error hint below.
    return EMAIL_NOT_CONNECTED


@app.post("/api/email/compose")
async def email_compose(body: dict):
    return JSONResponse(status_code=503, content={
        "error": "Gmail sender not connected. Draft saved locally.",
        "draft": body,
    })


@app.post("/api/email/triage")
async def email_triage(body: dict):
    """Ask the PM agent to summarize + assign priority + draft a reply.

    We don't have the message text server-side until Gmail is wired, so we
    return an instructive stub. Once /api/email/inbox returns real threads,
    this should fetch the thread by message_id and feed the body into the
    orchestrator.
    """
    message_id = (body or {}).get("message_id")
    return {
        "message_id": message_id,
        "summary": (
            "(stub) Connect the Gmail MCP to enable AI triage. The PM agent "
            "will read the thread, summarize it, and draft a reply."
        ),
        "priority": "P3",
        "reply": "",
        "connected": False,
    }


# Calendar file-backed store — lives next to the main DB so the dev user
# gets persistence for free. Safe to delete; it's recreated on next write.
_CAL_PATH = ROOT / "memory" / "calendar_events.json"


def _cal_load() -> list[dict]:
    try:
        if _CAL_PATH.exists():
            return json.loads(_CAL_PATH.read_text("utf-8"))
    except Exception:
        pass
    return []


def _cal_save(events: list[dict]) -> None:
    _CAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CAL_PATH.write_text(json.dumps(events, indent=2, ensure_ascii=False), "utf-8")


@app.get("/api/calendar/events")
async def calendar_list(start: Optional[str] = None, end: Optional[str] = None):
    events = _cal_load()
    # If a window was provided, filter client-side — cheap given the scale.
    if start or end:
        def in_window(e: dict) -> bool:
            s = e.get("start", "")
            if start and s < start:
                return False
            if end and s > end:
                return False
            return True
        events = [e for e in events if in_window(e)]
    return {"events": events}


@app.post("/api/calendar/events")
async def calendar_add(body: dict):
    events = _cal_load()
    evt = dict(body or {})
    evt.setdefault("id", f"evt_{_uuid.uuid4().hex[:10]}")
    evt.setdefault("created_at", datetime.now().isoformat())
    events.append(evt)
    _cal_save(events)
    return evt


@app.delete("/api/calendar/events/{event_id}")
async def calendar_delete(event_id: str):
    events = _cal_load()
    new_events = [e for e in events if e.get("id") != event_id]
    _cal_save(new_events)
    return {"deleted": event_id, "remaining": len(new_events)}


# === WebSocket for real-time updates ===



# === WebSocket for real-time updates ===

connected_clients: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # Send periodic state updates
            data = {
                "type": "state_update",
                "agents": {
                    role: {
                        "status": state.get("status", "offline"),
                        "current_task": state.get("current_task"),
                        "model": state.get("model"),
                    }
                    for role, state in [
                        (aid.replace("agent-", ""), s) for aid, s in agent_states.items()
                    ]
                },
                "pipeline_events": pipeline_log[-10:],
                "benchmark_status": benchmark_runner.status,
                "benchmark_progress": benchmark_runner.progress,
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_json(data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


# === Run ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=True)
