"""Session-wide saved grouping + A-Z union helpers (feature #10, PR-C).

Covers ``group_by_clauses`` (single/multi-clause ordering, ascending/descending, ``groupOn=2``
interval banding, the raw-custom-field two-hop, and the unresolvable degrade-to-ungrouped rule),
the ``&``-accelerator-stripped display names, and the A-Z union / find helpers over several
versions, plus the shared ``filter_to_uids`` / ``with_ancestors`` reduction primitives.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.grouping import filter_to_uids, with_ancestors
from schedule_forensics.engine.saved_grouping import (
    find_saved_filter,
    find_saved_group,
    group_by_clauses,
    group_first_field,
    saved_filters_union,
    saved_groups_union,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.saved_view import GroupClause, SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480
RAW_MAP = (("Text9", "IPT/ SUB"),)


def _t(uid: int, name: str, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=DAY, **kw)  # type: ignore[arg-type]


def _sch(*tasks: Task, **kw: object) -> Schedule:
    return Schedule(
        name="s",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=tasks,
        custom_field_by_raw_name=RAW_MAP,
        **kw,  # type: ignore[arg-type]
    )


def _clause(
    field: str, enum: str, *, ascending: bool = True, group_on: int = 0, interval: str | None = None
) -> GroupClause:
    return GroupClause(
        field=field, field_enum=enum, ascending=ascending, group_on=group_on, interval=interval
    )  # fmt: skip


# --- group_by_clauses ---------------------------------------------------------------------------


def test_single_clause_boolean_groups_and_orders() -> None:
    sch = _sch(
        _t(1, "a", is_milestone=True),
        _t(2, "b", is_milestone=False),
        _t(3, "c", is_milestone=True),
    )
    # ascending on a boolean: No (false) before Yes (true)
    asc = SavedGroup(name="M", clauses=(_clause("Milestone", "MILESTONE"),))
    assert group_by_clauses(sch, asc) == [("No", (2,)), ("Yes", (1, 3))]
    # descending flips the bucket order
    desc = SavedGroup(name="M", clauses=(_clause("Milestone", "MILESTONE", ascending=False),))
    assert group_by_clauses(sch, desc) == [("Yes", (1, 3)), ("No", (2,))]


def test_multi_clause_nested_ordering() -> None:
    # group by Milestone then by Name: the first clause is the outer bucket
    sch = _sch(
        _t(1, "zebra", is_milestone=True),
        _t(2, "apple", is_milestone=False),
        _t(3, "alpha", is_milestone=True),
    )
    grp = SavedGroup(
        name="MN",
        clauses=(_clause("Milestone", "MILESTONE"), _clause("Task Name", "NAME")),
    )
    # No/apple, then Yes/alpha, Yes/zebra (name ascending within the Yes bucket)
    assert group_by_clauses(sch, grp) == [
        ("No / apple", (2,)),
        ("Yes / alpha", (3,)),
        ("Yes / zebra", (1,)),
    ]


def test_group_on_interval_bands_percent_complete() -> None:
    sch = _sch(
        _t(1, "a", percent_complete=0.0),
        _t(2, "b", percent_complete=45.0),
        _t(3, "c", percent_complete=55.0),
        _t(4, "d", percent_complete=100.0),
    )
    grp = SavedGroup(
        name="P",
        clauses=(_clause("% Complete", "PERCENT_COMPLETE", group_on=2, interval="50"),),
    )
    # 50-wide bands: [0,50) has 0 & 45; [50,100) has 55; [100,150) has 100
    assert group_by_clauses(sch, grp) == [
        ("0-50", (1, 2)),
        ("50-100", (3,)),
        ("100-150", (4,)),
    ]


def test_custom_raw_field_two_hop_grouping() -> None:
    # a group clause references the RAW name Text9; the task stores it under the label "IPT/ SUB"
    sch = _sch(
        _t(1, "a", custom_fields=(("IPT/ SUB", "ZIN"),)),
        _t(2, "b", custom_fields=(("IPT/ SUB", "ACME"),)),
        _t(3, "c", custom_fields=(("IPT/ SUB", "ZIN"),)),
    )
    grp = SavedGroup(name="T", clauses=(_clause("Text9", "TEXT9"),))
    assert group_by_clauses(sch, grp) == [("ACME", (2,)), ("ZIN", (1, 3))]


def test_blank_values_bucket_together_as_none() -> None:
    sch = _sch(
        _t(1, "a", custom_fields=(("IPT/ SUB", "ZIN"),)),
        _t(2, "b"),  # no Text9 → None
    )
    grp = SavedGroup(name="T", clauses=(_clause("Text9", "TEXT9"),))
    assert group_by_clauses(sch, grp) == [("ZIN", (1,)), ("(none)", (2,))]


def test_unresolvable_first_clause_degrades_to_ungrouped() -> None:
    sch = _sch(_t(1, "a"), _t(2, "b"))
    grp = SavedGroup(name="X", clauses=(_clause("Board Status", "BOARD_STATUS"),))
    assert group_by_clauses(sch, grp) == [("(ungrouped)", (1, 2))]


def test_duration_text_enum_resolves_like_duration() -> None:
    # MPXJ names the Duration group column DURATION_TEXT (audit F1); it must group, not degrade.
    sch = _sch(
        Task(unique_id=1, name="a", duration_minutes=DAY),
        Task(unique_id=2, name="b", duration_minutes=2 * DAY),
        Task(unique_id=3, name="c", duration_minutes=DAY),
    )
    grp = SavedGroup(name="Dur", clauses=(_clause("Duration", "DURATION_TEXT"),))
    assert group_by_clauses(sch, grp) == [("1d", (1, 3)), ("2d", (2,))]


def test_percent_complete_interval_zero_is_complete_incomplete_split() -> None:
    # MS Project's "Complete and Incomplete Tasks": groupOn=2, interval="0" → two buckets, not one
    # per distinct percentage (audit F2).
    sch = _sch(
        _t(1, "a", percent_complete=0.0),
        _t(2, "b", percent_complete=50.0),
        _t(3, "c", percent_complete=100.0),
    )
    grp = SavedGroup(
        name="CI",
        clauses=(_clause("% Complete", "PERCENT_COMPLETE", group_on=2, interval="0"),),
    )
    assert group_by_clauses(sch, grp) == [("Incomplete", (1, 2)), ("Complete", (3,))]


def test_priority_and_status_groups_resolve() -> None:
    # PR-C.2: the "Priority" (numeric each-value) and computed "Status" groups.
    sch = Schedule(
        name="s",
        source_file="Plan.mpp",
        project_start=dt.datetime(2027, 1, 1, 8),
        status_date=dt.datetime(2027, 2, 1, 8),
        tasks=(
            Task(unique_id=1, name="done", duration_minutes=DAY, percent_complete=100.0,
                 priority=500),
            Task(unique_id=2, name="later", duration_minutes=DAY,
                 start=dt.datetime(2027, 3, 1, 8), priority=750),
            Task(unique_id=3, name="behind", duration_minutes=DAY,
                 start=dt.datetime(2027, 1, 4, 8), priority=500),
        ),
    )  # fmt: skip
    pri = SavedGroup(name="P", clauses=(_clause("Priority", "PRIORITY"),))
    assert group_by_clauses(sch, pri) == [("500", (1, 3)), ("750", (2,))]
    status = SavedGroup(name="S", clauses=(_clause("Status", "STATUS"),))
    assert group_by_clauses(sch, status) == [
        ("Complete", (1,)),
        ("Future Task", (2,)),
        ("Late", (3,)),
    ]
    proj = SavedGroup(name="Pr", clauses=(_clause("Project", "PROJECT"),))
    assert group_by_clauses(sch, proj) == [("Plan", (1, 2, 3))]


def test_task_mode_groups_auto_vs_manual() -> None:
    # the "Auto Scheduled vs. Manually Scheduled" group, derived from is_manual (audit F3).
    sch = _sch(_t(1, "a", is_manual=False), _t(2, "b", is_manual=True), _t(3, "c", is_manual=False))
    grp = SavedGroup(name="TM", clauses=(_clause("Task Mode", "TASK_MODE"),))
    assert group_by_clauses(sch, grp) == [
        ("Auto Scheduled", (1, 3)),
        ("Manually Scheduled", (2,)),
    ]


def test_no_clauses_is_one_ungrouped_bucket_and_empty_schedule_is_empty() -> None:
    sch = _sch(_t(1, "a"), _t(2, "b"))
    assert group_by_clauses(sch, SavedGroup(name="None")) == [("(ungrouped)", (1, 2))]
    assert group_by_clauses(_sch(), SavedGroup(name="None")) == []


def test_group_first_field() -> None:
    assert group_first_field(None) is None
    assert group_first_field(SavedGroup(name="e")) is None
    assert group_first_field(SavedGroup(name="g", clauses=(_clause("Text9", "TEXT9"),))) == "Text9"


# --- A-Z union / display names / find -----------------------------------------------------------


def test_display_name_strips_accelerator() -> None:
    assert SavedGroup(name="&No Group").display_name == "No Group"
    assert SavedGroup(name="Mi&lestones").display_name == "Milestones"
    assert SavedFilter(name="C&ritical").display_name == "Critical"
    assert SavedFilter(name="A && B").display_name == "A & B"  # literal ampersand preserved


def test_unions_dedupe_by_name_and_sort_case_insensitively() -> None:
    fa = SavedFilter(name="zeta")
    fb = SavedFilter(name="Alpha")
    fc = SavedFilter(name="Alpha")  # duplicate name across versions
    ga = SavedGroup(name="&No Group")
    gb = SavedGroup(name="Milestones")
    v1 = _sch(_t(1, "a"), saved_filters=(fa, fb), saved_groups=(ga,))
    v2 = _sch(_t(1, "a"), saved_filters=(fc,), saved_groups=(gb, ga))
    filters = saved_filters_union([v1, v2])
    assert [f.name for f in filters] == ["Alpha", "zeta"]  # deduped, A-Z case-insensitive
    groups = saved_groups_union([v1, v2])
    assert [g.display_name for g in groups] == ["Milestones", "No Group"]


def test_find_saved_filter_and_group_by_exact_name() -> None:
    v = _sch(
        _t(1, "a"),
        saved_filters=(SavedFilter(name="SVT-"),),
        saved_groups=(SavedGroup(name="Mi&lestones"),),
    )
    assert find_saved_filter([v], "SVT-") is not None
    assert find_saved_filter([v], "nope") is None
    assert find_saved_group([v], "Mi&lestones") is not None  # exact stored name, not display
    assert find_saved_group([v], "Milestones") is None


# --- shared reduction primitives ----------------------------------------------------------------


def test_filter_to_uids_keeps_only_internal_relationships() -> None:
    sch = Schedule(
        name="s",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=(_t(1, "a"), _t(2, "b"), _t(3, "c")),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )
    reduced = filter_to_uids(sch, frozenset({1, 2}))
    assert {t.unique_id for t in reduced.tasks} == {1, 2}
    # only the 1->2 relationship survives; 2->3 touches the dropped task 3
    assert [(r.predecessor_id, r.successor_id) for r in reduced.relationships] == [(1, 2)]
    assert filter_to_uids(sch, frozenset()).tasks == ()  # empty selection → task-less copy


def test_with_ancestors_adds_summary_parents() -> None:
    sch = _sch(
        _t(1, "Phase", is_summary=True, outline_level=1),
        _t(2, "Sub", is_summary=True, outline_level=2),
        _t(3, "Leaf", outline_level=3),
        _t(4, "Other", outline_level=1),
    )
    # matching the deep leaf pulls in both summary ancestors, not the unrelated sibling
    assert with_ancestors(sch, frozenset({3})) == frozenset({1, 2, 3})
    assert with_ancestors(sch, frozenset()) == frozenset()
