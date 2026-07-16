"""Resolve a **raw MS Project field name** (as saved filters/groups reference it) to the current
task's value, typed on the tool's own axis.

MS Project filters/groups reference fields by their raw name — ``Task Name``, ``Start``,
``Actual Finish``, ``Duration``, ``% Complete``, ``Summary``, ``Active``, and custom fields
``Text9`` / ``Flag6`` / ``Duration8`` … . The faithful filter evaluator
(:mod:`schedule_forensics.engine.msp_filters`) and the session-wide grouping both need each of
those resolved to a **typed** value so it can be compared against a literal, another field, or a
prompt.

Two resolution paths:

* **Core scheduling fields** are already typed attributes on :class:`Task` (dates are
  ``datetime`` or ``None``; durations are integer **working minutes**; ``% Complete`` a float
  0-100; the booleans real bools). No coercion — the table just names the accessor and the
  field's *kind*.
* **Custom (extended) fields** are stored on the task as ``(label, raw_string)`` and referenced
  in the filter by their **raw** name (``Text9``), so resolution is a two-hop lookup — raw name
  → label (:attr:`Schedule.custom_field_by_raw_name_map`) → the task's stored string — then a
  family-based coercion (``Flag`` → bool, ``Duration`` → minutes, ``Date`` → datetime,
  ``Number``/``Cost`` → float).

The ``kind`` a field carries is a pure function of its name (so the evaluator can coerce a
filter's *literal* right-hand value to the same axis **before** it has a task). Fields the
source can't carry (``Board Status``/``Sprint``) or the model drops by design (row ``ID``)
resolve to :data:`FieldKind.UNRESOLVED` so the UI can degrade gracefully.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from schedule_forensics.importers._common import (
    iso_duration_to_minutes,
    parse_datetime,
    parse_float,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: A resolved task value on the tool's axis (``int`` = working minutes; ``None`` = the field is
#: absent).
FieldValue = str | int | float | bool | dt.datetime | None


class FieldKind(StrEnum):
    """The comparison axis of a field — drives how the evaluator coerces the other operand."""

    STRING = "string"
    NUMERIC = "numeric"
    CURRENCY = "currency"
    DURATION_MINUTES = "duration_minutes"
    DATE = "date"
    BOOLEAN = "boolean"
    PERCENT = "percent"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ResolvedField:
    """A task's value for one field: the coerced ``value``, its ``kind``, and whether it is at all
    resolvable (``False`` ⇒ a source-absent / by-design-dropped field the UI should annotate)."""

    value: FieldValue
    kind: FieldKind
    resolvable: bool = True


def _resource_names(t: Task) -> str | None:
    return "; ".join(t.resource_names) or None


#: Core field ``MPXJ enum → (accessor, kind)``. Values are already typed on :class:`Task` (no
#: coercion).
_CORE: dict[str, tuple[Callable[[Task], FieldValue], FieldKind]] = {
    "NAME": (lambda t: t.name, FieldKind.STRING),
    "UNIQUE_ID": (lambda t: t.unique_id, FieldKind.NUMERIC),
    "WBS": (lambda t: t.wbs, FieldKind.STRING),
    "OUTLINE_LEVEL": (lambda t: t.outline_level, FieldKind.NUMERIC),
    "OUTLINE_NUMBER": (lambda t: t.outline_number, FieldKind.STRING),
    "PRIORITY": (lambda t: t.priority, FieldKind.NUMERIC),
    "STOP": (lambda t: t.stop, FieldKind.DATE),
    "NOTES": (lambda t: t.notes, FieldKind.STRING),
    "DURATION": (lambda t: t.duration_minutes, FieldKind.DURATION_MINUTES),
    "REMAINING_DURATION": (lambda t: t.remaining_duration_minutes, FieldKind.DURATION_MINUTES),
    "BASELINE_DURATION": (lambda t: t.baseline_duration_minutes, FieldKind.DURATION_MINUTES),
    "WORK": (lambda t: t.work_minutes, FieldKind.DURATION_MINUTES),
    "ACTUAL_WORK": (lambda t: t.actual_work_minutes, FieldKind.DURATION_MINUTES),
    "PERCENT_COMPLETE": (lambda t: t.percent_complete, FieldKind.PERCENT),
    "PHYSICAL_PERCENT_COMPLETE": (lambda t: t.physical_percent_complete, FieldKind.PERCENT),
    "SUMMARY": (lambda t: t.is_summary, FieldKind.BOOLEAN),
    "MILESTONE": (lambda t: t.is_milestone, FieldKind.BOOLEAN),
    "ACTIVE": (lambda t: t.is_active, FieldKind.BOOLEAN),
    "CRITICAL": (lambda t: t.stored_is_critical, FieldKind.BOOLEAN),
    # MS Project's "Task Mode" grouping ("Auto Scheduled vs. Manually Scheduled"); derived from the
    # model's is_manual flag, phrased exactly as MS Project labels the two buckets.
    "TASK_MODE": (
        lambda t: "Manually Scheduled" if t.is_manual else "Auto Scheduled",
        FieldKind.STRING,
    ),
    "TOTAL_SLACK": (lambda t: t.stored_total_float_minutes, FieldKind.DURATION_MINUTES),
    "CONSTRAINT_TYPE": (
        lambda t: t.constraint_type.value if t.constraint_type else None,
        FieldKind.STRING,
    ),
    "CONSTRAINT_DATE": (lambda t: t.constraint_date, FieldKind.DATE),
    "DEADLINE": (lambda t: t.deadline, FieldKind.DATE),
    "START": (lambda t: t.start, FieldKind.DATE),
    "FINISH": (lambda t: t.finish, FieldKind.DATE),
    "ACTUAL_START": (lambda t: t.actual_start, FieldKind.DATE),
    "ACTUAL_FINISH": (lambda t: t.actual_finish, FieldKind.DATE),
    "BASELINE_START": (lambda t: t.baseline_start, FieldKind.DATE),
    "BASELINE_FINISH": (lambda t: t.baseline_finish, FieldKind.DATE),
    "COST": (lambda t: t.cost, FieldKind.CURRENCY),
    "ACTUAL_COST": (lambda t: t.actual_cost, FieldKind.CURRENCY),
    "BASELINE_COST": (lambda t: t.budgeted_cost, FieldKind.CURRENCY),
    "RESOURCE_NAMES": (_resource_names, FieldKind.STRING),
}

#: Display name → MPXJ enum, so a filter that carries only the localized name still resolves.
_DISPLAY_TO_ENUM: dict[str, str] = {
    "Task Name": "NAME",
    "Name": "NAME",
    "Unique ID": "UNIQUE_ID",
    "Outline Level": "OUTLINE_LEVEL",
    "% Complete": "PERCENT_COMPLETE",
    "Physical % Complete": "PHYSICAL_PERCENT_COMPLETE",
    "Total Slack": "TOTAL_SLACK",
    "Constraint Type": "CONSTRAINT_TYPE",
    "Constraint Date": "CONSTRAINT_DATE",
    "Actual Start": "ACTUAL_START",
    "Actual Finish": "ACTUAL_FINISH",
    "Baseline Start": "BASELINE_START",
    "Baseline Finish": "BASELINE_FINISH",
    "Baseline Duration": "BASELINE_DURATION",
    "Baseline Cost": "BASELINE_COST",
    "Remaining Duration": "REMAINING_DURATION",
    "Actual Work": "ACTUAL_WORK",
    "Actual Cost": "ACTUAL_COST",
    "Resource Names": "RESOURCE_NAMES",
    "Duration": "DURATION",
    "Task Mode": "TASK_MODE",
    "Outline Number": "OUTLINE_NUMBER",
    "Priority": "PRIORITY",
    "Stop": "STOP",
    "Status": "STATUS",
    "Project": "PROJECT",
}

#: Fields the source cannot carry or the model drops by design → unresolvable (UI annotates).
_UNRESOLVABLE_ENUMS = frozenset({"ID", "BOARD_STATUS", "SPRINT"})

_CUSTOM_FAMILY_KIND: dict[str, FieldKind] = {
    "Text": FieldKind.STRING,
    "Outline Code": FieldKind.STRING,
    "Flag": FieldKind.BOOLEAN,
    "Number": FieldKind.NUMERIC,
    "Duration": FieldKind.DURATION_MINUTES,
    "Cost": FieldKind.CURRENCY,
    "Date": FieldKind.DATE,
    "Start": FieldKind.DATE,
    "Finish": FieldKind.DATE,
}
_CUSTOM_RE = re.compile(r"^(Text|Outline Code|Flag|Number|Duration|Cost|Date|Start|Finish)\s*\d+$")
#: Enum form of a custom field, e.g. ``TEXT9`` / ``OUTLINE_CODE3`` / ``DURATION8``.
_CUSTOM_ENUM_RE = re.compile(
    r"^(TEXT|OUTLINE_CODE|FLAG|NUMBER|DURATION|COST|DATE|START|FINISH)\d+$"
)
_ENUM_FAMILY_TO_DISPLAY: dict[str, str] = {
    "TEXT": "Text",
    "OUTLINE_CODE": "Outline Code",
    "FLAG": "Flag",
    "NUMBER": "Number",
    "DURATION": "Duration",
    "COST": "Cost",
    "DATE": "Date",
    "START": "Start",
    "FINISH": "Finish",
}


#: Fields computed from the SCHEDULE (not just the task) — resolved by :func:`resolve_field`
#: directly, since the ``_CORE`` accessors deliberately see only the task.
_SCHEDULE_LEVEL_KINDS: dict[str, FieldKind] = {
    "STATUS": FieldKind.STRING,
    "PROJECT": FieldKind.STRING,
}


def _msp_status(schedule: Schedule, task: Task) -> str | None:
    """MS Project's computed **Status** column, reproduced from its documented rule.

    * **Complete** — the task is 100% complete.
    * **Future Task** — the task starts after the status date.
    * **On Schedule** — progress (the stored ``Stop`` date, the date actuals run through) reaches
      at least the day before the status date.
    * **Late** — progress does not reach the day before the status date (including a task that
      should have started but records no progress at all).

    ``None`` (a blank bucket) when the file carries no status date or the task no start — the
    tool never fabricates "today" for a forensic artifact.
    """
    if task.percent_complete >= 100.0:
        return "Complete"
    status_date = schedule.status_date
    if status_date is None or task.start is None:
        return None
    if task.start > status_date:
        return "Future Task"
    threshold = status_date.date() - dt.timedelta(days=1)
    if task.stop is not None and task.stop.date() >= threshold:
        return "On Schedule"
    return "Late"


def _project_name(schedule: Schedule) -> str | None:
    """MS Project's per-task **Project** column: the source file's base name (as MSP and the
    SSI exports show it), falling back to the schedule's display name."""
    if schedule.source_file:
        stem = schedule.source_file.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return stem.rsplit(".", 1)[0] if "." in stem else stem
    return schedule.name or None


