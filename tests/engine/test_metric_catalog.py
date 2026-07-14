"""Metric Workbench catalog tests (ADR-0204).

The catalog must only *surface* already-validated numbers — never recompute. These tests pin
the library shape and prove each row equals its source (the DCMA audit / the ribbon), that
offenders reconcile, and that a metric the audit does not score is reported NA (not a
fabricated 0).
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metric_catalog import (
    catalog_entries,
    catalog_families,
    evaluate_catalog,
)
from schedule_forensics.engine.metrics.ribbon import compute_ribbon
from schedule_forensics.importers.mspdi import parse_mspdi_text

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _load(name: str) -> object:
    return parse_mspdi_text((GOLDEN / f"{name}.mspdi.xml").read_text(encoding="utf-8-sig"))


def test_catalog_shape_and_families() -> None:
    entries = catalog_entries()
    ids = [e.metric_id for e in entries]
    assert len(ids) == len(set(ids)), "metric ids must be unique"
    assert catalog_families() == ("DCMA-14", "Schedule Quality", "Float")
    # the 16 DCMA checks lead, then the ribbon extras
    assert ids[:3] == ["DCMA01", "DCMA02", "DCMA03"]
    assert {"logic_density", "insufficient_detail", "merge_hotspot"} <= set(ids)
    assert {"avg_float_days", "max_float_days"} <= set(ids)


def test_dcma_rows_equal_the_audit() -> None:
    sch = _load("Project5")
    cpm = compute_cpm(sch)
    audit = audit_schedule(sch, cpm)
    rows = evaluate_catalog(sch, cpm, audit)
    by_id = {c.metric_id: c for c in audit.checks}
    for mid, check in by_id.items():
        row = rows[mid]
        assert row.value == check.value
        assert row.status == check.status.value
        # offenders are exactly the audit citations (same UIDs, same order)
        assert row.offender_uids == tuple(c.unique_id for c in check.citations)


def test_ribbon_extras_equal_compute_ribbon() -> None:
    sch = _load("Project5")
    cpm = compute_cpm(sch)
    ribbon = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    rows = evaluate_catalog(sch, cpm)
    extras = (
        "logic_density",
        "insufficient_detail",
        "merge_hotspot",
        "avg_float_days",
        "max_float_days",
    )
    for mid in extras:
        assert rows[mid].value == float(getattr(ribbon, mid))
        assert rows[mid].status == "NA"  # informational — no threshold
        # …but the value IS real, so the extras stay applicable (the UI shows the number, not "—")
        assert rows[mid].applicable is True


def test_unscored_relationship_split_is_na_not_zero() -> None:
    # the golden carries no SS/FF or SF links -> those checks are NA, never a fabricated 0% PASS
    sch = _load("Project5")
    rows = evaluate_catalog(sch, compute_cpm(sch))
    assert rows["DCMA04_SSFF"].status == "NA"
    assert rows["DCMA04_SF"].status == "NA"
    # audit L1: a genuinely-unmeasurable cell is NOT applicable, so the UI shows "—" — the value
    # it carries (0.0) is a placeholder, never a real measurement reaching the analyst.
    assert rows["DCMA04_SSFF"].applicable is False
    assert rows["DCMA04_SF"].applicable is False


def test_scored_check_is_applicable() -> None:
    # a metric the audit actually scores (pass or fail) carries a real value → applicable
    sch = _load("Project5")
    rows = evaluate_catalog(sch, compute_cpm(sch))
    scored = [r for r in rows.values() if r.status in ("PASS", "FAIL")]
    assert scored, "expected at least one scored DCMA check"
    assert all(r.applicable for r in scored)


def test_cached_audit_matches_fresh_audit() -> None:
    sch = _load("Project2")
    cpm = compute_cpm(sch)
    fresh = evaluate_catalog(sch, cpm)  # computes its own audit
    cached = evaluate_catalog(sch, cpm, audit_schedule(sch, cpm))  # reuses one
    assert fresh == cached
