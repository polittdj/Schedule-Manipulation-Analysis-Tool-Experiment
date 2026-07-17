"""XER importer tests — field coverage on a synthetic fixture + loud failures."""

from __future__ import annotations

import datetime as dt
import zlib
from pathlib import Path

import pytest

from schedule_forensics.importers import ImporterError, parse_xer, parse_xer_text
from schedule_forensics.model import (
    ConstraintType,
    RelationshipType,
    ResourceType,
    Schedule,
)

FIXTURE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "xer" / "commercial_construction.xer"
)


def _uid(task_code: str) -> int:
    """The stable Activity-ID UniqueID the importer derives when every in-scope task
    carries a unique ``task_code`` (ADR-0185) — CRC32 of the code, masked to 31 bits."""
    return zlib.crc32(task_code.encode("utf-8")) & 0x7FFFFFFF


# the curated fixture's Activity IDs (its TASK table carries task_code on every row,
# so the importer keys tasks by the stable Activity-ID identity, not raw task_id)
UID_SUMMARY = _uid("WBS-CC")  # raw task_id 2000
UID_DESIGN = _uid("A1000")  # raw task_id 2001
UID_PERMIT = _uid("A1010")  # raw task_id 2002
UID_CONSTR = _uid("A1020")  # raw task_id 2003
UID_MILESTONE = _uid("A1030")  # raw task_id 2004


@pytest.fixture(scope="module")
def schedule() -> Schedule:
    return parse_xer(FIXTURE)


def _rel(schedule: Schedule, predecessor: int, successor: int) -> RelationshipType:
    for rel in schedule.relationships:
        if rel.predecessor_id == predecessor and rel.successor_id == successor:
            return rel.type
    raise AssertionError(f"no relationship {predecessor}->{successor}")


# --- project frame ----------------------------------------------------------------


def test_project_frame(schedule: Schedule) -> None:
    assert schedule.name == "CC-A"
    assert schedule.source_file == "commercial_construction.xer"
    assert schedule.project_start == dt.datetime(2025, 1, 6, 8, 0)
    assert schedule.project_finish == dt.datetime(2025, 3, 31, 17, 0)
    assert schedule.status_date == dt.datetime(2025, 2, 1, 17, 0)
    assert schedule.baseline_finish is None  # P6 baseline is a separate project (deferred)
    assert set(schedule.tasks_by_id) == {
        UID_SUMMARY,
        UID_DESIGN,
        UID_PERMIT,
        UID_CONSTR,
        UID_MILESTONE,
    }


# --- the fully-populated task -----------------------------------------------------


def test_fully_populated_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(UID_DESIGN)
    assert t.name == "Schematic Design"
    assert t.wbs == "CC.DESIGN"  # PROJWBS root->leaf path
    assert t.duration_minutes == 4800  # 80h * 60
    assert t.remaining_duration_minutes == 0
    assert t.is_milestone is False
    assert t.is_summary is False
    assert t.is_level_of_effort is False
    assert t.constraint_type is ConstraintType.SNET  # CS_MSOA
    assert t.constraint_date == dt.datetime(2025, 1, 6, 8, 0)
    assert t.percent_complete == 100.0
    assert t.physical_percent_complete == 100.0  # complete_pct_type CP_Phys
    assert t.start == dt.datetime(2025, 1, 6, 8, 0)  # early_start_date
    assert t.finish == dt.datetime(2025, 1, 17, 17, 0)  # early_end_date
    assert t.actual_start == dt.datetime(2025, 1, 6, 8, 0)
    assert t.actual_finish == dt.datetime(2025, 1, 17, 16, 30)
    assert t.baseline_start == dt.datetime(2025, 1, 6, 8, 0)  # target_start_date
    assert t.baseline_finish == dt.datetime(2025, 1, 17, 17, 0)  # target_end_date
    assert t.resource_ids == (100,)
    assert t.resource_names == ("Architect",)


def test_partial_progress_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(UID_PERMIT)
    assert t.wbs == "CC.DESIGN"
    assert t.constraint_type is ConstraintType.MSO  # CS_MSO
    assert t.duration_minutes == 2400  # 40h
    assert t.remaining_duration_minutes == 960  # 16h
    assert t.percent_complete == 40.0
    assert t.physical_percent_complete == 40.0
    assert t.actual_finish is None  # blank act_end_date
    assert t.finish == dt.datetime(2025, 1, 24, 17, 0)  # early_end_date
    assert t.baseline_start is None  # blank target_start_date (no P6 baseline project)


def test_multi_resource_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(UID_CONSTR)
    assert t.wbs == "CC.CONSTR"
    assert t.constraint_type is ConstraintType.FNLT  # CS_MEOB
    assert t.duration_minutes == 9600  # 160h
    assert t.resource_ids == (100, 101, 102)
    assert t.resource_names == ("Architect", "Concrete", "Crane")
    assert t.baseline_start == dt.datetime(2025, 1, 27, 8, 0)
    assert t.baseline_finish == dt.datetime(2025, 3, 15, 17, 0)


def test_classification_flags(schedule: Schedule) -> None:
    assert schedule.task_by_id(UID_MILESTONE).is_milestone is True  # TT_FinMile
    assert schedule.task_by_id(UID_MILESTONE).constraint_type is ConstraintType.ASAP  # no cstr_type
    assert schedule.task_by_id(UID_MILESTONE).start == dt.datetime(2025, 3, 15, 17, 0)
    summary = schedule.task_by_id(UID_SUMMARY)
    assert summary.is_summary is True  # TT_WBS
    assert summary.wbs == "CC"  # root WBS node


