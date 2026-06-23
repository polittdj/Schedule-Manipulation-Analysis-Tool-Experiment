"""Parity acceptance gate (§6.B) — the consolidated golden test for the whole engine.

This is the **acceptance gate** the build contract makes non-negotiable: the tool's
numbers must match **Acumen Fuse v8.11.0** and the **SSI** MS Project add-on for the
committed, non-CUI golden fixtures (`tests/fixtures/golden/`), matched by **UniqueID
only**. Every other test file covers units/edge cases; this one re-asserts the full
golden set in one place so CI can run it as a single named gate (`pytest -m parity`)
and so the §6.B evidence is auditable from one module.

Two classes of assertion:

* **Exact** — the engine value equals the Acumen/SSI golden (the large majority).
* **Documented residual** — the engine value is asserted at its current, intended value
  *and* the (small, citable) delta to the golden is asserted to be exactly what
  `case.json._deltas` + ADR-0012/0013 record. These are the figures that depend on MS
  Project's *progress-aware* total slack / Critical flag, which this engine deliberately
  does not consume (it recomputes pure-logic CPM float for independence/auditability,
  ADR-0010). A probe at M9 confirmed neither pure-logic CPM **nor** the stored MS Project
  values reproduce them exactly (e.g. stored `TotalSlack>44d` gives High Float 44/40, not
  44/41), so they are formally accepted as documented deltas rather than fabricated.
  The gate fails if a residual silently changes — so when M-future closes one, the gate
  forces the golden assertion to be tightened.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schedule_forensics.engine.driving_slack import PathTier, compute_driving_slack, driving_path
from schedule_forensics.engine.metrics import (
    CheckStatus,
    compute_baseline_compliance,
    compute_change_metrics,
    compute_dcma14,
    compute_evm_indices,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
DAY = 480


def _schedule(project: str) -> Schedule:
    return parse_mspdi(GOLDEN / "project2_5" / f"{project}.mspdi.xml")


def _case() -> dict:
    return json.loads((GOLDEN / "project2_5" / "case.json").read_text())


# --------------------------------------------------------------------------------------
# Acumen Fuse §A — Schedule-Quality summary (exact)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_acumen_schedule_quality_exact(project: str) -> None:
    g = _case()[project]["schedule_quality"]
    sq = compute_schedule_quality(_schedule(project))
    assert sq["missing_logic"].count == g["missing_logic"]
    assert sq["logic_density"].value == g["logic_density"]
    assert sq["critical"].count == g["critical"]  # 41 / 37
    assert sq["hard_constraints"].count == g["hard_constraints"]
    assert sq["negative_float"].count == g["negative_float"]
    assert sq["insufficient_detail"].count == g["insufficient_detail"]
    assert sq["number_of_lags"].count == g["number_of_lags"]
    assert sq["number_of_leads"].count == g["number_of_leads"]
    assert sq["merge_hotspot"].count == g["merge_hotspot"]


# --------------------------------------------------------------------------------------
# Acumen Fuse §B — DCMA-14 ribbon (13/14 exact; High Float = documented +1 residual)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_acumen_dcma14(project: str) -> None:
    g = _case()[project]["dcma14"]
    d = compute_dcma14(_schedule(project))
    for key in (
        "DCMA01",
        "DCMA02",
        "DCMA03",
        "DCMA04_SSFF",
        "DCMA04_SF",
        "DCMA05",
        "DCMA07",
        "DCMA08",
        "DCMA09",
        "DCMA10",
        "DCMA11",
    ):
        assert d[key].count == g[key], f"{project} {key}: {d[key].count} != {g[key]}"
    assert round(d["DCMA04_FS"].value) == g["DCMA04_FS_pct"]
    assert d["DCMA12"].status is CheckStatus.PASS
    assert d["DCMA13"].value == g["DCMA13"]  # CPLI 1.0
    assert d["DCMA14"].value == g["DCMA14"]  # BEI 0.74 / 0.59
    # DCMA-06 High Float scores on stored Total Slack (ADR-0109) and is now EXACT vs Acumen for
    # BOTH projects (P2 44 / P5 44): Project5's golden is the authoritative file (ADR-0112), which
    # closed the former stale-capture +1 residual. The chain test (ADR-0111) anchors P5 44.
    assert d["DCMA06"].count == g["DCMA06"]
    assert d["DCMA06"].status is CheckStatus.FAIL


# --------------------------------------------------------------------------------------
# Acumen Fuse §C — baseline compliance (counts + BFC exact; BSC = documented residual)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_acumen_baseline_compliance(project: str) -> None:
    g = _case()[project]["baseline_compliance"]
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
        assert c[key].count == g[key], f"{project} {key}: {c[key].count} != {g[key]}"
    assert round(c["baseline_finish_compliance"].value) == g["baseline_finish_compliance_pct"]
    # Baseline Start Compliance is now EXACT (41 / 25) — the Half-Step-Delay definition (actual
    # start <= baseline FINISH) resolves the former ADR-0013 residual (ADR-0083). Gate tightened.
    assert round(c["baseline_start_compliance"].value) == g["baseline_start_compliance_pct"]


# --------------------------------------------------------------------------------------
# EVM indices — cost-based are NA (golden schedules are not cost-loaded; never fabricated)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("project", ["Project2", "Project5"])
def test_evm_cost_indices_not_applicable(project: str) -> None:
    e = compute_evm_indices(_schedule(project))
    assert e["spi"].status is CheckStatus.NOT_APPLICABLE
    assert e["cpi"].status is CheckStatus.NOT_APPLICABLE
    assert e["tcpi"].status is CheckStatus.NOT_APPLICABLE


# --------------------------------------------------------------------------------------
# Acumen Fuse §E — Schedule-Network change + Net Finish Impact (Project5 vs Project2)
# --------------------------------------------------------------------------------------
def test_acumen_change_metrics_and_net_finish_impact() -> None:
    g = _case()["change_P2_to_P5"]
    p2, p5 = _schedule("Project2"), _schedule("Project5")
    ch = compute_change_metrics(p5, p2)
    # §E is pinned to the engine's pure-logic CPM output on the authoritative Project5 (ADR-0112).
    # The date-deterministic subset (activities_added, finish/start slips, completed, in_progress,
    # net_finish_impact) is Acumen-equivalent date arithmetic; the float/critical-dependent subset
    # (new_critical, no_longer_critical, float_erosion) is pure-logic CPM by design (ADR-0010) and
    # awaits a fresh Acumen §E PP&Change cross-check (see case.json _deltas).
    for key in (
        "activities_added",  # 0
        "new_critical",  # 1
        "no_longer_critical",  # 34
        "finish_date_slips",  # 9
        "start_date_slips",  # 9
        "remaining_duration_increases",  # 9
        "float_erosion",  # 1
        "completed",  # 27
        "in_progress",  # 2
    ):
        assert ch[key].count == g[key], f"{key}: {ch[key].count} != {g[key]}"
    assert compute_net_finish_impact(p5, p2).value == g["net_finish_impact_days"]  # -148

    # first snapshot has no prior: state counts computed, change counts 0, impact 0/NA
    first = g["_first_snapshot_P2"]
    ch2 = compute_change_metrics(p2, None)
    assert ch2["completed"].count == first["completed"]  # 20
    assert ch2["in_progress"].count == first["in_progress"]  # 3
    assert ch2["finish_date_slips"].count == 0
    assert compute_net_finish_impact(p2, None).value == first["net_finish_impact_days"]  # 0


# --------------------------------------------------------------------------------------
# SSI MS Project add-on — driving slack (107 UniqueIDs, exact, by UID)
# --------------------------------------------------------------------------------------
@pytest.mark.xfail(
    reason=(
        "ssi_uid143 golden was validated against the SSI add-on run on the PRIOR Project5 "
        "(37 stored-critical); it is stale against the authoritative file (4 critical, ADR-0112). "
        "Awaiting an SSI driving-slack export for the current Project5_TAMPERED.mpp to re-pin."
    ),
    strict=False,
)
def test_ssi_driving_slack_exact() -> None:
    case = json.loads((GOLDEN / "ssi_uid143" / "case.json").read_text())
    schedule = _schedule("Project5")
    results = compute_driving_slack(schedule, target_uid=case["focus_task_uid"])
    expected = {int(uid): days for uid, days in case["driving_slack_days_by_uid"].items()}
    assert set(results) == set(expected)  # exact set, no extras
    assert {uid: int(r.driving_slack_days) for uid, r in results.items()} == expected
    assert all(r.driving_slack_minutes % DAY == 0 for r in results.values())  # whole days
    focus = results[case["focus_task_uid"]]
    assert focus.driving_slack_minutes == 0 and focus.on_driving_path
    assert len(driving_path(schedule, results)) == 36  # the driving chain to UID 143
    assert sum(1 for r in results.values() if r.tier is PathTier.DRIVING) == 36


def test_ssi_driving_slack_uid145_exact() -> None:
    """SSI driving slack on the authoritative Project5, focus UID 145 (ADR-0115).

    Re-pins SSI parity after ADR-0112 made ``ssi_uid143`` stale: the SSI Directional Path Tool
    'Get all dependencies' export for focus UID 145 (108 UniqueIDs) is reproduced exactly.
    """
    case = json.loads((GOLDEN / "ssi_uid145" / "case.json").read_text())
    schedule = _schedule("Project5")
    results = compute_driving_slack(schedule, target_uid=case["focus_task_uid"])
    expected = {int(uid): days for uid, days in case["driving_slack_days_by_uid"].items()}
    assert set(results) == set(expected)  # exact set, no extras
    assert {uid: int(r.driving_slack_days) for uid, r in results.items()} == expected
    assert all(r.driving_slack_minutes % DAY == 0 for r in results.values())  # whole days
    focus = results[case["focus_task_uid"]]
    assert focus.driving_slack_minutes == 0 and focus.on_driving_path
    assert driving_path(schedule, results) == tuple(case["driving_path_uids"])  # 144 -> 145
    bands = case["tier_counts_default_bands"]
    tiers = {t: sum(1 for r in results.values() if r.tier is t) for t in PathTier}
    assert tiers[PathTier.DRIVING] == bands["DRIVING"]  # 2 (144, 145)
    assert tiers[PathTier.SECONDARY] == bands["SECONDARY"]  # 3 (the 1-day near path)
    assert tiers[PathTier.TERTIARY] == bands["TERTIARY"]  # 8 (the 20-day near path)
    assert tiers[PathTier.BEYOND] == bands["BEYOND"]  # 95
