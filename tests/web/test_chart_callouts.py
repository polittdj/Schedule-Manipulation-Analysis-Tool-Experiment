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
    assert "wireCallouts(host)" in js  # applied to every framed chart


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
