"""MSPDI (MS Project Data Interchange XML) importer → the M2 domain model.

Parses a Microsoft Project ``.xml`` (MSPDI) document into a frozen, UniqueID-keyed
:class:`~schedule_forensics.model.schedule.Schedule`. This is the parity-critical
ingestion path: at M4 the vendored MPXJ runner converts native ``.mpp`` to MSPDI and
feeds it straight through here, so every field the DCMA/EVM/forensic metrics read has
a typed home (M5-M11). No conversion, no network — only the standard-library
``xml.etree.ElementTree`` parser (the CUI egress guard stays green).

**Security:** MSPDI files arrive from outside the tool (CUI), so before parsing we
reject any document carrying a DTD or entity declaration — the precondition for both
XXE and "billion laughs" expansion — making the stdlib parser safe on untrusted input
(see ADR-0008).

**UniqueID is the sole identity.** Tasks/resources are keyed by ``UID``; relationships
reference endpoints by ``UID`` only. A dangling or self-referential link, or a
duplicate UID, makes the schedule *unconstructable* (the model validators raise) and is
surfaced as :class:`ImporterError` — never silently dropped.
"""

from __future__ import annotations

import datetime as dt
import os
import xml.etree.ElementTree as ET  # nosec B405  # hardened below: DTD/entity decls rejected
from decimal import Decimal

import pydantic

