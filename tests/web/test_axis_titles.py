"""Axis captions come from ONE shared helper, and the remaining work is an explicit ledger.

ADR-0298 promotes the single axis-caption implementation into ``chartframe.js``
(``SFChartFrame.axisTitles``) and retires the two conflicting ones that existed in the tree
(``performance.js``'s local pair, ``scatter.js``'s centred-X + rotated-Y pair).

The regression this guards is **not** "a chart forgot a caption" — it is "someone drew a caption
a second way". That is what re-fragments the convention, and it is asserted below globally.

**Why a ledger instead of a tick-detecting regex.** The spec's heuristic (match modules that draw
SVG tick text) under-detected by half: it missed ``path.js`` and ``resources.js``, which do draw
SVG axes, and it silently said nothing about the dozen modules whose visuals are **HTML/DOM, not
SVG** — including ``gantt.js``, which is explicitly "shared Microsoft-Project-style **HTML** Gantt
timeline primitives". An SVG ``<text>`` helper cannot caption an HTML Gantt, so those modules are
recorded as a separate, named category rather than quietly skipped. Every non-exempt module must
appear in exactly one bucket; a NEW file that fits none of them fails this test, which is the
anti-regression property the heuristic could not give.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"

#: Chrome, frames, rulers and utilities — they render no data visual of their own.
#: ``timeaxis`` / ``timescale`` are the shared rulers consumed by charts that carry their own
#: captions; ``chartframe`` is the frame (and now the caption helper's home).
EXEMPT = {
    "a11y.js",
    "ai_polish.js",
    "app.js",
    "ask.js",
    "chartframe.js",
    "checklist.js",
    "chrome.js",
    "colresize.js",
    "dashboard.js",
    "globe.js",
    "groups.js",
    "heartbeat.js",
    "hints.js",
    "home.js",
    "legend_toggle.js",
    "mission.js",
    "persist.js",
    "settings.js",
    "story.js",
    "sysmon.js",
    "target.js",
    "taskinfo.js",
    "theme.js",
    "timeaxis.js",
    "timescale.js",
    "tooltips.js",
    "translate.js",
    "vizhints.js",
}

#: Visuals rendered as HTML/DOM rather than SVG — tables, chip rows, DOM bars, and the HTML
#: Gantt family. ``SFChartFrame.axisTitles`` appends an SVG ``<text>``, so it does not apply to
#: them: captioning a DOM visual needs a DOM label element, which is a separate design decision
#: (deferred deliberately, ADR-0298 §Consequences — not an omission).
NO_SVG_AXES = {
    "drilldown.js",
    "driving_path.js",
    "driving_tiers.js",
    "findings_drill.js",
    "gantt.js",
    "path_evolution.js",
    "ribbon_drill.js",
    "scorecards.js",
    "sra_grid.js",
    "sra_risk.js",
    "whatif.js",
    "workbench.js",
}

#: SVG axis charts not yet captioned. This list SHRINKS one batch at a time and reaching empty
#: is the completion signal for AXIS-TITLES. A module may not be parked here once it calls the
#: helper, and may not be listed here unless it really renders SVG — both are asserted.
PENDING = {
    # ``drift.js`` is deliberately still here after batch 1, for two reasons worth stating so the
    # next batch does not "just add the call": (1) its Y axis is a list of three FORECAST METHODS
    # and its X axis is a forecast DATE — the patch spec's "SCHEDULE VERSION (UPDATE)" by
    # "SLIP AGAINST BASELINE (WORKDAYS)" would print a false statement on the chart; (2) the Y
    # caption anchor (``T + 9``) lands 7px above its first method-name row (``padT + 14``), so it
    # needs a padT nudge, and moving the plot is out of scope for a caption batch.
    "drift.js",
    "margin.js",
    "margin_dashboard.js",
    "path.js",
    "sra.js",
    "sra_jcl.js",
    "sra_ssi.js",
    "trend.js",
    "trend_drill.js",
    "volatility.js",
    "wbs.js",
}

CALLS_HELPER = re.compile(r"SFChartFrame\.axisTitles\s*\(")
#: Caption-drawing done any way other than the shared helper — the fragmentation this guards.
SECOND_CONVENTION = re.compile(
    r"""(rotate\(-90|axisTitle\s*=|\bxt\.textContent|\byt\.textContent)"""
)
RENDERS_SVG = re.compile(r"w3\.org/2000/svg")


def modules() -> list[Path]:
    return sorted(STATIC.glob("*.js"))


def _src(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_every_module_is_classified_exactly_once() -> None:
    """A new chart module must be triaged deliberately — it cannot slip through unnoticed."""
    names = {p.name for p in modules()}
    stale = (EXEMPT | NO_SVG_AXES | PENDING) - names
    assert not stale, f"ledger names files that no longer exist: {sorted(stale)}"

    captioned = {p.name for p in modules() if CALLS_HELPER.search(_src(p))}
    unclassified = names - EXEMPT - NO_SVG_AXES - PENDING - captioned
    assert not unclassified, (
        "these modules are in no bucket — add each to EXEMPT (no data visual), NO_SVG_AXES "
        f"(HTML/DOM visual), or PENDING (an SVG chart awaiting captions): {sorted(unclassified)}"
    )
    overlap = captioned & PENDING
    assert not overlap, f"already captioned but still parked in PENDING: {sorted(overlap)}"


@pytest.mark.parametrize("name", sorted(PENDING))
def test_pending_entries_are_really_svg_charts(name: str) -> None:
    """Keeps the remaining-work ledger honest: a DOM visual belongs in NO_SVG_AXES, not here,
    or the count of 'charts still to caption' silently overstates the work."""
    assert RENDERS_SVG.search(_src(STATIC / name)), (
        f"{name} renders no SVG — it belongs in NO_SVG_AXES, not PENDING"
    )


@pytest.mark.parametrize("name", sorted(NO_SVG_AXES))
def test_no_svg_axes_entries_really_render_no_svg(name: str) -> None:
    """The mirror check: a module parked as 'DOM visual' must not actually draw SVG axes."""
    assert not RENDERS_SVG.search(_src(STATIC / name)), (
        f"{name} does render SVG — move it to PENDING (or caption it) rather than exempting it"
    )


def test_captioned_modules_pass_both_labels() -> None:
    """One-axis captions are not acceptable: a captioned module must supply both labels."""
    for p in modules():
        if not CALLS_HELPER.search(_src(p)):
            continue
        src = _src(p)
        assert "xLabel" in src and "yLabel" in src, (
            f"{p.name} calls axisTitles but never supplies both xLabel and yLabel"
        )


def test_no_module_reimplements_the_caption_helper() -> None:
    """THE regression this file exists for: captions drawn a second way (ADR-0195, one
    convention). Only chartframe.js may contain caption-drawing code."""
    offenders = [
        p.name for p in modules() if p.name != "chartframe.js" and SECOND_CONVENTION.search(_src(p))
    ]
    assert not offenders, (
        "axis captions must be drawn only by SFChartFrame.axisTitles — these draw their own: "
        + ", ".join(offenders)
    )


def test_the_helper_takes_its_size_from_the_token_not_a_literal() -> None:
    """A numeric size in JS would fork the type ramp back into 30 modules."""
    frame = _src(STATIC / "chartframe.js")
    # the WHOLE caption block, not just axisTitles(): the node-building helper sits above it, and
    # a numeric size planted there escaped an earlier, narrower slice of this assertion.
    block = frame[frame.index("shared axis captions") : frame.index("window.SFChartFrame =")]
    assert "font-size" not in block, "the caption block must not set a font-size in JS"
    assert "fill" not in block, "the caption block must not set a fill in JS (.ch-at owns colour)"
    assert '"ch-at"' in block, "axisTitles must apply the .ch-at class"

    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "--sf-fs-axis-title:" in css, "the axis-caption size token must be defined"
    assert "font-size:var(--sf-fs-axis-title)" in css, ".ch-at must read the token"


def test_the_helper_is_available_on_every_page() -> None:
    """chartframe.js is layout-global, so no chart has to import anything to caption its axes."""
    app = (ROOT / "src" / "schedule_forensics" / "web" / "app.py").read_text(encoding="utf-8")
    assert '<script src="/static/chartframe.js"></script>' in app


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_the_helper_behaves_under_node() -> None:
    """Placement, the .ch-at hook, and the no-numeric-type law are BEHAVIOUR, and a source pin
    cannot catch a behaviour (ADR-0289). The harness boots chartframe.js against a DOM stub and
    drives axisTitles for real; it also pins that the Y caption is never rotated, which is the
    convention this ADR exists to retire."""
    node = shutil.which("node")
    assert node is not None
    harness = Path(__file__).parent / "js" / "axis_titles_harness.mjs"
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(harness)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.rstrip().endswith("OK axis titles"), proc.stdout
