"""Fuse Ribbon metrics — calibrated to the operator's Acumen Fuse workbook.

See docs/FUSE-VALIDATION.md for the reference values these pin.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics.ribbon import compute_ribbon
from schedule_forensics.importers.mspdi import parse_mspdi

FIX = Path(__file__).resolve().parents[1] / "fixtures"
TP = FIX / "test_projects"
GOLD = FIX / "golden" / "project2_5"

# project -> (path, missing_logic, logic_density, critical, hard, neg_float, lags, leads, merge)
_FUSE = {
    "Project2": (GOLD / "Project2.mspdi.xml", 6, 2.79, 41, 0, 0, 2, 0, 10),
    "TP1": (TP / "TP1_Library_Progressed.xml", 4, 2.61, 11, 0, 0, 3, 0, 1),
    "TP2": (TP / "TP2_Bridge_4x10_Calendar.xml", 2, 2.63, 7, 0, 0, 0, 0, 1),
    "TP3": (TP / "TP3_Outage_DCMA_Seeded.xml", 8, 2.38, 5, 2, 3, 3, 1, 2),
    "TP4v1": (TP / "TP4_DataCenter_v1.xml", 2, 2.67, 8, 0, 0, 0, 0, 1),
    "TP4v2": (TP / "TP4_DataCenter_v2.xml", 2, 2.67, 7, 0, 0, 0, 0, 1),
    "TP4v3": (TP / "TP4_DataCenter_v3.xml", 2, 2.67, 7, 0, 0, 0, 0, 1),
    "TP4v4": (TP / "TP4_DataCenter_v4.xml", 2, 2.67, 5, 0, 0, 0, 0, 1),
    "TP4v5": (TP / "TP4_DataCenter_v5.xml", 2, 2.67, 5, 0, 0, 0, 0, 1),
}


@pytest.mark.parametrize("name", list(_FUSE))
def test_ribbon_metrics_match_fuse(name: str) -> None:
    path, ml, ld, crit, hard, nf, lags, leads, mh = _FUSE[name]
    sch = parse_mspdi(path)
    cpm = compute_cpm(sch)
    r = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    assert r.missing_logic == ml, ("missing_logic", name, r.missing_logic, ml)
    assert r.logic_density == ld, ("logic_density", name, r.logic_density, ld)
    assert r.critical == crit, ("critical", name, r.critical, crit)
    assert r.hard_constraints == hard, ("hard", name, r.hard_constraints, hard)
    assert r.negative_float == nf, ("neg_float", name, r.negative_float, nf)
    assert r.number_of_lags == lags, ("lags", name, r.number_of_lags, lags)
    assert r.number_of_leads == leads, ("leads", name, r.number_of_leads, leads)
    assert r.merge_hotspot == mh, ("merge_hotspot", name, r.merge_hotspot, mh)


def test_ribbon_float_stats_are_present() -> None:
    sch = parse_mspdi(GOLD / "Project2.mspdi.xml")
    cpm = compute_cpm(sch)
    r = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    assert r.avg_float_days >= 0.0 and r.max_float_days >= r.avg_float_days
