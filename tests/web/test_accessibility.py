"""Accessibility (Section 508 / WCAG) foundations — focus ring, reduced-motion, theme tokens,
non-colour cues. From the external audit work order (Group 1 + theme tokens + colour cues).

These assert the static assets carry the required rules/attributes (the suite serves them via the
test client). Pure presentation — no engine numbers change."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

#: the five auto-play stepper charts that must honor prefers-reduced-motion (A2)
_AUTOPLAY_JS = ("cei.js", "drift.js", "path_evolution.js", "scurve.js", "trend_drill.js")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_visible_keyboard_focus_ring(client: TestClient) -> None:
    """A1 (WCAG 2.4.7): a visible, theme-aware :focus-visible ring exists (the --focus token,
    defined but previously unused, is now applied)."""
    css = client.get("/static/base.css").text
    assert ":focus-visible" in css and "var(--focus)" in css and "outline" in css


def test_reduced_motion_is_honored(client: TestClient) -> None:
    """A2 (WCAG 2.3.3): a prefers-reduced-motion media block neutralizes transitions/animations,
    and every auto-play stepper gates its timer on the same preference."""
    css = client.get("/static/base.css").text
    assert "@media (prefers-reduced-motion: reduce)" in css
    for name in _AUTOPLAY_JS:
        js = client.get(f"/static/{name}").text
        assert "prefers-reduced-motion" in js, name


def test_theme_tokens_border_and_grid_line_are_defined(client: TestClient) -> None:
    """A6: --border and --grid-line were used with hardcoded fallbacks but never defined; they are
    now defined in BOTH theme blocks so they adapt to light mode."""
    css = client.get("/static/base.css").text
    assert css.count("--border:") >= 2  # :root (dark) + html[data-theme=light]
    assert css.count("--grid-line:") >= 2


def test_sr_only_helper_present(client: TestClient) -> None:
    """A3 groundwork: the visually-hidden helper for screen-reader-only chart data tables."""
    css = client.get("/static/base.css").text
    assert ".sr-only" in css and "clip:rect(0 0 0 0)" in css


def test_critical_bars_carry_a_non_colour_cue(client: TestClient) -> None:
    """A8 (WCAG 1.4.1): critical / driving-path bars also carry a diagonal hatch, so criticality is
    distinguishable without relying on hue (CVD-safe). The palette is unchanged."""
    css = client.get("/static/app.css").text
    assert "repeating-linear-gradient" in css
    assert ".g-bar.g-crit" in css and ".gantt-bar.tier-DRIVING" in css


_CHART_JS = (
    "cei.js",
    "curves.js",
    "drift.js",
    "path_evolution.js",
    "scurve.js",
    "sra.js",
    "trend.js",
    "trend_drill.js",
    "wbs.js",
)


#: The data-series charts that ALSO carry a visually-hidden .sr-only data-table fallback, so a
#: screen reader can read the numbers (not just the chart's accessible name). Every chart in
#: _CHART_JS except the path-evolution Gantt — a timeline backed by its own visible per-activity
#: grid rather than a numeric series.
_DATA_TABLE_JS = tuple(n for n in _CHART_JS if n != "path_evolution.js")


def test_charts_have_accessible_names_and_data_tables(client: TestClient) -> None:
    """A3 (WCAG 1.1.1 / 508): every chart SVG gets a real accessible NAME (no more nameless
    role=img), and every data-series chart adds a visually-hidden data-table fallback so screen
    readers can read the numbers the chart draws (the path-evolution Gantt is name-only)."""
    a11y = client.get("/static/a11y.js")
    assert a11y.status_code == 200
    assert "window.SFA11y" in a11y.text and "aria-label" in a11y.text and "sr-only" in a11y.text
    assert "/static/a11y.js" in client.get("/curves").text  # shell-loaded, reaches every chart page
    for name in _CHART_JS:
        js = client.get(f"/static/{name}").text
        if name == "path_evolution.js":
            # ADR-0187: the evolution chart is a real HTML table Gantt — natively accessible,
            # with the SFA11y data-table kept as the "Data" toggle mirror
            assert "SFA11y.table" in js
            continue
        assert "SFA11y.label" in js, name  # named SVG
    for name in _DATA_TABLE_JS:
        assert "SFA11y.table" in client.get(f"/static/{name}").text, name  # data-table fallback


def test_print_stylesheet_makes_briefings_print_ready(client: TestClient) -> None:
    """A5: a @media print block hides the chrome (nav / toolbars / controls), forces light ink,
    avoids splitting panels across pages, and prints the scrollers in full."""
    css = client.get("/static/base.css").text
    assert "@media print" in css
    assert "#askPanel" in css  # the print block hides the ask panel (chrome)
    assert "break-inside:avoid" in css and "background:#fff" in css
    assert "overflow:visible" in css  # scrollers print in full


def test_table_headers_carry_scope(client: TestClient) -> None:
    """A4 (WCAG 1.3.1): server-rendered table column headers associate with their cells."""
    from pathlib import Path

    golden = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "golden"
        / "project2_5"
        / "Project5.mspdi.xml"
    )
    client.post("/upload", files={"files": ("Project5.mspdi.xml", golden.read_bytes(), "text/xml")})
    assert "scope=col" in client.get("/analysis/Project5").text
    assert "scope=col" in client.get("/help").text  # the metric dictionary table too


def test_theme_toggle_announces_state_and_defaults_to_light(client: TestClient) -> None:
    """A10: the theme control is a three-way CYCLE (Light -> Dark -> JARVIS, ADR-0146), so it
    announces via aria-label naming the NEXT theme (aria-pressed is a two-state semantic and
    would be wrong for a cycler). The tool still defaults to Light unless the saved choice is
    explicitly dark or jarvis."""
    js = client.get("/static/theme.js").text
    assert "aria-label" in js and "Switch theme" in js
    assert '"jarvis"' in js  # the HUD theme is part of the cycle
    assert 'saved !== "dark"' in js and 'setAttribute("data-theme"' in js


def test_layout_reflows_on_narrow_viewports(client: TestClient) -> None:
    """A9 (WCAG 1.4.10): a responsive breakpoint wraps the nav and collapses the wide card grids
    to a single column, so 200%-zoom / narrow widths don't need horizontal page scroll."""
    css = client.get("/static/base.css").text
    assert "@media (max-width:760px)" in css
    assert "flex-wrap:wrap" in css and "grid-template-columns:1fr" in css
