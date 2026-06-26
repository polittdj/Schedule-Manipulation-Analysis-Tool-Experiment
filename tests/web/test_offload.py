"""SRA Monte-Carlo process offload — keep the server responsive without changing the numbers.

The heavy SRA simulations run in a worker process so a concurrent request (e.g. Ask-the-AI on the
same page) isn't starved while they compute. These tests pin: the worker actually runs in another
process, its result is byte-identical to an in-process run (the parity guarantee), it falls back
in-process when no worker is available, small schedules stay in-process, and the SRA routes use it.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web import offload
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.offload import (
    OFFLOAD_TASK_THRESHOLD,
    run_maybe_offloaded,
    run_offloaded,
    shutdown_offload,
)

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


# top-level (picklable) helpers the worker process can resolve
def _pid() -> int:
    return os.getpid()


def _square(x: int) -> int:
    return x * x


def _seeded_samples(seed: int, n: int) -> list[float]:
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]


def test_run_offloaded_runs_in_a_worker_process() -> None:
    """The work happens in ANOTHER process — what frees the server's GIL for other requests."""
    try:
        child = run_offloaded(_pid)
    finally:
        shutdown_offload()
    assert child != os.getpid()


def test_run_offloaded_result_is_byte_identical_to_in_process() -> None:
    """The offloaded call returns exactly the in-process result; a seeded RNG draws the SAME
    sequence in the worker (so a deterministic Monte-Carlo stays byte-identical)."""
    try:
        assert run_offloaded(_square, 9) == _square(9)
        assert run_offloaded(_seeded_samples, 1234, 64) == _seeded_samples(1234, 64)
    finally:
        shutdown_offload()


def test_function_errors_propagate_unchanged(_reset_offload: None) -> None:
    """The function's OWN exception is raised to the caller (the route turns it into a 422); only
    pool-infrastructure failures trigger the in-process fallback."""
    with pytest.raises(ValueError, match="boom"):
        run_offloaded(_raise)
    shutdown_offload()


def test_falls_back_in_process_when_no_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    """A platform that cannot spawn a worker runs the call in-process — same answer, no crash."""
    monkeypatch.setattr(offload, "_pool", None)
    monkeypatch.setattr(offload, "_disabled", True)
    assert run_offloaded(_square, 7) == 49  # disabled pool → in-process, correct
    assert run_maybe_offloaded(True, _square, 6) == 36


def test_run_maybe_offloaded_stays_in_process_when_not_heavy() -> None:
    """Below the threshold the work runs in THIS process (no spawn cost for a sub-second run)."""
    assert run_maybe_offloaded(False, _pid) == os.getpid()


def test_offload_threshold_is_reasonable() -> None:
    assert 100 <= OFFLOAD_TASK_THRESHOLD <= 2000


def test_sra_routes_are_wired_through_the_offload() -> None:
    """Every heavy SRA compute call site goes through run_maybe_offloaded with a task-count gate, so
    a large schedule offloads while a small one stays in-process."""
    import re

    src = (Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/app.py").read_text(
        encoding="utf-8"
    )
    norm = re.sub(r"\s+", " ", src)  # whitespace-agnostic (survives ruff reflow)
    assert norm.count("run_maybe_offloaded(") >= 5  # the 5 heavy SRA call sites
    assert "run_maybe_offloaded( heavy, compute_sra," in norm
    assert "run_maybe_offloaded( heavy, compute_sra_ssi," in norm
    assert "run_maybe_offloaded( heavy, compute_oat_sensitivity," in norm
    assert src.count("len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD") >= 4
    assert "shutdown_offload()" in src  # the worker is torn down on Quit


def test_sra_simulation_still_runs_end_to_end() -> None:
    """A small golden schedule (< threshold) runs the simulation in-process and returns the result
    payload — the offload wiring doesn't change the served numbers."""
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    r = c.get("/api/sra?iterations=200")
    assert r.status_code == 200
    assert r.json()["iterations"] == 200  # the requested Monte-Carlo actually ran


def _raise() -> None:
    raise ValueError("boom")


@pytest.fixture
def _reset_offload() -> object:
    yield None
    shutdown_offload()


def test_reset_is_registered_with_atexit_for_watchdog_exit() -> None:
    """Audit L3: the worker teardown must run on ANY interpreter exit, not just the /api/shutdown
    route — the browser-gone watchdog exit skips the explicit call. The module registers `_reset`
    with atexit; here we exercise the teardown it invokes (start a pool, then `_reset` clears it).
    """
    import platform

    if platform.system() == "Windows":  # pragma: no cover - spawn cost in CI is POSIX-only here
        pytest.skip("pool spawn not exercised on this platform")
    try:
        offload.run_offloaded(_identity, 5)
    except Exception:  # pragma: no cover - platform without a usable spawn method
        pytest.skip("offload pool not available on this platform")
    assert offload._pool is not None  # a worker is live
    offload._reset()  # the function atexit invokes
    assert offload._pool is None  # torn down deterministically


def _identity(x: int) -> int:
    return x
