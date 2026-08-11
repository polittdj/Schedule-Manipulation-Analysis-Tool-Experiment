"""Docs closeout (M17) — metric-dictionary doc stays in sync; the report set is present."""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.web.help import render_dictionary_markdown

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_metric_dictionary_doc_is_in_sync() -> None:
    # docs/METRIC-DICTIONARY.md is generated from web.help — they must not drift.
    committed = (DOCS / "METRIC-DICTIONARY.md").read_text()
    assert committed == render_dictionary_markdown(), (
        "docs/METRIC-DICTIONARY.md is stale — regenerate: "
        'python -c "from schedule_forensics.web.help import render_dictionary_markdown as r; '
        "open('docs/METRIC-DICTIONARY.md','w').write(r())\""
    )


def test_closing_docs_exist_and_are_substantive() -> None:
    for name in ("USER-GUIDE.md", "PARITY-REPORT.md", "FINAL-REPORT.md", "METRIC-DICTIONARY.md"):
        text = (DOCS / name).read_text()
        assert len(text) > 400, f"{name} looks empty/stub"


def test_final_report_maps_every_requirement_group() -> None:
    report = (DOCS / "FINAL-REPORT.md").read_text()
    for section in ("§6.A", "§6.B", "§6.C", "§6.D", "§6.E", "§6.F", "§6.G"):
        assert section in report
    assert "BLOCKED" in report and "M15" in report  # the one externally-gated item is flagged


def test_parity_report_states_the_headline_results() -> None:
    parity = (DOCS / "PARITY-REPORT.md").read_text()
    # SSI per-UniqueID coverage + the headline slip. REPOINTED (ADR-0385): this asserted "107",
    # a number that appeared ONLY in the retired `ssi_uid143` row — so the guard was pinning the
    # stale claim in place, and correcting the report read as a regression. The live oracles are
    # `ssi_uid145` (108 UniqueIDs, all-dependencies) and `ssi_uid67` (the 20-task Path-01 set).
    assert "108 UIDs" in parity and "Net Finish Impact" in parity  # not bare "108": ADR-0108
    assert "ssi_uid67" in parity and "ssi_uid145" in parity  # both live oracles named, not one
    assert "NOT_APPLICABLE" in parity  # cost EVM honestly NA, not fabricated
