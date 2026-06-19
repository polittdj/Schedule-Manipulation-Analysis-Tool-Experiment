"""Field-based grouping & filtering — scope any analysis to a subset of activities (ADR-0090).

The operator can pick up to :data:`MAX_FIELDS` fields — standard built-ins (WBS, Activity Type,
Constraint Type, Resource, Critical, % Complete) **or** any mapped custom field (CA-WBS, CAM, …;
ADR-0088) — and a value per field. Two uses build on this layer:

* **filter** — every metric runs over the tasks that match ALL chosen ``(field, value)`` criteria
  (:func:`filter_schedule` returns a sub-schedule of the matching tasks and the relationships
  *among* them, which the existing engine then analyses unchanged);
* **breakdown** — :func:`group_values` splits a field into its distinct values, so a metric can be
  computed once per group (e.g. one BEI per CA-WBS code).

Matching is on the field's string value (case-sensitive, as MS Project stores it); ``Resource`` is
multi-valued, so a criterion matches when the task *carries* that resource.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: The most fields the operator may combine at once (a filter or a stack of breakdowns).
MAX_FIELDS = 5

#: A grouping/filter criterion: a field label and the required value(s). The value may be a single
#: string (exact match), a sequence of strings (match ANY — the MS-Project-style multi-select), or
#: empty ("" / empty sequence = "field is populated").
Criterion = tuple[str, "str | Sequence[str]"]


def _allowed_values(value: str | Sequence[str]) -> list[str]:
    """Normalise a criterion value to the list of accepted strings ([] = 'any populated value')."""
    if isinstance(value, str):
        return [value] if value else []
    return [v for v in value if v]


def _activity_type(t: Task) -> str:
    if t.is_summary:
        return "Summary"
    if t.is_milestone:
        return "Milestone"
    return "Normal"


def _percent_bucket(t: Task) -> str:
    if t.percent_complete >= 100.0:
        return "Complete"
    return "In Progress" if t.percent_complete > 0.0 else "Not Started"


#: Built-in single-valued groupable fields → a string value per task (``None`` when unset).
STANDARD_FIELDS: dict[str, Callable[[Task], str | None]] = {
    "WBS": lambda t: t.wbs,
    "Activity Type": _activity_type,
    "Constraint Type": lambda t: t.constraint_type.value if t.constraint_type else None,
    "Resource": lambda t: "; ".join(t.resource_names) or None,
    "Critical": lambda t: (
        None if t.stored_is_critical is None else ("Yes" if t.stored_is_critical else "No")
    ),
    "% Complete": _percent_bucket,
}


def available_fields(schedule: Schedule) -> tuple[str, ...]:
    """Selectable fields for this schedule: the built-in standard fields, then the custom fields."""
    return (*STANDARD_FIELDS.keys(), *schedule.custom_field_labels)


def field_value(schedule: Schedule, task: Task, field: str) -> str | None:
    """The task's ``field`` value — a custom field wins, else a standard field, else ``None``."""
    if field in schedule.custom_field_labels:
        return task.custom_field(field)
    accessor = STANDARD_FIELDS.get(field)
    return accessor(task) if accessor is not None else None


def task_matches(schedule: Schedule, task: Task, criteria: Sequence[Criterion]) -> bool:
    """True when the task satisfies EVERY criterion (logical AND across fields).

    Within a field the value(s) are OR'd: a non-empty value/sequence requires the task's value to be
    one of them (``Resource`` matches when the task carries any of them); an empty value requires
    only that the field is populated on the task.
    """
    for field, value in criteria:
        allowed = _allowed_values(value)
        if field == "Resource":
            names = task.resource_names
            if allowed:
                if not any(v in names for v in allowed):
                    return False
            elif not names:
                return False
            continue
        actual = field_value(schedule, task, field)
        if allowed:
            if actual not in allowed:
                return False
        elif not actual:
            return False
    return True


def select(schedule: Schedule, criteria: Sequence[Criterion]) -> tuple[int, ...]:
    """UIDs of the tasks matching all criteria (file order). Raises if > MAX_FIELDS given."""
    if len(criteria) > MAX_FIELDS:
        raise ValueError(f"at most {MAX_FIELDS} fields may be combined, got {len(criteria)}")
    return tuple(
        t.unique_id for t in schedule.tasks if task_matches(schedule, task=t, criteria=criteria)
    )


def filter_schedule(schedule: Schedule, criteria: Sequence[Criterion]) -> Schedule:
    """A sub-schedule of the matching tasks and the relationships *among* them.

    Project frame (start/finish/status/calendar/custom-field labels) is preserved so the existing
    engine analyses the subset unchanged; relationships to tasks outside the subset are dropped, so
    logic checks reflect only the selected population. An empty selection yields a task-less copy.
    """
    kept = {uid for uid in select(schedule, criteria)}
    tasks = tuple(t for t in schedule.tasks if t.unique_id in kept)
    rels = tuple(
        r for r in schedule.relationships if r.predecessor_id in kept and r.successor_id in kept
    )
    return schedule.model_copy(update={"tasks": tasks, "relationships": rels})


def group_values(schedule: Schedule, field: str) -> dict[str, tuple[int, ...]]:
    """Map each distinct populated value of ``field`` → the UIDs carrying it (for the breakdown).

    ``Resource`` expands per assigned resource (a task can land in several groups); unset values are
    skipped. Groups come back sorted by value for a stable scorecard.
    """
    groups: dict[str, list[int]] = {}
    for t in schedule.tasks:
        if field == "Resource":
            values: tuple[str, ...] = t.resource_names
        else:
            v = field_value(schedule, t, field)
            values = (v,) if v else ()
        for value in values:
            groups.setdefault(value, []).append(t.unique_id)
    return {k: tuple(groups[k]) for k in sorted(groups)}
