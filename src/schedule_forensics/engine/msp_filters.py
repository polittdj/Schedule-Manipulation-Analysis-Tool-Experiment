"""Faithful evaluator for MS Project saved **filters** — matches ``org.mpxj.GenericCriteria`` /
``TestOperator`` semantics so the tool selects exactly the tasks MS Project would (feature #10).

The subtlety of MS Project filtering is entirely in three places, reproduced here from the MPXJ
16.2.0 bytecode (verified, not guessed):

1. **Asymmetric normalization.** The *field* (left) value is normalized by its data type before
any comparison — a DATE is truncated to its calendar day (00:00), a DURATION coerces to the
tool's working-minute axis with ``None`` → 0, a STRING ``None`` → ``""``; everything else passes
through untouched (including ``None``). A *literal* right-hand value is **not** date-truncated
(a ``Start <= 2028-09-29T17:00`` literal keeps its 17:00). A *field-reference* right-hand value
(MPXJ "symbolic value", e.g. ``Duration9 > Duration8``) is normalized by *its own* field's type.
A *prompt* value is inserted raw. 2. **Null ordering.** In an ordered comparison a ``None`` left
value sorts **greater** than any value (``None >`` anything is TRUE), a ``None`` right sorts
less; both ``None`` compare equal. This is the explicit tri-state MPXJ's ``evaluateCompareTo``
implements — never Python's ``None`` comparison. 3. **Three string regimes.**
``EQUALS``/``DOES_NOT_EQUAL`` = case-**sensitive** whole-string match;
``CONTAINS``/``DOES_NOT_CONTAIN`` = case-**insensitive** substring; ``CONTAINS_EXACTLY`` = case-
**sensitive** substring. A non-string operand on either side of a *contains* → no match.

``AND``/``OR`` branches are fully recursive and short-circuit; an empty branch (and a filter
whose ``criteria is None`` — "All Tasks") matches everything. Durations are compared on the
tool's integer working-minute axis (exact), so MPXJ's float-hours 1e-5 tolerance is not needed
and its symbolic- duration HOURS→0 quirk does not arise (both sides normalize to minutes
uniformly).
"""

from __future__ import annotations

import datetime as dt
import re
from contextvars import ContextVar

from schedule_forensics.engine.msp_field_resolver import (
    FieldKind,
    FieldValue,
    field_kind,
    resolve_field,
)
from schedule_forensics.importers._common import parse_datetime, parse_float
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.saved_view import BRANCH_OPERATORS, Criterion, Operand, SavedFilter
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

#: Prompt answers supplied by the operator (prompt label → typed value).
PromptValues = dict[str, FieldValue]

_DUR_LITERAL_RE = re.compile(r"^\s*([\d.]+)\s*(e)?([a-z%]*)\s*$", re.IGNORECASE)

#: MPXJ's TimeUnitDefaultsContainer defaults, used when the source file does not declare the
#: project property (MPXJ mirrors MS Project's own 2400 min/week and 20 days/month).
_DEFAULT_MINUTES_PER_WEEK = 2400
_DEFAULT_DAYS_PER_MONTH = 20

#: MPXJ elapsed-unit → wall-clock minutes, decoded from the vendored mpxj-16.2.0
#: ``Duration.convertUnits`` bytecode (ADR-0354): day 1440 · week 10080 (7 d) · month 43200
#: (30 d) · year 524160 (**364 d** = 52x7, not 365). Calendars are ignored by design.
_ELAPSED_UNIT_MINUTES: dict[str, int] = {
    "m": 1, "h": 60, "d": 1440, "w": 10080, "mo": 43200, "y": 524160, "%": 1,
}  # fmt: skip

#: Long-form unit spellings tolerated on top of MPXJ's canonical one-token vocabulary
#: (``Duration.toString()`` emits only ``m h d w mo % y`` and their ``e``-prefixed elapsed
#: forms; the aliases keep hand-typed prompt answers like ``"5 days"`` working).
_UNIT_ALIASES: dict[str, str] = {
    "min": "m", "mins": "m", "minute": "m", "minutes": "m",
    "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "day": "d", "days": "d",
    "wk": "w", "wks": "w", "week": "w", "weeks": "w",
    "mon": "mo", "mons": "mo", "month": "mo", "months": "mo",
    "yr": "y", "yrs": "y", "year": "y", "years": "y",
}  # fmt: skip

