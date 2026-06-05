"""Domain model layer (pydantic v2, frozen, UniqueID-keyed).

Schedule / Task / Relationship / Resource / Calendar value objects plus
``units.py`` (minutes↔days deterministic rounding, signed-percent formatting).
Implemented in milestone **M2** (see ``docs/PLAN/BUILD-PLAN.md``).
"""

from __future__ import annotations

__all__: list[str] = []
