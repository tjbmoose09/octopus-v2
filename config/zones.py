"""Octopus V2.2 — Zone Routing Rules

Enforces the mainline / hacker-zone isolation boundary at the routing level.
This module is the single source of truth for "which agents can this agent
talk to right now?" — the engine consults it before dispatching any task.

Design principles:
- Hacker Zone (HZ) agents are powerful but sometimes uncensored / abliterated.
  They live in the mesh, but are only invoked when the user has the Hacker
  Zone UI panel active (i.e., explicit opt-in per session).
- Mainline agents never route to HZ agents, regardless of user state.
- HZ agents never route to mainline agents — they stay sandboxed. They can
  write to a private HZ memory namespace but cannot touch the main project
  memory without explicit bridge calls made by the orchestrator.
- The only agent permitted to cross the boundary is the `orchestrator` /
  `hz_orchestrator` pair, and only via an audited bridge call.

Usage from engine.py:
    from config.zones import (
        get_active_zone, can_route, zone_bridge_allowed,
        MAINLINE_ZONE, HACKER_ZONE,
    )

    active = get_active_zone(session_ctx)
    if not can_route(source_role, target_role, active):
        raise ZoneBoundaryError(...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional, Set

# -------------------------------------------------------------------------
# Zone identifiers — imported by agents_expanded.py as well. Keep them as
# simple strings so they serialize cleanly into SQLite and over websockets.
# -------------------------------------------------------------------------

MAINLINE_ZONE = "mainline"
HACKER_ZONE = "hacker_zone"

ALL_ZONES = (MAINLINE_ZONE, HACKER_ZONE)


class ZoneBoundaryError(RuntimeError):
    """Raised when a routing attempt crosses a forbidden zone boundary."""


# -------------------------------------------------------------------------
# SessionZoneState — owned by the API layer, mutated when the user toggles
# the Hacker Zone panel. Engine treats it as read-only.
# -------------------------------------------------------------------------

@dataclass
class SessionZoneState:
    """Live zone state for a single user session."""

    hacker_zone_active: bool = False
    # When true, the orchestrator is allowed to make a one-shot bridged call
    # into the opposite zone (audited + logged). Auto-resets to False after
    # the bridged call completes.
    bridge_open: bool = False
    # Optional reason string shown in the UI + written to the audit log.
    bridge_reason: Optional[str] = None
    # Tracks bridged-call history for this session — small ring buffer.
    recent_bridges: list = field(default_factory=list)

    def open_bridge(self, reason: str) -> None:
        self.bridge_open = True
        self.bridge_reason = reason

    def close_bridge(self) -> None:
        # Keep a compact audit trail.
        if self.bridge_reason:
            self.recent_bridges.append(self.bridge_reason)
            self.recent_bridges = self.recent_bridges[-20:]
        self.bridge_open = False
        self.bridge_reason = None


# -------------------------------------------------------------------------
# Zone lookup — engines call this with a role id to discover the zone.
# agents_expanded.py populates _ROLE_TO_ZONE at import time.
# -------------------------------------------------------------------------

_ROLE_TO_ZONE: dict[str, str] = {}


def register_role(role_id: str, zone: str) -> None:
    """Register a role's zone. Called by config modules at import time."""
    if zone not in ALL_ZONES:
        raise ValueError(f"Unknown zone: {zone!r}. Must be one of {ALL_ZONES}")
    _ROLE_TO_ZONE[role_id] = zone


def zone_for_role(role_id: str, default: str = MAINLINE_ZONE) -> str:
    """Return the zone for a given role id, defaulting to mainline."""
    return _ROLE_TO_ZONE.get(role_id, default)


def roles_in_zone(zone: str) -> Set[str]:
    """Return every role id registered in the given zone."""
    return {r for r, z in _ROLE_TO_ZONE.items() if z == zone}


def all_registered_roles() -> Set[str]:
    return set(_ROLE_TO_ZONE.keys())


# -------------------------------------------------------------------------
# Routing decisions
# -------------------------------------------------------------------------

# Roles permitted to cross the boundary via a bridge. Everyone else is
# boundary-rigid.
BRIDGE_CAPABLE_ROLES: Set[str] = {
    "orchestrator",
    "hz_orchestrator",
}


def get_active_zone(session: Optional[SessionZoneState]) -> str:
    """Return the zone the user is currently operating in.

    If no session state is provided, we assume mainline — safer default.
    """
    if session is None:
        return MAINLINE_ZONE
    return HACKER_ZONE if session.hacker_zone_active else MAINLINE_ZONE


def can_invoke_role(role_id: str, active_zone: str) -> bool:
    """Can the active session even see/invoke this role?

    Hacker-zone roles are invisible to a mainline session (not just
    unroutable — they don't show up in pickers, don't appear in status).
    """
    role_zone = zone_for_role(role_id)
    if role_zone == MAINLINE_ZONE:
        return True  # Mainline roles always invokable
    # HZ roles only invokable when HZ panel is active
    return active_zone == HACKER_ZONE