#: The evaluator's duration-literal semantics version (ADR-0354). v1 hard-coded 480-minute days
#: and silently read elapsed/unknown units as working days; v2 conforms to the vendored MPXJ
#: ``Duration.convertUnits``. Bump on any future change that can move a saved-filter population.
EVALUATOR_VERSION = 2

#: v1's table, kept VERBATIM and used ONLY by :func:`selection_migration_delta` (the
#: migration report shows the operator how a saved filter's population moved under v2).
_V1_UNIT_MINUTES: dict[str, int] = {
    "m": 1, "min": 1, "mins": 1, "minute": 1, "minutes": 1,
    "h": 60, "hr": 60, "hrs": 60, "hour": 60, "hours": 60,
    "d": 480, "day": 480, "days": 480,
    "w": 2400, "wk": 2400, "wks": 2400, "week": 2400, "weeks": 2400,
    "mo": 9600, "mon": 9600, "mons": 9600, "month": 9600, "months": 9600,
    "y": 115200, "yr": 115200, "yrs": 115200, "year": 115200, "years": 115200,
}  # fmt: skip
_V1_LITERAL_RE = re.compile(r"^\s*([\d.]+)\s*(e)?([a-z]*)\s*$", re.IGNORECASE)

#: Internal switch flipped only by :func:`selection_migration_delta` to re-evaluate a filter
#: under the retired v1 literal semantics. A ContextVar so the public evaluator signatures stay
#: stable and concurrent requests cannot see each other's mode.
_USE_V1_LITERALS: ContextVar[bool] = ContextVar("msp_filters_use_v1_literals", default=False)


def _parse_duration_literal_v1(text: str) -> int | None:
    """The retired pre-ADR-0354 parse (hard 480-minute days; elapsed marker discarded; unknown
    unit read as days). Report-only — never used for a live selection."""
    m = _V1_LITERAL_RE.match(text)
    if not m:
        return None
    unit = (m.group(3) or "d").lower()
    per = _V1_UNIT_MINUTES.get(unit, 480)
    return round(float(m.group(1)) * per)


def _parse_duration_literal(text: str, calendar: Calendar) -> int | None:
    """A filter's duration literal (``"5.0d"``, ``"2.0ed"``, ``"5 days"``) → comparison minutes.

    Conforms to the vendored MPXJ ``Duration.convertUnits`` (ADR-0354): ordinary units scale by
    the schedule's OWN ``working_minutes_per_day`` / ``minutes_per_week`` / ``days_per_month``
    (week is minutes-per-week, NOT 5 x day; year is minutes-per-week x 52); elapsed units
    (``e``-marked) are wall-clock constants regardless of calendar; ``%``/``e%`` pass the value
    through unscaled (MPXJ's switch default — mirrored, not repaired). A bare number reads as
    days (MS Project's default duration unit). ``Duration.toString()`` is a closed vocabulary,
    so an unknown unit can only mean a corrupted sidecar and fails closed (``None`` — the
    malformed-leaf convention), never a silent guess."""
    if _USE_V1_LITERALS.get():
        return _parse_duration_literal_v1(text)
    m = _DUR_LITERAL_RE.match(text)
    if not m:
        return None
    unit = (m.group(3) or "d").lower()
    unit = _UNIT_ALIASES.get(unit, unit)
    if m.group(2):  # the elapsed marker MPXJ writes as the unit's leading "e"
        per = _ELAPSED_UNIT_MINUTES.get(unit)
        return None if per is None else round(float(m.group(1)) * per)
    mpd = calendar.working_minutes_per_day
    mpw = calendar.minutes_per_week or _DEFAULT_MINUTES_PER_WEEK
    dpm = calendar.days_per_month or _DEFAULT_DAYS_PER_MONTH
    working: dict[str, int] = {
        "m": 1, "h": 60, "d": mpd, "w": mpw, "mo": mpd * dpm, "y": mpw * 52, "%": 1,
    }  # fmt: skip
    per = working.get(unit)
    return None if per is None else round(float(m.group(1)) * per)


