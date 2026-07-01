"""JSON schedule importer/exporter — the tool's own, human-readable schedule format.

``parse_json_text`` reads a friendly JSON schedule (a ``name`` + ``project_start`` + a list
of ``tasks`` and ``relationships``, with times in working minutes) into the domain
:class:`~schedule_forensics.model.schedule.Schedule`; it also accepts the strict pydantic
serialization as a fallback. ``to_json_text`` writes that friendly format back out (for
"Save .json"), emitting only meaningful fields so saved files stay readable and re-openable.
Best-effort and fail-loud: a malformed document raises :class:`ImporterError`.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.model import Schedule
from schedule_forensics.model.assignment import Assignment
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.resource import Resource, ResourceType
from schedule_forensics.model.task import ConstraintType, Task

_DATE_FIELDS = (
    "start",
    "finish",
    "actual_start",
    "actual_finish",
    "baseline_start",
    "baseline_finish",
    "constraint_date",
    "deadline",
)


def _dt(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ImporterError(f"invalid datetime in JSON schedule: {value!r}") from exc
    # naive like every other importer (_common.parse_datetime): one tz-aware status_date mixed
    # with naive versions crashed order_versions -> every multi-version page (QC audit D11)
    return parsed.replace(tzinfo=None)


def _int(value: Any, field: str) -> int:
    """A whole number, read strictly. ``unique_id`` is the SOLE cross-version identity, so a
    fractional value must fail loud, never truncate (``1.5`` silently becoming task ``1`` corrupts
    identity — QC audit D24); the same strictness applies to every integer field for consistency.
    """
    if isinstance(value, bool):
        raise ImporterError(f"invalid integer for {field!r}: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    try:
        return int(str(value), 10)
    except (TypeError, ValueError) as exc:
        raise ImporterError(f"invalid integer for {field!r}: {value!r}") from exc


def parse_json(path: str | os.PathLike[str]) -> Schedule:
    """Parse a ``.json`` schedule file. ``source_file`` is stamped with the file's basename so
    citations carry the file label, exactly like the MSPDI/XER importers (QC audit D24)."""
    p = Path(os.fspath(path))
    return parse_json_text(p.read_text(encoding="utf-8")).model_copy(update={"source_file": p.name})


def parse_json_text(text: str) -> Schedule:
    """Parse a friendly (or strict-serialized) JSON schedule into a :class:`Schedule`."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImporterError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "tasks" not in data:
        raise ImporterError("JSON schedule must be an object with a 'tasks' array")
    try:
        return _from_friendly(data)
    except ImporterError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        # fall back to the strict pydantic serialization (round-trips Save .json output)
        try:
            return Schedule.model_validate(data)
        except Exception:
            # surface the friendly-parse cause, not pydantic's strict-schema error
            raise ImporterError(f"could not read JSON schedule: {exc}") from exc


def _calendar(raw: dict[str, Any]) -> Calendar:
    # prefer the exact minute count when present (the writer emits both); a bare
    # hours_per_day is rounded, not truncated (123 min -> 2.05 h must come back as 123)
    if raw.get("working_minutes_per_day") is not None:
        wmpd = int(raw["working_minutes_per_day"])
    else:
        hours = raw.get("hours_per_day")
        wmpd = round(hours * 60) if hours else 480
    weekdays = raw.get("work_weekdays")
    kwargs: dict[str, Any] = {
        "name": str(raw.get("name", "Standard")),
        "working_minutes_per_day": wmpd,
    }
    if raw.get("uid") is not None:
        kwargs["uid"] = int(raw["uid"])
    if weekdays:
        kwargs["work_weekdays"] = tuple(int(d) for d in weekdays)
    if raw.get("holidays"):
        kwargs["holidays"] = tuple(dt.date.fromisoformat(str(h)) for h in raw["holidays"])
    # working_days exceptions + intraday day_segments round-trip (driving-slack parity inputs)
    if raw.get("working_days"):
        kwargs["working_days"] = tuple(dt.date.fromisoformat(str(d)) for d in raw["working_days"])
    if raw.get("day_segments"):
        kwargs["day_segments"] = tuple(
            (int(s[0]), int(s[1])) for s in raw["day_segments"] if isinstance(s, (list, tuple))
        )
    return Calendar(**kwargs)