def _normalize_enum(field_enum: str | None) -> str | None:
    """Canonicalize a group/filter clause's MPXJ enum.

    MS Project exposes some fields to a **group** clause by their *text* variant — the Duration
    column arrives as ``DURATION_TEXT``, a custom duration as ``DURATION8_TEXT`` — which is the same
    underlying value, just formatted. Strip a trailing ``_TEXT`` when the base names a real field
    (a core enum or a custom family), so the value resolves instead of degrading to UNRESOLVED. A
    genuinely unknown enum (``BOARD_STATUS``) is left untouched and still resolves to UNRESOLVED.
    """
    if field_enum and field_enum.endswith("_TEXT"):
        base = field_enum[: -len("_TEXT")]
        if base in _CORE or _CUSTOM_ENUM_RE.match(base):
            return base
    return field_enum


def _custom_family(raw_field: str, field_enum: str | None) -> str | None:
    """The custom family (``Text``/``Flag``/``Duration``/…) of ``raw_field``, or ``None`` if it
    is not
    a custom field. Prefers the unambiguous MPXJ enum (``TEXT9``); falls back to the display
    name."""
    if field_enum:
        m = _CUSTOM_ENUM_RE.match(field_enum)
        if m:
            return _ENUM_FAMILY_TO_DISPLAY[m.group(1)]
    m = _CUSTOM_RE.match(raw_field)
    return m.group(1) if m else None


