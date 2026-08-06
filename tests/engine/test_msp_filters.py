"""Faithful MS Project filter evaluation — pinned to the 10 real filters extracted from the
operator's ``Large Test File Leveled.mpp`` (the ground truth for "exact reproduction", feature #10).

Covers the raw-field resolver (core + the two-hop custom-field lookup), every ``TestOperator``'s
exact semantics (the three string regimes, the null-sorts-greater ordering, inclusive/order-
independent ``IS_WITHIN``, field-to-field, prompts), the recursive AND/OR short-circuit, and each of
the 10 real filters against a hand-built population whose expected matches are checkable by eye.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.msp_field_resolver import FieldKind, field_kind, resolve_field
from schedule_forensics.engine.msp_filters import (
    _parse_duration_literal,
    coerce_prompt_answers,
    evaluate_filter,
    required_prompts,
    select,
    selection_migration_delta,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.saved_view import Criterion, Operand, SavedFilter
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480


# --- fixture builders --------------------------------------------------------------------------
def leaf(op: str, field: str, enum: str, *operands: Operand) -> Criterion:
    return Criterion(operator=op, field=field, field_enum=enum, operands=tuple(operands))


def lit(text: str, vt: str | None = None) -> Operand:
    return Operand(kind="literal", text=text, value_type=vt)


def fld(name: str, enum: str) -> Operand:
    return Operand(kind="field", text=name, field_enum=enum)


def prompt(label: str) -> Operand:
    return Operand(kind="prompt", text=label)


NULL = Operand(kind="null")


def AND(*kids: Criterion) -> Criterion:
    return Criterion(operator="AND", children=tuple(kids))


def OR(*kids: Criterion) -> Criterion:
    return Criterion(operator="OR", children=tuple(kids))


#: The raw MS Project field name → stored label map (as the importer persists it from the file).
RAW_MAP = (
    ("Text9", "IPT/ SUB"),
    ("Flag6", "SSI SRA Event"),
    ("Text19", "Risk ID"),
    ("Duration8", "Best Case Duration"),
    ("Duration9", "Worst Case Duration"),
)


def _t(uid: int, name: str, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=DAY, **kw)  # type: ignore[arg-type]


def _population() -> Schedule:
    """A 5-task population exercising every branch of the 10 real filters."""
    tasks = (
        # T1: SVT- / ZIN / exported / _MCTasks match (active, unfinished, Worst>Best, no Risk ID)
        _t(
            1,
            "SVT- one",
            is_active=True,
            is_summary=False,
            is_milestone=False,
            start=dt.datetime(2027, 1, 1, 8),
            finish=dt.datetime(2027, 1, 5, 17),
            actual_finish=None,
            custom_fields=(
                ("IPT/ SUB", "ZIN"),
                ("Risk ID", ""),
                ("Best Case Duration", "PT8H0M0S"),
                ("Worst Case Duration", "PT16H0M0S"),
                ("SSI SRA Event", "1"),
            ),
        ),
        # T2: the _RiskRegTasks match (active, unfinished, has a Risk ID; Worst<Best fails _MCTasks)
        _t(
            2,
            "svt two",
            is_active=True,
            is_summary=False,
            is_milestone=False,
            start=dt.datetime(2027, 2, 1, 8),
            finish=dt.datetime(2027, 2, 3, 17),
            actual_finish=None,
            custom_fields=(
                ("IPT/ SUB", "OTHER"),
                ("Risk ID", "R-9"),
                ("Best Case Duration", "PT16H0M0S"),
                ("Worst Case Duration", "PT8H0M0S"),
                ("SSI SRA Event", "0"),
            ),
        ),
        _t(3, "Summary roll", is_summary=True, start=dt.datetime(2027, 2, 15, 8)),
        _t(
            4,
            "milestone done",
            is_milestone=True,
            is_active=True,
            actual_finish=dt.datetime(2027, 3, 1, 8),
        ),
        _t(5, "inactive block", is_active=False, start=dt.datetime(2027, 2, 20, 8)),
    )
    return Schedule(
        name="s",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=tasks,
        custom_field_by_raw_name=RAW_MAP,
    )


# --- resolver ----------------------------------------------------------------------------------
def test_resolver_core_fields() -> None:
    sch = _population()
    t1 = sch.tasks_by_id[1]
    assert resolve_field(sch, t1, "Task Name", field_enum="NAME").value == "SVT- one"
    assert resolve_field(sch, t1, "Active", field_enum="ACTIVE").value is True
    assert resolve_field(sch, t1, "Duration", field_enum="DURATION").value == DAY
    # an unset date resolves to None (not a fabricated 0), with kind DATE
    af = resolve_field(sch, t1, "Actual Finish", field_enum="ACTUAL_FINISH")
    assert af.value is None and af.kind is FieldKind.DATE


def test_resolver_custom_two_hop() -> None:
    sch = _population()
    t1 = sch.tasks_by_id[1]
    # Text9 → label "IPT/ SUB" → the task's stored value; Flag "1" → bool; Duration ISO → minutes
    assert resolve_field(sch, t1, "Text9", field_enum="TEXT9").value == "ZIN"
    assert resolve_field(sch, t1, "Flag6", field_enum="FLAG6").value is True
    assert resolve_field(sch, t1, "Duration8", field_enum="DURATION8").value == DAY  # PT8H = 480
    assert resolve_field(sch, t1, "Duration9", field_enum="DURATION9").value == 2 * DAY
    # an empty custom string stays "" (so EQUALS '' can distinguish empty from absent)
    assert resolve_field(sch, t1, "Text19", field_enum="TEXT19").value == ""


def test_resolver_field_kind_and_unresolvable() -> None:
    assert field_kind("Task Name", field_enum="NAME") is FieldKind.STRING
    assert field_kind("Start", field_enum="START") is FieldKind.DATE
    assert field_kind("Flag6", field_enum="FLAG6") is FieldKind.BOOLEAN
    assert field_kind("Duration8", field_enum="DURATION8") is FieldKind.DURATION_MINUTES
    # a source-absent field (Agile add-in) is unresolvable so the UI can annotate it
    assert field_kind("Board Status", field_enum="BOARD_STATUS") is FieldKind.UNRESOLVED


def test_resolver_priority_outline_number_stop() -> None:
    sch = Schedule(
        name="s",
        source_file="Big Plan.mpp",
        project_start=dt.datetime(2027, 1, 1, 8),
        status_date=dt.datetime(2027, 2, 1, 8),
        tasks=(
            Task(
                unique_id=1,
                name="a",
                duration_minutes=DAY,
                priority=750,
                outline_number="1.2.3",
                stop=dt.datetime(2027, 1, 31, 17),
            ),
        ),
    )
    t1 = sch.tasks_by_id[1]
    assert field_kind("Priority", field_enum="PRIORITY") is FieldKind.NUMERIC
    assert resolve_field(sch, t1, "Priority", field_enum="PRIORITY").value == 750
    assert resolve_field(sch, t1, "Outline Number", field_enum="OUTLINE_NUMBER").value == "1.2.3"
    assert resolve_field(sch, t1, "Stop", field_enum="STOP").value == dt.datetime(2027, 1, 31, 17)
    # Project = the source file's base name, exactly as MS Project / the SSI exports show it
    assert field_kind("Project", field_enum="PROJECT") is FieldKind.STRING
    assert resolve_field(sch, t1, "Project", field_enum="PROJECT").value == "Big Plan"


def test_resolver_msp_status_rule() -> None:
    """MS Project's computed Status: Complete / Future Task / On Schedule / Late — judged from
    the stored Stop date vs the status date (progress through the day before = on schedule)."""
    sd = dt.datetime(2027, 2, 1, 8)

    def status(**kw: object) -> str | None:
        sch = Schedule(
            name="s",
            project_start=dt.datetime(2027, 1, 1, 8),
            status_date=sd,
            tasks=(Task(unique_id=1, name="t", duration_minutes=DAY, **kw),),  # type: ignore[arg-type]
        )
        return resolve_field(sch, sch.tasks_by_id[1], "Status", field_enum="STATUS").value  # type: ignore[return-value]

    assert status(percent_complete=100.0) == "Complete"
    assert status(start=dt.datetime(2027, 3, 1, 8)) == "Future Task"  # starts after the DD
    # progress recorded through the day before the status date → On Schedule
    assert (
        status(
            start=dt.datetime(2027, 1, 4, 8),
            percent_complete=50.0,
            stop=dt.datetime(2027, 1, 31, 17),
        )
        == "On Schedule"
    )
    # progress stops short of the day before the status date → Late
    assert (
        status(
            start=dt.datetime(2027, 1, 4, 8),
            percent_complete=10.0,
            stop=dt.datetime(2027, 1, 20, 17),
        )
        == "Late"
    )
    # should have started, no progress at all → Late
    assert status(start=dt.datetime(2027, 1, 4, 8)) == "Late"
    # no status date on the file → blank (never fabricate "today")
    sch = Schedule(
        name="s",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=(Task(unique_id=1, name="t", duration_minutes=DAY, start=dt.datetime(2027, 1, 4)),),
    )
    assert resolve_field(sch, sch.tasks_by_id[1], "Status", field_enum="STATUS").value is None


def test_resolver_strips_text_enum_suffix() -> None:
    sch = _population()
    t1 = sch.tasks_by_id[1]
    # MPXJ names a group's Duration column DURATION_TEXT / a custom one DURATION8_TEXT (audit F1);
    # both are the same underlying value and must resolve, not degrade to UNRESOLVED.
    assert field_kind("Duration", field_enum="DURATION_TEXT") is FieldKind.DURATION_MINUTES
    assert resolve_field(sch, t1, "Duration", field_enum="DURATION_TEXT").value == DAY
    assert field_kind("Duration8", field_enum="DURATION8_TEXT") is FieldKind.DURATION_MINUTES
    assert resolve_field(sch, t1, "Duration8", field_enum="DURATION8_TEXT").value == DAY
    # Task Mode (Auto vs Manually Scheduled), derived from is_manual
    assert field_kind("Task Mode", field_enum="TASK_MODE") is FieldKind.STRING
    assert resolve_field(sch, t1, "Task Mode", field_enum="TASK_MODE").value == "Auto Scheduled"


# --- operator semantics ------------------------------------------------------------------------
def _match(
    sch: Schedule, uid: int, crit: Criterion, prompts: dict[str, object] | None = None
) -> bool:
    filt = SavedFilter(name="f", criteria=crit)
    return evaluate_filter(sch, sch.tasks_by_id[uid], filt, prompts)  # type: ignore[arg-type]


def test_contains_is_case_insensitive() -> None:
    sch = _population()
    # "svt two" CONTAINS "SVT" case-insensitively
    assert _match(sch, 2, leaf("CONTAINS", "Task Name", "NAME", lit("SVT")))


def test_contains_exactly_is_case_sensitive_substring() -> None:
    sch = _population()
    # CONTAINS_EXACTLY is a case-SENSITIVE substring, not equality
    assert not _match(
        sch, 2, leaf("CONTAINS_EXACTLY", "Task Name", "NAME", lit("SVT"))
    )  # "svt two"
    assert _match(sch, 1, leaf("CONTAINS_EXACTLY", "Task Name", "NAME", lit("SVT-")))  # "SVT- one"


def test_equals_null_matches_only_absent() -> None:
    sch = _population()
    # Actual Finish EQUALS <null> → matches the unfinished T1, not the finished T4
    crit = leaf("EQUALS", "Actual Finish", "ACTUAL_FINISH", NULL)
    assert _match(sch, 1, crit) and not _match(sch, 4, crit)


def test_empty_string_equals_and_not_equals() -> None:
    sch = _population()
    assert _match(sch, 1, leaf("EQUALS", "Text19", "TEXT19", lit("")))  # T1 Risk ID is ""
    assert _match(sch, 2, leaf("DOES_NOT_EQUAL", "Text19", "TEXT19", lit("")))  # T2 is "R-9"


def test_null_lhs_sorts_greater_in_ordered_compare() -> None:
    sch = _population()
    # T4 has no Start (None). START >= a real date: null LHS sorts GREATER → True; < → False.
    ge = leaf(
        "IS_GREATER_THAN_OR_EQUAL_TO", "Start", "START", lit("2027-01-01T00:00", "LocalDateTime")
    )
    lt = leaf("IS_LESS_THAN", "Start", "START", lit("2027-01-01T00:00", "LocalDateTime"))
    assert _match(sch, 4, ge) and not _match(sch, 4, lt)


def test_is_within_inclusive_and_order_independent() -> None:
    sch = _population()
    # T1 Start 2027-01-01 is within [2026-12-01, 2027-02-01] and within the flipped bounds too
    lo, hi = lit("2026-12-01T00:00", "LocalDateTime"), lit("2027-02-01T00:00", "LocalDateTime")
    assert _match(sch, 1, leaf("IS_WITHIN", "Start", "START", lo, hi))
    assert _match(sch, 1, leaf("IS_WITHIN", "Start", "START", hi, lo))  # order-independent
    assert _match(
        sch,
        1,
        leaf("IS_NOT_WITHIN", "Start", "START", lit("2028-01-01T00:00"), lit("2028-02-01T00:00")),
    )


def test_field_to_field_duration_compare() -> None:
    sch = _population()
    # Duration9 > Duration8: T1 (Worst 2d > Best 1d) True; T2 (Worst 1d > Best 2d) False
    crit = leaf("IS_GREATER_THAN", "Duration9", "DURATION9", fld("Duration8", "DURATION8"))
    assert _match(sch, 1, crit) and not _match(sch, 2, crit)


def test_and_or_short_circuit_and_empty_branch() -> None:
    sch = _population()
    # AND requires all; OR requires any; an empty branch passes everything
    both = AND(
        leaf("EQUALS", "Active", "ACTIVE", lit("true", "Boolean")),
        leaf("EQUALS", "Summary", "SUMMARY", lit("false", "Boolean")),
    )
    assert _match(sch, 1, both) and not _match(sch, 5, both)  # T5 inactive fails AND
    assert _match(
        sch,
        5,
        OR(
            leaf("EQUALS", "Active", "ACTIVE", lit("false", "Boolean")),
            leaf("EQUALS", "Summary", "SUMMARY", lit("true", "Boolean")),
        ),
    )
    assert _match(sch, 1, Criterion(operator="AND"))  # empty AND → match-all


def test_is_any_value_and_none_criteria_match_all() -> None:
    sch = _population()
    assert _match(sch, 3, leaf("IS_ANY_VALUE", "Task Name", "NAME"))
    assert select(sch, SavedFilter(name="All Tasks", criteria=None)) == (1, 2, 3, 4, 5)


# --- the 10 real filters (ground truth) --------------------------------------------------------
def test_the_ten_real_filters_select_the_expected_uids() -> None:
    sch = _population()

    def sel(crit: Criterion | None, **kw: object) -> tuple[int, ...]:
        return select(sch, SavedFilter(name="f", criteria=crit), kw.get("prompts"))  # type: ignore[arg-type]

    # All Tasks / All Resources — match-all
    assert sel(None) == (1, 2, 3, 4, 5)
    # SVT- / No SVT- / SVT — case-insensitive substring on the name
    assert sel(leaf("CONTAINS", "Task Name", "NAME", lit("SVT-"))) == (1,)
    assert sel(leaf("DOES_NOT_CONTAIN", "Task Name", "NAME", lit("SVT-"))) == (2, 3, 4, 5)
    assert sel(leaf("CONTAINS", "Task Name", "NAME", lit("SVT"))) == (1, 2)
    # CAM_Tasks — AND(Text9 == "ZIN", Start <= a late date)
    cam = AND(
        leaf("EQUALS", "Text9", "TEXT9", lit("ZIN")),
        leaf("IS_LESS_THAN_OR_EQUAL_TO", "Start", "START", lit("2028-09-29T17:00")),
    )
    assert sel(cam) == (1,)
    # _MCexportedTasks — Flag6 == true
    assert sel(leaf("EQUALS", "Flag6", "FLAG6", lit("true", "Boolean"))) == (1,)
    # _MCTasks — the 8-condition AND (incl. the field-to-field Duration9 > Duration8)
    mc = AND(
        leaf("EQUALS", "Summary", "SUMMARY", lit("false", "Boolean")),
        leaf("IS_GREATER_THAN", "Duration9", "DURATION9", fld("Duration8", "DURATION8")),
        leaf("IS_GREATER_THAN_OR_EQUAL_TO", "Duration8", "DURATION8", lit("0.0d", "Duration")),
        leaf("IS_GREATER_THAN_OR_EQUAL_TO", "Duration9", "DURATION9", lit("0.0d", "Duration")),
        leaf("EQUALS", "Text19", "TEXT19", lit("")),
        leaf("EQUALS", "Actual Finish", "ACTUAL_FINISH", NULL),
        leaf("EQUALS", "Active", "ACTIVE", lit("true", "Boolean")),
        leaf("EQUALS", "Milestone", "MILESTONE", lit("false", "Boolean")),
    )
    assert sel(mc) == (1,)
    # _RiskRegTasks — AND(Summary==false, Text19 != "", Actual Finish == null, Active==true)
    rr = AND(
        leaf("EQUALS", "Summary", "SUMMARY", lit("false", "Boolean")),
        leaf("DOES_NOT_EQUAL", "Text19", "TEXT19", lit("")),
        leaf("EQUALS", "Actual Finish", "ACTUAL_FINISH", NULL),
        leaf("EQUALS", "Active", "ACTIVE", lit("true", "Boolean")),
    )
    assert sel(rr) == (2,)


def test_date_range_prompt_filter() -> None:
    sch = _population()
    # Date Range... = AND(Finish >= after, Start <= before), two interactive prompts
    dr = SavedFilter(
        name="Date Range...",
        prompt_count=2,
        show_related_summary_rows=True,
        criteria=AND(
            leaf("IS_GREATER_THAN_OR_EQUAL_TO", "Finish", "FINISH", prompt("after:")),
            leaf("IS_LESS_THAN_OR_EQUAL_TO", "Start", "START", prompt("before:")),
        ),
    )
    assert required_prompts(dr) == ("after:", "before:")
    prompts = {"after:": dt.datetime(2027, 1, 1), "before:": dt.datetime(2027, 1, 31)}
    # T1 (Start 1/1, Finish 1/5) is inside the window; T2 (Start 2/1) is not
    assert select(sch, dr, prompts) == (1,)  # type: ignore[arg-type]


# --- ADR-0354: duration literals conform to the vendored MPXJ Duration.convertUnits -----------


def test_duration_literal_table_matches_mpxj_convert_units() -> None:
    """Every factor decoded from the mpxj-16.2.0 bytecode, pinned (ADR-0354).

    Ordinary units scale by the schedule's OWN properties (week = minutes-per-week, NOT
    5 x day; year = minutes-per-week x 52); elapsed units are wall-clock constants
    (year = 364 d = 52x7); ``%``/``e%`` pass through unscaled (the bytecode's switch
    default); an unknown token fails closed — Duration.toString() is a closed vocabulary.
    """
    std = Calendar()
    ten = Calendar(working_minutes_per_day=600, minutes_per_week=3000, days_per_month=22)
    ten_no_props = Calendar(working_minutes_per_day=600)  # file declared no MPW/DPM

    # ordinary units, standard calendar (MPXJ defaults 2400 mpw / 20 dpm)
    assert _parse_duration_literal("5.0d", std) == 2400
    assert _parse_duration_literal("1.0w", std) == 2400
    assert _parse_duration_literal("1.0mo", std) == 9600
    assert _parse_duration_literal("1.0y", std) == 124800  # mpw x 52 — NOT v1's 240-day 115200
    assert _parse_duration_literal("3", std) == 1440  # bare number = days (MSP default unit)
    assert _parse_duration_literal("5 days", std) == 2400  # long-form alias (typed prompts)
    assert _parse_duration_literal("90.0m", std) == 90
    assert _parse_duration_literal("2.0h", std) == 120

    # ordinary units scale on the schedule's DECLARED properties
    assert _parse_duration_literal("1.0d", ten) == 600
    assert _parse_duration_literal("1.0w", ten) == 3000
    assert _parse_duration_literal("1.0mo", ten) == 600 * 22
    assert _parse_duration_literal("1.0y", ten) == 3000 * 52
    # absent MPW/DPM fall back to MPXJ's own defaults — never a derived 5 x day guess
    assert _parse_duration_literal("1.0w", ten_no_props) == 2400
    assert _parse_duration_literal("1.0mo", ten_no_props) == 600 * 20

    # elapsed units are calendar-blind wall-clock constants, on EVERY calendar
    for cal in (std, ten):
        assert _parse_duration_literal("2.0ed", cal) == 2880
        assert _parse_duration_literal("1.5ed", cal) == 2160
        assert _parse_duration_literal("1.0ew", cal) == 10080
        assert _parse_duration_literal("1.0emo", cal) == 43200
        assert _parse_duration_literal("1.0ey", cal) == 524160  # 364 days, MPXJ's 52x7
        assert _parse_duration_literal("30.0em", cal) == 30
        assert _parse_duration_literal("2.0eh", cal) == 120
        assert _parse_duration_literal("3 edays", cal) == 4320  # alias under the marker

    # percent pseudo-durations pass through unscaled (bytecode switch default, mirrored)
    assert _parse_duration_literal("5.0%", std) == 5
    assert _parse_duration_literal("5.0e%", std) == 5

    # unknown tokens fail closed — no silent 480-minute guess (v1's defect)
    assert _parse_duration_literal("5 xyz", std) is None
    assert _parse_duration_literal("5.0e2", std) is None  # scientific notation is not a literal
    assert _parse_duration_literal("abc", std) is None
    assert _parse_duration_literal("", std) is None


def _duration_population() -> Schedule:
    """The V3 executed example (VALIDATION-20260729 §V3c): 8 tasks at 1..8 working days."""
    tasks = tuple(Task(unique_id=u, name=f"D{u}", duration_minutes=u * DAY) for u in range(1, 9))
    return Schedule(
        name="v3", project_start=dt.datetime(2027, 1, 4, 8), tasks=tasks, relationships=()
    )


def _dur_gt(text: str) -> SavedFilter:
    return SavedFilter(
        name=f"Duration > {text}",
        criteria=leaf("IS_GREATER_THAN", "Duration", "DURATION", lit(text, "Duration")),
    )


def test_the_v3_executed_example_reads_elapsed_as_elapsed() -> None:
    """The audit's own falsifying case, inverted into the pin (ADR-0354).

    v1 read 'Duration > 2.0ed' identically to '> 2.0d' (6 matches). Elapsed 2 days is 2880
    wall-clock minutes = 48 h; on the hours axis MPXJ compares 48 h against working durations
    (6 working days = 48 h), so only the 7- and 8-day tasks exceed it."""
    sch = _duration_population()
    assert select(sch, _dur_gt("2.0d")) == (3, 4, 5, 6, 7, 8)
    assert select(sch, _dur_gt("2.0ed")) == (7, 8)  # v1 returned (3, 4, 5, 6, 7, 8)
    assert select(sch, _dur_gt("2.0xyz")) == ()  # unknown unit fails closed (v1: 6 matches)


def test_selection_migration_delta_reports_the_movement() -> None:
    """(v1, v2) selections for a version-sensitive filter; None when version-invariant."""
    sch = _duration_population()
    delta = selection_migration_delta(sch, _dur_gt("2.0ed"))
    assert delta == ((3, 4, 5, 6, 7, 8), (7, 8))
    # after the report the live evaluator is back on v2 (the ContextVar reset)
    assert select(sch, _dur_gt("2.0ed")) == (7, 8)
    # a filter with no duration literal is version-invariant -> no report
    name_only = SavedFilter(name="svt", criteria=leaf("CONTAINS", "Name", "NAME", lit("D")))
    assert selection_migration_delta(sch, name_only) is None
    # field-to-field duration comparison stays on the stored-minutes axis in every version
    f2f = SavedFilter(
        name="wc>bc",
        criteria=leaf("IS_GREATER_THAN", "Duration9", "DURATION9", fld("Duration8", "DURATION8")),
    )
    assert selection_migration_delta(sch, f2f) is None


def test_prompt_answers_coerce_on_the_schedules_own_calendar() -> None:
    """A duration-typed prompt answer scales per schedule (ADR-0354): '3d' is 1,800 minutes
    on a 10-hour file and 1,440 on the standard calendar."""
    dr = SavedFilter(
        name="Longer than...",
        prompt_count=1,
        criteria=leaf("IS_GREATER_THAN", "Duration", "DURATION", prompt("longer than:")),
    )
    std = coerce_prompt_answers(dr, {"longer than:": "3d"}, Calendar())
    ten = coerce_prompt_answers(dr, {"longer than:": "3d"}, Calendar(working_minutes_per_day=600))
    assert std == {"longer than:": 1440}
    assert ten == {"longer than:": 1800}
