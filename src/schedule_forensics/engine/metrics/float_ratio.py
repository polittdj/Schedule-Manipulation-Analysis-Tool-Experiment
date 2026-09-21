"""Float Ratio™ — activity total float per day of remaining work, on Acumen Fuse's own FIELDS.

The Deltek Acumen Fuse "Float Ratio™" metric, taken verbatim from the NASA Acumen metric library
(the "Bible"). It answers *how much breathing room does the remaining work have, relative to how
much work is left* — a higher ratio means more float per day of remaining duration (a looser,
lower-risk schedule); a ratio near zero means the work is running out of room.

**One name, two metrics.** The ``.aft`` carries ``Float Ratio™`` under BOTH of the Bible's
algebraic forms, and Fuse v8.11.0 prints both under that one tile name depending on which metric
group the workbook loaded. This module computes both, and each is pinned to the ribbon that
displays it (R-78, ADR-0519 — ``tests/parity/test_fuse_duration_fields_oracle.py``):

* ``float_ratio`` — the *mean of the per-activity ratios*, the threshold-bearing form::

      Float Ratio = AVERAGE(TotalFloat / RemainingDuration)

  the AlltheProjects ribbon's tile: nine numeric tiles reproduce to 4 dp (Hard_File_updated3
  -10.9446 → -10.94, Project2 14.0076 → 14.01, Project5_TAMPERED 22.0173 → 22.02, Jacked Up
  Schedule 1 0.7678 → 0.77, Jacked up Schedule 2 0.2667 → 0.27) and ten N/A tiles reproduce
  exactly.

* ``float_ratio_aggregate`` — the *ratio of the means* (equivalently ``sum(TotalFloat) /
  sum(RemainingDuration)`` over one population)::

      Float Ratio (aggregate) = AVERAGE(TotalFloat) / AVERAGE(RemainingDuration)

  the 7/15 Analyst ribbon's tile (-8.0115 → -8.01 on the same rev-5 Hard_File_updated3 save the
  other ribbon reads -10.94, and -3.5758 → -3.58 on the 24-hour file) and the
  update2-vs-update3 ribbon's (5.7361 → 5.74 on Hard_File_updated2).

**Both terms are Fuse's whole-day FIELDS, not raw minutes** (R-75 / ADR-0516, R-76 / ADR-0518):
:func:`acumen_total_float_field` and :func:`acumen_duration_field`, each on the activity's OWN day
(:func:`activity_day_minutes` — 1440 for an elapsed duration, else the task's own calendar's day,
else the project's). That is what the analyst reads in the reference tool's grid, and averaging
the underlying minutes instead put the engine at -11.85 where Fuse printed -10.94.

**N/A is a divide-by-zero, not a finding.** A Remaining Duration field of 0 (a 480-minute
remainder on a 1,440-minute calendar rounds to 0 whole days) makes one per-activity ratio an
error, and Excel's ``AVERAGE`` propagates it: the mean-of-ratios tile prints **N/A** for the whole
project. The engine reports that as :data:`CheckStatus.NOT_APPLICABLE` with a **zero population** —
the only "this carried no figure" signal its consumers have, because the status pill is already
spent saying "informational, no threshold" (``web/standards.py`` renders a 0-population ratio as
an em dash; ``engine/trend.py`` emits ``None`` for that version rather than a fabricated 0.0).
The candidate activity count is deliberately NOT reported on an N/A: there is no field left to
carry it that a consumer would not read as a figure. The aggregate form has no per-activity
division to fail, so it keeps every activity — zero-remaining ones included — in BOTH sums and
stays computable; on the 24-hour file that is the tile's -3.58, where dropping them would print
-9.58. It is therefore the figure that survives when the primary reads N/A.

Population (the Bible's ``PrimaryFilter``): **Normal** activities (non-summary, non-milestone,
non-hammock) that are **Planned or In-Progress** — completed work is excluded (it has no remaining
duration and carries no forward risk). Total float is read from the source tool's stored,
progress-aware value when present (matching Acumen — :func:`effective_total_float`), otherwise the
engine's recomputed CPM float; an activity with neither cannot contribute and is skipped.

**The tile's two displayed decimals round half AWAY FROM ZERO.** ADR-0515 left every ``value_dp``
rounding on Python's half-to-even because no reference display was known at that precision; for
this metric there is one, and it has exactly one tie in the whole reference corpus — TP4_DataCenter
v1's mean is exactly 5/8 and Fuse writes **0.63** into the ribbon (half-to-even writes 0.62). So
both forms present through :func:`round_half_up` (MF-08, ADR-0467). Every other label in every
committed ribbon is a non-tie and reads identically under either rule. A NEGATIVE tie does not
occur in the corpus, so away-from-zero rather than toward positive infinity is the spreadsheet
convention applied, not a measurement (UNVERIFIED).

Bible interpretation bands (informational — Float Ratio is not a DCMA pass/fail check): ``< 0.1``
very tight, ``0.1-0.3`` tight, ``0.3-0.6`` healthy, ``> 0.6`` generous (check for missing logic).
The offenders cited are the activities in the very-tight band (ratio ``< 0.1``).
"""

