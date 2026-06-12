"""Completion-performance metrics — how finished work actually performed (M15).

The reference Power BI deck's "Metrics" / "Completion Metrics" pages slice the
**completed** work three ways against the baseline (ahead / on schedule / behind),
average the days gained and lost, and compare actual durations to their baselines
(longer/shorter than planned + the duration ratio's min/avg/max). Two index-style
measures join them: **MEI** (Milestone Execution Index — BEI restricted to milestones)
and the staleness indicator **% schedule elapsed since the latest actual finish**.
The DAX bodies in the reference deck are not extractable (XPress9-compressed
DataModel) — these are the documented reconstructions (ADR-0030). Day variances are
**calendar days** (the same axis as Net Finish Impact and the target panel).
"""

from __future__ import annotations

from collections.abc import Callable

from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    non_summary,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def compute_completion_performance(schedule: Schedule) -> dict[str, MetricResult]:
    """The deck's completion-performance family for one schedule, keyed by id.

    Populations are honest: the ahead/on/behind split runs over completed activities
    carrying **both** an actual and a baseline finish; the duration family over
    completed activities with a positive baseline duration. Empty populations read
    NA-shaped zeros (count 0 of 0), never fabricated values. All informational
    (no pass/fail threshold); every count carries its offender UIDs (§6).
    """
    tasks = non_summary(schedule)
    out: dict[str, MetricResult] = {}

    completed = [t for t in tasks if t.percent_complete >= 100.0]
    # (task, signed finish variance in calendar days — positive == finished late)
    measured: list[tuple[Task, int]] = []
    for t in completed:
        if t.actual_finish is not None and t.baseline_finish is not None:
            measured.append((t, (t.actual_finish.date() - t.baseline_finish.date()).days))
    ahead = [(t, v) for t, v in measured if v < 0]
    on_schedule = [(t, v) for t, v in measured if v == 0]
    behind = [(t, v) for t, v in measured if v > 0]
    n = len(measured)
    out["completed_ahead"] = _count("completed_ahead", "Completed Ahead", _tasks(ahead), n)
    out["completed_on_schedule"] = _count(
        "completed_on_schedule", "Completed On Schedule", _tasks(on_schedule), n
    )
    out["completed_behind"] = _count(
        "completed_behind", "Completed Behind Baseline", _tasks(behind), n
    )
    out["avg_days_ahead"] = _average(
        "avg_days_ahead", "Average Days Ahead", [-v for _, v in ahead], _tasks(ahead), n
    )
    out["avg_days_late"] = _average(
        "avg_days_late", "Average Days Late", [v for _, v in behind], _tasks(behind), n
    )
    out["avg_completion_variance"] = _average(
        "avg_completion_variance",
        "Average Completion Variance",
        [v for _, v in measured],
        _tasks(measured),
        n,
    )

    sized = [
        t
        for t in completed
        if t.baseline_duration_minutes is not None and t.baseline_duration_minutes > 0
    ]
    longer = [t for t in sized if t.duration_minutes > (t.baseline_duration_minutes or 0)]
    shorter = [t for t in sized if t.duration_minutes < (t.baseline_duration_minutes or 0)]
    ratios = [t.duration_minutes / (t.baseline_duration_minutes or 1) for t in sized]
    out["longer_than_planned"] = _count(
        "longer_than_planned", "Activities Longer Than Planned", longer, len(sized)
    )
    out["shorter_than_planned"] = _count(
        "shorter_than_planned", "Activities Shorter Than Baseline", shorter, len(sized)
    )
    out["duration_ratio_min"] = _ratio("duration_ratio_min", "Duration Ratio Min", ratios, min)
    out["duration_ratio_avg"] = _ratio(
        "duration_ratio_avg", "Duration Ratio Average", ratios, lambda r: sum(r) / len(r)
    )
    out["duration_ratio_max"] = _ratio("duration_ratio_max", "Duration Ratio Max", ratios, max)

    out["mei"] = _mei(schedule, tasks)
    out["elapsed_since_last_finish"] = _staleness(schedule)
    return out


def _tasks(pairs: list[tuple[Task, int]]) -> list[Task]:
    return [t for t, _ in pairs]


def _count(mid: str, name: str, offenders: list[Task], population: int) -> MetricResult:
    uids = tuple(sorted(t.unique_id for t in offenders))
    value = round(100.0 * len(uids) / population, 1) if population else 0.0
    return MetricResult(
        mid, name, len(uids), population, value, "%", CheckStatus.NOT_APPLICABLE, offender_uids=uids
    )


def _average(
    mid: str, name: str, day_values: list[int], offenders: list[Task], population: int
) -> MetricResult:
    value = round(sum(day_values) / len(day_values), 1) if day_values else 0.0
    return MetricResult(
        mid,
        name,
        len(day_values),
        population,
        value,
        "days",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=tuple(sorted(t.unique_id for t in offenders)),
    )


def _ratio(
    mid: str, name: str, ratios: list[float], pick: Callable[[list[float]], float]
) -> MetricResult:
    value = round(pick(ratios), 2) if ratios else 0.0
    return MetricResult(
        mid, name, len(ratios), len(ratios), value, "ratio", CheckStatus.NOT_APPLICABLE
    )


def _mei(schedule: Schedule, tasks: list[Task]) -> MetricResult:
    """Milestone Execution Index — BEI restricted to milestones.

    Milestones actually finished by the status date ÷ milestones the baseline placed
    by then. NA without a status date or with no due milestones (never a fabricated 0).
    The offenders are the due-but-unfinished milestones (citable, §6).
    """
    status = schedule.status_date
    milestones = [t for t in tasks if t.is_milestone]
    if status is None:
        return MetricResult("mei", "MEI", 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    due = [t for t in milestones if t.baseline_finish is not None and t.baseline_finish <= status]
    finished = sum(
        1 for t in milestones if t.actual_finish is not None and t.actual_finish <= status
    )
    if not due:
        return MetricResult("mei", "MEI", finished, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    offenders = tuple(sorted(t.unique_id for t in due if t.actual_finish is None))
    return MetricResult(
        "mei",
        "MEI",
        finished,
        len(due),
        round(finished / len(due), 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=offenders,
    )


def _staleness(schedule: Schedule) -> MetricResult:
    """% of the elapsed schedule that has passed since anything actually finished.

    High values mean the plan keeps aging while nothing completes — the deck's
    staleness tripwire. NA without a status date, any actual finish, or elapsed time.
    """
    mid, name = "elapsed_since_last_finish", "% Schedule Elapsed Since Latest Actual Finish"
    status = schedule.status_date
    finishes = [t.actual_finish for t in non_summary(schedule) if t.actual_finish is not None]
    if status is None or not finishes:
        return MetricResult(mid, name, 0, 0, 0.0, "%", CheckStatus.NOT_APPLICABLE)
    elapsed = (status.date() - schedule.project_start.date()).days
    if elapsed <= 0:
        return MetricResult(mid, name, 0, 0, 0.0, "%", CheckStatus.NOT_APPLICABLE)
    quiet = max(0, (status.date() - max(finishes).date()).days)
    return MetricResult(
        mid,
        name,
        quiet,
        elapsed,
        round(100.0 * quiet / elapsed, 1),
        "%",
        CheckStatus.NOT_APPLICABLE,
    )
