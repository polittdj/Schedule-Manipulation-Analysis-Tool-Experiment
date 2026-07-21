"""DCMA-14 tests — the Acumen golden parity (P2/P5) + synthetic edge cases.

The golden test reproduces `PARITY-TARGETS.md §B` exactly for every check except
High Float, which carries a documented +1 residual (ADR-0012) and is asserted within 1.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from schedule_forensics.engine.metrics import CheckStatus, compute_bei, compute_dcma14
from schedule_forensics.engine.metrics._common import forty_four_days_min
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_golden_dcma14_parity(project: str, golden: Callable[[str], Schedule]) -> None:
    case = json.loads((GOLDEN / "project2_5" / "case.json").read_text())[project]
    d = compute_dcma14(golden(project))
    g = case["dcma14"]

    # exact, count-keyed (every check but High Float)
    for key in (
        "DCMA01",
        "DCMA02",
        "DCMA03",
        "DCMA04_SSFF",
        "DCMA04_SF",
        "DCMA05",
        "DCMA07",
        "DCMA08",
        "DCMA09",
        "DCMA10",
        "DCMA11",
    ):
        assert d[key].count == g[key], f"{project} {key}: {d[key].count} != {g[key]}"
    assert round(d["DCMA04_FS"].value) == g["DCMA04_FS_pct"]
    assert d["DCMA12"].status is CheckStatus.PASS  # golden "x" == pass
    assert d["DCMA13"].value == g["DCMA13"]  # CPLI 1.0
    assert d["DCMA14"].value == g["DCMA14"]  # BEI 0.74 / 0.59

    # High Float: documented +1 residual vs Acumen (ADR-0012) — assert within 1, fails either way
    assert abs(d["DCMA06"].count - g["DCMA06"]) <= 1
    assert d["DCMA06"].status is CheckStatus.FAIL


@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_compute_bei_matches_dcma14_entry(project: str, golden: Callable[[str], Schedule]) -> None:
    # compute_bei is the single source of truth — DCMA-14's entry must equal it exactly.
    sch = golden(project)
    standalone = compute_bei(sch)
    from_dcma = compute_dcma14(sch)["DCMA14"]
    assert standalone == from_dcma


def test_leads_detected() -> None:
    s = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=DAY),
            Task(unique_id=2, name="B", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2, lag_minutes=-DAY)],
    )
    d = compute_dcma14(s)
    assert d["DCMA02"].count == 1 and d["DCMA02"].status is CheckStatus.FAIL


def test_sf_and_ssff_relationships_incomplete_only() -> None:
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2, 3)]
    rels = [
        Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.SF),
        Relationship(predecessor_id=1, successor_id=3, type=RelationshipType.SS),
    ]
    d = compute_dcma14(_sched(tasks, rels))
    assert d["DCMA04_SF"].count == 1
    assert d["DCMA04_SSFF"].count == 1


def test_negative_float_and_high_float() -> None:
    snlt = MON  # start no later than day 0, but a 3-day predecessor pushes it out -> negative float
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=3 * DAY),
        Task(
            unique_id=2,
            name="B",
            duration_minutes=DAY,
            constraint_type=ConstraintType.SNLT,
            constraint_date=snlt,
        ),
    ]
    d = compute_dcma14(_sched(tasks, [Relationship(predecessor_id=1, successor_id=2)]))
    # the SNLT cap propagates backward, so both the constrained task and its driver go negative
    assert d["DCMA07"].count == 2 and d["DCMA07"].status is CheckStatus.FAIL


def test_high_duration_and_resources() -> None:
    tasks = [
        Task(
            unique_id=1, name="long", duration_minutes=50 * DAY, baseline_duration_minutes=50 * DAY
        ),
        Task(unique_id=2, name="short", duration_minutes=DAY),
    ]
    d = compute_dcma14(_sched(tasks))
    assert d["DCMA08"].count == 1  # task 1 baseline duration > 44d
    assert d["DCMA10"].count == 2  # neither has a resource assigned


def test_invalid_dates_actual_after_status() -> None:
    status = dt.datetime(2025, 1, 10, 17, 0)
    future = dt.datetime(2025, 1, 20, 17, 0)
    tasks = [
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            percent_complete=100.0,
            actual_finish=future,
        ),  # finished after status -> invalid
        Task(
            unique_id=2, name="B", duration_minutes=DAY, percent_complete=50.0, actual_start=future
        ),  # started after status -> invalid
    ]
    d = compute_dcma14(_sched(tasks, status_date=status))
    assert d["DCMA09"].count == 2 and d["DCMA09"].status is CheckStatus.FAIL


def test_missed_and_bei_with_baseline() -> None:
    status = dt.datetime(2025, 1, 20, 17, 0)
    bf_due = dt.datetime(2025, 1, 8, 17, 0)  # baselined to finish before status
    bs = dt.datetime(2025, 1, 6, 8, 0)  # a real baseline carries a start + duration (BEI: dur > 0)
    tasks = [
        # due, completed on time -> not missed, counts toward BEI numerator
        Task(
            unique_id=1,
            name="ontime",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_start=bs,
            baseline_duration_minutes=DAY,
            baseline_finish=bf_due,
            actual_finish=dt.datetime(2025, 1, 7, 17, 0),
        ),
        # due, not finished -> missed
        Task(
            unique_id=2,
            name="late",
            duration_minutes=DAY,
            baseline_start=bs,
            baseline_duration_minutes=DAY,
            baseline_finish=bf_due,
        ),
    ]
    d = compute_dcma14(_sched(tasks, status_date=status))
    assert d["DCMA11"].count == 1 and d["DCMA11"].population == 2  # one missed of two due
    assert d["DCMA14"].count == 1 and d["DCMA14"].population == 2  # BEI 1/2 = 0.5
    assert d["DCMA14"].value == 0.5


def test_critical_path_test_fail() -> None:
    # An MSO-pinned low-UID critical task that is not on the longest forward path:
    # delaying it does not move the project finish by the full injected delay -> FAIL.
    tasks = [
        Task(
            unique_id=1,
            name="pinned",
            duration_minutes=DAY,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
        Task(unique_id=2, name="driver", duration_minutes=20 * DAY),
    ]
    d = compute_dcma14(_sched(tasks))
    assert d["DCMA12"].status is CheckStatus.FAIL


def test_critical_path_test_not_applicable_all_milestones() -> None:
    tasks = [Task(unique_id=1, name="ms", duration_minutes=0, is_milestone=True)]
    d = compute_dcma14(_sched(tasks))
    assert d["DCMA12"].status is CheckStatus.NOT_APPLICABLE
    assert d["DCMA13"].status is CheckStatus.NOT_APPLICABLE  # project_finish 0 -> CPLI NA


def test_bei_not_applicable_without_baseline() -> None:
    d = compute_dcma14(_sched([Task(unique_id=1, name="A", duration_minutes=DAY)]))
    assert d["DCMA14"].status is CheckStatus.NOT_APPLICABLE


def test_high_float_uses_44_day_threshold_on_the_schedules_calendar() -> None:
    # the tripwire is defined in working DAYS; the minute value scales with the calendar
    standard = _sched([Task(unique_id=1, name="A", duration_minutes=DAY)])
    assert forty_four_days_min(standard) == 44 * 480
    tens = _sched(
        [Task(unique_id=1, name="A", duration_minutes=600)],
        calendar=Calendar(name="Tens", working_minutes_per_day=600),
    )
    assert forty_four_days_min(tens) == 44 * 600


def test_ten_hour_calendar_high_duration_compares_days_not_minutes() -> None:
    # 45 x 480 = 21600 minutes is 45 days on the standard calendar (an offender) but only
    # 36 days on a 10-hour calendar — the hardcoded 480-min threshold falsely flagged it.
    task = Task(unique_id=1, name="A", duration_minutes=600, baseline_duration_minutes=45 * 480)
    d10 = compute_dcma14(
        _sched([task], calendar=Calendar(name="Tens", working_minutes_per_day=600))
    )
    assert d10["DCMA08"].count == 0
    d8 = compute_dcma14(_sched([task]))
    assert d8["DCMA08"].count == 1


def test_ten_hour_calendar_high_float_compares_days_not_minutes() -> None:
    # Parallel to a 41-day driver, task 2 carries 40 working days of float = 24000 minutes
    # on the 600-min calendar. 24000 > 44x480 made it a false offender; 40 days is under
    # the 44-day tripwire on this schedule's own calendar.
    tasks = [
        Task(unique_id=1, name="driver", duration_minutes=41 * 600),
        Task(unique_id=2, name="floaty", duration_minutes=600),
    ]
    d = compute_dcma14(_sched(tasks, calendar=Calendar(name="Tens", working_minutes_per_day=600)))
    assert d["DCMA06"].count == 0


def test_no_links_is_na_not_fail() -> None:
    # zero logic links once read as FS-share 0/0 = 0% >= 90 -> FAIL with no offenders —
    # the §6 uncited-finding crash class. An empty population is NA across the board.
    d = compute_dcma14(_sched([Task(unique_id=1, name="A", duration_minutes=DAY)]))
    for key in ("DCMA04_FS", "DCMA02", "DCMA03"):
        assert d[key].status is CheckStatus.NOT_APPLICABLE, key


def test_no_status_date_makes_invalid_dates_na() -> None:
    # neither invalid-dates condition is assessable without a data date — NA, not PASS
    d = compute_dcma14(_sched([Task(unique_id=1, name="A", duration_minutes=DAY)]))
    assert d["DCMA09"].status is CheckStatus.NOT_APPLICABLE


def test_bei_numerator_is_cumulative_complete_among_the_due_set() -> None:
    # ADR-0176 (corrects ADR-0089): BOTH BEI terms score the SAME cumulative baselined-due
    # population. A task completed EARLY — ahead of a baseline finish that is not yet due —
    # does NOT inflate the numerator (Acumen oracle: engine 0.55 vs Fuse 0.27 on
    # Hard_File_updated came exactly from counting such tasks). One due-but-unfinished +
    # one finished-early-not-yet-due = 0/1, not 1/1.
    status = MON + dt.timedelta(days=10)
    tasks = [
        Task(
            unique_id=1,
            name="due",
            duration_minutes=DAY,
            baseline_start=MON,
            baseline_duration_minutes=DAY,
            baseline_finish=MON + dt.timedelta(days=5),
        ),
        Task(
            unique_id=2,
            name="early",
            duration_minutes=DAY,
            baseline_start=MON + dt.timedelta(days=29),
            baseline_duration_minutes=DAY,
            baseline_finish=MON + dt.timedelta(days=30),
            actual_start=MON + dt.timedelta(days=3),
            actual_finish=MON + dt.timedelta(days=4),
            percent_complete=100.0,
        ),
    ]
    bei = compute_dcma14(_sched(tasks, status_date=status))["DCMA14"]
    assert bei.count == 0 and bei.population == 1 and bei.value == 0.0
    assert bei.offender_uids == (1,)  # the due-but-unfinished activity stays citable
    # once the early completion's baseline finish comes DUE, it counts in both terms
    later = compute_dcma14(_sched(tasks, status_date=MON + dt.timedelta(days=31)))["DCMA14"]
    assert later.count == 1 and later.population == 2 and later.value == 0.5


def test_exclude_milestones_scopes_work_checks_only() -> None:
    """ADR-0277 Acumen-parity milestone scope: exclude_milestones drops zero-duration milestones
    from the float / logic / constraint / relationship checks (a milestone is not an activity whose
    float or constraint is meaningful), but NEVER from the completion checks (Missed / BEI).
    Verified UID-exact against Acumen on the Large Test File (Hard 1→0, Negative Float 41→35)."""
    tasks = [
        # one normal task and one milestone per work-check, each tripping it
        Task(
            unique_id=1,
            name="hard-task",
            duration_minutes=DAY,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
        Task(
            unique_id=2,
            name="hard-ms",
            duration_minutes=0,
            is_milestone=True,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
        Task(unique_id=3, name="neg-task", duration_minutes=DAY, stored_total_float_minutes=-DAY),
        Task(
            unique_id=4,
            name="neg-ms",
            duration_minutes=0,
            is_milestone=True,
            stored_total_float_minutes=-DAY,
        ),
        Task(
            unique_id=5, name="hf-task", duration_minutes=DAY, stored_total_float_minutes=100 * DAY
        ),
        Task(
            unique_id=6,
            name="hf-ms",
            duration_minutes=0,
            is_milestone=True,
            stored_total_float_minutes=100 * DAY,
        ),
    ]
    sch = _sched(tasks)
    inc = compute_dcma14(sch)  # default: milestones included (prior behaviour)
    exc = compute_dcma14(sch, exclude_milestones=True)

    assert inc["DCMA05"].count == 2 and exc["DCMA05"].count == 1  # Hard constraints
    assert inc["DCMA07"].count == 2 and exc["DCMA07"].count == 1  # Negative float
    assert inc["DCMA06"].count == 2 and exc["DCMA06"].count == 1  # High float
    # exactly the milestone UIDs are the ones dropped
    assert set(inc["DCMA05"].offender_uids) - set(exc["DCMA05"].offender_uids) == {2}
    assert set(inc["DCMA07"].offender_uids) - set(exc["DCMA07"].offender_uids) == {4}
    assert set(inc["DCMA06"].offender_uids) - set(exc["DCMA06"].offender_uids) == {6}
    # the denominators (population) also drop the milestones for those checks
    assert exc["DCMA07"].population == inc["DCMA07"].population - 3


def test_exclude_milestones_keeps_missed_milestones() -> None:
    """A missed MILESTONE is a real missed deliverable — the completion checks keep milestones under
    both scopes (excluding them would undercount vs Acumen)."""
    status = MON + dt.timedelta(days=10)
    due = MON  # baselined to finish before the data date
    tasks = [
        Task(unique_id=1, name="late-task", duration_minutes=DAY, baseline_finish=due),
        Task(
            unique_id=2, name="late-ms", duration_minutes=0, is_milestone=True, baseline_finish=due
        ),
    ]
    sch = _sched(tasks, status_date=status)
    inc = compute_dcma14(sch)
    exc = compute_dcma14(sch, exclude_milestones=True)
    assert inc["DCMA11"].count == 2  # both the task and the milestone are missed
    assert exc["DCMA11"].count == 2  # milestone STILL counted under the exclude scope
    assert set(inc["DCMA11"].offender_uids) == set(exc["DCMA11"].offender_uids) == {1, 2}


def test_exclude_milestones_default_is_identical_to_prior() -> None:
    """Default off must be byte-identical to the prior single-arg behaviour (protects the P2/P5
    goldens): a schedule with no milestones is unaffected either way, and the default equals the
    explicit include on the golden P5 audit."""
    sch = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                constraint_type=ConstraintType.MSO,
                constraint_date=MON,
            ),
        ]
    )
    a = {k: v.count for k, v in compute_dcma14(sch).items()}
    b = {k: v.count for k, v in compute_dcma14(sch, exclude_milestones=False).items()}
    assert a == b
