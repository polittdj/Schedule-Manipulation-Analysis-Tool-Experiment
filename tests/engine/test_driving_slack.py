"""Driving-slack tests — synthetic hand-verified slack + the SSI golden parity gate.

The golden gate reproduces the SSI MS Project add-on's Driving Slack for Project5 /
focus UID 143 exactly (107 UniqueIDs), keyed by UniqueID (`SSI-DRIVING-SLACK.md`).
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

from schedule_forensics.engine.driving_slack import (
    PathTier,
    compute_driving_slack,
    driving_path,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _net() -> Schedule:
    # Focus = 4(D). Driving path 2(B,1d) -> 3(C,3d) -> 4(D,1d); 1(A,2d) -> 4 with 2 days slack.
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=2 * DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
        Task(unique_id=3, name="C", duration_minutes=3 * DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=4),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    return Schedule(name="net", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def test_synthetic_driving_slack() -> None:
    results = compute_driving_slack(_net(), target_uid=4)
    assert set(results) == {1, 2, 3, 4}  # focus + its ancestors only
    assert results[4].driving_slack_minutes == 0 and results[4].on_driving_path
    assert results[2].driving_slack_minutes == 0 and results[3].driving_slack_minutes == 0
    assert results[1].driving_slack_minutes == 2 * DAY  # A may slip 2 days
    assert results[1].on_driving_path is False
    assert results[1].tier is PathTier.SECONDARY


_LUNCH = ((480, 720), (780, 1020))  # 08:00-12:00 + 13:00-17:00


def _per_cal_schedule(
    *, holidays: tuple[dt.date, ...] = (), working_days: tuple[dt.date, ...] = ()
) -> Schedule:
    """Ancestor A (project calendar) -> FS -> focus F (calendar 2). A's driving slack is the
    free float to F, which SSI counts on F's (the successor's) own calendar (ADR-0118)."""
    cal2 = Calendar(uid=2, holidays=holidays, working_days=working_days, day_segments=_LUNCH)
    tasks = (
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            start=dt.datetime(2025, 1, 6, 8, 0),
            finish=dt.datetime(2025, 1, 6, 17, 0),
        ),
        Task(
            unique_id=2,
            name="F",
            duration_minutes=DAY,
            calendar_uid=2,
            start=dt.datetime(2025, 1, 20, 8, 0),
            finish=dt.datetime(2025, 1, 20, 17, 0),
        ),
    )
    return Schedule(
        name="percal",
        project_start=MON,
        calendar=Calendar(day_segments=_LUNCH),
        calendars=(cal2,),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_free_float_counted_on_successor_calendar() -> None:
    # baseline: 9 clear working days of free float from A's finish to F's start
    assert (
        compute_driving_slack(_per_cal_schedule(), target_uid=2)[1].driving_slack_minutes == 9 * DAY
    )
    # a holiday on F's calendar inside the window removes one working day (ADR-0118)
    hol = (dt.date(2025, 1, 15),)
    assert (
        compute_driving_slack(_per_cal_schedule(holidays=hol), target_uid=2)[
            1
        ].driving_slack_minutes
        == 8 * DAY
    )
    # an extra working day (a worked Saturday) on F's calendar adds one
    sat = (dt.date(2025, 1, 11),)
    assert (
        compute_driving_slack(_per_cal_schedule(working_days=sat), target_uid=2)[
            1
        ].driving_slack_minutes
        == 10 * DAY
    )


def test_sf_link_and_non_worked_endpoint() -> None:
    # SF link exercises the start->finish free-float branch; A's Saturday start (non-worked on
    # its calendar with a lunch) exercises the non-worked-day branch of the date conversion.
    cal2 = Calendar(uid=2, day_segments=_LUNCH)
    tasks = (
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            calendar_uid=2,
            start=dt.datetime(2025, 1, 11, 8, 0),  # Saturday — not a worked day
            finish=dt.datetime(2025, 1, 11, 17, 0),
        ),
        Task(
            unique_id=2,
            name="F",
            duration_minutes=DAY,
            calendar_uid=2,
            start=dt.datetime(2025, 1, 13, 8, 0),
            finish=dt.datetime(2025, 1, 20, 17, 0),
        ),
    )
    sched = Schedule(
        name="sf",
        project_start=MON,
        calendar=Calendar(day_segments=_LUNCH),
        calendars=(cal2,),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.SF),),
    )
    # ff_SF = off(F.finish=11 working days) - off(A.start=Saturday, 5 working days) = 6 days
    assert compute_driving_slack(sched, target_uid=2)[1].driving_slack_minutes == 6 * DAY


def test_ss_and_ff_link_free_float() -> None:
    # exercise the start-start and finish-finish free-float branches on the project calendar
    f = dt.datetime(2025, 1, 13, 8, 0)
    tasks = (
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            start=MON,
            finish=dt.datetime(2025, 1, 6, 17, 0),
        ),
        Task(
            unique_id=2,
            name="B",
            duration_minutes=DAY,
            start=MON,
            finish=dt.datetime(2025, 1, 6, 17, 0),
        ),
        Task(unique_id=3, name="F", duration_minutes=DAY, start=f, finish=f.replace(hour=17)),
    )
    sched = Schedule(
        name="ssff",
        project_start=MON,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=1, successor_id=3, type=RelationshipType.SS),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FF),
        ),
    )
    res = compute_driving_slack(sched, target_uid=3)
    assert res[1].driving_slack_minutes == 5 * DAY  # SS: F.start - A.start = 5 working days
    assert res[2].driving_slack_minutes == 5 * DAY  # FF: F.finish - B.finish = 5 working days


def test_driving_path_is_ordered() -> None:
    results = compute_driving_slack(_net(), target_uid=4)
    assert driving_path(_net(), results) == (2, 3, 4)


def test_tier_thresholds_configurable() -> None:
    # A's 2-day slack lands beyond a 1-day tertiary ceiling.
    results = compute_driving_slack(_net(), target_uid=4, secondary_max_days=1, tertiary_max_days=1)
    assert results[1].tier is PathTier.BEYOND
    # Widen secondary to include it.
    results2 = compute_driving_slack(_net(), target_uid=4, secondary_max_days=5)
    assert results2[1].tier is PathTier.SECONDARY


def test_target_with_no_ancestors() -> None:
    results = compute_driving_slack(_net(), target_uid=2)  # B is a start task
    assert set(results) == {2}
    assert results[2].driving_slack_minutes == 0


def test_tier_bands_convert_days_on_the_schedules_calendar() -> None:
    # On a 10-hour (600-min) calendar, A->T carries 9 working days of slack (5400 min).
    # Tiering against hardcoded 480-min days read that as 11.25d -> TERTIARY; the bands
    # are defined in days, so on this calendar it is 9d -> SECONDARY (default band <=10).
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=600),
        Task(unique_id=2, name="B", duration_minutes=10 * 600),
        Task(unique_id=3, name="T", duration_minutes=600),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=2, successor_id=3),
    ]
    sched = Schedule(
        name="tens",
        project_start=MON,
        calendar=Calendar(name="Tens", working_minutes_per_day=600),
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )
    results = compute_driving_slack(sched, target_uid=3)
    assert results[1].driving_slack_minutes == 9 * 600
    assert results[1].driving_slack_days == Decimal("9.00")  # not 11.25
    assert results[1].tier is PathTier.SECONDARY


def test_golden_ssi_driving_slack_uid67_parity(golden_project5: Schedule) -> None:
    """SSI Directional Path export, focus UID 67 'Pour roof slab' (delivered 2026-07-08, A-5).

    Retires the stale ssi_uid143 xfail: this export was run on the AUTHORITATIVE
    Project5_TAMPERED (4 stored-critical, ADR-0112) with Dependency Range = Driving Slack <= 0 d,
    so it pins the exact 20-task driving-path membership; every Path-01 task carries 0 days of
    driving slack. SSI's per-task Drag is provenance-only (the engine does not compute drag)."""
    case = json.loads((GOLDEN / "ssi_uid67" / "case.json").read_text())
    results = compute_driving_slack(golden_project5, target_uid=case["focus_task_uid"])

    ssi_path = set(map(int, case["driving_slack_days_by_uid"]))
    engine_zero = {uid for uid, r in results.items() if r.driving_slack_minutes == 0}
    assert engine_zero == ssi_path  # exact membership, UID-for-UID, no extras
    assert driving_path(golden_project5, results) == tuple(case["driving_path_uids"])
    assert all(results[uid].tier is PathTier.DRIVING for uid in ssi_path)

    focus = results[case["focus_task_uid"]]
    assert focus.driving_slack_minutes == 0 and focus.on_driving_path


