"""The Assessment Scorecards page (issue #331): NASA STAT / GAO-10 / SRA-readiness + reserve card.

Pins the web wiring — the page renders the three ribbons and the reserve card, the reserve API runs
the on-demand SRA and returns sensible JSON, the exports serialize, and the page is reachable from
the chapter-02 navigation. The engine numbers themselves are pinned in tests/engine/test_scorecards.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    xml = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", xml, "text/xml")})
    return c


def test_page_renders_the_three_scorecards_and_reserve_card(client: TestClient) -> None:
    t = client.get("/scorecards").text
    for needle in (
        "NASA STAT",
        "GAO 10 Best Practices",
        "SRA-Readiness Gate",
        "Reserve / buffer sizing",
        "/static/scorecards.js",
        'class="page-takeaway"',
    ):
        assert needle in t, needle


def test_empty_session_prompts_to_load(client: TestClient) -> None:
    c = TestClient(create_app(SessionState()))
    t = c.get("/scorecards").text
    assert "Load a schedule" in t


def test_reserve_api_runs_the_sra_and_returns_sizing(client: TestClient) -> None:
    r = client.get(
        "/api/scorecards/buffer",
        params={"committed": "2028-06-01", "iterations": 200},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["iterations"] == 200
    assert 0.0 <= body["committed_confidence"] <= 1.0
    assert body["committed_date"] == "2028-06-01"
    # four confidence rows, each with a finish date + a non-negative reserve
    pcts = [row["percentile"] for row in body["rows"]]
    assert pcts == [50, 70, 80, 90]
    for row in body["rows"]:
        assert row["reserve_days"] >= 0.0
        assert row["finish_date"]


def test_reserve_api_requires_a_committed_date(client: TestClient) -> None:
    r = client.get("/api/scorecards/buffer", params={"committed": ""})
    assert r.status_code == 422


def test_scorecards_export_serializes(client: TestClient) -> None:
    for fmt in ("xlsx", "docx"):
        r = client.get(f"/export/{fmt}/scorecards")
        assert r.status_code == 200
        assert len(r.content) > 0
    assert client.get("/export/csv/scorecards").status_code == 404


def test_scorecards_is_reachable_from_chapter_two(client: TestClient) -> None:
    """The page is a chapter-02 secondary ('Can we trust the plan?'), so its link is on /ribbon."""
    assert "/scorecards" in client.get("/ribbon").text


# ── Mission Ops rank 8: panel shells on the scorecard visuals ────────────────────────────────


def test_scorecard_panels_wear_the_contract(client: TestClient) -> None:
    """Each scorecard panel gets the headline strip + ⤓/⛶ tools + prov chip + sf-take (the
    existing engine figures, verbatim); ⤓ EXCEL rides the EXISTING /export/xlsx/scorecards
    endpoint for the assessed version; ▦ DATA omitted (the table IS the data)."""
    page = client.get("/scorecards").text
    for name in ("NASA STAT", "GAO 10 Best Practices", "SRA-Readiness Gate"):
        assert f"<div class=panel-head><h2>{name}</h2>" in page, name
    assert page.count('data-export="/export/xlsx/scorecards?file=') == 3
    assert "data-sf-excel" in page and "data-sf-big" in page
    assert "data-sf-data" not in page  # the tables ARE the data — no ▦ DATA anywhere
    takes = re.findall(r"<p class=sf-take data-no-i18n><b>(.*?)</b>", page)
    assert len(takes) == 3
    for score in takes:  # the engine's own score line, verbatim (pinned in tests/engine)
        assert re.fullmatch(r"\d+/\d+ scored checks pass|no scored checks", score), score
    # the assessed version's provenance chip on all three cards + the reserve panel
    chips = re.findall(r"<span class=prov-chip data-no-i18n>(SOURCE: [^<]*· DD [^<]*)</span>", page)
    assert len(chips) == 4 and len(set(chips)) == 1
    # PER-PAGE include, cache-busted src (?v=…) → substring match, never the exact tag
    assert 'src="/static/panelkit.js' in page
    # and the ⤓ target is a live endpoint, never a dead link
    assert client.get("/export/xlsx/scorecards").status_code == 200


def test_reserve_panel_shell_has_no_excel_glyph(client: TestClient) -> None:
    """No existing endpoint serves the on-demand reserve card, so its tools are ⛶ only."""
    page = client.get("/scorecards").text
    assert "<div class=panel-head><h2>Reserve / buffer sizing</h2>" in page
    reserve = page.split("<div class=panel-head><h2>Reserve / buffer sizing</h2>", 1)[1]
    head = reserve.split("</div>", 1)[0]
    assert "data-sf-big" in head and "data-sf-excel" not in head
    # the reserve form itself is untouched (field ids + on-demand API wiring)
    assert "reserveForm" in reserve and "reserveDate" in reserve and "reserveRun" in reserve


def test_scorecards_page_has_the_chapter_lede(client: TestClient) -> None:
    page = client.get("/scorecards").text
    assert '<p class="page-lede">' in page
    assert "Three published assessment frameworks scored on the chosen version" in page


def test_new_strings_never_introduce_loaded_terms(client: TestClient) -> None:
    from schedule_forensics.ai.citations import introduces_loaded_terms

    # CONTROL: the gate MUST flag a bare accusation against an empty source
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True

    page = client.get("/scorecards").text
    lede = re.search(r'<p class="page-lede">(.*?)</p>', page, re.S)
    assert lede is not None
    new_strings = [
        lede.group(1),
        *re.findall(r"<p class=sf-take data-no-i18n>(.*?)</p>", page, re.S),
        "Export the three assessment scorecards for this version — opens in Excel",
    ]
    assert len(new_strings) >= 5
    for s in new_strings:
        assert introduces_loaded_terms("", s) is False, s


def test_scorecards_js_is_vendored_and_air_gap_safe() -> None:
    js = (STATIC / "scorecards.js").read_text(encoding="utf-8")
    assert "/api/scorecards/buffer" in js
    # local fetch only — no remote origin, matching the air-gap (Law 1)
    assert "http://" not in js and "https://" not in js
