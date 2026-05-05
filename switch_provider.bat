@echo off
REM ============================================================
REM  Quick-switch: Toggle Claude Code between LOCAL and CLOUD
REM ============================================================
REM  Usage:
REM    switch_provider.bat local   — Route claude CLI to LM Studio
REM    switch_provider.bat cloud   — Route claude CLI to Anthropic API
REM    switch_provider.bat hybrid  — Use both (offload heavy tasks)
REM    switch_provider.bat status  — Show current config
REM ============================================================

if "%1"=="local" goto :local
if "%1"=="cloud" goto :cloud
if "%1"=="hybrid" goto :hybrid
if "%1"=="status" goto :status
goto :usage

:local
echo [Switch] Routing Claude Code CLI + Octopus → LM Studio (LOCAL)
set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lm-studio-local-token
set OCTOPUS_PROVIDER_MODE=local
set LM_STUDIO_MODEL=nemomix-unleashed-12b
set ORCHESTRATOR_MODEL=nemomix-unleashed-12b
echo   Provider mode: LOCAL
echo   Model: %ORCHESTRATOR_MODEL%
echo   All agents use LM Studio — zero API usage
echo   Done. Run: python run.py
goto :eof

:cloud
echo [Switch] Routing Claude Code CLI + Octopus → Anthropic API (CLOUD)
set ANTHROPIC_BASE_URL=https://api.anthropic.com
set ANTHROPIC_AUTH_TOKEN=
set OCTOPUS_PROVIDER_MODE=cloud
set ORCHESTRATOR_MODEL=claude-sonnet-4-6
echo   Provider mode: CLOUD
echo   Orchestrator: %ORCHESTRATOR_MODEL%
echo   All agents use Anthropic API
echo   Note: Make sure ANTHROPIC_API_KEY is set or log in with: claude login
goto :eof

:hybrid
echo [Switch] Routing Octopus → Hybrid (LOCAL + CLOUD)
set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lm-studio-local-token
set OCTOPUS_PROVIDER_MODE=hybrid
set LM_STUDIO_MODEL=nemomix-unleashed-12b
set ORCHESTRATOR_MODEL=nemomix-unleashed-12b
echo   Provider mode: HYBRID
echo   Brain tier (orchestrator, critic, research) → Claude API
echo   Arm tier (dev, qa, pm, review, devops, automation) → LM Studio
echo   Done. Run: python run.py
goto :eof

:status
echo.
echo =============== Octopus V2 Provider Status ===============
echo.
echo   ANTHROPIC_BASE_URL  = %ANTHROPIC_BASE_URL%
echo   PROVIDER_MODE       = %OCTOPUS_PROVIDER_MODE%
echo   LM_STUDIO_URL       = %LM_STUDIO_URL%
echo   LM_STUDIO_MODEL     = %LM_STUDIO_MODEL%
echo   ORCHESTRATOR_MODEL  = %ORCHESTRATOR_MODEL%
echo   OBSIDIAN_URL        = %OBSIDIAN_URL%
echo   OBSIDIAN_VAULT      = %OBSIDIAN_VAULT%
echo   OCTOPUS_PORT        = %OCTOPUS_PORT%
echo.
echo ============= MCP Memory ==============
echo   Obsidian MCP:  %OBSIDIAN_URL%
echo   Vault:         %OBSIDIAN_VAULT%
echo.
goto :eof

:usage
echo Usage: switch_provider.bat [local^|cloud^|hybrid^|status]
echo   local  — All agents use LM Studio (no API usage)
echo   cloud  — All agents use Anthropic API
echo   hybrid — Brain tier uses API, arms use LM Studio (default)
echo   status — Show current configuration
goto :eof
