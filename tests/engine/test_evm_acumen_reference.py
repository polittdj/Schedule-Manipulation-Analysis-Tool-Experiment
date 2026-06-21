"""EVM1/EVM2 validation against the operator's Acumen Fuse reference export.

These two cost-loaded test schedules (operator-supplied, NOT CUI) were exported from Acumen Fuse;
this test pins the metrics the tool **confirms** against that reference, and documents the **known
residuals** that await a faithful MS Project progress-scheduler (see ``docs/STATE/HANDOFF.md``).

Reference values are read from the Acumen "Metric History Report" for EVM1 (status 2012-09-01) and
EVM2 (status 2012-09-12); the activity model reconciles as 11 tasks+milestones + 3 summaries (+ the
project root MPXJ emits), matching Acumen's 14 with the root excluded.

NOT marked ``parity`` because of the documented residuals below — it is a forward-looking validation
harness, green on the matches, that the progress-scheduler work will extend.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.metrics import (
    compute_dcma14,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.engine.metrics.constraint_health import compute_constraint_health
from schedule_forensics.engine.metrics.health_extra import compute_health_checks
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "evm"


def _load(name: str) -> Schedule:
    return parse_mspdi_text(
        (_GOLDEN / f"{name}.mspdi.xml").read_text(encoding="utf-8"), source_file=f"{name}.mpp"
    )


@pytest.fixture(scope="module")
def evm1() -> Schedule:
    return _load("EVM1")


@pytest.fixture(scope="module")
def evm2() -> Schedule:
    return _load("EVM2")


def test_cost_loaded_and_two_versions(evm1: Schedule, evm2: Schedule) -> None:
    # both carry budgeted cost on every activity (these unblock the cost EVM indices)
    for s in (evm1, evm2):
        ns = non_summary(s)
        assert len(ns) == 11  # Acumen's 14 = 11 tasks+milestones + 3 summaries
        assert all(t.budgeted_cost is not None for t in ns)
    assert evm1.status_date == dt.datetime(2012, 9, 1, 17, 0)
    assert evm2.status_date == dt.datetime(2012, 9, 12, 17, 0)


# ── confirmed matches vs Acumen (regression-locked) ──────────────────────────────────────


def test_structural_metrics_match_acumen(evm1: Schedule, evm2: Schedule) -> None:
    """DCMA / health / constraint metrics the tool confirms against the Acumen Metric History."""
    for s, crit, dcma01 in ((evm1, 10, 2), (evm2, 8, 1)):
        c = compute_cpm(s)
        d = compute_dcma14(s)
        sq = compute_schedule_quality(s, c)
        assert sq["critical"].count == crit  # Acumen Critical Path (Tasks & Milestones) 10 / 8
        assert d["DCMA01"].count == dcma01  # Acumen Missing Logic 2 / 1 (incomplete-only)
        assert d["DCMA05"].count == 0  # Hard Constraints 0
        assert d["DCMA07"].count == 0  # Negative Float 0
        assert d["DCMA06"].count == 0  # High Float 0
        assert round(d["DCMA04_FS"].value) == 100  # all FS logic


def test_new_session_checks_match_acumen(evm1: Schedule, evm2: Schedule) -> None:
    """The checks added this session, validated against Acumen's own metric set (all 0 / 0)."""
    for s in (evm1, evm2):
        c = compute_cpm(s)
        hc = {x.key: x.count for x in compute_health_checks(s, c).checks}
        ch = {x.key: x.count for x in compute_constraint_health(s, c).checks}
        assert hc["estimated_duration"] == 0  # Acumen Estimated Duration 0
        assert hc["missing_wbs"] == 0  # Acumen Missing WBS 0
        assert ch["unsatisfied_constraint"] == 0  # Acumen Unsatisfied Constraints 0
        assert ch["deadline_negative_float"] == 0  # Acumen Deadlines 0


def test_bei_matches_acumen(evm1: Schedule, evm2: Schedule) -> None:
    assert round(compute_dcma14(evm1)["DCMA14"].value, 2) == 0.0  # Acumen BEI cumulative 0
    assert round(compute_dcma14(evm2)["DCMA14"].value, 2) == 0.25  # Acumen BEI 0.25


def test_evm1_project_finish_matches_acumen(evm1: Schedule) -> None:
    c = compute_cpm(evm1)
    fin = offset_to_datetime(evm1.project_start, c.project_finish, evm1.calendar).date()
    assert fin == dt.date(2012, 9, 12)  # Acumen HSD20 Project Finish 41164 = 2012-09-12


# ── known residuals (documented; await the MS Project progress-scheduler) ─────────────────


def test_known_residuals_are_documented(evm1: Schedule, evm2: Schedule) -> None:
    """These DIVERGE from Acumen because the CPM does not yet reschedule an in-progress task's
    remaining duration from the data date (MS Project progress override). Pinned to the tool's
    CURRENT values so a future fix that closes the gap trips this test and updates it knowingly.
    Acumen targets: EVM2 finish 2012-10-04, Net Finish Impact -22, SPI(t) 0.56."""
    c2 = compute_cpm(evm2)
    fin2 = offset_to_datetime(evm2.project_start, c2.project_finish, evm2.calendar).date()
    assert fin2 == dt.date(2012, 10, 1)  # RESIDUAL: Acumen 2012-10-04 (3 working days short)
    nfi = compute_net_finish_impact(evm2, evm1)
    assert nfi.value == -19.0  # RESIDUAL: Acumen -22
