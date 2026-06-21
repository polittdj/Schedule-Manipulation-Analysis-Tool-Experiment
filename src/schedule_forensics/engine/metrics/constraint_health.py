"""Constraint-health checks — unsatisfied date constraints and deadline negative float.

Two deterministic checks the tool did not carry, from the NASA Schedule Management Handbook /
assessment decks (plan A1). Both compare the trusted CPM's computed early dates against the
activity's own imposed date, so a violation is exactly verifiable (no new schedule math). Parity-
isolated lightweight dataclasses (NOT ``MetricResult``) — out of the Fuse ribbon and the metric-
dictionary coverage test, like ``health_extra`` / ``logic_integrity`` / ``float_erosion``.

* **Unsatisfied date constraint** — a hard-constrained activity whose CPM date the constraint can't
  hold: a *no-later-than* / *must* date the logic-driven early date already runs past. SNLT / MSO
  compare the early **start**; FNLT / MFO compare the early **finish**, against the constraint date.
  (MSO / MFO are *pinned* by the solver, so a must-date that conflicts with the logic instead shows
  as negative float — DCMA-07; this check reports the no-later-than caps the forward pass overruns.)
* **Deadline negative float** — an activity carrying a (soft) ``deadline`` whose logic finish runs
  past it: ``early_finish > deadline``. That is the "artificial negative float" a deadline imposes —
  distinct from a hard constraint, and the precise driver behind a slice of the DCMA-07 count.

Sources: NASA Schedule Management Handbook Fig. 6-9 (pp.170-172); assessment Deck-1 (constraint /
deadline checks). The CPM constraint model (engine/cpm.py): SNLT/FNLT/MSO/MFO/deadline are backward
caps; a forward early date exceeding the cap is exactly a negative-float violation.
"""

from __future__ import annotations

from dataclasses import dataclass

from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.engine.metrics._common import non_summary, to_offset
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType

#: cap the offender list carried to the UI (the activity grid is the full record)
_OFFENDER_CAP = 50
#: hard constraints compared on the early START vs the constraint date (no-later-than / must-start)
_START_CAPPED = frozenset({ConstraintType.SNLT, ConstraintType.MSO})
#: hard constraints compared on the early FINISH vs the constraint date (no-later-than / must)
_FINISH_CAPPED = frozenset({ConstraintType.FNLT, ConstraintType.MFO})


@dataclass(frozen=True)
class ConstraintCheck:
    """One constraint-health check: how many offend, which activities (capped), and why."""

    key: str
    label: str
    count: int
    population: int
    offenders: tuple[int, ...]
    description: str


@dataclass(frozen=True)
class ConstraintHealth:
    """The constraint-health checks for one schedule."""

    checks: tuple[ConstraintCheck, ...]


def compute_constraint_health(schedule: Schedule, cpm: CPMResult) -> ConstraintHealth:
    """Compute the unsatisfied-constraint + deadline-negative-float checks for ``schedule``.

    Uses the deterministic CPM early dates (``cpm.timings``) versus each activity's own constraint /
    deadline offset on the schedule calendar — a violation is the forward early date running past
    the imposed cap (exactly the negative-float condition the solver would produce).
    """
    tasks = non_summary(schedule)

    constrained = [t for t in tasks if t.has_hard_constraint]
    unsatisfied: list[int] = []
    for t in constrained:
        timing = cpm.timings.get(t.unique_id)
        off = to_offset(schedule, t.constraint_date)
        if timing is None or off is None:
            continue
        start_violated = t.constraint_type in _START_CAPPED and timing.early_start > off
        finish_violated = t.constraint_type in _FINISH_CAPPED and timing.early_finish > off
        if start_violated or finish_violated:
            unsatisfied.append(t.unique_id)

    deadlined = [t for t in tasks if t.deadline is not None]
    past_deadline: list[int] = []
    for t in deadlined:
        timing = cpm.timings.get(t.unique_id)
        off = to_offset(schedule, t.deadline)
        if timing is None or off is None:
            continue
        if timing.early_finish > off:
            past_deadline.append(t.unique_id)

    checks = (
        ConstraintCheck(
            key="unsatisfied_constraint",
            label="Unsatisfied date constraints",
            count=len(unsatisfied),
            population=len(constrained),
            offenders=tuple(sorted(unsatisfied)[:_OFFENDER_CAP]),
            description=(
                "Hard-constrained activities whose imposed no-later-than / must date the logic "
                "already runs past (the CPM early date exceeds the constraint date) — the date "
                "cannot be honored without negative float. Resolve the logic or relax the date."
            ),
        ),
        ConstraintCheck(
            key="deadline_negative_float",
            label="Deadlines breached (negative float)",
            count=len(past_deadline),
            population=len(deadlined),
            offenders=tuple(sorted(past_deadline)[:_OFFENDER_CAP]),
            description=(
                "Activities whose logic finish runs past a set deadline (early finish > "
                "deadline) — the artificial negative float a deadline imposes, signalling the plan "
                "can't meet a committed date on the current logic."
            ),
        ),
    )
    return ConstraintHealth(checks=checks)
