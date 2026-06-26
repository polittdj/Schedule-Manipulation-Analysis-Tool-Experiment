"""Citation-enforcement tests — the §6.D 'every statement cited' gate + figure preservation."""

from __future__ import annotations

import pytest

from schedule_forensics.ai.citations import (
    CitedStatement,
    Narrative,
    UncitedStatementError,
    assert_all_cited,
    introduces_loaded_terms,
    preserves_figures,
    reattach,
)
from schedule_forensics.engine.dcma_audit import Citation

C = Citation("Project5.mspdi.xml", 143, "Obtain CofO")


def test_rendered_appends_citation_tag() -> None:
    s = CitedStatement("The finish slipped.", (C,))
    assert s.rendered() == "The finish slipped. [Obtain CofO (UID 143, Project5.mspdi.xml)]"


def test_rendered_truncates_many_citations() -> None:
    cites = tuple(Citation("f", i, f"T{i}") for i in range(1, 6))
    assert "+2 more" in CitedStatement("x", cites).rendered()


def test_rendered_without_citations_returns_plain_text() -> None:
    assert CitedStatement("bare", ()).rendered() == "bare"


def test_assert_all_cited_raises_on_uncited() -> None:
    with pytest.raises(UncitedStatementError):
        assert_all_cited([CitedStatement("uncited claim", ())])
    assert_all_cited([CitedStatement("ok", (C,))])  # no raise


def test_reattach_preserves_citations_and_verifies() -> None:
    sources = (CitedStatement("orig a", (C,)), CitedStatement("orig b", (C,)))
    polished = reattach(("rephrased a", "rephrased b"), sources)
    assert [s.text for s in polished] == ["rephrased a", "rephrased b"]
    assert all(
        s.citations == (C,) for s in polished
    )  # citations come from the engine, not the model


def test_reattach_length_mismatch_raises() -> None:
    with pytest.raises(UncitedStatementError):
        reattach(("only one",), (CitedStatement("a", (C,)), CitedStatement("b", (C,))))


def test_reattach_empty_text_falls_back_to_source() -> None:
    out = reattach(("",), (CitedStatement("source text", (C,)),))
    assert out[0].text == "source text" and out[0].citations == (C,)


def test_narrative_to_text() -> None:
    n = Narrative("Title", (CitedStatement("a", (C,)),))
    text = n.to_text()
    assert text.startswith("# Title") and "UID 143" in text


def test_preserves_figures_allows_rewording_and_reordering() -> None:
    src = "37 of 126 activities (29.4%) missed their baseline finish."
    assert preserves_figures(src, src)
    assert preserves_figures(src, "Baseline finishes were missed by 29.4% — 37 out of 126.")
    assert preserves_figures("no numbers here", "still no numbers, just words")


def test_preserves_figures_rejects_dropped_invented_or_altered_numbers() -> None:
    src = "37 of 126 activities (29.4%)."
    assert not preserves_figures(src, "Some of the 126 activities missed (29.4%).")  # dropped 37
    assert not preserves_figures(src, "37 of 126 activities (29.4%), about 40 more at risk.")
    assert not preserves_figures(src, "38 of 126 activities (29.4%).")  # altered
    # multiplicity counts: a duplicated figure may not be silently de-duplicated
    assert not preserves_figures("44 days; threshold 44 days", "the 44-day threshold")
    # decimals are one figure, not two ("29.4" must not pass as "29" + "4")
    assert not preserves_figures("29.4% missed", "29% missed, 4 unknown")


def test_preserves_figures_is_sign_aware() -> None:
    # Audit M6: a sign is load-bearing in schedule forensics (variance/float/slip direction).
    # A flip from "-5" (ahead) to "5" (behind) must change the multiset and fail the gate.
    assert not preserves_figures("Variance -5 days", "Variance 5 days behind")
    assert not preserves_figures("total float -240 minutes", "total float 240 minutes")
    # an unchanged sign still passes; a preserved negative is fine
    assert preserves_figures("Net impact -148 days", "the net impact was -148 days")


def test_reattach_discards_rephrase_that_alters_figures() -> None:
    # a model that mangles a number loses its rephrase — the verbatim sentence is kept
    sources = (CitedStatement("the finish slipped 99 calendar days", (C,)),)
    out = reattach(("the finish slipped 100 calendar days",), sources)
    assert out[0].text == "the finish slipped 99 calendar days"
    assert out[0].citations == (C,)
    # while a figure-faithful rephrase is kept
    kept = reattach(("a 99-calendar-day slip on the finish",), sources)
    assert kept[0].text == "a 99-calendar-day slip on the finish"


def test_introduces_loaded_terms_flags_unverified_accusations() -> None:
    # Audit H2: a rephrase that injects an accusatory/intent term the engine never asserted
    # (fraud, deliberate, concealed, intentional, ...) must be flagged.
    src = "12 of 126 activities have hard constraints. Review and justify each."
    assert introduces_loaded_terms(
        src,
        "The contractor DELIBERATELY CONCEALED schedule fraud: 12 of 126 activities have hard "
        "constraints, proving intentional manipulation. Review.",
    )
    # a faithful polish that adds no loaded term is fine
    assert not introduces_loaded_terms(
        src, "Hard constraints appear on 12 of 126 activities; review and justify each."
    )
    # a loaded term already in the source (the engine's own finding) is not an introduction
    assert not introduces_loaded_terms(
        "Deliberate constraint manipulation suspected on 3 tasks.",
        "Deliberate manipulation suspected on 3 tasks.",
    )


def test_reattach_discards_prose_that_injects_an_accusation() -> None:
    # the verbatim engine sentence is kept when a rephrase preserves the digits but adds an
    # unverified conclusion (digits 12/126 unchanged, but "fraud"/"deliberately" injected)
    src = CitedStatement("12 of 126 activities have hard constraints; justify each.", (C,))
    tampered = (
        "12 of 126 activities have hard constraints — clear evidence the contractor "
        "deliberately concealed fraud."
    )
    out = reattach([tampered], (src,))
    assert out[0].text == src.text  # verbatim kept, accusation discarded
    # a clean rephrase with the same digits and no accusation IS used
    clean = "Hard date constraints sit on 12 of 126 activities; justify each."
    assert reattach([clean], (src,))[0].text == clean
