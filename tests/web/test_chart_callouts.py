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
