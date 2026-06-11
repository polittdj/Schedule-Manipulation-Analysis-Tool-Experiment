"""XER importer tests — field coverage on a synthetic fixture + loud failures."""

from __future__ import annotations

import datetime as dt
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
    assert set(schedule.tasks_by_id) == {2000, 2001, 2002, 2003, 2004}


# --- the fully-populated task -----------------------------------------------------


def test_fully_populated_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(2001)
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
    t = schedule.task_by_id(2002)
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
    t = schedule.task_by_id(2003)
    assert t.wbs == "CC.CONSTR"
    assert t.constraint_type is ConstraintType.FNLT  # CS_MEOB
    assert t.duration_minutes == 9600  # 160h
    assert t.resource_ids == (100, 101, 102)
    assert t.resource_names == ("Architect", "Concrete", "Crane")
    assert t.baseline_start == dt.datetime(2025, 1, 27, 8, 0)
    assert t.baseline_finish == dt.datetime(2025, 3, 15, 17, 0)


def test_classification_flags(schedule: Schedule) -> None:
    assert schedule.task_by_id(2004).is_milestone is True  # TT_FinMile
    assert schedule.task_by_id(2004).constraint_type is ConstraintType.ASAP  # no cstr_type
    assert schedule.task_by_id(2004).start == dt.datetime(2025, 3, 15, 17, 0)
    summary = schedule.task_by_id(2000)
    assert summary.is_summary is True  # TT_WBS
    assert summary.wbs == "CC"  # root WBS node


# --- relationships ---------------------------------------------------------------


def test_relationship_types_and_topology(schedule: Schedule) -> None:
    assert len(schedule.relationships) == 5
    assert _rel(schedule, 2001, 2002) is RelationshipType.FS
    assert _rel(schedule, 2002, 2003) is RelationshipType.SS
    assert _rel(schedule, 2001, 2003) is RelationshipType.FF
    assert _rel(schedule, 2003, 2004) is RelationshipType.FS
    assert _rel(schedule, 2002, 2004) is RelationshipType.SF


def test_lag_and_lead(schedule: Schedule) -> None:
    fs = next(
        r for r in schedule.relationships if (r.predecessor_id, r.successor_id) == (2001, 2002)
    )
    assert fs.lag_minutes == 480  # 8h lag
    lead = next(
        r for r in schedule.relationships if (r.predecessor_id, r.successor_id) == (2003, 2004)
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


def test_taskpred_missing_task_id_raises() -> None:
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
    with pytest.raises(ImporterError, match="missing required integer column 'task_id'"):
        parse_xer_text(text)


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