def _coerce_custom(family: str, raw: str) -> FieldValue:
    """Coerce a custom field's stored string to its family's typed value (an empty string stays
    ``""``
    so the evaluator's empty-vs-absent distinction survives)."""
    kind = _CUSTOM_FAMILY_KIND[family]
    if kind is FieldKind.STRING:
        return raw
    if kind is FieldKind.BOOLEAN:
        return raw.strip().lower() in {"1", "true", "yes"}
    if kind is FieldKind.DURATION_MINUTES:
        return iso_duration_to_minutes(raw)
    if kind is FieldKind.DATE:
        return parse_datetime(raw)
    # NUMERIC / CURRENCY
    return parse_float(raw)


def field_kind(raw_field: str, *, field_enum: str | None = None) -> FieldKind:
    """The comparison kind of a field **without a task** — lets the evaluator coerce a filter's
    literal
    right-hand value (``"0.0d"`` → minutes, ``"true"`` → bool, an ISO date) before comparing."""
    field_enum = _normalize_enum(field_enum)
    if field_enum and field_enum in _UNRESOLVABLE_ENUMS:
        return FieldKind.UNRESOLVED
    if field_enum and field_enum in _SCHEDULE_LEVEL_KINDS:
        return _SCHEDULE_LEVEL_KINDS[field_enum]
    if not field_enum and raw_field in _DISPLAY_TO_ENUM:
        mapped = _DISPLAY_TO_ENUM[raw_field]
        if mapped in _SCHEDULE_LEVEL_KINDS:
            return _SCHEDULE_LEVEL_KINDS[mapped]
    if field_enum and field_enum in _CORE:
        return _CORE[field_enum][1]
    fam = _custom_family(raw_field, field_enum)
    if fam is not None:
        return _CUSTOM_FAMILY_KIND[fam]
    enum = _DISPLAY_TO_ENUM.get(raw_field)
    if enum and enum in _CORE:
        return _CORE[enum][1]
    if raw_field in _CORE:  # a raw_field that is itself the enum (e.g. "WBS")
        return _CORE[raw_field][1]
    return FieldKind.UNRESOLVED


