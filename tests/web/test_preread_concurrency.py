"""home.js pre-reads picked files with BOUNDED CONCURRENCY, order-identically (ADR-0289).

The upload pre-read (`file.arrayBuffer()` per picked file, which surfaces an unreadable OneDrive
placeholder as a catchable error instead of a silent send-time failure) used to await one file at a
time. On a folder drop that paid the full per-file latency serially — and for cloud-backed files
that latency is a network hydrate, so an N-file folder cost N round-trips end to end.

Overlapping the reads is only safe if ORDER is preserved: `/upload` relies on `readable[j]` staying
aligned with `meta[j]`, and the "could not read these files" notice lists `skipped` in pick order.
The harness therefore re-implements the original sequential algorithm as an oracle and asserts the
pooled version is byte-identical over empty / single / clean / failure-laden selections with
jittered latency, then asserts the pool is genuinely bounded (peak <= cap — what stops a 500-file
folder opening 500 concurrent buffers) and genuinely parallel (peak > 1).

Executed under node rather than asserted from source: a concurrency bug is a behaviour, and a
source pin cannot catch one. Skips only when node is absent (a documented local-gate tool).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_HARNESS = Path(__file__).parent / "js" / "preread_concurrency_harness.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_preread_is_bounded_parallel_and_order_identical_to_sequential() -> None:
    node = shutil.which("node")
    assert node is not None
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(_HARNESS)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.startswith("OK"), proc.stdout


def test_the_concurrency_bound_is_declared_once_and_is_sane() -> None:
    """A cap of 1 silently restores serial behaviour; an unbounded one defeats the point."""
    js = (REPO / "src/schedule_forensics/web/static/home.js").read_text(encoding="utf-8")
    line = next(ln for ln in js.splitlines() if "var PREREAD_CONCURRENCY" in ln)
    cap = int(line.split("=", 1)[1].strip().rstrip(";"))
    assert 2 <= cap <= 16, f"PREREAD_CONCURRENCY={cap} is outside the sane band"
    assert js.count("var PREREAD_CONCURRENCY") == 1  # one source of truth
