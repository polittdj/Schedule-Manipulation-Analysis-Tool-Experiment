"""Interactive-visuals tests (M14) — activity/driving JSON contract + static serving."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_static_assets_are_served_locally(client: TestClient) -> None:
    js = client.get("/static/app.js")
    css = client.get("/static/app.css")
    assert js.status_code == 200 and "drill" in js.text  # the drill-into-metadata feature
    assert css.status_code == 200 and "gantt" in css.text


def test_analysis_json_has_citable_activity_rows(client: TestClient) -> None:
    data = client.get("/api/analysis/Project5").json()
    acts = data["activities"]
    normal = [a for a in acts if not a["is_summary"]]
    summaries = [a for a in acts if a["is_summary"]]
    assert len(normal) == 126  # schedulable activities (CPM-covered)
    assert len(summaries) == 19  # WBS summaries incl. the UID-0 project row (Gantt rows)
    row = next(a for a in acts if a["unique_id"] == 143)
    # the drill-down + Gantt fields the grid exposes, each verifiable against the parent file
    for key in (
        "name",
        "start",
        "finish",
        "baseline_start",
        "baseline_finish",
        "duration_days",
        "total_float_days",
        "percent_complete",
        "is_critical",
        "is_milestone",
        "is_summary",
        "resource_names",
        "source_file",
    ):
        assert key in row
    assert row["is_critical"] is True and row["source_file"] == "Project5.mspdi.xml"
    assert data["status_date"] == "2026-08-27"  # the data-date marker the Gantt draws
    assert all(s["total_float_days"] is None for s in summaries)  # no CPM float on summaries


def test_app_js_renders_the_gantt_timeline(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    assert "timelineCell" in js and "monthTicks" in js  # the MS-Project-style timeline column
    assert "g-ms" in js and "g-sum" in js and "g-crit" in js  # milestone/summary/critical bars
    css = client.get("/static/app.css").text
    assert ".g-bar" in css and ".g-status" in css


def test_driving_rows_carry_completion_and_milestone_flags(client: TestClient) -> None:
    # the trace's "show completed" toggle and milestone diamonds need these per row
    dj = client.get("/api/driving/Project5?target=143").json()
    assert all("percent_complete" in r and "is_milestone" in r for r in dj["rows"])
    # waterfall order: earliest finish first
    finishes = [r["finish_ord"] for r in dj["rows"] if r["finish_ord"] is not None]
    assert finishes == sorted(finishes)


def test_grid_filters_and_trace_toggle_are_wired(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=showDone" in page  # user chooses whether completed tasks display in the trace
    js = client.get("/static/app.js").text
    assert "rowMatches" in js and "filter-row" in js  # per-column filters (MS-Project style)
    assert "showDone" in js and "lastDriving" in js  # completed-toggle re-renders the trace


def test_driving_endpoint_returns_tiers_and_gantt_ordinals(client: TestClient) -> None:
    dj = client.get("/api/driving/Project5?target=143&secondary=10&tertiary=20").json()
    assert dj["target_uid"] == 143 and dj["rows"]
    tiers = {r["tier"]: 0 for r in dj["rows"]}
    for r in dj["rows"]:
        tiers[r["tier"]] += 1
    # matches the SSI-parity driving-path tiering (M6): 36 driving, 12 secondary, 12 tertiary
    assert tiers["DRIVING"] == 36 and tiers["SECONDARY"] == 12 and tiers["TERTIARY"] == 12
    # Gantt needs an ordinal time axis per row
    assert all("start_ord" in r and "finish_ord" in r for r in dj["rows"])
    assert client.get("/api/driving/Project5?target=999999").json()["rows"] == []
    assert client.get("/api/driving/missing?target=1").status_code == 404


def test_analysis_page_wires_the_interactive_viz(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=viz" in page and 'data-name="Project5"' in page
    assert "/static/app.js" in page and "/static/app.css" in page
    assert "id=gantt" in page and "id=grid" in page and "id=fieldToggles" in page


def test_driving_summary_target_returns_note_not_500(client: TestClient) -> None:
    # Project5 UID 0 is the project-summary row: not in the logic network. Tracing it
    # raised KeyError -> 500 (and the session-wide target auto-trace made that constant).
    r = client.get("/api/driving/Project5?target=0")
    assert r.status_code == 200
    data = r.json()
    assert data["rows"] == [] and "summary" in data["note"]


def test_driving_on_unschedulable_schedule_is_422_not_500(client: TestClient) -> None:
    cyc = (
        b"<Project xmlns='http://schemas.microsoft.com/project'>"
        b"<StartDate>2026-01-05T08:00:00</StartDate><Tasks>"
        b"<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        b"<PredecessorLink><PredecessorUID>2</PredecessorUID></PredecessorLink></Task>"
        b"<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        b"<PredecessorLink><PredecessorUID>1</PredecessorUID></PredecessorLink></Task>"
        b"</Tasks></Project>"
    )
    client.post("/upload", files={"files": ("Cycle.xml", cyc, "text/xml")})
    r = client.get("/api/driving/Cycle?target=1")
    assert r.status_code == 422  # the page-level routes already degraded; this one 500'd


def test_charts_carry_legends_descriptions_and_thinned_labels(client: TestClient) -> None:
    """Operator request: every chart has a legend + a description, and its x-axis labels are
    thinned so they never overlap (readable on many-version workbooks)."""
    trend = client.get("/static/trend.js").text
    assert "chart-desc" in trend and "chart-legend" in trend  # caption + legend on every chart
    assert "labelStep" in trend and "i % step" in trend  # x-labels thinned, not drawn every tick
    drill = client.get("/static/trend_drill.js").text
    assert "chart-desc" in drill and "chart-legend" in drill
    assert "chart-legend" in client.get("/static/drift.js").text  # forecast-drift color key
    css = client.get("/static/app.css").text
    assert ".chart-desc" in css and ".chart-legend" in css and ".chart-swatch" in css
    # the /forecast spread ruler (server-rendered SVG) carries its color-key legend inline
    page = client.get("/forecast").text
    assert "id=forecastRuler" in page and "chart-legend" in page


def test_unknown_analysis_page_is_404(client: TestClient) -> None:
    r = client.get("/analysis/NoSuchSchedule")
    assert r.status_code == 404 and "No schedule named" in r.text
