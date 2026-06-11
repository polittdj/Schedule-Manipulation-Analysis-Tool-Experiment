"""Primavera P6 XER importer → the M2 domain model.

Parses a P6 ``.xer`` export into a frozen, UniqueID-keyed
:class:`~schedule_forensics.model.schedule.Schedule`. XER is a tab-delimited text
format: a ``%T`` line names a table, the following ``%F`` line names its columns,
each ``%R`` line is a data row (zipped positionally to the column names), and ``%E``
ends the file. Fields are read **by name**, never by position, so column reordering
is harmless. Only the standard library is used (the CUI egress guard stays green).

**UniqueID is the sole identity.** Tasks are keyed by ``task_id``; logic
(``TASKPRED``) and assignments (``TASKRSRC``) reference tasks by ``task_id`` only.
Links the selected project cannot resolve — dangling endpoints (filtered/partial
exports), cross-project rows, self-references, duplicates — are valid real-world P6
states and are dropped with a count logged (the same tolerance classes as the MSPDI
importer; ALAP and dateless date-constraints likewise normalize to ASAP).

``TASKRSRC`` quantities drive the ``CP_Units`` percent complete (actual ÷ at-completion
units); the project's ``CALENDAR`` row drives the schedule calendar (work weekdays,
per-day minutes, holidays — ADR-0028). Deferred (ADR-0008, carried to a later
milestone): per-task cost roll-up from ``TASKRSRC``/expenses and per-task calendars
(the engine models one schedule-level calendar). The parity-critical ingestion path is
MSPDI (from ``.mpp`` via MPXJ, M4); XER is a secondary native format.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
from collections import Counter

import pydantic

from schedule_forensics.importers._common import (
    DATE_REQUIRING_CONSTRAINTS,
    ImporterError,
    clamped_percent_or_none,
    dominant_day_minutes,
    excel_serial_to_date,
    hours_to_minutes,
    parse_datetime,
    parse_float,
    parse_percent,
    weekday_from_source,
    working_span_minutes,
)
from schedule_forensics.model import (
    Calendar,
    ConstraintType,
    Relationship,
    RelationshipType,
    Resource,
    ResourceType,
    Schedule,
    Task,
)

logger = logging.getLogger("schedule_forensics.importers.xer")

Row = dict[str, str]
Tables = dict[str, list[Row]]

#: XER ``TASK.cstr_type`` enum → model constraint. SOURCE-PENDING (ADR-0008):
#: re-confirm against the live P6 object model at M4/M9.
_CONSTRAINT_BY_XER: dict[str, ConstraintType] = {
    "CS_ALAP": ConstraintType.ALAP,
    "CS_MSO": ConstraintType.MSO,  # Start On
    "CS_MEO": ConstraintType.MFO,  # Finish On
    "CS_MSOA": ConstraintType.SNET,  # Start On or After
    "CS_MSOB": ConstraintType.SNLT,  # Start On or Before
    "CS_MEOA": ConstraintType.FNET,  # Finish On or After
    "CS_MEOB": ConstraintType.FNLT,  # Finish On or Before
    "CS_MANDSTART": ConstraintType.MSO,  # Mandatory Start (hard)
    "CS_MANDFIN": ConstraintType.MFO,  # Mandatory Finish (hard)
}

#: XER ``TASKPRED.pred_type`` enum → model link type.
_RELATIONSHIP_BY_XER: dict[str, RelationshipType] = {
    "PR_FS": RelationshipType.FS,
    "PR_SS": RelationshipType.SS,
    "PR_FF": RelationshipType.FF,
    "PR_SF": RelationshipType.SF,
}

#: XER ``RSRC.rsrc_type`` enum → model resource type.
_RESOURCE_BY_XER: dict[str, ResourceType] = {
    "RT_Labor": ResourceType.WORK,
    "RT_Equip": ResourceType.WORK,
    "RT_Mat": ResourceType.MATERIAL,
}

_MILESTONE_TYPES = frozenset({"TT_Mile", "TT_FinMile"})


def parse_xer(path: str | os.PathLike[str]) -> Schedule:
    """Parse a P6 ``.xer`` file at ``path`` into a :class:`Schedule`.

    The file name becomes ``Schedule.source_file`` for citations. Raises
    :class:`ImporterError` on any malformed input.
    """
    file_path = os.fspath(path)
    try:
        with open(file_path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        raise ImporterError(f"cannot read XER file: {exc}") from exc
    return parse_xer_text(decode_xer_bytes(data), source_file=os.path.basename(file_path))


def decode_xer_bytes(data: bytes) -> str:
    """Decode raw XER bytes: BOM-tagged UTF-16 first, then UTF-8, then the legacy
    Windows cp1252 P6 exports. Shared by the file path and the web upload path so the
    same file can never parse differently depending on how it entered the tool."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def parse_xer_text(text: str, *, source_file: str | None = None) -> Schedule:
    """Parse an XER document already held as a string.

    Raises :class:`ImporterError` if the document has no usable ``PROJECT``/
    ``TASK`` data or does not form a valid schedule.
    """
    tables = _parse_tables(text)

    projects = tables.get("PROJECT", [])
    all_tasks = tables.get("TASK", [])
    project = _select_project(projects, all_tasks)
    proj_id = _g(project, "proj_id")

    if len(projects) > 1 and proj_id is not None:
        task_rows = [t for t in all_tasks if _g(t, "proj_id") == proj_id]
    else:
        task_rows = all_tasks

    project_start = parse_datetime(_g(project, "plan_start_date"))
    if project_start is None:
        raise ImporterError("XER PROJECT is missing a usable plan_start_date")

    wbs_short, wbs_parent = _wbs_index(tables.get("PROJWBS", []))
    resources = _parse_resources(tables.get("RSRC", []))
    resource_name_by_id = {r.unique_id: r.name for r in resources}
    uids_by_task, names_by_task = _parse_assignments(
        tables.get("TASKRSRC", []), resource_name_by_id
    )
    units_pct_by_task = _units_percent_by_task(tables.get("TASKRSRC", []))

    tasks = [
        _parse_task(row, wbs_short, wbs_parent, uids_by_task, names_by_task, units_pct_by_task)
        for row in task_rows
    ]
    all_task_ids = {_req_int(t, "task_id") for t in all_tasks}
    in_scope_ids = {t.unique_id for t in tasks}
    relationships = _parse_relationships(tables.get("TASKPRED", []), all_task_ids, in_scope_ids)

    try:
        return Schedule(
            name=_g(project, "proj_short_name") or proj_id or (source_file or "Untitled"),
            source_file=source_file,
            project_start=project_start,
            project_finish=parse_datetime(_g(project, "plan_end_date")),
            status_date=parse_datetime(_g(project, "last_recalc_date")),
            baseline_finish=None,  # P6 baseline lives in a separate project (deferred)
            calendar=_parse_project_calendar(tables, project),  # ADR-0028
            tasks=tuple(tasks),
            relationships=tuple(relationships),
            resources=tuple(resources),
        )
    except pydantic.ValidationError as exc:
        raise ImporterError(f"XER does not form a valid schedule: {exc}") from exc


