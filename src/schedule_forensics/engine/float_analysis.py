"""Single-schedule float analysis — total/free float per task, in days, + a summary.

A thin, presentation-oriented layer over a :class:`~schedule_forensics.engine.cpm.CPMResult`:
it joins each scheduled task's CPM timing with its progress and renders float on the
**day** axis with deterministic rounding (Law 2 / §3 — :mod:`schedule_forensics.model.units`).

Two notions of "critical" live here, kept distinct:

* ``is_critical`` — the pure CPM property ``total_float <= 0`` (a property of the
  network logic, independent of progress);
* the **Acumen "Critical" metric** — ``total_float <= 0`` **and** the activity is not
  yet complete (a finished activity is no longer a forward schedule risk).
  :attr:`ScheduleFloatSummary.critical_incomplete_count` is that metric, validated
  against the Acumen targets (Project2 = 41, Project5 = 37).

Cross-version float *trends* (erosion across a series) are a separate, forensic
concern handled at M11, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.units import minutes_to_days


@dataclass(frozen=True)
class FloatResult:
    """Total/free float for one task, in working minutes and (rounded) days."""

    unique_id: int
    total_float_minutes: int
    free_float_minutes: int
    total_float_days: Decimal
    free_float_days: Decimal
    is_critical: bool  # pure CPM: total_float <= 0
    is_complete: bool  # percent_complete >= 100

    @property
    def is_critical_incomplete(self) -> bool:
        """The Acumen "Critical" metric basis: on the critical path and not finished."""
        return self.is_critical and not self.is_complete


@dataclass(frozen=True)
class ScheduleFloatSummary:
    """Schedule-level float roll-up over the scheduled (non-summary) activities."""

    task_count: int
    critical_count: int  # total_float <= 0 (pure CPM)
    critical_incomplete_count: int  # Acumen "Critical" metric (<= 0 and not complete)
    negative_float_count: int  # total_float < 0 (over-constrained / behind an imposed finish)
    network_finish_minutes: int
    network_finish_days: Decimal


def analyze_floats(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> tuple[FloatResult, ...]:
    """Per-task float for every scheduled activity, sorted by UniqueID.

    Computes the CPM if ``cpm_result`` is not supplied. Each result carries float in
    both working minutes (exact) and rounded days (presentation).
    """
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    tasks_by_id = schedule.tasks_by_id
    out: list[FloatResult] = []
    for uid in sorted(result.timings):
        timing = result.timings[uid]
        task = tasks_by_id[uid]
        out.append(
            FloatResult(
                unique_id=uid,
                total_float_minutes=timing.total_float,
                free_float_minutes=timing.free_float,
                total_float_days=minutes_to_days(timing.total_float),
                free_float_days=minutes_to_days(timing.free_float),
                is_critical=timing.is_critical,
                is_complete=task.is_complete,
            )
        )
    return tuple(out)


def summarize_floats(
    schedule: Schedule, cpm_result: CPMResult | None = None
) -> ScheduleFloatSummary:
    """Roll up :func:`analyze_floats` into schedule-level counts + the network finish."""
    result = cpm_result if cpm_result is not None else compute_cpm(schedule)
    floats = analyze_floats(schedule, result)
    return ScheduleFloatSummary(
        task_count=len(floats),
        critical_count=sum(1 for f in floats if f.is_critical),
        critical_incomplete_count=sum(1 for f in floats if f.is_critical_incomplete),
        negative_float_count=sum(1 for f in floats if f.total_float_minutes < 0),
        network_finish_minutes=result.project_finish,
        network_finish_days=minutes_to_days(result.project_finish),
    )