def _day_start(value: FieldValue) -> FieldValue:
    """Truncate a datetime to its calendar day at 00:00 (MPXJ's ``getDayStartDate``); pass
    non-dates.
    """
    if isinstance(value, dt.datetime):
        return dt.datetime(value.year, value.month, value.day)
    return value


def _normalize_lhs(value: FieldValue, kind: FieldKind) -> FieldValue:
    """Normalize a *field* value by its data type, MPXJ order: DATE → day-truncate, DURATION →
    minutes
    with ``None`` → 0, STRING ``None`` → ``""``; every other kind (incl. ``None``) untouched."""
    if kind is FieldKind.DATE:
        return _day_start(value)
    if kind is FieldKind.DURATION_MINUTES:
        return 0 if value is None else value
    if kind is FieldKind.STRING:
        return "" if value is None else value
    return value


def _coerce_literal(text: str | None, kind: FieldKind, calendar: Calendar) -> FieldValue:
    """Coerce a filter's literal string to the left field's axis (a literal date is **not**
    truncated). ``calendar`` supplies the schedule's own day/week/month scale for duration
    literals (ADR-0354) — hard-coding 480 min/day compared apples to oranges on any other
    calendar.
    """
    if text is None:
        return None
    if kind is FieldKind.DATE:
        return parse_datetime(text)
    if kind is FieldKind.DURATION_MINUTES:
        return _parse_duration_literal(text, calendar)
    if kind is FieldKind.BOOLEAN:
        return text.strip().lower() in {"1", "true", "yes"}
    if kind in (FieldKind.NUMERIC, FieldKind.CURRENCY, FieldKind.PERCENT):
        return parse_float(text)
    return text  # STRING / UNRESOLVED — verbatim


def _resolve_operand(
    schedule: Schedule, task: Task, operand: Operand, lhs_kind: FieldKind, prompts: PromptValues
) -> FieldValue:
    """The right-hand value for a leaf, per its kind: a literal coerced to the LHS axis; a
    referenced
    field resolved on the same task and normalized by ITS OWN kind; a prompt answer (raw); or
    ``None``."""
    if operand.kind == "null":
        return None
    if operand.kind == "prompt":
        return prompts.get(operand.text or "")
    if operand.kind == "field":
        rf = resolve_field(schedule, task, operand.text or "", field_enum=operand.field_enum)
        return _normalize_lhs(rf.value, rf.kind)
    return _coerce_literal(operand.text, lhs_kind, schedule.calendar)  # literal


def _compare(lhs: FieldValue, rhs: FieldValue) -> int | None:
    """MPXJ ``evaluateCompareTo`` tri-state: a ``None`` LHS sorts **greater** (+1), a ``None``
    RHS less
    (-1), both ``None`` equal (0). ``None`` when the two are not mutually comparable (a
    malformed
    cross-type filter — the leaf then fails closed)."""
    if lhs is None or rhs is None:
        if lhs is None and rhs is None:
            return 0
        return 1 if lhs is None else -1
    try:
        if lhs < rhs:  # type: ignore[operator]
            return -1
        if lhs > rhs:  # type: ignore[operator]
            return 1
        return 0
    except TypeError:
        return None


def _equals(lhs: FieldValue, rhs: FieldValue) -> bool:
    """MPXJ EQUALS: ``lhs is None ? rhs is None : lhs == rhs`` (strings case-sensitive; a
    ``None`` field
    matches only a ``None`` operand — this is ``Actual Finish EQUALS <null>``)."""
    if lhs is None:
        return rhs is None
    if rhs is None:
        return False
    # keep bool/int from cross-matching (Python True == 1); MS Project types are consistent per
    # field
    if isinstance(lhs, bool) != isinstance(rhs, bool):
        return False
    try:
        return bool(lhs == rhs)
    except TypeError:
        return False


def _contains(lhs: FieldValue, rhs: FieldValue, *, case_insensitive: bool) -> bool:
    """MPXJ CONTAINS / CONTAINS_EXACTLY: field-contains-literal on two strings; anything else →
    False.
    """
    if not isinstance(lhs, str) or not isinstance(rhs, str):
        return False
    if case_insensitive:
        return rhs.upper() in lhs.upper()
    return rhs in lhs