# --- table parsing ----------------------------------------------------------------


def _parse_tables(text: str) -> Tables:
    """Split the ``%T/%F/%R/%E`` stream into ``{table_name: [row_dict, ...]}``."""
    tables: Tables = {}
    current: str | None = None
    fields: list[str] = []
    for line in text.splitlines():
        if not line:
            continue
        tokens = line.split("\t")
        tag = tokens[0]
        if tag == "%T":
            current = tokens[1] if len(tokens) > 1 else None
            fields = []
            if current is not None:
                tables.setdefault(current, [])
        elif tag == "%F":
            fields = tokens[1:]
        elif tag == "%R":
            if current is None:
                continue
            values = tokens[1:]
            tables[current].append(
                {field: (values[i] if i < len(values) else "") for i, field in enumerate(fields)}
            )
        elif tag == "%E":
            break
        # ERMHDR and any other leading token are ignored.
    return tables


def _g(row: Row, key: str) -> str | None:
    """Return ``row[key]`` stripped, or ``None`` when missing/blank."""
    value = row.get(key)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _req_int(row: Row, key: str) -> int:
    """Parse a required integer column; raise :class:`ImporterError` if absent/non-int."""
    raw = _g(row, key)
    if raw is None:
        raise ImporterError(f"XER row missing required integer column {key!r}")
    try:
        return int(raw)
    except ValueError as exc:
        raise ImporterError(f"expected an integer for {key!r}, got {raw!r}") from exc


