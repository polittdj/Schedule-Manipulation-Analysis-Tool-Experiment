"""Citation-enforcement tests — the §6.D 'every statement cited' gate."""

from __future__ import annotations

import pytest

from schedule_forensics.ai.citations import (
    CitedStatement,
    Narrative,
    UncitedStatementError,
    assert_all_cited,
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
