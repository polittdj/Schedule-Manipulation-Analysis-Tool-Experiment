"""Execute workbench.js's fmt() cell formatter under node (audit L1 / M8).

`workbench.js` was previously only syntax-checked (`node --check`); the cell presentation — unit
formatting and the NA "—" branch — was never EXECUTED, which hid the L1 bug (an unmeasurable
metric rendered "0.00" not "—"). The .mjs harness brace-extracts the real fmt and drives the
cases the server pins (a not-applicable cell → "—"; an informational extra's real 0 → "0").
Skips only when node is absent (node is a documented local-gate dependency).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "workbench_fmt_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_workbench_fmt_renders_na_as_dash_and_keeps_real_values() -> None:
    node = shutil.which("node")
    assert node is not None
    proc = subprocess.run(
        [node, str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