def _task(raw: dict[str, Any]) -> Task:
    uid = _int(raw["unique_id"], "unique_id")
    # a null or empty name falls back to the UID label, matching MSPDI/XER (a literal "None" /
    # empty-string task name corrupted downstream name handling — QC audit D24)
    name = raw.get("name")
    fields: dict[str, Any] = {
        "unique_id": uid,
        "name": str(name) if name not in (None, "") else f"Task {uid}",
        "duration_minutes": _int(raw.get("duration_minutes", 0), "duration_minutes"),
        "duration_is_elapsed": bool(raw.get("duration_is_elapsed", False)),
    }
    for key in (
        "wbs",
        "is_milestone",
        "is_summary",
        "is_manual",
        "is_estimated_duration",
        "is_level_of_effort",
        "is_active",
        "percent_complete",
        "resource_names",
    ):
        if key in raw and raw[key] is not None:
            fields[key] = raw[key]
    for key in (
        "remaining_duration_minutes",
        "baseline_duration_minutes",
        "calendar_uid",
        "outline_level",
        "stored_total_float_minutes",
    ):
        if raw.get(key) is not None:
            fields[key] = _int(raw[key], key)
    if raw.get("physical_percent_complete") is not None:
        fields["physical_percent_complete"] = float(raw["physical_percent_complete"])
    if raw.get("stored_is_critical") is not None:
        fields["stored_is_critical"] = bool(raw["stored_is_critical"])
    if isinstance(raw.get("custom_fields"), list):
        fields["custom_fields"] = tuple(
            (str(pair[0]), str(pair[1]))
            for pair in raw["custom_fields"]
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        )
    for key in ("cost", "actual_cost", "budgeted_cost"):
        if raw.get(key) is not None:
            fields[key] = float(raw[key])
    for field in _DATE_FIELDS:
        if raw.get(field) is not None:
            fields[field] = _dt(raw[field])
    if raw.get("constraint_type"):
        fields["constraint_type"] = ConstraintType(str(raw["constraint_type"]))
    if isinstance(fields.get("resource_names"), list):
        fields["resource_names"] = tuple(str(r) for r in fields["resource_names"])
    if isinstance(raw.get("resource_ids"), list):
        fields["resource_ids"] = tuple(_int(r, "resource_ids") for r in raw["resource_ids"])
    if isinstance(raw.get("resource_assignments"), list):
        fields["resource_assignments"] = tuple(
            Assignment(
                resource_id=_int(a["resource_id"], "resource_id"),
                work_minutes=_int(a.get("work_minutes", 0), "work_minutes"),
                units=float(a.get("units", 1.0)),
            )
            for a in raw["resource_assignments"]
            if isinstance(a, dict) and a.get("resource_id") is not None
        )
    return Task(**fields)


def _resource(raw: dict[str, Any]) -> Resource:
    kwargs: dict[str, Any] = {
        "unique_id": _int(raw["unique_id"], "resource unique_id"),
        "name": str(raw.get("name", f"Resource {raw['unique_id']}")),
        "is_generic": bool(raw.get("is_generic", False)),
    }
    if raw.get("type"):
        kwargs["type"] = ResourceType(str(raw["type"]))
    for key in ("max_units", "standard_rate"):
        if raw.get(key) is not None:
            kwargs[key] = float(raw[key])
    return Resource(**kwargs)


def _relationship(pred: int, succ: int, raw: dict[str, Any] | None = None) -> Relationship:
    raw = raw or {}
    return Relationship(
        predecessor_id=pred,
        successor_id=succ,
        type=RelationshipType(str(raw.get("type", "FS"))),
        lag_minutes=_int(raw.get("lag_minutes", 0), "lag_minutes"),
    )