from schedule_forensics.importers._common import (
    ImporterError,
    iso_duration_to_minutes,
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

# --- source enum maps (MS Project standard codes) ---------------------------------

#: MSPDI ``Task/ConstraintType`` numeric code → model constraint.
_CONSTRAINT_BY_CODE: dict[int, ConstraintType] = {
    0: ConstraintType.ASAP,
    1: ConstraintType.ALAP,
    2: ConstraintType.MSO,
    3: ConstraintType.MFO,
    4: ConstraintType.SNET,
    5: ConstraintType.SNLT,
    6: ConstraintType.FNET,
    7: ConstraintType.FNLT,
}

#: MSPDI ``PredecessorLink/Type`` numeric code → model link type.
_RELATIONSHIP_BY_CODE: dict[int, RelationshipType] = {
    0: RelationshipType.FF,
    1: RelationshipType.FS,
    2: RelationshipType.SF,
    3: RelationshipType.SS,
}

#: MSPDI ``Resource/Type`` numeric code → model resource type.
#: SOURCE-PENDING (ADR-0008): confirm against a real export at M4/M9.
_RESOURCE_BY_CODE: dict[int, ResourceType] = {
    0: ResourceType.MATERIAL,
    1: ResourceType.WORK,
    2: ResourceType.COST,
}

#: MSPDI ``LinkLag`` is stored in tenths of a minute (``LagFormat`` only governs the
#: *displayed* unit, not storage), so ``LinkLag / 10`` is working minutes directly.
#: SOURCE-PENDING (ADR-0008): re-confirm against a real export at M4/M9.
_LINKLAG_TENTHS_PER_MINUTE = Decimal(10)


def parse_mspdi(path: str | os.PathLike[str]) -> Schedule:
    """Parse an MSPDI ``.xml`` file at ``path`` into a :class:`Schedule`.

    The file name (not its path) becomes ``Schedule.source_file`` for citations.
    Raises :class:`ImporterError` on any malformed input.
    """
    file_path = os.fspath(path)
    try:
        with open(file_path, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        raise ImporterError(f"cannot read MSPDI file: {exc}") from exc
    text = data.decode("utf-8-sig", errors="replace")
    return parse_mspdi_text(text, source_file=os.path.basename(file_path))


def parse_mspdi_text(text: str, *, source_file: str | None = None) -> Schedule:
    """Parse an MSPDI document already held as a string.

    ``source_file`` is recorded on the schedule for citations. Raises
    :class:`ImporterError` if the document is not well-formed MSPDI or does not
    form a valid schedule.
    """
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ImporterError("MSPDI with a DTD or entity declaration is rejected (XXE defense)")
    try:
        root = ET.fromstring(text)  # nosec B314  # DTD/entity decls rejected above
    except ET.ParseError as exc:
        raise ImporterError(f"malformed MSPDI XML: {exc}") from exc
    _strip_namespaces(root)
    if root.tag != "Project":
        raise ImporterError(
            f"not an MSPDI document (root element is {root.tag!r}, expected 'Project')"
        )

    project_start = parse_datetime(_text(root, "StartDate"))
    if project_start is None:
        raise ImporterError("MSPDI is missing a usable Project/StartDate")

    resources = _parse_resources(root)
    resource_name_by_uid = {res.unique_id: res.name for res in resources}
    assigned_uids_by_task, assigned_names_by_task = _parse_assignments(root, resource_name_by_uid)

    tasks: list[Task] = []
    relationships: list[Relationship] = []
    tasks_el = root.find("Tasks")
    for task_el in [] if tasks_el is None else tasks_el.findall("Task"):
        if _text(task_el, "IsNull") == "1":
            continue  # an explicitly null placeholder row (not a real activity)
        task = _parse_task(task_el, assigned_uids_by_task, assigned_names_by_task)
        tasks.append(task)
        relationships.extend(_parse_predecessor_links(task_el, task.unique_id))

    project_finish = parse_datetime(_text(root, "FinishDate"))
    status_date = parse_datetime(_text(root, "StatusDate"))
    baseline_finish = _project_baseline_finish(root)
    name = _text(root, "Title") or _text(root, "Name") or (source_file or "Untitled")

    try:
        return Schedule(
            name=name,
            source_file=source_file,
            project_start=project_start,
            project_finish=project_finish,
            status_date=status_date,
            baseline_finish=baseline_finish,
            calendar=Calendar(),  # calendar parsing deferred (ADR-0008); default 8h Mon-Fri
            tasks=tuple(tasks),
            relationships=tuple(relationships),
            resources=tuple(resources),
        )
    except pydantic.ValidationError as exc:
        raise ImporterError(f"MSPDI does not form a valid schedule: {exc}") from exc


# --- element helpers --------------------------------------------------------------


def _strip_namespaces(root: ET.Element) -> None:
    """Drop the ``{http://schemas.microsoft.com/project}`` prefix from every tag."""
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _text(parent: ET.Element, tag: str) -> str | None:
    """Return the stripped text of the first ``tag`` child, or ``None`` if absent/empty."""
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    stripped = child.text.strip()
    return stripped or None


def _int(parent: ET.Element, tag: str) -> int | None:
    """Parse an integer child element; ``None`` if absent. Raises on non-integer text."""
    raw = _text(parent, tag)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ImporterError(f"expected an integer for <{tag}>, got {raw!r}") from exc


def _bool(parent: ET.Element, tag: str, *, default: bool) -> bool:
    """MSPDI boolean (``"1"``/``"0"``); absent → ``default``."""
    raw = _text(parent, tag)
    if raw is None:
        return default
    return raw == "1"


# --- task ------------------------------------------------------------------------


def _parse_task(
    task_el: ET.Element,
    assigned_uids_by_task: dict[int, tuple[int, ...]],
    assigned_names_by_task: dict[int, tuple[str, ...]],
) -> Task:
    uid = _int(task_el, "UID")
    if uid is None:
        raise ImporterError("a <Task> has no <UID> (UniqueID is the required identity key)")

    constraint_code = _int(task_el, "ConstraintType")
    constraint_type = _CONSTRAINT_BY_CODE.get(constraint_code or 0, ConstraintType.ASAP)
    bl_start, bl_finish, bl_cost, bl_duration = _primary_baseline(task_el)

    try:
        return Task(
            unique_id=uid,
            name=_text(task_el, "Name") or f"Task {uid}",
            wbs=_text(task_el, "WBS"),
            duration_minutes=iso_duration_to_minutes(_text(task_el, "Duration")),
            remaining_duration_minutes=_optional_minutes(task_el, "RemainingDuration"),
            baseline_duration_minutes=bl_duration,
            is_milestone=_bool(task_el, "Milestone", default=False),
            is_summary=_bool(task_el, "Summary", default=False) or uid == 0,
            is_level_of_effort=False,  # not represented in MSPDI (ADR-0008)
            is_active=_bool(task_el, "Active", default=True),
            constraint_type=constraint_type,
            constraint_date=parse_datetime(_text(task_el, "ConstraintDate")),
            deadline=parse_datetime(_text(task_el, "Deadline")),
            percent_complete=parse_percent(_text(task_el, "PercentComplete")),
            physical_percent_complete=parse_float(_text(task_el, "PhysicalPercentComplete")),
            start=parse_datetime(_text(task_el, "Start")),
            finish=parse_datetime(_text(task_el, "Finish")),
            actual_start=parse_datetime(_text(task_el, "ActualStart")),
            actual_finish=parse_datetime(_text(task_el, "ActualFinish")),
            baseline_start=bl_start,
            baseline_finish=bl_finish,
            cost=parse_float(_text(task_el, "Cost")),
            actual_cost=parse_float(_text(task_el, "ActualCost")),
            budgeted_cost=bl_cost,
            resource_names=assigned_names_by_task.get(uid, ()),
            resource_ids=assigned_uids_by_task.get(uid, ()),
        )
    except pydantic.ValidationError as exc:
        raise ImporterError(f"task UID {uid} is invalid: {exc}") from exc


def _optional_minutes(parent: ET.Element, tag: str) -> int | None:
    """ISO-8601 duration child → minutes, or ``None`` when the element is absent."""
    raw = _text(parent, tag)
    return None if raw is None else iso_duration_to_minutes(raw)


def _primary_baseline(
    task_el: ET.Element,
) -> tuple[dt.datetime | None, dt.datetime | None, float, int | None]:
    """Pick the primary baseline (``Number == 0``, else the first) → start/finish/cost/duration.

    Baseline cost is the budget-at-completion (BAC) basis for EVM; absent → ``0.0``
    (the model's ``budgeted_cost`` default; never fabricated).
    """
    chosen: ET.Element | None = None
    for bl in task_el.findall("Baseline"):
        if _text(bl, "Number") == "0":
            chosen = bl
            break
        if chosen is None:
            chosen = bl
    if chosen is None:
        return None, None, 0.0, None
    cost = parse_float(_text(chosen, "Cost"))
    duration = _optional_minutes(chosen, "Duration")
    return (
        parse_datetime(_text(chosen, "Start")),
        parse_datetime(_text(chosen, "Finish")),
        0.0 if cost is None else cost,
        duration,
    )


def _project_baseline_finish(root: ET.Element) -> dt.datetime | None:
    """Latest non-summary task baseline finish — the project baseline finish (CPLI basis)."""
    tasks_el = root.find("Tasks")
    finishes: list[dt.datetime] = []
    for task_el in [] if tasks_el is None else tasks_el.findall("Task"):
        if _bool(task_el, "Summary", default=False):
            continue
        _, bl_finish, _, _ = _primary_baseline(task_el)
        if bl_finish is not None:
            finishes.append(bl_finish)
    return max(finishes) if finishes else None


# --- relationships ---------------------------------------------------------------


def _parse_predecessor_links(task_el: ET.Element, successor_uid: int) -> list[Relationship]:
    """A task's ``<PredecessorLink>`` children → incoming :class:`Relationship` edges."""
    links: list[Relationship] = []
    for link_el in task_el.findall("PredecessorLink"):
        predecessor_uid = _int(link_el, "PredecessorUID")
        if predecessor_uid is None:
            raise ImporterError(
                f"a <PredecessorLink> on task {successor_uid} has no <PredecessorUID>"
            )
        type_code = _int(link_el, "Type")
        link_type = _RELATIONSHIP_BY_CODE.get(
            1 if type_code is None else type_code, RelationshipType.FS
        )
        try:
            links.append(
                Relationship(
                    predecessor_id=predecessor_uid,
                    successor_id=successor_uid,
                    type=link_type,
                    lag_minutes=_link_lag_to_minutes(_text(link_el, "LinkLag")),
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(
                f"invalid logic link {predecessor_uid}->{successor_uid}: {exc}"
            ) from exc
    return links


def _link_lag_to_minutes(value: str | None) -> int:
    """MSPDI ``LinkLag`` (tenths of a minute, sign preserved) → working minutes."""
    if value is None or not value.strip():
        return 0
    try:
        tenths = Decimal(value.strip())
    except (ValueError, ArithmeticError) as exc:
        raise ImporterError(f"unparseable <LinkLag>: {value!r}") from exc
    return int((tenths / _LINKLAG_TENTHS_PER_MINUTE).to_integral_value(rounding="ROUND_HALF_UP"))


# --- resources & assignments -----------------------------------------------------


def _parse_resources(root: ET.Element) -> list[Resource]:
    """``Project/Resources/Resource`` → :class:`Resource` list (blank-name rows skipped)."""
    resources: list[Resource] = []
    resources_el = root.find("Resources")
    for res_el in [] if resources_el is None else resources_el.findall("Resource"):
        uid = _int(res_el, "UID")
        name = _text(res_el, "Name")
        if uid is None or name is None:
            continue  # the UID-0 / unnamed placeholder resource MS Project always emits
        type_code = _int(res_el, "Type")
        try:
            resources.append(
                Resource(
                    unique_id=uid,
                    name=name,
                    type=_RESOURCE_BY_CODE.get(
                        1 if type_code is None else type_code, ResourceType.WORK
                    ),
                    is_generic=_bool(res_el, "IsGeneric", default=False),
                    max_units=parse_float(_text(res_el, "MaxUnits")),
                    standard_rate=parse_float(_text(res_el, "StandardRate")),
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(f"resource UID {uid} is invalid: {exc}") from exc
    return resources


def _parse_assignments(
    root: ET.Element, resource_name_by_uid: dict[int, str]
) -> tuple[dict[int, tuple[int, ...]], dict[int, tuple[str, ...]]]:
    """``Project/Assignments`` → per-task resource UID and name tuples (order-preserving)."""
    uids_by_task: dict[int, list[int]] = {}
    names_by_task: dict[int, list[str]] = {}
    assignments_el = root.find("Assignments")
    for assign_el in [] if assignments_el is None else assignments_el.findall("Assignment"):
        task_uid = _int(assign_el, "TaskUID")
        resource_uid = _int(assign_el, "ResourceUID")
        if task_uid is None or resource_uid is None or resource_uid < 0:
            continue
        uids = uids_by_task.setdefault(task_uid, [])
        if resource_uid not in uids:
            uids.append(resource_uid)
        name = resource_name_by_uid.get(resource_uid)
        if name is not None:
            names = names_by_task.setdefault(task_uid, [])
            if name not in names:
                names.append(name)
    return (
        {uid: tuple(v) for uid, v in uids_by_task.items()},
        {uid: tuple(v) for uid, v in names_by_task.items()},
    )