# --- relationships ---------------------------------------------------------------


def test_relationship_types_and_topology(schedule: Schedule) -> None:
    assert len(schedule.relationships) == 5
    assert _rel(schedule, UID_DESIGN, UID_PERMIT) is RelationshipType.FS
    assert _rel(schedule, UID_PERMIT, UID_CONSTR) is RelationshipType.SS
    assert _rel(schedule, UID_DESIGN, UID_CONSTR) is RelationshipType.FF
    assert _rel(schedule, UID_CONSTR, UID_MILESTONE) is RelationshipType.FS
    assert _rel(schedule, UID_PERMIT, UID_MILESTONE) is RelationshipType.SF


def test_lag_and_lead(schedule: Schedule) -> None:
    fs = next(
        r
        for r in schedule.relationships
        if (r.predecessor_id, r.successor_id) == (UID_DESIGN, UID_PERMIT)
    )
    assert fs.lag_minutes == 480  # 8h lag
    lead = next(
        r
        for r in schedule.relationships
        if (r.predecessor_id, r.successor_id) == (UID_CONSTR, UID_MILESTONE)
    )
    assert lead.lag_minutes == -240  # -4h lead
    assert lead.is_lead is True


# --- resources -------------------------------------------------------------------


def test_resources(schedule: Schedule) -> None:
    assert set(schedule.resources_by_id) == {100, 101, 102}
    assert schedule.resource_by_id(100).type is ResourceType.WORK  # RT_Labor
    assert schedule.resource_by_id(100).standard_rate == 150.0
    assert schedule.resource_by_id(101).type is ResourceType.MATERIAL  # RT_Mat
    assert schedule.resource_by_id(101).standard_rate == 95.5
    assert schedule.resource_by_id(102).type is ResourceType.WORK  # RT_Equip
    assert schedule.resource_by_id(102).standard_rate == 220.0


# --- helpers for tiny inline documents -------------------------------------------


def _xer(tables: list[tuple[str, list[str], list[list[str]]]]) -> str:
    lines = ["ERMHDR\t19.12\t2025-02-01"]
    for name, fields, rows in tables:
        lines.append("%T\t" + name)
        lines.append("%F\t" + "\t".join(fields))
        lines.extend("%R\t" + "\t".join(row) for row in rows)
    lines.append("%E")
    return "\n".join(lines)


_MIN_PROJECT = (
    "PROJECT",
    ["proj_id", "proj_short_name", "plan_start_date"],
    [["1", "P1", "2025-01-06 08:00"]],
)


# --- loud-failure / edge cases ---------------------------------------------------


def test_unreadable_file_raises() -> None:
    with pytest.raises(ImporterError, match="cannot read"):
        parse_xer("/no/such/file.xer")


def test_no_project_table_raises() -> None:
    text = _xer([("TASK", ["task_id", "task_name"], [["1", "A"]])])
    with pytest.raises(ImporterError, match="no PROJECT"):
        parse_xer_text(text)


def test_missing_plan_start_raises() -> None:
    text = _xer([("PROJECT", ["proj_id", "proj_short_name"], [["1", "P1"]])])
    with pytest.raises(ImporterError, match="plan_start_date"):
        parse_xer_text(text)


def test_non_integer_task_id_raises() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["abc", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    with pytest.raises(ImporterError, match="integer for 'task_id'"):
        parse_xer_text(text)


def test_dangling_relationship_is_dropped() -> None:
    # filtered/partial P6 exports legitimately carry TASKPRED rows whose endpoint is not
    # in the file — the real-world tolerance class drops the row, never the whole file
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["10", "999", "PR_FS", "0"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.relationships == ()


def test_project_title_is_the_project_short_name() -> None:
    """v4 grouped ingestion: XER has no exact document Title, so ``project_title`` is the best-
    available real project identity — ``proj_short_name`` (None when absent)."""
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.project_title == "P1"
    assert sched.name == "P1"


def test_duplicate_task_id_raises() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"], ["10", "1", "B", "TT_Task", "8"]],
            ),
        ]
    )
    with pytest.raises(ImporterError, match="valid schedule"):
        parse_xer_text(text)


def test_multi_project_selection_and_cross_project_link_dropped() -> None:
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date"],
                [["1", "P1", "2025-01-06 08:00"], ["2", "P2", "2025-02-01 08:00"]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [
                    ["10", "2", "A", "TT_Task", "8"],
                    ["11", "2", "B", "TT_Task", "8"],
                    ["20", "1", "C", "TT_Task", "8"],
                ],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["11", "10", "PR_FS", "0"], ["11", "20", "PR_FS", "0"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    # Project 2 owns more tasks -> selected; its plan_start_date is used.
    assert sched.name == "P2"
    assert sched.project_start == dt.datetime(2025, 2, 1, 8, 0)
    assert set(sched.tasks_by_id) == {10, 11}
    # 10->11 kept; cross-project 20->11 dropped (20 is out of scope, not an error).
    assert len(sched.relationships) == 1
    assert _rel(sched, 10, 11) is RelationshipType.FS


def test_fields_read_by_name_not_position() -> None:
    # Columns deliberately reordered; reading is by %F name, so it still parses.
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_name", "target_drtn_hr_cnt", "task_type", "proj_id", "task_id"],
                [["Reordered", "8", "TT_Task", "1", "42"]],
            ),
        ]
    )
    t = parse_xer_text(text).task_by_id(42)
    assert t.name == "Reordered"
    assert t.duration_minutes == 480


