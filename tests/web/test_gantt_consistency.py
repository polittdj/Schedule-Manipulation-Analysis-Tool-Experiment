"""Gantt visual-consistency tests — one consistent look + interaction across every Gantt.

The operator asked for the same MS-Project feel on every Gantt chart in the tool: a white canvas, a
"View entire project" control that auto-scales the timeline to the whole span, an add/remove-columns
dropdown, and per-column filter dropdowns. These pin the wiring; the white-canvas palette itself is
pinned in test_visuals.py.
"""

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


def test_view_entire_project_button_on_every_gantt_page(client: TestClient) -> None:
    """A "View entire project" fit control is offered on the path-analysis and SRA grid pages
    (the two that render their Gantt unconditionally with a single schedule)."""
    path_page = client.get("/path").text
    assert "id=pathFit" in path_page and "View entire project" in path_page
    sra_page = client.get("/sra").text
    assert "id=ssiGridFit" in sra_page and "View entire project" in sra_page


def test_fit_to_project_logic_in_every_gantt_script(client: TestClient) -> None:
    """Every scalable-timeline Gantt script implements a `fitToProject` "View entire project"
    behaviour. The SRA and driving-path grids keep the `forcedPx` override (set by the fit button,
    cleared when the zoom control is nudged); the path grid drives the same control through its
    auto-fill axis (see test_path_timeline_fills_the_page_next_to_the_columns). The driving-path and
    evolution pages gate their controls on a multi-version corridor, so the wiring is pinned at the
    source level here."""
    for name, button in (("sra_grid.js", "ssiGridFit"), ("driving_path.js", "dpFit")):
        js = client.get(f"/static/{name}").text
        assert "fitToProject" in js, name
        assert "forcedPx" in js, name
        assert button in js, name
    path_js = client.get("/static/path.js").text
    assert "function fitToProject" in path_js and "pathFit" in path_js
    # the evolution SVG Gantt fits the whole project by snapping the view back to its full axis
    evo = client.get("/static/path_evolution.js").text
    assert "evoZoomReset" in evo and "lo = fullLo; hi = fullHi" in evo


def test_freeze_columns_locks_data_columns_on_every_gantt(client: TestClient) -> None:
    """Operator: lock the left-hand data columns on every Gantt so they stay visible when the wide
    timeline scrolls left↔right. The shared SFGantt.freezeColumns() pins every column but the
    scalable timeline (position:sticky + a per-column left offset); each table Gantt calls it, the
    CSS gives the pinned cells an opaque canvas background + a freeze line, it is undone for print,
    and a column resize re-pins."""
    gantt = client.get("/static/gantt.js").text
    assert "function freezeColumns" in gantt
    assert "freezeColumns: freezeColumns" in gantt  # exported on window.SFGantt
    for name in ("app.js", "path.js", "driving_path.js", "sra_grid.js"):
        js = client.get(f"/static/{name}").text
        assert "SFGantt.freezeColumns(" in js, name
    # a drag-resize shifts later columns' left edges → colresize re-pins them
    assert "SFGantt.freezeColumns(table)" in client.get("/static/colresize.js").text
    css = client.get("/static/app.css").text
    assert ".gantt-grid .sf-frozen-col { background: var(--gantt-canvas)" in css
    assert ".gantt-grid .sf-frozen-last { border-right:" in css  # the MS-Project freeze line
    base = client.get("/static/base.css").text
    assert ".gantt-grid .sf-frozen-col{position:static!important" in base  # print un-pins them


def test_path_timeline_fills_the_page_next_to_the_columns(client: TestClient) -> None:
    """Operator: when a path is selected, fit the timeline to it so the bars fill the page next to
    the frozen columns; "View entire project" widens to every activity and rescales; keep the gold
    data-date line off the right border."""
    js = client.get("/static/path.js").text
    # the axis fits the selected tier (the chosen path), else every activity; View-entire widens it
    assert "function axisRows" in js and "scopeAll" in js
    assert "scopeAll = true" in js  # fitToProject spans every activity
    assert "fitFill" in js  # auto-scale px to fill the page; the zoom slider clears it
    # selecting a tier re-fits the timeline to that path
    assert "pathTierSel = s; scopeAll = false; fitFill = true; reflow()" in js
    # asymmetric padding: small left (bars hug the columns), larger right (status-date room)
    assert "t0 -= 2 * DAY_MS" in js
    assert "span * 0.04" in js  # right margin keeps the data-date line off the border
    # the fill width is the page minus the MEASURED data-column width
    assert "function availWidth" in js and "lastFrozenWidth" in js


