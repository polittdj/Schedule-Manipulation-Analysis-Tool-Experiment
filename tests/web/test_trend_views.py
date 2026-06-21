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
    for key in (
        "float_total_0",
        "float_total_lt5",
        "float_total_lt10",
        "float_free_0",
        "float_free_lt5",
        "float_free_lt10",
    ):
        assert key in fb and "count" in fb[key] and "pct" in fb[key]
    # critical count from bands matches the trend headline (total-float-0 = critical)
    assert fb["float_total_0"]["count"] == v5["critical"]


def test_api_trend_quality_carries_per_version_offenders(client: TestClient) -> None:
    """M18 item 8 — each §A metric carries per-version offender activities (uid + name)."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/trend").json()
    crit = data["quality"]["critical"]
    assert crit["lower_is_better"] is True
    assert crit["counts"] == [41, 37]  # full offender counts per version
    assert len(crit["offenders"][0]) == 41 and len(crit["offenders"][1]) == 37
    assert all("uid" in o and "name" in o for o in crit["offenders"][0])
    # a neutral ratio has no offenders and is flagged so the drill-down can say so
    ld = data["quality"]["logic_density"]
    assert ld["lower_is_better"] is None
    assert ld["offenders"] == [[], []]


def test_trend_page_has_quality_drilldown_and_animation_panel(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/trend").text
    assert "Quality drill-down" in page and "locked axis" in page
    for ctl in (
        "id=qualMetric",
        "id=qualPrev",
        "id=qualNext",
        "id=qualPlay",
        "id=qualBars",
        "id=qualDrill",
    ):
        assert ctl in page, ctl
    assert "/static/trend_drill.js" in page


def test_trend_js_has_combined_execution_index_chart(client: TestClient) -> None:
    """Handbook Fig. 7-21: the BEI/CEI/HMI execution indices are overlaid on one combined chart
    (the data — bei / cei_tasks / hmi_tasks — is already in the /api/trend payload per version)."""
    js = client.get("/static/trend.js").text
    assert "are we executing the plan?" in js
    for key in ("bei", "cei_tasks", "hmi_tasks"):
        assert key in js, key
    # the combined chart reads the same per-version indices the payload already serves
    _upload(client, "Project2")
    _upload(client, "Project5")
    indices = client.get("/api/trend").json()["versions"][1]["indices"]
    assert "bei" in indices and "cei_tasks" in indices and "hmi_tasks" in indices


def test_trend_carries_svt_and_js_has_variance_trend(client: TestClient) -> None:
    """Handbook Figs 7-12/7-13: a zero-baselined SVt (ES - AT, working days) trend across versions.
    The /api/trend payload carries per-version svt_days; trend.js renders the variance chart."""
    js = client.get("/static/trend.js").text
    assert "varianceTrendChart" in js
    assert "Schedule variance (SVt) across versions" in js
    assert "Ahead (favorable)" in js and "Behind (unfavorable)" in js
    _upload(client, "Project2")
    _upload(client, "Project5")
    versions = client.get("/api/trend").json()["versions"]
    for v in versions:
        assert "svt_days" in v  # present (may be None when ES is undefined for that version)


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
