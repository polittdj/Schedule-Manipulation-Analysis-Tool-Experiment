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
  * v2.1.0 — additive: ``Task.duration_is_elapsed`` (MSP elapsed durations, PR #90) and
    ``Task.is_manual`` (MSP manually-scheduled mode; stored-date CPM mandate, ADR-0034).
"""

from __future__ import annotations

from schedule_forensics.model import units
from schedule_forensics.model.assignment import Assignment, CostPiece, WorkPiece
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task, TaskType

#: Bump on ANY change to a model's field set (see tests/model/test_schema_freeze.py).
# 2.11.0: Calendar.declared_minutes_per_day (ADR-0355) — the file's own MinutesPerDay
#   duration-scale SETTING, distinct from the calendar's derived day length; MPXJ scales
#   day/month filter literals by the declared property (Codex C1).
# 2.10.0: Calendar.minutes_per_week / days_per_month (ADR-0354) — the project-level duration
#   scale MPXJ's Duration.convertUnits uses for week/month/year filter literals; optional,
#   None = "the source didn't provide it" (MPXJ defaults 2400/20 at the consumer).
# 2.9.0: Schedule.import_notes (ADR-0312) AND, retroactively, Task.resume (ADR-0309) — the
#   latter shipped in #483 with the freeze test's field set updated but this version left at
#   2.8.0, because the guard only asserts a literal and cannot see an un-bumped add. Both
#   additive fields are covered here rather than leaving the record wrong.
# 2.8.0: Task priority/outline_number/stop (ADR-0234); 2.7.0: saved filters/groups (ADR-0231).
# 2.12.0: Resource.calendar_uid, Task.ignore_resource_calendar, Task.leveling_delay_minutes
#   (ADR-0474) — the resource-calendar / leveling-delay scheduling inputs the CPM now honours.
# 2.13.0: Assignment.work_pieces + WorkPiece (ADR-0491) — a WORK booking's leveling split as the
#   file time-phases it; AND, retroactively, Assignment.start / finish (ADR-0487, #671), which
#   shipped with the freeze test's field set updated but this version left at 2.12.0 — the
#   2.9.0 case again: the guard asserts a literal and cannot see an un-bumped add.
# 2.14.0: Assignment.baseline_cost_pieces + CostPiece (ADR-0492) — a booking's time-phased
#   baseline cost as the file records it: the BCWS MS Project stores and Fuse sums (R-46).
SCHEMA_VERSION = "2.14.0"

__all__ = [
    "SCHEMA_VERSION",
    "Assignment",
    "Calendar",
    "ConstraintType",
    "CostPiece",
    "Relationship",
    "RelationshipType",
    "Resource",
    "ResourceType",
    "Schedule",
    "Task",
    "TaskType",
    "WorkPiece",
    "units",
]
