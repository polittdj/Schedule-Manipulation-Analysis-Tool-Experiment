"""Field-by-field comparison of two :class:`Schedule` reads of the SAME source.

This is the validation primitive behind ``scripts/validate_against_msp.py``: on
Windows it reads one ``.mpp`` via the COM importer AND via the cross-platform
MPXJ importer, then diffs them here. Two INDEPENDENT readers agreeing on every
field is strong evidence that the COM mapping is right -- in particular the two
assumptions that are ``source-pending`` until verified on Windows (CLAUDE.md
"Windows / COM gotchas"): gotcha 5 (``Duration``/``Lag`` are in MINUTES) and
gotcha 10 (the ``ConstraintType``/``Dependency.Type`` integer enum codes). Any
disagreement is surfaced for the operator to adjudicate against the MS Project
UI rather than silently trusted (LAW 2 -- fidelity over speed).

It is a PURE function (no I/O, no ``win32com``), so it is fully unit-testable
off-Windows even though the COM read that feeds it is Windows-bound.
"""

from __future__ import annotations

from enum import Enum

from schedule_forensics.schemas import Schedule

# Task fields compared, by attribute name. Covers every field the importers map
# (the COM gotcha-5 minute durations and gotcha-10 constraint enums are included
# via ``duration_minutes`` / ``constraint_type``).
_TASK_FIELDS: tuple[str, ...] = (
    "name",
    "duration_minutes",
    "is_milestone",
    "is_summary",
    "constraint_type",
    "constraint_date",
    "deadline",
    "percent_complete",
    "actual_start",
    "actual_finish",
    "finish",
    "baseline_start",
    "baseline_finish",
    "budgeted_cost",
    "resource_names",
)

# Schedule-level scalar fields (task/relation collections are diffed separately).
_SCHEDULE_FIELDS: tuple[str, ...] = ("name", "project_start", "status_date", "baseline_finish")

_FLOAT_TOLERANCE = 1e-6


def _differ(a_val: object, b_val: object) -> bool:
    """True if two field values differ (floats compared within a small tolerance)."""
    if isinstance(a_val, float) and isinstance(b_val, float):
        return abs(a_val - b_val) > _FLOAT_TOLERANCE
    return a_val != b_val


def _show(value: object) -> str:
    """Render a field value for the report (enum -> its value, else repr)."""
    if isinstance(value, Enum):
        return str(value.value)
    return repr(value)


def diff_schedules(
    a: Schedule, b: Schedule, *, a_label: str = "A", b_label: str = "B"
) -> list[str]:
    """Return human-readable differences between two reads of the same schedule.

    Tasks are matched by ``unique_id`` (the sole cross-version key -- commandment
    3); relations by ``(predecessor_id, successor_id)``. The list is empty when the
    two schedules are field-by-field identical (across the compared fields).
    """
    diffs: list[str] = []

    for field in _SCHEDULE_FIELDS:
        a_val, b_val = getattr(a, field), getattr(b, field)
        if _differ(a_val, b_val):
            diffs.append(f"schedule.{field}: {a_label}={_show(a_val)} {b_label}={_show(b_val)}")

    a_tasks = {t.unique_id: t for t in a.tasks}
    b_tasks = {t.unique_id: t for t in b.tasks}
    for uid in sorted(a_tasks.keys() - b_tasks.keys()):
        diffs.append(f"task {uid}: present in {a_label} only")
    for uid in sorted(b_tasks.keys() - a_tasks.keys()):
        diffs.append(f"task {uid}: present in {b_label} only")
    for uid in sorted(a_tasks.keys() & b_tasks.keys()):
        ta, tb = a_tasks[uid], b_tasks[uid]
        for field in _TASK_FIELDS:
            a_val, b_val = getattr(ta, field), getattr(tb, field)
            if _differ(a_val, b_val):
                diffs.append(
                    f"task {uid}.{field}: {a_label}={_show(a_val)} {b_label}={_show(b_val)}"
                )

    a_rels = {(r.predecessor_id, r.successor_id): r for r in a.relations}
    b_rels = {(r.predecessor_id, r.successor_id): r for r in b.relations}
    for pred, succ in sorted(a_rels.keys() - b_rels.keys()):
        diffs.append(f"relation {pred}->{succ}: present in {a_label} only")
    for pred, succ in sorted(b_rels.keys() - a_rels.keys()):
        diffs.append(f"relation {pred}->{succ}: present in {b_label} only")
    for key in sorted(a_rels.keys() & b_rels.keys()):
        ra, rb = a_rels[key], b_rels[key]
        pred, succ = key
        if ra.type != rb.type:
            diffs.append(
                f"relation {pred}->{succ}.type: "
                f"{a_label}={_show(ra.type)} {b_label}={_show(rb.type)}"
            )
        if ra.lag_minutes != rb.lag_minutes:
            diffs.append(
                f"relation {pred}->{succ}.lag_minutes: "
                f"{a_label}={ra.lag_minutes} {b_label}={rb.lag_minutes}"
            )

    return diffs
