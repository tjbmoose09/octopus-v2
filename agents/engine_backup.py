"""Retirement stub — pre-V2.2 engine backup (truncated).

The pre-V2.2 backup engine snapshot has been moved to
``archive/engine_snapshots/engine_backup.py`` and is no longer
importable from this location. The canonical V2.2 engine is
``agents.engine``.

The archived file is a truncated snapshot that would raise ``SyntaxError``
if executed; it's kept only as a reference point. If you hit this
ImportError, update the caller to import from ``agents.engine`` instead.
See ``archive/engine_snapshots/README.md`` and
``docs/SYSTEM_DESIGN_V2.2.md``.
"""

from __future__ import annotations

raise ImportError(
    "agents.engine_backup is retired in V2.2. Use 'from agents.engine import ...' "
    "instead. Historical copy: archive/engine_snapshots/engine_backup.py."
)
