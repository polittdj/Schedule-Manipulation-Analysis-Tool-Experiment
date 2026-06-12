"""Float-band metrics — how much of the to-go work is running out of room (M15).

The reference Power BI deck's "Float Analysis" page banded the incomplete work by
remaining float: activities at **0 days** of float (no room at all), under **5 days**,
and under **10 days**, for both **total** and **free** float, as counts and shares —
trended across versions, the swelling of the low-float bands is the early-warning that
a schedule is losing its ability to absorb slips. The bands are **cumulative**
(``<= 0`` ⊆ ``< 5`` ⊆ ``< 10``) and convert to working minutes on the schedule's own
calendar (ADR-0027/0028). The DAX bodies in the reference deck are not extractable
(XPress9-compressed DataModel) — these are the documented reconstructions (ADR-0030).
"""

from __future__ import annotations

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
