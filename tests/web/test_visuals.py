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


def test_analysis_gantts_use_the_scalable_px_per_day_model(client: TestClient) -> None:
    """Bug fix: the /analysis driving-path trace + activity Gantt no longer squeeze the whole
    span into a fixed-width column (% of span). Both now use the /path px-per-day + horizontal
    scroll model — a user-adjustable zoom (pixels/day) and a scroll container."""
    js = client.get("/static/app.js").text
    # the scalable axis helpers (mirrors path.js) replace the old %-of-span math
    assert "pxPerDay" in js and "buildAxis" in js
    assert "gantt-scroll" in js  # the trace rows share one horizontal scroller
    # the squeeze is gone: no "% of span" positioning remains
    assert "/ span) * 100" not in js
    assert "pct(range" not in js and "function pct(" not in js
    # the page exposes the adjustable scale + the tier filter the operator asked for
    page = client.get("/analysis/Project5").text
    assert "id=vizZoom" in page  # pixels-per-day zoom (adjustable time scale)
    assert "id=ganttTier" in page  # Primary/Secondary/Tertiary tier filter on the trace
    css = client.get("/static/app.css").text
    assert ".gantt-scroll" in css and "#grid { overflow-x" in css  # horizontal scroll, both


def test_full_task_names_wrap_on_both_path_and_analysis(client: TestClient) -> None:
    """Operator request (item C): the Name column wraps to its FULL text on /path and the
    /analysis grid, instead of truncating (path.js sliced trace names to 22 chars before)."""
    path_js = client.get("/static/path.js").text
    assert "pv-name" in path_js  # the /path Name cell wraps
    assert ".path-grid td.pv-name" in client.get("/static/app.css").text
    app_js = client.get("/static/app.js").text
    assert "name-cell" in app_js  # the /analysis grid Name cell wraps
    assert ".slice(0, 22)" not in app_js  # the trace no longer truncates the task name
    assert "td.name-cell" in client.get("/static/app.css").text


def test_msproject_checklist_filters_replace_substring_and_tier_selects(client: TestClient) -> None:
    """Item B: MS-Project-style dropdown checklist filters (select-all / clear / search the
    distinct values) replace the grid's substring inputs and the single-tier <select>s."""
    cl = client.get("/static/checklist.js")
    assert cl.status_code == 200
    assert "window.SFChecklist" in cl.text and "function filter" in cl.text
    assert "sf-filter-search" in cl.text  # the in-dropdown search box
    assert ">All<" in cl.text or "All" in cl.text  # select-all / clear links
    # loaded once via the page shell so both the grid and the path tier reuse it
    assert "/static/checklist.js" in client.get("/analysis/Project5").text
    assert "/static/checklist.js" in client.get("/path").text

    app_js = client.get("/static/app.js").text
    assert "SFChecklist.filter" in app_js and "distinctValues" in app_js
    assert 'placeholder: "filter' not in app_js  # the old substring filter input is gone
    path_js = client.get("/static/path.js").text
    assert "SFChecklist.filter" in path_js
    assert '$("pathTier").value' not in path_js  # the old single-select tier read is gone

    # the tier controls are now checklist mount points, not <select>s
    analysis = client.get("/analysis/Project5").text
    assert "id=ganttTier" in analysis and "<select id=ganttTier" not in analysis
    path = client.get("/path").text
    assert "id=pathTier" in path and "<select id=pathTier" not in path
    assert ".sf-filter-pop" in client.get("/static/app.css").text


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


def test_dcma_audit_table_shows_count_percent_and_tooltip(client: TestClient) -> None:
    """Operator request: the DCMA-14 audit must show each metric's COUNT and PERCENTAGE (as
    Acumen Fuse does), not just a pass/fail colour, and a hover/focus tooltip must explain the
    metric, its pass/fail criteria, why it matters, and what it indicates."""
    page = client.get("/analysis/Project5").text
    # count + percentage columns (replacing the bare "Value" column)
    assert "<th scope=col>Count</th>" in page
    assert "<th scope=col>% of tasks</th>" in page
    assert "class=num" in page  # numeric count/percent cells
    assert " of " in page and "%" in page  # "n of population" + a percentage
    # the keyboard-operable, labelled tooltip per check
    assert "dcma-metric" in page and "role=tooltip" in page and "aria-describedby" in page
    # the four tooltip facets the operator asked for
    assert "Pass criteria:" in page
    assert "Why it matters:" in page
    assert "Indicates:" in page
    css = client.get("/static/app.css").text
    assert ".dcma-tip" in css and "td.num" in css


def test_dcma_metric_docs_carry_importance_and_indication() -> None:
    """Every DCMA-14 check now documents why it matters and what a failing value indicates."""
    from schedule_forensics.web.help import METRIC_DICTIONARY

    dcma_ids = [m for m in METRIC_DICTIONARY if m.startswith("DCMA")]
    assert len(dcma_ids) >= 14
    for mid in dcma_ids:
        doc = METRIC_DICTIONARY[mid]
        assert doc.importance, f"{mid} missing importance"
        assert doc.indicates, f"{mid} missing indication"


