"""Execute path.js populateGroupBy() under node to prove the stored DOM-XSS stays fixed (audit).

A custom-field label / MSPDI <Alias> is attacker-controlled free text from an opposing-party
schedule; the old populateGroupBy concatenated it into <option> HTML and assigned innerHTML — a
stored DOM-XSS running as first-party code in the CUI tool (Law 1). The .mjs harness brace-extracts
el()/populateGroupBy() (closure-private) and drives them against a DOM stub that distinguishes
textContent from innerHTML, asserting the labels are built via textContent/attributes with no
innerHTML sink. Skips only when node is absent (a documented local-gate + CI dependency).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "path_groupby_xss_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_path_groupby_has_no_innerhtml_xss_sink() -> None:
    node = shutil.which("node")
    assert node is not None
    proc = subprocess.run(
        [node, str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"XSS harness failed:\n{proc.stdout}\n{proc.stderr}"
