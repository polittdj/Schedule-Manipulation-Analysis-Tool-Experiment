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
