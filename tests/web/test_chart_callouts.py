"""Shared chart hover call-outs (chart-framework slice 1).

chartframe.js frames every `.chart-host`; this adds a single styled tooltip that shows an instant
call-out for any chart shape carrying a direct `<title>` child (the existing native-tooltip text
used across the charts) or an explicit `data-callout`. So every title-bearing chart gains a real
hover call-out without per-chart wiring. The repo tests vendored JS by presence + `node --check`
(no DOM harness), so this asserts the wiring tokens and the broadened coverage.
"""

from __future__ import annotations

from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


def test_chartframe_wires_hover_callouts() -> None:
    js = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    assert "cf-tip" in js  # the shared tooltip element
    assert "data-callout" in js  # explicit rich-callout hook
    assert "calloutText" in js and "mousemove" in js  # reads <title>/data-callout, follows cursor
    # ADR-0190: wired ONCE at document level (every page, framed or not), not per-host
    assert 'document.addEventListener("mousemove"' in js and "wireCallouts()" in js


def test_callout_never_doubles_with_the_native_tooltip() -> None:
    """Operator (ADR-0190): only ONE call-out at a time — the styled cf-tip — never the browser's
    own title-attribute tooltip popping up on top of it. chartframe moves the hovered element's
    title= (and SVG <title> child) into data-cf-title, so the native tooltip can never fire again
    for anything the styled call-out covers."""
    js = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    assert 'setAttribute("data-cf-title"' in js  # the text survives on the element
    assert 'removeAttribute("title")' in js  # HTML title= stripped -> no native tooltip
    assert "removeChild(k)" in js  # SVG <title> child stripped -> no native tooltip
    assert 'getAttribute("data-cf-title")' in js  # subsequent hovers read the moved text
    assert 'addEventListener("scroll", hideTip, true)' in js  # no stale tip mid-scroll


def test_callout_tooltip_is_styled() -> None:
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ".cf-tip" in css and "pointer-events: none" in css


def test_histogram_bars_carry_a_callout_title() -> None:
    js = (STATIC / "histogram.js").read_text(encoding="utf-8")
    # previously title-less; bars now emit a <title> so the shared call-out covers them
    assert 'svgEl("title"' in js
    assert "% of " in js  # count + share-of-population call-out text


def test_sra_charts_carry_callout_titles() -> None:
    js = (STATIC / "sra.js").read_text(encoding="utf-8")
    # SRA was title-less; the finish histogram bars and the sensitivity tornado bars now emit
    # <title> call-outs (operator named the SRA page specifically)
    assert js.count('svgEl("title"') >= 2
    assert "simulated finishes" in js  # histogram bar call-out
    assert "Sensitivity " in js and "Criticality " in js  # tornado bar call-out


def test_chartframe_exposes_a_rescan_api_and_zooms_non_svg_visuals() -> None:
    """Charts built AFTER load (the on-demand SSI run) need a public hook to frame their fresh
    .chart-host wrappers; the HTML 5x5 matrix opts into zoom via the cf-zoom-box transform path."""
    js = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    assert "window.SFChartFrame" in js and "scan: scan" in js  # public re-scan hook
    assert "cf-zoom-box" in js and "scale(" in js  # transform-zoom the non-SVG matrix


def test_ssi_charts_are_framed_and_carry_value_callouts() -> None:
    """Operator: enlarge/shrink the SSI visuals and read the values on hover. Each S-curve /
    histogram is wrapped in its own .chart-host (zoom + full screen) and every shape emits a
    <title> call-out."""
    js = (STATIC / "sra_ssi.js").read_text(encoding="utf-8")
    assert "chart-host" in js  # each chart gets its own frame
    assert "SFChartFrame.scan()" in js  # re-frame the freshly-built charts
    assert 'svg("title")' in js and "function titled(" in js  # hover-callout helper
    assert "% confidence" in js  # the S-curve per-point call-out
    assert 'class: "ch-hot"' in js  # transparent per-point hover hotspots
    assert 'finish" + (b.count === 1' in js  # the histogram bar call-out (count of finishes)
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ".ssi-svg .ch-hot" in css  # the invisible hover hotspots
    assert ".ssi-matrices" in css  # the matrices laid out in a framed row


def test_ssi_matrix_cells_call_out_the_risks_that_land_in_them() -> None:
    """Operator: dive into the Risk Assessment Matrix — hover a cell to see its risks."""
    js = (STATIC / "sra_ssi.js").read_text(encoding="utf-8")
    assert "function cellItems(" in js  # the per-cell membership (same binning as the engine grid)
    assert "data-callout" in js  # the rich hover call-out chartframe reads
    assert "Risks here:" in js and "Opportunities here:" in js  # the cell detail headings
    assert "cf-zoom-box" in js  # the matrix is zoomable
    assert "nm-detail" in js  # populated cells get the dive-in cursor
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert ".nm-cell.nm-detail" in css and "cursor: help" in css


def test_scurve_uses_the_shared_time_tier_axis() -> None:
    """The S-curve draws its stacked Year/Quarter/Month axis via the shared SFTimeAxis module."""
    js = (STATIC / "scurve.js").read_text(encoding="utf-8")
    assert "SFTimeAxis.draw" in js and "SFTimeAxis.tiersFor" in js


def test_shared_time_axis_module_has_the_tier_logic() -> None:
    """Operator: the lowest tier shows the first letter of each month (J F M A M J ...)."""
    ta = (STATIC / "timeaxis.js").read_text(encoding="utf-8")
    assert "yearRuns" in ta and "quarterRuns" in ta and "monthRuns" in ta
    assert "function draw" in ta and "parseMonth" in ta
    assert "JFMAMJJASOND" in ta  # first-letter month labels


def test_scurve_page_offers_a_file_version_selector() -> None:
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    client = TestClient(create_app(SessionState()))
    client.post("/example")
    page = client.get("/scurve").text
    assert "id=scurveVersion" in page
    assert "All files (chronological)" in page
    js = (STATIC / "scurve.js").read_text(encoding="utf-8")
    assert "buildVersionSelect" in js and "startAuto" in js


def test_scurve_page_offers_the_time_scale_selector() -> None:
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    client = TestClient(create_app(SessionState()))
    client.post("/example")
    page = client.get("/scurve").text
    assert "id=scurveGran" in page
    assert "Months (year / quarter / month)" in page


def test_scurve_curves_have_per_point_hover_callouts() -> None:
    """The S-curve is a line chart (no per-point shapes), so per-month transparent hit-strips give
    it hover call-outs of planned/actual values via the shared chartframe tooltip."""
    js = (STATIC / "scurve.js").read_text(encoding="utf-8")
    assert 'fill: "transparent"' in js  # the per-month hit-strip
    assert "planned " in js and "actual " in js  # the call-out text


def test_curves_line_charts_have_per_point_hover_callouts() -> None:
    """The Finishes / Data-date / Slippage line charts get the same per-month hit-strip call-outs,
    listing every series' value at the hovered month."""
    js = (STATIC / "curves.js").read_text(encoding="utf-8")
    assert 'fill: "transparent"' in js
    assert "s.values[hi]" in js  # per-series value in the call-out
