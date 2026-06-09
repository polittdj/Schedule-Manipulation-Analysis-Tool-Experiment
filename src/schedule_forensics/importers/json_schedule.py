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
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.task import ConstraintType, Task

_DATE_FIELDS = (
    ("start", "start"),
    ("finish", "finish"),
    ("actual_start", "actual_start"),
    ("actual_finish", "actual_finish"),
    ("baseline_start", "baseline_start"),
    ("baseline_finish", "baseline_finish"),
    ("constraint_date", "constraint_date"),
    ("deadline", "deadline"),
)


def _dt(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ImporterError(f"invalid datetime in JSON schedule: {value!r}") from exc


def parse_json(path: str | os.PathLike[str]) -> Schedule:
    """Parse a ``.json`` schedule file."""
    return parse_json_text(Path(os.fspath(path)).read_text(encoding="utf-8"))


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
    hours = raw.get("hours_per_day")
    wmpd = int(hours * 60) if hours else int(raw.get("working_minutes_per_day", 480))
    weekdays = raw.get("work_weekdays")
    kwargs: dict[str, Any] = {
        "name": str(raw.get("name", "Standard")),
        "working_minutes_per_day": wmpd,
    }
    if weekdays:
        kwargs["work_weekdays"] = tuple(int(d) for d in weekdays)
    return Calendar(**kwargs)


def _task(raw: dict[str, Any]) -> Task:
    fields: dict[str, Any] = {
        "unique_id": int(raw["unique_id"]),
        "name": str(raw.get("name", f"Task {raw['unique_id']}")),
        "duration_minutes": int(raw.get("duration_minutes", 0)),
    }
    for key in ("wbs", "is_milestone", "is_summary", "percent_complete", "resource_names"):
        if key in raw and raw[key] is not None:
            fields[key] = raw[key]
    for key in ("remaining_duration_minutes", "baseline_duration_minutes"):
        if raw.get(key) is not None:
            fields[key] = int(raw[key])
    for src, dest in _DATE_FIELDS:
        if raw.get(src) is not None:
            fields[dest] = _dt(raw[src])
    if raw.get("constraint_type"):
        fields["constraint_type"] = ConstraintType(str(raw["constraint_type"]))
    if isinstance(fields.get("resource_names"), list):
        fields["resource_names"] = tuple(str(r) for r in fields["resource_names"])
    return Task(**fields)


def _relationship(pred: int, succ: int, raw: dict[str, Any] | None = None) -> Relationship:
    raw = raw or {}
    return Relationship(
        predecessor_id=pred,
        successor_id=succ,
        type=RelationshipType(str(raw.get("type", "FS"))),
        lag_minutes=int(raw.get("lag_minutes", 0)),
    )


def _from_friendly(data: dict[str, Any]) -> Schedule:
    calendars = [_calendar(c) for c in data.get("calendars", []) if isinstance(c, dict)]
    tasks = [_task(t) for t in data["tasks"]]
    rels: list[Relationship] = []
    for r in data.get("relationships", []):
        rels.append(_relationship(int(r["predecessor_id"]), int(r["successor_id"]), r))
    # task-level predecessors: [2] or [{"id": 2, "type": "FS", "lag_minutes": 0}]
    for t in data["tasks"]:
        for p in t.get("predecessors", []) or []:
            if isinstance(p, dict):
                pred_id = p.get("id", p.get("predecessor_id"))
                if pred_id is None:
                    raise ImporterError("task predecessor entry needs an 'id' or 'predecessor_id'")
                rels.append(_relationship(int(pred_id), int(t["unique_id"]), p))
            else:
                rels.append(_relationship(int(p), int(t["unique_id"])))
    schedule_kwargs: dict[str, Any] = {
        "name": str(data.get("name", "Schedule")),
        "project_start": _dt(data.get("project_start")) or dt.datetime(2025, 1, 6, 8, 0),
        "tasks": tuple(tasks),
        "relationships": tuple(rels),
    }
    if data.get("status_date"):
        schedule_kwargs["status_date"] = _dt(data["status_date"])
    if calendars:
        schedule_kwargs["calendar"] = calendars[0]
        schedule_kwargs["calendars"] = tuple(calendars)
    return Schedule(**schedule_kwargs)


def to_json_text(schedule: Schedule) -> str:
    """Serialize a schedule to the friendly JSON format (for 'Save .json'); re-openable."""

    def iso(value: dt.datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    cal = schedule.calendar
    out: dict[str, Any] = {
        "name": schedule.name,
        "project_start": schedule.project_start.isoformat(),
        "calendars": [{"name": cal.name, "hours_per_day": cal.working_minutes_per_day / 60}],
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
    for t in schedule.tasks:
        task: dict[str, Any] = {
            "unique_id": t.unique_id,
            "name": t.name,
            "duration_minutes": t.duration_minutes,
        }
        if t.percent_complete:
            task["percent_complete"] = t.percent_complete
        if t.resource_names:
            task["resource_names"] = list(t.resource_names)
        for src, _dest in _DATE_FIELDS:
            value = iso(getattr(t, src))
            if value is not None:
                task[src] = value
        if t.constraint_type is not ConstraintType.ASAP:
            task["constraint_type"] = str(t.constraint_type)
        out["tasks"].append(task)
    return json.dumps(out, indent=2)
