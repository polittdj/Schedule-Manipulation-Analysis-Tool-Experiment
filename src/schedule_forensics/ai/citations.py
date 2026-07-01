"""Citation enforcement — every narrative statement must carry file + UID + task (§6.D/D2).

The tool's AI narrative is forensic evidence: each sentence must be traceable to the parent
schedule. A :class:`CitedStatement` pairs a sentence with the :class:`Citation`s that back
it; :func:`assert_all_cited` is the hard gate (raises :class:`UncitedStatementError` if any
fact statement lacks a citation). A model may *rephrase* a statement's text but never strip
its citations — :func:`reattach` carries them onto polished prose and re-verifies coverage,
so the AI can never emit an uncited claim. The same gate guards the **figures**: a rephrase
that drops, invents, or alters any number (:func:`preserves_figures`) is discarded for the
engine's verbatim sentence — dates, counts, and percentages are evidence, not prose. It also
guards against an **introduced conclusion**: a rephrase that injects an accusatory/intent term
the engine never asserted (fraud, deliberate, concealed, …; :func:`introduces_loaded_terms`)
is likewise discarded — the model may polish wording, never add an unverified accusation.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from schedule_forensics.engine.dcma_audit import Citation

#: A numeric figure as the engine writes them: an optional leading minus, then an integer or
#: plain decimal. The sign is part of the figure — in schedule forensics a sign is load-bearing
#: (variance, total float, slip direction), so a rephrase that flips "-5 days" (ahead) to
#: "5 days behind" must change the multiset and force the verbatim fallback (audit M6). A model
#: reformatting "21600" as "21,600" likewise fails the check and the verbatim sentence is kept —
#: fail closed.
_FIGURE_RE = re.compile(r"-?\d+(?:\.\d+)?")

#: One evidence token per ISO date/timestamp, matched BEFORE the plain-number pattern. Without
#: this, "2026-03-02" tokenizes as 2026 / -03 / -02 and the month/day fragments enter the gates
#: as small negative "engine figures" — operands the Layer-B verifier could then use to
#: "reconstruct" (and thereby launder) an invented number (QC audit 2026-07-01, D1). A date is
#: one piece of evidence, not three numbers.
_TOKEN_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?|-?\d+(?:\.\d+)?")


def figure_tokens(text: str) -> list[str]:
    """The numeric-evidence tokens of ``text``, in order.

    ISO dates (and timestamps) are single whole tokens; every other number tokenizes exactly as
    :data:`_FIGURE_RE` (sign-aware, audit M6). This is THE tokenizer for every figure gate —
    ``preserves_figures``, the Ask-the-AI role gate, and the dual-model cross-check — so no gate
    can disagree with another about what counts as a figure.
    """
    return _TOKEN_RE.findall(text)


#: Accusatory / intent-attributing terms the engine never asserts. The engine reports *what*
#: changed (a constraint added, float eroded); it never concludes *why* (fraud, intent). A local
#: model polishing prose must not introduce such a conclusion — if a rephrase adds one of these
#: terms that the engine's own sentence did not contain, the verbatim engine sentence is kept
#: (audit H2). This guards *accuracy* (no unverified intent reaches a testimony reader); it does
#: NOT restrict legitimate numeric/analytic derivation, which carries none of these words.
_LOADED_TERMS = frozenset(
    {
        "fraud",
        "fraudulent",
        "fraudulently",
        "deliberate",
        "deliberately",
        "intentional",
        "intentionally",
        "conceal",
        "concealed",
        "concealing",
        "concealment",
        "falsify",
        "falsified",
        "falsifying",
        "falsification",
        "sabotage",
        "sabotaged",
        "malicious",
        "maliciously",
        "willful",
        "willfully",
        "deceive",
        "deceptive",
        "deception",
        "dishonest",
        "dishonestly",
        "criminal",
        "criminally",
    }
)
_WORD_RE = re.compile(r"[a-z]+")


def introduces_loaded_terms(source: str, candidate: str) -> bool:
    """True iff ``candidate`` adds an accusatory/intent term (``_LOADED_TERMS``) the ``source``
    did not contain — an unverified conclusion the engine never drew, so the rephrase is rejected
    in favor of the verbatim engine sentence (audit H2). A loaded term already present in the
    source (e.g. the engine's own ``manipulation`` finding) is fine; only *introduced* ones fail.
    """
    src_words = set(_WORD_RE.findall(source.lower()))
    return any(
        word in _LOADED_TERMS and word not in src_words
        for word in _WORD_RE.findall(candidate.lower())
    )


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


def preserves_figures(source: str, candidate: str) -> bool:
    """True iff ``candidate`` carries exactly the numeric figures of ``source``.

    Compared as a multiset: every number in the source must survive (same multiplicity)
    and no new number may appear. A rephrase may reorder figures and reword everything
    around them, but a dropped, invented, or altered date/count/percentage fails.
    Dates compare as whole tokens (:func:`figure_tokens`), so reformatting a date fails
    exactly as before — fail closed.
    """
    return Counter(figure_tokens(source)) == Counter(figure_tokens(candidate))


def reattach(texts: Sequence[str], sources: Sequence[CitedStatement]) -> tuple[CitedStatement, ...]:
    """Carry each source statement's citations onto a (possibly model-rephrased) text.

    ``texts`` is the rephrased prose, aligned 1:1 with ``sources``. Citations come from the
    deterministic source (never from the model), and the result is re-verified — so polishing
    can change wording but can never drop or invent a citation. A rephrased text is used only
    when it is non-empty, preserves every numeric figure of its source (:func:`preserves_figures`),
    **and** introduces no accusatory/intent term the source lacked
    (:func:`introduces_loaded_terms`); otherwise the engine's verbatim sentence is kept — the model
    may polish prose, never edit evidence or add an unverified conclusion.
    """
    if len(texts) != len(sources):
        raise UncitedStatementError(
            f"rephrased text count ({len(texts)}) does not match sources ({len(sources)})"
        )
    out: list[CitedStatement] = []
    for text, src in zip(texts, sources, strict=True):
        polished = text.strip()
        acceptable = (
            bool(polished)
            and preserves_figures(src.text, polished)
            and not introduces_loaded_terms(src.text, polished)
        )
        kept = polished if acceptable else src.text
        out.append(CitedStatement(text=kept, citations=src.citations))
    result = tuple(out)
    assert_all_cited(result)
    return result
