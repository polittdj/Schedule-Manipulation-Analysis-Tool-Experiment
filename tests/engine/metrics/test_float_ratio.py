"""Float Ratio™ tests — Acumen Bible formula AVERAGE(TotalFloat/RemainingDuration).

Hand-verified on small committed fixtures (real .mpp files are CUI): the population filter (normal,
planned/in-progress), both algebraic forms (mean-of-ratios and ratio-of-means), the
remaining-duration fallback, the division guard, the very-tight offenders, and the period-to-period
trend with its delta. Float and remaining duration are working minutes at 480/day (4800 = 10 days).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import CheckStatus, compute_float_ratio
from schedule_forensics.engine.trend import compute_float_ratio_trend
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

PAST = dt.datetime(2025, 2, 1, 17, 0)
NOW = dt.datetime(2025, 3, 10, 17, 0)


def _t(
    uid: int,
    *,
    duration: int = 4800,
    remaining: int | None = None,
    float_min: int | None = 0,
    pct: float = 0.0,
    ms: bool = False,
    summary: bool = False,
    loe: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=0 if ms else duration,
        remaining_duration_minutes=remaining,
        stored_total_float_minutes=float_min,
        percent_complete=pct,
        is_milestone=ms,
        is_summary=summary,
        is_level_of_effort=loe,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(
        name="s", project_start=PAST, status_date=NOW, tasks=tuple(tasks), relationships=()
    )


def test_float_ratio_both_forms_and_population_filter() -> None:
    s = _sched(
        [
            # A: planned, 5d float over 10d remaining -> ratio 0.5
            _t(1, duration=4800, remaining=4800, float_min=2400),
            # B: in-progress 50%, 1d float over 5d remaining -> ratio 0.2
            _t(2, duration=4800, remaining=2400, float_min=480, pct=50.0),
            # C: planned, 0 float over 20d remaining -> ratio 0.0 (very tight, an offender)
            _t(3, duration=9600, remaining=9600, float_min=0),
            # excluded from the population: milestone, summary, complete, level-of-effort
            _t(4, float_min=2400, ms=True),
            _t(5, duration=4800, remaining=4800, float_min=2400, summary=True),
            _t(6, duration=4800, remaining=0, float_min=2400, pct=100.0),
            _t(7, duration=4800, remaining=4800, float_min=2400, loe=True),
        ]
    )
    out = compute_float_ratio(s)
    primary = out["float_ratio"]
    # mean of per-activity ratios = (0.5 + 0.2 + 0.0) / 3 = 0.2333 -> 0.23
    assert primary.value == round((0.5 + 0.2 + 0.0) / 3, 2) == 0.23
    assert primary.population == 3  # only the three normal planned/in-progress activities
    assert primary.offender_uids == (3,)  # the sub-0.1 (very tight) activity is cited
    # aggregate = sum(float_days) / sum(remaining_days) = (5+1+0) / (10+5+20) = 6/35 = 0.17
    assert out["float_ratio_aggregate"].value == round(6 / 35, 2) == 0.17


def test_float_ratio_remaining_duration_falls_back_to_percent_left() -> None:
    # no stored remaining duration -> duration * (100 - pct)/100 = 4800 * 0.5 = 2400 min = 5 days
    s = _sched([_t(1, duration=4800, remaining=None, float_min=2400, pct=50.0)])
    # float 5 days over remaining 5 days -> 1.0
    assert compute_float_ratio(s)["float_ratio"].value == 1.0


def test_float_ratio_skips_zero_remaining_and_is_na_when_empty() -> None:
    # a planned activity with zero remaining duration is skipped (division guard) -> empty pop
    s = _sched([_t(1, duration=0, remaining=0, float_min=2400)])
    out = compute_float_ratio(s)
    assert out["float_ratio"].population == 0
    assert out["float_ratio"].status is CheckStatus.NOT_APPLICABLE
    assert out["float_ratio_aggregate"].status is CheckStatus.NOT_APPLICABLE


def test_float_ratio_negative_float_drags_the_ratio_below_zero() -> None:
    # behind a constraint: -5d float over 5d remaining -> -1.0 (the right forensic signal)
    s = _sched([_t(1, duration=2400, remaining=2400, float_min=-2400)])
    primary = compute_float_ratio(s)["float_ratio"]
    assert primary.value == -1.0
    assert primary.offender_uids == (1,)  # negative float is, of course, very tight


def test_float_ratio_trend_is_period_to_period_with_deltas() -> None:
    # three periods, loosening then tightening; the delta is the period-over-period change
    v1 = _sched([_t(1, duration=4800, remaining=4800, float_min=480)])  # 1d/10d = 0.1
    v2 = _sched([_t(1, duration=4800, remaining=4800, float_min=1440)])  # 3d/10d = 0.3
    v3 = _sched([_t(1, duration=4800, remaining=4800, float_min=960)])  # 2d/10d = 0.2
    series = compute_float_ratio_trend([v1, v2, v3])
    assert series.values == (0.1, 0.3, 0.2)
    assert series.deltas == (None, round(0.3 - 0.1, 2), round(0.2 - 0.3, 2)) == (None, 0.2, -0.1)
    assert series.populations == (1, 1, 1)


def test_float_ratio_trend_single_version_has_no_prior_delta() -> None:
    series = compute_float_ratio_trend([_sched([_t(1, remaining=4800, float_min=2400)])])
    assert series.values == (0.5,) and series.deltas == (None,)


def test_float_ratio_elapsed_activity_each_term_converts_on_its_own_axis() -> None:
    """Audit NEW-1, corrected by QC audit D7: each term converts to DAYS on ITS OWN axis. Total
    float — stored or recomputed — is always WORKING minutes, so it divides by the calendar's
    per-day (480 here); only the elapsed activity's remaining duration is wall-clock (1440). The
    result is the displayed-days ratio an analyst reads in MSP: 5 days of float over 5 edays of
    remaining work = 1.0. (NEW-1's fix put BOTH terms on 1440, understating the float term 3x and
    pinning 0.33 here — that pin was itself wrong.)"""
    # remaining 5 elapsed days (7200 wall-clock min); stored float 5 working days (2400 min)
    elapsed = Task(
        unique_id=1,
        name="elapsed WIP",
        duration_minutes=7200,
        duration_is_elapsed=True,
        remaining_duration_minutes=7200,
        stored_total_float_minutes=2400,
    )
    out = compute_float_ratio(_sched([elapsed]))
    # TF 2400/480 = 5 days; RD 7200/1440 = 5 edays -> 1.0
    assert out["float_ratio"].value == 1.0
