"""Hit or Miss Index (HMI) — period-over-period baseline execution (formula-audit, ADR-0087).

Unlike BEI/MEI (cumulative, single-snapshot indices), the Acumen Bible's **HMI** measures
performance *within the current status period* — the interval between the previous data date
(``ProjectPreviousTimeNow``) and the current one (``ProjectTimeNow``). A **hit** is an activity the
baseline placed to finish in this period that actually completed in this period; a **miss** is one
baselined to finish this period that did not. It therefore needs *two* consecutive snapshots, so it
is computed across loaded versions (see
:func:`schedule_forensics.engine.trend.compute_hmi_trend`), not from a single schedule.

Bible formula (``HMI - Value Tasks`` / ``HMI - Value Milestones``)::

    SUM(IF(PercentComplete=100%, IF(Finish>PrevTimeNow,
            IF(BaselineFinish<=TimeNow, IF(BaselineFinish>PrevTimeNow, 1)))))
    / SUM(IF(BaselineFinish<=TimeNow, IF(BaselineFinish>PrevTimeNow, 1)))

Tasks (Normal activities) and milestones are scored separately, matching the Bible's PrimaryFilter
inclusions (``HMI - Value Tasks`` = Normal only; ``HMI - Value Milestones`` = milestones only).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    non_summary,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def compute_hmi(
    current: Schedule, previous_time_now: dt.datetime | None
) -> dict[str, MetricResult]:
    """HMI for the current status period ``(previous_time_now, current.status_date]``.

    Returns ``hmi_tasks`` and ``hmi_milestones``. Both read NA (count 0 of 0) when the period is
    undefined (no current/previous data date, or non-advancing) or empty (nothing baselined to
    finish in the period) — never a fabricated value. Offenders are the **misses** — activities
    baselined to finish this period that did not complete in it (citable, §6).
    """
    now = current.status_date
    activities = non_summary(current)
    normal = [t for t in activities if not t.is_milestone]
    milestones = [t for t in activities if t.is_milestone]
    return {
        "hmi_tasks": _hmi("hmi_tasks", "HMI (Tasks)", normal, now, previous_time_now),
        "hmi_milestones": _hmi(
            "hmi_milestones", "HMI (Milestones)", milestones, now, previous_time_now
        ),
    }


def _is_hit(t: Task, previous_time_now: dt.datetime) -> bool:
    """A hit: complete, and its finish landed *in this period* (after the previous data date).

    ``PercentComplete=100%`` ⇒ the activity carries an actual finish, which is the Bible's
    ``Finish`` for a complete activity; ``Finish>PrevTimeNow`` keeps the credit in the period the
    work landed in (an activity finished in an earlier period was a hit *there*, not here)."""
    return (
        t.percent_complete >= 100.0
        and t.actual_finish is not None
        and t.actual_finish > previous_time_now
    )


def _hmi(
    metric_id: str,
    name: str,
    population: list[Task],
    now: dt.datetime | None,
    previous_time_now: dt.datetime | None,
) -> MetricResult:
    na = MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    if now is None or previous_time_now is None or now <= previous_time_now:
        return na
    # baselined to finish in this period: PrevTimeNow < BaselineFinish <= TimeNow
    due = [
        t
        for t in population
        if t.baseline_finish is not None and previous_time_now < t.baseline_finish <= now
    ]
    if not due:
        return na
    hits = [t for t in due if _is_hit(t, previous_time_now)]
    misses = tuple(sorted(t.unique_id for t in due if not _is_hit(t, previous_time_now)))
    return MetricResult(
        metric_id,
        name,
        len(hits),
        len(due),
        round(len(hits) / len(due), 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=misses,
    )
