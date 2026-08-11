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
import re
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


def test_fuse_validation_marker_cannot_be_silently_deleted_f01() -> None:
    """Audit F-01 closure (ADR-0151): the §E float/critical subset flipped from engine-pinned
    self-consistency to ENGINE==FUSE against the delivered 2026-06/07 export suite. The prior
    version of this test pinned the honest *disclaimer*; this version pins the honest *upgrade*
    — the provenance markers and the two asserted divergences (the 96↔99 membership swap and
    the -148 vs -134 Net-Finish-Impact basis) may not be silently deleted from either the
    human-readable report or the golden's machine-readable caveat."""
    root = Path(__file__).resolve().parents[1]
    report = _norm((root / "docs" / "PARITY-REPORT.md").read_text(encoding="utf-8"))
    assert "ENGINE==FUSE" in report
    assert "fuse_exports_2026-06.json" in report
    assert "-148 = -134 - 15 + 1" in report  # the Net-Finish-Impact basis reconciliation
    assert "UID 99" in report and "UID 96" in report  # the SN04 membership swap disclosure

    case = json.loads(
        (root / "tests" / "fixtures" / "golden" / "project2_5" / "case.json").read_text(
            encoding="utf-8"
        )
    )
    caveat = case["_deltas"]["change_P2_to_P5_engine_pinned"]
    assert "SUPERSEDED" in caveat and "ADR-0151" in caveat
    assert "Fuse-validated (ENGINE==FUSE)" in caveat
    # the transcription file itself records the divergences it asserts
    fuse = json.loads(
        (
            root / "tests" / "fixtures" / "golden" / "project2_5" / "fuse_exports_2026-06.json"
        ).read_text(encoding="utf-8")
    )
    assert set(fuse["_documented_divergences"]) >= {
        "no_longer_critical_membership",
        "net_finish_impact_basis",
        "sn07_name_vs_basis",
    }


def test_the_parity_evidence_never_cites_a_golden_that_does_not_exist() -> None:
    """A residual or a report row may not name a golden fixture the tree no longer carries.

    ADR-0385: the SSI driving-slack entry went on describing ``ssi_uid143`` as a live gap with an
    ``xfail`` for a month after ADR-0154's replacement export retired it. The golden directory was
    gone and ``test_ssi_driving_slack_exact`` with it, while TWO exact UID-for-UID exports
    (``ssi_uid67``, ``ssi_uid145``) had taken their place and were passing in the gate — so the
    tool's own parity record UNDERSTATED its measured SSI fidelity. In a testimony context that is
    the expensive direction to be wrong in: it claims an unvalidated gap that does not exist.

    String-pinning the corrected prose would catch only this instance. The property that
    generalizes is that every golden the evidence cites BY PATH must exist on disk. A historical
    mention is fine — write it as a bare name, not as a ``tests/fixtures/golden/...`` path, because
    a path citation is an instruction to go and look.
    """
    golden_dir = REPO / "tests" / "fixtures" / "golden"
    sources = {
        "docs/PARITY-REPORT.md": REPORT.read_text(encoding="utf-8"),
        "case.json _deltas": json.dumps(json.loads(CASE.read_text(encoding="utf-8"))["_deltas"]),
    }
    cited = {
        name: sorted(set(re.findall(r"golden/([A-Za-z0-9_]+)", text)))
        for name, text in sources.items()
    }
    # positive control: an empty scan is not evidence (the regex must actually match something)
    assert any(cited.values()), f"no golden references found at all - the scan is broken: {cited}"

    missing = {
        name: [d for d in dirs if not (golden_dir / d).is_dir()] for name, dirs in cited.items()
    }
    missing = {name: dirs for name, dirs in missing.items() if dirs}
    assert not missing, (
        f"the parity evidence cites golden fixtures that do not exist: {missing}. Either the "
        "fixture was removed and the claim around it is now false (ADR-0385), or the path is a "
        "typo. Fix the claim, do not delete the guard."
    )


def test_the_ssi_driving_slack_xfail_claim_stays_retired() -> None:
    """The specific regression ADR-0385 closed: both records claimed an open SSI ``xfail``.

    Pinned in BOTH places, because both carried it and either could rot alone.
    """
    report = REPORT.read_text(encoding="utf-8")
    caveat = json.loads(CASE.read_text(encoding="utf-8"))["_deltas"]["ssi_driving_slack_golden"]
    for where, text in (("PARITY-REPORT.md", report), ("case.json caveat", caveat)):
        assert "ssi_uid67" in text, f"{where} does not record the UID-67 Directional Path oracle"
        assert "ssi_uid145" in text, f"{where} does not record the UID-145 oracle"
    assert "CLOSED" in caveat, "the caveat must state the gap is closed"
    assert "stale, `xfail`" not in report, "the retired SSI xfail row is back in the report"
