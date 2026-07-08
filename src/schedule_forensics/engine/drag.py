"""Drag Analysis — how many working days each driving-path activity personally adds.

DRAG (Devaux's Removed Activity Gauge) answers "if this activity's remaining work vanished,
how much sooner would the target finish?" — the complement of float: float measures how much an
OFF-path activity can slip; drag measures how much an ON-path activity is worth compressing.

Semantics, validated exactly against the operator's SSI Directional Path export (focus UID 67,
``tests/fixtures/golden/ssi_uid67/case.json`` — all 20 Path-01 Drag values reproduce):

* Only driving-path activities carry drag (off-path activities have float instead; SSI reports
  Drag only on Path-01 rows).
* A path activity's drag is capped by its **remaining** working duration — a 25-day activity at
  36% complete can only give back its 16 remaining days (SSI UID 35: Drag 16 d).
* An activity running **in parallel with another zero-slack activity** has 0 drag: removing it
  does not move the target because the parallel branch still governs (SSI UIDs 60/61 and 65/66
  — the parallel rebar/form pairs — all report 0 d).
* Generally: drag = min(remaining duration, minimum driving slack among CONCURRENT activities
  not on the same serial segment), where "concurrent" = the CPM windows overlap.

Pure analysis on top of :mod:`driving_slack` — no CPM number is modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from schedule_forensics.engine.cpm import CPMResult, compute_cpm
from schedule_forensics.engine.driving_slack import DrivingSlackResult
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.units import MINUTES_PER_DAY


@dataclass(frozen=True)
class DragResult:
    """One driving-path activity's drag."""

    unique_id: int
    name: str
    drag_minutes: int
    drag_days: Decimal
    remaining_minutes: int
    #: the UniqueID of the concurrent activity that caps this drag (None = capped only by
    #: the activity's own remaining duration)
    capped_by_uid: int | None


def _remaining_minutes(schedule: Schedule, uid: int) -> int:
    task = schedule.task_by_id(uid)
    if task.remaining_duration_minutes is not None:
        return task.remaining_duration_minutes
    if task.percent_complete >= 100.0:
        return 0
    return round(task.duration_minutes * (1.0 - task.percent_complete / 100.0))


def compute_drag(
    schedule: Schedule,
    results: dict[int, DrivingSlackResult],
    *,
    cpm_result: CPMResult | None = None,
) -> dict[int, DragResult]:
    """Drag for every on-driving-path activity in ``results`` (working minutes / days)."""
    cpm = cpm_result if cpm_result is not None else compute_cpm(schedule)
    per_day = MINUTES_PER_DAY

    path_uids = [uid for uid, r in results.items() if r.on_driving_path]
    windows: dict[int, tuple[int, int]] = {}
    for uid in path_uids:
        t = cpm.timing(uid)
        windows[uid] = (t.early_start, t.early_finish)

    out: dict[int, DragResult] = {}
    for uid in path_uids:
        start, finish = windows[uid]
        remaining = _remaining_minutes(schedule, uid)
        drag = remaining
        capped_by: int | None = None
        if remaining > 0 and finish > start:
            # concurrent = any OTHER traced activity whose CPM window overlaps this one's;
            # its driving slack caps how much removing this activity can help the target
            for other, r in results.items():
                if other == uid:
                    continue
                ot = cpm.timing(other)
                o_start, o_finish = ot.early_start, ot.early_finish
                if o_finish <= o_start:
                    continue  # zero-length (milestone/summary window) — cannot govern a span
                if o_start < finish and start < o_finish:  # windows overlap
                    slack = r.driving_slack_minutes
                    if slack < drag:
                        drag = slack
                        capped_by = other
        drag = max(0, drag)
        out[uid] = DragResult(
            unique_id=uid,
            name=schedule.task_by_id(uid).name,
            drag_minutes=drag,
            drag_days=(Decimal(drag) / Decimal(per_day)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            remaining_minutes=remaining,
            capped_by_uid=capped_by,
        )
    return out
