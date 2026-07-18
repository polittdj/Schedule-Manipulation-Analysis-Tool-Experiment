"""Run a CPU-bound engine computation in a worker PROCESS so it never holds the server's GIL.

The Schedule Risk Analysis Monte-Carlo (``compute_sra`` / ``compute_sra_ssi``) and the OAT
sensitivity sweep run hundreds-to-thousands of CPM passes in pure Python. In a FastAPI ``def``
route that work runs in the server's thread-pool and holds the GIL the whole time, which starves
every concurrent request — on the heavy SRA page a simultaneous "Ask the AI" call could hang until
the simulation finished (operator: "the Ask the AI feature freezes on the SRA page"). Dispatching
the call to a single, reusable worker process keeps the server process responsive: the route thread
blocks on the child's result (which releases the GIL), while the actual iterations run on the
child's own interpreter / GIL.

**Deterministic and parity-safe.** The worker runs the SAME top-level engine function with the SAME
(pickled) inputs, so the result is byte-identical to an in-process call — the engine's seeded RNG
(``random.Random(seed + i)`` per iteration) does not depend on the process. The byte-frozen parity
tests call ``compute_sra`` in-process and are untouched.

**Never a new failure mode.** If a worker cannot be created or the pool dies (e.g. a frozen build
without spawn support, or an OOM-killed child), the call falls back to running in-process —
correctness never depends on the pool. The *function's own* exceptions (a ``CPMError`` etc.) are
re-raised unchanged for the route to handle; only infrastructure failures trigger the fallback.

Std-lib only (``concurrent.futures``); the loopback / air-gap posture is unchanged (no sockets, no
network — a local child process).
"""

from __future__ import annotations

import atexit
import threading
from collections.abc import Callable
from concurrent.futures import BrokenExecutor, ProcessPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, TypeVar

T = TypeVar("T")

#: Below this task count an in-process run is sub-second, so the worker's spawn cost isn't worth it.
#: Large schedules (the kind that actually froze the page) clear it and get offloaded.
OFFLOAD_TASK_THRESHOLD = 300

#: Hard ceiling on ONE offloaded compute (ADR-0261 P5). Generous on purpose — the point is that a
#: wedged or runaway worker can never hang the page forever, not to police long runs (the biggest
#: legitimate SRA/OAT runs finish well inside it). On expiry the pool is torn down (the child may
#: be mid-CPM and cannot be interrupted cooperatively) and the caller gets a clear, actionable
#: error instead of an endless spinner. The rare in-process FALLBACK path cannot be timed out
#: (same interpreter); the size caps at the call sites bound that path instead.
OFFLOAD_TIMEOUT_S = 1800.0

_lock = threading.Lock()
_pool: ProcessPoolExecutor | None = None
_disabled = False


def _executor() -> ProcessPoolExecutor | None:
    """The shared single-worker pool, created lazily; ``None`` if this platform can't spawn one.

    Uses the interpreter's default start method on purpose: on Windows (the deployed desktop target)
    that is *spawn*, which is safe to start from the server's worker threads and runs the guarded
    launcher cleanly; on POSIX CI it is *fork*, which the test suite relies on. One worker is enough
    — SRA runs are user-initiated and serialised by the operator, and a single child already frees
    the server's GIL for concurrent requests.
    """
    global _pool, _disabled
    with _lock:
        if _disabled:
            return None
        if _pool is None:
            try:
                _pool = ProcessPoolExecutor(max_workers=1)
            except Exception:  # pragma: no cover - platform dependent (no spawn support)
                _disabled = True
                return None
        return _pool


def _reset() -> None:
    global _pool
    with _lock:
        pool, _pool = _pool, None
    if pool is not None:
        pool.shutdown(wait=False, cancel_futures=True)


def run_offloaded(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run ``fn(*args, **kwargs)`` in the worker process; fall back in-process on a pool failure.

    ``fn`` must be importable by qualified name (a module-level function) and its arguments + result
    picklable — true for the engine's SRA computes (frozen dataclasses + pydantic models). The
    function's own exceptions propagate unchanged; only pool failures fall back in-process.
    """
    ex = _executor()
    if ex is None:
        return fn(*args, **kwargs)
    try:
        future = ex.submit(fn, *args, **kwargs)
    except Exception:  # pragma: no cover - submit rarely fails synchronously
        return fn(*args, **kwargs)
    try:
        return future.result(timeout=OFFLOAD_TIMEOUT_S)
    except FuturesTimeoutError:
        # ADR-0261 P5: never hang forever. The worker may be wedged mid-solve — tear the pool
        # down (a fresh one spawns lazily on the next call) and surface an actionable error;
        # deliberately NOT the in-process fallback, which would just hang the server instead.
        future.cancel()
        _reset()
        raise RuntimeError(
            f"The computation exceeded {int(OFFLOAD_TIMEOUT_S // 60)} minutes and was stopped. "
            "A smaller population (filter/target), fewer iterations, or excluding completed "
            "activities will run faster."
        ) from None
    except BrokenExecutor:
        # the pool itself died (worker crash / un-picklable arg), NOT the function's own error —
        # drop the broken pool and run this call in-process so the request still succeeds
        _reset()
        return fn(*args, **kwargs)


def run_maybe_offloaded(offload: bool, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Offload only when ``offload`` is true (a heavy schedule); else run in-process directly."""
    if offload:
        return run_offloaded(fn, *args, **kwargs)
    return fn(*args, **kwargs)


def shutdown_offload() -> None:
    """Tear down the worker process (called on app shutdown; a no-op if none was started)."""
    global _disabled
    _reset()
    with _lock:
        _disabled = False


# Safety net: the explicit teardown is wired only to the Quit route (/api/shutdown), but the
# browser-gone watchdog and any other non-graceful exit skip it. Registering the pool teardown with
# atexit guarantees the worker process is reaped on ANY interpreter exit (audit L3). ProcessPool has
# its own atexit join, but this also cancels queued futures and drops our handle deterministically.
atexit.register(_reset)
