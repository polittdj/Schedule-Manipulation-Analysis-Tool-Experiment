# ADR-0126 — Offload the SRA Monte-Carlo to a worker process

## Status

Accepted.

## Context

Operator report: **"the Ask the AI feature freezes when trying to use it on the SRA page."** Two
causes were found.

1. **Client-side (fixed in #258):** the header globe doubles as the AI-status light; asking turns on
   `.ai-thinking`, which restarted `globe.js`'s stroke-heavy canvas animation for the *whole*
   generation. On the heavy SRA grid that pegged a CPU core and starved input. Fixed by throttling the
   spin to ~15 fps.

2. **Server-side (this ADR):** the SRA simulations — `compute_sra` / `compute_sra_ssi` (1000–2000 CPM
   passes) and `compute_oat_sensitivity` (one CPM solve per task) — are CPU-bound **pure Python**. In a
   FastAPI `def` route that work runs in the server thread-pool and holds the **GIL** the entire time,
   so a concurrent request on the same page (an Ask-the-AI call, the heartbeat) is starved until the
   simulation finishes. On a large schedule (the operator's ~1700-activity IMS) that is the multi-second
   "freeze". The simulation is user-initiated (a Run button), so the contention window is the time a
   user runs a sim and then asks a question.

## Decision

Dispatch the **heavy** SRA computations to a single, reusable **worker process** so they never hold the
server's GIL — `web/offload.py`:

- `run_offloaded(fn, *args, **kwargs)` runs `fn` in a lazily-created `ProcessPoolExecutor(max_workers=1)`
  and returns its result. The route thread blocks on the child's result (releasing the GIL) while the
  iterations run on the child's own interpreter, so concurrent requests proceed.
- `run_maybe_offloaded(offload, fn, …)` offloads **only when `offload` is true**. Each SRA route gates
  on `len(sch.tasks_by_id) >= OFFLOAD_TASK_THRESHOLD` (300): below it an in-process run is sub-second and
  the worker's spawn cost isn't worth it; large schedules (the ones that froze) clear it and offload.
- The five heavy call sites — `/api/sra` (`compute_sra`), `/api/sra/ssi` (`compute_sra_ssi`),
  `/api/sra/oat` (`compute_oat_sensitivity`), and the two SRA export routes — go through it.

**Determinism / parity is preserved.** The worker runs the *same* top-level engine function with the
*same* (pickled) inputs; the engine's seeded RNG (`random.Random(seed + i)` per iteration) does not
depend on the process, so the result is **byte-identical** to an in-process run. The byte-frozen
parity tests (`tests/engine/test_sra.py`) call `compute_sra` in-process and are untouched.

**Never a new failure mode.** If a worker can't be created or the pool dies (a frozen build without
spawn support, an OOM-killed child), the call **falls back in-process** — correctness never depends on
the pool. The *function's own* exceptions (e.g. `CPMError`) propagate unchanged so the route still
turns them into a 422; only pool-infrastructure failures (`BrokenExecutor`) trigger the fallback.

**Start method** is the interpreter default on purpose: on **Windows** (the deployed desktop target)
that is *spawn*, which is safe to start from the server's worker threads and runs the guarded launcher
cleanly; on **POSIX CI** it is *fork*, which the test suite relies on. `launcher.py` calls
`multiprocessing.freeze_support()` under its `__main__` guard for a future PyInstaller build. The worker
is torn down on Quit (`shutdown_offload()` in `POST /api/shutdown`).

## Consequences

- The SRA page no longer freezes a concurrent Ask-the-AI (or any other request) while a large
  simulation runs; the first heavy run on a session pays a one-time worker-spawn cost (~0.5–1 s),
  then the warm worker is reused.
- Still **std-lib only** (`concurrent.futures` / `multiprocessing`) — no new dependency, and the
  loopback / air-gap posture is unchanged (a local child process, no sockets, no network).
- No model change (`SCHEMA_VERSION` untouched, no schema-freeze update); engine numbers are unmoved.
- New tests in `tests/web/test_offload.py` pin: the worker runs in another process, byte-identical
  results, seeded-RNG determinism through the worker, the in-process fallback, the task-count gate, and
  the route wiring.

## Alternatives considered

- **Force a `spawn` / `forkserver` context everywhere.** Rejected: forcing spawn breaks pickling of the
  test-local helper functions on POSIX CI and adds a per-call re-import cost, while the platform default
  already gives spawn on the Windows deployment (where fork-from-threads would be the real hazard) and
  fork on Linux CI.
- **Lower the iteration count on big schedules.** Rejected: it would change the numbers (a fidelity
  regression in a testimony context) — Law 2.
- **Leave it in-process and only fix the globe.** Rejected: the operator explicitly asked to harden the
  server side so a running simulation can't slow a concurrent ask.
