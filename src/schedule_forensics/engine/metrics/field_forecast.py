"""Per-field group execution metrics for the Forecast page (operator 2026-07-09, ADR-0179).

The operator picks any STANDARD or CUSTOM field (e.g. a CAM code); every loaded version is
split into one group per populated value of that field plus an **NA** group for the tasks
carrying no value, and each group gets the execution indices computed over ONLY its tasks:
BEI (cumulative, ADR-0176), HMI (tasks), CEI Finish/Start, both SPI(t) methods, and a
start-basis leading index. Every figure reuses the exact engine function the schedule-wide
number comes from (one source of truth) — the group is just a sub-schedule.

**Groups with no completed work** (the operator's research ask): the finish-anchored indices
(BEI / HMI / CEI-Finish / both SPI(t)s) are mathematically undefined or degenerate there, and
published practice — the NDIA Planning & Scheduling Excellence Guide's treatment of BEI-style
indices and the DCMA construct both — is explicit that an index without qualifying data reads
N/A rather than an imputed number (an imputed 0 or 1 poisons any forecast built on it). The
accepted *leading* substitutes are START-anchored: work must start before it can finish, so a
start execution index (started ÷ baselined-to-start-by-the-data-date — the same shape as
Acumen's "BEI - Value Task Starts") plus the group's to-go burden (remaining count) forecast
execution before any finish lands. This module therefore NEVER fabricates a finish index: it
reports the start index (``sei``) and the to-go count for every group, flags
``no_completed_work``, and leaves the undefined finish measures ``None`` for the UI to render
as N/A with the start-basis read alongside.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.grouping import field_value
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.engine.metrics.dcma14 import compute_bei
from schedule_forensics.engine.metrics.evm import compute_evm_indices
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.model.schedule import Schedule

#: The display label for the unassigned group (operator: "will just title those NA").
NA_GROUP = "NA"


@dataclass(frozen=True)
class GroupMetrics:
    """One (field value, version) cell: the execution indices over ONLY that group's tasks."""

    group: str  # the field value, or NA_GROUP for unassigned tasks
    version: str  # the version label (source file or name)
    activities: int  # non-summary tasks in the group this version
    completed: int  # of those, 100% complete
    started: int  # carrying an actual start
    to_go: int  # incomplete (the group's workoff burden, in counts)
    bei: float | None  # cumulative BEI (None = no baselined-due population)
    hmi: float | None  # HMI (tasks) for the current period (needs a prior data date)
    cei_finish: float | None
    cei_start: float | None
    spi_t: float | None  # Earned-Schedule SPI(t)
    spi_t_acumen: float | None  # the Bible per-activity SPI(t)
    sei: float | None  # start execution index: started / baselined-to-start-by-DD (leading)
    no_completed_work: bool  # finish-anchored indices undefined — read the start basis


def _value(result: MetricResult) -> float | None:
    """A MetricResult's value, or None when it is NOT_APPLICABLE (never fabricate)."""
    return None if result.status is CheckStatus.NOT_APPLICABLE else result.value


def _sub_schedule(schedule: Schedule, uids: set[int]) -> Schedule:
    """The group as a sub-schedule (same frame; relationships among members only)."""
    tasks = tuple(t for t in schedule.tasks if t.unique_id in uids)
    rels = tuple(
        r for r in schedule.relationships if r.predecessor_id in uids and r.successor_id in uids
    )
    return schedule.model_copy(update={"tasks": tasks, "relationships": rels})


def _groups(schedule: Schedule, field: str) -> dict[str, set[int]]:
    """field value → non-summary member UIDs, plus the NA group for unassigned tasks.

    ``Resource`` expands per assigned resource (a task can sit in several groups); the NA
    group then holds the tasks with no resource at all.
    """
    out: dict[str, set[int]] = {}
    for t in non_summary(schedule):
        if field == "Resource":
            values: tuple[str, ...] = t.resource_names
        else:
            v = field_value(schedule, t, field)
            values = (v,) if v else ()
        if not values:
            out.setdefault(NA_GROUP, set()).add(t.unique_id)
        for value in values:
            out.setdefault(value, set()).add(t.unique_id)
    return out


def _sei(schedule: Schedule) -> float | None:
    """Start execution index — started ÷ baselined-to-start-by-the-data-date (Normal tasks).

    The start-anchored twin of the cumulative BEI (Acumen's "BEI - Value Task Starts" shape):
    a LEADING indicator that is defined as soon as any work is baselined to start, so a group
    with no completions still gets an execution read. ``None`` when nothing is due to start
    (or no data date) — never fabricated."""
    status = schedule.status_date
    if status is None:
        return None
    normal = [t for t in non_summary(schedule) if not t.is_milestone]
    due = [t for t in normal if t.baseline_start is not None and t.baseline_start <= status]
    if not due:
        return None
    started = sum(1 for t in due if t.actual_start is not None)
    return round(started / len(due), 2)


def compute_field_forecast(schedules: Sequence[Schedule], field: str) -> tuple[GroupMetrics, ...]:
    """Per-(group, version) execution metrics for ``field`` across ``schedules`` (oldest
    first). Groups are the union of values seen in ANY version (a group that disappears in a
    later version still shows, with 0 activities), NA last."""
    all_groups: list[str] = []
    per_version: list[tuple[Schedule, dict[str, set[int]]]] = []
    for sch in schedules:
        groups = _groups(sch, field)
        per_version.append((sch, groups))
        for g in groups:
            if g not in all_groups:
                all_groups.append(g)
    all_groups.sort(key=lambda g: (g == NA_GROUP, g))  # values alphabetical, NA last

    out: list[GroupMetrics] = []
    for group in all_groups:
        for vi, (sch, groups) in enumerate(per_version):
            uids = groups.get(group, set())
            label = sch.source_file or sch.name
            if not uids:
                out.append(
                    GroupMetrics(
                        group=group,
                        version=label,
                        activities=0,
                        completed=0,
                        started=0,
                        to_go=0,
                        bei=None,
                        hmi=None,
                        cei_finish=None,
                        cei_start=None,
                        spi_t=None,
                        spi_t_acumen=None,
                        sei=None,
                        no_completed_work=True,
                    )
                )
                continue
            sub = _sub_schedule(sch, uids)
            tasks = non_summary(sub)
            completed = sum(1 for t in tasks if t.percent_complete >= 100.0)
            started = sum(1 for t in tasks if t.actual_start is not None)
            prior_status: dt.datetime | None = (
                per_version[vi - 1][0].status_date if vi > 0 else None
            )
            evm = compute_evm_indices(sub)
            hmi = compute_hmi(sub, prior_status)["hmi_tasks"]
            out.append(
                GroupMetrics(
                    group=group,
                    version=label,
                    activities=len(tasks),
                    completed=completed,
                    started=started,
                    to_go=len(tasks) - completed,
                    bei=_value(compute_bei(sub)),
                    hmi=_value(hmi),
                    cei_finish=_value(evm["cei_finish"]),
                    cei_start=_value(evm["cei_start"]),
                    spi_t=_value(evm["spi_t"]),
                    spi_t_acumen=_value(evm["spi_t_acumen"]),
                    sei=_sei(sub),
                    no_completed_work=completed == 0,
                )
            )
    return tuple(out)
