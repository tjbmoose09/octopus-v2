#!/usr/bin/env bash
# ============================================================
#  Octopus Agents V2 — Environment Setup (macOS/Linux/WSL)
#  Sets up LM Studio + Obsidian Memory + MCP Servers
# ============================================================
# Usage: source setup_env.sh

echo "[Octopus V2] Setting up environment variables..."

# ----------------------------------------------------------
#  1. LM STUDIO (Local Provider)
# ----------------------------------------------------------
#  LM Studio server must be running: lms server start
export LM_STUDIO_URL="http://localhost:1234"
export LM_STUDIO_API_KEY="lm-studio-local-token"
export LM_STUDIO_MODEL="nemomix-unleashed-12b"
export LM_STUDIO_MAX_TOKENS=4096
export LM_STUDIO_CONTEXT_WINDOW=32768
export LM_STUDIO_TIMEOUT=120

# ----------------------------------------------------------
#  2. ORCHESTRATOR MODEL
# ----------------------------------------------------------
#  NemoMix Unleashed 12B — replaces text-embedding model
export ORCHESTRATOR_MODEL="nemomix-unleashed-12b"

# ----------------------------------------------------------
#  3. CLAUDE CODE CLI → LM STUDIO (Anthropic-compatible)
# ----------------------------------------------------------
export ANTHROPIC_BASE_URL="http://localhost:1234"
export ANTHROPIC_AUTH_TOKEN="lm-studio-local-token"

# ----------------------------------------------------------
#  4. OBSIDIAN MCP MEMORY
# ----------------------------------------------------------
#  Obsidian REST API running in Docker on port 27124
export OBSIDIAN_URL="http://localhost:27124"
# Generate inside Obsidian -> Settings -> Local REST API plugin
export OBSIDIAN_API_KEY="your-obsidian-rest-api-key-here"
export OBSIDIAN_VAULT="OctopusMemory"

# ----------------------------------------------------------
#  5. OFFLOADING CONFIG
# ----------------------------------------------------------
#  Provider mode: local | cloud | hybrid
export OCTOPUS_PROVIDER_MODE="hybrid"

#  Per-agent provider overrides (lm_studio | claude_api)
#  Uncomment to customize which agents use cloud vs local:
# export AGENT_PROVIDER_ORCHESTRATOR="claude_api"
# export AGENT_PROVIDER_DEV="lm_studio"
# export AGENT_PROVIDER_CRITIC="claude_api"
# export AGENT_PROVIDER_RESEARCH="claude_api"

# ----------------------------------------------------------
#  6. OCTOPUS SERVER
# ----------------------------------------------------------
export OCTOPUS_HOST="0.0.0.0"
export OCTOPUS_PORT=8080

echo ""
echo "[Octopus V2] Environment configured!"
echo "  LM Studio:      $LM_STUDIO_URL"
echo "  Model:          $LM_STUDIO_MODEL"
echo "  Orchestrator:   $ORCHESTRATOR_MODEL"
echo "  Provider:       $OCTOPUS_PROVIDER_MODE"
echo "  Obsidian:       $OBSIDIAN_URL (vault: $OBSIDIAN_VAULT)"
echo "  Server:         http://$OCTOPUS_HOST:$OCTOPUS_PORT"
echo ""
echo "Next steps:"
echo "  1. Start LM Studio server:  lms server start"
echo "  2. Load NemoMix Unleashed 12B in LM Studio"
echo "  3. Verify Obsidian Docker:   docker ps"
echo "  4. Run backend:              python run.py"
echo "  5. Run frontend:             cd frontend && npm run dev"
