"""Execute the "Play all" coordinator in chartframe.js under node (ADR-0275).

The enlarged-chart play/stop bug: a page master "Play all" steps every animated chart by
programmatically clicking their Next buttons on a timer, so a per-chart Stop (which only cleared
that chart's own timer) couldn't halt motion the master was driving — the operator hit Stop and it
"kept playing". The fix registers each master's stop() with window.SFPlayAll and stops every master
on a TRUSTED user click on any per-chart animation control, while the master's OWN element.click()
(isTrusted === false) must not stop it. The .mjs harness boots the IIFE against a minimal DOM stub
and asserts exactly that distinction. Skips only when node is absent (a documented local-gate tool).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "playall_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_play_all_coordinator_stops_masters_only_on_a_real_user_click() -> None:
    proc = subprocess.run(
        [str(shutil.which("node")), str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
