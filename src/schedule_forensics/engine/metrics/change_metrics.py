"""Schedule-Network / Change metrics — version-to-version, by UniqueID (Acumen §E, M8).

Acumen's "PP & Change — Schedule Quality" panel compares the current snapshot to the
**previous** snapshot in the workbook (`docs/PLAN/PARITY-TARGETS.md §E`). The first
snapshot has no prior, so every change count is 0 except *Activities Added* (all are
new). Matching is by **UniqueID only** (§6.B) — never row ID, never name.

Validated against the golden Project2 (prior) → Project5 (current) comparison:

* **Exact:** *Activities Added* (0 — identical UID set), *New Critical* (0),
  **Finish Date Slips (9)** = activities the prior plan placed on/before the new data
  date that are still incomplete, *Completed* (20 → 27), *In-Progress* (3 → 2), and the
  forensic **Net Finish Impact (-99 days)** (:func:`compute_net_finish_impact`).
* **Documented residuals (ADR-0013, → M9):** *No Longer Critical* (0 vs 1), *Start Date
  Slips* (9 vs 10), *Remaining Duration Increases* (7 vs 8), *Float Erosion* (4 vs 6).
  One root cause: Acumen reads MS Project's *progress-aware* total slack / Critical flag,
  whereas this engine recomputes pure-logic CPM float for independence and auditability
  (ADR-0010). The float-independent counts above are exact; the float-dependent and
  per-snapshot-granularity counts differ by a few activities and are driven toward zero
  at M9. Population is the schedulable (non-summary) activities — the same denominator as
  every other framework here; Acumen's §E header counts all 144 task rows (incl. WBS
  summaries), this engine's 126 schedulable activities.
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import CPMResult, compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    non_summary,
)
from schedule_forensics.model.schedule import Schedule


def _count_metric(
    metric_id: str, name: str, uids: tuple[int, ...], population: int
) -> MetricResult:
    """A citable count metric (no pass/fail threshold) over the activity population."""
    return MetricResult(
        metric_id,
        name,
        len(uids),
        population,
        float(len(uids)),
        "count",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=uids,
    )


def _critical_incomplete(schedule: Schedule, cpm_result: CPMResult) -> set[int]:
    """Acumen "Critical" basis: on the critical path (CPM total float ≤ 0) and not done."""
    by_id = schedule.tasks_by_id
    return {
        uid
        for uid, timing in cpm_result.timings.items()
        if timing.is_critical and by_id[uid].percent_complete < 100.0
    }


def compute_change_metrics(
    current: Schedule,
    prior: Schedule | None = None,
    *,
    current_cpm: CPMResult | None = None,
    prior_cpm: CPMResult | None = None,
) -> dict[str, MetricResult]:
    """Acumen §E Schedule-Network change metrics for ``current`` vs its ``prior`` snapshot.

    ``prior`` is the earlier version (lower status date); pass ``None`` for the first
    snapshot in a series. CPM results may be supplied to avoid recomputation.
    """
    cur_tasks = non_summary(current)
    cur_by_id = {t.unique_id: t for t in cur_tasks}
    n = len(cur_tasks)
    status = current.status_date
    cpm_cur = current_cpm if current_cpm is not None else compute_cpm(current)

    completed = tuple(sorted(u for u, t in cur_by_id.items() if t.percent_complete >= 100.0))
    in_progress = tuple(sorted(u for u, t in cur_by_id.items() if 0.0 < t.percent_complete < 100.0))

    out: dict[str, MetricResult] = {}
    out["total_activities"] = _count_metric("SN01", "Total Activities", tuple(sorted(cur_by_id)), n)

    if prior is None:
        # First snapshot: everything is "added"; no prior to diff against.
        out["activities_added"] = _count_metric(
            "SN02", "Activities Added", tuple(sorted(cur_by_id)), n
        )
        for mid, nm in (
            ("SN03", "New Critical"),
            ("SN04", "No Longer Critical"),
            ("SN05", "Finish Date Slips"),
            ("SN06", "Start Date Slips"),
            ("SN07", "Remaining Duration Increases"),
            ("SN09", "Float Erosion"),
        ):
            key = {
                "SN03": "new_critical",
                "SN04": "no_longer_critical",
                "SN05": "finish_date_slips",
                "SN06": "start_date_slips",
                "SN07": "remaining_duration_increases",
                "SN09": "float_erosion",
            }[mid]
            out[key] = _count_metric(mid, nm, (), n)
        out["completed"] = _count_metric("SN18", "Completed", completed, n)
        out["in_progress"] = _count_metric("SN19", "In-Progress", in_progress, n)
        return out

    prior_tasks = non_summary(prior)
    prior_by_id = {t.unique_id: t for t in prior_tasks}
    cpm_prior = prior_cpm if prior_cpm is not None else compute_cpm(prior)
    common = set(cur_by_id) & set(prior_by_id)

    added = tuple(sorted(set(cur_by_id) - set(prior_by_id)))
    out["activities_added"] = _count_metric("SN02", "Activities Added", added, n)

    cci_cur = _critical_incomplete(current, cpm_cur)
    cci_prior = _critical_incomplete(prior, cpm_prior)
    new_crit = tuple(sorted(u for u in (cci_cur & common) if u not in cci_prior))
    no_longer = tuple(
        sorted(
            u
            for u in (cci_prior & common)
            if u not in cci_cur and cur_by_id[u].percent_complete < 100.0
        )
    )
    out["new_critical"] = _count_metric("SN03", "New Critical", new_crit, n)
    out["no_longer_critical"] = _count_metric("SN04", "No Longer Critical", no_longer, n)

    # Finish/Start slips: activities the *prior* plan placed on/before the new data date
    # that have not (respectively) completed / started in the current snapshot.
    fin_slips = tuple(
        sorted(
            u
            for u in common
            if status is not None
            and prior_by_id[u].finish is not None
            and prior_by_id[u].finish <= status  # type: ignore[operator]
            and cur_by_id[u].percent_complete < 100.0
        )
    )
    start_slips = tuple(
        sorted(
            u
            for u in common
            if status is not None
            and prior_by_id[u].start is not None
            and prior_by_id[u].start <= status  # type: ignore[operator]
            and cur_by_id[u].actual_start is None
        )
    )
    out["finish_date_slips"] = _count_metric("SN05", "Finish Date Slips", fin_slips, n)
    out["start_date_slips"] = _count_metric("SN06", "Start Date Slips", start_slips, n)

    rem_dur_inc = tuple(
        sorted(u for u in common if cur_by_id[u].duration_minutes > prior_by_id[u].duration_minutes)
    )
    out["remaining_duration_increases"] = _count_metric(
        "SN07", "Remaining Duration Increases", rem_dur_inc, n
    )

    erosion = tuple(
        sorted(
            u
            for u in common
            if u in cpm_cur.timings
            and u in cpm_prior.timings
            and cpm_cur.timings[u].total_float < cpm_prior.timings[u].total_float
            and cur_by_id[u].percent_complete < 100.0
        )
    )
    out["float_erosion"] = _count_metric("SN09", "Float Erosion", erosion, n)

    out["completed"] = _count_metric("SN18", "Completed", completed, n)
    out["in_progress"] = _count_metric("SN19", "In-Progress", in_progress, n)
    return out


def compute_net_finish_impact(
    current: Schedule,
    prior: Schedule | None = None,
    *,
    current_cpm: CPMResult | None = None,
    prior_cpm: CPMResult | None = None,
) -> MetricResult:
    """HSD Net Finish Impact (days): how far the project finish moved since the prior snapshot.

    The CPM project finish of each version is mapped to a wall-clock date; the metric is
    ``(prior finish date - current finish date)`` in **calendar days**. A negative value
    means the finish slipped later (the headline forensic signal). The first snapshot has
    no prior, so the impact is 0. Validated: Project2 → Project5 = **-99 days**.
    """
    if prior is None:
        return MetricResult(
            "HSD10", "Net Finish Impact", 0, 0, 0.0, "days", CheckStatus.NOT_APPLICABLE
        )
    cpm_cur = current_cpm if current_cpm is not None else compute_cpm(current)
    cpm_prior = prior_cpm if prior_cpm is not None else compute_cpm(prior)
    cur_date = offset_to_datetime(current.project_start, cpm_cur.project_finish, current.calendar)
    prior_date = offset_to_datetime(prior.project_start, cpm_prior.project_finish, prior.calendar)
    days = (prior_date.date() - cur_date.date()).days
    return MetricResult(
        "HSD10", "Net Finish Impact", days, 0, float(days), "days", CheckStatus.NOT_APPLICABLE
    )
