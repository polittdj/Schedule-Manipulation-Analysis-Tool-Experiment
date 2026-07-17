"""Per-task-calendar Gantt shading (ADR-0243) — each activity row carries its GOVERNING
calendar name so the Gantt shades non-working time per the calendar that task actually runs on.

The operator's 24-hour-calendar file has a Mon-Fri project calendar with a few critical tasks
on a 24-hour calendar; those weekend-working tasks were shaded as if the weekend were
non-working (a misleading gray band behind a bar that DOES work weekends). The fix threads each
task's own calendar through to the client shading layer; this test pins the payload that carries
it — a task with its own calendar resolves to that calendar, a task without one inherits the
project calendar (MS Project semantics).
"""

from __future__ import annotations

import datetime as dt
from typing import cast

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.driving_path import compute_driving_path_evolution
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import _activity_rows, _driving_path_gantt

_DAY = 480


def _mixed_calendar_schedule() -> Schedule:
    """Mon-Fri project calendar + a 24-hour calendar; one task on each."""
    cal24 = Calendar(
        uid=10,
        name="24 Hours",
        working_minutes_per_day=1440,
        work_weekdays=(0, 1, 2, 3, 4, 5, 6),
    )
    tasks = (
        Task(
            unique_id=1,
            name="Mon-Fri task",
            duration_minutes=_DAY,
            start=dt.datetime(2025, 1, 6, 8, 0),
            finish=dt.datetime(2025, 1, 6, 17, 0),
        ),
        Task(
            unique_id=2,
            name="Round-the-clock task",
            duration_minutes=_DAY,
            calendar_uid=10,
            start=dt.datetime(2025, 1, 7, 8, 0),
            finish=dt.datetime(2025, 1, 7, 17, 0),
        ),
    )
    return Schedule(
        name="mixed",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),  # Mon-Fri default
        calendars=(cal24,),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_activity_rows_carry_each_tasks_governing_calendar() -> None:
    sch = _mixed_calendar_schedule()
    rows = {r["unique_id"]: r for r in _activity_rows(sch, compute_cpm(sch))}
    # every row carries the field (the client keys per-row shading off it)
    assert all("calendar" in r for r in rows.values())
    # the task with no own calendar inherits the project calendar (Mon-Fri → weekends shaded)
    assert rows[1]["calendar"] == "Standard"
    # the task on the 24-hour calendar resolves to it (all days worked → no weekend gray)
    assert rows[2]["calendar"] == "24 Hours"


def test_normal_single_calendar_schedule_resolves_every_row_to_the_project_calendar() -> None:
    # A schedule with no per-task calendars is a no-op for the change: every row resolves to the
    # project calendar, so shading is byte-identical to the pre-ADR-0243 global behavior.
    tasks = (
        Task(
            unique_id=1,
            name="A",
            duration_minutes=_DAY,
            start=dt.datetime(2025, 1, 6, 8, 0),
            finish=dt.datetime(2025, 1, 6, 17, 0),
        ),
        Task(
            unique_id=2,
            name="B",
            duration_minutes=_DAY,
            start=dt.datetime(2025, 1, 7, 8, 0),
            finish=dt.datetime(2025, 1, 7, 17, 0),
        ),
    )
    sch = Schedule(
        name="plain",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        calendar=Calendar(name="Standard"),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    rows = _activity_rows(sch, compute_cpm(sch))
    assert {r["calendar"] for r in rows} == {"Standard"}


def _mixed_calendar_corridor() -> tuple[list[Schedule], list[CPMResult]]:
    """Two versions of a Kickoff → round-the-clock build → Deliver chain (a driving corridor), the
    build task on a 24-hour calendar and the endpoints on the Mon-Fri project calendar."""

    def _v(name: str, status: str) -> Schedule:
        cal24 = Calendar(
            uid=10,
            name="24 Hours",
            working_minutes_per_day=1440,
            work_weekdays=(0, 1, 2, 3, 4, 5, 6),
        )
        tasks = (
            Task(unique_id=1, name="Kickoff", duration_minutes=_DAY),
            Task(
                unique_id=2,
                name="Round-the-clock build",
                duration_minutes=5 * _DAY,
                calendar_uid=10,
            ),
            Task(unique_id=3, name="Deliver", duration_minutes=0, is_milestone=True),
        )
        return Schedule(
            name=name,
            source_file=f"{name}.mpp",
            project_start=dt.datetime(2025, 1, 6, 8, 0),
            status_date=dt.datetime.fromisoformat(status),
            calendar=Calendar(name="Standard"),
            calendars=(cal24,),
            tasks=tasks,
            relationships=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=2, successor_id=3),
            ),
        )

    schedules = [_v("v1", "2025-01-01"), _v("v2", "2025-02-01")]
    return schedules, [compute_cpm(s) for s in schedules]


def test_driving_path_gantt_carries_per_task_calendar_and_the_registry() -> None:
    """Audit (ADR-0247): #382 shipped driving_path.js reading a per-row ``a.calendar``, but the
    server never emitted that field OR the calendar registry the page needs to resolve it — so the
    ``/driving-path`` corridor Gantt fell back to a flat Mon-Fri shade (the misleading behavior
    ADR-0243 fixed on /analysis). Pin BOTH halves of the now-complete wiring: each corridor activity
    carries its governing calendar name, and the payload carries the calendar definitions the page
    registers via ``SFTimescale.setCalendars``.
    """
    schedules, cpms = _mixed_calendar_corridor()
    evo = compute_driving_path_evolution(schedules, cpms, 1, 3)
    gantt = _driving_path_gantt(schedules, cpms, evo, "Kickoff", "Deliver")

    # the registry (union across versions) carries each calendar's shading definition by name
    cals = {c["name"]: c for c in cast("list[dict[str, object]]", gantt["calendars"])}
    assert cals["Standard"]["work_weekdays"] == [0, 1, 2, 3, 4]  # Mon-Fri → weekends shaded
    assert cals["24 Hours"]["work_weekdays"] == [0, 1, 2, 3, 4, 5, 6]  # all days → NO weekend gray

    # every corridor activity carries its OWN governing calendar name (what the JS keys shading off)
    versions = cast("list[dict[str, object]]", gantt["versions"])
    assert any(v["activities"] for v in versions)  # the corridor is non-empty
    for version in versions:
        acts = {
            a["uid"]: a["calendar"] for a in cast("list[dict[str, object]]", version["activities"])
        }
        if not acts:
            continue
        assert acts[1] == "Standard"  # Mon-Fri task inherits the project calendar
        assert acts[2] == "24 Hours"  # the round-the-clock task resolves to its OWN calendar
        assert acts[3] == "Standard"  # milestone inherits the project calendar
