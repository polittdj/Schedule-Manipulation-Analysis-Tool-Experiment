"""Primavera P6 XER importer → the M2 domain model.

Parses a P6 ``.xer`` export into a frozen, UniqueID-keyed
:class:`~schedule_forensics.model.schedule.Schedule`. XER is a tab-delimited text
format: a ``%T`` line names a table, the following ``%F`` line names its columns,
each ``%R`` line is a data row (zipped positionally to the column names), and ``%E``
ends the file. Fields are read **by name**, never by position, so column reordering
is harmless. Only the standard library is used (the CUI egress guard stays green).

**UniqueID is the sole identity.** Tasks are keyed by ``task_id``; logic
(``TASKPRED``) and assignments (``TASKRSRC``) reference tasks by ``task_id`` only. A
relationship pointing at a ``task_id`` absent from the whole file is malformed and
raises :class:`ImporterError`; a relationship that merely crosses into a *different*
project in a multi-project export is out of scope and is excluded (not an error).

Deferred (ADR-0008, carried to a later milestone): per-task cost roll-up from
``TASKRSRC``/expenses and detailed ``CALENDAR`` parsing (the default 8h/Mon-Fri
calendar is used). The parity-critical ingestion path is MSPDI (from ``.mpp`` via
MPXJ, M4); XER is a secondary native format.
"""

from __future__ import annotations

import os
from collections import Counter

import pydantic

from schedule_forensics.importers._common import (
    ImporterError,
    hours_to_minutes,
    parse_datetime,
    parse_float,
    parse_percent,
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
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")  # legacy Windows P6 exports
    return parse_xer_text(text, source_file=os.path.basename(file_path))


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

    tasks = [
        _parse_task(row, wbs_short, wbs_parent, uids_by_task, names_by_task) for row in task_rows
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
            calendar=Calendar(),  # CALENDAR parsing deferred (ADR-0008)
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
) -> Task:
    task_id = _req_int(row, "task_id")
    task_type = _g(row, "task_type") or ""
    constraint = _g(row, "cstr_type")
    physical = _g(row, "phys_complete_pct")
    name = _g(row, "task_name") or _g(row, "task_code") or f"Task {task_id}"

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
            constraint_type=_CONSTRAINT_BY_XER.get(constraint or "", ConstraintType.ASAP),
            constraint_date=parse_datetime(_g(row, "cstr_date")),
            deadline=None,  # P6 deadlines are a secondary constraint (deferred)
            percent_complete=parse_percent(physical),
            physical_percent_complete=(
                parse_float(physical) if _g(row, "complete_pct_type") == "CP_Phys" else None
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


# --- relationships ----------------------------------------------------------------


def _parse_relationships(
    pred_rows: list[Row], all_task_ids: set[int], in_scope_ids: set[int]
) -> list[Relationship]:
    """``TASKPRED`` → :class:`Relationship` edges (UID-keyed).

    A reference to a ``task_id`` absent from the entire file is malformed → raise.
    A reference to a task in another project (present in ``all_task_ids`` but not
    ``in_scope_ids``) is out of scope → excluded (not an error).
    """
    relationships: list[Relationship] = []
    for row in pred_rows:
        successor = _req_int(row, "task_id")
        predecessor = _req_int(row, "pred_task_id")
        for endpoint in (successor, predecessor):
            if endpoint not in all_task_ids:
                raise ImporterError(
                    f"TASKPRED references task_id {endpoint}, which is not in the file"
                )
        if successor not in in_scope_ids or predecessor not in in_scope_ids:
            continue  # a cross-project link; out of scope for the selected project
        try:
            relationships.append(
                Relationship(
                    predecessor_id=predecessor,
                    successor_id=successor,
                    type=_RELATIONSHIP_BY_XER.get(_g(row, "pred_type") or "", RelationshipType.FS),
                    lag_minutes=hours_to_minutes(_g(row, "lag_hr_cnt")),
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(f"invalid logic link {predecessor}->{successor}: {exc}") from exc
    return relationships


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
