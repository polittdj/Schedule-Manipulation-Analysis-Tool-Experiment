"""Session-wide grouping and A-Z ordering for MS Project **saved groups** (feature #10, PR-C).

A :class:`~schedule_forensics.model.saved_view.SavedGroup` is an ordered list of clauses (a field,
a direction, and — for ``groupOn == 2`` — an interval band). This module realizes that definition
as ordered ``(label, uids)`` buckets a view can band/sort by, and provides the A-Z union helpers
that gather the distinct saved filters/groups across every loaded version for the pickers.

Unlike the field-based breakdown (``grouping.group_values``, keyed by the operator's *label*), a
group clause references the **raw** MS Project field name (``Text9``, ``% Complete``), so field
lookups route through :func:`~schedule_forensics.engine.msp_field_resolver.resolve_field`.
A group whose first clause field cannot be resolved on a given file degrades to a single
``(ungrouped)`` bucket for that file rather than erroring — the same file may group fine on another
version that carries the field.

Grouping is **presentation only** (ordering + banding); it never changes a metric or a population.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Sequence
from typing import Any

from schedule_forensics.engine.msp_field_resolver import (
    FieldKind,
    ResolvedField,
    field_kind,
    resolve_field,
)
from schedule_forensics.model.saved_view import GroupClause, SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_DAY_MINUTES = 480
_UNGROUPED = "(ungrouped)"
_BLANK = "(none)"

#: A per-clause sort key: ``(is_blank, typed_key)``. ``is_blank`` sorts blanks together at one end;
#: within a clause every task shares the field's kind, so the typed keys are mutually comparable
#: (the ``Any`` on the second slot is deliberate — the kind guarantees same-type comparands).
_ClauseKey = tuple[int, Any]


def _fmt_number(value: float) -> str:
    """A compact numeric label (integers without a trailing ``.0``)."""
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _parse_interval(interval: str | None) -> float | None:
    """The clause's ``groupOn == 2`` band size as a positive float, or ``None`` if not usable."""
    if interval is None:
        return None
    try:
        size = float(interval)
    except (TypeError, ValueError):
        return None
    return size if size > 0 else None


def _clause_key_and_label(resolved: ResolvedField, clause: GroupClause) -> tuple[_ClauseKey, str]:
    """One clause's ``(sort_key, display_label)`` for a task's resolved value."""
    value = resolved.value
    kind = resolved.kind
    if value is None:
        return (1, ""), _BLANK
    if clause.group_on == 2 and kind in (
        FieldKind.NUMERIC,
        FieldKind.PERCENT,
        FieldKind.CURRENCY,
        FieldKind.DURATION_MINUTES,
    ):
        size = _parse_interval(clause.interval)
        if size is not None:
            numeric = float(value)  # type: ignore[arg-type]
            base = numeric / _DAY_MINUTES if kind is FieldKind.DURATION_MINUTES else numeric
            band = math.floor(base / size)
            lo, hi = band * size, (band + 1) * size
            return (0, lo), f"{_fmt_number(lo)}-{_fmt_number(hi)}"
        # A non-positive interval on a % Complete field is MS Project's "Complete and Incomplete
        # Tasks" built-in — a two-bucket split at 100%, NOT one bucket per distinct percentage. (No
        # positive band size is verifiable via MPXJ, which carries no group-render oracle; this
        # mirrors the documented built-in and the tool's own Complete/Incomplete convention.)
        if kind is FieldKind.PERCENT and isinstance(value, int | float):
            complete = float(value) >= 100.0
            return (0, int(complete)), ("Complete" if complete else "Incomplete")
    if kind is FieldKind.BOOLEAN:
        return (0, int(bool(value))), ("Yes" if value else "No")
    if kind is FieldKind.DATE and isinstance(value, dt.datetime):
        return (0, value), value.date().isoformat()
    if kind is FieldKind.DURATION_MINUTES and isinstance(value, int | float):
        return (0, float(value)), f"{_fmt_number(float(value) / _DAY_MINUTES)}d"
    if kind in (FieldKind.NUMERIC, FieldKind.PERCENT, FieldKind.CURRENCY) and isinstance(
        value, int | float
    ):
        return (0, float(value)), _fmt_number(float(value))
    return (0, str(value)), str(value)