def _within(lhs: FieldValue, b0: FieldValue, b1: FieldValue) -> bool:
    """MPXJ ``evaluateWithin``: inclusive, order-independent bounds. ``None`` LHS matches only
    when a
    bound is ``None``; a ``None`` bound with a non-``None`` LHS → False."""
    if lhs is None:
        return b0 is None or b1 is None
    if b0 is None or b1 is None:
        return False
    try:
        return (b0 <= lhs <= b1) or (b1 <= lhs <= b0)  # type: ignore[operator]
    except TypeError:
        return False


def _eval_leaf(schedule: Schedule, task: Task, node: Criterion, prompts: PromptValues) -> bool:
    op = node.operator
    if op == "IS_ANY_VALUE":
        return True
    raw_field = node.field or ""
    lhs_kind = field_kind(raw_field, field_enum=node.field_enum)
    lhs = _normalize_lhs(
        resolve_field(schedule, task, raw_field, field_enum=node.field_enum).value, lhs_kind
    )
    ops = node.operands
    if op in ("IS_WITHIN", "IS_NOT_WITHIN"):
        b0 = _resolve_operand(schedule, task, ops[0], lhs_kind, prompts) if len(ops) > 0 else None
        b1 = _resolve_operand(schedule, task, ops[1], lhs_kind, prompts) if len(ops) > 1 else None
        within = _within(lhs, b0, b1)
        return within if op == "IS_WITHIN" else not within
    rhs = _resolve_operand(schedule, task, ops[0], lhs_kind, prompts) if ops else None
    if op == "EQUALS":
        return _equals(lhs, rhs)
    if op == "DOES_NOT_EQUAL":
        return not _equals(lhs, rhs)
    if op == "CONTAINS":
        return _contains(lhs, rhs, case_insensitive=True)
    if op == "DOES_NOT_CONTAIN":
        return not _contains(lhs, rhs, case_insensitive=True)
    if op == "CONTAINS_EXACTLY":
        return _contains(lhs, rhs, case_insensitive=False)
    cmp = _compare(lhs, rhs)
    if cmp is None:  # non-comparable → the leaf fails closed
        return False
    if op == "IS_GREATER_THAN":
        return cmp > 0
    if op == "IS_GREATER_THAN_OR_EQUAL_TO":
        return cmp >= 0
    if op == "IS_LESS_THAN":
        return cmp < 0
    if op == "IS_LESS_THAN_OR_EQUAL_TO":
        return cmp <= 0
    raise ValueError(f"unknown filter operator: {op!r}")


def _eval_node(schedule: Schedule, task: Task, node: Criterion, prompts: PromptValues) -> bool:
    """Evaluate one criteria node against ``task`` — recurse AND/OR (short-circuit; empty ⇒
    True).
    """
    if node.operator in BRANCH_OPERATORS:
        if not node.children:
            return True  # an empty branch is a pass-through (MPXJ)
        if node.operator == "AND":
            return all(_eval_node(schedule, task, c, prompts) for c in node.children)
        return any(_eval_node(schedule, task, c, prompts) for c in node.children)
    return _eval_leaf(schedule, task, node, prompts)


def evaluate_filter(
    schedule: Schedule, task: Task, filt: SavedFilter, prompts: PromptValues | None = None
) -> bool:
    """True iff ``task`` satisfies ``filt``. A filter whose ``criteria is None`` (e.g. "All Tasks")
    matches everything. ``prompts`` supplies the operator's answers for an interactive filter
    (label → value); a missing prompt behaves as a ``None`` operand."""
    if filt.criteria is None:
        return True
    return _eval_node(schedule, task, filt.criteria, prompts or {})


def select(
    schedule: Schedule, filt: SavedFilter, prompts: PromptValues | None = None
) -> tuple[int, ...]:
    """The UniqueIDs of the tasks matching ``filt``, in file order. (``show_related_summary_rows`` —
    keeping matching tasks' parent summaries — is applied at the presentation layer, not here.)"""
    return tuple(t.unique_id for t in schedule.tasks if evaluate_filter(schedule, t, filt, prompts))


