# ADR-0226 — Scale to thousands: SQLite cache + lazy summary tier + RAM estimate + batch JVM (v4 Feature 2)

## Status

Accepted. Second increment of the **SMAT v4** feature build (grouped ingestion → **scale/RAM** → NASA
margin → roles), one PR per feature. Feature 1 (ADR-0225) removed the file-count cap and added recursive
folder ingest + the Portfolio view, but still held every parsed schedule in RAM and booted a fresh JVM
per `.mpp`. This PR is the **performance layer** that makes a folder of thousands cheap — with **no
engine-math change and parity untouched**.

## Context

After F1 an operator can drop a whole recursive project folder on the tool, but three costs scaled
linearly and hurt at thousands of files:

1. **Re-parsing.** Every upload re-parsed from source — for a native `.mpp` that means a JVM subprocess.
2. **Re-computing the portfolio.** `/portfolio` ran a full CPM per project's latest version on every render.
3. **JVM boot.** A fresh `java` process per `.mpp` pays ~1s of boot each — thousands of boots for a big folder.

The red-team pass (ADR-0225) banked the enabling fact for this PR: pydantic `model_dump_json` round-trips
a `Schedule` **byte-deterministically** with an **identical** analysis — so a JSON blob is a safe, bandit-
clean cache format (no pickle / code-exec surface).

## Decision

- **SQLite parse+summary cache (`engine/cache.py`, std-lib `sqlite3`).** Keyed by
  **(file content hash, `engine_version`)**, where `engine_version` is **auto-derived** = a content hash
  of the `importers` + `model` + `engine` source, so ANY change that could move a number invalidates the
  cache — a stale cached answer can never reach the analyst (Law 2), and there is **no manual version to
  bump**. Schedule blobs are stored as `model_dump_json` (**not pickle**). Every operation **fails soft**
  (a missing/locked/corrupt entry degrades to a miss and the tool recomputes), per-call connections use
  **WAL + busy-timeout** (routes are threadpooled), and the DB lives **outside the repo**
  (`$SF_CACHE_DIR` else `~/.cache/schedule-forensics`) so a CUI cache file can never be committed and is
  **cleared on `/session/wipe`**. The upload route consults it before parsing (a re-uploaded file skips
  the JVM entirely) and a process-wide lazy singleton (`get_default_cache`) honors the test isolation dir.
- **Lazy summary tier (`engine/summary.py`).** A tiny `VersionSummary` (finish, effective margin, DCMA-14
  pass/fail counts, task count, status date) computed once from the full schedule and cached in SQLite by
  content hash. `SessionState.summary_for` reads it in-memory → on-disk before recomputing, so the
  Portfolio renders from summaries, not a fresh CPM per row, and survives a session restart. It is
  **scope-aware**: an active filter/target (which changes the numbers) bypasses the on-disk cache and
  computes over the scoped schedule, so a summary always **equals** the fully-computed row.
- **RAM estimate + configurable warning (`engine/memory.py`).** The tool keeps parsed schedules resident
  for instant comparative analysis, so a very large ingest has a real footprint. A conservative estimate
  (base + per-task, calibrated on the goldens at ~5.4 KB/task) surfaces on the Portfolio page and, when an
  ingest crosses the operator's threshold (default 16 GB, `POST /session/ram-threshold`), raises a
  **non-blocking** notice. Per the spec it **warns, never blocks** — the operator always proceeds. No
  change to the SRA offload pickling.
- **Persistent out-of-process batch JVM (`tools/mpxj/MpxjToMspdi.java` + `importers/mpp_mpxj.py`).** The
  vendored converter gains a `--server` mode: one heap-capped JVM (`-Xmx`, default 1g) reads
  `<in>\t<out>` requests and writes tagged (`@@SF@@`) status replies over stdin/stdout, converting a whole
  ingest in **one process** — still fully **out-of-process (no JPype)**. A per-request timeout via a
  reader-thread queue means a hung JVM can never block; one unreadable file is reported, never fatal. The
  Python side exposes `mpxj_batch_session()` (a ContextVar the upload loop opens); inside it every `.mpp`
  reuses the one JVM, and **any** server trouble falls back transparently to the existing per-file
  one-shot path — the parsed result is identical either way, and `parse_mpp`'s default (one-shot) behavior
  and all its tests are unchanged. The tag prefix makes the protocol robust to stray JVM/Log4j stdout noise.

## Consequences

- A re-uploaded file skips parsing (incl. the JVM); the Portfolio reads cached summaries; a folder of
  `.mpp` boots **one** JVM, not thousands. Browsing thousands is cheap; full schedules still materialize
  in RAM (the estimate/warning governs that), with true summary-only eviction a natural follow-up.
- **CUI at rest (local-only):** the cache holds parsed content + derived metrics on local disk — never the
  network, cleared on wipe, outside the repo (the pre-commit guard + the cache dir location enforce it).
- No engine/metric change; **parity untouched**. `tests/guards/test_egress.py` unaffected — no runtime HTTP
  client added (the batch JVM is still a local subprocess; numpy not added).
- Tests: cache hit == fresh compute + engine-version invalidation + corrupt/unwritable degrade-to-miss;
  upload re-upload is a cache hit + wipe clears the on-disk cache; summary == full analysis + JSON
  round-trip + unsolvable network; portfolio reads the in-memory and cross-session summary caches; RAM
  estimate monotonic + threshold configurable + non-blocking warning; batch JVM reuses one process +
  one-shot fallback when disabled + reports a bad file without hanging + an end-to-end folder upload
  reuses one JVM. Version 1.0.37 → 1.0.38; wheel + 9 installers in lockstep.
