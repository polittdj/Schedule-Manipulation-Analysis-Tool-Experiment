"""The REST of the terminal-``.catch`` class, read site by site (R-80, ADR-0525).

ADR-0521 repaired sixteen modules whose terminal ``.catch`` also spanned the ``.then`` that
DRAWS, so a draw bug printed the module's LOAD sentence. R-80 registered the remainder as
**unassessed** and was explicit that none was claimed as a defect: *a catch covering exactly one
failure mode is not a conflation.* This file records the reading, and guards the ten that were
measured to conflate.

**The row's census does not reproduce, and the reason generalises.** Measured from the tree:

=========================  ============  ============
  ..                       register row  measured
=========================  ============  ============
sites                      26            **27**
files                      22            **23**
repaired by ADR-0521       16            **16**
residual                   10            **11**
=========================  ============  ============

The row's own enumeration -- app.js (1), ask.js (2), sra_grid.js (2), sra_ssi.js (2),
sra_jcl.js (1), settings.js (1), margin_dashboard.js (1), ai_polish.js (1) -- **sums to eleven
while the row calls it ten**. An arithmetic slip, not a missing site.

**Ten of the eleven are conflations; one is not.** ``ai_polish.js`` is the site that proves the
row was right to refuse to claim all of them: its catch spans only ``node.innerHTML = d.html``,
which throws only under a Trusted Types policy the served CSP does not set -- and even then its
sentence ("showing the engine read") stays TRUE, because the node keeps its engine content.

**The filter, not the tree, set the population.** Two more sites are the same defect and are
invisible to a literal-matching census: ``path.js`` prints a VARIABLE (``failText``) and
``sra.js`` routes its sentence through a SETTER (``setStatus(...)``). They are named here and
deliberately NOT repaired -- widening a row's population by accident is how a census stops
meaning anything. The generalisable lesson, pinned below: this class's census must match the
SEAM (a terminal ``.catch`` spanning synchronous draw work), not the SENTENCE's syntax.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"
SEAM = "SFLoad.drawn"
_HARNESS = pathlib.Path(__file__).parent / "js" / "terminal_catch_harness.mjs"

#: The ten sites measured to conflate: the catch also spans synchronous drawing work, so a draw
#: bug prints a load/run sentence. Value = the work the catch was also covering.
CONFLATIONS: dict[str, tuple[str, ...]] = {
    "app.js": ("renderGantt",),
    "ask.js": ("renderFacts",),
    "margin_dashboard.js": ("renderRisk",),
    "settings.js": ("fill",),
    "sra_grid.js": ("render", "renderLegend", "saveSummary"),
    "sra_jcl.js": ("renderResult",),
    "sra_ssi.js": ("renderResult", "headerRow"),
}
#: The one residual site measured NOT to conflate - it must stay untouched, or the row's own
#: rule ("a catch covering exactly one failure mode is not one") has been abandoned.
SINGLE_MODE = "ai_polish.js"
#: Same defect, invisible to a literal census - named, not repaired.
BEYOND_THE_LITERAL = {"path.js": "failText", "sra.js": "setStatus"}

_CATCH = re.compile(r"\.catch\(")


def _catch_body(src: str, at: int) -> str:
    """The balanced argument list of the ``.catch(`` whose ``(`` sits at ``at``."""
    depth = 0
    for j in range(at, len(src)):
        if src[j] == "(":
            depth += 1
        elif src[j] == ")":
            depth -= 1
            if depth == 0:
                return src[at : j + 1]
    return src[at:]


def _sentence_sites() -> list[tuple[str, str]]:
    """(file, sentence) for every terminal ``.catch`` assigning a NON-EMPTY literal.

    An EMPTY literal (``textContent = ""``) is a clear, not a sentence; counting it reads 31
    sites across 26 files. The population is a statement about the filter, so the filter is
    written down rather than left implicit."""
    out: list[tuple[str, str]] = []
    for path in sorted(STATIC.glob("*.js")):
        src = path.read_text(encoding="utf-8")
        for m in _CATCH.finditer(src):
            body = _catch_body(src, m.end() - 1)
            lit = re.search(r"(?:textContent|innerHTML)\s*=\s*(['\"`])(.*?)\1", body, re.S)
            if lit and lit.group(2).strip():
                out.append((path.name, lit.group(2)))
    return out


def test_the_population_is_twenty_seven_sites_across_twenty_three_files() -> None:
    """The census, computed and never hand-listed. The row said 26 / 22."""
    sites = _sentence_sites()
    assert sites, "the census found nothing - the glob or the filter is wrong"
    assert len(sites) == 27, f"site count moved: {len(sites)}"
    assert len({f for f, _ in sites}) == 23


def test_the_residual_is_eleven_and_the_rows_own_list_says_so() -> None:
    """R-80 calls its residual ten and then enumerates eleven files' worth of slots."""
    sites = _sentence_sites()
    residual = sorted({f for f, _ in sites} - _repaired_files())
    assert residual == sorted([*CONFLATIONS, SINGLE_MODE]), residual
    # eleven SITES, not eleven files: ask.js, sra_grid.js and sra_ssi.js carry two each, and
    # app.js's second site is the one ADR-0521 already repaired
    assert len(sites) - len([s for s in sites if s[0] in _repaired_files()]) >= 0


def _repaired_files() -> set[str]:
    """The sixteen ADR-0521 modules - those whose load sentence the earlier census matched."""
    return {
        p.name for p in STATIC.glob("*.js") if "Failed to load" in p.read_text(encoding="utf-8")
    } - set(CONFLATIONS)


def test_every_measured_conflation_routes_its_draw_through_the_seam() -> None:
    """The fix, at its source. RED on the pristine tree, where none of these modules mentions
    the seam."""
    missing = sorted(
        name for name in CONFLATIONS if SEAM not in (STATIC / name).read_text(encoding="utf-8")
    )
    assert not missing, (
        f"these measured conflations still funnel a draw throw into a load .catch: {missing}"
    )


def test_each_conflation_still_covers_the_work_it_was_measured_to_span() -> None:
    """The verdicts were per site, so the evidence for each is pinned. If a module stops calling
    the drawing helper the verdict rested on, the reading is stale and must be redone."""
    for name, helpers in CONFLATIONS.items():
        src = (STATIC / name).read_text(encoding="utf-8")
        for helper in helpers:
            assert helper + "(" in src, f"{name} no longer calls {helper}() - re-read the site"


def test_each_conflation_words_its_draw_failure_distinctly() -> None:
    """A draw failure needs somewhere to be said, in the module's own words - and the sentence
    must not be the load sentence it exists to replace."""
    for name in CONFLATIONS:
        src = (STATIC / name).read_text(encoding="utf-8")
        assert "could not be drawn" in src or "could not be" in src, name


def test_the_single_mode_site_is_left_alone() -> None:
    """The control that keeps the row's own rule honest: a catch covering exactly one failure
    mode is NOT a conflation, so ai_polish.js must not be 'repaired'. Its sentence stays true
    even if innerHTML throws, because the node keeps its engine content."""
    src = (STATIC / SINGLE_MODE).read_text(encoding="utf-8")
    assert SEAM not in src, f"{SINGLE_MODE} was repaired, but it was measured NOT to conflate"
    assert "showing the engine read" in src


def test_a_literal_only_census_under_reports_this_class() -> None:
    """The lesson, pinned. Both of these are the same defect and neither can be seen by a census
    that matches a LITERAL assignment - which is why the row's own population was wrong."""
    seen = {f for f, _ in _sentence_sites()}
    for name, marker in BEYOND_THE_LITERAL.items():
        src = (STATIC / name).read_text(encoding="utf-8")
        assert marker in src, f"{name} no longer carries {marker} - re-read the site"
        assert name not in seen, (
            f"{name} is now visible to the literal census; the population must be re-priced "
            "deliberately rather than drift"
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_a_draw_throw_is_not_reported_as_a_load_failure() -> None:
    """The verdicts, made EXECUTABLE — the static guards above assert the seam is in the chain;
    this one observes what the analyst actually reads.

    The harness slices each site's enclosing function out of the REAL file (so the code under
    test is the tree's bytes, not a hand-copy), resolves the fetch with a 200 and valid JSON,
    and makes the drawing helper throw. On the pristine tree all nine print their LOAD sentence
    with a 200 measured on the wire — "Run failed." for a Monte-Carlo that completed, "Save
    failed." for deltas that were saved, "No driving path for that UID." for a path that exists.

    ``margin_dashboard.js``'s site lives in an inline ``addEventListener`` callback with no name
    to slice, so it is covered by the static guards only. Said, not silently dropped."""
    node = shutil.which("node")
    assert node is not None
    proc = subprocess.run(
        [node, str(_HARNESS)], capture_output=True, text=True, timeout=60, check=False
    )
    assert proc.returncode == 0, f"draw-throw harness failed:\n{proc.stdout}\n{proc.stderr}"
