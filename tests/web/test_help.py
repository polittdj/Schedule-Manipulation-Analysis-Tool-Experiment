"""Metric-dictionary coverage — every metric the engine emits must be documented (§6.A, A5)."""

from __future__ import annotations

from schedule_forensics.engine.metrics import (
    compute_baseline_compliance,
    compute_change_metrics,
    compute_completion_performance,
    compute_dcma14,
    compute_evm_indices,
    compute_float_bands,
    compute_net_finish_impact,
    compute_schedule_quality,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.help import (
    METRIC_DICTIONARY,
    RELIABILITY_DIMENSIONS,
    documented_metric_ids,
    metric_doc,
    reliability_dimension,
)


def _emitted_metric_ids(p2: Schedule, p5: Schedule) -> set[str]:
    ids: set[str] = set()
    for results in (
        compute_dcma14(p5),
        compute_schedule_quality(p5),
        compute_baseline_compliance(p5),
        compute_evm_indices(p5),
        compute_change_metrics(p5, p2),
        compute_float_bands(p5),
        compute_completion_performance(p5),
    ):
        ids.update(r.metric_id for r in results.values())
    ids.add(compute_net_finish_impact(p5, p2).metric_id)
    ids.add("driving_slack")  # SSI tier metric (engine/driving_slack)
    return ids


def test_every_emitted_metric_is_documented(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    emitted = _emitted_metric_ids(golden_project2, golden_project5)
    missing = emitted - documented_metric_ids()
    assert not missing, f"undocumented metrics in the in-tool dictionary: {sorted(missing)}"


def test_each_doc_has_definition_formula_and_source() -> None:
    for doc in METRIC_DICTIONARY.values():
        assert doc.name and doc.definition and doc.formula and doc.source
        assert "cites file + UniqueID + task name" in doc.citation_basis


def test_metric_doc_lookup() -> None:
    assert metric_doc("DCMA14") is not None and metric_doc("DCMA14").name == "BEI"
    assert metric_doc("nope") is None


def test_reliability_dimension_tags_every_documented_metric() -> None:
    """D9: every documented metric carries one of the four handbook reliability dimensions."""
    for mid in documented_metric_ids():
        assert reliability_dimension(mid) in RELIABILITY_DIMENSIONS, mid


def test_reliability_dimension_family_assignments() -> None:
    """Representative family-level assignments (the documented organizing lens)."""
    assert reliability_dimension("cpi") == "Affordability"  # cost EVM
    assert reliability_dimension("spi") == "Affordability"
    assert reliability_dimension("DCMA10") == "Comprehensiveness"  # resource loading
    assert reliability_dimension("missing_logic") == "Comprehensiveness"
    assert reliability_dimension("DCMA05") == "Construction"  # hard constraints
    assert reliability_dimension("float_total_0") == "Construction"
    assert reliability_dimension("DCMA14") == "Realism"  # BEI — execution performance
    assert reliability_dimension("spi_t") == "Realism"