def test_short_row_pads_missing_trailing_fields() -> None:
    # A row shorter than its %F header -> trailing fields default to blank, no error.
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt", "cstr_type"],
                [["7", "1", "Stub", "TT_Task"]],
            ),  # missing duration + cstr_type
        ]
    )
    t = parse_xer_text(text).task_by_id(7)
    assert t.duration_minutes == 0
    assert t.constraint_type is ConstraintType.ASAP


def test_encoding_fallback_to_cp1252(tmp_path: Path) -> None:
    # A non-UTF-8 (cp1252) byte in a resource name must not crash the read.
    rows = [
        "ERMHDR\t19.12",
        "%T\tPROJECT",
        "%F\tproj_id\tproj_short_name\tplan_start_date",
        "%R\t1\tP1\t2025-01-06 08:00",
        "%T\tRSRC",
        "%F\trsrc_id\trsrc_name\trsrc_type",
        "%R\t1\tBéton\tRT_Mat",  # 'é' encoded as cp1252 byte 0xE9
        "%E",
    ]
    path = tmp_path / "latin1.xer"
    path.write_bytes("\n".join(rows).encode("cp1252"))
    sched = parse_xer(path)
    assert sched.resource_by_id(1).name == "Béton"


def test_blank_lines_and_orphan_records_ignored() -> None:
    # Hand-built (no %E) so the table loop also exits naturally; blank lines and
    # records appearing before any %T are ignored rather than crashing.
    text = "\n".join(
        [
            "",  # blank line
            "%R\torphan\trow",  # %R before any %T -> ignored
            "%T",  # %T with no table name -> no table opened
            "%R\t1\t2",  # %R with no current table -> ignored
            "ERMHDR\t19.12",  # header -> ignored
            "%T\tPROJECT",
            "%F\tproj_id\tproj_short_name\tplan_start_date",
            "%R\t1\tP1\t2025-01-06 08:00",
            "%T\tTASK",
            "%F\ttask_id\tproj_id\ttask_name\ttask_type\ttarget_drtn_hr_cnt",
            "%R\t1\t1\tA\tTT_Task\t8",
        ]
    )
    sched = parse_xer_text(text)
    assert set(sched.tasks_by_id) == {1}


def test_out_of_range_physical_percent_is_clamped() -> None:
    # 150% physical complete is data noise (tool quirks / P6 round-trips) — clamp to the
    # valid range like the MSPDI importer, never reject the whole file
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_name",
                    "task_type",
                    "phys_complete_pct",
                    "complete_pct_type",
                    "target_drtn_hr_cnt",
                    "act_start_date",
                ],
                [["1", "1", "A", "TT_Task", "150", "CP_Phys", "8", "2025-01-06 08:00"]],
            ),
        ]
    )
    task = parse_xer_text(text).tasks_by_id[1]
    assert task.physical_percent_complete == 100.0
    assert task.percent_complete == 100.0  # started + CP_Phys reads the (clamped) physical


def test_self_loop_relationship_is_dropped() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["10", "10", "PR_FS", "0"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.relationships == ()  # self-referential row dropped, schedule kept


def test_taskpred_missing_task_id_is_dropped_not_fatal() -> None:
    # Audit H4: a TASKPRED row with no resolvable endpoint (empty/missing or non-integer
    # task_id) is an unresolvable link, not corruption — it is dropped and counted, like a
    # dangling endpoint, rather than sinking the whole file.
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"]],
            ),
            ("TASKPRED", ["task_id", "pred_task_id", "pred_type"], [["", "10", "PR_FS"]]),
        ]
    )
    sched = parse_xer_text(text)  # must not raise
    assert sched.relationships == ()


def test_resource_rows_skipped_with_name_fallback() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "RSRC",
                ["rsrc_id", "rsrc_name", "rsrc_short_name", "rsrc_type", "cost_per_qty"],
                [
                    ["", "X", "XS", "RT_Labor", "10"],  # no rsrc_id -> skipped
                    ["6", "", "", "RT_Labor", "10"],  # no name at all -> skipped
                    ["5", "", "SHORT", "RT_Labor", "10"],
                ],
            ),  # rsrc_name blank -> falls back to short_name
        ]
    )
    sched = parse_xer_text(text)
    assert set(sched.resources_by_id) == {5}
    assert sched.resource_by_id(5).name == "SHORT"


def test_non_integer_rsrc_id_raises() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            ("RSRC", ["rsrc_id", "rsrc_name", "rsrc_type"], [["abc", "R", "RT_Labor"]]),
        ]
    )
    with pytest.raises(ImporterError, match="integer for 'rsrc_id'"):
        parse_xer_text(text)


def test_negative_rate_resource_raises() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "RSRC",
                ["rsrc_id", "rsrc_name", "rsrc_type", "cost_per_qty"],
                [["5", "R", "RT_Labor", "-5"]],
            ),
        ]
    )
    with pytest.raises(ImporterError, match="resource rsrc_id 5 is invalid"):
        parse_xer_text(text)


