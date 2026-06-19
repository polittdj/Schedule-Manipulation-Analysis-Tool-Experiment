"""FEI / BRI tests — Acumen Bible formulas, hand-verified synthetic schedules.

The exact-vs-Acumen Large-Test-File validation (BRI 0.51 / denominator 1228 EXACT; FEI starts
numerator 828 EXACT, ratios ~2.78/2.89 within .mpp→MSPDI conversion tolerance) lives in the ADR +
docs/STATE; here the formula is pinned on small committed fixtures, checked numerator/denominator
independently.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import CheckStatus, compute_bri, compute_fei
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

NOW = dt.datetime(2025, 3, 10, 17, 0)
PAST = dt.datetime(2025, 2, 1, 17, 0)
FUTURE = dt.datetime(2025, 4, 1, 17, 0)


def _t(
    uid: int,
    *,
    start: dt.datetime | None = None,
    finish: dt.datetime | None = None,
    bstart: dt.datetime | None = None,
    bfinish: dt.datetime | None = None,
    afinish: dt.datetime | None = None,
    ms: bool = False,
    summary: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=0 if ms else 480,
        is_milestone=ms,
        is_summary=summary,
        start=start,
        finish=finish,
        baseline_start=bstart,
        baseline_finish=bfinish,
        actual_finish=afinish,
        percent_complete=100.0 if afinish is not None else 0.0,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(
        name="s",
        project_start=PAST,
        status_date=NOW,
        tasks=tuple(tasks),
        relationships=(),
    )


def test_fei_starts_and_finish_counts() -> None:
    s = _sched(
        [
            # forecast to start AND baselined to start in the future -> both num & den
            _t(1, start=FUTURE, bstart=FUTURE, finish=FUTURE, bfinish=FUTURE),
            # forecast to start/finish future, but baselined in the past -> numerator only
            _t(2, start=FUTURE, bstart=PAST, finish=FUTURE, bfinish=PAST),
            # baseline start future, but forecast started already (past) -> den only
            _t(3, start=PAST, bstart=FUTURE, finish=PAST, bfinish=PAST, afinish=PAST),
            # milestone + summary are excluded from the value-task population
            _t(4, start=FUTURE, bstart=FUTURE, ms=True),
            _t(5, start=FUTURE, bstart=FUTURE, summary=True),
        ]
    )
    fei = compute_fei(s)
    # starts: forecast (Start>=now) = {1,2} = 2 ; baseline (BaselineStart>=now) = {1,3} = 2
    assert (fei["fei_starts"].count, fei["fei_starts"].population) == (2, 2)
    assert fei["fei_starts"].value == 1.0
    # finish: forecast open finish>=now = {1,2} = 2 ; baseline finish>=now = {1} = 1 -> 2.0
    assert (fei["fei_finish"].count, fei["fei_finish"].population) == (2, 1)
    assert fei["fei_finish"].value == 2.0


def test_fei_excludes_tasks_finished_early_from_finish_numerator() -> None:
    s = _sched(
        [
            # forecast finish >= now but already actually finished before now -> NOT counted
            _t(1, finish=FUTURE, bfinish=FUTURE, afinish=PAST),
            _t(2, finish=FUTURE, bfinish=FUTURE),  # open -> counted
        ]
    )
    fei = compute_fei(s)
    assert fei["fei_finish"].count == 1 and fei["fei_finish"].population == 2


def test_fei_na_when_no_baseline_in_window() -> None:
    s = _sched([_t(1, start=FUTURE, finish=FUTURE)])  # no baseline dates at all
    fei = compute_fei(s)
    assert fei["fei_starts"].status is CheckStatus.NOT_APPLICABLE
    assert fei["fei_finish"].status is CheckStatus.NOT_APPLICABLE


def test_bri_baseline_realism_and_misses() -> None:
    s = _sched(
        [
            _t(1, bfinish=PAST, afinish=PAST),  # baselined-due AND finished -> hit
            _t(2, bfinish=PAST, afinish=NOW),  # baselined-due, finished AT now -> hit
            _t(3, bfinish=PAST),  # baselined-due, not finished -> MISS
            _t(4, bfinish=FUTURE),  # baselined to finish in future -> not due, excluded
            _t(10, bfinish=PAST, afinish=PAST, ms=True),  # milestone -> excluded
        ]
    )
    bri = compute_bri(s)
    assert bri.count == 2 and bri.population == 3  # 2 of 3 baselined-due finished
    assert bri.value == round(2 / 3, 2)
    assert bri.offender_uids == (3,)  # the realism miss is citable


def test_bri_na_without_baselined_due() -> None:
    s = _sched([_t(1, bfinish=FUTURE)])  # nothing baselined to finish by now
    assert compute_bri(s).status is CheckStatus.NOT_APPLICABLE
