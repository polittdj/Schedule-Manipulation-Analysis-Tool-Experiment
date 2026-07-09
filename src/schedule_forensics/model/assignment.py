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