def test_duplicate_assignment_is_deduped() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
            ("RSRC", ["rsrc_id", "rsrc_name", "rsrc_type"], [["100", "Architect", "RT_Labor"]]),
            (
                "TASKRSRC",
                ["taskrsrc_id", "task_id", "rsrc_id"],
                [["1", "1", "100"], ["2", "1", "100"], ["3", "", "100"]],
            ),  # dup + a row missing task_id
        ]
    )
    t = parse_xer_text(text).task_by_id(1)
    assert t.resource_ids == (100,)  # deduped
    assert t.resource_names == ("Architect",)  # deduped


def test_assignment_to_undefined_resource_keeps_uid_without_name() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
            ("TASKRSRC", ["taskrsrc_id", "task_id", "rsrc_id"], [["1", "1", "999"]]),  # no RSRC 999
        ]
    )
    t = parse_xer_text(text).task_by_id(1)
    assert t.resource_ids == (999,)
    assert t.resource_names == ()


def test_wbs_path_edge_cases() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "PROJWBS",
                ["wbs_id", "proj_id", "parent_wbs_id", "wbs_short_name", "wbs_name"],
                [
                    ["", "1", "", "X", "ignored"],  # blank wbs_id -> skipped
                    ["W1", "1", "", "", ""],  # no name at all -> empty segment
                    ["W2", "1", "W1", "LEAF", "Leaf"],
                ],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "wbs_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [
                    ["1", "1", "W2", "A", "TT_Task", "8"],  # path skips the empty W1 segment
                    ["2", "1", "NOPE", "B", "TT_Task", "8"],  # wbs_id not in PROJWBS -> None
                    ["3", "1", "W1", "C", "TT_Task", "8"],
                ],
            ),  # only an empty segment -> None
        ]
    )
    sched = parse_xer_text(text)
    assert sched.task_by_id(1).wbs == "LEAF"
    assert sched.task_by_id(2).wbs is None
    assert sched.task_by_id(3).wbs is None


def test_alap_and_dateless_constraints_normalize_to_asap() -> None:
    # the same real-world tolerance class as MSPDI: ALAP (out of scope for the early-date
    # engine) and a date-requiring constraint with the date cleared both collapse to ASAP
    # instead of the CPM refusing the whole schedule
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_name",
                    "task_type",
                    "target_drtn_hr_cnt",
                    "cstr_type",
                    "cstr_date",
                ],
                [
                    ["1", "1", "A", "TT_Task", "8", "CS_ALAP", ""],
                    ["2", "1", "B", "TT_Task", "8", "CS_MSOA", ""],  # SNET, date cleared
                    ["3", "1", "C", "TT_Task", "8", "CS_MSOA", "2025-02-03 08:00"],
                ],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.tasks_by_id[1].constraint_type is ConstraintType.ASAP
    assert sched.tasks_by_id[2].constraint_type is ConstraintType.ASAP
    assert sched.tasks_by_id[2].constraint_date is None
    assert sched.tasks_by_id[3].constraint_type is ConstraintType.SNET  # dated one survives


def test_duration_percent_type_derives_progress_from_durations() -> None:
    # P6's default CP_Drtn keeps phys_complete_pct at 0 while work progresses; the
    # activity % must derive from remaining vs target duration (and actual dates rule)
    cols = [
        "task_id",
        "proj_id",
        "task_name",
        "task_type",
        "complete_pct_type",
        "phys_complete_pct",
        "target_drtn_hr_cnt",
        "remain_drtn_hr_cnt",
        "act_start_date",
        "act_end_date",
    ]
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                cols,
                [
                    # finished: actual end is a fact -> 100 even with phys 0
                    [
                        "1",
                        "1",
                        "Done",
                        "TT_Task",
                        "CP_Drtn",
                        "0",
                        "80",
                        "0",
                        "2025-01-06 08:00",
                        "2025-01-17 17:00",
                    ],
                    # in progress: 60 of 80 hours remain -> 25%
                    [
                        "2",
                        "1",
                        "Doing",
                        "TT_Task",
                        "CP_Drtn",
                        "0",
                        "80",
                        "60",
                        "2025-01-06 08:00",
                        "",
                    ],
                    # not started -> 0
                    ["3", "1", "Todo", "TT_Task", "CP_Drtn", "0", "80", "80", "", ""],
                ],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.tasks_by_id[1].percent_complete == 100.0
    assert sched.tasks_by_id[2].percent_complete == 25.0
    assert sched.tasks_by_id[3].percent_complete == 0.0


