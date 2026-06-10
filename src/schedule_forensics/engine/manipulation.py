"""Schedule-manipulation trend detection — cited forensic signals across versions (§6.D, M11).

Reads the UniqueID-keyed :func:`~schedule_forensics.engine.diff.diff_versions` plus the
prior CPM to flag the classic manipulation patterns a forensic scheduler looks for between
two snapshots — each as a cited :class:`~schedule_forensics.engine.recommendations.Finding`
(file + UID + task, never uncited):

* **deleted tasks** that were on the prior critical/driving path (work removed to keep the
  finish from slipping);
* **deleted logic** (relationships removed — breaking ties that would otherwise push dates);
* **shortened durations** on still-incomplete activities (compressing to hold a date);
* **baseline-date changes** (DECM 29I401a — re-baselining to absorb/mask variance);
* **actual-date edits** (DECM 06A504a/b — a previously reported actual start/finish changed
  in the next snapshot).

A statement is only ever made with the underlying delta attached. :func:`trend_across_versions`
adds the multi-snapshot (≤10) CPM/finish/completion trend that feeds the §6.D story and the
dashboard charts.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.engine.diff import VersionDiff, diff_versions
from schedule_forensics.engine.recommendations import Category, Finding, Severity
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _cite(file: str | None, task: Task) -> Citation:
    return Citation(source_file=file, unique_id=task.unique_id, task_name=task.name)


def _critical_incomplete(schedule: Schedule, cpm: CPMResult) -> set[int]:
    by_id = schedule.tasks_by_id
    return {
        uid
        for uid, t in cpm.timings.items()
        if t.is_critical and by_id[uid].percent_complete < 100.0
    }


def detect_manipulation(
    current: Schedule,
    prior: Schedule,
    *,
    current_cpm: CPMResult | None = None,
    prior_cpm: CPMResult | None = None,
) -> tuple[Finding, ...]:
    """Flag schedule-manipulation signals from ``prior`` → ``current`` (cited, severity-ordered)."""
    diff = diff_versions(prior, current)
    cpm_prior = prior_cpm if prior_cpm is not None else compute_cpm(prior)
    prior_critical = _critical_incomplete(prior, cpm_prior)
    prior_by_id = {t.unique_id: t for t in prior.tasks}
    cur_by_id = {t.unique_id: t for t in current.tasks}
    findings: list[Finding] = []

    findings.extend(_deleted_tasks(diff, prior_by_id, prior_critical, prior.source_file))
    findings.extend(_deleted_logic(diff, prior_by_id, prior.source_file))
    findings.extend(_shortened_durations(diff, prior_by_id, cur_by_id, current.source_file))
    findings.extend(_baseline_date_changes(diff, cur_by_id, current.source_file))
    findings.extend(_actual_date_changes(diff, cur_by_id, current.source_file))

    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
    findings.sort(key=lambda f: (order[f.severity], f.metric_id))
    return tuple(findings)


def _deleted_tasks(
    diff: VersionDiff,
    prior_by_id: dict[int, Task],
    prior_critical: set[int],
    prior_file: str | None,
) -> list[Finding]:
    if not diff.deleted_tasks:
        return []
    on_path = tuple(u for u in diff.deleted_tasks if u in prior_critical)
    citations = tuple(_cite(prior_file, prior_by_id[u]) for u in diff.deleted_tasks)
    severity = Severity.HIGH if on_path else Severity.MEDIUM
    detail = f"{len(diff.deleted_tasks)} activities present in the prior version were removed"
    if on_path:
        detail += f"; {len(on_path)} were on the prior critical path (UIDs {list(on_path)})"
    return [
        Finding(
            category=Category.CONCERN,
            severity=severity,
            metric_id="MANIP_DELETED_TASK",
            title=f"{len(diff.deleted_tasks)} activities deleted since the prior version",
            detail=detail + ".",
            course_of_action="Confirm each deletion is authorized scope removal, not work "
            "removed to keep the critical path or a target date from slipping.",
            citations=citations,
        )
    ]


def _deleted_logic(
    diff: VersionDiff, prior_by_id: dict[int, Task], prior_file: str | None
) -> list[Finding]:
    if not diff.removed_links:
        return []
    # cite the successor end of each removed link (the activity that lost a driver)
    seen: dict[int, Citation] = {}
    for pred, succ, _type, _lag in diff.removed_links:
        task = prior_by_id.get(succ) or prior_by_id.get(pred)
        if task is not None and task.unique_id not in seen:
            seen[task.unique_id] = _cite(prior_file, task)
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="MANIP_DELETED_LOGIC",
            title=f"{len(diff.removed_links)} logic links removed since the prior version",
            detail=f"{len(diff.removed_links)} relationships present in the prior version are "
            "gone — removing logic can stop a delay from propagating to successors.",
            course_of_action="Verify each removed relationship was genuinely incorrect, not "
            "deleted to break a chain that would otherwise push the finish.",
            citations=tuple(seen.values()),
        )
    ]


def _shortened_durations(
    diff: VersionDiff,
    prior_by_id: dict[int, Task],
    cur_by_id: dict[int, Task],
    current_file: str | None,
) -> list[Finding]:
    offenders: list[Citation] = []
    for td in diff.changed_tasks:
        if td.changed("duration_minutes") is None:
            continue
        cur = cur_by_id[td.unique_id]
        prior = prior_by_id[td.unique_id]
        if cur.duration_minutes < prior.duration_minutes and cur.percent_complete < 100.0:
            offenders.append(_cite(current_file, cur))
    if not offenders:
        return []
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="MANIP_SHORTENED_DURATION",
            title=f"{len(offenders)} incomplete activities had their duration shortened",
            detail="Remaining duration was reduced on still-incomplete work — a common way to "
            "absorb a slip without moving the finish date.",
            course_of_action="Confirm the shorter durations reflect a real plan change with "
            "basis, not compression to mask a slip.",
            citations=tuple(offenders),
        )
    ]


def _baseline_date_changes(
    diff: VersionDiff, cur_by_id: dict[int, Task], current_file: str | None
) -> list[Finding]:
    offenders = tuple(
        _cite(current_file, cur_by_id[td.unique_id])
        for td in diff.changed_tasks
        if td.changed("baseline_start") is not None or td.changed("baseline_finish") is not None
    )
    if not offenders:
        return []
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.HIGH,
            metric_id="MANIP_BASELINE_CHANGE",
            title=f"{len(offenders)} activities had baseline dates changed (DECM 29I401a)",
            detail="Baseline start/finish dates moved between snapshots — re-baselining can "
            "absorb variance so a slip never shows against the baseline.",
            course_of_action="Confirm each baseline change followed an authorized re-baseline, "
            "not an edit to mask schedule variance.",
            citations=offenders,
        )
    ]


def _actual_date_changes(
    diff: VersionDiff, cur_by_id: dict[int, Task], current_file: str | None
) -> list[Finding]:
    offenders: list[Citation] = []
    for td in diff.changed_tasks:
        for field in ("actual_start", "actual_finish"):
            delta = td.changed(field)
            # an EDITED actual (was a date, now a different date) is the 06A504* signal;
            # a newly-set actual (None -> date) is normal progress, not manipulation.
            if delta is not None and delta.before is not None and delta.after is not None:
                offenders.append(_cite(current_file, cur_by_id[td.unique_id]))
                break
    if not offenders:
        return []
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.HIGH,
            metric_id="MANIP_ACTUAL_CHANGE",
            title=f"{len(offenders)} activities had a previously-reported actual date changed",
            detail="An actual start/finish reported in the prior snapshot was changed in this "
            "one (DECM 06A504a/b) — recorded history should not move.",
            course_of_action="Investigate why a recorded actual date changed; confirm it was a "
            "correction with basis, not a rewrite of progress history.",
            citations=tuple(offenders),
        )
    ]


@dataclass(frozen=True)
class TrendPoint:
    """One snapshot's headline numbers for the multi-version CPM/progress trend (§6.D)."""

    version_index: int
    source_file: str | None
    status_date: dt.datetime | None
    project_finish: dt.datetime
    completed: int
    in_progress: int
    critical: int


def trend_across_versions(schedules: Sequence[Schedule]) -> tuple[TrendPoint, ...]:
    """Per-version CPM finish + completion/criticality counts across an ordered series (≤10).

    Versions are taken in the order given (chronological by status date is the caller's
    responsibility). Drives the §6.D CPM-trend story and the dashboard trend charts.
    """
    points: list[TrendPoint] = []
    for idx, schedule in enumerate(schedules):
        cpm = compute_cpm(schedule)
        finish = offset_to_datetime(schedule.project_start, cpm.project_finish, schedule.calendar)
        leaves = [t for t in schedule.tasks if not t.is_summary]
        completed = sum(1 for t in leaves if t.percent_complete >= 100.0)
        in_progress = sum(1 for t in leaves if 0.0 < t.percent_complete < 100.0)
        critical = len(_critical_incomplete(schedule, cpm))
        points.append(
            TrendPoint(
                version_index=idx,
                source_file=schedule.source_file,
                status_date=schedule.status_date,
                project_finish=finish,
                completed=completed,
                in_progress=in_progress,
                critical=critical,
            )
        )
    return tuple(points)
