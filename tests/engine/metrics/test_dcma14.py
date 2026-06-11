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

from schedule_forensics.engine.metrics import CheckStatus, compute_dcma14
from schedule_forensics.engine.metrics._common import FORTY_FOUR_DAYS_MIN
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
    tasks = [
        # due, completed on time -> not missed, counts toward BEI numerator
        Task(
            unique_id=1,
            name="ontime",
            duration_minutes=DAY,
            percent_complete=100.0,
            baseline_finish=bf_due,
            actual_finish=dt.datetime(2025, 1, 7, 17, 0),
        ),
        # due, not finished -> missed
        Task(unique_id=2, name="late", duration_minutes=DAY, baseline_finish=bf_due),
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


def test_high_float_uses_44_day_threshold() -> None:
    assert FORTY_FOUR_DAYS_MIN == 44 * 480


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


def test_bei_counts_early_completions_beyond_the_due_set() -> None:
    # DCMA's BEI numerator is ALL activities completed by the status date, not just the
    # baselined-due set: one due-but-unfinished + one finished early = 1/1, not 0/1.
    status = MON + dt.timedelta(days=10)
    tasks = [
        Task(
            unique_id=1,
            name="due",
            duration_minutes=DAY,
            baseline_finish=MON + dt.timedelta(days=5),
        ),
        Task(
            unique_id=2,
            name="early",
            duration_minutes=DAY,
            baseline_finish=MON + dt.timedelta(days=30),
            actual_start=MON + dt.timedelta(days=3),
            actual_finish=MON + dt.timedelta(days=4),
            percent_complete=100.0,
        ),
    ]
    bei = compute_dcma14(_sched(tasks, status_date=status))["DCMA14"]
    assert bei.count == 1 and bei.population == 1 and bei.value == 1.0
    assert bei.offender_uids == (1,)  # the due-but-unfinished activity stays citable
