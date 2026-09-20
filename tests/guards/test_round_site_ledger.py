"""Every builtin ``round()`` call in the package is classified by EXPOSURE, and the ledger that
classifies it is tied to the tree (R-04, ADR-0515).

R-04 named MF-08's residual — the ``round()`` sites outside ``engine/metrics`` — and asked for
them to be classified by exposure and read, family by family, against the reference tool's own
rounding rule. The reading is in ADR-0515 and the Forensic oracle
(``tests/parity/test_fuse_forensic_rounding_oracle.py``): every rule Acumen Fuse's own code
applies at a tie is half-to-even, which is what ``round()`` is. So the ledger's job is not to
drive a sweep; it is to keep the classification honest — a site that appears, moves file or is
reworded is unclassified until someone names its family here, and the report's §4 census rows
(``round_family_*``) are re-derived from this ledger by ``test_audit_report_wp8.py``.

The families and the rule each one follows:
"""

from __future__ import annotations

import ast
import csv
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "schedule_forensics"
LEDGER = Path(__file__).with_name("round_site_ledger.tsv")

#: family -> the rule it follows (the ADR's table; a family not listed here is not a family)
FAMILIES: dict[str, str] = {
    "quantize": "a real value snapped to the model's integer grid (working minutes, a sample, "
    "an offset, an index) — internal arithmetic, no displayed digit; half-even",
    "quantize_measured": "a grid snap whose rule was MEASURED against MS Project's stored "
    "dates (ADR-0474 / 0491 / 0502 / 0512) — never swept",
    "measured_field": "acumen_whole_day_float — Fuse's Total Float field, half-even on 3,637 "
    "displayed activities (ADR-0514); its callers are exempt from any sweep",
    "whole_day": "a minute quantity displayed in whole working days — Fuse's whole-day fields "
    "are half-even on every Forensic row (ADR-0515); round() IS the rule",
    "whole_pct": "a fraction displayed as a whole percent — Fuse pre-rounds its percent field "
    "in code (half-even); no tie in the corpus, consistent by construction",
    "days_dp": "a minute quantity displayed in days / hours at 1-2 dp — Fuse shows whole days "
    "and MS Project's 2-dp display rule is UNVERIFIED (no rendered export in the intake); "
    "the tool's rule is correctly-rounded half-even, the same rule Fuse's code applies to its "
    "own decimals",
    "pct_dp": "a fraction displayed as a percent at 1-2 dp — no reference display at this "
    "precision (Fuse writes raw values under Excel's General format); half-even, stated",
    "value_dp": "a ratio, cost, probability, std-dev or an already-rounded MetricResult value "
    "re-rounded at 1-4 dp — no reference display; half-even, stated (a MetricResult re-round "
    "is idempotent)",
    "tolerance": "the AI figure-derivation gate: a reconstruction at _DP compared to or "
    "explained beside the model's token — not a schedule display",
    "telemetry": "host RAM / disk / CPU / temperature on the system page — not a schedule figure",
    "geometry": "EMU, points, colour channels and CSS widths in the report writers and a bar — "
    "not a figure",
    "axis_label": "a chart axis tick label of half the maximum count",
}


def _tree_sites() -> Counter[tuple[str, str]]:
    """(file, normalized call text) of every bare ``round(`` call under the package."""
    out: Counter[tuple[str, str]] = Counter()
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(SRC).as_posix()
        for node in ast.walk(ast.parse(text)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "round"
            ):
                seg = " ".join((ast.get_source_segment(text, node) or "").split())
                out[(rel, seg)] += 1
    return out


def _ledger() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    with LEDGER.open(encoding="utf-8", newline="") as fh:
        for rec in csv.reader((ln for ln in fh if not ln.startswith("#")), delimiter="\t"):
            assert len(rec) == 3, rec
            rows.append((rec[0], rec[1], rec[2]))
    return rows


def _diff(
    tree: Counter[tuple[str, str]], ledger: Counter[tuple[str, str]]
) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]]]:
    """(unledgered, stale): sites the tree has beyond the ledger, and ledger rows the tree
    no longer carries — each with the surplus count, by name."""
    unledgered = sorted((f, c, n) for (f, c), n in (tree - ledger).items())
    stale = sorted((f, c, n) for (f, c), n in (ledger - tree).items())
    return unledgered, stale


def test_every_round_site_is_ledgered_and_every_ledger_row_is_live() -> None:
    tree = _tree_sites()
    assert sum(tree.values()) >= 300  # the walker sees the population (positive control)
    ledger = Counter((f, c) for f, _fam, c in _ledger())
    unledgered, stale = _diff(tree, ledger)
    assert not unledgered, f"round() sites the ledger does not classify: {unledgered}"
    assert not stale, f"ledger rows the tree no longer carries: {stale}"


def test_every_family_is_named_and_the_measured_ones_hold_their_sites() -> None:
    rows = _ledger()
    unknown = sorted({fam for _f, fam, _c in rows} - set(FAMILIES))
    assert not unknown, f"ledger families without a stated rule: {unknown}"
    by_fam = Counter(fam for _f, fam, _c in rows)
    assert set(by_fam) == set(FAMILIES), sorted(set(FAMILIES) - set(by_fam))
    # the measured sites are pinned by name — a re-classification is a decision, not a drift
    measured = {(f, c) for f, fam, c in rows if fam in ("measured_field", "quantize_measured")}
    assert measured == {
        ("engine/metrics/_common.py", "round(minutes / minutes_per_day)"),
        ("engine/cpm.py", "round(ratio * dur)"),
        ("engine/cpm.py", "round(share * span)"),
        ("engine/cpm.py", "round(span * minutes / duration)"),
        ("engine/cpm.py", "round(task_by_id[s].duration_minutes * (100.0 - pct) / 100.0)"),
        ("importers/mspdi.py", "round(delay_tenths / 10)"),
    }


def test_the_diff_reports_a_new_site_and_a_stale_row_by_name() -> None:
    """Negative control: the comparison can fail in both directions."""
    tree = _tree_sites()
    ledger = Counter((f, c) for f, _fam, c in _ledger())
    added = tree.copy()
    added[("web/app.py", "round(x / mpd, 1)")] += 1
    unledgered, stale = _diff(added, ledger)
    assert unledgered == [("web/app.py", "round(x / mpd, 1)", 1)] and not stale
    dropped = ledger.copy()
    key = ("engine/metrics/_common.py", "round(minutes / minutes_per_day)")
    dropped[key] += 1  # the ledger claims one more than the tree carries
    unledgered, stale = _diff(tree, dropped)
    assert not unledgered and stale == [(*key, 1)]
