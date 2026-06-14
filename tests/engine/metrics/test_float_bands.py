"""Float-band tests — hand-built band edges (calendar-aware) + golden pins (M15).

Float sums (ADR-0039, PBIX p5) are also tested here: TotalFloatSum / FreeFloatSum
in working days, shrinking sums signal cushion erosion across versions.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import compute_float_bands, compute_float_sums
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)


def test_cumulative_bands_with_band_edges_on_the_schedules_calendar() -> None:
    # 600-min (10h) calendar. Driver chain A1->A2 spans 20 days (TF 0); B carries exactly
    # 4 days of float (2400 min — under the 5-day band ONLY because 5d = 3000 min on this
    # calendar; a 480-min hardcode would put the edge at 2400 and miss it); C carries 9
    # days (< 10); D carries 19 days (outside every band).
    day = 600
    tasks = [
        Task(unique_id=1, name="A1", duration_minutes=5 * day),
        Task(unique_id=2, name="A2", duration_minutes=15 * day),
        Task(unique_id=3, name="B", duration_minutes=16 * day),
        Task(unique_id=4, name="C", duration_minutes=11 * day),
        Task(unique_id=5, name="D", duration_minutes=1 * day),
    ]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    sch = Schedule(
        name="bands",
        project_start=MON,
        calendar=Calendar(name="Tens", working_minutes_per_day=600),
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )
    fb = compute_float_bands(sch)
    assert fb["float_total_0"].count == 2 and fb["float_total_0"].offender_uids == (1, 2)
    assert fb["float_total_lt5"].count == 3  # + B (4 days)
    assert fb["float_total_lt10"].count == 4  # + C (9 days)
    assert 5 not in fb["float_total_lt10"].offender_uids  # D (19 days) is outside
    assert fb["float_total_0"].population == 5
    assert fb["float_total_lt10"].value == 80.0
    # bands are cumulative by construction
    assert set(fb["float_total_0"].offender_uids) <= set(fb["float_total_lt5"].offender_uids)
    assert set(fb["float_total_lt5"].offender_uids) <= set(fb["float_total_lt10"].offender_uids)


def test_completed_work_is_excluded_from_the_population() -> None:
    tasks = [
        Task(unique_id=1, name="done", duration_minutes=480, percent_complete=100.0),
        Task(unique_id=2, name="todo", duration_minutes=480),
    ]
    fb = compute_float_bands(Schedule(name="s", project_start=MON, tasks=tuple(tasks)))
    assert fb["float_total_0"].population == 1
    assert fb["float_total_0"].offender_uids == (2,)


def test_float_sums_basic() -> None:
    # A1->A2 chain: A1 TF=0, A2 TF=0; B has 4 days float; C has 9 days; D has 19 days.
    # 600-min day: TF total = (0+0+4+9+19)*600 = 32*600 min => 32 days total.
    day = 600
    tasks = [
        Task(unique_id=1, name="A1", duration_minutes=5 * day),
        Task(unique_id=2, name="A2", duration_minutes=15 * day),
        Task(unique_id=3, name="B", duration_minutes=16 * day),
        Task(unique_id=4, name="C", duration_minutes=11 * day),
        Task(unique_id=5, name="D", duration_minutes=1 * day),
    ]
    rels = [Relationship(predecessor_id=1, successor_id=2)]
    sch = Schedule(
        name="sums",
        project_start=MON,
        calendar=Calendar(name="Tens", working_minutes_per_day=day),
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )
    fs = compute_float_sums(sch)
    assert fs.total_days == 32.0
    # free float: A1=0, A2=0, B=4, C=9, D=19 (no successors, so free==total for B/C/D)
    assert fs.free_days == 32.0


def test_float_sums_excludes_completed_work() -> None:
    tasks = [
        Task(unique_id=1, name="done", duration_minutes=480, percent_complete=100.0),
        Task(unique_id=2, name="todo", duration_minutes=480),
    ]
    fs = compute_float_sums(Schedule(name="s", project_start=MON, tasks=tuple(tasks)))
    # only task 2 (critical, TF=0) contributes
    assert fs.total_days == 0.0


def test_float_sums_golden_project5(golden_project5: Schedule) -> None:
    fs = compute_float_sums(golden_project5)
    # 99 incomplete activities; the sum must be positive and consistent with bands
    assert fs.total_days >= 0
    assert fs.free_days >= 0
    # free float sum <= total float sum (free is the tighter constraint)
    assert fs.free_days <= fs.total_days


def test_golden_pins(golden_project2: Schedule, golden_project5: Schedule) -> None:
    # the 0-day total band reproduces the Acumen "Critical" parity counts (41 / 37)
    p2 = compute_float_bands(golden_project2)
    assert (p2["float_total_0"].count, p2["float_total_0"].population) == (41, 106)
    assert p2["float_total_lt5"].count == 42
    assert p2["float_total_lt10"].count == 46
    assert p2["float_free_0"].count == 71
    p5 = compute_float_bands(golden_project5)
    assert (p5["float_total_0"].count, p5["float_total_0"].population) == (37, 99)
    assert p5["float_total_lt10"].count == 42
    assert p5["float_free_lt10"].count == 75
