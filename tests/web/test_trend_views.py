"""Trend + Executive Briefing view tests — multi-version analysis over the goldens."""

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


def test_trend_view_needs_two_versions(client: TestClient) -> None:
    assert "at least two analyzable versions" in client.get("/trend").text
    _upload(client, "Project5")
    assert "at least two analyzable versions" in client.get("/trend").text
    assert client.get("/api/trend").status_code == 400


def test_trend_view_orders_by_data_date_and_shows_quality_trends(client: TestClient) -> None:
    _upload(client, "Project5")  # newer data date loaded FIRST — must still sort oldest-first
    _upload(client, "Project2")
    page = client.get("/trend").text
    assert "2 versions, oldest first" in page
    assert page.index("Project2.mspdi.xml") < page.index("Project5.mspdi.xml")
    assert "Net Finish Impact across the series" in page and "-99 calendar days" in page
    assert "Critical: decreases over time" in page  # quality-trend sentence (41 -> 37)
    assert "Hard Constraints: remains constant over time." in page
    assert "id=trendCharts" in page and "/static/trend.js" in page
    assert "honest progress" in page  # clean golden pair -> no manipulation signals


def test_api_trend_serves_chart_series(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/trend").json()
    assert [v["label"] for v in data["versions"]] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    assert data["versions"][0]["completed"] == 20 and data["versions"][1]["completed"] == 27
    assert data["versions"][0]["critical"] == 41 and data["versions"][1]["critical"] == 37
    assert data["quality"]["missing_logic"]["values"] == [6.0, 6.0]
    assert data["versions"][1]["finish"] > data["versions"][0]["finish"]  # the slip is visible


def test_api_trend_carries_cross_file_and_float_data(client: TestClient) -> None:
    """PBIX p4+p5 — per-version makeup/indices/float fields (ADR-0039)."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/trend").json()
    v2, v5 = data["versions"][0], data["versions"][1]

    # PBIX p4 — activity makeup
    assert "makeup" in v2 and "normal" in v2["makeup"] and "milestones" in v2["makeup"]
    assert v5["makeup"]["normal"] == 126  # golden count

    # PBIX p4 — status split (must sum to non-summary total)
    sp = v5["status_split"]
    assert sp["complete"] + sp["in_progress"] + sp["planned"] == v5["makeup"]["normal"]

    # PBIX p4 — completion performance (ahead/on/behind)
    cp = v5["completion_perf"]
    assert "ahead" in cp and "on_schedule" in cp and "behind" in cp
    assert cp["ahead"] + cp["on_schedule"] + cp["behind"] <= v5["completed"]

    # PBIX p4 — indices: MEI/BEI/EPI/SFR are present (may be None if population=0)
    idx = v5["indices"]
    assert "mei" in idx and "bei" in idx and "epi" in idx and "sfr" in idx

    # PBIX p5 — float sums: total >= free (free is the tighter constraint)
    fs = v5["float_sums"]
    assert "total_days" in fs and "free_days" in fs
    assert fs["total_days"] >= fs["free_days"]

    # PBIX p5 — float bands: all six keys present with count + pct
    fb = v5["float_bands"]
    for key in ("float_total_0", "float_total_lt5", "float_total_lt10",
                "float_free_0", "float_free_lt5", "float_free_lt10"):
        assert key in fb and "count" in fb[key] and "pct" in fb[key]
    # critical count from bands matches the trend headline (total-float-0 = critical)
    assert fb["float_total_0"]["count"] == v5["critical"]


def test_briefing_view_renders_cited_executive_summary(client: TestClient) -> None:
    assert "Load at least one analyzable schedule" in client.get("/briefing").text
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/briefing").text
    assert "Diagnostic Executive Briefing" in page
    assert "Workbook Summary" in page and "Trend Analysis" in page
    assert "126 normal activities" in page  # golden project summary counts
    assert "20 (15.9%) are complete" in page
    assert "Schedule Quality Analysis" in page
    assert "UID" in page  # citation tags rendered with every statement


def test_briefing_single_version_works_without_trend(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/briefing").text
    assert "Workbook Summary" in page and "Trend Analysis" not in page
    assert "27 (21.4%) are complete" in page


def test_dashboard_links_trend_and_briefing(client: TestClient) -> None:
    _upload(client, "Project2")
    home = client.get("/").text
    assert 'href="/briefing"' in home
    _upload(client, "Project5")
    home = client.get("/").text
    assert 'href="/trend"' in home and 'href="/compare"' in home
