"""Every tolerance-shaped assertion in the CI parity population is classified in a ledger tied
to the tree, and every family the ledger classes as TOLERANCE is named in
``docs/PARITY-REPORT.md`` as "within documented tolerance" with no "exact" beside it
(R-18 / NUM-01, ADR-0529).

NUM-01 found "parity" covering three different claims — an exact pin, a transcribed oracle, and
agreement inside a band — with the report calling a banded family "exact" (SPI / TCPI sat at
"✅ exact" beside a ``<= 0.0101`` gate). A doc that says "exact" where the test says "within
0.01" is the failure a testimony reader cannot detect from the doc alone, so the doc is linted
against the tests, not against itself.

The instrument has two halves, both tied to the tree:

* **AST rows** (``seen = ast``): every ``Compare`` in the population whose ``<`` / ``<=`` side is
  an ``abs(...)`` call, and every ``pytest.approx(...)`` comparison, keyed by (file, normalized
  source). A new, moved or reworded site is unclassified until it is ledgered here by name; a
  ledger row the tree no longer carries is stale by name. Two shapes the walker CANNOT see are
  ledgered as **text rows** (``seen = text``), whose site text must still occur in the file: a
  compare whose ``abs()`` sits upstream of the compared name (the leveled UID 152 battery's
  ``d < 0.02``) and a two-sided range with no ``abs()`` (R-57's ``0 < ... <= 120``). A tolerance
  bound carried in a NAME (``days``, ``bcws_tol``, ``_TOL_DAYS``, ``tol``) is classified by the
  value the test binds it to at the time of ledgering — the walker reads shape, not value.
* **The doc lint**: every ``tolerance`` row names an anchor phrase; each anchor must occur in the
  report, every line carrying it must contain the phrase "within documented tolerance", and no
  line carrying it may contain the word "exact". An ``exact`` row (a zero band, a float epsilon,
  a bare ``approx`` at rel 1e-6) needs no anchor: it IS an equality.
"""

from __future__ import annotations

import ast
import csv
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "docs" / "PARITY-REPORT.md"
LEDGER = Path(__file__).with_name("parity_tolerance_ledger.tsv")

#: the CI parity step's population, verbatim from ``.github/workflows/ci.yml`` (a bare
#: ``-m parity`` collects more; this is what the gate RUNS)
POPULATION = (
    "tests/parity",
    "tests/engine/test_ssi_leveled_uid152.py",
    "tests/importers/test_msp_views.py",
)
PHRASE = "within documented tolerance"
_EXACT_WORD = re.compile(r"\bexact\b", re.IGNORECASE)

#: class -> what it asserts (a class not listed here is not a class)
CLASSES: dict[str, str] = {
    "exact": "an equality written in a tolerance shape: a zero band (``days`` is 0 on every "
    "row, ``bcws_tol`` 0.0), a float epsilon (1e-6 / 1e-9 on a serial or a divisor), or a bare "
    "``pytest.approx`` (rel 1e-6) — no figure is accepted that the reference does not print",
    "tolerance": "agreement inside a stated band — a display precision the reference writes "
    "(2 dp, the cent, the minute), a statistical band (the SRA oracles), or a floor count — "
    "named in the report as within documented tolerance, never as exact",
}


class Row(NamedTuple):
    file: str
    cls: str
    seen: str
    site: str
    anchor: str


def _files() -> list[Path]:
    out: list[Path] = []
    for rel in POPULATION:
        p = REPO / rel
        out.extend(sorted(p.glob("*.py")) if p.is_dir() else [p])
    return out


def _is_abs(n: ast.AST) -> bool:
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "abs"


def _is_approx(n: ast.AST) -> bool:
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "approx"


def _ast_sites() -> Counter[tuple[str, str]]:
    """(file, normalized source) of every tolerance-shaped comparison in the population."""
    out: Counter[tuple[str, str]] = Counter()
    for path in _files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO).as_posix()
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Compare):
                continue
            sides = [node.left, *node.comparators]
            banded = any(isinstance(o, (ast.Lt, ast.LtE)) for o in node.ops) and any(
                _is_abs(s) for s in sides
            )
            if banded or any(_is_approx(s) for s in sides):
                seg = " ".join((ast.get_source_segment(text, node) or "").split())
                out[(rel, seg)] += 1
    return out


def _ledger() -> list[Row]:
    rows: list[Row] = []
    with LEDGER.open(encoding="utf-8", newline="") as fh:
        for rec in csv.reader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"):
            assert len(rec) == 5, rec
            rows.append(Row(*rec))
    return rows


