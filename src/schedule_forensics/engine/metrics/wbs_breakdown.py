"""WBS-grouped completion + Earned-Schedule breakdown — the deck's Completion Metrics
and SPI/Earned-Schedule pages (PBIX pages 8, 9; ADR-0041).

The reference deck pivots its completion family **by WBS**: per WBS group, the activity
count, completed / not-completed counts, the ahead / on-schedule / behind split with
average days, longer/shorter-than-planned counts and the duration ratio, plus a per-WBS
**SPI(t) / Earned Schedule** combo. Activities are grouped by the **top-level WBS
segment** (the first dotted component of the stored WBS code — ``"7.3"`` → ``"7"``); a
2-level code base rolls up to a useful, bounded set of groups (a full-code pivot would
be all singletons). Activities with no WBS group under ``"(none)"``.

Lightweight frozen dataclasses (deliberately **not** ``MetricResult`` — the
metric-dictionary coverage test is unaffected, the ADR-0038/0039/0040 pattern). Day
figures are **calendar days** for the completion variances (the same axis as the
schedule-level completion panel) and **working days** for Earned Schedule / Actual Time
(the SPI(t) time basis, on the schedule's own calendar). Every population is honest —
empty groups read ``None``/0, never a fabricated value.
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary, percent
from schedule_forensics.engine.metrics.evm import earned_schedule
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Label for activities carrying no WBS code.
_NO_WBS = "(none)"


def _top_level(wbs: str | None) -> str:
    """The top-level WBS segment (first dotted component), or ``"(none)"``."""
    if not wbs:
        return _NO_WBS
    return wbs.split(".", 1)[0].strip() or _NO_WBS


@dataclass(frozen=True)
class WBSGroup:
    """One WBS group's completion + Earned-Schedule figures."""

    wbs: str  # the top-level WBS segment (or "(none)")
    total: int  # non-summary activities in the group
    completed: int  # percent_complete >= 100
    not_completed: int
    percent_complete: float  # share of the group's activities that are complete
    completed_ahead: int  # completed with actual & baseline finish, finished early
    completed_on_schedule: int  # finished exactly on the baseline finish
    completed_behind: int  # finished late
    avg_days_ahead: float | None  # mean calendar days early (early finishers), else None
    avg_days_late: float | None  # mean calendar days late (late finishers), else None
    avg_completion_variance: float | None  # mean signed variance (+ = late), else None
    longer_than_planned: int  # completed, actual duration > baseline
    shorter_than_planned: int
    duration_ratio_min: float | None  # actual / baseline duration, over sized completions
    duration_ratio_avg: float | None
    duration_ratio_max: float | None
    spi_t: float | None  # Earned-Schedule SPI(t) for the group, else None
    earned_schedule_days: float | None  # ES in working days
    actual_time_days: float | None  # AT in working days (schedule-level basis)
    uids: tuple[int, ...]  # the group's non-summary activity ids (for the SPI-bar drill)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _group(schedule: Schedule, wbs: str, tasks: list[Task]) -> WBSGroup:
    completed = [t for t in tasks if t.percent_complete >= 100.0]
    n = len(tasks)

    # ahead / on / behind, over completions carrying both an actual and a baseline finish
    measured: list[tuple[Task, int]] = [
        (t, (t.actual_finish.date() - t.baseline_finish.date()).days)
        for t in completed
        if t.actual_finish is not None and t.baseline_finish is not None
    ]
    ahead = [v for _, v in measured if v < 0]
    on_sched = [v for _, v in measured if v == 0]
    behind = [v for _, v in measured if v > 0]

    sized = [
        t
        for t in completed
        if t.baseline_duration_minutes is not None and t.baseline_duration_minutes > 0
    ]
    ratios = [t.duration_minutes / (t.baseline_duration_minutes or 1) for t in sized]
    longer = sum(1 for t in sized if t.duration_minutes > (t.baseline_duration_minutes or 0))
    shorter = sum(1 for t in sized if t.duration_minutes < (t.baseline_duration_minutes or 0))

    es = earned_schedule(schedule, tasks)
    per_day = schedule.calendar.working_minutes_per_day or 1

    return WBSGroup(
        wbs=wbs,
        total=n,
        completed=len(completed),
        not_completed=n - len(completed),
        percent_complete=round(percent(len(completed), n), 1),
        completed_ahead=len(ahead),
        completed_on_schedule=len(on_sched),
        completed_behind=len(behind),
        avg_days_ahead=_mean([-v for v in ahead]),
        avg_days_late=_mean([float(v) for v in behind]),
        avg_completion_variance=_mean([float(v) for _, v in measured]),
        longer_than_planned=longer,
        shorter_than_planned=shorter,
        duration_ratio_min=round(min(ratios), 2) if ratios else None,
        duration_ratio_avg=round(sum(ratios) / len(ratios), 2) if ratios else None,
        duration_ratio_max=round(max(ratios), 2) if ratios else None,
        spi_t=round(es.spi_t, 2) if es is not None else None,
        earned_schedule_days=round(es.es_minutes / per_day, 1) if es is not None else None,
        actual_time_days=round(es.at_minutes / per_day, 1) if es is not None else None,
        uids=tuple(t.unique_id for t in tasks),
    )


def compute_wbs_breakdown(schedule: Schedule) -> tuple[WBSGroup, ...]:
    """Per-top-level-WBS completion + Earned-Schedule groups, ordered by WBS code.

    Groups are sorted numerically when every label is an integer segment (the common
    case — ``"1"`` before ``"2"`` before ``"10"``), else lexicographically; ``"(none)"``
    always sorts last.
    """
    groups: dict[str, list[Task]] = {}
    for t in non_summary(schedule):
        groups.setdefault(_top_level(t.wbs), []).append(t)

    def sort_key(label: str) -> tuple[int, float, str]:
        if label == _NO_WBS:
            return (2, 0.0, "")
        if label.isdigit():
            return (0, float(label), "")
        return (1, 0.0, label)

    return tuple(_group(schedule, wbs, groups[wbs]) for wbs in sorted(groups, key=sort_key))
