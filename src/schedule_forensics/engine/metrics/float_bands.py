"""Float-band metrics — how much of the to-go work is running out of room (M15).

The reference Power BI deck's "Float Analysis" page banded the incomplete work by
remaining float: activities at **0 days** of float (no room at all), under **5 days**,
and under **10 days**, for both **total** and **free** float, as counts and shares —
trended across versions, the swelling of the low-float bands is the early-warning that
a schedule is losing its ability to absorb slips. The bands are **cumulative**
(``<= 0`` ⊆ ``< 5`` ⊆ ``< 10``) and convert to working minutes on the schedule's own
calendar (ADR-0027/0028). The DAX bodies in the reference deck are not extractable
(XPress9-compressed DataModel) — these are the documented reconstructions (ADR-0030).

**Float source — recomputed CPM, by validated design (QC audit D20 disposition, re-examined and
CONFIRMED against the fresh Fuse export suite, ADR-0151).** The bands read the engine's pure-logic
CPM float, NOT the stored-preferring ``effective_total_float`` that DCMA-06/07 use: the 0-day
total band at raw CPM float reproduces the delivered Fuse "Zero Days Float" counts on the
authoritative goldens exactly (P2 41 / P5 4 — ``tests/engine/metrics/test_float_bands.py``),
while a stored-float variant broke the match when probed (ADR-0141) and the two bases are known to
swap one Project2 membership (stored flags UID 96, raw CPM flags UID 99 — both count 41; see
``fuse_exports_2026-06.json``). The reference tools themselves mix sources (a Critical count from
their own recompute; a Negative Float check from stored slack), so on a progressed file this page
and the DCMA float checks can legitimately cite different activity sets — that is the reference
behaviour, not a defect.
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.metrics._common import (
    CheckStatus,
    MetricResult,
    is_incomplete,
    non_summary,
    percent,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The deck's band edges, in working days (converted on the schedule's calendar).
_BAND_DAYS = (0, 5, 10)


@dataclass(frozen=True)
class FloatSums:
    """Sum of total and free float across incomplete activities, in working days.

    The deck's Float Analysis page (PBIX p5) charts TotalFloatSum and FreeFloatSum
    per version; a shrinking sum over successive snapshots is the early sign that the
    schedule is consuming its scheduling cushion without recovering it.
    """

    total_days: float
    free_days: float


def compute_float_sums(schedule: Schedule, cpm_result: CPMResult | None = None) -> FloatSums:
    """Sum of all total/free float (working days) across the incomplete population.

    Negative float is included as-is (it drags the sum below what a healthy schedule
    would show — the right forensic signal). Activities absent from the CPM result
    (no timing) are excluded from the sum.
    """
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    incomplete = [t for t in non_summary(schedule) if is_incomplete(t)]
    per_day = schedule.calendar.working_minutes_per_day
    total_min = sum(
        result.timings[t.unique_id].total_float for t in incomplete if t.unique_id in result.timings
    )
    free_min = sum(
        result.timings[t.unique_id].free_float for t in incomplete if t.unique_id in result.timings
    )
    denom = per_day if per_day else 1
    return FloatSums(
        total_days=round(total_min / denom, 1),
        free_days=round(free_min / denom, 1),
    )


def compute_float_bands(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> dict[str, MetricResult]:
    """Cumulative low-float bands over the incomplete activities, keyed by id.

    Six metrics: ``float_total_0`` / ``float_total_lt5`` / ``float_total_lt10`` and the
    ``float_free_*`` trio. "0" is ``float <= 0`` (critical or negative — no room);
    "lt5"/"lt10" are ``float < 5/10 working days`` (each band contains the previous).
    Counts and percentages are over the incomplete population; every band carries its
    offender UIDs (§6 citation basis). Informational (no pass/fail threshold).
    """
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    incomplete = [t for t in non_summary(schedule) if is_incomplete(t)]
    per_day = schedule.calendar.working_minutes_per_day
    out: dict[str, MetricResult] = {}
    for kind, label in (("total", "Total"), ("free", "Free")):
        floats: dict[int, int] = {}
        for t in incomplete:
            timing = result.timings.get(t.unique_id)
            if timing is not None:
                floats[t.unique_id] = timing.total_float if kind == "total" else timing.free_float
        for days in _BAND_DAYS:
            if days == 0:
                offenders = _band(incomplete, floats, limit_minutes=0, inclusive=True)
                mid, name = f"float_{kind}_0", f"{label} Float 0 Days"
            else:
                offenders = _band(incomplete, floats, limit_minutes=days * per_day, inclusive=False)
                mid, name = f"float_{kind}_lt{days}", f"{label} Float < {days} Days"
            out[mid] = MetricResult(
                mid,
                name,
                len(offenders),
                len(incomplete),
                round(percent(len(offenders), len(incomplete)), 1),
                "%",
                CheckStatus.NOT_APPLICABLE,
                offender_uids=offenders,
            )
    return out


def _band(
    incomplete: list[Task], floats: dict[int, int], *, limit_minutes: int, inclusive: bool
) -> tuple[int, ...]:
    """UIDs of incomplete activities whose float is under (or at) the band edge."""
    return tuple(
        t.unique_id
        for t in incomplete
        if t.unique_id in floats
        and (
            floats[t.unique_id] <= limit_minutes
            if inclusive
            else floats[t.unique_id] < limit_minutes
        )
    )
