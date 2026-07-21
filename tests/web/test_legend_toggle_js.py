"""Execute the SFLegend series-toggle module (legend_toggle.js) under node (ADR-0276).

Interactive legends: clicking a legend entry shows/hides that series on a chart, plus a
show-all/none control. Animated charts rebuild their series SVG every frame, so the hidden state
must survive a redraw — a lazy per-scope MutationObserver re-applies it. The .mjs harness boots the
IIFE against a minimal DOM stub, drives its delegated click handler, and asserts hide/show, scope
independence, all/none, and (the load-bearing part) that a re-drawn series element inherits the
hidden state. Skips only when node is absent (a documented local-gate tool).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "legend_toggle_harness.mjs"
_SCOPE_HARNESS = Path(__file__).parent / "js" / "legend_scope_harness.mjs"
_STATIC_HARNESS = Path(__file__).parent / "js" / "legend_static_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_legend_toggle_hides_shows_series_and_survives_redraw() -> None:
    proc = subprocess.run(
        [str(shutil.which("node")), str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_legend_stable_scope_survives_svg_replacement() -> None:
    """Phase-3 charts (performance.js / cei.js) draw the legend INSIDE an svg that is rebuilt every
    animation frame; they mark their persistent host with data-series-scope so scopeFor resolves to
    the stable host and a firing MutationObserver re-hides the freshly drawn series after a full svg
    replacement. This harness proves that path (the other harness covers the legend-outside-svg
    fallback)."""
    proc = subprocess.run(
        [str(shutil.which("node")), str(_SCOPE_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_legend_static_and_conditional_color_series() -> None:
    """margin_dashboard.js (phase 3b) mixes clickable toggles with a STATIC color-key entry
    ("Below requirement" is a per-month recoloring of the margin bars, not a separate series), and
    tags a conditional-color series (green above / red below the requirement) with one key. This
    harness proves a single toggle hides both colors together, the static entry is inert, and
    all/none toggles only the real series."""
    proc = subprocess.run(
        [str(shutil.which("node")), str(_STATIC_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