def group_by_clauses(schedule: Schedule, group: SavedGroup) -> list[tuple[str, tuple[int, ...]]]:
    """Order ``schedule``'s tasks into the saved group's buckets: ``[(label, uids), …]``.

    Buckets come back in the group's sort order (each clause's ``ascending`` honored, clauses nested
    left-to-right). ``group_on == 2`` clauses band numeric/percent/duration values by the clause
    interval. A group with no clauses, or whose **first** clause field is unresolvable on this file,
    yields one ``(ungrouped)`` bucket holding every task in file order — never an error.
    """
    tasks = list(schedule.tasks)
    if not group.clauses or not tasks:
        return [(_UNGROUPED, tuple(t.unique_id for t in tasks))] if tasks else []
    first = group.clauses[0]
    if first.field is None or field_kind(first.field, field_enum=first.field_enum) is (
        FieldKind.UNRESOLVED
    ):
        return [(_UNGROUPED, tuple(t.unique_id for t in tasks))]

    # Precompute each task's (per-clause key, per-clause label). Stable multi-key sort: sort by the
    # LAST clause first, then earlier ones, so the first clause is the outermost grouping.
    labels: dict[int, tuple[str, ...]] = {}
    keys: dict[int, tuple[_ClauseKey, ...]] = {}
    for t in tasks:
        clause_keys: list[_ClauseKey] = []
        clause_labels: list[str] = []
        for clause in group.clauses:
            resolved = resolve_field(schedule, t, clause.field or "", field_enum=clause.field_enum)
            key, label = _clause_key_and_label(resolved, clause)
            clause_keys.append(key)
            clause_labels.append(label)
        keys[t.unique_id] = tuple(clause_keys)
        labels[t.unique_id] = tuple(clause_labels)

    ordered = list(tasks)
    for i in reversed(range(len(group.clauses))):
        desc = not group.clauses[i].ascending

        def clause_key(t: Task, idx: int = i) -> _ClauseKey:
            return keys[t.unique_id][idx]

        ordered.sort(key=clause_key, reverse=desc)

    buckets: list[tuple[str, list[int]]] = []
    for t in ordered:
        label = " / ".join(labels[t.unique_id])
        if not buckets or buckets[-1][0] != label:
            buckets.append((label, []))
        buckets[-1][1].append(t.unique_id)
    return [(label, tuple(uids)) for label, uids in buckets]


def group_first_field(group: SavedGroup | None) -> str | None:
    """The group's first clause field (raw name) — the single field a scorecard/rollup breaks down
    by when a saved group is active but no explicit breakdown field is chosen. ``None`` when there
    is no group or its first clause has no field."""
    if group is None or not group.clauses:
        return None
    return group.clauses[0].field


def saved_filters_union(schedules: Sequence[Schedule]) -> tuple[SavedFilter, ...]:
    """Every distinct saved filter across ``schedules`` (dedup by name, first-seen wins), sorted
    A-Z by display name (case-insensitive) for the picker."""
    seen: set[str] = set()
    out: list[SavedFilter] = []
    for schedule in schedules:
        for f in schedule.saved_filters:
            if f.name not in seen:
                seen.add(f.name)
                out.append(f)
    return tuple(sorted(out, key=lambda f: f.display_name.casefold()))


def saved_groups_union(schedules: Sequence[Schedule]) -> tuple[SavedGroup, ...]:
    """Every distinct saved group across ``schedules`` (dedup by name, first-seen wins), sorted A-Z
    by display name (case-insensitive) for the picker."""
    seen: set[str] = set()
    out: list[SavedGroup] = []
    for schedule in schedules:
        for g in schedule.saved_groups:
            if g.name not in seen:
                seen.add(g.name)
                out.append(g)
    return tuple(sorted(out, key=lambda g: g.display_name.casefold()))


def find_saved_filter(schedules: Sequence[Schedule], name: str) -> SavedFilter | None:
    """The saved filter named ``name`` from the union (exact name match), or ``None``."""
    for f in saved_filters_union(schedules):
        if f.name == name:
            return f
    return None


def find_saved_group(schedules: Sequence[Schedule], name: str) -> SavedGroup | None:
    """The saved group named ``name`` from the union (exact name match), or ``None``."""
    for g in saved_groups_union(schedules):
        if g.name == name:
            return g
    return None
