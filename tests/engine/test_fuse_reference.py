"""Fuse-reference validation — the tool's per-project facts vs Acumen Fuse on the same files.

The operator ran Acumen Fuse on a workbook of all the test projects and provided the exports
(see docs/FUSE-VALIDATION.md). These tests pin the agreement on the fixtures that live in the
repo: the tool's NORMAL (non-milestone) completed-activity count matches Fuse exactly, and the
TP4 v1-v4 computed finish dates match Fuse. The known differences (TP2 calendar caveat, TP4 v5
fixture/manifest, the workbook's Project2 differing from the committed golden) are documented in
docs/FUSE-VALIDATION.md and deliberately not asserted here.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.importers.mspdi import parse_mspdi

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TP = FIXTURES / "test_projects"
GOLD = FIXTURES / "golden" / "project2_5"

#: Fuse reference: project -> (fixture path, fuse normal-complete, fuse finish or None if the
#: file/finish is a documented difference we do not pin here).
_REFERENCE: dict[str, tuple[Path, int, str | None]] = {
    "Project2": (
        GOLD / "Project2.mspdi.xml",
        20,
        None,
    ),  # workbook's Project2 differs (08-30 vs 09-14)
    "TP1_Library_Progressed": (TP / "TP1_Library_Progressed.xml", 4, None),  # -1d convention
    "TP3_Outage_DCMA_Seeded": (TP / "TP3_Outage_DCMA_Seeded.xml", 8, None),  # -5d, to reconcile
    "TP4_DataCenter_v1": (TP / "TP4_DataCenter_v1.xml", 1, "2026-06-05"),
    "TP4_DataCenter_v2": (TP / "TP4_DataCenter_v2.xml", 3, "2026-06-05"),
    "TP4_DataCenter_v3": (TP / "TP4_DataCenter_v3.xml", 5, "2026-06-05"),
    "TP4_DataCenter_v4": (TP / "TP4_DataCenter_v4.xml", 7, "2026-06-26"),
    "TP4_DataCenter_v5": (
        TP / "TP4_DataCenter_v5.xml",
        7,
        None,
    ),  # committed MSPDI 06-26 vs Fuse .mpp 07-17
}


def test_tool_normal_completion_matches_fuse() -> None:
    """Counting normal (non-milestone) completed activities, the tool equals Fuse on every
    in-container fixture (the '+1' in the tool's headline is completed milestones it includes)."""
    for name, (path, fuse_normal_complete, _finish) in _REFERENCE.items():
        sch = parse_mspdi(path)
        normal_complete = sum(
            1 for t in non_summary(sch) if not t.is_milestone and t.percent_complete >= 100.0
        )
        assert normal_complete == fuse_normal_complete, (
            name,
            normal_complete,
            fuse_normal_complete,
        )


def test_tool_finish_matches_fuse_where_files_agree() -> None:
    """On the unambiguous TP4 v1-v4 cases the tool's computed finish equals Fuse's exactly."""
    for name, (path, _nc, finish) in _REFERENCE.items():
        if finish is None:
            continue
        sch = parse_mspdi(path)
        cpm = compute_cpm(sch)
        got = offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar).date()
        assert got == dt.date.fromisoformat(finish), (name, got.isoformat(), finish)
