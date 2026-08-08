"""/integrity wears the panel contract (Mission Ops rank 6, ADR-0298).

The Chapter-02 beat header (kicker via the spine — "Schedule Integrity" is a Chapter 02 title —
plus a complete-sentence takeaway h1 restating the ENGINE's own findings and a muted lede), the
panel-contract shells on the A/B picker / manipulation-findings table (verdict-band wash toned by
the engine's worst severity) / isolated-effect table / counterfactual read, the 'A vs B' pair
provenance chips, and the findings-drill citation-card restyle (findings_drill.js renders the
card; the embedded drill JSON script tag is untouched).

Presentation only — every figure quoted is an engine output the page already rendered verbatim,
and the takeaway lines only RESTATE engine findings (loaded-term guard territory: the audit test
below proves the gate can FAIL before trusting its clean results)."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


def _client() -> TestClient:
    """One project, three versions (folder upload — the test_drill_tables fixture): the
    Hard_File → Project5 pair produces HIGH-severity findings, a counterfactual, and a
    finding with > 4 citations (the cite-more drill link)."""
    hf = gzip.decompress((GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes())
    hfu = gzip.decompress(
        (GOLDEN / "fuse_hardfile" / "Hard_File_updated.mspdi.xml.gz").read_bytes()
    )
    p5 = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c = TestClient(create_app(SessionState()))
    for name, data in (
        ("Hard_File.mpp.xml", hf),
        ("Hard_File_updated.mpp.xml", hfu),
        ("Project5.mpp.xml", p5),
    ):
        c.post(
            "/upload",
            files={"files": (name, data, "text/xml")},
            data={"file_meta": json.dumps([{"rel": f"History/{name}", "mtime": 1}])},
        )
    return c


@pytest.fixture(scope="module")
def page() -> str:
    return _client().get("/integrity?a=0&b=2").text


def test_integrity_has_the_chapter_beat_header(page: str) -> None:
    """Takeaway h1 is a complete sentence from EXISTING engine data: the pair's finding count,
    the worst ENGINE severity, and the CPM finish movement (never an invented trend word)."""
    m = re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page)
    assert m, "no takeaway h1 on /integrity"
    takeaway = m.group(1)
    # count + severity are the engine's own (verified against the engine below)
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.engine.manipulation import detect_manipulation
    from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text

    prior = parse_mspdi_text(
        gzip.decompress(
            (GOLDEN / "fuse_hardfile" / "Hard_File.mspdi.xml.gz").read_bytes()
        ).decode(),
        source_file="Hard_File.mpp.xml",
    )
    current = parse_mspdi(GOLDEN / "project2_5" / "Project5.mspdi.xml")
    findings = detect_manipulation(
        current, prior, current_cpm=compute_cpm(current), prior_cpm=compute_cpm(prior)
    )
    assert findings, "golden Hard_File→Project5 must flag findings"
    n = len(findings)
    assert f"{n} manipulation-pattern finding{'s' if n != 1 else ''} between" in takeaway
    sevs = {str(f.severity) for f in findings}
    worst = next(s for s in ("HIGH", "MEDIUM", "LOW", "INFO") if s in sevs)
    assert f"highest severity {worst}" in takeaway
    # the finish direction comes from the two CPM finishes (the _what_changed_header wording)
    assert (
        "the computed finish moved out" in takeaway
        or "the computed finish pulled in" in takeaway
        or "the computed finish is unchanged" in takeaway
    )
    assert '<p class="page-lede">' in page
    # the chapter kicker rides _page's spine resolution ("Schedule Integrity" → Chapter 02)
    assert "CHAPTER 02" in page


def test_integrity_panels_wear_the_contract_shells(page: str) -> None:
    # A/B picker panel shell (the picker itself is unchanged — labels still render)
    assert (
        "<div class=panel-head><h2>Version pair &mdash; baseline (A) vs comparison (B)</h2>" in page
    )
    assert "Baseline (A)" in page and "Comparison (B)" in page
    # findings / effects / logic-diagram / counterfactual shells (the change-effects panel
    # carries data-export since 2026-08-08 — its ⤓ EXCEL serves the underlying change ledger)
    assert re.search(r"<div class=panel-head><h2>[^<]*&rarr;[^<]*</h2>", page)
    assert '<div class="panel change-effects" data-export=' in page
    assert "Effect of each change on" in page
    assert '<div class="panel logic-changes" data-export=' in page
    assert "Logic changes &mdash; before &rarr; after" in page
    assert '<div class="panel counterfactual"><div class=panel-head>' in page
    assert "Counterfactual — without these changes" in page
    # the 'A vs B' pair provenance chip on every shelled panel (i18n-inert)
    chips = re.findall(r"<span class=prov-chip data-no-i18n>v1→v3 · SOURCE: ", page)
    assert len(chips) == 5, f"expected 5 pair chips, found {len(chips)}"
    # the toolbar behavior script actually ships on THIS page (per-page include)
    assert "/static/panelkit.js" in page


def test_integrity_findings_panel_wears_the_verdict_wash(page: str) -> None:
    """The band tone comes from the ENGINE's own worst severity — never re-judged here."""
    # the fixture pair carries HIGH findings → --bad tone
    assert '<div class="panel verdict-band vb-stack vb-at-risk"' in page
    assert "<p class=sf-take data-no-i18n>" in page
    # the findings table and drill stay inside the band panel, untruncated
    assert "integrity-table" in page
    assert "cite-more" in page and "view all" in page
    assert "findingsDrill" in page and "/static/findings_drill.js" in page