def test_driving_endpoint_returns_tiers_and_gantt_ordinals(client: TestClient) -> None:
    dj = client.get("/api/driving/Project5?target=143&secondary=10&tertiary=20").json()
    assert dj["target_uid"] == 143 and dj["rows"]
    tiers = {r["tier"]: 0 for r in dj["rows"]}
    for r in dj["rows"]:
        tiers[r["tier"]] += 1
    # driving-path tiering on the authoritative file (ADR-0112): 3 driving, 0 secondary, 8 tertiary
    # (the corridor collapsed vs the prior 37-critical golden)
    assert tiers["DRIVING"] == 3 and tiers.get("SECONDARY", 0) == 0 and tiers["TERTIARY"] == 8
    # Gantt needs an ordinal time axis per row
    assert all("start_ord" in r and "finish_ord" in r for r in dj["rows"])
    assert client.get("/api/driving/Project5?target=999999").json()["rows"] == []
    assert client.get("/api/driving/missing?target=1").status_code == 404


def test_analysis_page_wires_the_interactive_viz(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=viz" in page and 'data-name="Project5"' in page
    assert "/static/app.js" in page and "/static/app.css" in page
    assert "id=gantt" in page and "id=grid" in page and "id=fieldToggles" in page


def test_dcma_table_defines_each_check_inline(client: TestClient) -> None:
    """Operator request: each DCMA 1-14 score on the Interactive Analysis page states what the
    check is and how it is measured (sourced from the in-tool metric dictionary)."""
    page = client.get("/analysis/Project5").text
    assert "What it measures (how)" in page  # the new column
    # DCMA-01 (Logic) definition + its "how" formula are surfaced in place
    assert "missing a predecessor and/or successor" in page
    assert "How:" in page and "incomplete" in page
    # the panel points at the full Metric Dictionary for the formulas + citations
    assert 'href="/help"' in page


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


def test_chart_frame_fullscreen_zoom_and_readable_labels() -> None:
    """Operator request: every chart can go full screen and zoom in/out, version labels do
    not overlap (data-date-primary), and the forecast-drift date scale is meaningful."""
    c = TestClient(create_app(SessionState()))
    for fn in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        c.post(
            "/upload",
            files={"files": (fn, (GOLDEN / "project2_5" / fn).read_bytes(), "text/xml")},
        )

    cf = c.get("/static/chartframe.js")
    assert cf.status_code == 200
    # the frame supplies full screen + zoom controls, and re-applies zoom across re-renders
    assert "requestFullscreen" in cf.text and "cf-frame" in cf.text and "cf-bar" in cf.text
    assert "chart-host" in cf.text and "MutationObserver" in cf.text

    # loaded once via the page shell, so it reaches EVERY page/chart
    assert "/static/chartframe.js" in c.get("/analysis/Project5").text

    # every chart container is marked so the frame attaches
    for path in ("/analysis/Project5", "/curves", "/wbs/Project5", "/forecast", "/trend", "/cei"):
        assert "chart-host" in c.get(path).text, path

    css = c.get("/static/app.css").text
    assert ".cf-frame" in css and ".cf-bar" in css and ".cf-scroll" in css

    # readable, non-overlapping labels: trend + curves prefer the data date over long filenames
    marker = "versions.some(function (v) { return v.status_date; })"
    assert marker in c.get("/static/trend.js").text
    assert marker in c.get("/static/curves.js").text
    # forecast-drift axis is adaptive (year / quarter / month), not the old year-only scale
    assert "stepMonths" in c.get("/static/drift.js").text


def test_hide_completed_uses_a_robust_complete_flag(client: TestClient) -> None:
    """The grid/driving rows carry a robust `complete` flag and the hide-completed toggles
    filter on it — fixing done-at-99% activities (actual finish, <100%) slipping past >=100."""
    acts = client.get("/api/analysis/Project5").json()["activities"]
    assert all("complete" in a for a in acts)
    assert next(a for a in acts if a["percent_complete"] >= 100)["complete"] is True
    dj = client.get("/api/driving/Project5?target=143").json()
    assert all("complete" in r for r in dj["rows"])
    path_js = client.get("/static/path.js").text
    assert "r.complete" in path_js and "r.percent_complete >= 100" not in path_js
    assert "!r.complete" in client.get("/static/app.js").text  # report trace filters on it


def test_complete_flag_true_when_actual_finish_present_below_100() -> None:
    import datetime as dt

    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import _activity_rows

    mon = dt.datetime(2025, 1, 6, 8, 0)
    t1 = Task(
        unique_id=1,
        name="A",
        duration_minutes=480,
        percent_complete=99.0,  # real .mpp/.xer done activity reporting <100%...
        actual_start=mon,
        actual_finish=dt.datetime(2025, 1, 6, 17, 0),  # ...but it carries an actual finish
    )
    t2 = Task(unique_id=2, name="B", duration_minutes=480)
    sch = Schedule(
        name="s",
        project_start=mon,
        tasks=(t1, t2),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    rows = {r["unique_id"]: r for r in _activity_rows(sch, compute_cpm(sch))}
    assert rows[1]["complete"] is True  # actual finish present despite 99%
    assert rows[2]["complete"] is False  # not started


def test_unknown_analysis_page_is_404(client: TestClient) -> None:
    r = client.get("/analysis/NoSuchSchedule")
    assert r.status_code == 404 and "No schedule named" in r.text
