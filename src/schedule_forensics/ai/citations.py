"""Citation enforcement — every narrative statement must carry file + UID + task (§6.D/D2).

The tool's AI narrative is forensic evidence: each sentence must be traceable to the parent
schedule. A :class:`CitedStatement` pairs a sentence with the :class:`Citation`s that back
it; :func:`assert_all_cited` is the hard gate (raises :class:`UncitedStatementError` if any
fact statement lacks a citation). A model may *rephrase* a statement's text but never strip
its citations — :func:`reattach` carries them onto polished prose and re-verifies coverage,
so the AI can never emit an uncited claim.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from schedule_forensics.engine.dcma_audit import Citation


class UncitedStatementError(ValueError):
    """A narrative statement carries no citation — forbidden (§6.D: cite every statement)."""


@dataclass(frozen=True)
class CitedStatement:
    """One narrative sentence and the activities (file + UID + task) that substantiate it."""

    text: str
    citations: tuple[Citation, ...]

    def rendered(self) -> str:
        """The sentence with a compact, verifiable citation tag appended."""
        if not self.citations:
            return self.text
        shown = self.citations[:3]
        tag = "; ".join(str(c) for c in shown)
        if len(self.citations) > 3:
            tag += f"; +{len(self.citations) - 3} more"
        return f"{self.text} [{tag}]"


@dataclass(frozen=True)
class Narrative:
    """A cited forensic story: a title plus an ordered list of cited statements."""

    title: str
    statements: tuple[CitedStatement, ...]

    def to_text(self) -> str:
        body = "\n".join(f"- {s.rendered()}" for s in self.statements)
        return f"# {self.title}\n\n{body}"


def assert_all_cited(statements: Iterable[CitedStatement]) -> None:
    """Raise :class:`UncitedStatementError` if any statement lacks at least one citation."""
    for index, statement in enumerate(statements):
        if not statement.citations:
            raise UncitedStatementError(
                f"narrative statement #{index} has no citation: {statement.text!r}"
            )


def reattach(texts: Sequence[str], sources: Sequence[CitedStatement]) -> tuple[CitedStatement, ...]:
    """Carry each source statement's citations onto a (possibly model-rephrased) text.

    ``texts`` is the rephrased prose, aligned 1:1 with ``sources``. Citations come from the
    deterministic source (never from the model), and the result is re-verified — so polishing
    can change wording but can never drop or invent a citation.
    """
    if len(texts) != len(sources):
        raise UncitedStatementError(
            f"rephrased text count ({len(texts)}) does not match sources ({len(sources)})"
        )
    out = tuple(
        CitedStatement(text=text.strip() or src.text, citations=src.citations)
        for text, src in zip(texts, sources, strict=True)
    )
    assert_all_cited(out)
    return out