def test_units_percent_type_reads_taskrsrc_quantities() -> None:
    # P6 "Units % Complete" = actual ÷ at-completion units across the task's assignments
    # (at-completion = actual + remaining). Previously CP_Units approximated via the
    # duration share; with TASKRSRC quantities present the real basis is used.
    cols = [
        "task_id",
        "proj_id",
        "task_name",
        "task_type",
        "complete_pct_type",
        "target_drtn_hr_cnt",
        "remain_drtn_hr_cnt",
        "act_start_date",
        "act_end_date",
    ]
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                cols,
                [
                    # single assignment: (30 + 10) actual ÷ (40 + 60) at-completion = 40%
                    ["1", "1", "Single", "TT_Task", "CP_Units", "80", "70", "2025-01-06 08:00", ""],
                    # two assignments summed: (40 + 20) ÷ (60 + 100) = 37.5%
                    ["2", "1", "Multi", "TT_Task", "CP_Units", "80", "70", "2025-01-06 08:00", ""],
                    # no quantities anywhere -> duration share fallback: (80-60)/80 = 25%
                    ["3", "1", "NoQty", "TT_Task", "CP_Units", "80", "60", "2025-01-06 08:00", ""],
                    # an actual finish is a fact and rules over any quantity arithmetic
                    [
                        "4",
                        "1",
                        "Done",
                        "TT_Task",
                        "CP_Units",
                        "80",
                        "0",
                        "2025-01-06 08:00",
                        "2025-01-17 17:00",
                    ],
                ],
            ),
            (
                "TASKRSRC",
                ["taskrsrc_id", "task_id", "rsrc_id", "act_reg_qty", "act_ot_qty", "remain_qty"],
                [
                    ["1", "1", "100", "30", "10", "60"],
                    ["2", "2", "100", "30", "10", "60"],
                    ["3", "2", "101", "20", "", "40"],
                    ["4", "4", "100", "10", "0", "0"],
                ],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.tasks_by_id[1].percent_complete == 40.0
    assert sched.tasks_by_id[2].percent_complete == 37.5
    assert sched.tasks_by_id[3].percent_complete == 25.0
    assert sched.tasks_by_id[4].percent_complete == 100.0


def test_units_percent_zero_at_completion_falls_back_to_duration_share() -> None:
    # all-zero quantities give no units basis (0 ÷ 0) — never a fabricated 0%/100%;
    # the duration share (80-20)/80 = 75% is the honest stand-in
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_name",
                    "task_type",
                    "complete_pct_type",
                    "target_drtn_hr_cnt",
                    "remain_drtn_hr_cnt",
                    "act_start_date",
                ],
                [["1", "1", "A", "TT_Task", "CP_Units", "80", "20", "2025-01-06 08:00"]],
            ),
            (
                "TASKRSRC",
                ["taskrsrc_id", "task_id", "rsrc_id", "act_reg_qty", "act_ot_qty", "remain_qty"],
                [["1", "1", "100", "0", "0", "0"]],
            ),
        ]
    )
    assert parse_xer_text(text).tasks_by_id[1].percent_complete == 75.0


def test_duplicate_taskpred_rows_are_deduplicated() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"], ["2", "1", "B", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["2", "1", "PR_FS", "0"], ["2", "1", "PR_FS", "0"]],  # duplicate row
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert len(sched.relationships) == 1  # would double-count DCMA logic/lag edges


def test_utf16_xer_decodes_via_bom(tmp_path: Path) -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "Tâche", "TT_Task", "8"]],
            ),
        ]
    )
    path = tmp_path / "exported.xer"
    path.write_bytes(text.encode("utf-16"))  # BOM-tagged, as P6 writes on some locales
    sched = parse_xer(path)
    assert sched.tasks_by_id[1].name == "Tâche"


def test_nan_and_infinity_numerics_are_noise_not_crashes() -> None:
    # Decimal("NaN")/Decimal("Infinity") construct fine and once escaped as raw
    # InvalidOperation (a 500 through the upload path) or poisoned downstream sums
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"], ["2", "1", "B", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["2", "1", "PR_FS", "Infinity"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert sched.relationships[0].lag_minutes == 0  # non-finite lag is data noise


# --- project calendar (ADR-0028) ----------------------------------------------------


def _clndr_data(days: dict[int, list[tuple[str, str]]], exceptions: list[tuple[int, str]]) -> str:
    """Build a P6 ``clndr_data`` blob: days = {1..7: [(from, to), ...]},
    exceptions = [(excel_serial, "" | "HH:MM-HH:MM"), ...] ("" = full day off)."""
    day_nodes = []
    for day in range(1, 8):
        spans = days.get(day, [])
        inner = "".join(f"(0||{i}(s|{s}|f|{f})())" for i, (s, f) in enumerate(spans))
        day_nodes.append(f"(0||{day}()({inner}))" if inner else f"(0||{day}())")
    exc_nodes = []
    for i, (serial, hours) in enumerate(exceptions):
        if hours:
            start, finish = hours.split("-")
            exc_nodes.append(f"(0||{i}(d|{serial})((0||0(s|{start}|f|{finish})())))")
        else:
            exc_nodes.append(f"(0||{i}(d|{serial})())")
    return (
        "(0||CalendarData()("
        f"(0||DaysOfWeek()({''.join(day_nodes)}))"
        f"(0||Exceptions()({''.join(exc_nodes)}))"
        "))"
    )


_FOUR_TENS = {d: [("07:00", "12:00"), ("13:00", "18:00")] for d in (2, 3, 4, 5)}  # Mon-Thu


def test_project_calendar_from_clndr_data() -> None:
    holiday = (dt.date(2025, 7, 14) - dt.date(1899, 12, 30)).days  # a Monday
    changed_hours = holiday + 1  # a working exception: changed hours, NOT a day off
    data = _clndr_data(_FOUR_TENS, [(holiday, ""), (changed_hours, "08:00-12:00")])
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Y", "4x10", "10", data]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "10"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.name == "4x10"
    assert cal.working_minutes_per_day == 600
    assert cal.work_weekdays == (0, 1, 2, 3)  # Mon-Thu
    assert cal.holidays == (dt.date(2025, 7, 14),)  # the changed-hours day is NOT one
    # the changed-hours exception fell on a WORKING weekday (Tue) — not a worked-weekend
    assert cal.working_days == ()


