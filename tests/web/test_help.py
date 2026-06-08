"""Metric-dictionary coverage — every metric the engine emits must be documented (§6.A, A5)."""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_change_metrics,
    compute_dcma14,
    compute_evm_indices,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web.help import METRIC_DICTIONARY, documented_metric_ids, metric_doc

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _emitted_metric_ids() -> set[str]:
    p2 = parse_mspdi(GOLDEN / "project2_5" / "Project2.mspdi.xml")
    p5 = parse_mspdi(GOLDEN / "project2_5" / "Project5.mspdi.xml")
    ids: set[str] = set()
    for results in (
        compute_dcma14(p5),
        compute_schedule_quality(p5),
        compute_baseline_compliance(p5),
        compute_evm_indices(p5),
        compute_change_metrics(p5, p2),
    ):
        ids.update(r.metric_id for r in results.values())
    ids.add(compute_net_finish_impact(p5, p2).metric_id)
    ids.add("driving_slack")  # SSI tier metric (engine/driving_slack)
    return ids


def test_every_emitted_metric_is_documented() -> None:
    emitted = _emitted_metric_ids()
    missing = emitted - documented_metric_ids()
    assert not missing, f"undocumented metrics in the in-tool dictionary: {sorted(missing)}"


def test_each_doc_has_definition_formula_and_source() -> None:
    for doc in METRIC_DICTIONARY.values():
        assert doc.name and doc.definition and doc.formula and doc.source
        assert "cites file + UniqueID + task name" in doc.citation_basis


def test_metric_doc_lookup() -> None:
    assert metric_doc("DCMA14") is not None and metric_doc("DCMA14").name == "BEI"
    assert metric_doc("nope") is None