from __future__ import annotations

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    activity_day_minutes,
    acumen_duration_field,
    acumen_total_float_field,
    effective_total_float,
    non_summary,
    round_half_up,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The Bible's lowest ("Low") band edge — activities below this are very tight (cited as offenders).
_LOW_BAND = 0.1


def _float_ratio_population(schedule: Schedule) -> list[Task]:
    """Normal, planned-or-in-progress activities (the Bible's Float Ratio filter).

    Non-summary, non-milestone, non-level-of-effort (hammock), and **incomplete** — completed
    work is excluded (it has no remaining duration and poses no forward risk)."""
    return [
        t
        for t in non_summary(schedule)
        if not t.is_milestone and not t.is_level_of_effort and not t.is_complete
    ]


def _remaining_minutes(task: Task) -> int:
    """Remaining duration in working minutes — the stored value, else duration scaled by % left."""
    if task.remaining_duration_minutes is not None:
        return task.remaining_duration_minutes
    return round(task.duration_minutes * (100.0 - task.percent_complete) / 100.0)


def _scored(schedule: Schedule, result: CPMResult) -> list[tuple[Task, float, int]]:
    """``(task, total_float_field, remaining_duration_field)`` for each scorable activity.

    Both terms are the WHOLE-DAY fields Fuse displays, on the activity's own day. A zero
    remaining field is **kept** — it is what makes the mean-of-ratios form N/A and what the
    ratio-of-means form carries in its denominator sum, so the caller decides, not this loop.
    Only an activity with no available float at all (no stored value and absent from the CPM
    result) is dropped: it cannot contribute either figure."""
    by_uid = {c.uid: c for c in schedule.calendars}
    out: list[tuple[Task, float, int]] = []
    for t in _float_ratio_population(schedule):
        if t.stored_total_float_minutes is None and t.unique_id not in result.timings:
            continue
        recomputed = (
            float(result.timings[t.unique_id].total_float) if t.unique_id in result.timings else 0.0
        )
        day = activity_day_minutes(schedule, t, by_uid)
        out.append(
            (
                t,
                acumen_total_float_field(t, effective_total_float(t, recomputed), day),
                acumen_duration_field(_remaining_minutes(t), day),
            )
        )
    return out


def _na(metric_id: str, name: str) -> MetricResult:
    return MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)


def compute_float_ratio(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Float Ratio™ over the normal planned/in-progress population — both Bible forms.

    Returns ``float_ratio`` (the mean-of-ratios, the AlltheProjects ribbon's tile) and
    ``float_ratio_aggregate`` (the ratio-of-means, the Analyst ribbon's). Both are
    single-snapshot and informational (no pass/fail threshold), so both carry an NA *status* even
    when they carry a figure; ``population`` is the activity count scored, and a population of 0
    is the "no figure" signal — the primary reads it whenever any Remaining Duration field is 0
    (Fuse's own N/A), the aggregate only when every one of them is. ``offender_uids`` on the
    primary are the very-tight activities (per-activity ratio ``< 0.1``)."""
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    scored = _scored(schedule, result)
    count = len(scored)
    if count == 0:
        return {
            "float_ratio": _na("float_ratio", "Float Ratio"),
            "float_ratio_aggregate": _na("float_ratio_aggregate", "Float Ratio (aggregate)"),
        }
    total_remaining = sum(rd for _, _, rd in scored)
    if total_remaining:
        aggregate = MetricResult(
            "float_ratio_aggregate",
            "Float Ratio (aggregate)",
            count,
            count,
            round_half_up(sum(tf for _, tf, _ in scored) / total_remaining, 2),
            "ratio",
            CheckStatus.NOT_APPLICABLE,
        )
    else:
        aggregate = _na("float_ratio_aggregate", "Float Ratio (aggregate)")
    if any(rd == 0 for _, _, rd in scored):
        return {
            "float_ratio": _na("float_ratio", "Float Ratio"),
            "float_ratio_aggregate": aggregate,
        }
    mean_of_ratios = sum(tf / rd for _, tf, rd in scored) / count
    tight = tuple(sorted(t.unique_id for t, tf, rd in scored if tf / rd < _LOW_BAND))
    return {
        "float_ratio": MetricResult(
            "float_ratio",
            "Float Ratio",
            count,
            count,
            round_half_up(mean_of_ratios, 2),
            "ratio",
            CheckStatus.NOT_APPLICABLE,
            offender_uids=tight,
        ),
        "float_ratio_aggregate": aggregate,
    }