def test_project_calendar_reads_a_worked_weekend_exception() -> None:
    # PR-R3: a P6 working-time exception on a normally-NON-working weekday is an extra working
    # day (a worked Saturday, MSPDI DayWorking=1 analogue) — it must reach Calendar.working_days,
    # not be silently dropped like a changed-hours exception on a working day.
    worked_sat = dt.date(2025, 7, 19)  # a Saturday
    off_monday = dt.date(2025, 7, 14)  # a full day off, for contrast

    def serial(d: dt.date) -> int:
        return (d - dt.date(1899, 12, 30)).days

    data = _clndr_data(_FOUR_TENS, [(serial(off_monday), ""), (serial(worked_sat), "08:00-16:00")])
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Y", "4x10+Sat", "10", data]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "10"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.work_weekdays == (0, 1, 2, 3)  # Sat is NOT a standing work weekday
    assert cal.holidays == (off_monday,)
    assert cal.working_days == (worked_sat,)  # the worked Saturday is the extra working day
    assert cal.is_worked(worked_sat) and not cal.is_working_day(worked_sat)


def test_project_calendar_reads_a_24_hour_day_from_clndr_data() -> None:
    """audit L8 (same root as H3): P6 encodes a 24-hour continuous day as a single s|00:00|f|00:00
    span. It must read as 1440 working minutes/day from clndr_data — not collapse to nothing and
    fall back to the 8h day_hr_cnt. day_hr_cnt is deliberately 8 here to prove clndr_data wins."""
    twenty_four = {d: [("00:00", "00:00")] for d in range(1, 8)}  # all 7 days, 24h each
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Y", "24 Hour", "8", _clndr_data(twenty_four, [])]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "24"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.name == "24 Hour"
    assert cal.working_minutes_per_day == 1440  # the full day, not the 8h day_hr_cnt fallback
    assert cal.work_weekdays == (0, 1, 2, 3, 4, 5, 6)


def test_project_clndr_id_selects_among_calendars_with_default_flag_fallback() -> None:
    five_eights = {d: [("08:00", "12:00"), ("13:00", "17:00")] for d in (2, 3, 4, 5, 6)}
    rows = [
        ["100", "Y", "Corporate", "8", _clndr_data(five_eights, [])],
        ["200", "N", "Field", "10", _clndr_data(_FOUR_TENS, [])],
    ]
    base = [
        (
            "CALENDAR",
            ["clndr_id", "default_flag", "clndr_name", "day_hr_cnt", "clndr_data"],
            rows,
        ),
        (
            "TASK",
            ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
            [["1", "1", "A", "TT_Task", "10"]],
        ),
    ]
    # the project's clndr_id wins
    linked = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "200"]],
            ),
            *base,
        ]
    )
    assert parse_xer_text(linked).calendar.name == "Field"
    assert parse_xer_text(linked).calendar.working_minutes_per_day == 600
    # a dangling clndr_id falls back to the default_flag=Y row
    dangling = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "999"]],
            ),
            *base,
        ]
    )
    assert parse_xer_text(dangling).calendar.name == "Corporate"
    assert parse_xer_text(dangling).calendar.working_minutes_per_day == 480


def test_calendar_base_chain_provides_the_day_grid() -> None:
    # the project calendar has no parseable grid of its own; its base supplies it
    five_eights = {d: [("08:00", "12:00"), ("13:00", "17:00")] for d in (2, 3, 4, 5, 6)}
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "300"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "base_clndr_id", "clndr_name", "clndr_data"],
                [
                    ["300", "100", "Project Default", ""],
                    ["100", "", "Corporate", _clndr_data(five_eights, [])],
                ],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    cal = parse_xer_text(text).calendar
    assert cal.name == "Project Default"  # named by the project's row
    assert cal.working_minutes_per_day == 480  # grid from the base
    assert cal.work_weekdays == (0, 1, 2, 3, 4)


def test_unparseable_clndr_data_falls_back_to_day_hr_cnt_then_default() -> None:
    project = (
        "PROJECT",
        ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
        [["1", "P1", "2025-01-06 08:00", "100"]],
    )
    task = (
        "TASK",
        ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
        [["1", "1", "A", "TT_Task", "10"]],
    )
    with_hours = _xer(
        [
            project,
            (
                "CALENDAR",
                ["clndr_id", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Tens", "10", "garbage that is not calendar data"]],
            ),
            task,
        ]
    )
    cal = parse_xer_text(with_hours).calendar
    assert cal.working_minutes_per_day == 600  # day_hr_cnt
    assert cal.work_weekdays == (0, 1, 2, 3, 4)  # default week
    without_hours = _xer(
        [
            project,
            ("CALENDAR", ["clndr_id", "clndr_name", "clndr_data"], [["100", "Odd", "junk"]]),
            task,
        ]
    )
    assert parse_xer_text(without_hours).calendar.working_minutes_per_day == 480


def test_no_calendar_table_keeps_the_default(schedule: Schedule) -> None:
    # the curated fixture has no CALENDAR table — behaviorally identical to before
    assert schedule.calendar.working_minutes_per_day == 480
    assert schedule.calendar.work_weekdays == (0, 1, 2, 3, 4)
    assert schedule.calendar.holidays == ()


def test_unreadable_calendar_row_degrades_to_the_default_not_an_error() -> None:
    # a non-numeric day_hr_cnt (with no parseable day grid) trips the fail-soft
    # guard: the calendar defaults, the schedule still loads
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "clndr_id"],
                [["1", "P1", "2025-01-06 08:00", "100"]],
            ),
            (
                "CALENDAR",
                ["clndr_id", "clndr_name", "day_hr_cnt", "clndr_data"],
                [["100", "Odd", "ten hours", "junk"]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
        ]
    )
    sch = parse_xer_text(text)
    assert sch.calendar.working_minutes_per_day == 480
    assert sch.tasks_by_id[1].name == "A"