def test_integrity_toolbar_excel_targets_are_live(page: str) -> None:
    """⤓ EXCEL only where an EXISTING endpoint serves the data — every target answers 200;
    the tables are their own data drawer, so no ▦ DATA (the /evm precedent). Since 2026-08-08
    the findings, change-effects and logic-diagram panels all export — one shared URL that
    pins the pair (a/b), so the workbook carries the underlying change ledger too."""
    assert "▦ DATA" not in page
    assert page.count("⛶ ENLARGE") == 5  # + the logic-changes diagram panel (2026-08-08)
    assert page.count("⤓ EXCEL") == 3  # findings + change-effects + logic diagram
    urls = set(re.findall(r'data-export="([^"]+)"', page))
    assert urls == {"/export/xlsx/integrity?file=Project5.mpp.xml&a=0&b=2"}
    c = _client()
    for url in urls:
        assert c.get(url).status_code == 200, url
    # the picker's Excel link is kept — now naming the ledger it carries
    assert "Excel (findings + change ledger)" in page


def test_integrity_drill_json_script_tag_is_untouched(page: str) -> None:
    """The embedded drill JSON rides the same non-executable script tag with the same shape —
    findings_drill.js's data flow is unchanged (only its rendering wears the citation card)."""
    m = re.search(r'<script type="application/json" id=findingsData>(.*?)</script>', page, re.S)
    assert m, "drill JSON script tag missing"
    payload = json.loads(m.group(1))
    assert set(payload) == {"file", "findings"}
    assert payload["findings"], "fixture pair must carry drilled findings"
    for f in payload["findings"]:
        assert set(f) == {"title", "uids"}
    # script src is cache-busted (_bust_static appends ?v=...) — match the substring
    assert '<script src="/static/findings_drill.js' in page


def test_findings_drill_js_renders_citation_cards() -> None:
    """The drill's rendering vocabulary is the shared .finding.cite-card contract, severity-toned
    by the engine's own sev-* cell (whitelisted) — and the data flow (embedded UIDs +
    /api/analysis + Excel export) is intact."""
    js = (STATIC / "findings_drill.js").read_text(encoding="utf-8")
    assert 'class: "finding cite-card"' in js
    assert "sev-(HIGH|MEDIUM|LOW|INFO)" in js  # whitelist — engine severities only
    # unchanged data flow
    assert "findingsData" in js and "/api/analysis/" in js
    assert "/export/xlsx/activities/" in js and "filterText" in js


def test_new_integrity_strings_introduce_no_loaded_terms(page: str) -> None:
    """Loaded-term audit (the /compare rank-5 law): every NEW visible sentence this round added
    must introduce no accusatory/intent term beyond the engine's own finding strings. The gate
    is proven able to FAIL first (control string) — a green audit is only trusted after red."""
    from schedule_forensics.ai.citations import introduces_loaded_terms

    # CONTROL: the gate MUST flag a bare accusation against an empty source
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True

    new_strings = [
        re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page).group(1),  # type: ignore[union-attr]
        re.search(r'<p class="page-lede">(.*?)</p>', page, re.S).group(1),  # type: ignore[union-attr]
        *re.findall(r"<p class=sf-take data-no-i18n>(.*?)</p>", page, re.S),
        "Version pair — baseline (A) vs comparison (B)",
        "Export this pair's integrity findings — opens in Excel",
        "cited activities · SOURCE:",  # the drill card's cite line (findings_drill.js)
    ]
    assert len(new_strings) >= 5
    for s in new_strings:
        assert introduces_loaded_terms("", s) is False, s
