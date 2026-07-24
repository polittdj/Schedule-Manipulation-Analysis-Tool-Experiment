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


# ── ADR-0280: the single Acumen-parity mode (supersedes the milestone/CPLI toggles) ──────


def test_acumen_parity_population_is_baseline_duration_in_whole_days() -> None:
    """The unifying parity rule: Acumen scopes the work checks to Baseline Duration > 0,
    whole days (a sub-day baseline reads as 0), and KEEPS milestones that carry a real baseline. A
    Normal task with a half-day baseline drops out under parity; a baselined milestone stays in."""
    tasks = [
        # normal, hard-constrained, but only a half-day baseline -> parity drops it (sub-day)
        Task(
            unique_id=1,
            name="half-day",
            duration_minutes=DAY,
            baseline_duration_minutes=DAY // 2,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
        # milestone, hard-constrained, WITH a 2-day baseline -> parity KEEPS it (IncludeMilestone=1)
        Task(
            unique_id=2,
            name="ms-baselined",
            duration_minutes=0,
            is_milestone=True,
            baseline_duration_minutes=2 * DAY,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
    ]
    sch = _sched(tasks)
    default = compute_dcma14(sch)["DCMA05"]
    parity = compute_dcma14(sch, acumen_parity=True)["DCMA05"]
    assert set(default.offender_uids) == {1, 2}  # pure logic: both hard-constrained
    assert set(parity.offender_uids) == {2}  # parity: sub-day baseline dropped, milestone kept


def test_acumen_parity_resources_uses_baseline_cost_and_work() -> None:
    """Parity flags Resources on Baseline Cost = 0 AND Baseline Work = 0 (not "no named resource"):
    a task with no resource but baseline work is NOT flagged; one with neither is."""
    tasks = [
        Task(
            unique_id=1, name="no-loading", duration_minutes=DAY, baseline_duration_minutes=2 * DAY
        ),
        Task(
            unique_id=2,
            name="has-baseline-work",
            duration_minutes=DAY,
            baseline_duration_minutes=2 * DAY,
            baseline_work_minutes=3 * DAY,
        ),
    ]
    sch = _sched(tasks)
    default = compute_dcma14(sch)["DCMA10"]
    parity = compute_dcma14(sch, acumen_parity=True)["DCMA10"]
    assert set(default.offender_uids) == {1, 2}  # pure logic: neither has a named resource
    assert set(parity.offender_uids) == {1}  # parity: #2 carries baseline work, so Acumen keeps it


def test_acumen_parity_negative_float_is_day_grained() -> None:
    """Acumen displays Total Float in whole days, so a sub-day negative float (-0.29 day) is not
    flagged under parity; a whole-day-negative float is (default flags both)."""
    tasks = [
        Task(
            unique_id=1,
            name="tiny-neg",
            duration_minutes=DAY,
            baseline_duration_minutes=2 * DAY,
            stored_total_float_minutes=-(DAY // 3),  # ≈ -0.33 day → rounds to 0
        ),
        Task(
            unique_id=2,
            name="real-neg",
            duration_minutes=DAY,
            baseline_duration_minutes=2 * DAY,
            stored_total_float_minutes=-2 * DAY,
        ),
    ]
    sch = _sched(tasks)
    assert set(compute_dcma14(sch)["DCMA07"].offender_uids) == {1, 2}
    assert set(compute_dcma14(sch, acumen_parity=True)["DCMA07"].offender_uids) == {2}


def test_acumen_parity_bei_uses_two_term_denominator() -> None:
    """Parity BEI (ADR-0280) adds Acumen's second denominator term — activities carrying a duration
    but MISSING a baseline count as due — so an un-baselined in-progress task lowers BEI."""
    status = MON + dt.timedelta(days=30)
    due = MON  # baselined to finish before the data date
    tasks = [
        Task(
            unique_id=1,
            name="done",
            duration_minutes=DAY,
            baseline_duration_minutes=2 * DAY,
            baseline_start=MON,
            baseline_finish=due,
            percent_complete=100.0,
            actual_finish=MON,
        ),
        # a real-duration task with NO baseline -> only the parity two-term denominator counts it
        Task(unique_id=2, name="no-baseline", duration_minutes=DAY),
    ]
    sch = _sched(tasks, status_date=status)
    assert compute_dcma14(sch)["DCMA14"].value == 1.0  # default: 1 complete / 1 due
    # parity: 1 complete / (1 baselined-due + 1 no-baseline) = 0.5
    assert compute_dcma14(sch, acumen_parity=True)["DCMA14"].value == 0.5


def test_acumen_parity_cpli_uses_stored_float() -> None:
    """Parity CPLI reads the STORED negative float + stored finish (folds in the CPLI toggle):
    default reads ~0 recomputed float → 1.0, parity reads the behind-schedule slip → < 1."""
    status = MON
    finish = MON + dt.timedelta(days=30)
    sch = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=5 * DAY,
                baseline_duration_minutes=2 * DAY,
                finish=finish,
                stored_total_float_minutes=-4 * DAY,
            ),
        ],
        status_date=status,
    )
    assert compute_dcma14(sch)["DCMA13"].value == 1.0
    parity = compute_dcma14(sch, acumen_parity=True)["DCMA13"]
    assert parity.value < 1.0 and parity.status is CheckStatus.FAIL


