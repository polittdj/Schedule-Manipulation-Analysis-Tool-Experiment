"""Pin the two standing WORKING RULES (QC-1 / QC-2) in ``CLAUDE.md`` so they cannot be
silently deleted, softened, or demoted (ADR-0393).

Why this test exists, in one sentence: **the 2026-08-13 audit's headline lesson was that a
guard is only as strong as the test that pins its DATA** — POLARIS's entire Law-1 locality
guarantee turned out to rest on an unpinned frozenset, and widening it left 226-854 tests green.
A standing rule written only in prose is exactly that same shape: load-bearing data with nothing
asserting it is still there. So the rules that govern how every future session works are pinned
the same way a security constant should have been.

What this asserts, and what it deliberately does NOT:

* IT ASSERTS the two rule sections exist, are numbered, carry their binding normative clauses,
  and retain the mandatory language ("MUST", "NO EXCEPTIONS", "not optional"). A future edit may
  freely improve the wording AROUND those clauses.
* IT DOES NOT assert byte-exact prose. A guard that fires on ordinary editing gets deleted, and
  then it guards nothing — the same reasoning ``.githooks/pre-commit`` uses for leaving prose
  alone (CLAUDE.md, Law 1).

The positive control matters here: asserting only the PRESENCE of substrings would pass just as
happily against a file that had been replaced by something enormous and irrelevant, so the
structural checks below (heading present, rule appears in the laws region, file is a plausible
CLAUDE.md) are what make the absence-checks meaningful.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

#: The section heading that must carry both rules.
_SECTION_HEADING = "## The two non-negotiable working rules"

#: The two rule headings, in order. Each must be present verbatim — a rule that loses its own
#: heading has been merged into surrounding prose, which is how the predecessor of QC-2 came to be
#: skipped for months (it was a trailing sentence in the ADR-0240 section).
_RULE_HEADINGS = {
    "QC-1": "### QC-1 — Prove or refute it before you report it",
    "QC-2": "### QC-2 — Read everything, verify everything",
}

#: Rule id -> the normative clauses that give the rule its force, checked WITHIN THAT RULE'S OWN
#: SECTION rather than file-globally.
#:
#: The scoping is load-bearing and was paid for: the first version of this guard checked the whole
#: file, so stripping "sandbox" and "refute" out of QC-1's binding sentence still passed, because
#: both words survived in QC-1's bullet list. A mutation battery caught it. A census can be exact
#: and still not be membership — the clause must be in the sentence that binds, not merely
#: somewhere in the document.
_REQUIRED_CLAUSES: dict[str, list[str]] = {
    "QC-1": [
        # the trigger: before a conclusion, a change, OR a document update
        "before any change is made",
        "conclusion is drawn",
        "document is updated",
        # the obligation: an executable pass/fail check, run in a sandbox, that could refute
        "pass/fail",
        "sandbox",
        "refute",
        # the ordering: the proof comes BEFORE the report/change
        "before the result is reported",
        # red-before-green and mutation are what make a check evidence rather than decoration.
        # NOTE the phrase, not the bare word "fail": a mutation proved that bare "fail" still
        # matched "never failed" further down the section, so softening the binding sentence to
        # "should ideally be observed to work" slipped through. Pin the obligation, not a token.
        "observed to fail",
        "mutation",
        "unverified",
    ],
    "QC-2": [
        "read everything",
        "skip nothing",
        "assume nothing",
        "verify",
        # scope: not just code
        "documentation",
        "instructions",
        # the interlock: errors found under QC-2 re-enter QC-1
        "qc-1 applies before",
    ],
}


def _rule_section(rule: str) -> str:
    """The normalized text of ONE rule's own section — from its heading to the next heading.

    Scoping the search to the rule's own slice is what makes a missing clause detectable; see the
    note on ``_REQUIRED_CLAUSES``.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")
    heading = _RULE_HEADINGS[rule]
    assert heading in text, f"missing rule heading: {heading!r}"
    body = text.split(heading, 1)[1]
    # stop at the next heading of any level (### sibling rule, or ## next section)
    nxt = re.search(r"\n#{2,3} ", body)
    if nxt:
        body = body[: nxt.start()]
    return re.sub(r"\s+", " ", body.lower())


#: Language that makes the rules binding. If a future edit strips these, the rules have been
#: demoted to advice and this test must fail.
_MANDATORY_LANGUAGE = ["must", "no exceptions", "not optional"]


def _normalized() -> str:
    """CLAUDE.md, lowercased with runs of whitespace collapsed to single spaces.

    Normalizing means a re-wrap or a reflow does not break the guard, while a deletion or a
    softened clause still does.
    """
    return re.sub(r"\s+", " ", CLAUDE_MD.read_text(encoding="utf-8").lower())


def test_claude_md_is_the_file_we_think_it_is() -> None:
    """Positive control. Without this, every assertion below could pass vacuously against a
    file that had been replaced wholesale — the 'empty sweep needs a positive control' rule."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert CLAUDE_MD.is_file(), CLAUDE_MD
    assert len(text) > 5_000, f"CLAUDE.md is implausibly small ({len(text)} bytes)"
    assert "## The two non-negotiable laws" in text, "the product laws heading is gone"
    assert "Data sovereignty (CUI)" in text, "Law 1 is gone"
    assert "Fidelity over speed" in text, "Law 2 is gone"


def test_the_working_rules_section_exists() -> None:
    """The rules must live under their own heading, not be buried in another section as a
    trailing sentence — which is exactly where 'READ EVERYTHING, ASSUME NOTHING, VERIFY
    EVERYTHING' sat before ADR-0393, and why it was routinely skipped."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert _SECTION_HEADING in text, f"missing section heading: {_SECTION_HEADING!r}"


def test_both_rules_keep_their_own_headings() -> None:
    """A rule merged into surrounding prose is a rule that gets skipped."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    missing = [h for h in _RULE_HEADINGS.values() if h not in text]
    assert not missing, f"CLAUDE.md lost rule headings: {missing}"


def test_both_rules_carry_their_binding_clauses() -> None:
    """Every normative clause that gives QC-1/QC-2 their force is present IN ITS OWN SECTION."""
    missing: list[tuple[str, str]] = []
    for rule, clauses in _REQUIRED_CLAUSES.items():
        section = _rule_section(rule)
        for clause in clauses:
            if clause.lower() not in section:
                missing.append((rule, clause))
    assert not missing, f"CLAUDE.md lost binding clauses (per-rule scope): {missing}"


def test_the_rules_are_still_mandatory_not_advisory() -> None:
    """A rule that has been reworded into a suggestion is a deleted rule."""
    text = _normalized()
    missing = [phrase for phrase in _MANDATORY_LANGUAGE if phrase not in text]
    assert not missing, f"CLAUDE.md lost its mandatory language: {missing}"


def test_the_rules_are_not_commented_out() -> None:
    """Demotion by HTML comment is deletion with extra steps."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    for block in re.findall(r"<!--.*?-->", text, flags=re.S):
        assert "QC-1" not in block and "QC-2" not in block, (
            "a standing rule has been commented out of CLAUDE.md"
        )