# --- cost roll-up (ADR-0029) ---------------------------------------------------------


def test_costs_roll_up_from_assignments_and_expenses() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [
                    ["1", "1", "A", "TT_Task", "8"],
                    ["2", "1", "B", "TT_Task", "8"],
                    ["3", "1", "C", "TT_Task", "8"],
                ],
            ),
            (
                "TASKRSRC",
                [
                    "taskrsrc_id",
                    "task_id",
                    "rsrc_id",
                    "act_reg_cost",
                    "act_ot_cost",
                    "remain_cost",
                    "target_cost",
                ],
                [
                    # two assignments on task 1 sum component-wise
                    ["1", "1", "100", "100", "20", "80", "150"],
                    ["2", "1", "101", "50", "", "50", "100"],
                    # task 2 is budget-loaded only: actuals/remaining were never recorded
                    ["3", "2", "100", "", "", "", "300"],
                ],
            ),
            (
                "PROJCOST",
                ["cost_item_id", "task_id", "act_cost", "remain_cost", "target_cost"],
                [["10", "1", "30", "10", "40"]],  # an expense on task 1 joins the sums
            ),
        ]
    )
    sched = parse_xer_text(text)
    one = sched.tasks_by_id[1]
    assert one.actual_cost == 200.0  # 100+20 + 50 + 30 (assignments + expense)
    assert one.cost == 340.0  # actual 200 + remaining 80+50+10
    assert one.budgeted_cost == 290.0  # targets 150+100+40
    two = sched.tasks_by_id[2]
    assert two.budgeted_cost == 300.0
    assert two.actual_cost is None  # never recorded — absence is honest, not 0
    assert two.cost is None
    three = sched.tasks_by_id[3]  # no cost rows at all
    assert (three.cost, three.actual_cost, three.budgeted_cost) == (None, None, 0.0)


def test_negative_budget_clamps_but_actual_credits_survive() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["1", "1", "A", "TT_Task", "8"]],
            ),
            (
                "TASKRSRC",
                ["taskrsrc_id", "task_id", "rsrc_id", "act_reg_cost", "remain_cost", "target_cost"],
                [["1", "1", "100", "-25", "0", "-50"]],
            ),
        ]
    )
    t = parse_xer_text(text).tasks_by_id[1]
    assert t.actual_cost == -25.0  # a credit is real data — preserved
    assert t.budgeted_cost == 0.0  # the BAC/EV basis cannot be negative — clamped
    assert t.cost == -25.0


def test_cost_loaded_xer_drives_the_evm_indices() -> None:
    # a finished, baselined, cost-loaded activity: CPI = EV/ACWP = 100/80 = 1.25 and
    # SPI = 1.0 — previously every XER reported the cost indices as NA
    from schedule_forensics.engine.metrics import compute_evm_indices

    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "last_recalc_date"],
                [["1", "P1", "2025-01-06 08:00", "2025-02-01 17:00"]],
            ),
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_name",
                    "task_type",
                    "target_drtn_hr_cnt",
                    "target_start_date",
                    "target_end_date",
                    "act_start_date",
                    "act_end_date",
                ],
                [
                    [
                        "1",
                        "1",
                        "Done",
                        "TT_Task",
                        "8",
                        "2025-01-06 08:00",
                        "2025-01-06 17:00",
                        "2025-01-06 08:00",
                        "2025-01-06 17:00",
                    ]
                ],
            ),
            (
                "TASKRSRC",
                ["taskrsrc_id", "task_id", "rsrc_id", "act_reg_cost", "remain_cost", "target_cost"],
                [["1", "1", "100", "80", "0", "100"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    indices = compute_evm_indices(sched)
    assert indices["cpi"].value == 1.25
    assert indices["spi"].value == 1.0


def test_fixture_without_cost_columns_stays_cost_free(schedule: Schedule) -> None:
    # the curated fixture's TASKRSRC has no cost columns — fields keep their defaults
    t = schedule.task_by_id(UID_DESIGN)
    assert (t.cost, t.actual_cost, t.budgeted_cost) == (None, None, 0.0)


def test_non_integer_task_id_in_non_selected_project_is_tolerated() -> None:
    """Audit H3: a malformed task_id in a NON-selected project must not sink the file. The
    cross-project id universe is built tolerantly; only in-scope rows are validated loudly."""
    text = _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date"],
                [["1", "P1", "2025-01-06 08:00"], ["2", "P2", "2025-02-01 08:00"]],
            ),
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [
                    ["10", "2", "A", "TT_Task", "8"],
                    ["11", "2", "B", "TT_Task", "8"],
                    ["GARBAGE", "1", "C", "TT_Task", "8"],  # non-selected project's bad id
                ],
            ),
        ]
    )
    sched = parse_xer_text(text)  # must not raise
    assert set(sched.tasks_by_id) == {10, 11}


def test_non_integer_taskpred_endpoint_drops_the_link_not_the_file() -> None:
    """Audit H4: a non-integer endpoint in a TASKPRED row drops that (unresolvable) link and
    is counted, instead of sinking the whole file."""
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_name", "task_type", "target_drtn_hr_cnt"],
                [["10", "1", "A", "TT_Task", "8"], ["11", "1", "B", "TT_Task", "8"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["11", "10", "PR_FS", "0"], ["11", "BADPRED", "PR_FS", "0"]],
            ),
        ]
    )
    sched = parse_xer_text(text)  # must not raise
    assert len(sched.relationships) == 1  # the 11->10 link kept; the BADPRED link dropped
    assert _rel(sched, 10, 11) is RelationshipType.FS


