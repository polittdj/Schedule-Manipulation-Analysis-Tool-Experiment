"""Resource model — a labour / material / cost resource, keyed by UniqueID.

Resources support the DCMA "Resources" check (incomplete, duration-bearing tasks that
carry cost/work but no assigned resource). Tasks reference resources by name
(``Task.resource_names``) and/or UID (``Task.resource_ids``). Cost/rate fields are
optional: a schedule that is not cost-loaded simply leaves them ``None`` (never
fabricated).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from enum import StrEnum

from pydantic import Field

from schedule_forensics.model._base import StrictFrozenModel


class ResourceType(StrEnum):
    """Resource kind (MS Project resource types)."""

    WORK = "WORK"  # labour / equipment (time-phased by units)
    MATERIAL = "MATERIAL"  # consumed materials
    COST = "COST"  # a fixed cost line item


class AvailabilityPeriod(StrictFrozenModel):
    """One row of a resource's availability table as the file records it (ADR-0506, R-63): the
    units the resource is available at between two instants — MSPDI ``Resource/
    AvailabilityPeriods/AvailabilityPeriod`` (``AvailableFrom`` / ``AvailableTo`` /
    ``AvailableUnits``), the grid MS Project shows as Resource Information → Resource
    Availability. MS Project's "NA" start is written as 1984-01-01 and reads as ``None`` (an
    open start, like every other pre-1985 sentinel the importers see); its "NA" end is written as
    2049-12-31 23:59 and kept as written. ``None`` on either bound means open."""

    available_from: dt.datetime | None = None
    #: the row's stated end — carried as the file's own statement (and written back by the Save
    #: format); the resolution rule below does not consult it, see :func:`value_in_effect`
    available_to: dt.datetime | None = None
    units: float = Field(
        ge=0.0
    )  # the capacity ratio in force from ``available_from`` (1.0 == 100%)


def value_in_effect(
    spans: Sequence[tuple[dt.datetime | None, float]], when: dt.datetime
) -> float | None:
    """The value of a dated table in force at ``when`` — the ONE rule every time-varying resource
    table resolves by (ADR-0506): **the latest row that has begun by ``when``** (a ``None`` start
    has always begun; a row is a statement in force until the next row begins), else, before
    every row's start, the earliest row (a table whose every row starts in the future states its
    first row rather than nothing — the XER ``RSRCRATE`` rule, operator 2026-08-20). ``None``
    only for an empty table.

    A row's stated END is deliberately not consulted. On every table the corpus carries the rows
    are contiguous (each ends the minute before the next begins), so "the row containing
    ``when``" and "the latest row begun" are the same row — the containing-row check was a second
    code path that could not change an outcome (its start-bound mutant SURVIVED the battery) and
    was deleted. For a gap between rows — or after the last row's stated end — the latest row
    begun is held in force, the P6 reading. Whether MS Project instead treats such a day as ZERO
    availability is UNVERIFIED: the corpus carries the shape (the three tampered Project5_FX0x
    saves book crews on 113 / 179 / 113 loaded days past their single bounded rows) but no MS
    Project verdict on it; under this rule those days keep the row's units, exactly the figure
    the converter's scalar gave, and a future reading that needs the end bound finds it here."""
    if not spans:
        return None
    begun = [s for s in spans if s[0] is None or s[0] <= when]
    if begun:
        return max(begun, key=lambda s: s[0] or dt.datetime.min)[1]
    return min(spans, key=lambda s: s[0] or dt.datetime.min)[1]


def units_in_effect(periods: Sequence[AvailabilityPeriod], when: dt.datetime) -> float | None:
    """:func:`value_in_effect` over an availability table: the units in force at ``when``."""
    return value_in_effect([(p.available_from, p.units) for p in periods], when)


class Resource(StrictFrozenModel):
    """A single project resource, keyed by UniqueID."""

    unique_id: int
    name: str
    type: ResourceType = ResourceType.WORK
    is_generic: bool = False
    #: capacity as a ratio (1.0 == 100%). A resource whose file carries an availability table
    #: states this at the schedule's STATUS date (else its project start) — the table's units in
    #: force then (ADR-0506, R-63) — never the converter's wall clock: MS Project's own
    #: ``MaxUnits`` is "the current row of the Resource Availability grid", the row containing
    #: the CURRENT date, and the vendored MPXJ writer resolves it at conversion time, so the same
    #: save converted a month apart carried two different figures. ``None`` = the file states
    #: no max units at all (the loading engine then assumes one full unit and says so).
    max_units: float | None = Field(default=None, ge=0.0)
    standard_rate: float | None = Field(default=None, ge=0.0)  # cost per unit (currency)
    #: The resource's availability table as the file records it, in time order (ADR-0506):
    #: every row of MS Project's Resource Availability grid. ``()`` = the file carries no table
    #: (a single, unchanging availability — MPXJ writes the table only when a row's bounds are
    #: not the defaults; an XER; a Save .json written before this field). The loading engine
    #: earns each working day's capacity from the row in force THAT day, so a crew that doubles
    #: on 08-02 has one unit of capacity in July's bucket and two in September's.
    availability: tuple[AvailabilityPeriod, ...] = ()
    #: The resource's OWN calendar (MSPDI ``Resource/CalendarUID``), resolved against
    #: ``Schedule.calendars`` by ``uid``. MS Project schedules an assignment on the resource's
    #: calendar (intersected with the task's own calendar, unless the task ignores resource
    #: calendars), so a task whose crew works 16-hour or 24-hour days finishes on THAT calendar,
    #: not the project's (ADR-0474). ``None`` = the source carries no resource calendar (XER,
    #: older saves) — the engine then schedules on the task / project calendar as before.
    calendar_uid: int | None = None

    def units_at(self, when: dt.datetime) -> float | None:
        """The availability table's units in force at ``when`` (:func:`units_in_effect`);
        ``None`` when the resource carries no table — the caller then reads ``max_units``."""
        return units_in_effect(self.availability, when)
