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
reference endpoints by ``UID`` only. A duplicate UID makes the schedule *unconstructable*
(the model validators raise) → :class:`ImporterError`.

**Real-world tolerance (matching the XER importer):** a genuine MS Project export carries
constructs the curated parity files never do — **external / cross-project predecessor
links** (to a master/sub-project UID not in this file), self-referential or duplicate
links, **ALAP** constraints (out of scope for the early-date CPM), and date-requiring
constraints with the date cleared. These are *valid* schedule states, not corruption, so
they are normalized on import (links dropped, those constraints collapsed to ASAP) and
logged by count — never silently changing a parity-relevant value of a well-formed file.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import xml.etree.ElementTree as ET  # nosec B405  # hardened below: DTD/entity decls rejected
from decimal import Decimal

import pydantic

from schedule_forensics.importers._common import (
    DATE_REQUIRING_CONSTRAINTS,
    ImporterError,
    clamped_percent_or_none,
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

logger = logging.getLogger("schedule_forensics.importers.mspdi")

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

#: MSPDI ``LinkLag`` is stored in tenths of a minute for time-unit ``LagFormat``s, so
#: ``LinkLag / 10`` is working minutes directly. For the PERCENT formats (19 / elapsed
#: 20) it is stored in tenths of a percent of the PREDECESSOR's duration instead —
#: ``FS+25%`` arrives as ``LinkLag=250, LagFormat=19``.
_LINKLAG_TENTHS_PER_MINUTE = Decimal(10)
_PERCENT_LAG_FORMATS = frozenset({19, 20})


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
    raw_links: list[tuple[int, ET.Element]] = []
    tasks_el = root.find("Tasks")
    for task_el in [] if tasks_el is None else tasks_el.findall("Task"):
        if _text(task_el, "IsNull") == "1":
            continue  # an explicitly null placeholder row (not a real activity)
        task = _parse_task(task_el, assigned_uids_by_task, assigned_names_by_task)
        tasks.append(task)
        raw_links.extend((task.unique_id, el) for el in task_el.findall("PredecessorLink"))

    # links resolve after all tasks parse: a percent lag is a share of the PREDECESSOR's
    # duration, and predecessors can appear later in the file than their successors
    durations = {t.unique_id: t.duration_minutes for t in tasks}
    relationships = _in_file_links(_build_links(raw_links, durations), {t.unique_id for t in tasks})

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
    """MSPDI boolean; absent → ``default``. MS Project writes ``"1"``/``"0"`` but
    xsd:boolean also admits ``"true"``/``"false"``, which third-party exporters use."""
    raw = _text(parent, tag)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true"}


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
    constraint_date = parse_datetime(_text(task_el, "ConstraintDate"))
    # Normalize two valid-but-unschedulable real-world constraint states the curated parity
    # files never contain (the CPM engine would otherwise refuse the whole schedule, Law 2):
    #   * ALAP — as-late-as-possible is out of scope for this early-date engine;
    #   * a date-requiring constraint whose date is missing/sentinel — meaningless.
    # Both collapse to ASAP (no constraint). ALAP/SNET/etc. are not "Hard Constraints" unless
    # dated, so the DCMA §B counts are unaffected for well-formed schedules.
    if constraint_type is ConstraintType.ALAP or (
        constraint_type in DATE_REQUIRING_CONSTRAINTS and constraint_date is None
    ):
        constraint_type = ConstraintType.ASAP
        constraint_date = None
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
            constraint_date=constraint_date,
            deadline=parse_datetime(_text(task_el, "Deadline")),
            percent_complete=parse_percent(_text(task_el, "PercentComplete")),
            physical_percent_complete=clamped_percent_or_none(
                _text(task_el, "PhysicalPercentComplete")
            ),
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
        # the BAC basis cannot be negative (EV is never earned against a negative budget);
        # a negative baseline cost (a credit) clamps to 0 rather than rejecting the file
        max(0.0, cost) if cost is not None else 0.0,
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


def _build_links(
    raw_links: list[tuple[int, ET.Element]], pred_durations: dict[int, int]
) -> list[Relationship]:
    """``(successor_uid, <PredecessorLink>)`` pairs → :class:`Relationship` edges."""
    links: list[Relationship] = []
    for successor_uid, link_el in raw_links:
        predecessor_uid = _int(link_el, "PredecessorUID")
        if predecessor_uid is None:
            raise ImporterError(
                f"a <PredecessorLink> on task {successor_uid} has no <PredecessorUID>"
            )
        if predecessor_uid == successor_uid:
            continue  # a self-referential link is meaningless; drop it (the model forbids it)
        type_code = _int(link_el, "Type")
        link_type = _RELATIONSHIP_BY_CODE.get(
            1 if type_code is None else type_code, RelationshipType.FS
        )
        if _int(link_el, "LagFormat") in _PERCENT_LAG_FORMATS:
            lag = _percent_lag_to_minutes(
                _text(link_el, "LinkLag"), pred_durations.get(predecessor_uid, 0)
            )
        else:
            lag = _link_lag_to_minutes(_text(link_el, "LinkLag"))
        try:
            links.append(
                Relationship(
                    predecessor_id=predecessor_uid,
                    successor_id=successor_uid,
                    type=link_type,
                    lag_minutes=lag,
                )
            )
        except pydantic.ValidationError as exc:
            raise ImporterError(
                f"invalid logic link {predecessor_uid}->{successor_uid}: {exc}"
            ) from exc
    return links


def _in_file_links(relationships: list[Relationship], task_uids: set[int]) -> list[Relationship]:
    """Keep only logic links whose endpoints are both activities in *this* file.

    Real MS Project exports carry **external / cross-project** predecessor links (to a
    master or sub-project's UID) and occasional self-referential or duplicate links. The
    CPM engine already ignores edges whose endpoints are outside the task set, but the
    strict :class:`Schedule` model would reject the whole schedule — so a single external
    link sank an otherwise valid file. We drop those links here (matching the XER
    importer's existing cross-project handling) and log the count (no CUI — a number only).
    """
    kept: list[Relationship] = []
    seen: set[tuple[int, int, RelationshipType]] = set()
    dropped = 0
    for r in relationships:
        key = (r.predecessor_id, r.successor_id, r.type)
        if (
            r.predecessor_id not in task_uids
            or r.successor_id not in task_uids
            or r.predecessor_id == r.successor_id
            or key in seen
        ):
            dropped += 1
            continue
        seen.add(key)
        kept.append(r)
    if dropped:
        logger.info(
            "dropped %d logic link(s) not resolvable within this file "
            "(external/cross-project, self-referential, or duplicate)",
            dropped,
        )
    return kept


def _link_lag_to_minutes(value: str | None) -> int:
    """MSPDI ``LinkLag`` (tenths of a minute, sign preserved) → working minutes."""
    tenths = _lag_tenths(value)
    return int((tenths / _LINKLAG_TENTHS_PER_MINUTE).to_integral_value(rounding="ROUND_HALF_UP"))


def _percent_lag_to_minutes(value: str | None, pred_duration_minutes: int) -> int:
    """``LinkLag`` under a percent ``LagFormat`` (tenths of a percent of the predecessor's
    duration, sign preserved) → working minutes. ``FS+25%`` on a 10-day predecessor is
    1 200 minutes, not the 25 "minutes" a tenths-of-a-minute reading would fabricate."""
    tenths_of_pct = _lag_tenths(value)
    share = tenths_of_pct / Decimal(1000)  # tenths of a percent -> fraction
    return int((share * pred_duration_minutes).to_integral_value(rounding="ROUND_HALF_UP"))


def _lag_tenths(value: str | None) -> Decimal:
    if value is None or not value.strip():
        return Decimal(0)
    try:
        tenths = Decimal(value.strip())
    except (ValueError, ArithmeticError) as exc:
        raise ImporterError(f"unparseable <LinkLag>: {value!r}") from exc
    return tenths if tenths.is_finite() else Decimal(0)  # NaN/Infinity are data noise


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
