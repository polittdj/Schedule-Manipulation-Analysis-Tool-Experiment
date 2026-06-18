"""Finish & Slippage curve view tests (PBIX pages 6, 7, 12; ADR-0040)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_curves_view_needs_a_schedule(client: TestClient) -> None:
    assert "Load at least one schedule" in client.get("/curves").text
    assert client.get("/api/curves").status_code == 400


def test_curves_page_renders_three_charts_for_one_version(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/curves").text
    assert "Finishes &mdash; actual vs baseline by month" in page
    assert "DATA Date Finishes" in page and "Slippage" in page
    assert "id=finishesChart" in page and "id=dataDateChart" in page and "id=slippageChart" in page
    assert "/static/curves.js" in page
    # a single version still works (the curves show that version alone)
    assert "Load more than one version" in page


def test_curves_page_drops_the_single_version_hint_with_two(client: TestClient) -> None:
    _upload(client, "Project5")
    _upload(client, "Project2")
    page = client.get("/curves").text
    assert "Load more than one version" not in page


def test_api_curves_serves_shared_axis_and_per_version_series(client: TestClient) -> None:
    _upload(client, "Project5")  # load order reversed on purpose
    _upload(client, "Project2")
    data = client.get("/api/curves").json()
    months = data["months"]
    vers = data["versions"]
    # ordered by data date (Project2 older than Project5)
    assert [v["label"] for v in vers] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    for v in vers:
        for key in ("baseline_finishes", "actual_finishes", "baseline_starts", "actual_starts"):
            assert len(v[key]) == len(months)
    # the golden completed counts surface as actual finishes (20 / 27)
    assert sum(vers[0]["actual_finishes"]) >= 20
    assert sum(vers[1]["actual_finishes"]) >= 27
    # the data-date marker lands on the shared axis for each version
    assert vers[0]["status_index"] is not None and vers[1]["status_index"] is not None


def test_curves_export_xlsx_and_docx(client: TestClient) -> None:
    _upload(client, "Project5")
    for fmt in ("xlsx", "docx"):
        resp = client.get(f"/export/{fmt}/curves")
        assert resp.status_code == 200
        assert len(resp.content) > 0
    # an unknown format degrades to 404
    assert client.get("/export/pdf/curves").status_code == 404


def test_curves_export_needs_a_schedule(client: TestClient) -> None:
    assert client.get("/export/xlsx/curves").status_code == 400


def test_nav_always_links_curves(client: TestClient) -> None:
    # the header nav links the page unconditionally (it handles the empty/one-version cases)
    assert 'href="/curves">Finish &amp; Slippage</a>' in client.get("/").text


def test_dashboard_body_links_curves_only_with_two_versions(client: TestClient) -> None:
    _upload(client, "Project2")
    # the body's multi-version action row appears only with >= 2 versions (nav link aside)
    assert "Finish &amp; slippage curves" not in client.get("/").text
    _upload(client, "Project5")
    assert "Finish &amp; slippage curves" in client.get("/").text


def test_curves_have_a_clickable_show_hide_legend(client: TestClient) -> None:
    """Item E: the Data-Date / Slippage overlaid line families get a clickable, keyboard-operable
    show/hide legend (real <button>s toggling each line) so the clutter can be decluttered."""
    js = client.get("/static/curves.js").text
    assert "buildLegend" in js and "curve-legend" in js
    assert "aria-pressed" in js  # the toggle announces state and is keyboard-operable
    assert "pl.style.display" in js  # toggling a line's visibility
    assert "Show all" in js and "Hide all" in js  # bulk controls for many-version clutter
    assert "var lx = padL" not in js  # the old static in-SVG legend is gone
    assert ".curve-legend-item" in client.get("/static/app.css").text
