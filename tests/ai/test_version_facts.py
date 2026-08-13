"""The cross-version population facts (ADR-0392) — the AI must be told the whole workbook exists.

The defect these tests pin, measured before the fix on a synthetic 31-version workbook: the
workbook fact sheet held 23 facts, exactly ONE of which named more than one version (the "How to
Verify" boilerplate), and it carried no per-version series of any kind. A local model asked to read
the S-curve across 31 files answered that its evidence covered two file versions and contained no
cumulative-progress series — an accurate description of what it had been given.

So the assertions below are about the EVIDENCE, not about model prose: does the fact base state the
population, does it carry a point for every loaded version, and can fact selection drop it?
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.ai.citations import CitedStatement, assert_all_cited
from schedule_forensics.ai.qa import build_workbook_fact_sheet, model_evidence, relevant_facts
from schedule_forensics.ai.version_facts import version_series_facts
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import Citation
from schedule_forensics.model.schedule import Schedule

_FIRST_DATA_DATE = dt.datetime(2026, 4, 15)  # inside golden Project5's own window


def _versions(base: Schedule, n: int, *, statused: bool = True) -> list[Schedule]:
    return [
        base.model_copy(
            update={
                "name": f"v{i + 1:02d}.mpp",
                "source_file": f"v{i + 1:02d}.mpp",
                "status_date": (_FIRST_DATA_DATE + dt.timedelta(days=30 * i) if statused else None),
            }
        )
        for i in range(n)
    ]


def test_every_loaded_version_appears_in_the_series_facts(golden_project5: Schedule) -> None:
    """THE regression: 31 loaded files must produce evidence naming all 31, not two."""
    versions = _versions(golden_project5, 31)
    facts = version_series_facts(versions, [compute_cpm(v) for v in versions])
    assert facts, "a multi-version workbook must produce population facts"
    blob = "\n".join(f.text for f in facts)
    for v in versions:
        assert v.source_file is not None and v.source_file in blob, f"{v.source_file} unmentioned"
    assert "31 schedule version(s) are loaded" in blob
    assert "S-CURVE SERIES across all 31 loaded version(s)" in blob


def test_the_workbook_fact_sheet_carries_the_population(golden_project5: Schedule) -> None:
    """The end-to-end path the /api/ask workbook route uses."""
    versions = _versions(golden_project5, 31)
    cpms = [compute_cpm(v) for v in versions]
    facts = build_workbook_fact_sheet(versions, cpms)
    assert_all_cited(facts)
    texts = [f.text for f in facts]
    assert any(t.startswith("WORKBOOK POPULATION: 31 ") for t in texts)
    assert any(t.startswith("S-CURVE SERIES across all 31 ") for t in texts)
    assert any(t.startswith("S-CURVE TREND across the 31 ") for t in texts)
    assert any(t.startswith("SCHEDULE-LOGIC FINISH SERIES across 31 ") for t in texts)
    # the briefing's frame fact still leads — the population block rides behind it
    assert texts[0].startswith("In one sentence:")


def test_the_population_block_survives_an_unrelated_question(golden_project5: Schedule) -> None:
    """A question sharing NO words with the series facts must still be answered with them in
    evidence — ranking-by-overlap is right for evidence and wrong for the population frame."""
    versions = _versions(golden_project5, 31)
    facts = build_workbook_fact_sheet(versions, [compute_cpm(v) for v in versions])
    question = "zzz qqq xyzzy"  # deliberately overlaps nothing
    for selected in (model_evidence(facts, question), relevant_facts(facts, question)):
        texts = [f.text for f in selected]
        assert any(t.startswith("WORKBOOK POPULATION: 31 ") for t in texts)
        assert any(t.startswith("S-CURVE SERIES") for t in texts)
        assert any(t.startswith("S-CURVE TREND") for t in texts)
        assert any(t.startswith("SCHEDULE-LOGIC FINISH SERIES") for t in texts)


def test_pinned_facts_survive_a_cap_smaller_than_the_fact_sheet() -> None:
    """The cap is what would have dropped them: prove it cannot, at a cap below the pinned count."""
    cite = (Citation("f.mpp", 0, "f.mpp"),)
    frame = CitedStatement("frame", cite)
    pinned = [CitedStatement(f"pinned {i}", cite, pinned=True) for i in range(4)]
    noise = [CitedStatement(f"noise {i}", cite) for i in range(30)]
    facts = (frame, *pinned, *noise)

    ev = model_evidence(facts, "noise", limit=3)
    assert ev[0] is frame
    assert all(p in ev for p in pinned)

    shown = relevant_facts(facts, "noise", limit=3)
    assert shown[0] is frame
    assert all(p in shown for p in pinned)


def test_ranked_evidence_still_follows_the_pinned_block() -> None:
    """Pinning must not starve the evidence: matching facts still rank in behind the frame."""
    cite = (Citation("f.mpp", 0, "f.mpp"),)
    facts = (
        CitedStatement("frame", cite),
        CitedStatement("pinned population", cite, pinned=True),
        CitedStatement("nothing to do with it", cite),
        CitedStatement("float erosion on the critical path", cite),
    )
    ev = model_evidence(facts, "float erosion")
    assert [f.text for f in ev][:2] == ["frame", "pinned population"]
    assert ev[2].text == "float erosion on the critical path"

    shown = relevant_facts(facts, "float erosion")
    assert [f.text for f in shown] == [
        "frame",
        "pinned population",
        "float erosion on the critical path",
    ]


def test_undated_versions_are_reported_unreadable_never_zero(golden_project5: Schedule) -> None:
    """Law 2 at the fact boundary: no data date must never be narrated as 0% / on plan."""
    versions = _versions(golden_project5, 4, statused=False)
    facts = version_series_facts(versions, [compute_cpm(v) for v in versions])
    blob = "\n".join(f.text for f in facts)
    assert "none of the 4 loaded version(s) carries a data date" in blob
    assert "This is missing input, not zero progress." in blob
    assert "S-CURVE TREND" not in blob  # no readable points => no verdict is invented
    assert "gap" not in blob.split("S-CURVE SERIES")[1]


def test_the_two_unreadable_reasons_are_not_conflated(golden_project5: Schedule) -> None:
    """No data date and no activities in scope are different failures; the series says which."""
    scoped_out = golden_project5.model_copy(
        update={
            "name": "scoped-out.mpp",
            "source_file": "scoped-out.mpp",
            "tasks": (),
            "status_date": _FIRST_DATA_DATE,
        }
    )
    undated = golden_project5.model_copy(
        update={"name": "undated.mpp", "source_file": "undated.mpp", "status_date": None}
    )
    versions = [scoped_out, undated, *_versions(golden_project5, 2)]
    blob = "\n".join(f.text for f in version_series_facts(versions))
    assert "scoped-out.mpp no activities in scope — unreadable" in blob
    assert "undated.mpp no data date — unreadable" in blob


def test_a_single_version_produces_no_series(golden_project5: Schedule) -> None:
    """One file is not a series; the existing single-version facts already name it."""
    assert version_series_facts([golden_project5], [compute_cpm(golden_project5)]) == ()


def test_a_long_portfolio_states_its_own_elision(golden_project5: Schedule) -> None:
    """Past the render cap the middle is dropped — and SAID to be dropped. A truncation the
    reader cannot see is the exact defect this module exists to fix."""
    versions = _versions(golden_project5, 90)
    facts = version_series_facts(versions, [compute_cpm(v) for v in versions])
    blob = "\n".join(f.text for f in facts)
    assert "90 schedule version(s) are loaded" in blob
    assert "50 versions between the oldest 20 and the newest 20 are omitted" in blob
    assert "they are loaded and analyzed" in blob
    assert "v01.mpp" in blob and "v90.mpp" in blob  # both edges survive


def test_the_facts_are_all_cited_and_pinned(golden_project5: Schedule) -> None:
    versions = _versions(golden_project5, 5)
    facts = version_series_facts(versions, [compute_cpm(v) for v in versions])
    assert_all_cited(facts)
    assert all(f.pinned for f in facts)
    for f in facts:  # every loaded file is cited: the population IS the subject
        assert len(f.citations) == 5


@pytest.mark.parametrize("with_cpms", [True, False])
def test_the_finish_series_is_absent_rather_than_invented(
    golden_project5: Schedule, with_cpms: bool
) -> None:
    versions = _versions(golden_project5, 3)
    cpms = [compute_cpm(v) for v in versions] if with_cpms else None
    blob = "\n".join(f.text for f in version_series_facts(versions, cpms))
    assert ("SCHEDULE-LOGIC FINISH SERIES" in blob) is with_cpms
