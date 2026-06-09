"""Domain model layer (pydantic v2, frozen, strict, UniqueID-keyed).

The trust-root value objects the whole engine consumes unchanged:
:class:`Schedule` / :class:`Task` / :class:`Relationship` / :class:`Resource` /
:class:`Calendar`, plus :mod:`~schedule_forensics.model.units` (the minutes↔days
deterministic-rounding and signed-percent presentation boundary). Implemented in
milestone **M2**.

Only *source-of-truth* fields live on these models; derived analytics (CPM, float,
driving slack, DCMA/EVM) are computed by the engine and never persisted here.

**Change control:** every model is frozen + ``extra="forbid"``, so any field
add/remove/rename requires bumping :data:`SCHEMA_VERSION` and updating
``tests/model/test_schema_freeze.py`` in the same change (the freeze test fails
otherwise — deliberate).

Change log:
  * v2.0.0 — M2 trust-root model (pydantic v2, modular layout; supersedes the prior
    build's single-module v1.x schema). Source-only fields; engine computes derivatives.
"""

from __future__ import annotations

from schedule_forensics.model import units
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

#: Bump on ANY change to a model's field set (see tests/model/test_schema_freeze.py).
SCHEMA_VERSION = "2.0.0"

__all__ = [
    "SCHEMA_VERSION",
    "Calendar",
    "ConstraintType",
    "Relationship",
    "RelationshipType",
    "Resource",
    "ResourceType",
    "Schedule",
    "Task",
    "units",
]