def _from_friendly(data: dict[str, Any]) -> Schedule:
    calendars = [_calendar(c) for c in data.get("calendars", []) if isinstance(c, dict)]
    tasks = [_task(t) for t in data["tasks"]]
    rels: list[Relationship] = []
    for r in data.get("relationships", []):
        rels.append(
            _relationship(
                _int(r["predecessor_id"], "predecessor_id"),
                _int(r["successor_id"], "successor_id"),
                r,
            )
        )
    # task-level predecessors: [2] or [{"id": 2, "type": "FS", "lag_minutes": 0}]
    for t in data["tasks"]:
        for p in t.get("predecessors", []) or []:
            if isinstance(p, dict):
                pred_id = p.get("id", p.get("predecessor_id"))
                if pred_id is None:
                    raise ImporterError("task predecessor entry needs an 'id' or 'predecessor_id'")
                rels.append(
                    _relationship(
                        _int(pred_id, "predecessor id"), _int(t["unique_id"], "unique_id"), p
                    )
                )
            else:
                rels.append(
                    _relationship(_int(p, "predecessor id"), _int(t["unique_id"], "unique_id"))
                )
    # project_start is the CPM anchor; a missing/null value must NOT be fabricated (the old
    # 2025-01-06 default invented a forensic input and masked truncated files). Raise like the
    # MSPDI / XER importers do (audit M3).
    project_start = _dt(data.get("project_start"))
    if project_start is None:
        raise ImporterError("JSON schedule is missing 'project_start'")
    schedule_kwargs: dict[str, Any] = {
        "name": str(data.get("name", "Schedule")),
        "project_start": project_start,
        "tasks": tuple(tasks),
        "relationships": tuple(rels),
    }
    if data.get("status_date"):
        schedule_kwargs["status_date"] = _dt(data["status_date"])
    for key in ("project_finish", "baseline_finish"):
        if data.get(key):
            schedule_kwargs[key] = _dt(data[key])
    if isinstance(data.get("custom_field_labels"), list):
        schedule_kwargs["custom_field_labels"] = tuple(str(x) for x in data["custom_field_labels"])
    if isinstance(data.get("resources"), list):
        schedule_kwargs["resources"] = tuple(
            _resource(r) for r in data["resources"] if isinstance(r, dict)
        )
    # The PROJECT calendar is the explicit "calendar" object when present; "calendars" is the full
    # per-task registry. Older saves carried only a single-entry "calendars" — first-entry remains
    # the fallback for them. Never assume calendars[0] IS the project calendar on a multi-calendar
    # file: a strict model_dump lists the registry in uid order, and picking [0] silently swapped
    # the project calendar (every duration/day conversion shifted — QC audit D9).
    if isinstance(data.get("calendar"), dict):
        schedule_kwargs["calendar"] = _calendar(data["calendar"])
        if calendars:
            schedule_kwargs["calendars"] = tuple(calendars)
    elif calendars:
        schedule_kwargs["calendar"] = calendars[0]
        schedule_kwargs["calendars"] = tuple(calendars)
    return Schedule(**schedule_kwargs)


def _calendar_out(cal: Calendar) -> dict[str, Any]:
    # working_minutes_per_day is the exact round-trip value; hours_per_day stays for
    # human readability (the parser prefers the minute count)
    return {
        "uid": cal.uid,
        "name": cal.name,
        "hours_per_day": cal.working_minutes_per_day / 60,
        "working_minutes_per_day": cal.working_minutes_per_day,
        "work_weekdays": list(cal.work_weekdays),
        # holidays / working-day exceptions / intraday segments round-trip exactly so a
        # re-opened file keeps the SSI driving-slack parity inputs (audit C1)
        "holidays": [d.isoformat() for d in cal.holidays],
        "working_days": [d.isoformat() for d in cal.working_days],
        "day_segments": [list(seg) for seg in cal.day_segments],
    }


