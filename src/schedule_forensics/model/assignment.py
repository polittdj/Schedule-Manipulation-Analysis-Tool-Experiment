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


class WorkPiece(StrictFrozenModel):
    """One contiguous run of a WORK booking's time-phased work, as the file records it: the
    run's first and last instants and the working minutes of work inside it (ADR-0491)."""

    start: dt.datetime
    finish: dt.datetime
    work_minutes: int = Field(ge=0)


class CostPiece(StrictFrozenModel):
    """One block of a booking's time-phased BASELINE COST as the file records it (ADR-0492):
    the block's first and last instants and the currency units planned inside it."""

    start: dt.datetime
    finish: dt.datetime
    cost: float


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
    #: A WORK booking's leveling SPLIT as the file time-phases it (ADR-0491, R-60): MS Project's
    #: resource leveling can leave zero-work gaps inside a booking, recorded only in the
    #: assignment's time-phased work (MSPDI ``TimephasedData``, remaining and actual work). Each
    #: piece is one maximal run of worked blocks; the gaps are what lies between consecutive
    #: pieces. ``()`` = one contiguous piece, or a source that records no time-phasing (an XER,
    #: a Save .json written before this field, a conversion made before the converter wrote
    #: it). The engine honours every gap between the pieces as working minutes of the leg's
    #: calendar, the way it honours the leveling delay before the start — measured on
    #: Hard_File_updated3 UID 403: 14 h, eight working days of nothing, 12 h, 3.2 h of nothing,
    #: 6 h; finish 2026-11-05 09:12 and LateStart 11-25 13:48, both MS Project's, to the minute.
    #: A MATERIAL / COST booking's pieces are inert: its leg is its recorded window (ADR-0487).
    work_pieces: tuple[WorkPiece, ...] = ()
    #: The BOOKING's own resource-leveling delay (MSPDI ``Assignment/LevelingDelay``, stored in
    #: tenths of a minute, read to the nearest whole minute), distinct from the task's
    #: :attr:`~schedule_forensics.model.task.Task.leveling_delay_minutes` (ADR-0474): MS Project
    #: levels one crew off a task without moving the task or its other crews. The engine delays
    #: that LEG alone — WORKING minutes of the leg's own calendar before the leg's work begins,
    #: then the calendar admits it again — and discloses the task on
    #: ``CPMResult.assignment_leveling_driven`` (ADR-0502, R-57). The task's START is NOT moved:
    #: on all 17 goldens' tasks that carry one, ``Task.Start`` is the earliest booking's start
    #: and every one of them also carries an undelayed booking. 0 = no delay on this booking.
    leveling_delay_minutes: int = Field(default=0, ge=0)
    #: The booking's time-phased BASELINE COST as the file records it (ADR-0492, R-46): every
    #: valued block of the MSPDI assignment's baseline-cost series (``TimephasedData`` Type 5),
    #: in time order, in currency units. This is the planned value MS Project stores per
    #: activity as BCWS and the reference tool sums (the Bible's ``sum(BCWSPV)``): a crew on a
    #: 16-hour calendar front-loads its budget, a merged block spans several equal days, and
    #: neither is visible to a proration of the task's budget over its baseline span on the
    #: project calendar (Hard_File_updated UID 187: 3,600 planned by the status date where
    #: that proration read 3,750 — the ribbon's 16,000 against the engine's 16,150). ``()`` =
    #: not recorded (an XER, a Save .json written before this field, a conversion made before
    #: the converter wrote timephased data); the engine then accrues the budget linearly.
    baseline_cost_pieces: tuple[CostPiece, ...] = ()
    #: The booking's ACTUAL work as the file TIME-PHASES it (ADR-0511, R-45): the sum of its MSPDI
    #: ``TimephasedData`` Type-2 (actual regular work) blocks, in working SECONDS — the file's own
    #: resolution (14h 46m 9s on Hard_File_updated2's UID 210), kept because the reference prices
    #: the record to the unit: rounded to whole minutes per booking it reads 64,104.17 where the
    #: ribbon prints 64,105 (the exact 64,104.61). The one seconds-valued field in the model, and
    #: a recorded quantity, never an axis duration (integer working minutes remain the Law).
    #: ``None`` = the file records no time-phased work
    #: for the booking at all (an XER, a Save .json written before this field, a conversion made
    #: without timephased data); 0 = a record with nothing performed. This is NOT the scalar
    #: ``Assignment/ActualWork``: Hard_File_updated3's UID 290 is written 31 h of actual work on a
    #: 40 h booking while its record holds 16 h regular + 6 h overtime, and MS Project's own
    #: EV (BCWP) and AC (ACWP) — the fields Fuse imports — are computed from the RECORD: 22 of 40
    #: booked hours earn 6,875 of the 12,500 baseline cost (the ribbon's 53,715, not the scalar's
    #: 59,340), and 16 h x 200 + 6 h x 300 = 5,000 is spent, not the 6,800 the scalar says.
    performed_work_seconds: int | None = Field(default=None, ge=0)
    #: The booking's actual OVERTIME work as the file time-phases it (Type-3 blocks), read the
    #: same way. Overtime counts toward the performed share of the booked work and is priced at the
    #: resource's overtime rate.
    performed_overtime_seconds: int | None = Field(default=None, ge=0)
    #: The booking's recorded baseline cost (MSPDI ``Assignment/Baseline[0]/Cost``, currency
    #: units, a negative clamped to 0 like the task's): the weight its performed share earns
    #: against. ``None`` = not recorded (the engine then weighs the baseline-cost series).
    baseline_cost: float | None = Field(default=None, ge=0.0)
    #: The booking's recorded actual cost (MSPDI ``Assignment/ActualCost``, currency units): what a
    #: MATERIAL / COST booking, or a WORK booking without a time-phased record, has spent.
    #: ``None`` = not recorded; the task then spends its own actual cost as before.
    actual_cost: float | None = None
