"""Assignment model — one resource's work on one task (resource loading basis).

A task can carry several assignments (``Task.resource_assignments``); each ties a
:class:`~schedule_forensics.model.resource.Resource` (by UniqueID) to the **work** it
contributes and the **units** (allocation ratio) it is booked at. This is the source data
the engine time-phases into a resource-loading histogram and over-allocation check
(``engine/resources.py``) — never stored derived, only what the schedule file records.

``work_minutes`` is working minutes (480 == one 8-hour day), matching every other duration
in the model. ``units`` is the MS Project assignment units ratio (1.0 == 100%). Both default
to a benign zero/one so a schedule that does not record them (only a name/UID assignment) is
still valid — the loading view then falls back to a units-only (concurrency) read.
"""

from __future__ import annotations

import datetime as dt

from pydantic import Field

from schedule_forensics.model._base import StrictFrozenModel


class Assignment(StrictFrozenModel):
    """One resource's booking on one task: the resource UID, its work, and its units."""

    resource_id: int
    work_minutes: int = Field(default=0, ge=0)  # working minutes of work (480 == one day)
    units: float = Field(default=1.0, ge=0.0)  # allocation ratio (1.0 == 100%)
    #: working minutes of REMAINING work on this booking (0 == fully performed). ``None`` means
    #: the source file records no per-assignment remaining work — never assume 0 (that would
    #: read as "done"). Feeds the Fuse-parity assignment change tracker (ADR-0176): Acumen's
    #: forensic 'Resources' sheet rows are exactly the (task, resource) pairs whose remaining
    #: work changed or whose assignment appeared/disappeared between snapshots.
    remaining_work_minutes: int | None = Field(default=None, ge=0)
    #: The booking's scheduled window as the FILE records it (MSPDI ``Assignment/Start`` and
    #: ``/Finish``); ``None`` = not recorded (a Save .json written before ADR-0487, an XER). A
    #: WORK booking's window is reproduced by the engine from work / units / calendar
    #: (ADR-0474) and is never read from here. A MATERIAL / COST booking's window is the one
    #: scheduling input the file carries for it: MS Project spreads such a booking over a span
    #: no stored quantity determines (measured on Hard_File_updated3: UID 302's two non-work
    #: bookings, 1 unit at 100 % and 0.15 units at 0.06 %, share one 36 h span; at UID 385 the
    #: 1-unit / 100 % booking spans 24 h and the 2.5-unit / 0.06 % booking 125 h), so the
    #: engine reads the recorded span as a leg of the task's execution plan, like a leveling
    #: delay, and discloses the task on ``CPMResult.booking_span_driven`` (ADR-0487, R-56).
    start: dt.datetime | None = None
    finish: dt.datetime | None = None