def test_evolution_reset_button_reads_view_entire_project(client: TestClient) -> None:
    """The critical-path evolution's axis-reset control is labelled like every other Gantt's
    fit control ("View entire project") rather than the old terse "reset"."""
    body = _evolution_page(client)
    assert "id=evoZoomReset" in body
    assert "View entire project" in body
    assert ">reset<" not in body


def test_shared_columns_dropdown_on_grids(client: TestClient) -> None:
    """The activity grid and the path grid both expose add/remove columns through the SAME
    MS-Project-style checklist dropdown (SFChecklist) rather than a loose row of checkboxes."""
    for name in ("app.js", "path.js"):
        js = client.get(f"/static/{name}").text
        assert "SFChecklist.filter(" in js, name
        assert '"Columns"' in js or "'Columns'" in js, name
        assert "Add or remove columns" in js, name


def test_path_grid_has_per_column_filter_row(client: TestClient) -> None:
    """The path grid carries an MS-Project per-column filter row: a filter dropdown under each
    column header that lists that column's distinct values and scopes the visible rows."""
    js = client.get("/static/path.js").text
    assert 'class: "filter-row"' in js  # the per-column filter row under the headers
    assert "distinctValues" in js and "rowMatchesColumns" in js  # the value list + the predicate
    assert "colFilters" in js  # per-column key -> selected Set
    css = client.get("/static/app.css").text
    assert ".path-grid .filter-row" in css  # the row is styled compactly


def test_gantt_headers_are_sticky_and_panes_capped(client: TestClient) -> None:
    """Operator: lock the headers + timescale so they stay visible when scrolling down. Each table
    Gantt scrolls inside its own capped pane and its whole <thead> (column titles + filter row)
    sticks to the top."""
    css = client.get("/static/app.css").text
    assert ".gantt-grid thead { position: sticky; top: 0;" in css
    assert "#grid { overflow-x: auto; overflow-y: auto; max-height: 80vh; }" in css
    assert ".path-view { overflow-x: auto; overflow-y: auto; max-height: 80vh;" in css
    # the opaque header background keeps body rows from showing through the sticky header
    assert ".gantt-grid thead th, .gantt-grid thead td { background: var(--gantt-canvas); }" in css
    # capped panes still print in full (no clipped Gantt on a hard copy)
    base = client.get("/static/base.css").text
    assert "max-height:none!important" in base


def test_all_table_gantts_have_resizable_columns(client: TestClient) -> None:
    """Operator: MS-Project widen/narrow columns on EVERY Gantt. The activity grid and SSI grid
    already attach SFColResize; the path grid and the driving-path corridor now do too, and all of
    them wrap their header rows in a <thead> for the shared sticky-header CSS."""
    for name, key in (
        ("app.js", "analysis"),
        ("sra_grid.js", "ssiGrid"),
        ("path.js", "path"),
        ("driving_path.js", "driving"),
    ):
        js = client.get(f"/static/{name}").text
        assert f'SFColResize.attach(table, "{key}")' in js, name
    # the path + driving grids build a <thead> so the sticky-header rule applies uniformly
    assert 'el("thead")' in client.get("/static/path.js").text
    assert 'el("thead")' in client.get("/static/driving_path.js").text


def test_main_grid_has_msproject_find_outline_and_bar_dates(client: TestClient) -> None:
    """Operator: mirror MS Project on the activity Gantt — a Find-a-UID box that snaps to the row,
    an outline-level picker, a 'dates on bars' toggle, and always-visible bold summary tasks with a
    distinct summary bar."""
    page = client.get("/analysis/Project5").text
    for cid in ("id=gridFind", "id=gridOutline", "id=gridBarDates"):
        assert cid in page, cid
    js = client.get("/static/app.js").text
    assert "function findUid" in js and "scrollIntoView" in js  # snap to the UID's row
    assert "function populateOutline" in js and "maxOutline" in js  # outline-level picker
    assert "barDates" in js and "function shortDate" in js  # dates on the bars
    assert 'tr.setAttribute("data-uid"' in js  # rows carry their UID for Find
    # summaries are ALWAYS shown (WBS context); the outline-level picker collapses depth
    assert "act.is_summary || rowMatches(act, fields)" in js
    css = client.get("/static/app.css").text
    assert ".g-barlabel" in css  # the on-bar date labels
    assert ".g-bar.g-sum::before, .g-bar.g-sum::after" in css  # MS-Project summary end-caps
    assert "#grid tr.row-found td" in css  # the Find highlight


def _evolution_page(client: TestClient) -> str:
    """The evolution view needs two versions to render its animated controls; load a second
    version (a copy is enough to exercise the control markup) and return the page body."""
    second = (GOLDEN / "project2_5" / "Project2.mspdi.xml").read_bytes()
    client.post("/upload", files={"files": ("Project2.mspdi.xml", second, "text/xml")})
    return client.get("/evolution").text
