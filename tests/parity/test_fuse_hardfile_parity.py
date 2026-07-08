"""ENGINE==FUSE parity against the operator-delivered Acumen Fuse v8.11.0 export suite for
``Hard_File.mpp`` + ``Hard_File_updated.mpp`` (delivered 2026-07-08, ADR-0159).

A SECOND independent Fuse oracle (the first is ``project2_5/fuse_exports_2026-06.json``,
ADR-0151), and the only one covering an **elapsed in-progress activity** (needs-list D7): the
updated snapshot carries exactly one normal in-progress to-go task, reproduced exactly.

Every value in ``case.json``'s ``exact`` blocks is asserted UID-for-count against the engine;
the three ``_documented_divergences`` are asserted EXACTLY (their current engine values) rather
than papered over — each is root-caused in the golden and on the needs list. Fixtures are the
gzipped MPXJ-converted MSPDI of the intake ``.mpp`` files (non-CUI build inputs per CLAUDE.md).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.metrics import compute_dcma14, compute_schedule_quality
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"


def _schedule(name: str) -> Schedule:
    xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{name}.mspdi.xml")


def _case() -> dict:
    return json.loads((GOLDEN / "case.json").read_text(encoding="utf-8"))


def _engine_counts(sch: Schedule) -> dict[str, int]:
    """The subset of Fuse metrics the engine reproduces, computed from one schedule."""
    dcma = compute_dcma14(sch)
    quality = compute_schedule_quality(sch)
    non_summary = [t for t in sch.tasks if not t.is_summary]
    to_go = [t for t in non_summary if (t.percent_complete or 0) < 100]
    return {
        "missing_logic": quality["missing_logic"].count,
        "hard_constraints": quality["hard_constraints"].count,
        "high_float_44d": dcma["DCMA06"].count,
        "milestones_with_duration_gt_0": sum(
            1 for t in non_summary if t.is_milestone and (t.duration_minutes or 0) > 0
        ),
        "tasks_and_milestones_to_go": len(to_go),
        "milestones_to_go": sum(1 for t in to_go if t.is_milestone),
        "normal_tasks_to_go": sum(1 for t in to_go if not t.is_milestone),
        "normal_tasks_to_go_in_progress": sum(
            1 for t in to_go if not t.is_milestone and 0 < (t.percent_complete or 0) < 100
        ),
    }


@pytest.mark.parametrize("snapshot", ["Hard_File", "Hard_File_updated"])
def test_fuse_hardfile_engine_equals_fuse(snapshot: str) -> None:
    """Every ``exact`` metric in the golden reproduces the Fuse export value UID-for-count."""
    case = _case()
    sch = _schedule(snapshot)
    counts = _engine_counts(sch)
    expected = case["snapshots"][snapshot]["exact"]
    for metric, value in expected.items():
        assert counts[metric] == value, (
            f"{snapshot}/{metric}: engine {counts[metric]} != Fuse {value}"
        )


def test_fuse_hardfile_covers_elapsed_in_progress_activity() -> None:
    """Needs-list D7: the updated snapshot has exactly one elapsed in-progress normal task, and
    the base snapshot has none — the Fuse 'Normal Tasks (To-Go, In Progress)' 0 -> 1 transition
    both engine and Fuse agree on, giving the elapsed-axis metrics a real Fuse oracle."""
    base = _engine_counts(_schedule("Hard_File"))
    updated = _engine_counts(_schedule("Hard_File_updated"))
    assert base["normal_tasks_to_go_in_progress"] == 0
    assert updated["normal_tasks_to_go_in_progress"] == 1


def test_fuse_hardfile_divergences_are_exact_not_papered_over() -> None:
    """The three documented divergences hold at their recorded engine values (Law 2: assert the
    difference exactly, never force a match). If any of these changes, the golden note and the
    needs list must be revisited in the same commit."""
    case = _case()
    div = case["_documented_divergences"]
    quality_base = compute_schedule_quality(_schedule("Hard_File"))
    quality_upd = compute_schedule_quality(_schedule("Hard_File_updated"))

    # 1. Negative float: engine 34/33 vs Fuse 0/0 (stored-critical, no stored TotalSlack)
    assert quality_base["negative_float"].count == div["negative_float"]["engine"]["Hard_File"]
    assert (
        quality_upd["negative_float"].count == div["negative_float"]["engine"]["Hard_File_updated"]
    )
    # every negative-float offender carries the source's stored Critical flag (the root cause)
    by_uid = {t.unique_id: t for t in _schedule("Hard_File").tasks}
    assert all(
        by_uid[u].stored_is_critical and by_uid[u].stored_total_float_minutes is None
        for u in quality_base["negative_float"].offender_uids
    )

    # 2. Missing logic on the updated snapshot: engine 10 vs Fuse 8 (Fuse definition nuance)
    assert quality_upd["missing_logic"].count == div["missing_logic_updated"]["engine"]

    # 3. Activities with Duration=0: engine 0 vs Fuse 1 (all zero-duration tasks are milestones)
    for name in ("Hard_File", "Hard_File_updated"):
        sch = _schedule(name)
        zero_non_ms = sum(
            1
            for t in sch.tasks
            if not t.is_summary and not t.is_milestone and (t.duration_minutes or 0) == 0
        )
        assert zero_non_ms == div["activities_with_duration_0"]["engine"][name]
