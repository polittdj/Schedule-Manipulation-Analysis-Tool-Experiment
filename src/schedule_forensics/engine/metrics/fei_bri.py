"""FEI and BRI — Forecast Execution Index and Baseline Realism Index (Acumen Bible formulas).

Two single-snapshot SEM indices from the NASA Acumen metric library (the "Bible"), scored over the
Normal value-task population (non-summary, non-milestone), with ``ProjectTimeNow`` = the schedule's
status date:

* **FEI — Forecast Execution Index** (forward-looking, "to-go"): are the remaining activities still
  on plan against the baseline? Two cuts, exactly as the Bible defines them::

      FEI starts  = count(Start >= now) / count(BaselineStart  >= now)
      FEI finish  = count(Finish >= now and not finished early) / count(BaselineFinish >= now)

  > 1 means more work is forecast in the remaining window than the baseline placed there (a to-go
  bow wave); validated vs Acumen on the Large Test File (FEI starts ≈ 2.78, finish ≈ 2.89; the few-
  task residual is the .mpp→MSPDI conversion, not the formula — start numerator 828 EXACT).

* **BRI — Baseline Realism Index** (cumulative, backward-looking): of the activities the baseline
  placed to finish by now, how many actually finished by now::

      BRI = count(BaselineFinish <= now and actually finished <= now) / count(BaselineFinish <= now)

  Validated EXACT vs Acumen (Large Test File: **0.51**, denominator 1228 EXACT). The misses
  (baselined-due, not finished) are the offenders.
"""

from __future__ import annotations

from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult, non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _value_tasks(schedule: Schedule) -> list[Task]:
    """The Acumen 'Value Tasks' population: Normal activities (non-summary, non-milestone)."""
    return [t for t in non_summary(schedule) if not t.is_milestone]


def _ratio(
    metric_id: str, name: str, num: int, den: int, offenders: tuple[int, ...] = ()
) -> MetricResult:
    if den <= 0:
        return MetricResult(metric_id, name, num, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    return MetricResult(
        metric_id,
        name,
        num,
        den,
        round(num / den, 2),
        "ratio",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=offenders,
    )


def compute_fei(schedule: Schedule) -> dict[str, MetricResult]:
    """FEI (Forecast Execution Index) — start and finish cuts over the to-go window.

    ``fei_starts`` / ``fei_finish``. NA when the status date is unknown or nothing is baselined into
    the remaining window. Single-snapshot (needs only this schedule + its baseline + data date)."""
    now = schedule.status_date
    tasks = _value_tasks(schedule)
    if now is None:
        return {
            "fei_starts": MetricResult(
                "fei_starts", "FEI (Starts)", 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE
            ),
            "fei_finish": MetricResult(
                "fei_finish", "FEI (Finish)", 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE
            ),
        }

    start_fc = sum(1 for t in tasks if t.start is not None and t.start >= now)
    start_bl = sum(1 for t in tasks if t.baseline_start is not None and t.baseline_start >= now)
    # finish numerator: forecast to finish in the to-go window AND not already finished early
    finish_fc = sum(
        1
        for t in tasks
        if t.finish is not None
        and t.finish >= now
        and (t.actual_finish is None or t.actual_finish >= now)
    )
    finish_bl = sum(1 for t in tasks if t.baseline_finish is not None and t.baseline_finish >= now)
    return {
        "fei_starts": _ratio("fei_starts", "FEI (Starts)", start_fc, start_bl),
        "fei_finish": _ratio("fei_finish", "FEI (Finish)", finish_fc, finish_bl),
    }


def compute_bri(schedule: Schedule) -> MetricResult:
    """BRI (Baseline Realism Index, cumulative) — baselined-due activities that actually finished.

    NA when the status date is unknown or nothing was baselined to finish by it. Offenders are the
    baselined-due activities that did not finish by the data date (the realism misses)."""
    now = schedule.status_date
    tasks = _value_tasks(schedule)
    if now is None:
        return MetricResult("bri_cumulative", "BRI", 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)
    due = [t for t in tasks if t.baseline_finish is not None and t.baseline_finish <= now]
    done_ids = {t.unique_id for t in due if t.actual_finish is not None and t.actual_finish <= now}
    misses = tuple(sorted(t.unique_id for t in due if t.unique_id not in done_ids))
    return _ratio("bri_cumulative", "BRI", len(done_ids), len(due), misses)
