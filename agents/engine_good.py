"""Retirement stub — pre-V2.2 engine variant.

The pre-V2.2 "known-good" engine has been moved to
``archive/engine_snapshots/engine_good.py`` and is no longer importable
from this location. The canonical V2.2 engine is ``agents.engine``.

If you hit this ImportError, update the caller to import from
``agents.engine`` instead. This stub exists specifically to flush out
stale import sites during the V2.2 rollout; see
``archive/engine_snapshots/README.md`` and
``docs/SYSTEM_DESIGN_V2.2.md``.
"""

from __future__ import annotations

raise ImportError(
    "agents.engine_good is retired in V2.2. Use 'from agents.engine import ...' "
    "instead. Historical copy: archive/engine_snapshots/engine_good.py."
)
