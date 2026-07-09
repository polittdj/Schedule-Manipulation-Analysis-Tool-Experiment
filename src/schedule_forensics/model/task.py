"""Task (activity) model — the schedule's atomic unit, keyed by UniqueID.

``unique_id`` is the **sole** cross-version identity (never the row ID, which
renumbers on insert/delete; never the name, which is not unique). Every field here is
a value the schedule file records; CPM dates, total/free float, driving slack, and the
DCMA/EVM metrics are derived by the engine and are deliberately **not** stored on the
task. Durations are integer working minutes (``480`` == one 8-hour day); a 0-minute,
``is_milestone`` task is an instantaneous event. Optional date/cost fields default to
``None`` meaning *"not provided by the source"* — never assume 0/empty.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import Field

from schedule_forensics.model._base import StrictFrozenModel
from schedule_forensics.model.assignment import Assignment


class ConstraintType(StrEnum):
    """Task date-constraint type (MS Project ``ConstraintType`` enumeration)."""

    ASAP = "ASAP"  # as soon as possible (default — no constraint)
    ALAP = "ALAP"  # as late as possible
    SNET = "SNET"  # start no earlier than (soft)
    SNLT = "SNLT"  # start no later than (hard)
    FNET = "FNET"  # finish no earlier than (soft)
    FNLT = "FNLT"  # finish no later than (hard)
    MSO = "MSO"  # must start on (hard)
    MFO = "MFO"  # must finish on (hard)


#: The constraint types the DCMA "Hard Constraints" check counts (06A209a, MS Project
#: set): mandatory/must dates plus the no-later-than caps. ASAP/ALAP/SNET/FNET are soft.
_HARD_CONSTRAINTS: frozenset[ConstraintType] = frozenset(
    {ConstraintType.MSO, ConstraintType.MFO, ConstraintType.SNLT, ConstraintType.FNLT}
)


class Task(StrictFrozenModel):
    """A single schedule activity. ``unique_id`` is the only cross-version key."""

    # --- identity ---
    unique_id: int
    name: str
    wbs: str | None = None  # WBS code (display / traceability; never an identity key)
    #: Source ``<CalendarUID>`` the task is scheduled on; ``None`` = the project default
    #: calendar. Resolved against ``Schedule.calendars`` for SSI driving-slack parity, where a
    #: link's free float is counted on the successor's own calendar (ADR-0118).
    calendar_uid: int | None = None
    #: WBS/outline nesting depth (MSPDI ``<OutlineLevel>``): 0 = the project summary row, 1 = a
    #: top-level WBS, 2 = its child, and so on to any depth. Drives the Gantt's Microsoft-Project
    #: style name indentation; the value, not a fixed count, sets the indent (ADR-0119).
    outline_level: int = 0

    # --- duration (working minutes; 0 + is_milestone == instantaneous event) ---
    duration_minutes: int = Field(ge=0)
    #: MS Project elapsed durations ("1 eday"/"2 ewks") consume wall-clock time and
    #: ignore both the task and project calendars (weekends/holidays included).
    duration_is_elapsed: bool = False
    remaining_duration_minutes: int | None = Field(default=None, ge=0)
    baseline_duration_minutes: int | None = Field(default=None, ge=0)
    #: MS Project "Estimated" duration flag (MSPDI ``<Estimated>``): the duration is a placeholder
    #: the planner has not yet firmed up — a not-fully-developed estimate, flagged by the handbook.
    is_estimated_duration: bool = False

    # --- work (effort, working minutes; distinct from duration — a 2-day task with two
    # full-time resources carries 4 days of work). None = the source records no work; never
    # assume 0. Tracked cross-version for the Fuse-parity work-change signals (ADR-0176).
    work_minutes: int | None = Field(default=None, ge=0)  # total (planned) work
    actual_work_minutes: int | None = Field(default=None, ge=0)  # work performed to date

    # --- classification ---
    is_milestone: bool = False
    is_summary: bool = False  # WBS rollup; excluded from the CPM network and DCMA denominators
    is_level_of_effort: bool = False
    is_active: bool = True
    #: MS Project "Manually Scheduled" task mode (MSPDI ``<Manual>``): MSP keeps the task
    #: at its stored dates regardless of logic. The CPM engine honors this for unstarted
    #: tasks and reports the logic-vs-stored divergence as a cited finding (ADR-0034).
    is_manual: bool = False

    # --- constraints ---
    constraint_type: ConstraintType = ConstraintType.ASAP
    constraint_date: dt.datetime | None = None
    deadline: dt.datetime | None = None

    # --- progress / status ---
    percent_complete: float = Field(default=0.0, ge=0.0, le=100.0)
    physical_percent_complete: float | None = Field(default=None, ge=0.0, le=100.0)

    # --- MS Project / source-tool STORED scheduling values (Acumen fidelity) ---
    # Acumen Fuse (and MS Project's own views) report Total Slack and the Critical flag from the
    # source tool's *stored, progress-aware* calculation. The engine recomputes pure-logic CPM
    # float for independence (ADR-0010); these capture the source's own values so the DCMA
    # float-based metrics can match Acumen on progressed real files. ``None`` = the source file
    # did not carry the value (e.g. a non-MSPDI import) — the metric then uses recomputed float.
    stored_total_float_minutes: int | None = None  # working minutes; < 0 = behind a constraint
    stored_is_critical: bool | None = None

    # --- dates as recorded in the source (forecast / actual / baseline) ---
    start: dt.datetime | None = None  # current scheduled/forecast start
    finish: dt.datetime | None = None  # current scheduled/forecast finish
    actual_start: dt.datetime | None = None
    actual_finish: dt.datetime | None = None
    baseline_start: dt.datetime | None = None
    baseline_finish: dt.datetime | None = None

    # --- cost / earned value ---
    # scheduled/actual cost may legitimately be negative in real exports (credits,
    # adjustments); the BAC basis (budgeted_cost) stays non-negative (EV cannot be earned
    # against a negative budget — importers clamp a negative baseline cost to 0).
    cost: float | None = None  # scheduled cost
    actual_cost: float | None = None  # ACWP basis
    budgeted_cost: float = Field(default=0.0, ge=0.0)  # baseline cost / BAC (EV basis)

    # --- resource assignment (DCMA Resources check) ---
    resource_names: tuple[str, ...] = ()
    resource_ids: tuple[int, ...] = ()
    # Per-resource bookings with work + units — the source for resource loading / over-allocation
    # (engine/resources.py). Empty when the file records only names/UIDs (no work-phased loading).
    resource_assignments: tuple[Assignment, ...] = ()

    # --- custom / extended fields (MSPDI ExtendedAttributes: Text/Number/Flag/Date/Outline codes).
    # Stored as (label, value) pairs — label is the MS Project alias (e.g. "CA-WBS") when set, else
    # the field name (e.g. "Text20"). A tuple keeps the model frozen + hashable (like resources).
    custom_fields: tuple[tuple[str, str], ...] = ()

    @property
    def custom_field_map(self) -> dict[str, str]:
        """Label → value view of :attr:`custom_fields` (built on access; the model is frozen)."""
        return dict(self.custom_fields)

    def custom_field(self, label: str) -> str | None:
        """The value of the custom field with this label (alias or field name), or ``None``."""
        for key, value in self.custom_fields:
            if key == label:
                return value
        return None

    @property
    def is_complete(self) -> bool:
        """DCMA convention: a task is complete at 100% (incomplete is strictly < 100)."""
        return self.percent_complete >= 100.0

    @property
    def is_in_progress(self) -> bool:
        return 0.0 < self.percent_complete < 100.0

    @property
    def is_not_started(self) -> bool:
        return self.percent_complete <= 0.0

    @property
    def has_hard_constraint(self) -> bool:
        """True for the hard/mandatory constraint types the DCMA check counts."""
        return self.constraint_type in _HARD_CONSTRAINTS
