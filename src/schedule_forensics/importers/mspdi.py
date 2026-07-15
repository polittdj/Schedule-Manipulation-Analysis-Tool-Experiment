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
    dominant_day_minutes,
    iso_duration_to_minutes,
    parse_datetime,
    parse_float,
    parse_percent,
    weekday_from_source,
    working_time_span,
)
from schedule_forensics.model import (
    Assignment,
    Calendar,
    ConstraintType,
    Relationship,
    RelationshipType,
    Resource,
    ResourceType,
    Schedule,
    Task,
)
from schedule_forensics.model.units import MINUTES_PER_DAY

logger = logging.getLogger("schedule_forensics.importers.mspdi")

# --- source enum maps (MS Project standard codes) ---------------------------------

#: MSPDI ``Task/DurationFormat`` codes meaning ELAPSED time (em/eh/ed/ew/emo/e%,
#: plus their "?" estimated variants) — wall-clock durations that ignore calendars.
_ELAPSED_DURATION_FORMATS = frozenset({4, 6, 8, 10, 12, 20, 36, 38, 40, 42, 44, 52})

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
    assigned_uids_by_task, assigned_names_by_task, assignments_by_task = _parse_assignments(
        root, resource_name_by_uid
    )
    ext_defs = _parse_extended_attribute_defs(root)
    raw_name_map = _parse_extended_attribute_raw_names(root)

    tasks: list[Task] = []
    raw_links: list[tuple[int, ET.Element]] = []
    tasks_el = root.find("Tasks")
    for task_el in [] if tasks_el is None else tasks_el.findall("Task"):
        if _text(task_el, "IsNull") == "1":
            continue  # an explicitly null placeholder row (not a real activity)
        task = _parse_task(
            task_el, assigned_uids_by_task, assigned_names_by_task, assignments_by_task, ext_defs
        )
        tasks.append(task)
        raw_links.extend((task.unique_id, el) for el in task_el.findall("PredecessorLink"))

    # the selectable custom fields: those actually populated on ≥1 task, in project-declared order
    # (so the picker shows only fields with data, not every empty Text/Number slot the file holds).
    populated = {label for t in tasks for label, _ in t.custom_fields}
    custom_field_labels = tuple(
        dict.fromkeys(label for label in ext_defs.values() if label in populated)
    )

    # links resolve after all tasks parse: a percent lag is a share of the PREDECESSOR's
    # duration, and predecessors can appear later in the file than their successors
    durations = {t.unique_id: t.duration_minutes for t in tasks}
    relationships = _in_file_links(_build_links(raw_links, durations), {t.unique_id for t in tasks})

    project_finish = parse_datetime(_text(root, "FinishDate"))
    status_date = parse_datetime(_text(root, "StatusDate"))
    baseline_finish = _project_baseline_finish(root)
    # the real document Title (for grouping files into Projects) — None when the file carries none,
    # kept distinct from ``name`` which falls back to <Name>/filename
    project_title = _text(root, "Title")
    name = project_title or _text(root, "Name") or (source_file or "Untitled")

    try:
        return Schedule(
            name=name,
            project_title=project_title,
            source_file=source_file,
            project_start=project_start,
            project_finish=project_finish,
            status_date=status_date,
            baseline_finish=baseline_finish,
            calendar=_parse_project_calendar(root),  # ADR-0028; defaults on any surprise
            calendars=parse_calendar_registry(root, tuple(tasks)),  # per-task cals (ADR-0118)
            tasks=tuple(tasks),
            relationships=tuple(relationships),
            resources=tuple(resources),
            custom_field_labels=custom_field_labels,
            custom_field_by_raw_name=tuple(raw_name_map.items()),
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


def _cosmetic_int(parent: ET.Element, tag: str, default: int) -> int:
    """Parse an integer for a **cosmetic-only** field (e.g. OutlineLevel — Gantt indentation).

    A non-integer in such a field must NOT refuse the whole file (audit L7): the value is purely
    presentational, so a malformed entry falls back to ``default``. Identity / structural fields
    keep the loud :func:`_int` that raises."""
    raw = _text(parent, tag)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool(parent: ET.Element, tag: str, *, default: bool) -> bool:
    """MSPDI boolean; absent → ``default``. MS Project writes ``"1"``/``"0"`` but
    xsd:boolean also admits ``"true"``/``"false"``, which third-party exporters use."""
    raw = _text(parent, tag)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true"}


def _bool_or_none(parent: ET.Element, tag: str) -> bool | None:
    """MSPDI boolean that distinguishes *absent* (``None``) from ``0``/``1`` — so a metric
    can tell "the source tool did not provide this" from "the source says false"."""
    raw = _text(parent, tag)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true"}


def _stored_slack_minutes(task_el: ET.Element) -> int | None:
    """MSPDI ``Task/TotalSlack`` → working minutes (``None`` if absent). MS Project stores slack
    fields in **tenths of a minute** (verified against the goldens — stored ÷ 10 == recomputed
    CPM float on clean tasks); the engine's float axis is whole minutes (480/day)."""
    raw = _int(task_el, "TotalSlack")
    return None if raw is None else round(raw / 10)


# --- calendar ---------------------------------------------------------------------

#: Defensive cap when expanding one exception date range into holidays — real holiday
#: ranges are days long; a malformed multi-decade range must not balloon the model.
_MAX_EXCEPTION_RANGE_DAYS = 366


def _parse_project_calendar(root: ET.Element) -> Calendar:
    """``Project/CalendarUID`` → the model :class:`Calendar` (ADR-0028).

    Reads the project calendar's working weekdays, its dominant per-day working-minute
    total, and its non-working exceptions (holidays). A derived calendar with no day
    pattern of its own walks its base chain (cycle-safe); exceptions collect across the
    chain. The engine models ONE schedule-level calendar with one contiguous block per
    day, so varying day lengths use the dominant total and per-task/per-resource
    calendars stay out of scope (both documented). Any structural surprise degrades to
    the standard 8h/Mon-Fri default with a logged note — a bad calendar must never sink
    an otherwise valid schedule (the Law-2 tolerance posture).
    """
    try:
        return _project_calendar(root)
    except Exception:
        logger.warning("unreadable project calendar; using the standard 8h/Mon-Fri default")
        return Calendar()


def _project_calendar(root: ET.Element) -> Calendar:
    by_uid = _calendars_by_uid(root)
    target_uid = _text(root, "CalendarUID")
    cal = _build_calendar(target_uid, by_uid) if target_uid is not None else None
    return cal or Calendar()


def _calendars_by_uid(root: ET.Element) -> dict[str, ET.Element]:
    """``<Calendars>`` indexed by UID string (the base-calendar chain resolves through this)."""
    calendars_el = root.find("Calendars")
    if calendars_el is None:
        return {}
    out: dict[str, ET.Element] = {}
    for el in calendars_el.findall("Calendar"):
        uid = _text(el, "UID")
        if uid is not None:
            out[uid] = el
    return out


def parse_calendar_registry(root: ET.Element, tasks: tuple[Task, ...]) -> tuple[Calendar, ...]:
    """Every calendar a task is scheduled on (plus the project calendar), UID-keyed, for the
    SSI driving-slack parity path (ADR-0118 — a link's free float is counted on the successor's
    own calendar). Best-effort: a calendar that won't parse is skipped, never sinking the file."""
    by_uid = _calendars_by_uid(root)
    needed: set[str] = set()
    proj = _text(root, "CalendarUID")
    if proj is not None:
        needed.add(proj)
    needed.update(str(t.calendar_uid) for t in tasks if t.calendar_uid is not None)
    out: dict[int, Calendar] = {}
    for uid in needed:
        try:
            cal = _build_calendar(uid, by_uid)
        except Exception:
            cal = None
        if cal is not None:
            out[cal.uid] = cal
    return tuple(out[k] for k in sorted(out))


def _build_calendar(target_uid: str | None, by_uid: dict[str, ET.Element]) -> Calendar | None:
    """Parse one calendar (walking its base-calendar chain) into a model :class:`Calendar`.

    Holidays (``DayWorking=0`` exceptions) and extra working days (``DayWorking=1`` — a worked
    weekend or a recovered holiday) collect across the chain; the weekday pattern + intraday
    segments come from the first chain member that defines one. ``None`` if no usable weekday
    pattern is found. Per-task calendars feed the driving-slack parity (ADR-0118); the engine's
    other metrics still consume the single project calendar (ADR-0028).
    """
    cal_el = by_uid.get(target_uid) if target_uid is not None else None
    if cal_el is None or target_uid is None:
        return None

    # the base-calendar chain: this calendar first, then its bases (cycle-safe; the "-1" base
    # UID of a base calendar resolves to nothing and ends the walk)
    chain: list[ET.Element] = []
    seen: set[str] = set()
    cursor: ET.Element | None = cal_el
    cursor_uid: str = target_uid
    while cursor is not None and cursor_uid not in seen:
        chain.append(cursor)
        seen.add(cursor_uid)
        base_uid = _text(cursor, "BaseCalendarUID")
        cursor = by_uid.get(base_uid) if base_uid is not None else None
        cursor_uid = base_uid or ""

    work_weekdays: set[int] = set()
    day_totals: list[int] = []
    segments_by_total: dict[int, tuple[tuple[int, int], ...]] = {}
    holidays: set[dt.date] = set()
    working: set[dt.date] = set()
    pattern_found = False
    for el in chain:
        weekdays_el = el.find("WeekDays")
        entries = [] if weekdays_el is None else weekdays_el.findall("WeekDay")
        # old-style exception entries (DayType 0 + TimePeriod) apply at every chain level
        for wd in entries:
            if (_int(wd, "DayType") or 0) != 0:
                continue
            sink = working if _bool(wd, "DayWorking", default=False) else holidays
            sink.update(_exception_range(wd.find("TimePeriod")))
        # the weekday pattern comes from the FIRST chain member that defines one (a
        # derived resource/project calendar without WeekDays inherits its base's week)
        day_entries = [wd for wd in entries if (_int(wd, "DayType") or 0) != 0]
        if day_entries and not pattern_found:
            pattern_found = True
            for wd in day_entries:
                weekday = weekday_from_source(_int(wd, "DayType") or 0)
                if weekday is None or not _bool(wd, "DayWorking", default=False):
                    continue
                work_weekdays.add(weekday)
                segments = tuple(
                    span
                    for wt in wd.iter("WorkingTime")
                    if (span := working_time_span(_text(wt, "FromTime"), _text(wt, "ToTime")))
                )
                minutes = sum(end - start for start, end in segments)
                if minutes > 0:
                    day_totals.append(minutes)
                    # keep the segment layout of the dominant day length (resolved below) so
                    # the driving-slack pass can honor intraday gaps (e.g. a lunch break)
                    segments_by_total.setdefault(minutes, tuple(sorted(segments)))
        # modern exceptions, collected across the whole chain
        for exc in el.iter("Exception"):
            sink = working if _bool(exc, "DayWorking", default=False) else holidays
            occ = _int(exc, "Occurrences")
            sink.update(_exception_range(exc.find("TimePeriod"), occurrences=occ))

    if not work_weekdays:
        return None  # no usable weekday pattern anywhere
    # a DayWorking day with no WorkingTimes means "the default times" (480) in MS Project
    minutes_per_day = dominant_day_minutes(day_totals) or MINUTES_PER_DAY
    # only carry intraday segments when they actually gap (a lunch break); a single
    # contiguous block is the legacy default and stays as () so nothing else changes
    segments = segments_by_total.get(minutes_per_day, ())
    day_segments = segments if len(segments) > 1 else ()
    # keep only working-day exceptions that a weekday-minus-holiday count would miss
    extra_working = tuple(
        sorted(d for d in working if d.weekday() not in work_weekdays or d in holidays)
    )
    return Calendar(
        uid=int(target_uid) if target_uid.lstrip("-").isdigit() else 0,
        name=_text(cal_el, "Name") or "Standard",
        working_minutes_per_day=minutes_per_day,
        work_weekdays=tuple(sorted(work_weekdays)),
        # a weekend holiday is a no-op for the engine; keep the model lean
        holidays=tuple(sorted(h for h in holidays if h.weekday() in work_weekdays)),
        working_days=extra_working,
        day_segments=day_segments,
    )


def _exception_range(
    period_el: ET.Element | None, *, occurrences: int | None = None
) -> set[dt.date]:
    """A ``TimePeriod``'s ``FromDate``..``ToDate`` (inclusive) as dates, capped defensively.

    A **recurring** exception ("every Friday off", a yearly holiday) carries a TimePeriod
    spanning first..last occurrence — expanding that contiguously would erase whole months
    of working days. MS Project writes ``Occurrences``: a contiguous daily exception has
    occurrences == days-in-range; anything else is a recurrence pattern, which the
    single-block model cannot represent — skipped with a logged note (under-modeling is
    honest; fabricating weeks of holidays is not).
    """
    if period_el is None:
        return set()
    start = parse_datetime(_text(period_el, "FromDate"))
    finish = parse_datetime(_text(period_el, "ToDate"))
    if start is None or finish is None or finish < start:
        return set()
    days = (finish.date() - start.date()).days + 1
    if occurrences is not None and occurrences > 1 and occurrences != days:
        logger.info(
            "skipped a recurring calendar exception (%d occurrences over %d days — "
            "recurrence patterns are outside the single-block day model)",
            occurrences,
            days,
        )
        return set()
    days = min(days, _MAX_EXCEPTION_RANGE_DAYS)
    return {start.date() + dt.timedelta(days=i) for i in range(days)}


# --- task ------------------------------------------------------------------------


def _parse_extended_attribute_defs(root: ET.Element) -> dict[str, str]:
    """Map each custom field's ``FieldID`` → display label (``Alias`` when set, else ``FieldName``).

    MSPDI declares custom/extended fields once at the project level (``<ExtendedAttributes>``); each
    task then carries values keyed by ``FieldID``. The label is what the user picks fields by, so an
    operator-given alias (e.g. ``CA-WBS``) wins over the raw field name (``Text20``)."""
    defs: dict[str, str] = {}
    container = root.find("ExtendedAttributes")
    for ea in [] if container is None else container.findall("ExtendedAttribute"):
        field_id = _text(ea, "FieldID")
        if field_id is None:
            continue
        defs[field_id] = _text(ea, "Alias") or _text(ea, "FieldName") or field_id
    return defs


def _parse_extended_attribute_raw_names(root: ET.Element) -> dict[str, str]:
    """Map each custom field's raw ``FieldName`` (e.g. ``Text9``) → its stored label (``Alias`` when
    set, else the raw name).

    MS Project **filters/groups reference the raw name**, but each task stores custom values keyed
    by the label, so faithful filter/group evaluation (#10) needs this raw-name → label indirection
    (ADR-0231). Built from every declared extended-attribute def (not just the populated ones), so a
    referenced-but-empty field resolves to "absent" rather than "unknown"."""
    out: dict[str, str] = {}
    container = root.find("ExtendedAttributes")
    for ea in [] if container is None else container.findall("ExtendedAttribute"):
        field_name = _text(ea, "FieldName")
        if field_name is None:
            continue
        out[field_name] = _text(ea, "Alias") or field_name
    return out


def _task_custom_fields(
    task_el: ET.Element, ext_defs: dict[str, str]
) -> tuple[tuple[str, str], ...]:
    """The task's populated custom fields as ``(label, value)`` pairs (file order, dedup by label).

    A value whose ``FieldID`` has no project-level definition is skipped — it cannot be labelled."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for ea in task_el.findall("ExtendedAttribute"):
        field_id = _text(ea, "FieldID")
        value = _text(ea, "Value")
        if field_id is None or value is None:
            continue
        label = ext_defs.get(field_id)
        if label is None or label in seen:
            continue
        seen.add(label)
        out.append((label, value))
    return tuple(out)


def _parse_task(
    task_el: ET.Element,
    assigned_uids_by_task: dict[int, tuple[int, ...]],
    assigned_names_by_task: dict[int, tuple[str, ...]],
    assignments_by_task: dict[int, tuple[Assignment, ...]],
    ext_defs: dict[str, str],
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

    cal_uid = _int(task_el, "CalendarUID")
    if cal_uid is not None and cal_uid < 0:  # MSPDI writes -1 for "use the project calendar"
        cal_uid = None

    try:
        return Task(
            unique_id=uid,
            name=_text(task_el, "Name") or f"Task {uid}",
            wbs=_text(task_el, "WBS"),
            calendar_uid=cal_uid,
            outline_level=_cosmetic_int(task_el, "OutlineLevel", 0),
            duration_minutes=iso_duration_to_minutes(_text(task_el, "Duration")),
            duration_is_elapsed=_int(task_el, "DurationFormat") in _ELAPSED_DURATION_FORMATS,
            is_estimated_duration=_bool(task_el, "Estimated", default=False),
            remaining_duration_minutes=_optional_minutes(task_el, "RemainingDuration"),
            baseline_duration_minutes=bl_duration,
            is_milestone=_bool(task_el, "Milestone", default=False),
            is_summary=_bool(task_el, "Summary", default=False) or uid == 0,
            is_level_of_effort=False,  # not represented in MSPDI (ADR-0008)
            is_active=_bool(task_el, "Active", default=True),
            is_manual=_bool(task_el, "Manual", default=False),
            constraint_type=constraint_type,
            constraint_date=constraint_date,
            deadline=parse_datetime(_text(task_el, "Deadline")),
            notes=_text(task_el, "Notes"),
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
            work_minutes=_optional_minutes(task_el, "Work"),
            actual_work_minutes=_optional_minutes(task_el, "ActualWork"),
            resource_names=assigned_names_by_task.get(uid, ()),
            resource_ids=assigned_uids_by_task.get(uid, ()),
            resource_assignments=assignments_by_task.get(uid, ()),
            stored_total_float_minutes=_stored_slack_minutes(task_el),
            stored_is_critical=_bool_or_none(task_el, "Critical"),
            custom_fields=_task_custom_fields(task_el, ext_defs),
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
        # mirror the model's effective-summary rule (`is_summary or uid == 0`, :531): a UID-0
        # project-summary row whose XML omits <Summary> must NOT leak its project-spanning
        # rollup baseline into the CPLI basis (audit M4).
        if _bool(task_el, "Summary", default=False) or _int(task_el, "UID") == 0:
            continue
        # an INACTIVE task is out of the schedule (MS Project excludes it from every rollup, and
        # so does the whole engine — CPM/metrics/driving-slack); a late baseline finish on an
        # inactive row must not inflate the project baseline finish either (else the CPLI basis
        # disagrees with the network the rest of the tool computes on).
        if not _bool(task_el, "Active", default=True):
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
        # KNOWN APPROXIMATION (audit L11): duplicate links differing ONLY by lag collapse to the
        # first occurrence (file order) — dedup keys on (pred, succ, type), matching the XER
        # importer. MSP itself forbids exact same-pair duplicates in the UI, so a real export
        # carries them only via XML editing; negligible impact, documented rather than modelled.
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
) -> tuple[
    dict[int, tuple[int, ...]],
    dict[int, tuple[str, ...]],
    dict[int, tuple[Assignment, ...]],
]:
    """``Project/Assignments`` → per-task resource UID / name tuples (order-preserving) and the
    richer per-task :class:`Assignment` list (resource UID + Work minutes + Units) the resource
    loading view needs. Multiple assignment rows for the same task+resource are summed (work) /
    kept (units) so a task carries one Assignment per resource."""
    uids_by_task: dict[int, list[int]] = {}
    names_by_task: dict[int, list[str]] = {}
    work_by_task_res: dict[int, dict[int, int]] = {}
    units_by_task_res: dict[int, dict[int, float]] = {}
    remaining_by_task_res: dict[int, dict[int, int]] = {}
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
        work = iso_duration_to_minutes(_text(assign_el, "Work")) or 0
        units = parse_float(_text(assign_el, "Units"))
        work_map = work_by_task_res.setdefault(task_uid, {})
        work_map[resource_uid] = work_map.get(resource_uid, 0) + max(0, work)
        units_map = units_by_task_res.setdefault(task_uid, {})
        # keep the first/representative units booked for the pair (typically constant per pair)
        units_map.setdefault(resource_uid, 1.0 if units is None else max(0.0, units))
        # per-assignment remaining work (None when the file omits it — distinct from 0 = done);
        # summed like work when a pair carries several rows
        rem = _text(assign_el, "RemainingWork")
        if rem is not None:
            rem_map = remaining_by_task_res.setdefault(task_uid, {})
            rem_map[resource_uid] = rem_map.get(resource_uid, 0) + max(
                0, iso_duration_to_minutes(rem)
            )
    assignments_by_task: dict[int, tuple[Assignment, ...]] = {}
    for task_uid, uids in uids_by_task.items():
        work_map = work_by_task_res.get(task_uid, {})
        units_map = units_by_task_res.get(task_uid, {})
        rem_map = remaining_by_task_res.get(task_uid, {})
        assignments_by_task[task_uid] = tuple(
            Assignment(
                resource_id=ruid,
                work_minutes=work_map.get(ruid, 0),
                units=units_map.get(ruid, 1.0),
                remaining_work_minutes=rem_map.get(ruid),
            )
            for ruid in uids
        )
    return (
        {uid: tuple(v) for uid, v in uids_by_task.items()},
        {uid: tuple(v) for uid, v in names_by_task.items()},
        assignments_by_task,
    )