def resolve_field(
    schedule: Schedule, task: Task, raw_field: str, *, field_enum: str | None = None
) -> ResolvedField:
    """The task's value for ``raw_field`` (identified by the MPXJ ``field_enum`` when available,
    else
    the raw/display name): a core attribute, else a custom field via the two-hop label lookup,
    else
    :data:`FieldKind.UNRESOLVED`."""
    field_enum = _normalize_enum(field_enum)
    if field_enum and field_enum in _UNRESOLVABLE_ENUMS:
        return ResolvedField(None, FieldKind.UNRESOLVED, resolvable=False)
    # schedule-computed fields (Status / Project) — resolved here, where the schedule is in scope
    schedule_enum = field_enum if field_enum in _SCHEDULE_LEVEL_KINDS else None
    if schedule_enum is None and _DISPLAY_TO_ENUM.get(raw_field) in _SCHEDULE_LEVEL_KINDS:
        schedule_enum = _DISPLAY_TO_ENUM[raw_field]
    if schedule_enum == "STATUS":
        return ResolvedField(_msp_status(schedule, task), FieldKind.STRING)
    if schedule_enum == "PROJECT":
        return ResolvedField(_project_name(schedule), FieldKind.STRING)
    # core field (by enum, then display alias, then a raw_field that is itself the enum)
    core_enum = None
    if field_enum and field_enum in _CORE:
        core_enum = field_enum
    elif raw_field in _DISPLAY_TO_ENUM and _DISPLAY_TO_ENUM[raw_field] in _CORE:
        core_enum = _DISPLAY_TO_ENUM[raw_field]
    elif raw_field in _CORE:
        core_enum = raw_field
    if core_enum is not None:
        accessor, kind = _CORE[core_enum]
        return ResolvedField(accessor(task), kind)
    # custom field: raw name → label → stored string → coerce by family
    fam = _custom_family(raw_field, field_enum)
    if fam is not None:
        label = schedule.custom_field_by_raw_name_map.get(raw_field, raw_field)
        stored = task.custom_field(label)
        if stored is None:
            return ResolvedField(None, _CUSTOM_FAMILY_KIND[fam])
        return ResolvedField(_coerce_custom(fam, stored), _CUSTOM_FAMILY_KIND[fam])
    return ResolvedField(None, FieldKind.UNRESOLVED, resolvable=False)


def is_resolvable(raw_field: str, *, field_enum: str | None = None) -> bool:
    """Whether the tool can resolve ``raw_field`` at all (drives whether the UI offers/annotates a
    filter or group that references it)."""
    return field_kind(raw_field, field_enum=field_enum) is not FieldKind.UNRESOLVED