def can_route(
    source_role: str,
    target_role: str,
    active_zone: str,
    session: Optional[SessionZoneState] = None,
) -> bool:
    """Can source_role delegate a task to target_role right now?

    Three checks:
    1. The target role is invokable in the current active zone.
    2. Source and target are in the same zone -- OR --
       one end is bridge-capable AND session.bridge_open is True.
    """
    if not can_invoke_role(target_role, active_zone):
        return False

    src_zone = zone_for_role(source_role)
    tgt_zone = zone_for_role(target_role)

    if src_zone == tgt_zone:
        return True

    # Cross-zone: require both ends bridge-capable AND an open bridge.
    if session is None or not session.bridge_open:
        return False
    return source_role in BRIDGE_CAPABLE_ROLES and target_role in BRIDGE_CAPABLE_ROLES


def zone_bridge_allowed(source_role: str, target_role: str) -> bool:
    """Would a bridge be *possible* between these two roles if opened?

    Used by the UI to decide whether to show a "Bridge to HZ" button.
    """
    return source_role in BRIDGE_CAPABLE_ROLES and target_role in BRIDGE_CAPABLE_ROLES


# -------------------------------------------------------------------------
# Memory namespaces — each zone gets isolated memory directories/tables.
# -------------------------------------------------------------------------

MEMORY_NAMESPACE: dict[str, dict[str, str]] = {
    MAINLINE_ZONE: {
        "sqlite_db": "octopus.db",
        "markdown_root": "memory/long_term",
        "chroma_collection": "octopus_rag",
        "episodic_root": "memory/episodic",
    },
    HACKER_ZONE: {
        "sqlite_db": "octopus_hz.db",
        "markdown_root": "memory/hz_long_term",
        "chroma_collection": "octopus_hz_rag",
        "episodic_root": "memory/hz_episodic",
    },
}


def memory_paths_for_zone(zone: str) -> dict[str, str]:
    if zone not in MEMORY_NAMESPACE:
        raise ValueError(f"Unknown zone: {zone!r}")
    return dict(MEMORY_NAMESPACE[zone])  # copy so callers don't mutate


# -------------------------------------------------------------------------
# UI helper — returns the color language for a zone, used by the neural-link
# Brain Mesh visual to tint nodes differently.
# -------------------------------------------------------------------------

ZONE_UI_THEME: dict[str, dict[str, str]] = {
    MAINLINE_ZONE: {
        "node_color": "#00e5ff",      # cyan
        "edge_color": "#4e6fff",      # blue-violet
        "glow": "#00e5ff66",
        "label": "Mainline Mesh",
    },
    HACKER_ZONE: {
        "node_color": "#ff2d7a",      # hot pink / red
        "edge_color": "#7a00ff",      # deep violet
        "glow": "#ff2d7a55",
        "label": "Hacker Zone",
    },
}


def ui_theme_for_zone(zone: str) -> dict[str, str]:
    return dict(ZONE_UI_THEME.get(zone, ZONE_UI_THEME[MAINLINE_ZONE]))


# -------------------------------------------------------------------------
# Bootstrapping — agents_expanded.py calls register_zones_from_config()
# after its role dict is defined, so this module is always authoritative.
# -------------------------------------------------------------------------

def register_zones_from_config(expanded_roles: dict) -> None:
    """Populate _ROLE_TO_ZONE from EXPANDED_AGENT_ROLES + settings.AGENT_ROLES.

    expanded_roles should be a mapping of role_id -> role_meta where each
    role_meta has a ``zone`` key. Roles missing a zone default to mainline.
    """
    for role_id, meta in expanded_roles.items():
        zone = meta.get("zone", MAINLINE_ZONE) if isinstance(meta, dict) else MAINLINE_ZONE
        register_role(role_id, zone)


def register_mainline_legacy(role_ids: Iterable[str]) -> None:
    """Register the original 9 settings.AGENT_ROLES as mainline."""
    for r in role_ids:
        if r not in _ROLE_TO_ZONE:
            register_role(r, MAINLINE_ZONE)


__all__ = [
    "MAINLINE_ZONE",
    "HACKER_ZONE",
    "ALL_ZONES",
    "ZoneBoundaryError",
    "SessionZoneState",
    "register_role",
    "zone_for_role",
    "roles_in_zone",
    "all_registered_roles",
    "BRIDGE_CAPABLE_ROLES",
    "get_active_zone",
    "can_invoke_role",
    "can_route",
    "zone_bridge_allowed",
    "MEMORY_NAMESPACE",
    "memory_paths_for_zone",
    "ZONE_UI_THEME",
    "ui_theme_for_zone",
    "register_zones_from_config",
    "register_mainline_legacy",
]
