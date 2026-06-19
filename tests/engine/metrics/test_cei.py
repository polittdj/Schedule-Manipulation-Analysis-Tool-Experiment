"""CEI tests — forecast-anchored, period-over-period (Acumen DCMA parity).

Synthetic two-period schedules with hand-verified hits/misses. The exact-vs-Acumen Large-Test-File
validation (CEI Value Tasks 24/129 = 0.19, Milestones 1/6 = 0.17) is on the operator's CUI files and
is recorded in docs/STATE; here we pin the formula on small committed fixtures.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import CheckStatus, compute_cei
from schedule_forensics.engine.trend import compute_cei_trend
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

S1 = dt.datetime(2025, 2, 7, 17, 0)  # prior data date
S2 = dt.datetime(2025, 3, 10, 17, 0)  # current data date
IN = dt.datetime(2025, 2, 20, 17, 0)  # a finish inside the period (S1, S2]
AFTER = dt.datetime(2025, 4, 1, 17, 0)  # a finish after the period


def _t(
    uid: int, *, finish: dt.datetime | None, actual: dt.datetime | None, ms: bool = False
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=0 if ms else 480,
        is_milestone=ms,
        finish=finish,
        actual_finish=actual,
        percent_complete=100.0 if actual is not None else 0.0,
    )


def _sched(tasks: list[Task], status: dt.datetime) -> Schedule:
    return Schedule(
        name="s", project_start=S1, status_date=status, tasks=tuple(tasks), relationships=()
    )


def test_cei_forecast_anchored_hits_and_misses() -> None:
    # PRIOR schedule forecasts tasks 1,2,3 to finish in the period; 4 forecast after; 5 already done
    prior = _sched(
        [
            _t(1, finish=IN, actual=None),  # forecast in-period
            _t(2, finish=IN, actual=None),  # forecast in-period
            _t(3, finish=IN, actual=None),  # forecast in-period
            _t(4, finish=AFTER, actual=None),  # forecast AFTER the period -> not in denom
            _t(
                5, finish=IN, actual=S1 - dt.timedelta(days=1)
            ),  # already complete at S1 -> excluded
        ],
        S1,
    )
    # CURRENT schedule: of 1,2,3 only task 1 actually finished by S2 (2 slipped, 3 not done)
    current = _sched(
        [
            _t(1, finish=IN, actual=IN),  # finished in period -> hit
            _t(2, finish=AFTER, actual=None),  # slipped out -> miss
            _t(3, finish=AFTER, actual=None),  # miss
            _t(4, finish=AFTER, actual=None),
            _t(5, finish=IN, actual=S1 - dt.timedelta(days=1)),
        ],
        S2,
    )
    r = compute_cei(prior, current)["cei_tasks"]
    assert r.count == 1 and r.population == 3  # 1 hit of 3 forecast-due
    assert r.value == 0.33
    assert r.offender_uids == (2, 3)  # the misses, citable


def test_cei_milestones_scored_separately() -> None:
    prior = _sched(
        [
            _t(1, finish=IN, actual=None),  # task
            _t(10, finish=IN, actual=None, ms=True),  # milestone forecast in-period
            _t(11, finish=IN, actual=None, ms=True),  # milestone forecast in-period
        ],
        S1,
    )
    current = _sched(
        [
            _t(1, finish=IN, actual=IN),
            _t(10, finish=IN, actual=IN),  # milestone hit
            _t(11, finish=AFTER, actual=None),  # milestone miss
        ],
        S2,
    )
    out = compute_cei(prior, current)
    assert (out["cei_tasks"].count, out["cei_tasks"].population) == (1, 1)
    ms = out["cei_milestones"]
    assert ms.count == 1 and ms.population == 2 and ms.value == 0.5
    assert ms.offender_uids == (11,)


def test_cei_is_na_for_single_or_nonadvancing_period() -> None:
    prior = _sched([_t(1, finish=IN, actual=None)], S1)
    # same status date both sides -> non-advancing period -> NA (matches Acumen's single-period N/A)
    same = compute_cei(prior, _sched([_t(1, finish=IN, actual=IN)], S1))
    assert same["cei_tasks"].status is CheckStatus.NOT_APPLICABLE
    assert same["cei_tasks"].population == 0


def test_cei_na_when_nothing_forecast_in_period() -> None:
    prior = _sched([_t(1, finish=AFTER, actual=None)], S1)  # nothing forecast in (S1, S2]
    out = compute_cei(prior, _sched([_t(1, finish=AFTER, actual=None)], S2))
    assert (
        out["cei_tasks"].status is CheckStatus.NOT_APPLICABLE and out["cei_tasks"].population == 0
    )


def test_cei_trend_is_none_on_first_version_then_period_scored() -> None:
    v1 = _sched([_t(1, finish=IN, actual=None), _t(2, finish=IN, actual=None)], S1)
    v2 = _sched([_t(1, finish=IN, actual=IN), _t(2, finish=AFTER, actual=None)], S2)
    series = compute_cei_trend([v1, v2])
    assert series.task_values[0] is None  # first version has no prior period
    assert series.task_values[1] == 0.5  # 1 of 2 forecast-due finished
    assert series.task_offenders[1] == (2,)
    assert len(series.labels) == 2


def test_cei_trend_needs_two_versions() -> None:
    import pytest

    with pytest.raises(ValueError, match="at least two"):
        compute_cei_trend([_sched([_t(1, finish=IN, actual=None)], S1)])


# --- variant cuts (Starts / Critical / adjusted), ADR-0101 -----------------------------------


def _full(
    uid: int,
    *,
    start: dt.datetime | None = None,
    finish: dt.datetime | None = None,
    astart: dt.datetime | None = None,
    afinish: dt.datetime | None = None,
    critical: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=480,
        start=start,
        finish=finish,
        actual_start=astart,
        actual_finish=afinish,
        stored_is_critical=critical,
        percent_complete=100.0 if afinish is not None else 0.0,
    )


def test_cei_task_starts_cut() -> None:
    # prior forecast tasks 1,2,3 to START in the period; current: 1 & 2 started, 3 not.
    prior = _sched(
        [_full(1, start=IN), _full(2, start=IN), _full(3, start=IN), _full(4, start=AFTER)], S1
    )
    current = _sched(
        [
            _full(1, start=IN, astart=IN),
            _full(2, start=IN, astart=IN),
            _full(3, start=AFTER),
            _full(4, start=AFTER),
        ],
        S2,
    )
    s = compute_cei(prior, current)["cei_task_starts"]
    assert s.count == 2 and s.population == 3 and s.value == round(2 / 3, 2)
    assert s.offender_uids == (3,)  # forecast to start, did not


def test_cei_critical_cut_uses_current_criticality() -> None:
    # 3 prior-forecast-due tasks; only 1 & 3 are critical in the CURRENT schedule.
    prior = _sched([_full(1, finish=IN), _full(2, finish=IN), _full(3, finish=IN)], S1)
    current = _sched(
        [
            _full(1, finish=IN, afinish=IN, critical=True),  # critical + complete -> hit
            _full(2, finish=AFTER, critical=False),  # not critical -> excluded
            _full(3, finish=AFTER, critical=True),  # critical, not complete -> miss
        ],
        S2,
    )
    c = compute_cei(prior, current)["cei_critical"]
    assert c.count == 1 and c.population == 2 and c.value == 0.5  # 1 of 2 critical due finished
    assert c.offender_uids == (3,)


def test_cei_adjusted_credits_early_completions() -> None:
    # denom = prior-forecast-due in window (1,2); task 3 forecast in the FUTURE but done early.
    prior = _sched([_full(1, finish=IN), _full(2, finish=IN), _full(3, finish=AFTER)], S1)
    current = _sched(
        [
            _full(1, finish=IN, afinish=IN),  # in-window complete
            _full(2, finish=AFTER),  # in-window, not complete
            _full(3, finish=AFTER, afinish=IN),  # FUTURE-forecast but completed early -> credit
        ],
        S2,
    )
    out = compute_cei(prior, current)
    plain = out["cei_tasks"]
    adj = out["cei_tasks_adjusted"]
    assert (plain.count, plain.population) == (1, 2)  # plain: 1 of 2 in-window
    # adjusted: numerator adds the early future completion (3) -> 2 of 2
    assert (adj.count, adj.population) == (2, 2) and adj.value == 1.0


def test_cei_trend_carries_variant_series() -> None:
    v1 = _sched([_full(1, start=IN, finish=IN)], S1)
    v2 = _sched([_full(1, start=IN, finish=IN, astart=IN, afinish=IN, critical=True)], S2)
    series = compute_cei_trend([v1, v2])
    assert series.start_values[0] is None and series.start_values[1] == 1.0
    assert series.critical_values[1] == 1.0
    assert series.adjusted_values[1] == 1.0
