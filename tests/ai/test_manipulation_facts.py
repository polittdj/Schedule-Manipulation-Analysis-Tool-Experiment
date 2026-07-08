"""Manipulation-forensics facts for the Q&A fact base (ADR-0150).

Operator gap: asked "what tasks had durations shortened to avoid UID X pushing right?",
the AI answered "the facts do not provide information on which tasks had their durations
shortened". These facts close that class of question with engine-computed, cited statements:
duration cuts on the driving/critical path, the reverted-changes counterfactual (what the
finish would be had the edits not been made), and the focused activity's baseline variance.
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.ai.qa import manipulation_forensics_facts
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.importers.mspdi import parse_mspdi_text

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _pair():
    scheds = [
        parse_mspdi_text(
            (_GOLDEN / f"{n}.mspdi.xml").read_text(encoding="utf-8"),
            source_file=f"{n}.mspdi.xml",
        )
        for n in ("Project2", "Project5")
    ]
    return scheds, [compute_cpm(s) for s in scheds]


def test_facts_cover_shortening_counterfactual_and_baseline_variance() -> None:
    scheds, cpms = _pair()
    texts = [f.rendered() for f in manipulation_forensics_facts(scheds, cpms, target_uid=145)]
    joined = "\n".join(texts)
    # the driving-path shortening question is answered either way (found or explicitly none)
    assert "duration shortened" in joined.lower()
    assert "driving path to UID 145" in joined
    # the counterfactual quantifies what reverting the edits would do, naming the activities
    assert "Counterfactual (changes reverted)" in joined
    assert "CHANGED, not completed" in joined
    # the focused activity's baseline-vs-current variance is stated
    assert "baseline finish" in joined and "+201 calendar days" in joined
    # every fact carries citations (the never-uncited contract)
    assert all(f.citations for f in manipulation_forensics_facts(scheds, cpms, target_uid=145))


def test_untargeted_facts_use_the_critical_path_basis() -> None:
    scheds, cpms = _pair()
    texts = [f.rendered() for f in manipulation_forensics_facts(scheds, cpms)]
    assert any("the critical path" in t for t in texts)


def test_single_version_returns_no_facts() -> None:
    scheds, cpms = _pair()
    assert manipulation_forensics_facts(scheds[:1], cpms[:1]) == ()
