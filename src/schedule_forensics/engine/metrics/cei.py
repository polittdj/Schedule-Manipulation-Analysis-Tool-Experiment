"""Current Execution Index (CEI) — Acumen DCMA parity, period-over-period (validated vs Acumen).

Where HMI (:mod:`.hmi`) is **baseline**-anchored ("of the activities the BASELINE placed in this
period, how many hit?"), CEI is **forecast**-anchored: of the activities the *previous* schedule
**forecast** to finish in this period, how many actually finished by the current data date. It is
the DCMA "Current Execution Index" — a read on whether the team executes the plan it most recently
committed to, so it needs **two** consecutive snapshots (the prior forecast + the current actuals)
and is N/A for a single schedule (which is exactly what Acumen reports).

Definition (matched bit-for-bit against the operator's Acumen two-period comparison, "CEI - Value
Tasks"/"CEI - Value Milestones"), period ``(prev_now, now]`` with ``prev_now`` = the prior
snapshot's data date and ``now`` = the current one::

    denominator = activities the PRIOR schedule scheduled to finish in the period and not yet
                  complete at prev_now: prev.finish in (prev_now, now] and incomplete at prev_now
    numerator   = of those, the ones actually complete by now in the CURRENT schedule
                  (actual_finish <= now)
    CEI         = numerator / denominator

Tasks (Normal) and milestones are scored separately, matching Acumen's PrimaryFilter inclusions.
Validated on the operator's Large Test File (v1 2025-02-07 → v2 2025-03-10): CEI Value Tasks
**24 / 129 = 0.19** and CEI Value Milestones **1 / 6 = 0.17**, both EXACT vs Acumen.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def compute_cei(prior: Schedule, current: Schedule) -> dict[str, MetricResult]:
    """CEI for the status period ``(prior.status_date, current.status_date]``.

    Returns ``cei_tasks`` and ``cei_milestones``. Both read NA (count 0 of 0) when the period is
    undefined (missing/non-advancing data dates) or empty (nothing the prior schedule forecast to
    finish in the period) — never a fabricated value. Offenders are the **misses**: activities the
    prior schedule forecast to finish this period that had not completed by ``now`` (citable, §6).
    """
    prev_now, now = prior.status_date, current.status_date
    current_by = {t.unique_id: t for t in current.tasks}
    prior_activities = non_summary(prior)
    normal = [t for t in prior_activities if not t.is_milestone]
    milestones = [t for t in prior_activities if t.is_milestone]
    # the critical cut filters the Normal population to activities the CURRENT schedule marks
    # critical (Acumen reads the MS-Project Critical flag); identity is by UniqueID.
    critical = [
        t
        for t in normal
        if (cur := current_by.get(t.unique_id)) is not None and cur.stored_is_critical
    ]
    return {
        "cei_tasks": _cei("cei_tasks", "CEI (Tasks)", normal, current_by, prev_now, now),
        "cei_milestones": _cei(
            "cei_milestones", "CEI (Milestones)", milestones, current_by, prev_now, now
        ),
        # variants, all validated EXACT vs Acumen (ADR-0101):
        "cei_task_starts": _cei_starts(
            "cei_task_starts", "CEI (Task Starts)", normal, current_by, prev_now, now
        ),
        "cei_critical": _cei("cei_critical", "Critical CEI", critical, current_by, prev_now, now),
        "cei_tasks_adjusted": _cei_adjusted(
            "cei_tasks_adjusted", "CEI (Tasks, adjusted)", normal, current_by, prev_now, now
        ),
    }


def _started(task: Task | None) -> bool:
    """The current-schedule activity has actually started (carries an actual start)."""
    return task is not None and task.actual_start is not None


def _is_complete(task: Task | None) -> bool:
    """The current-schedule activity is 100% complete (Acumen's CEI numerator predicate)."""
    return task is not None and task.percent_complete >= 100.0


def _cei_starts(
    metric_id: str,
    name: str,
    prior_population: list[Task],
    current_by: dict[int, Task],
    prev_now: dt.datetime | None,
    now: dt.datetime | None,
) -> MetricResult:
    """CEI start cut: of the activities the prior schedule forecast to START this period, how many
    have actually started. ``count(ActualStart>0) / count(PreviousStart in (prev_now, now])``."""
    na = MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    if prev_now is None or now is None or now <= prev_now:
        return na
    forecast = [t for t in prior_population if t.start is not None and prev_now < t.start <= now]
    if not forecast:
        return na
    started = sum(1 for t in forecast if _started(current_by.get(t.unique_id)))
    misses = tuple(
        sorted(t.unique_id for t in forecast if not _started(current_by.get(t.unique_id)))
    )
    return MetricResult(
        metric_id,
        name,
        started,
        len(forecast),
        round(started / len(forecast), 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=misses,
    )


def _cei_adjusted(
    metric_id: str,
    name: str,
    prior_population: list[Task],
    current_by: dict[int, Task],
    prev_now: dt.datetime | None,
    now: dt.datetime | None,
) -> MetricResult:
    """CEI finish cut with early-completion credit: the denominator is the in-period forecast set,
    but the numerator counts EVERY now-complete activity the prior schedule forecast to finish from
    ``prev_now`` onward (in-window OR future) — so finishing ahead of the forecast is rewarded."""
    na = MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    if prev_now is None or now is None or now <= prev_now:
        return na
    denom = [t for t in prior_population if t.finish is not None and prev_now < t.finish <= now]
    if not denom:
        return na
    done = sum(
        1
        for t in prior_population
        if t.finish is not None
        and t.finish > prev_now
        and _is_complete(current_by.get(t.unique_id))
    )
    return MetricResult(
        metric_id,
        name,
        done,
        len(denom),
        round(done / len(denom), 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
    )


def _completed_by(task: Task | None, when: dt.datetime) -> bool:
    """The current-schedule activity finished on/before ``when`` (carries an actual finish)."""
    return task is not None and task.actual_finish is not None and task.actual_finish <= when


def _cei(
    metric_id: str,
    name: str,
    prior_population: list[Task],
    current_by: dict[int, Task],
    prev_now: dt.datetime | None,
    now: dt.datetime | None,
) -> MetricResult:
    na = MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    if prev_now is None or now is None or now <= prev_now:
        return na
    # the prior schedule forecast these to finish this period and they were not complete at prev_now
    forecast = [
        t
        for t in prior_population
        if t.finish is not None
        and prev_now < t.finish <= now
        and (t.actual_finish is None or t.actual_finish > prev_now)
    ]
    if not forecast:
        return na
    done = [t for t in forecast if _completed_by(current_by.get(t.unique_id), now)]
    misses = tuple(
        sorted(t.unique_id for t in forecast if not _completed_by(current_by.get(t.unique_id), now))
    )
    return MetricResult(
        metric_id,
        name,
        len(done),
        len(forecast),
        round(len(done) / len(forecast), 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=misses,
    )
