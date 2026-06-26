"""Schedule-manipulation trend detection — cited forensic signals across versions (§6.D, M11).

Reads the UniqueID-keyed :func:`~schedule_forensics.engine.diff.diff_versions` plus the
prior CPM to flag the classic manipulation patterns a forensic scheduler looks for between
two snapshots — each as a cited :class:`~schedule_forensics.engine.recommendations.Finding`
(file + UID + task, never uncited):

* **deleted tasks** that were on the prior critical/driving path (work removed to keep the
  finish from slipping);
* **deleted logic** (relationships removed — breaking ties that would otherwise push dates);
* **shortened durations** on still-incomplete activities (compressing to hold a date);
* **constraint tightening** — a hard date constraint (MSO/MFO/SNLT/FNLT) added to an
  incomplete activity since the prior version (ADR-0130; a hard date can clamp negative
  float so a slip never surfaces as a late finish);
* **calendar loosening** — the project calendar gained working time between snapshots
  (longer work day, an added working weekday, removed holidays, or extra worked-day
  exceptions; ADR-0130 — added working time can absorb a slip without any activity reading
  late);
* **baseline-date changes** (DECM 29I401a — re-baselining to absorb/mask variance);
* **actual-date edits** (DECM 06A504a/b — a previously reported actual start/finish changed
  in the next snapshot).

The constraint/calendar signals are emitted as MEDIUM **review** items (confirm-authorized),
correlated with the slip they could mask where the data allows; they never gate parity.

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
from schedule_forensics.engine.recommendations import (
    SEVERITY_ORDER,
    Category,
    Finding,
    Severity,
)
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
    cpm_current = current_cpm if current_cpm is not None else compute_cpm(current)
    prior_critical = _critical_incomplete(prior, cpm_prior)
    prior_by_id = {t.unique_id: t for t in prior.tasks}
    cur_by_id = {t.unique_id: t for t in current.tasks}
    findings: list[Finding] = []

    findings.extend(_deleted_tasks(diff, prior_by_id, prior_critical, prior.source_file))
    findings.extend(_deleted_logic(diff, prior_by_id, prior.source_file))
    findings.extend(_shortened_durations(diff, prior_by_id, cur_by_id, current.source_file))
    findings.extend(
        _constraint_tightening(diff, prior_by_id, cur_by_id, cpm_current, current.source_file)
    )
    findings.extend(_calendar_loosening(prior, current, current.source_file))
    findings.extend(_baseline_date_changes(diff, cur_by_id, current.source_file))
    findings.extend(_actual_date_changes(diff, cur_by_id, current.source_file))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.metric_id))
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
            detail="Total duration was reduced on still-incomplete work — a common way to "
            "absorb a slip without moving the finish date.",
            course_of_action="Confirm the shorter durations reflect a real plan change with "
            "basis, not compression to mask a slip.",
            citations=tuple(offenders),
        )
    ]


def _constraint_tightening(
    diff: VersionDiff,
    prior_by_id: dict[int, Task],
    cur_by_id: dict[int, Task],
    current_cpm: CPMResult,
    current_file: str | None,
) -> list[Finding]:
    """Incomplete activities where a newly-added HARD date constraint is **clamping** float.

    A hard constraint (MSO/MFO/SNLT/FNLT) can pin a date and clamp negative float so a slip never
    surfaces as a late finish — the constraint-abuse vector (audit F-05). To stay specific (real
    schedules add benign contractual constraints all the time), this fires ONLY when the new hard
    constraint coincides with ≤ 0 total float in the current network — i.e. the constraint is
    actually what is holding the date, the masking signature — not on every constraint edit.
    """
    tf = current_cpm.timings
    offenders: list[Citation] = []
    for td in diff.changed_tasks:
        if td.changed("constraint_type") is None:
            continue
        cur = cur_by_id[td.unique_id]
        prior = prior_by_id[td.unique_id]
        timing = tf.get(cur.unique_id)
        if (
            cur.has_hard_constraint
            and not prior.has_hard_constraint
            and cur.percent_complete < 100.0
            and timing is not None
            and timing.total_float <= 0  # the constraint is binding / clamping the date
        ):
            offenders.append(_cite(current_file, cur))
    if not offenders:
        return []
    detail = (
        f"{len(offenders)} still-incomplete activities gained a hard date constraint "
        "(MSO/MFO/SNLT/FNLT) since the prior version AND now sit at ≤ 0 total float — the new "
        "constraint is what is holding the date, which can clamp negative float so a slip never "
        "shows as a late finish."
    )
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="MANIP_CONSTRAINT_ADDED",
            title=f"{len(offenders)} incomplete activities gained a clamping hard constraint",
            detail=detail,
            course_of_action="Confirm each new hard constraint reflects a real external date "
            "driver, not a constraint added to pin a date and mask negative float / a slip.",
            citations=tuple(offenders),
        )
    ]


def _calendar_loosening(
    prior: Schedule, current: Schedule, current_file: str | None
) -> list[Finding]:
    """The project calendar gained working time between snapshots.

    Adding working time (a longer work day, an extra working weekday, removed holidays, or
    added worked-day exceptions) can absorb a slip so the finish holds without any activity
    reading late — calendar gaming (audit F-05). Project-level signal, cited to the project
    calendar (UID 0). Compares the project default calendar only (the schedule-wide axis).
    """
    pc, cc = prior.calendar, current.calendar
    signals: list[str] = []
    if cc.working_minutes_per_day > pc.working_minutes_per_day:
        signals.append(
            f"work day lengthened {pc.working_minutes_per_day}→{cc.working_minutes_per_day} min"
        )
    added_weekdays = sorted(set(cc.work_weekdays) - set(pc.work_weekdays))
    if added_weekdays:
        signals.append(f"{len(added_weekdays)} working weekday(s) added")
    removed_holidays = set(pc.holidays) - set(cc.holidays)
    if removed_holidays:
        signals.append(f"{len(removed_holidays)} holiday(s) removed")
    added_exceptions = set(cc.working_days) - set(pc.working_days)
    if added_exceptions:
        signals.append(f"{len(added_exceptions)} extra worked-day exception(s) added")
    if not signals:
        return []
    cite = Citation(
        source_file=current_file, unique_id=0, task_name=f"project calendar '{cc.name}'"
    )
    return [
        Finding(
            category=Category.CONCERN,
            severity=Severity.MEDIUM,
            metric_id="MANIP_CALENDAR_LOOSENED",
            title="Project calendar gained working time since the prior version",
            detail="Available working time was increased ("
            + "; ".join(signals)
            + ") — adding working time can absorb a slip so the finish holds without any "
            "activity appearing late.",
            course_of_action="Confirm the calendar change reflects an authorized resourcing "
            "change (e.g. approved overtime), not working time added to mask a slip.",
            citations=(cite,),
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
    edited: list[Citation] = []
    erased: list[Citation] = []
    for td in diff.changed_tasks:
        for field in ("actual_start", "actual_finish"):
            delta = td.changed(field)
            if delta is None or delta.before is None:
                # a newly-set actual (None -> date) is normal progress, not manipulation
                continue
            # an EDITED actual (was a date, now a different date) is the 06A504* signal;
            # an ERASED actual (date -> None) un-statuses recorded progress — the classic
            # history rewrite — and is at least as suspect.
            bucket = edited if delta.after is not None else erased
            bucket.append(_cite(current_file, cur_by_id[td.unique_id]))
            break
    out: list[Finding] = []
    if edited:
        out.append(
            Finding(
                category=Category.CONCERN,
                severity=Severity.HIGH,
                metric_id="MANIP_ACTUAL_CHANGE",
                title=f"{len(edited)} activities had a previously-reported actual date changed",
                detail="An actual start/finish reported in the prior snapshot was changed in "
                "this one (DECM 06A504a/b) — recorded history should not move.",
                course_of_action="Investigate why a recorded actual date changed; confirm it "
                "was a correction with basis, not a rewrite of progress history.",
                citations=tuple(edited),
            )
        )
    if erased:
        out.append(
            Finding(
                category=Category.CONCERN,
                severity=Severity.HIGH,
                metric_id="MANIP_ACTUAL_ERASED",
                title=f"{len(erased)} activities had a previously-reported actual date erased",
                detail="An actual start/finish reported in the prior snapshot is gone in this "
                "one — progress was rolled back, which recorded history should never do.",
                course_of_action="Investigate why recorded progress was un-statused; confirm a "
                "legitimate correction (e.g. a mis-keyed actual), not a slip being hidden by "
                "re-opening completed work.",
                citations=tuple(erased),
            )
        )
    return out


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


def trend_across_versions(
    schedules: Sequence[Schedule], cpms: Sequence[CPMResult] | None = None
) -> tuple[TrendPoint, ...]:
    """Per-version CPM finish + completion/criticality counts across an ordered series (≤10).

    Versions are taken in the order given (chronological by status date is the caller's
    responsibility). ``cpms`` (parallel to ``schedules``) avoids re-solving networks the
    caller already has. Drives the §6.D CPM-trend story and the dashboard trend charts.
    """
    if cpms is not None and len(cpms) != len(schedules):
        raise ValueError("cpms must parallel schedules")
    points: list[TrendPoint] = []
    for idx, schedule in enumerate(schedules):
        cpm = cpms[idx] if cpms is not None else compute_cpm(schedule)
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