def _opt_int(row: Row, key: str) -> int | None:
    """Parse an optional integer column; ``None`` if absent. Raises on non-int text."""
    raw = _g(row, key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ImporterError(f"expected an integer for {key!r}, got {raw!r}") from exc


def _opt_hours(row: Row, key: str) -> int | None:
    """Optional hour-count column → working minutes, or ``None`` when absent."""
    raw = _g(row, key)
    return None if raw is None else hours_to_minutes(raw)


def _select_project(projects: list[Row], task_rows: list[Row]) -> Row:
    """Pick the project to analyse: the only one, or the one owning the most tasks."""
    if not projects:
        raise ImporterError("XER has no PROJECT table")
    if len(projects) == 1:
        return projects[0]
    counts = Counter(_g(t, "proj_id") for t in task_rows)
    return max(projects, key=lambda p: counts.get(_g(p, "proj_id"), 0))


# --- WBS --------------------------------------------------------------------------


def _wbs_index(wbs_rows: list[Row]) -> tuple[dict[str, str], dict[str, str | None]]:
    """Index ``PROJWBS`` → (wbs_id → short name, wbs_id → parent wbs_id)."""
    short: dict[str, str] = {}
    parent: dict[str, str | None] = {}
    for row in wbs_rows:
        wbs_id = _g(row, "wbs_id")
        if wbs_id is None:
            continue
        short[wbs_id] = _g(row, "wbs_short_name") or _g(row, "wbs_name") or ""
        parent[wbs_id] = _g(row, "parent_wbs_id")
    return short, parent


def _wbs_path(
    wbs_id: str | None, short: dict[str, str], parent: dict[str, str | None]
) -> str | None:
    """Build a dotted root→leaf WBS path for ``wbs_id`` (cycle-safe), or ``None``."""
    if wbs_id is None or wbs_id not in short:
        return None
    segments: list[str] = []
    seen: set[str] = set()
    current: str | None = wbs_id
    while current is not None and current in short and current not in seen:
        seen.add(current)
        segment = short[current]
        if segment:
            segments.append(segment)
        current = parent.get(current)
    return ".".join(reversed(segments)) or None


# --- task -------------------------------------------------------------------------


def _parse_task(
    row: Row,
    wbs_short: dict[str, str],
    wbs_parent: dict[str, str | None],
    uids_by_task: dict[int, tuple[int, ...]],
    names_by_task: dict[int, tuple[str, ...]],
    units_pct_by_task: dict[int, float],
) -> Task:
    task_id = _req_int(row, "task_id")
    task_type = _g(row, "task_type") or ""
    constraint = _g(row, "cstr_type")
    physical = _g(row, "phys_complete_pct")
    name = _g(row, "task_name") or _g(row, "task_code") or f"Task {task_id}"
    constraint_type = _CONSTRAINT_BY_XER.get(constraint or "", ConstraintType.ASAP)
    constraint_date = parse_datetime(_g(row, "cstr_date"))
    # the same real-world normalization the MSPDI importer applies (Law 2): ALAP is out of
    # scope for the early-date engine, and a date-requiring constraint with the date
    # cleared is meaningless — both collapse to ASAP instead of refusing the schedule
    if constraint_type is ConstraintType.ALAP or (
        constraint_type in DATE_REQUIRING_CONSTRAINTS and constraint_date is None
    ):
        constraint_type = ConstraintType.ASAP
        constraint_date = None

    try:
        return Task(
            unique_id=task_id,
            name=name,
            wbs=_wbs_path(_g(row, "wbs_id"), wbs_short, wbs_parent),
            duration_minutes=hours_to_minutes(_g(row, "target_drtn_hr_cnt")),
            remaining_duration_minutes=_opt_hours(row, "remain_drtn_hr_cnt"),
            baseline_duration_minutes=None,  # P6 baseline duration is in a separate project
            is_milestone=task_type in _MILESTONE_TYPES,
            is_summary=task_type == "TT_WBS",
            is_level_of_effort=task_type == "TT_LOE",
            is_active=True,  # XER has no per-task active flag (status_code is progress)
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            deadline=None,  # P6 deadlines are a secondary constraint (deferred)
            percent_complete=_percent_complete(row, units_pct_by_task.get(task_id)),
            physical_percent_complete=(
                clamped_percent_or_none(physical)
                if _g(row, "complete_pct_type") == "CP_Phys"
                else None
            ),
            start=parse_datetime(_g(row, "early_start_date")),
            finish=parse_datetime(_g(row, "early_end_date")),
            actual_start=parse_datetime(_g(row, "act_start_date")),
            actual_finish=parse_datetime(_g(row, "act_end_date")),
            baseline_start=parse_datetime(_g(row, "target_start_date")),
            baseline_finish=parse_datetime(_g(row, "target_end_date")),
            resource_names=names_by_task.get(task_id, ()),
            resource_ids=uids_by_task.get(task_id, ()),
        )
    except pydantic.ValidationError as exc:
        raise ImporterError(f"task task_id {task_id} is invalid: {exc}") from exc


def _percent_complete(row: Row, units_pct: float | None = None) -> float:
    """P6 activity % complete honoring ``complete_pct_type``.

    ``phys_complete_pct`` only carries the user-maintained *physical* % — under the
    P6-default ``CP_Drtn`` it stays 0 while work progresses, so reading it universally
    imported finished work as "not started". Actual dates are facts and rule first:
    finished → 100, not started → 0. In between, ``CP_Phys`` reads the physical %,
    ``CP_Units`` reads the TASKRSRC quantity share (``units_pct``, actual ÷
    at-completion units) when the file carries quantities, and ``CP_Drtn`` — or any
    type left without a usable basis — derives duration % = (target - remaining) /
    target, with the physical % as the last fallback.
    """
    if _g(row, "act_end_date") is not None:
        return 100.0
    if _g(row, "act_start_date") is None:
        return 0.0
    pct_type = _g(row, "complete_pct_type") or "CP_Drtn"
    if pct_type == "CP_Phys":
        return parse_percent(_g(row, "phys_complete_pct"))
    if pct_type == "CP_Units" and units_pct is not None:
        return units_pct
    target = parse_float(_g(row, "target_drtn_hr_cnt"))
    remain = parse_float(_g(row, "remain_drtn_hr_cnt"))
    if not target or target <= 0 or remain is None:
        return parse_percent(_g(row, "phys_complete_pct"))
    return min(100.0, max(0.0, 100.0 * (1.0 - remain / target)))


# --- relationships ----------------------------------------------------------------


def _parse_relationships(
    pred_rows: list[Row], all_task_ids: set[int], in_scope_ids: set[int]
) -> list[Relationship]:
    """``TASKPRED`` → :class:`Relationship` edges (UID-keyed).

    Real exports (filtered or multi-project) carry rows this file cannot resolve:
    endpoints absent from the file entirely (an external/partial-export link), links
    into another project, self-referential rows, and duplicates. All are *valid P6
    states*, not corruption — they are dropped and logged by count (no CUI — numbers
    only), matching the MSPDI importer's tolerance classes.
    """
    relationships: list[Relationship] = []
    seen: set[tuple[int, int, RelationshipType]] = set()
    dropped = 0
    for row in pred_rows:
        successor = _req_int(row, "task_id")
        predecessor = _req_int(row, "pred_task_id")
        link_type = _RELATIONSHIP_BY_XER.get(_g(row, "pred_type") or "", RelationshipType.FS)
        key = (predecessor, successor, link_type)
        if (
            successor not in all_task_ids  # dangling endpoint (filtered/partial export)
            or predecessor not in all_task_ids
            or successor not in in_scope_ids  # cross-project link; out of scope
            or predecessor not in in_scope_ids
            or predecessor == successor  # self-referential row
            or key in seen  # duplicate TASKPRED row (would double-count DCMA edges)
        ):
            dropped += 1
            continue
        seen.add(key)
        try:
            relationships.append(
                Relationship(
                    predecessor_id=predecessor,
                    successor_id=successor,
                    type=link_type,
                    lag_minutes=hours_to_minutes(_g(row, "lag_hr_cnt")),
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(f"invalid logic link {predecessor}->{successor}: {exc}") from exc
    if dropped:
        logger.info(
            "dropped %d TASKPRED link(s) not resolvable within this project "
            "(external/cross-project, dangling, self-referential, or duplicate)",
            dropped,
        )
    return relationships


# --- calendar -----------------------------------------------------------------------

#: ``clndr_data`` day-of-week nodes look like ``(0||3()`` (3 = Tuesday; 1=Sun..7=Sat).
_CLNDR_DAY_RE = re.compile(r"\(0\|\|([1-7])\(\)")
#: One working-time span inside a day or exception node: ``s|08:00|f|17:00``.
_CLNDR_SPAN_RE = re.compile(r"s\|(\d{1,2}:\d{2})\|f\|(\d{1,2}:\d{2})")
#: An exception node: ``(0||N(d|45292)`` — ``d|`` carries the Excel serial day number.
_CLNDR_EXCEPTION_RE = re.compile(r"\(0\|\|\d+\(d\|(\d+)\)")


def _parse_project_calendar(tables: Tables, project: Row) -> Calendar:
    """The project's ``CALENDAR`` row → the model :class:`Calendar` (ADR-0028).

    ``PROJECT.clndr_id`` picks the row (fallback: the ``default_flag=Y`` row); the
    packed ``clndr_data`` yields the work weekdays, the dominant per-day working-minute
    total, and full non-working exception days (holidays). A row with no parseable day
    grid walks its ``base_clndr_id`` chain (cycle-safe), then falls back to
    ``day_hr_cnt``. The engine models ONE schedule-level calendar (per-task
    ``TASK.clndr_id`` calendars stay deferred). Any structural surprise degrades to
    the standard 8h/Mon-Fri default with a logged note — a bad calendar must never
    sink an otherwise valid schedule.
    """
    try:
        return _project_calendar(tables, project)
    except Exception:
        logger.warning("unreadable project calendar; using the standard 8h/Mon-Fri default")
        return Calendar()


def _project_calendar(tables: Tables, project: Row) -> Calendar:
    rows = tables.get("CALENDAR", [])
    if not rows:
        return Calendar()
    by_id = {cal_id: r for r in rows if (cal_id := _g(r, "clndr_id")) is not None}
    proj_cal_id = _g(project, "clndr_id")
    row = by_id.get(proj_cal_id) if proj_cal_id is not None else None
    if row is None:
        row = next((r for r in rows if (_g(r, "default_flag") or "").upper() == "Y"), None)
    if row is None:
        return Calendar()
    name = _g(row, "clndr_name") or "Standard"

    # the day grid comes from this row, else its base chain (cycle-safe)
    seen: set[str] = set()
    cursor: Row | None = row
    weekdays: set[int] = set()
    day_totals: list[int] = []
    holidays: set[dt.date] = set()
    while cursor is not None and (_g(cursor, "clndr_id") or "") not in seen:
        seen.add(_g(cursor, "clndr_id") or "")
        weekdays, day_totals, holidays = _parse_clndr_data(cursor.get("clndr_data") or "")
        if weekdays:
            break
        base_id = _g(cursor, "base_clndr_id")
        cursor = by_id.get(base_id) if base_id is not None else None

    if not weekdays:
        # no parseable day grid anywhere — day_hr_cnt is the only remaining signal
        hours = parse_float(_g(row, "day_hr_cnt"))
        if hours is not None and hours > 0:
            return Calendar(
                name=name, working_minutes_per_day=hours_to_minutes(_g(row, "day_hr_cnt"))
            )
        return Calendar(name=name)
    minutes_per_day = dominant_day_minutes(day_totals)
    if minutes_per_day is None:  # unreachable while weekdays implies positive totals
        return Calendar(name=name)
    return Calendar(
        name=name,
        working_minutes_per_day=minutes_per_day,
        work_weekdays=tuple(sorted(weekdays)),
        # a weekend holiday is a no-op for the engine; keep the model lean
        holidays=tuple(sorted(h for h in holidays if h.weekday() in weekdays)),
    )


def _parse_clndr_data(data: str) -> tuple[set[int], list[int], set[dt.date]]:
    """P6's packed ``clndr_data`` → (work weekdays, per-day minute totals, holidays).

    The format is a nested ``(0||key(params)(children))`` token tree; rather than a
    full grammar, anchored patterns read it positionally: day nodes ``(0||<1-7>()``
    own the ``s|HH:MM|f|HH:MM`` spans up to the next day node, and ``Exceptions``
    entries ``(0||N(d|<serial>)`` with **no** working span are full days off
    (holidays; a span means changed hours — outside the single-block model, skipped).
    Tolerant by construction: anything unrecognized contributes nothing.
    """
    exceptions_at = data.find("Exceptions")
    day_part = data if exceptions_at < 0 else data[:exceptions_at]
    exception_part = "" if exceptions_at < 0 else data[exceptions_at:]

    weekdays: set[int] = set()
    day_totals: list[int] = []
    day_marks = list(_CLNDR_DAY_RE.finditer(day_part))
    for i, mark in enumerate(day_marks):
        end = day_marks[i + 1].start() if i + 1 < len(day_marks) else len(day_part)
        spans = _CLNDR_SPAN_RE.findall(day_part[mark.end() : end])
        minutes = sum(working_span_minutes(start, finish) for start, finish in spans)
        weekday = weekday_from_source(int(mark.group(1)))
        if minutes <= 0 or weekday is None:
            continue  # a day node without a working span is a non-working day
        weekdays.add(weekday)
        day_totals.append(minutes)

    holidays: set[dt.date] = set()
    exception_marks = list(_CLNDR_EXCEPTION_RE.finditer(exception_part))
    for i, mark in enumerate(exception_marks):
        end = (
            exception_marks[i + 1].start() if i + 1 < len(exception_marks) else len(exception_part)
        )
        if _CLNDR_SPAN_RE.search(exception_part[mark.end() : end]):
            continue  # changed working hours, not a day off
        day = excel_serial_to_date(int(mark.group(1)))
        if day is not None:
            holidays.add(day)
    return weekdays, day_totals, holidays


# --- resources & assignments ------------------------------------------------------


def _parse_resources(rsrc_rows: list[Row]) -> list[Resource]:
    """``RSRC`` → :class:`Resource` list (rows without an id or name are skipped)."""
    resources: list[Resource] = []
    for row in rsrc_rows:
        rsrc_id = _opt_int(row, "rsrc_id")
        name = _g(row, "rsrc_name") or _g(row, "rsrc_short_name")
        if rsrc_id is None or name is None:
            continue
        try:
            resources.append(
                Resource(
                    unique_id=rsrc_id,
                    name=name,
                    type=_RESOURCE_BY_XER.get(_g(row, "rsrc_type") or "", ResourceType.WORK),
                    standard_rate=parse_float(_g(row, "cost_per_qty")),
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(f"resource rsrc_id {rsrc_id} is invalid: {exc}") from exc
    return resources


def _units_percent_by_task(taskrsrc_rows: list[Row]) -> dict[int, float]:
    """``TASKRSRC`` quantities → per-task units % complete (P6 "Units % Complete").

    Units % = actual ÷ at-completion units summed across the task's assignments, where
    actual = ``act_reg_qty`` + ``act_ot_qty`` and at-completion = actual + ``remain_qty``.
    Tasks with no parseable quantities (or zero at-completion units) are absent —
    :func:`_percent_complete` falls back to the duration share for those, so a file
    without quantities behaves exactly as before.
    """
    actual: dict[int, float] = {}
    remaining: dict[int, float] = {}
    for row in taskrsrc_rows:
        task_id = _opt_int(row, "task_id")
        if task_id is None:
            continue
        regular = parse_float(_g(row, "act_reg_qty"))
        overtime = parse_float(_g(row, "act_ot_qty"))
        remain = parse_float(_g(row, "remain_qty"))
        if regular is None and overtime is None and remain is None:
            continue  # an assignment with no quantities carries no progress signal
        actual[task_id] = actual.get(task_id, 0.0) + (regular or 0.0) + (overtime or 0.0)
        remaining[task_id] = remaining.get(task_id, 0.0) + (remain or 0.0)
    out: dict[int, float] = {}
    for task_id, act in actual.items():
        at_completion = act + remaining[task_id]
        if at_completion > 0:
            out[task_id] = min(100.0, max(0.0, 100.0 * act / at_completion))
    return out


def _parse_assignments(
    taskrsrc_rows: list[Row], resource_name_by_id: dict[int, str]
) -> tuple[dict[int, tuple[int, ...]], dict[int, tuple[str, ...]]]:
    """``TASKRSRC`` → per-task resource UID and name tuples (order-preserving)."""
    uids_by_task: dict[int, list[int]] = {}
    names_by_task: dict[int, list[str]] = {}
    for row in taskrsrc_rows:
        task_id = _opt_int(row, "task_id")
        rsrc_id = _opt_int(row, "rsrc_id")
        if task_id is None or rsrc_id is None:
            continue
        uids = uids_by_task.setdefault(task_id, [])
        if rsrc_id not in uids:
            uids.append(rsrc_id)
        name = resource_name_by_id.get(rsrc_id)
        if name is not None:
            names = names_by_task.setdefault(task_id, [])
            if name not in names:
                names.append(name)
    return (
        {uid: tuple(v) for uid, v in uids_by_task.items()},
        {uid: tuple(v) for uid, v in names_by_task.items()},
    )
