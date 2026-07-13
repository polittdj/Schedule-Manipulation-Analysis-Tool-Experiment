"""The Assessment Scorecards page (issue #331): NASA STAT / GAO-10 / SRA-readiness + reserve card.

Pins the web wiring — the page renders the three ribbons and the reserve card, the reserve API runs
the on-demand SRA and returns sensible JSON, the exports serialize, and the page is reachable from
the chapter-02 navigation. The engine numbers themselves are pinned in tests/engine/test_scorecards.
"""

from __future__ import annotations

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


def test_scorecards_js_is_vendored_and_air_gap_safe() -> None:
    js = (STATIC / "scorecards.js").read_text(encoding="utf-8")
    assert "/api/scorecards/buffer" in js
    # local fetch only — no remote origin, matching the air-gap (Law 1)
    assert "http://" not in js and "https://" not in js