def to_json_text(schedule: Schedule) -> str:
    """Serialize a schedule to the friendly JSON format (for 'Save .json'); re-openable.

    Lossless by contract: **every** model field round-trips except ``source_file`` (a runtime
    citation label the loader re-stamps from the file name) — a model-introspection guard test
    fails if a new field is added without a writer line. In particular the whole per-task
    ``calendars`` registry is written (Save .json used to keep only the project calendar, leaving
    ``Task.calendar_uid`` dangling and silently changing driving-slack numbers on reopen — QC
    audit D5), along with ``resources``, ``project_finish`` and ``baseline_finish`` (D10/D24).
    """

    def iso(value: dt.datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    out: dict[str, Any] = {
        "name": schedule.name,
        "project_start": schedule.project_start.isoformat(),
        # the project default calendar, then the FULL per-task registry (QC audit D5)
        "calendar": _calendar_out(schedule.calendar),
        "calendars": [_calendar_out(c) for c in (schedule.calendars or (schedule.calendar,))],
        "tasks": [],
        "relationships": [
            {
                "predecessor_id": r.predecessor_id,
                "successor_id": r.successor_id,
                "type": str(r.type),
                "lag_minutes": r.lag_minutes,
            }
            for r in schedule.relationships
        ],
    }
    if schedule.status_date is not None:
        out["status_date"] = schedule.status_date.isoformat()
    for finish_key, finish_val in (
        ("project_finish", schedule.project_finish),
        ("baseline_finish", schedule.baseline_finish),
    ):
        if finish_val is not None:
            out[finish_key] = finish_val.isoformat()
    if schedule.custom_field_labels:
        out["custom_field_labels"] = list(schedule.custom_field_labels)
    if schedule.resources:
        out["resources"] = [
            {
                "unique_id": res.unique_id,
                "name": res.name,
                "type": str(res.type),
                "is_generic": res.is_generic,
                "max_units": res.max_units,
                "standard_rate": res.standard_rate,
            }
            for res in schedule.resources
        ]
    for t in schedule.tasks:
        task: dict[str, Any] = {
            "unique_id": t.unique_id,
            "name": t.name,
            "duration_minutes": t.duration_minutes,
            "duration_is_elapsed": t.duration_is_elapsed,
        }
        if t.percent_complete:
            task["percent_complete"] = t.percent_complete
        if t.resource_names:
            task["resource_names"] = list(t.resource_names)
        if t.resource_ids:
            task["resource_ids"] = list(t.resource_ids)
        if t.resource_assignments:
            task["resource_assignments"] = [
                {"resource_id": a.resource_id, "work_minutes": a.work_minutes, "units": a.units}
                for a in t.resource_assignments
            ]
        # every field the parser reads is written back: a Save .json round-trip must not
        # silently demote milestones/summaries or drop WBS, durations, or costs
        if t.wbs is not None:  # an empty-string WBS is a value, not an absence (QC audit D24)
            task["wbs"] = t.wbs
        if t.is_milestone:
            task["is_milestone"] = True
        if t.is_summary:
            task["is_summary"] = True
        if t.is_manual:
            task["is_manual"] = True
        if t.is_estimated_duration:
            task["is_estimated_duration"] = True
        if t.is_level_of_effort:
            task["is_level_of_effort"] = True
        # is_active defaults True; emit only when False so a deactivated task survives a
        # round-trip (re-activating it silently would defeat the inactive-task exclusion — ADR-0128)
        if not t.is_active:
            task["is_active"] = False
        if t.calendar_uid is not None:
            task["calendar_uid"] = t.calendar_uid
        if t.outline_level:
            task["outline_level"] = t.outline_level
        if t.physical_percent_complete is not None:
            task["physical_percent_complete"] = t.physical_percent_complete
        # stored, progress-aware Total Slack / Critical flag — preferred over recomputed CPM float
        # for Acumen parity (effective_total_float / is_effective_critical); MUST survive Save .json
        if t.stored_total_float_minutes is not None:
            task["stored_total_float_minutes"] = t.stored_total_float_minutes
        if t.stored_is_critical is not None:
            task["stored_is_critical"] = t.stored_is_critical
        if t.custom_fields:
            task["custom_fields"] = [[k, v] for k, v in t.custom_fields]
        if t.remaining_duration_minutes is not None:
            task["remaining_duration_minutes"] = t.remaining_duration_minutes
        if t.baseline_duration_minutes is not None:
            task["baseline_duration_minutes"] = t.baseline_duration_minutes
        if t.cost is not None:
            task["cost"] = t.cost
        if t.actual_cost is not None:
            task["actual_cost"] = t.actual_cost
        if t.budgeted_cost:
            task["budgeted_cost"] = t.budgeted_cost
        for field in _DATE_FIELDS:
            value = iso(getattr(t, field))
            if value is not None:
                task[field] = value
        if t.constraint_type is not ConstraintType.ASAP:
            task["constraint_type"] = str(t.constraint_type)
        out["tasks"].append(task)
    return json.dumps(out, indent=2)
