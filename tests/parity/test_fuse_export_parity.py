"""ENGINE==FUSE parity against the operator-delivered Acumen Fuse v8.11.0 export suite (A-1/A-2).

Until 2026-07 the §A/§B/§C rows were validated against *transcribed* golden targets
(``ENGINE==GOLDEN``) and the §E float/critical subset was **engine-pinned** (self-consistency).
The operator then delivered the complete Fuse export suite for the exact golden pair
(``00_REFERENCE_INTAKE/``, repo-tracked, non-CUI): the Metric History / DCMA / Detailed /
Quick Add reports (created 6/21/2026) and two independently-created Forensic Analysis Report
comparisons (6/22 and 7/7/2026, programmatically verified row-identical). Every value asserted
here was transcribed into ``fuse_exports_2026-06.json`` from at least TWO independent places in
that suite — this module is the **ENGINE==FUSE** gate those exports unlock.

Highlights (PARK-LIST A-1):

* §E **Newly Critical (1, UID 131)**, **No Longer Critical (34)**, **Float Erosion (1, UID
  131)** and the slip/duration-increase sets are now validated against Fuse — *UID-exact*
  wherever the suite publishes or lets us derive a per-activity list.
* Two divergences are asserted EXACTLY rather than papered over (never force a match):
  the 96↔99 no-longer-critical membership swap (stored vs pure-logic CPM critical basis,
  ADR-0010) and the -148 vs -134 Net Finish Impact basis (CPM-recomputed vs stored project
  finishes, the ADR-0108 data-date gap) — each reconciled to the day in its test.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_change_metrics,
    compute_dcma14,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
_EXCEL_EPOCH = dt.datetime(1899, 12, 30)


def _schedule(project: str) -> Schedule:
    return parse_mspdi(GOLDEN / f"{project}.mspdi.xml")


def _fuse() -> dict:
    return json.loads((GOLDEN / "fuse_exports_2026-06.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# §A Schedule Quality — ENGINE==FUSE (Metric History + DCMA Report rows)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_schedule_quality_engine_equals_fuse(project: str) -> None:
    f = _fuse()[project]["schedule_quality"]
    sq = compute_schedule_quality(_schedule(project))
    assert sq["logic_density"].value == f["logic_density"]  # 2.79 / 2.81 (all-activity)
    assert sq["critical"].count == f["critical_zero_days_float"]  # 41 / 4
    assert sq["hard_constraints"].count == f["hard_constraints"]  # 0 / 1
    assert sq["negative_float"].count == f["negative_float"]  # 0 / 0
    assert sq["insufficient_detail"].count == f["insufficient_detail"]  # 1 / 0
    assert sq["merge_hotspot"].count == f["merge_hotspot"]  # 10 / 10
    # Fuse publishes Missing Logic INCOMPLETE-scoped — that is the engine's DCMA01, not the
    # all-activity §A missing_logic (6/7, no Fuse counterpart; documented in case.json _deltas).
    d = compute_dcma14(_schedule(project))
    assert d["DCMA01"].count == f["missing_logic_incomplete_scoped"]  # 4 / 5


# --------------------------------------------------------------------------------------
# §B DCMA-14 — ENGINE==FUSE for every row the export suite carries
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_dcma14_engine_equals_fuse(project: str) -> None:
    f = _fuse()[project]["dcma14"]
    d = compute_dcma14(_schedule(project))
    for key in ("DCMA01", "DCMA02", "DCMA03", "DCMA05", "DCMA06", "DCMA07", "DCMA08", "DCMA09"):
        assert d[key].count == f[key], f"{project} {key}: {d[key].count} != {f[key]}"
    assert d["DCMA11"].count == f["DCMA11"]  # Finished Late + due-but-not-finished: 18 / 37
    assert d["DCMA14"].value == f["DCMA14"]  # BEI - Value Tasks 0.74 / 0.59
    assert d["DCMA14"].count == f["DCMA14_complete"]  # BEI - Complete Tasks 20 / 27
    # BEI - Total Tasks (27 / 46) is the same population §C calls Forecast to be Finished
    c = compute_baseline_compliance(_schedule(project))
    assert c["forecast_to_be_finished"].count == f["DCMA14_total"]


# --------------------------------------------------------------------------------------
# §C Baseline Compliance — ENGINE==FUSE (Metric History block + Advanced sheet, verbatim)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_baseline_compliance_engine_equals_fuse(project: str) -> None:
    f = _fuse()[project]["baseline_compliance"]
    c = compute_baseline_compliance(_schedule(project))
    for key in (
        "forecast_to_be_finished",
        "completed_on_time",
        "completed_late",
        "not_completed",
        "forecast_to_be_started",
        "started_on_time",
        "started_late",
        "not_started",
    ):
        assert c[key].count == f[key], f"{project} {key}: {c[key].count} != {f[key]}"
    # Fuse publishes the compliance ratios at 2dp (0.33/0.20 and 0.41/0.25)
    assert round(c["baseline_finish_compliance"].value) == round(
        f["baseline_finish_compliance"] * 100
    )
    assert round(c["baseline_start_compliance"].value) == round(
        f["baseline_start_compliance"] * 100
    )


# --------------------------------------------------------------------------------------
# §E Schedule-Network change — the A-1 re-pin: ENGINE==FUSE, UID-exact where published
# --------------------------------------------------------------------------------------
def test_change_metrics_engine_equals_fuse_uid_exact() -> None:
    f = _fuse()["change_P2_to_P5"]
    p2, p5 = _schedule("Project2"), _schedule("Project5")
    ch = compute_change_metrics(p5, p2)

    assert ch["activities_added"].count == f["activities_added"]  # 0 — identical UID set

    # SN "Newly Critical": Fuse says 1, and names UID 131 in three independent places
    assert ch["new_critical"].count == f["newly_critical"] == 1
    assert list(ch["new_critical"].offender_uids) == f["newly_critical_uids"] == [131]

    # Float Erosion: Fuse's own per-activity stored-TF data, scoped exactly like the engine
    # (non-summary + incomplete), erodes ONLY UID 131 — the engine's pure-CPM basis agrees
    assert ch["float_erosion"].count == f["float_erosion_stored_basis"] == 1
    assert list(ch["float_erosion"].offender_uids) == f["float_erosion_stored_basis_uids"]

    # Finish Date Slips == Fuse "CEI - Incomplete Tasks" (9), UID-exact per the offender list
    assert ch["finish_date_slips"].count == f["finish_slips_cei_incomplete"] == 9
    assert list(ch["finish_date_slips"].offender_uids) == f["finish_slips_cei_incomplete_uids"]

    # Start Date Slips: count-consistent with Fuse CEI Starts 0.40 (6 of 15 due started -> 9
    # missed); the suite publishes no per-activity start list, so this row is count-level only.
    # Fuse's period starts = Actual Starts 23 -> 29 (Metric History), i.e. 6 new starts.
    def _started(s: Schedule) -> int:
        return sum(1 for t in s.tasks if not t.is_summary and t.actual_start is not None)

    started_in_period = _started(p5) - _started(p2)
    assert (_started(p2), _started(p5)) == (23, 29)  # the Metric History 'Actual Starts' row
    due = ch["start_date_slips"].count + started_in_period
    assert ch["start_date_slips"].count == 9
    assert round(started_in_period / due, 2) == f["start_cei_by_status_dates"]  # 6/15 = 0.40

    # SN07: UID-exact against the Fuse Forensic Original-Duration change sheet (D14 disposition:
    # the engine's total-duration comparison IS the Fuse-validated basis; remaining-duration
    # would give the 7-UID subset — both recorded in the reference JSON)
    assert ch["remaining_duration_increases"].count == f["original_duration_increases"] == 9
    assert (
        list(ch["remaining_duration_increases"].offender_uids)
        == f["original_duration_increases_uids"]
    )
    assert set(f["remaining_duration_increases_nonsummary_uids"]) < set(
        f["original_duration_increases_uids"]
    )

    assert ch["completed"].count == f["completed"] == 27
    assert ch["in_progress"].count == f["in_progress"] == 2


def test_no_longer_critical_count_matches_fuse_and_the_one_membership_swap_is_exact() -> None:
    """34 == 34, and the single member difference is precisely the 96↔99 basis swap.

    Fuse reads MS Project's stored progress-aware Critical flag; the engine recomputes
    pure-logic CPM float (ADR-0010). In Project2 the two bases disagree on exactly one pair:
    stored flags UID 96 critical (CPM float 5d), CPM flags UID 99 critical (stored slack 10d).
    Both count 41 critical in Project2, so the transition count matches while the membership
    differs by that one swap. Assert it exactly so any drift (a second swapped UID, or the
    counts separating) fails loudly."""
    f = _fuse()["change_P2_to_P5"]
    p2, p5 = _schedule("Project2"), _schedule("Project5")
    ch = compute_change_metrics(p5, p2)

    fuse_set = set(f["no_longer_critical_uids"])
    engine_set = set(ch["no_longer_critical"].offender_uids)
    assert ch["no_longer_critical"].count == f["no_longer_critical"] == 34
    assert len(fuse_set) == 34
    assert engine_set - fuse_set == {99}
    assert fuse_set - engine_set == {96}

    # pin the swap's root cause on the source data itself
    p2_by_id = {t.unique_id: t for t in p2.tasks}
    cpm2 = compute_cpm(p2)
    assert p2_by_id[96].stored_is_critical is True and not cpm2.timings[96].is_critical
    assert p2_by_id[99].stored_is_critical is False and cpm2.timings[99].is_critical


def test_net_finish_impact_bases_reconcile_to_the_day() -> None:
    """Engine -148 (pure-logic CPM finishes) vs Fuse HSD10 -134 (stored finishes) — exact.

    The .aft Bible formula is ``ROUND(ProjectPreviousFinish - ProjectFinish, 0)`` over the
    STORED project finishes; the engine deliberately subtracts its own CPM finishes
    (independence/auditability, ADR-0010 — the gap is the ADR-0108 data-date behaviour, not a
    computation error). Assert BOTH numbers and the day-exact reconciliation between them."""
    f = _fuse()["change_P2_to_P5"]
    p2, p5 = _schedule("Project2"), _schedule("Project5")

    # the goldens' stored finishes ARE Fuse's project finishes (data-level parity)
    stored_p2 = max(t.finish for t in p2.tasks if t.finish is not None).date()
    stored_p5 = max(t.finish for t in p5.tasks if t.finish is not None).date()
    assert stored_p2 == (_EXCEL_EPOCH + dt.timedelta(days=f["project_finish_serial_P2"])).date()
    assert stored_p5 == (_EXCEL_EPOCH + dt.timedelta(days=f["project_finish_serial_P5"])).date()
    fuse_impact = (stored_p2 - stored_p5).days
    assert fuse_impact == f["net_finish_impact_days_stored"] == -134

    # the engine's CPM-basis figure, and the exact bridge between the two bases
    engine_impact = compute_net_finish_impact(p5, p2).value
    assert engine_impact == -148.0
    cpm_p2 = offset_to_datetime(p2.project_start, compute_cpm(p2).project_finish, p2.calendar)
    cpm_p5 = offset_to_datetime(p5.project_start, compute_cpm(p5).project_finish, p5.calendar)
    gap_p2 = (stored_p2 - cpm_p2.date()).days  # CPM lands 15 days before the stored finish
    gap_p5 = (stored_p5 - cpm_p5.date()).days  # CPM lands 1 day before the stored finish
    assert (gap_p2, gap_p5) == (15, 1)
    assert engine_impact == fuse_impact - gap_p2 + gap_p5  # -148 == -134 - 15 + 1
