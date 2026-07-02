"""Execute the client-side days<->% derive math under node (audit L9 / ADR-0143).

`sra_risk.js` was previously only syntax-checked (`node --check`); the derivation the operator
actually uses was never executed by a test. The .mjs harness stubs the minimal DOM, drives the
IIFE's own input handlers, and asserts the server-mirrored formula cases + the L4 stale-value
clear. Skips only when node is absent (node is a documented local-gate dependency)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HARNESS = Path(__file__).parent / "js" / "sra_derive_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_client_derive_math_executes_and_matches_the_server_formula() -> None:
    proc = subprocess.run(
        [str(shutil.which("node")), str(_HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
