"""Guard against ``docs/PARITY-REPORT.md`` drifting behind the authoritative golden.

The parity report is the human-readable summary a reader (incl. a testimony reader) cites. The
audit (audit/AUDIT-REPORT.md F-03) found it had gone stale behind the ADR-0112 Project5 refresh -
it still showed Critical 41/37, High-Float 43/40, Net Impact -99 while the gate's ``case.json`` had
4, 44/44, -148. This test pins the report's headline numbers to ``case.json`` so the same drift
fails loudly next time (the ``METRIC-DICTIONARY.md``-from-``help.py`` pattern, applied to parity).

Minus signs are normalized (the doc uses U+2212 MINUS SIGN; JSON uses ASCII hyphen).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CASE = REPO / "tests" / "fixtures" / "golden" / "project2_5" / "case.json"
REPORT = REPO / "docs" / "PARITY-REPORT.md"


def _norm(text: str) -> str:
    return text.replace(chr(0x2212), "-")  # U+2212 MINUS SIGN -> ASCII hyphen


def test_parity_report_reflects_current_case_json() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    report = _norm(REPORT.read_text(encoding="utf-8"))
    p2, p5, chg = case["Project2"], case["Project5"], case["change_P2_to_P5"]

    # §A Schedule-Quality — the headline that went stale (P5 critical 37 -> 4)
    assert f"41 / {p5['schedule_quality']['critical']}" in report  # Critical 41 / 4
    assert (
        f"{p2['schedule_quality']['logic_density']} / {p5['schedule_quality']['logic_density']}"
        in report
    )  # Logic Density 2.79 / 2.81

    # §B DCMA-06 High Float — former -1 residual now exact both projects
    assert f"{p2['dcma14']['DCMA06']} / {p5['dcma14']['DCMA06']}" in report  # 44 / 44

    # §C Baseline-Start-Compliance — former residual closed
    assert (
        f"{p2['baseline_compliance']['baseline_start_compliance_pct']}% / "
        f"{p5['baseline_compliance']['baseline_start_compliance_pct']}%" in report
    )  # 41% / 25%

    # §E change metrics — the authoritative pairing (Net Impact -148, not the old -99)
    assert str(chg["net_finish_impact_days"]) in report  # -148
    assert str(chg["no_longer_critical"]) in report  # 34
    assert str(chg["finish_date_slips"]) in report  # 9

    # the specific stale strings this fix removed must not reappear
    for stale in ("41 / 37", "43 / 40", "38% / 23%", "**-99**"):
        assert stale not in report, f"stale parity figure resurfaced in PARITY-REPORT.md: {stale!r}"