def test_golden_ssi_driving_slack_uid145_parity(golden_project5: Schedule) -> None:
    """SSI 'Get all dependencies' export for focus UID 145 on the authoritative file (ADR-0115).

    The live SSI driving-slack parity gate (108 UniqueIDs, exact, by UID) after ADR-0112 made the
    ssi_uid143 golden stale. This export is focus 145, so it does NOT lift the ssi_uid143 xfail.
    """
    case = json.loads((GOLDEN / "ssi_uid145" / "case.json").read_text())
    results = compute_driving_slack(golden_project5, target_uid=case["focus_task_uid"])

    expected = {int(uid): days for uid, days in case["driving_slack_days_by_uid"].items()}
    assert set(results) == set(expected)  # exact, UniqueID-keyed: every traced task, no extras
    got_days = {uid: int(r.driving_slack_days) for uid, r in results.items()}
    assert got_days == expected
    assert all(r.driving_slack_minutes % DAY == 0 for r in results.values())  # whole working days

    focus = results[case["focus_task_uid"]]
    assert focus.driving_slack_minutes == 0 and focus.on_driving_path
    assert driving_path(golden_project5, results) == tuple(case["driving_path_uids"])  # 144 -> 145

    bands = case["tier_counts_default_bands"]
    tiers = {tier: sum(1 for r in results.values() if r.tier is tier) for tier in PathTier}
    assert {t.name: c for t, c in tiers.items()} == bands


