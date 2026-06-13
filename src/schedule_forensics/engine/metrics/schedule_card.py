"""Schedule "ID card" profile — the deck's *Metrics* page (PBIX page 1, ADR-0030/0037).

Reproduces the reference deck's landing-page aggregates from the trust-root model: the
**activity makeup** (milestone / normal / summary split and the complete / in-progress /
planned status split) and the **primary-constraint distribution** (count + percent per
MS-Project constraint type). These were the two documented engine gaps behind PBIX page 1
(`docs/PLAN/PBIX-VISUALS.md`); the remaining page-1 cards reuse the completion-performance
and CPM outputs the engine already computes.

Both helpers run over **non-summary** activities (summary rollups are not real work),
matching every other metric population, and the summary *count* excludes MS Project's
UID-0 project row (the Acumen "summary" convention — see ``ai/briefing.py``).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from schedule_forensics.engine.metrics._common import non_summary, percent
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class ActivityMakeup:
    """The deck's "Schedule Task Makeup" + activity-status counts for one schedule."""

    total: int  # non-summary activities (the metric population everywhere)
    milestones: int
    normal: int  # non-summary, non-milestone activities
    summaries: int  # WBS summaries excluding the UID-0 project row (Acumen convention)
    complete: int
    in_progress: int
    planned: int  # not started (0%)


@dataclass(frozen=True)
class ConstraintCount:
    """One primary-constraint type's share of the schedule (deck "Primary Constraint")."""

    constraint_type: str  # the ConstraintType value (ASAP, SNET, MFO, …)
    count: int
    percent: float  # of all non-summary activities


def compute_activity_makeup(schedule: Schedule) -> ActivityMakeup:
    """Milestone/normal/summary makeup + complete/in-progress/planned status counts."""
    tasks = non_summary(schedule)
    milestones = sum(1 for t in tasks if t.is_milestone)
    complete = sum(1 for t in tasks if t.percent_complete >= 100.0)
    in_progress = sum(1 for t in tasks if 0.0 < t.percent_complete < 100.0)
    # the Acumen "summary" count excludes MS Project's UID-0 project-level row
    summaries = sum(1 for t in schedule.tasks if t.is_summary and t.unique_id != 0)
    return ActivityMakeup(
        total=len(tasks),
        milestones=milestones,
        normal=len(tasks) - milestones,
        summaries=summaries,
        complete=complete,
        in_progress=in_progress,
        planned=len(tasks) - complete - in_progress,
    )


def compute_constraint_distribution(schedule: Schedule) -> tuple[ConstraintCount, ...]:
    """Count + percent of each primary constraint type, most-common first.

    Over non-summary activities; ties broken by constraint-type name for determinism.
    An all-ASAP schedule (no imposed dates) returns a single ASAP row at 100%.
    """
    tasks = non_summary(schedule)
    total = len(tasks)
    counts = Counter(t.constraint_type.value for t in tasks)
    rows = [
        ConstraintCount(constraint_type=ctype, count=n, percent=percent(n, total))
        for ctype, n in counts.items()
    ]
    rows.sort(key=lambda r: (-r.count, r.constraint_type))
    return tuple(rows)