# --- stable Activity-ID identity (ADR-0185) -----------------------------------------


def _versioned_xer(recalc_date: str, task_rows: list[list[str]]) -> str:
    """A minimal single-project XER snapshot with a data date and code-bearing tasks."""
    return _xer(
        [
            (
                "PROJECT",
                ["proj_id", "proj_short_name", "plan_start_date", "last_recalc_date"],
                [["1", "P1", "2025-01-06 08:00", recalc_date]],
            ),
            (
                "TASK",
                [
                    "task_id",
                    "proj_id",
                    "task_code",
                    "task_name",
                    "task_type",
                    "target_drtn_hr_cnt",
                    "early_end_date",
                    "act_start_date",
                    "act_end_date",
                ],
                task_rows,
            ),
        ]
    )


def test_stable_identity_survives_task_id_renumbering() -> None:
    # P6 renumbers task_id whenever a project is re-imported/copied between monthly
    # submittals; the Activity ID (task_code) is the identity that survives, so the
    # same activity must get the same UniqueID in both versions (ADR-0185)
    v1 = _versioned_xer(
        "2025-01-31 17:00",
        [["10", "1", "A1000", "Pour", "TT_Task", "40", "2025-02-14 17:00", "", ""]],
    )
    v2 = _versioned_xer(
        "2025-02-28 17:00",
        [["77", "1", "A1000", "Pour", "TT_Task", "40", "2025-02-14 17:00", "", ""]],
    )
    s1, s2 = parse_xer_text(v1), parse_xer_text(v2)
    assert set(s1.tasks_by_id) == set(s2.tasks_by_id) == {_uid("A1000")}
    assert s1.task_by_id(_uid("A1000")).custom_field("Activity ID") == "A1000"


def test_cei_computes_across_renumbered_xer_versions() -> None:
    # THE user-visible defect this fixes: a multi-file XER series showed CEI flat 0.00
    # across every period because each monthly submittal renumbered task_id, so CEI's
    # prior->current UniqueID join missed every task (numerator 0 forever). With the
    # Activity-ID identity the join lands and CEI reads the real execution rate.
    from schedule_forensics.engine.metrics.cei import compute_cei

    prior = parse_xer_text(
        _versioned_xer(
            "2025-01-31 17:00",
            [
                # both forecast to finish inside (Jan 31, Feb 28], neither complete yet
                ["10", "1", "A1000", "Pour", "TT_Task", "40", "2025-02-14 17:00", "", ""],
                ["11", "1", "A1010", "Frame", "TT_Task", "40", "2025-02-21 17:00", "", ""],
            ],
        )
    )
    current = parse_xer_text(
        _versioned_xer(
            "2025-02-28 17:00",
            [
                # task_ids renumbered by the re-import; A1000 actually finished in-period
                [
                    "70",
                    "1",
                    "A1000",
                    "Pour",
                    "TT_Task",
                    "40",
                    "2025-02-14 17:00",
                    "2025-02-03 08:00",
                    "2025-02-14 16:00",
                ],
                ["71", "1", "A1010", "Frame", "TT_Task", "40", "2025-03-14 17:00", "", ""],
            ],
        )
    )
    result = compute_cei(prior, current)["cei_tasks"]
    assert result.population == 2  # both were forecast to finish in the period
    assert result.count == 1  # A1000 landed; A1010 slipped
    assert result.value == 0.5  # a real rate, not the phantom 0.00
    assert result.offender_uids == (_uid("A1010"),)  # the miss is citable


def test_missing_task_code_falls_back_to_raw_task_ids() -> None:
    # one task without an Activity ID disables the remap for the WHOLE file (never
    # mixed keying) — tasks keep raw task_id keys exactly as before ADR-0185
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_code", "task_name", "task_type"],
                [["10", "1", "A1000", "A", "TT_Task"], ["11", "1", "", "B", "TT_Task"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert set(sched.tasks_by_id) == {10, 11}
    # the code-bearing task still carries its Activity ID for citations/grouping
    assert sched.task_by_id(10).custom_field("Activity ID") == "A1000"


def test_duplicate_task_code_falls_back_to_raw_task_ids() -> None:
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_code", "task_name", "task_type"],
                [["10", "1", "A1000", "A", "TT_Task"], ["11", "1", "A1000", "B", "TT_Task"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert set(sched.tasks_by_id) == {10, 11}


def test_relationships_translate_through_the_stable_identity() -> None:
    # TASKPRED references raw task_ids; the kept edge must come out keyed by the same
    # stable UniqueIDs the tasks carry, or the logic graph would dangle after the remap
    text = _xer(
        [
            _MIN_PROJECT,
            (
                "TASK",
                ["task_id", "proj_id", "task_code", "task_name", "task_type"],
                [["10", "1", "A1000", "A", "TT_Task"], ["11", "1", "A1010", "B", "TT_Task"]],
            ),
            (
                "TASKPRED",
                ["task_id", "pred_task_id", "pred_type", "lag_hr_cnt"],
                [["11", "10", "PR_FS", "0"]],
            ),
        ]
    )
    sched = parse_xer_text(text)
    assert len(sched.relationships) == 1
    assert _rel(sched, _uid("A1000"), _uid("A1010")) is RelationshipType.FS
