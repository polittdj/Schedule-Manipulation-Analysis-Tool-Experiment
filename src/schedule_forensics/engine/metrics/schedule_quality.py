"""Acumen "Schedule Quality" summary metrics (`PARITY-TARGETS.md §A`).

A separate framework from the DCMA-14 ribbon (different denominators — keep them
distinct, per the golden doc). Each metric is a :class:`MetricResult`. Validated
counts/percentages against the golden P2/P5 exports:

* Missing Logic 6/6, Logic Density 2.79/2.83 (= 2 x links / activities), Critical
  41/37 (incomplete & total float ≤ 0), Hard Constraints 0/0, Negative Float 0/0,
  Insufficient Detail 1/0 (baseline duration > 44 days), Number of Lags 2/2, Number
  of Leads 0/0, Merge Hotspot 10/10 (≥ 3 predecessors).

The composite Acumen "Score" (88) is a proprietary Bad/Neutral/Good weighting not
published in the exports or the Acumen metric guide; it is not reproduced here and is
tracked as an M9 calibration item (ADR-0012).
"""

from __future__ import annotations

from collections import Counter

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    Direction,
    MetricResult,
    evaluate,
    forty_four_days_min,
    is_incomplete,
    non_summary,
    percent,
)
from schedule_forensics.model.schedule import Schedule

#: Predecessor count at/above which an activity is a "merge hotspot" (validated = 3).
MERGE_HOTSPOT_MIN_PREDECESSORS = 3


def compute_schedule_quality(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Compute the Acumen Schedule-Quality summary metrics, keyed by name."""
    tasks = non_summary(schedule)
    real_ids = {t.unique_id for t in tasks}
    incomplete = [t for t in tasks if is_incomplete(t)]
    n_tasks, n_inc = len(tasks), len(incomplete)

    links = [
        r
        for r in schedule.relationships
        if r.predecessor_id in real_ids and r.successor_id in real_ids
    ]
    n_links = len(links)
    has_pred: set[int] = set()
    has_succ: set[int] = set()
    npred: Counter[int] = Counter()
    for r in links:
        has_succ.add(r.predecessor_id)
        has_pred.add(r.successor_id)
        npred[r.successor_id] += 1

    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    tf = {uid: t.total_float for uid, t in result.timings.items()}

    out: dict[str, MetricResult] = {}

    missing = tuple(
        t.unique_id for t in tasks if t.unique_id not in has_pred or t.unique_id not in has_succ
    )
    out["missing_logic"] = _pct_result(
        "missing_logic", "Missing Logic", len(missing), n_tasks, 5.0, Direction.LE, missing
    )

    density = round(2 * n_links / n_tasks, 2) if n_tasks else 0.0
    out["logic_density"] = MetricResult(
        "logic_density",
        "Logic Density",
        n_links,
        n_tasks,
        density,
        "ratio",
        CheckStatus.NOT_APPLICABLE,
    )

    crit = tuple(t.unique_id for t in incomplete if tf.get(t.unique_id, 0) <= 0)
    out["critical"] = MetricResult(
        "critical",
        "Critical",
        len(crit),
        n_inc,
        round(percent(len(crit), n_inc), 0),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=crit,
    )

    hard = tuple(t.unique_id for t in tasks if t.has_hard_constraint)
    out["hard_constraints"] = MetricResult(
        "hard_constraints",
        "Hard Constraints",
        len(hard),
        n_tasks,
        percent(len(hard), n_tasks),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=hard,
    )

    neg = tuple(t.unique_id for t in incomplete if tf.get(t.unique_id, 0) < 0)
    out["negative_float"] = MetricResult(
        "negative_float",
        "Negative Float",
        len(neg),
        n_inc,
        percent(len(neg), n_inc),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=neg,
    )

    insuff = tuple(
        t.unique_id
        for t in tasks
        if t.baseline_duration_minutes is not None
        and t.baseline_duration_minutes > forty_four_days_min(schedule)
    )
    out["insufficient_detail"] = _pct_result(
        "insufficient_detail",
        "Insufficient Detail",
        len(insuff),
        n_tasks,
        5.0,
        Direction.LE,
        insuff,
    )

    lags = tuple(r.successor_id for r in links if r.lag_minutes > 0)
    out["number_of_lags"] = _pct_result(
        "number_of_lags", "Number of Lags", len(lags), n_tasks, 5.0, Direction.LE, lags
    )

    leads = tuple(r.successor_id for r in links if r.lag_minutes < 0)
    out["number_of_leads"] = MetricResult(
        "number_of_leads",
        "Number of Leads",
        len(leads),
        n_tasks,
        percent(len(leads), n_tasks),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=leads,
    )

    merge = tuple(uid for uid, c in npred.items() if c >= MERGE_HOTSPOT_MIN_PREDECESSORS)
    out["merge_hotspot"] = MetricResult(
        "merge_hotspot",
        "Merge Hotspot",
        len(merge),
        n_tasks,
        percent(len(merge), n_tasks),
        "%",
        CheckStatus.NOT_APPLICABLE,
        offender_uids=tuple(sorted(merge)),
    )

    return out


def _pct_result(
    metric_id: str,
    name: str,
    count: int,
    population: int,
    threshold: float | None,
    direction: Direction | None,
    offenders: tuple[int, ...],
) -> MetricResult:
    value = percent(count, population)
    return MetricResult(
        metric_id,
        name,
        count,
        population,
        value,
        "%",
        evaluate(value, threshold, direction),
        threshold,
        direction,
        offenders,
    )
