"""Execute the Gantt non-working-time shading under node to prove per-task calendar shading (audit).

ADR-0243 shades each Gantt row's non-working time per THAT task's own calendar — a 24-hour task
shows no weekend gray, a Mon-Fri task does. The logic lives in vendored ``timescale.js``
(``SFTimescale.nonworkStyle`` + the ``setCalendars`` registry) and was behaviorally untested; #382
even shipped a ``/driving-path`` per-row calendar read that silently did nothing. The ``.mjs``
harness loads the vendored IIFE with injected globals and asserts the shading differs by calendar
(Mon-Fri shades weekends, 24-hour does not, and an explicit global pick overrides the per-row one).
Skips only when node is absent (a documented local-gate + CI dependency).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "gantt_shading_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_gantt_shading_is_per_task_calendar() -> None:
    node = shutil.which("node")
    assert node is not None
    proc = subprocess.run(
        [node, str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"Gantt-shading harness failed:\n{proc.stdout}\n{proc.stderr}"
