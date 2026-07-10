"""Finish-forecast tests — hand-verified ES/rate math, honest absences, golden pins (M15)."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.forecast import (
    compute_carnac_summary,
    compute_finish_forecasts,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, *, baseline_day: int, done: bool) -> Task:
    baseline = dt.datetime(2025, 1, 5 + baseline_day, 17, 0)
    extra = (
        dict(
            percent_complete=100.0,
            actual_start=MON,
            actual_finish=baseline,
        )
        if done
        else {}
    )
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        baseline_finish=baseline,
        **extra,  # type: ignore[arg-type]
    )


def _chain(tasks: list[Task]) -> Schedule:
    from itertools import pairwise

    from schedule_forensics.model.relationship import Relationship

    rels = [
        Relationship(predecessor_id=a.unique_id, successor_id=b.unique_id)
        for a, b in pairwise(tasks)
    ]
    return Schedule(name="f", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels))


def test_earned_schedule_forecast_hand_verified() -> None:
    # 4 one-day tasks baselined on days 1..4; 2 complete; status at end of day 4
    # (AT = 1920 min). ES = offset of the 2nd planned finish = 960. SPI(t) = 0.5.
    # IEAC(t) = 1920 + (1920 - 960) / 0.5 = 3840 min = end of working day 8 -> Jan 15.
    tasks = [_task(i, baseline_day=i, done=(i <= 2)) for i in (1, 2, 3, 4)]
    sch = _chain(tasks).model_copy(update={"status_date": dt.datetime(2025, 1, 9, 17, 0)})
    fs = compute_finish_forecasts(sch)
    by_id = {f.method_id: f for f in fs.forecasts}
    assert fs.spi_t == 0.5
    assert fs.planned_finish == dt.date(2025, 1, 9)
    assert by_id["earned_schedule"].finish == dt.date(2025, 1, 15)
    # the CPM method is the network's own finish: 4 chained one-day tasks -> Jan 9
    assert by_id["cpm"].finish == dt.date(2025, 1, 9)
    assert fs.completed_count == 2 and fs.remaining_count == 2


def test_rate_forecast_matches_first_principles() -> None:
    tasks = [_task(i, baseline_day=i, done=(i <= 2)) for i in (1, 2, 3, 4)]
    status = dt.datetime(2025, 3, 6, 17, 0)  # 59 elapsed days
    sch = _chain(tasks).model_copy(update={"status_date": status})
    fs = compute_finish_forecasts(sch)
    rate = fs.rate_per_month
    assert rate is not None and rate > 0
    months_per = 365.25 / 12
    expected_months = 2 / (2 / (59 / months_per))  # remaining / rate
    expected = status.date() + dt.timedelta(days=round(expected_months * months_per))
    by_id = {f.method_id: f for f in fs.forecasts}
    assert by_id["rate"].finish == expected  # completed and to-go are equal -> ~59 more days


def test_rate_forecast_absent_when_no_time_has_elapsed_since_start() -> None:
    """If the status date is the project start day, zero months have elapsed
    (``elapsed_months <= 0``) so a completion rate cannot be derived — the rate forecast yields
    no date and the default basis (forecast.py branch 87->98). Completed work exists, so this is
    the elapsed-time guard, not the no-completions guard."""
    tasks = [_task(i, baseline_day=i, done=(i <= 2)) for i in (1, 2, 3, 4)]
    # status on the very first project day -> status.date() == project_start.date() -> elapsed 0.
    sch = _chain(tasks).model_copy(update={"status_date": MON})
    fs = compute_finish_forecasts(sch)
    by_id = {f.method_id: f for f in fs.forecasts}
    assert by_id["rate"].finish is None  # no elapsed time → no rate forecast
    assert fs.rate_per_month is None
    assert fs.completed_count == 2  # there ARE completions; only elapsed time is missing
    assert "needs a status date and at least one completed activity" in by_id["rate"].basis


def test_missing_inputs_yield_no_date_never_a_fabrication() -> None:
    # no status date, no baselines, nothing complete: only the CPM answer exists
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    ]
    fs = compute_finish_forecasts(Schedule(name="s", project_start=MON, tasks=tuple(tasks)))
    by_id = {f.method_id: f for f in fs.forecasts}
    assert by_id["cpm"].finish is not None
    assert by_id["rate"].finish is None
    assert by_id["earned_schedule"].finish is None
    assert fs.spi_t is None and fs.rate_per_month is None
    assert fs.citation_uids  # the §6 anchor is always present


def test_carnac_summary_reuses_forecast_and_cpm(golden_project5: Schedule) -> None:
    # PBIX page 13 (ADR-0042): the Carnac cards must equal the forecast/CPM values exactly.
    cpm = compute_cpm(golden_project5)
    fs = compute_finish_forecasts(golden_project5, cpm)
    c = compute_carnac_summary(golden_project5, cpm, fs)
    by_id = {f.method_id: f for f in fs.forecasts}
    assert c.latest_finish == by_id["cpm"].finish == dt.date(2028, 1, 25)
    assert c.forecasted_end == by_id["rate"].finish == dt.date(2028, 6, 10)
    assert c.estimated_end_es == by_id["earned_schedule"].finish == dt.date(2029, 2, 1)
    assert c.spi_t == fs.spi_t == 0.47
    assert c.avg_tasks_per_month == fs.rate_per_month == 4.62
    assert c.to_go_count == fs.remaining_count == 99
    # derived working-day spans (golden P5: 497 wd project span, ES 60 wd)
    assert c.project_duration_days == 497.0
    assert c.earned_schedule_days == 60.0
    assert c.earliest_start == dt.date(2026, 3, 2)
    # remaining duration is positive and no longer than the whole project
    assert c.remaining_duration_days is not None
    assert 0 < c.remaining_duration_days <= c.project_duration_days


def test_carnac_summary_honest_absences_without_status_or_progress() -> None:
    # no status date, no completions, no baselines: rate/ES/remaining are None, never faked
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
    ]
    sch = _chain(tasks)
    cpm = compute_cpm(sch)
    c = compute_carnac_summary(sch, cpm, compute_finish_forecasts(sch, cpm))
    assert c.latest_finish is not None  # the CPM date always exists
    assert c.forecasted_end is None and c.estimated_end_es is None
    assert c.avg_tasks_per_month is None and c.spi_t is None
    assert c.earned_schedule_days is None
    assert c.remaining_duration_days is None  # no data date -> no to-go span
    assert c.to_go_count == 2


def test_carnac_summary_without_stored_starts_has_no_project_window() -> None:
    # tasks carry no stored start -> earliest start / project duration are None (not faked);
    # the CPM finish still exists (logic always yields a date)
    tasks = [Task(unique_id=i, name=f"T{i}", duration_minutes=DAY, start=None) for i in (1, 2)]
    sch = _chain(tasks)
    cpm = compute_cpm(sch)
    c = compute_carnac_summary(sch, cpm, compute_finish_forecasts(sch, cpm))
    assert c.earliest_start is None and c.project_duration_days is None
    assert c.latest_finish is not None


def test_golden_pins(golden_project2: Schedule, golden_project5: Schedule) -> None:
    p2 = compute_finish_forecasts(golden_project2)
    by_id = {f.method_id: f for f in p2.forecasts}
    assert by_id["cpm"].finish == dt.date(2027, 8, 30)
    assert by_id["rate"].finish == dt.date(2027, 8, 7)
    assert by_id["earned_schedule"].finish == dt.date(2029, 3, 8)
    assert p2.spi_t == 0.45 and p2.rate_per_month == 7.33
    p5 = compute_finish_forecasts(golden_project5)
    by_id5 = {f.method_id: f for f in p5.forecasts}
    assert by_id5["cpm"].finish == dt.date(2028, 1, 25)
    assert by_id5["rate"].finish == dt.date(2028, 6, 10)
    # exact-ratio IEAC(t): dividing by the 2-decimal SPI(t) (0.47 vs 0.4651) read 9 days early
    assert by_id5["earned_schedule"].finish == dt.date(2029, 2, 1)
    assert p5.planned_finish == dt.date(2027, 7, 9)


# --- group-weighted rollup (ADR-0188) -------------------------------------------------


def _rollup_schedule() -> Schedule:
    """Two custom-field groups: 'Hot' (2 done of 3) and 'Cold' (0 done of 2 — unforecastable
    by rate). Data date after the completions so rates and ES are defined."""

    def gt(uid: int, group: str, *, done: bool, baseline_day: int) -> Task:
        # _task's day arithmetic is January-bound; build the baseline date directly
        baseline = dt.datetime(2025, 1, 6, 17, 0) + dt.timedelta(days=baseline_day)
        extra = (
            {"percent_complete": 100.0, "actual_start": MON, "actual_finish": baseline}
            if done
            else {}
        )
        return Task(
            unique_id=uid,
            name=f"T{uid}",
            duration_minutes=DAY,
            baseline_finish=baseline,
            custom_fields=(("CAM", group),),
            **extra,  # type: ignore[arg-type]
        )

    tasks = (
        gt(1, "Hot", done=True, baseline_day=1),
        gt(2, "Hot", done=True, baseline_day=2),
        gt(3, "Hot", done=False, baseline_day=60),
        gt(4, "Cold", done=False, baseline_day=61),
        gt(5, "Cold", done=False, baseline_day=62),
    )
    return Schedule(
        name="Rollup",
        project_start=MON,
        status_date=dt.datetime(2025, 3, 3, 17, 0),
        tasks=tasks,
        custom_field_labels=("CAM",),  # grouping resolves custom fields via this registry
    )


def test_group_rollup_weights_disclose_and_bottleneck() -> None:
    from schedule_forensics.engine.forecast import compute_group_rollup

    sch = _rollup_schedule()
    rollup = compute_group_rollup(sch, "CAM")
    assert rollup is not None
    assert rollup.field == "CAM"
    # both groups carry to-go work; only Hot has completions (an SPI + a rate)
    assert rollup.groups_total == 2
    assert rollup.total_to_go == 3
    # Cold has no completions -> honestly unforecastable by rate, never imputed
    assert rollup.unforecastable == ("Cold",)
    # the bottleneck rate answer comes from the only forecastable group
    assert rollup.rate_limiting_group == "Hot"
    assert rollup.rate_finish is not None and rollup.rate_finish > sch.status_date.date()
    # weighted SPI(t) covers only the SPI-bearing groups' to-go work — disclosed
    assert rollup.covered_to_go <= rollup.total_to_go
    if rollup.weighted_spi_t is not None:
        assert rollup.weighted_spi_t > 0


def test_group_rollup_none_when_field_yields_no_groups() -> None:
    from schedule_forensics.engine.forecast import compute_group_rollup

    # None is reserved for a schedule with no tasks at all (an unknown field still
    # yields the NA group, so a populated schedule never returns None)
    empty = Schedule(name="E", project_start=MON, tasks=())
    assert compute_group_rollup(empty, "CAM") is None
