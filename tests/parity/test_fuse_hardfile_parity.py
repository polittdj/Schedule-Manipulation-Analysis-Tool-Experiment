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


@pytest.mark.parametrize(
    "snapshot", ["Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3"]
)
def test_fuse_hardfile_updated_series_uid_exact_and_values(snapshot: str) -> None:
    """The 2026-07-09 delivery (ADR-0176): BEI + Acumen SPI(t) values and the Invalid-Forecast-
    Dates / critical-path / negative-float UID SETS reproduce the Fuse Detailed Metric Report
    activity-for-activity (not just count-for-count) on the updated2/updated3 snapshots, and
    value-for-value across the whole updated series."""
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.engine.metrics.evm import compute_evm_indices
    from schedule_forensics.engine.path_evolution import effective_critical_set

    case = _case()
    entry = case["snapshots"][snapshot]
    sch = _schedule(snapshot)
    cpm = compute_cpm(sch)
    dcma = compute_dcma14(sch, cpm)
    evm = compute_evm_indices(sch, cpm)
    sets = entry["fuse_uid_sets"]

    # scalar values from the Fuse Metric History
    assert dcma["DCMA14"].value == entry["fuse_values"]["bei_value_tasks"]
    assert evm["spi_t_acumen"].value == round(entry["fuse_values"]["spi_t"], 2)

    # UID-exact: DCMA09's offenders == Fuse's Invalid Forecast Dates X-marked activities
    assert sorted(dcma["DCMA09"].offender_uids or ()) == sets["invalid_forecast_dates"]

    # UID-exact: the effective critical set == Fuse's Critical Path (Tasks & Milestones),
    # including the milestone / normal-task split
    crit = effective_critical_set(sch, cpm)
    assert sorted(crit) == sets["critical_path_tasks_and_milestones"]
    by = sch.tasks_by_id
    assert sorted(u for u in crit if by[u].is_milestone) == sets["critical_path_milestones"]
    assert sorted(u for u in crit if not by[u].is_milestone) == sets["critical_path_normal_tasks"]

    if "negative_float" in sets:  # updated2/updated3 — UID-exact vs Fuse
        quality = compute_schedule_quality(sch)
        assert sorted(quality["negative_float"].offender_uids or ()) == sets["negative_float"]


def test_fuse_hardfile_missing_logic_superset_divergence_is_exact() -> None:
    """Missing Logic on updated2/updated3: the engine's offender set is a strict SUPERSET of
    Fuse's (the extras are the COMPLETED open-ended activities 187/400/412, which Fuse's own
    earlier exports counted — the inconsistency is Fuse-side; operator kept engine behavior)."""
    case = _case()
    div = case["_documented_divergences"]["missing_logic_updated23"]
    for snapshot in ("Hard_File_updated2", "Hard_File_updated3"):
        quality = compute_schedule_quality(_schedule(snapshot))
        engine_uids = set(quality["missing_logic"].offender_uids or ())
        fuse_uids = set(case["snapshots"][snapshot]["fuse_uid_sets"]["missing_logic"])
        assert len(engine_uids) == div["engine"][snapshot]
        assert len(fuse_uids) == div["fuse"][snapshot]
        assert fuse_uids < engine_uids  # strict superset — same activities plus the completed
        assert engine_uids - fuse_uids == {187, 400, 412}


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


@pytest.mark.parametrize(
    "prior_name,current_name,key",
    [
        ("Hard_File_updated", "Hard_File_updated2", "Hard_File_updated->Hard_File_updated2"),
        ("Hard_File_updated2", "Hard_File_updated3", "Hard_File_updated2->Hard_File_updated3"),
    ],
)
def test_fuse_forensic_change_trackers_are_uid_exact(
    prior_name: str, current_name: str, key: str
) -> None:
    """ADR-0176: the cross-version change trackers reproduce the Fuse Forensic Analysis Report
    change sheets UID-for-UID (leaf activities; Fuse's extra summary rollup rows are derivative)
    and the assignment tracker reproduces the 'Resources' sheet ROW-for-row — (task, resource)
    pairs whose remaining work changed or whose booking appeared/disappeared."""
    from schedule_forensics.engine.diff import diff_versions
    from schedule_forensics.engine.manipulation import assignment_change_rows

    case = _case()
    oracle = case["forensic_changes"][key]
    prior, current = _schedule(prior_name), _schedule(current_name)
    diff = diff_versions(prior, current)
    prior_by = {t.unique_id: t for t in prior.tasks if not t.is_summary}
    cur_by = {t.unique_id: t for t in current.tasks if not t.is_summary}

    def changed(field: str) -> list[int]:
        return sorted(td.unique_id for td in diff.changed_tasks if td.changed(field) is not None)

    assert changed("cost") == oracle["total_cost_uids"]
    assert changed("actual_cost") == oracle["actual_cost_uids"]
    assert changed("work_minutes") == oracle["total_work_uids"]
    assert changed("actual_work_minutes") == oracle["actual_work_uids"]
    # remaining cost is DERIVED (cost - actual cost) — the derived set matches Fuse's
    # Remaining-Cost sheet exactly
    rem = sorted(
        u
        for u in set(prior_by) & set(cur_by)
        if ((prior_by[u].cost or 0) - (prior_by[u].actual_cost or 0))
        != ((cur_by[u].cost or 0) - (cur_by[u].actual_cost or 0))
    )
    assert rem == oracle["remaining_cost_uids"]

    rows = assignment_change_rows(prior, current)
    assert sorted([r.task_uid, r.resource] for r in rows) == oracle["resource_rows"]