def _diff(
    tree: Counter[tuple[str, str]], ledger: Counter[tuple[str, str]]
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    """(unledgered, stale): sites the tree has beyond the ledger, and ledger rows the tree
    no longer carries — each with the surplus count, by name."""
    unledgered = sorted((f, c, n) for (f, c), n in (tree - ledger).items())
    stale = sorted((f, c, n) for (f, c), n in (ledger - tree).items())
    return unledgered, stale


def _doc_findings(report: str, rows: list[Row]) -> list[str]:
    """Every way the report's wording disagrees with the ledger, by anchor."""
    lines = report.splitlines()
    out: list[str] = []
    for anchor in sorted({r.anchor for r in rows if r.cls == "tolerance"}):
        carrying = [ln for ln in lines if anchor in ln]
        if not carrying:
            out.append(f"{anchor!r}: not named in the report")
            continue
        for ln in carrying:
            if PHRASE not in ln:
                out.append(f"{anchor!r}: a line names it without {PHRASE!r}: {ln[:80]!r}")
            if _EXACT_WORD.search(ln):
                out.append(f"{anchor!r}: 'exact' sits beside a tolerance family: {ln[:80]!r}")
    return out


def test_the_walker_sees_the_population() -> None:
    """Positive control: the census is not empty and spans more than one oracle file."""
    tree = _ast_sites()
    assert sum(tree.values()) >= 30
    assert len({f for f, _c in tree}) >= 7


def test_every_ast_site_is_ledgered_and_every_ledger_row_is_live() -> None:
    tree = _ast_sites()
    ledger = Counter((r.file, r.site) for r in _ledger() if r.seen == "ast")
    unledgered, stale = _diff(tree, ledger)
    assert not unledgered, f"tolerance-shaped sites the ledger does not classify: {unledgered}"
    assert not stale, f"ledger rows the tree no longer carries: {stale}"


def test_every_text_row_is_still_in_its_file() -> None:
    for r in _ledger():
        if r.seen != "text":
            continue
        src = " ".join((REPO / r.file).read_text(encoding="utf-8").split())
        assert r.site in src, f"text row no longer in {r.file}: {r.site!r}"


def test_every_row_is_classed_and_only_a_tolerance_row_carries_an_anchor() -> None:
    rows = _ledger()
    assert {r.seen for r in rows} <= {"ast", "text"}
    unknown = sorted({r.cls for r in rows} - set(CLASSES))
    assert not unknown, f"ledger classes without a stated rule: {unknown}"
    assert {r.cls for r in rows} == set(CLASSES)
    for r in rows:
        assert bool(r.anchor) == (r.cls == "tolerance"), r


def test_the_report_names_every_tolerance_family_and_never_calls_it_exact() -> None:
    findings = _doc_findings(REPORT.read_text(encoding="utf-8"), _ledger())
    assert not findings, "\n".join(findings)


def test_the_diff_reports_a_new_site_and_a_stale_row_by_name() -> None:
    """Negative control: the comparison can fail in both directions."""
    tree = _ast_sites()
    ledger = Counter((r.file, r.site) for r in _ledger() if r.seen == "ast")
    added = tree.copy()
    key_new = ("tests/parity/test_sem_parity.py", "m.value == pytest.approx(expected, abs=0.5)")
    added[key_new] += 1
    unledgered, stale = _diff(added, ledger)
    assert unledgered == [(*key_new, 1)] and not stale
    dropped = ledger.copy()
    key = ("tests/parity/test_sem_parity.py", "m.value == pytest.approx(expected, abs=0.005)")
    assert ledger[key] == 1  # the row this control leans on is live
    dropped[key] += 1  # the ledger claims one more than the tree carries
    unledgered, stale = _diff(tree, dropped)
    assert not unledgered and stale == [(*key, 1)]


def test_the_doc_lint_reports_a_missing_phrase_and_an_exact_beside_a_family_by_name() -> None:
    """Negative control on a doctored report: absent, unphrased, and 'exact' each fail by name."""
    rows = [
        Row("f", "tolerance", "ast", "s", "family A"),
        Row("f", "tolerance", "ast", "s", "family B"),
        Row("f", "tolerance", "ast", "s", "family C"),
        Row("f", "exact", "ast", "s", ""),
    ]
    doctored = "\n".join(
        [
            f"| family A | ±0.01 | {PHRASE} |",
            "| family B | ±0.01 | agreed |",
            f"| family C | ±0.01 | {PHRASE}; ✅ exact |",
        ]
    )
    findings = _doc_findings(doctored, rows)
    assert [f.split(":")[0] for f in findings] == ["'family B'", "'family C'"]
    assert PHRASE in findings[0] and "'exact' sits beside" in findings[1]
    assert not _doc_findings(f"| family A | {PHRASE} |", rows[:1])
