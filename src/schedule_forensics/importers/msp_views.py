"""Parse the MPXJ saved-views sidecar (``<output>.views.json``) into the model.

MSPDI XML does not carry a project's saved **views** — the named task filters and
groups the planner built — so the vendored converter (``tools/mpxj/MpxjToMspdi.java``)
writes them to a sidecar JSON beside every converted MSPDI. This module parses that
sidecar into the frozen :mod:`schedule_forensics.model.saved_view` objects the
faithful evaluator (:mod:`schedule_forensics.engine.msp_filters`) consumes.

The sidecar shape mirrors the model one-to-one (see the Java exporter):

* ``filters`` — ``name`` / ``isTaskFilter`` / ``showRelatedSummaryRows`` /
  ``promptCount`` / ``criteria`` (``null`` = match-all, else a recursive node of
  ``op`` + either ``children`` (AND/OR) or ``field``/``fieldEnum``/``operands``);
* each operand carries ``kind`` (``literal``/``field``/``prompt``/``null``) plus
  ``text``/``fieldEnum``/``valueType`` as applicable;
* ``groups`` — ``name`` / ``showSummaryTasks`` / ``clauses`` (each ``field`` /
  ``fieldEnum`` / ``ascending`` / ``groupOn`` / ``interval`` / ``startAt``).

A *missing* sidecar means "no saved views" (an older converter, or MSPDI/XER input
that never had them) — the caller simply skips this module. A *malformed* sidecar
raises :class:`ImporterError`: it is produced by our own converter in the same
conversion, so damage means the conversion itself is suspect — fail loud, never
silently drop a saved view (Law 2).
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.model.saved_view import (
    Criterion,
    GroupClause,
    Operand,
    SavedFilter,
    SavedGroup,
)


def _opt_str(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) else None


def _operand(raw: object) -> Operand:
    if not isinstance(raw, dict):
        raise ImporterError(f"views sidecar: operand must be an object, got {type(raw).__name__}")
    kind = raw.get("kind")
    if not isinstance(kind, str):
        raise ImporterError("views sidecar: operand is missing its 'kind'")
    return Operand(
        kind=kind,
        text=_opt_str(raw, "text"),
        field_enum=_opt_str(raw, "fieldEnum"),
        value_type=_opt_str(raw, "valueType"),
    )


def _criterion(raw: object) -> Criterion:
    if not isinstance(raw, dict):
        raise ImporterError(f"views sidecar: criterion must be an object, got {type(raw).__name__}")
    op = raw.get("op")
    if not isinstance(op, str):
        raise ImporterError("views sidecar: criterion is missing its 'op'")
    children = raw.get("children", [])
    operands = raw.get("operands", [])
    if not isinstance(children, list) or not isinstance(operands, list):
        raise ImporterError(f"views sidecar: malformed criterion {op!r}")
    return Criterion(
        operator=op,
        field=_opt_str(raw, "field"),
        field_enum=_opt_str(raw, "fieldEnum"),
        operands=tuple(_operand(o) for o in operands),
        children=tuple(_criterion(c) for c in children),
    )


def _saved_filter(raw: object) -> SavedFilter:
    if not isinstance(raw, dict):
        raise ImporterError(f"views sidecar: filter must be an object, got {type(raw).__name__}")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ImporterError("views sidecar: filter is missing its 'name'")
    criteria = raw.get("criteria")
    prompt_count = raw.get("promptCount", 0)
    return SavedFilter(
        name=name,
        criteria=None if criteria is None else _criterion(criteria),
        is_task_filter=bool(raw.get("isTaskFilter", True)),
        show_related_summary_rows=bool(raw.get("showRelatedSummaryRows", False)),
        prompt_count=prompt_count if isinstance(prompt_count, int) else 0,
    )


def _group_clause(raw: object) -> GroupClause:
    if not isinstance(raw, dict):
        raise ImporterError(
            f"views sidecar: group clause must be an object, got {type(raw).__name__}"
        )
    group_on = raw.get("groupOn", 0)
    return GroupClause(
        field=_opt_str(raw, "field"),
        field_enum=_opt_str(raw, "fieldEnum"),
        ascending=bool(raw.get("ascending", True)),
        group_on=group_on if isinstance(group_on, int) else 0,
        interval=_opt_str(raw, "interval"),
        start_at=_opt_str(raw, "startAt"),
    )


def _saved_group(raw: object) -> SavedGroup:
    if not isinstance(raw, dict):
        raise ImporterError(f"views sidecar: group must be an object, got {type(raw).__name__}")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ImporterError("views sidecar: group is missing its 'name'")
    clauses = raw.get("clauses", [])
    if not isinstance(clauses, list):
        raise ImporterError(f"views sidecar: malformed group {name!r}")
    return SavedGroup(
        name=name,
        show_summary_tasks=bool(raw.get("showSummaryTasks", True)),
        clauses=tuple(_group_clause(c) for c in clauses),
    )


def parse_views_json_text(
    text: str,
) -> tuple[tuple[SavedFilter, ...], tuple[SavedGroup, ...]]:
    """Parse a views sidecar into ``(saved_filters, saved_groups)``.

    Raises :class:`ImporterError` on any malformation — the sidecar comes from our
    own vendored converter, so a parse failure means the conversion is suspect.
    """
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImporterError(f"MPXJ views sidecar is not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ImporterError("MPXJ views sidecar: top level must be an object")
    filters_raw = doc.get("filters", [])
    groups_raw = doc.get("groups", [])
    if not isinstance(filters_raw, list) or not isinstance(groups_raw, list):
        raise ImporterError("MPXJ views sidecar: 'filters' and 'groups' must be lists")
    try:
        filters = tuple(_saved_filter(f) for f in filters_raw)
        groups = tuple(_saved_group(g) for g in groups_raw)
    except ValidationError as exc:  # a shape our frozen model rejects → same loud failure
        raise ImporterError(f"MPXJ views sidecar is malformed: {exc}") from exc
    return filters, groups
