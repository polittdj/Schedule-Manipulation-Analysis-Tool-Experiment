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