def test_acumen_parity_default_is_identical_to_prior() -> None:
    """Default off (the arg absent) must equal ``acumen_parity=False`` on every check: pure-logic
    behaviour is byte-identical, protecting the P2/P5 golden gate."""
    tasks = [
        Task(
            unique_id=1,
            name="A",
            duration_minutes=DAY,
            baseline_duration_minutes=DAY,
            constraint_type=ConstraintType.MSO,
            constraint_date=MON,
        ),
    ]
    sch = _sched(tasks)
    a = {k: (v.count, v.population, v.value) for k, v in compute_dcma14(sch).items()}
    b = {
        k: (v.count, v.population, v.value)
        for k, v in compute_dcma14(sch, acumen_parity=False).items()
    }
    assert a == b


def test_acumen_parity_invalid_dates_scoped_to_baselined_population() -> None:
    """DCMA-09 parity scoping (ADR-0283). The NASA library's "9. Invalid Forecast/Actual Dates"
    metrics carry the SAME universal PrimaryFilter as the other work checks — Baseline Duration > 0
    (whole days) — which ADR-0280 applied everywhere EXCEPT DCMA-09. Default (pure-logic) still
    flags every non-summary activity with a stored date past the status date; parity drops the
    no-baseline placeholders/milestones Acumen never lists, reproducing Fuse's detail (Large Test
    File2: 182 → 173). Each date condition self-excludes the wrong completion state, so one combined
    loop equals Acumen's two separately-filtered metrics."""
    status = MON + dt.timedelta(days=30)
    past = MON  # a stored (forecast) date already behind the data date
    future = status + dt.timedelta(days=10)  # an actual after the data date
    tasks = [
        # baselined Normal with a forecast start in the past, not yet started -> invalid in BOTH
        Task(
            unique_id=1,
            name="baselined-past-forecast",
            duration_minutes=DAY,
            baseline_duration_minutes=2 * DAY,
            start=past,
            finish=past + dt.timedelta(days=1),
        ),
        # NO-baseline milestone with a past forecast date -> Acumen never lists it (Baseline
        # Duration = 0); default flags it, parity drops it
        Task(
            unique_id=2,
            name="no-baseline-milestone",
            duration_minutes=0,
            is_milestone=True,
            start=past,
            finish=past,
        ),
        # NO-baseline completed task whose ACTUAL finish is in the future (the File2 dH18… case) ->
        # default flags the actual-in-future; parity drops it (no baseline duration)
        Task(
            unique_id=3,
            name="no-baseline-actual-future",
            duration_minutes=DAY,
            percent_complete=100.0,
            actual_start=past,
            actual_finish=future,
        ),
    ]
    sch = _sched(tasks, status_date=status)
    default = compute_dcma14(sch)["DCMA09"]
    parity = compute_dcma14(sch, acumen_parity=True)["DCMA09"]
    assert set(default.offender_uids) == {1, 2, 3}  # pure logic: every stored date past the DD
    assert default.population == 3
    assert set(parity.offender_uids) == {1}  # parity: only the baselined activity survives
    assert parity.population == 1  # population scoped to Baseline Duration > 0
