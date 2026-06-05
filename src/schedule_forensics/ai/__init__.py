"""Local-AI layer (pluggable, CUI fail-closed).

Backend interface with Null and Ollama (default) implementations plus an
explicit unclassified-cloud toggle behind a persistent banner; the cited
narrative generator and ``citations.py`` (every AI statement carries
file + UniqueID + task name). Milestone **M12**; see ``docs/PLAN/BUILD-PLAN.md``.
"""

from __future__ import annotations

__all__: list[str] = []
