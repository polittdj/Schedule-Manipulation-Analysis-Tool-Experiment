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


def available_fields_union(schedules: Sequence[Schedule]) -> tuple[str, ...]:
    """Selectable fields across several schedules: the standard fields, then every custom field that
    appears on any of them (first-seen order). Used when a filter applies to all loaded files at
    once, so a custom field present in only some versions is still offered."""
    custom: list[str] = []
    for schedule in schedules:
        for label in schedule.custom_field_labels:
            if label not in custom:
                custom.append(label)
    return (*STANDARD_FIELDS.keys(), *custom)


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


def filter_to_uids(schedule: Schedule, kept: frozenset[int]) -> Schedule:
    """A sub-schedule of the tasks whose UniqueID is in ``kept`` and the relationships *among* them.

    The single reduction primitive shared by the field-based filter (:func:`filter_schedule`) and
    the faithful saved-filter path (``web.app`` scope), so "reduce to these UIDs" means exactly one
    thing. Project frame (start/finish/status/calendar/custom-field labels) is preserved so the
    existing engine analyses the subset unchanged; relationships to tasks outside the subset are
    dropped, so logic checks reflect only the selected population. An empty ``kept`` yields a
    task-less copy.
    """
    tasks = tuple(t for t in schedule.tasks if t.unique_id in kept)
    rels = tuple(
        r for r in schedule.relationships if r.predecessor_id in kept and r.successor_id in kept
    )
    return schedule.model_copy(update={"tasks": tasks, "relationships": rels})


def with_ancestors(schedule: Schedule, kept: frozenset[int]) -> frozenset[int]:
    """``kept`` plus every matching task's summary ancestors (MS Project's "show related summary
    rows").

    Ancestry is by ``outline_level`` over file order: a task's parent is the nearest preceding task
    with a strictly smaller outline level. Metrics are unaffected (the engine runs on non-summary
    tasks anyway) — this only restores the WBS context rows a filtered MS Project view would keep.
    """
    if not kept:
        return kept
    tasks = list(schedule.tasks)
    parent_of: dict[int, int | None] = {}
    stack: list[Task] = []
    for t in tasks:
        while stack and (stack[-1].outline_level or 0) >= (t.outline_level or 0):
            stack.pop()
        parent_of[t.unique_id] = stack[-1].unique_id if stack else None
        stack.append(t)
    out = set(kept)
    for uid in kept:
        cur = parent_of.get(uid)
        while cur is not None and cur not in out:
            out.add(cur)
            cur = parent_of.get(cur)
    return frozenset(out)


def filter_schedule(schedule: Schedule, criteria: Sequence[Criterion]) -> Schedule:
    """A sub-schedule of the tasks matching all field ``criteria`` and the relationships among them.

    Thin wrapper over :func:`filter_to_uids` on the field-selected UID set (so the field and
    saved-filter reduce paths share one rule). An empty selection yields a task-less copy.
    """
    return filter_to_uids(schedule, frozenset(select(schedule, criteria)))


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


def distinct_values(schedules: Sequence[Schedule], field: str) -> list[str]:
    """Every distinct populated value of ``field`` across ``schedules`` (sorted, de-duplicated).

    Powers the filter value picker when a filter spans all loaded files: a value present in any
    version is offered, even if the previewed version doesn't carry it."""
    seen: set[str] = set()
    for schedule in schedules:
        if field in available_fields(schedule):
            seen.update(group_values(schedule, field))
    return sorted(seen)
