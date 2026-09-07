"""WP8 (ADR-0472): the consolidated audit report and repair roadmap are pinned to the tree.

A report is testimony about the code, and this repo's own history is that prose drifts behind the
thing it describes (a handoff five slices stale, an ADR whose diagnosis was wrong, a FINAL-REPORT
that called a blocked milestone delivered). So the WP8 report carries three machine-readable
surfaces and this module re-derives each of them from the tree on every run:

1. **Coverage** — every row id the campaign ledger (`docs/STATE/AUDIT-2026-08-27.md`) carries
   appears in the report's register. A row the ledger knows and the report forgot is a hole in
   the testimony record.
2. **Pricing** — every roadmap row is priced (S/M/L) or owned (ASK/ORG/HELD/CLOSED-WP8) and
   names its first executable step or its settling observation. An open item without a first
   step is an opinion.
3. **Census** — the figures the report states about the tree (the `round()` call sites outside
   `engine/metrics`, the expression-string waits, the fetch-catch modules, …) are RECOMPUTED here
   by the stated method and must match. A census the report cannot re-derive is a number of
   unknown provenance — the exact defect this campaign found in the ledger's own `176`.

Red-first (2026-09-07): the report did not exist (every test red at the first assertion); then a
mutated census value and a dropped row id each went red by name.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs" / "STATE" / "AUDIT-2026-08-27.md"
REPORT = REPO / "docs" / "STATE" / "AUDIT-2026-08-27-REPORT.md"
SRC = REPO / "src" / "schedule_forensics"

#: a ledger/report row id: `CPM-01`, `M3-01`, `TX-03`, `WP5-A`, `S1`, `OBS`, …
ROW_ID = re.compile(r"\b([A-Z]{1,4}\d?-\d{2}[a-z]?|WP5-[ABG]|S[1-5]|OBS)\b")
PRICES = {"S", "M", "L", "S-M", "M-L"}
STATUSES = {"OPEN", "ASK", "ORG", "HELD", "CLOSED-WP8", "CLOSED"}


def _ledger_ids() -> set[str]:
    """Every row id in the ledger's tables — the FIRST cell of a table row, bold or not."""
    ids: set[str] = set()
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        first = line.split("|")[1]
        ids.update(ROW_ID.findall(first))
    return ids


def _report() -> str:
    assert REPORT.exists(), f"{REPORT.relative_to(REPO)} is missing — WP8 has not landed"
    text = REPORT.read_text(encoding="utf-8")
    assert len(text) > 20_000, "the WP8 report is a stub"
    return text


def _table(text: str, heading_marker: str) -> list[list[str]]:
    """The rows of the first markdown table under the heading containing ``heading_marker``."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("#") and heading_marker in ln]
    assert starts, f"no heading containing {heading_marker!r}"
    rows: list[list[str]] = []
    seen_table = False
    for ln in lines[starts[0] + 1 :]:
        if ln.startswith("#"):
            break
        if ln.startswith("|"):
            seen_table = True
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # the separator row
            rows.append(cells)
        elif seen_table and ln.strip() == "":
            break
    assert len(rows) > 1, f"no table under {heading_marker!r}"
    return rows[1:]  # drop the header row


# ── 1. coverage ───────────────────────────────────────────────────────────────────────────────


def test_the_ledger_carries_row_ids_the_regex_can_see() -> None:
    """Positive control for the coverage census: the extractor must find the campaign's rows."""
    ids = _ledger_ids()
    for known in ("CPM-01", "TX-03", "M3-01", "M4-01", "S5", "RC-02", "CF-01", "OBS"):
        assert known in ids, known
    assert len(ids) >= 70, len(ids)


def test_every_ledger_row_id_appears_in_the_report() -> None:
    report = _report()
    missing = sorted(i for i in _ledger_ids() if not re.search(rf"\b{re.escape(i)}\b", report))
    assert not missing, f"ledger rows the report does not register: {missing}"


# ── 2. pricing ────────────────────────────────────────────────────────────────────────────────


def test_every_roadmap_row_is_priced_or_owned_and_names_its_first_step() -> None:
    rows = _table(_report(), "The repair roadmap")
    assert len(rows) >= 30, len(rows)
    for cells in rows:
        assert len(cells) >= 7, cells
        ref, tier, _rows, status, price, step, settles = cells[:7]
        assert re.fullmatch(r"R-\d{2}", ref), ref
        assert re.fullmatch(r"T[1-6]", tier), (ref, tier)
        assert status in STATUSES, (ref, status)
        if status == "OPEN":
            assert price in PRICES, (ref, price)
        else:
            assert price in PRICES | {"—"}, (ref, price)
        assert len(step) >= 20, (ref, "no first step")
        if status in {"OPEN", "ASK", "ORG", "HELD"}:  # a closed row needs no settling observation
            assert len(settles) >= 8, (ref, "nothing settles it")


