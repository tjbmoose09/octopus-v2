@echo off
REM ============================================================
REM  Octopus Agents V2 — Environment Setup (Windows)
REM  Sets up LM Studio + Obsidian Memory + MCP Servers
REM ============================================================

echo [Octopus V2] Setting up environment variables...

REM ----------------------------------------------------------
REM  1. LM STUDIO (Local Provider)
REM ----------------------------------------------------------
REM  LM Studio server must be running: lms server start
set LM_STUDIO_URL=http://localhost:1234
set LM_STUDIO_API_KEY=lm-studio-local-token
set LM_STUDIO_MODEL=nemomix-unleashed-12b
set LM_STUDIO_MAX_TOKENS=4096
set LM_STUDIO_CONTEXT_WINDOW=32768
set LM_STUDIO_TIMEOUT=120

REM ----------------------------------------------------------
REM  2. ORCHESTRATOR MODEL
REM ----------------------------------------------------------
REM  NemoMix Unleashed 12B — replaces text-embedding model
set ORCHESTRATOR_MODEL=nemomix-unleashed-12b

REM ----------------------------------------------------------
REM  3. CLAUDE CODE CLI → LM STUDIO (Anthropic-compatible)
REM ----------------------------------------------------------
set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lm-studio-local-token

REM ----------------------------------------------------------
REM  4. OBSIDIAN MCP MEMORY
REM ----------------------------------------------------------
REM  Obsidian REST API running in Docker on port 27124
set OBSIDIAN_URL=http://localhost:27124
REM Generate inside Obsidian -> Settings -> Local REST API plugin
set OBSIDIAN_API_KEY=your-obsidian-rest-api-key-here
set OBSIDIAN_VAULT=OctopusMemory

REM ----------------------------------------------------------
REM  5. OFFLOADING CONFIG
REM ----------------------------------------------------------
REM  Provider mode: local | cloud | hybrid
set OCTOPUS_PROVIDER_MODE=hybrid

REM  Per-agent provider overrides (lm_studio | claude_api)
REM  Uncomment to customize which agents use cloud vs local:
REM set AGENT_PROVIDER_ORCHESTRATOR=claude_api
REM set AGENT_PROVIDER_DEV=lm_studio
REM set AGENT_PROVIDER_CRITIC=claude_api
REM set AGENT_PROVIDER_RESEARCH=claude_api

REM ----------------------------------------------------------
REM  6. OCTOPUS SERVER
REM ----------------------------------------------------------
set OCTOPUS_HOST=0.0.0.0
set OCTOPUS_PORT=8080

echo.
echo [Octopus V2] Environment configured!
echo   LM Studio:      %LM_STUDIO_URL%
echo   Model:          %LM_STUDIO_MODEL%
echo   Orchestrator:   %ORCHESTRATOR_MODEL%
echo   Provider:       %OCTOPUS_PROVIDER_MODE%
echo   Obsidian:       %OBSIDIAN_URL% (vault: %OBSIDIAN_VAULT%)
echo   Server:         http://%OCTOPUS_HOST%:%OCTOPUS_PORT%
echo.
echo Next steps:
echo   1. Start LM Studio server:  lms server start
echo   2. Load NemoMix Unleashed 12B in LM Studio
echo   3. Verify Obsidian Docker:   docker ps
echo   4. Run backend:              python run.py
echo   5. Run frontend:             cd frontend ^&^& npm run dev
