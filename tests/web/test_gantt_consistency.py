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
    # the evolution table Gantt (ADR-0187) fits the whole locked axis by clearing the px zoom
    evo = client.get("/static/path_evolution.js").text
    assert "evoZoomReset" in evo and "pxZoom = null" in evo


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
    assert "barDates" in js and "SFGantt.fmtMDY(" in js  # dates on the bars (MM/DD/YYYY)
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


def test_checklist_popup_survives_scrolling_its_own_list(client: TestClient) -> None:
    """Bug fix: the checklist popup closed on ANY capture-phase scroll — including scrolling its
    OWN option list (max-height 240px, app.css). The scroll handler now ignores events whose
    target lives inside the open popup, and still closes on real page scrolls."""
    js = client.get("/static/checklist.js").text
    assert "openPopup.contains(ev.target)" in js  # the popup-scroll guard
    assert 'window.addEventListener("scroll"' in js  # still closes on real page scrolls
    css = client.get("/static/app.css").text
    assert ".sf-filter-list { max-height: 240px; overflow-y: auto;" in css  # the scrollable list


def test_shared_mdy_date_formatter_on_every_gantt(client: TestClient) -> None:
    """Operator: every Gantt date reads MM/DD/YYYY (e.g. 02/25/2026), zero-padded, never a
    time-of-day. One shared formatter (SFGantt.fmtMDY) renders the row date cells, the on-bar
    labels and the bar tooltips; the underlying data stays ISO and is formatted at render only."""
    gantt = client.get("/static/gantt.js").text
    assert "function fmtMDY" in gantt
    assert "fmtMDY: fmtMDY" in gantt  # exported on window.SFGantt
    for name in ("app.js", "path.js", "sra_grid.js", "driving_path.js", "path_evolution.js"):
        assert "fmtMDY(" in client.get(f"/static/{name}").text, name


def test_trace_gantt_is_the_same_table_grid_as_the_others(client: TestClient) -> None:
    """Uniformity: the /analysis driving-path trace (#gantt) renders the SAME table-based
    gantt-grid as the other grids — a sticky thead with the tiered timescale, SFGantt-frozen
    data columns, SFColResize resizable columns and per-column checklist filters — replacing its
    old one-off flex-div layout (no sticky header, no filters, no frozen columns)."""
    js = client.get("/static/app.js").text
    assert '"gantt-grid trace-grid"' in js  # the shared table Gantt
    assert 'SFColResize.attach(table, "trace")' in js  # drag-to-resize, persisted per view
    assert "traceDistinct" in js and "traceFilters" in js  # per-column checklist filters
    assert "TRACE_FIELDS" in js and "Driv slack" in js  # the trace data columns live on
    assert "tier-" in js  # driving/secondary/tertiary/beyond tier tinting preserved
    css = client.get("/static/app.css").text
    # the trace scroll pane caps + scrolls like #grid/.path-view so the sticky thead engages
    assert ".gantt-scroll { overflow-x: auto; overflow-y: auto; max-height: 80vh;" in css
    assert ".trace-grid tr.done td" in css  # completed rows stay muted in the table form


def test_trace_honors_dates_on_bars_and_labels_are_clamped(client: TestClient) -> None:
    """#gridBarDates drives BOTH gantts (the activity grid AND the driving-path trace), and the
    on-bar labels are clamped inside the visible track so a label near x=0 or the right edge is
    no longer clipped by the track's overflow:hidden."""
    js = client.get("/static/app.js").text
    assert "function barLabel" in js and "axis.width - LABEL_W" in js  # clamped into the track
    # grid bars + milestone AND trace bars + milestone all place labels through the clamp
    assert js.count("barLabel(track, axis,") >= 6
    assert "renderGantt(lastDriving)" in js  # the barDates toggle re-renders the trace too


def test_fit_uses_measured_frozen_width_not_hardcoded(client: TestClient) -> None:
    """Fit-to-page subtracts the REAL measured frozen-column width (recorded from the
    SFGantt.freezeColumns return, as path.js already did) instead of the old hard-coded
    estimates (360/520/320 px), so the timeline fills the whole page next to the columns."""
    for name in ("app.js", "sra_grid.js", "driving_path.js"):
        assert "lastFrozenWidth" in client.get(f"/static/{name}").text, name
    assert "- 360" not in client.get("/static/app.js").text
    assert "- 520" not in client.get("/static/sra_grid.js").text
    assert "- 320" not in client.get("/static/driving_path.js").text


def test_per_column_filters_on_sra_and_corridor_grids(client: TestClient) -> None:
    """MS-Project per-column checklist filters everywhere: the SRA grid filters its non-editable
    columns (UID / Task / Rem d) and the driving-path corridor filters UID / Name; both repaint
    only the body so the open dropdown survives a selection."""
    sra = client.get("/static/sra_grid.js").text
    assert "SFChecklist.filter(" in sra
    assert '"filter-row"' in sra and "rowMatchesFilters" in sra
    assert '"UID"' in sra and '"Task"' in sra and '"Rem d"' in sra
    dp = client.get("/static/driving_path.js").text
    assert "SFChecklist.filter(" in dp
    assert '"filter-row"' in dp and "rowMatchesFilters" in dp
    assert "paintBody" in dp  # a filter change repaints the body, not the whole table
