# ADR-0293 — Probe the native-`.mpp` capability once per ingest, ahead of the I/O

- **Status:** Accepted
- **Date:** 2026-07-25
- **Supersedes / amends:** none (perf backlog item 5 of 7, opened by ADR-0281)
- **Related:** ADR-0193 (deployed `tools/mpxj` layout), ADR-0249 (measure-don't-hand-wave),
  ADR-0289 (bounded-concurrency upload pre-read), ADR-0292 (order-dependent measurements lie)

## Context

Perf backlog item 5 was recorded as "an MPP capability probe" and nothing more. The first job was
therefore to find out whether the item names a real cost — and where.

Native `.mpp` has no Python reader, so every conversion needs two things to exist on the machine:
the vendored MPXJ runner (`tools/mpxj/classes/MpxjToMspdi.class`) and a JRE. Both were located
**per file**, and in the web upload path the JRE lookup happened only *after* the file's bytes had
been written to a temp path for the (never-to-be-spawned) subprocess to read.

### What the measurement actually said

All numbers below are from this sandbox against the committed reference `.mpp`
(`00_REFERENCE_INTAKE/Project2.mpp`, 691,712 B) with a warmed page cache. Per ADR-0292, every
comparison is interleaved and repeated — *if the answer depends on measurement order, you are
measuring the wrong quantity.*

| Quantity | Measured |
| --- | --- |
| `_find_java()` calls, 8-file `.mpp` ingest, one-shot path | **8** (plus 9 `_mpxj_home()`) |
| Cost of one `_find_java()` (wide-scan case) | **~0.3 ms** |
| `/upload` of 16 `.mpp`, no JRE on the machine | **16 temp writes, 3,200,064 B** written then discarded |
| Batch JVM boot to `READY` | **0.05 s** |
| First MPXJ conversion in a JVM | **~1.35 s** (in-JVM classload/JIT warm-up) |
| Each subsequent conversion | **~0.15 s** |
| `/upload` entry → first conversion starting | **0.097 s** |

Three of those readings changed the plan, and two of them **killed** a hypothesis:

1. **Discovery is not a wall-clock problem.** The obvious reading of "capability probe" is
   "memoise the expensive JRE scan." At ~0.3 ms a call, that is worth nothing. Doing it anyway,
   process-wide, would have added a stale-cache hazard in exchange for microseconds.
2. **A background pre-warm of the JVM is not worth building.** The whole window between the upload
   request arriving and the first conversion starting is **97 ms** — there is nothing to overlap
   the 1.35 s MPXJ warm-up with. Rejected on measurement, not on taste.
3. **The batch JVM is not slower for a single file.** A first, order-dependent reading said the
   persistent-server path cost 2.99 s at N=1 against 1.58 s for a one-shot — a 1.4 s regression on
   the *most common* case. Interleaved and repeated, the truth is **1.52 s vs 1.49 s at N=1** and
   **2.71 s vs 11.74 s at N=8**. The first reading was cold page cache on the MPXJ jars. Exactly
   the ADR-0292 failure mode, caught the same way.

**The cost that survived measurement is I/O, not CPU:** on a machine that cannot convert `.mpp` at
all — no JRE, or a deployment missing `tools/mpxj` — the upload path materialises every file to
disk before finding out, once per file, that no subprocess will ever read it. 16 files cost 3.2 MB
of write-then-delete; the operator's real files are ~10 MB each, so a 500-file folder is ~5 GB of
pointless writes on a laptop disk that may be BitLocker-encrypted or OneDrive-synced.

## Decision

Answer the question once per ingest, before the work.

- **`MppCapability`** — a frozen `(mpxj_home, java, reason)` record. `reason` is empty exactly when
  the capability is available and otherwise carries the *same operator-facing text the conversion
  path has always raised*.
- **`probe_mpp_capability()`** — the single place that resolves runner + JRE. The runner is checked
  **before** the JRE, preserving the precedence the conversion path always reported: a broken
  deployment names itself rather than blaming a JRE it never got far enough to need.
- **`mpp_capability()`** — returns the probe cached on the active `mpxj_batch_session()`, else a
  fresh probe. `_build_command` / `_try_start_server` / `_convert_one_shot` take the capability
  instead of re-resolving; `parse_mpp` and the upload path's `.mpp` branch gate on it up front.

### Why the memo is scoped to the ingest, not the process

This is the whole reason the caching is safe. A process-wide memo would have to be invalidated when
the operator installs a JRE and retries — a stale "no Java here" answer that outlives the fix is a
worse bug than the one being solved, and it is exactly the class of bug this codebase keeps
re-learning (ADR-0281's "never another slightly-too-small LRU"). A batch session is one ingest;
the next upload re-probes. There is no invalidation problem because there is no long-lived answer.
The probe costs microseconds, so re-running it per ingest is free — the win being bought is the
**work it skips**, never its own speed.

## Consequences

- An N-file `.mpp` ingest resolves runner + JRE **once** — measured **(8, 9) → (1, 1)**.
- An upload that cannot convert writes **zero** bytes — measured **3,200,064 B → 0** at 16 files,
  linear in folder size.
- Both failure messages, and their order, are unchanged; a successful parse is unchanged (Law 2).
  `tests/importers/test_mpp_capability_probe.py` pins all of it, and 6 of its 7 tests fail on the
  pre-change tree.
- **Not done, deliberately:** the probe is not surfaced in the UI yet. A "native `.mpp` is
  unavailable on this machine — here is how to fix it" panel is the natural next use of
  `mpp_capability()`, but it is UI work and owes the `docs/DESIGN-SYSTEM.md` Definition-of-Done
  checklist (ADR-0195); folding it into a perf PR would smuggle a UI change past that gate.
- **Not done, on measurement:** background JVM pre-warm (97 ms of overlap available) and a
  process-wide discovery memo (~0.3 ms saved, stale-answer hazard bought).
