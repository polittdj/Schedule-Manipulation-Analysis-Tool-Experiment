"""Resource model — a labour / material / cost resource, keyed by UniqueID.

Resources support the DCMA "Resources" check (incomplete, duration-bearing tasks that
carry cost/work but no assigned resource). Tasks reference resources by name
(``Task.resource_names``) and/or UID (``Task.resource_ids``). Cost/rate fields are
optional: a schedule that is not cost-loaded simply leaves them ``None`` (never
fabricated).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from schedule_forensics.model._base import StrictFrozenModel


class ResourceType(StrEnum):
    """Resource kind (MS Project resource types)."""

    WORK = "WORK"  # labour / equipment (time-phased by units)
    MATERIAL = "MATERIAL"  # consumed materials
    COST = "COST"  # a fixed cost line item


class Resource(StrictFrozenModel):
    """A single project resource, keyed by UniqueID."""

    unique_id: int
    name: str
    type: ResourceType = ResourceType.WORK
    is_generic: bool = False
    max_units: float | None = Field(default=None, ge=0.0)  # capacity as a ratio (1.0 == 100%)
    standard_rate: float | None = Field(default=None, ge=0.0)  # cost per unit (currency)
    #: The resource's OWN calendar (MSPDI ``Resource/CalendarUID``), resolved against
    #: ``Schedule.calendars`` by ``uid``. MS Project schedules an assignment on the resource's
    #: calendar (intersected with the task's own calendar, unless the task ignores resource
    #: calendars), so a task whose crew works 16-hour or 24-hour days finishes on THAT calendar,
    #: not the project's (ADR-0474). ``None`` = the source carries no resource calendar (XER,
    #: older saves) — the engine then schedules on the task / project calendar as before.
    calendar_uid: int | None = None