def test_the_roadmap_is_ordered_by_testimony_tier() -> None:
    rows = _table(_report(), "The repair roadmap")
    tiers = [int(cells[1][1]) for cells in rows]
    assert tiers == sorted(tiers), "a lower-risk row sits above a higher-risk one"


# ── 3. census ─────────────────────────────────────────────────────────────────────────────────


def _round_calls(inside_metrics: bool) -> int:
    n = 0
    for path in SRC.rglob("*.py"):
        if ("engine/metrics" in path.as_posix()) != inside_metrics:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        n += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "round"
        )
    return n


def _expression_string_waits() -> int:
    """`wait_for_function(` sites under tests/ whose literal predicate is not a FUNCTION string."""
    n = 0
    fn = re.compile(r"^\s*(\(?\s*[\w, ]*\)?\s*=>|function\b)")
    for path in (REPO / "tests").rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        for m in re.finditer(r"wait_for_function\(\s*f?[\"']", src):
            literal = src[m.end() :].lstrip()
            if not fn.match(literal):
                n += 1
    return n


def _census_from_tree() -> dict[str, int]:
    static = SRC / "web" / "static"
    return {
        "round_calls_outside_engine_metrics": _round_calls(False),
        "round_calls_inside_engine_metrics": _round_calls(True),
        "wait_for_function_expression_strings": _expression_string_waits(),
        "fetch_catch_failed_to_load_modules": sum(
            1 for p in static.glob("*.js") if "Failed to load the" in p.read_text(encoding="utf-8")
        ),
        "evm_acwp_or_zero_sites": (SRC / "engine" / "metrics" / "evm.py")
        .read_text(encoding="utf-8")
        .count("actual_cost or 0.0"),
        "dcma14_parity_round_sites": (SRC / "engine" / "metrics" / "dcma14.py")
        .read_text(encoding="utf-8")
        .count("round("),
        "license_placeholder": int(
            "PLACEHOLDER" in (REPO / "LICENSE").read_text(encoding="utf-8").splitlines()[0]
        ),
        # this module names the literal it censuses — exclude itself, or the census self-matches
        # (the `pgrep -f` trap the render-verify skill records, in a new coat)
        "chromium_build_path_pins_in_tests": sum(
            1
            for p in (REPO / "tests").rglob("*.py")
            if p.resolve() != Path(__file__).resolve()
            and "/chromium-1194/" in p.read_text(encoding="utf-8")
        ),
        "final_report_headline_unqualified": int(
            "COMPLETE and parity-green"
            in (REPO / "docs" / "FINAL-REPORT.md").read_text(encoding="utf-8")
        ),
    }


def _census_from_report() -> dict[str, int]:
    rows = _table(_report(), "Census")
    out: dict[str, int] = {}
    for cells in rows:
        key = cells[0].strip("`")
        assert key not in out, f"duplicate census key {key}"
        out[key] = int(cells[1].replace(",", ""))
    return out


def test_the_reports_census_is_the_trees() -> None:
    stated, measured = _census_from_report(), _census_from_tree()
    unknown = sorted(set(stated) - set(measured))
    assert not unknown, f"the report states figures this guard cannot re-derive: {unknown}"
    unstated = sorted(set(measured) - set(stated))
    assert not unstated, f"the guard measures figures the report does not state: {unstated}"
    drift = {k: (stated[k], measured[k]) for k in measured if stated[k] != measured[k]}
    assert not drift, f"report says / tree measures: {drift}"


@pytest.mark.parametrize(
    "key", ["round_calls_outside_engine_metrics", "wait_for_function_expression_strings"]
)
def test_the_census_instruments_can_see(key: str) -> None:
    """Positive controls: the AST walker sees `round(` in a known file; the wait scanner sees a
    function string as a function and an expression as an expression."""
    if key.startswith("round"):
        assert _round_calls(True) > 0 and _round_calls(False) > 0
    else:
        fn = re.compile(r"^\s*(\(?\s*[\w, ]*\)?\s*=>|function\b)")
        assert fn.match("() => document.title") and fn.match("(q) => q > 1")
        assert not fn.match("document.title === 'x'")


# ── the ledger's own WP8 section ──────────────────────────────────────────────────────────────


def test_the_ledger_points_at_the_report_and_no_longer_says_pending() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    m = re.search(r"^### WP8 — .*$", text, re.M)
    assert m, "the ledger has no WP8 heading"
    assert "PENDING" not in m.group(0), m.group(0)
    assert "AUDIT-2026-08-27-REPORT.md" in text