def required_prompts(filt: SavedFilter) -> tuple[str, ...]:
    """The distinct prompt labels an interactive filter asks for (first-seen order), so the UI can
    collect the operator's answers before applying it."""
    labels: list[str] = []

    def walk(node: Criterion | None) -> None:
        if node is None:
            return
        for operand in node.operands:
            if operand.kind == "prompt" and operand.text and operand.text not in labels:
                labels.append(operand.text)
        for child in node.children:
            walk(child)

    walk(filt.criteria)
    return tuple(labels)


def coerce_prompt_answers(
    filt: SavedFilter, answers: dict[str, str], calendar: Calendar | None = None
) -> PromptValues:
    """The operator's typed prompt answers coerced onto each prompt's comparison axis.

    MS Project types a prompt's answer by the field it is compared against ("Show tasks that
    start or finish after:" against a DATE field expects a date). This walks the criteria tree,
    finds each prompt operand's **left field kind**, and coerces the raw answer string with the
    same rule a literal uses (:func:`_coerce_literal` — so a date stays untruncated, a duration
    parses "3d", a number parses plainly). A label compared against several fields keeps the
    first-seen kind (MS Project reuses one answer the same way); an unanswered label is simply
    absent (the evaluator treats a missing prompt as a ``None`` operand).

    ``calendar`` scales any duration-typed answer onto that schedule's own axis (ADR-0354).
    The session applies one filter across EVERY loaded file, so the caller coerces per
    schedule at selection time; ``None`` falls back to the standard calendar (a duration
    answer then reads 480-minute days — only correct for standard-calendar files)."""
    kinds: dict[str, FieldKind] = {}

    def walk(node: Criterion | None) -> None:
        if node is None:
            return
        lhs_kind = field_kind(node.field or "", field_enum=node.field_enum)
        for operand in node.operands:
            if operand.kind == "prompt" and operand.text and operand.text not in kinds:
                kinds[operand.text] = lhs_kind
        for child in node.children:
            walk(child)

    walk(filt.criteria)
    cal = calendar if calendar is not None else Calendar()
    return {
        label: _coerce_literal(text, kinds.get(label, FieldKind.UNRESOLVED), cal)
        for label, text in answers.items()
        if text != ""
    }


def filter_reads_duration_literals(filt: SavedFilter) -> bool:
    """True iff any leaf compares a DURATION field against a literal or prompt operand — the
    only shape whose selection can move between evaluator versions (ADR-0354). Field-to-field
    duration comparisons stay on the stored minutes axis in every version."""

    def walk(node: Criterion | None) -> bool:
        if node is None:
            return False
        if node.operator in BRANCH_OPERATORS:
            return any(walk(c) for c in node.children)
        lhs_kind = field_kind(node.field or "", field_enum=node.field_enum)
        if lhs_kind is not FieldKind.DURATION_MINUTES:
            return False
        return any(op.kind in ("literal", "prompt") for op in node.operands)

    return walk(filt.criteria)


def selection_migration_delta(
    schedule: Schedule, filt: SavedFilter, prompts: PromptValues | None = None
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """``(v1_selection, v2_selection)`` for a filter whose population can move under ADR-0354.

    The migration report the evaluator-version bump is gated on: re-runs the SAME selection
    under the retired v1 duration-literal semantics (hard 480-minute days, elapsed marker
    discarded) beside the live v2 (MPXJ-conformant) selection, so the operator sees exactly
    which population moved and by how much. ``None`` when the filter carries no duration
    literal/prompt (its selection is version-invariant, and the report would be noise).
    ``prompts`` must be the v2-coerced values; the v1 leg re-parses only LITERALS (a prompt
    answer's coercion difference is folded into the v2 leg the operator is already shown)."""
    if not filter_reads_duration_literals(filt):
        return None
    token = _USE_V1_LITERALS.set(True)
    try:
        v1 = select(schedule, filt, prompts)
    finally:
        _USE_V1_LITERALS.reset(token)
    return v1, select(schedule, filt, prompts)