def test_subday_slack_is_driving_like_ssi_displays_it() -> None:
    # Real stored dates carry minutes of time-of-day raggedness: a chain SSI shows at
    # "0 days" of driving slack must read DRIVING here, not fall out over a sub-day
    # offset (a real file read 4 driving tasks where MS Project + SSI showed ~66).
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY),  # exactly 1 day of slack
        Task(unique_id=2, name="B", duration_minutes=2 * DAY - 30),  # 30 ragged minutes
        Task(unique_id=3, name="C", duration_minutes=DAY - 30),  # a day + 30 minutes over
        Task(unique_id=4, name="D", duration_minutes=2 * DAY),  # the tight driver
        Task(unique_id=5, name="T", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=5),
        Relationship(predecessor_id=2, successor_id=5),
        Relationship(predecessor_id=3, successor_id=5),
        Relationship(predecessor_id=4, successor_id=5),
    ]
    sched = Schedule(
        name="ragged", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels)
    )
    results = compute_driving_slack(sched, target_uid=5)
    assert results[4].driving_slack_minutes == 0 and results[4].on_driving_path
    # 30 minutes of slack — the time-of-day noise case — displays 0 days: DRIVING
    assert results[2].driving_slack_minutes == 30
    assert results[2].tier is PathTier.DRIVING and results[2].on_driving_path
    # exactly one whole day is NOT driving (matches the old exact-multiple behavior)
    assert results[1].driving_slack_minutes == DAY
    assert results[1].tier is PathTier.SECONDARY and not results[1].on_driving_path
    # one day + ragged minutes floors to 1 day: SECONDARY, not driving
    assert results[3].driving_slack_minutes == DAY + 30
    assert results[3].tier is PathTier.SECONDARY and not results[3].on_driving_path


def test_ignore_flags_are_stored_date_noops_on_a_fully_dated_file(
    golden_project5: Schedule,
) -> None:
    """ADR-0251 (operator decision on the ADR-0250 queued finding): the ignore flags mirror
    SSI's same-named options, which keep reporting against the stored dates — so on a
    fully-dated single-calendar file the trace is IDENTICAL with or without them. This is
    the parity-validated behavior (SSI's own options-ON UID-152 export matches the
    stored-date trace); genuinely clearing dates and re-solving diverges wildly and is the
    web layer's separate, banner-labeled ``_optioned_versions`` counterfactual."""
    sch = golden_project5
    assert all(  # the premise: every scheduled task carries stored dates
        t.start is not None and t.finish is not None
        for t in sch.tasks
        if not t.is_summary and t.is_active
    )
    base = compute_driving_slack(sch, 67)
    for flags in (
        {"ignore_constraints": True},
        {"ignore_leveling_delay": True},
        {"ignore_constraints": True, "ignore_leveling_delay": True},
    ):
        assert compute_driving_slack(sch, 67, **flags) == base, flags
