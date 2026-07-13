# ADR-0212 — Robust completeness for the critical-path evolution burn-down

## Status

Accepted. Operator directive 2026-07-13 (while using the tool): "verify that … 'Completed on the
path — version to version' accurately reflects all of the activities that would be [on the] driving
path to the selected UID … on all versions. This has to be correct. Check everything and assume
nothing and verify everything."

## Context

The Critical-Path Evolution chapter (`/evolution`) renders a **"Completed on the path — version to
version"** panel: for each consecutive version pair, the activities that were on the go-forward
driving/critical path in version N and are done by version N+1 — "the work that actually burned down
the driving chain each period." A read-only trace of `engine/path_evolution.py` confirmed the
structure is sound (each version's path is recomputed independently; activities are matched across
versions by `unique_id` only; membership is version N, completion is version N+1) — **but** it decided
"complete" with the **strict** `Task.is_complete` (`percent_complete >= 100`) alone, at three points:
the go-forward path membership filters, the `completed_on_path` set, and the `_classify_left`
"completed" reason.

Everywhere else that the same page (and the app at large) judges completion, it uses the **robust**
ADR-0051 rule — `percent_complete >= 100` **OR** a stored `actual_finish` — including the stepper's
"complete" shading, the hide-completed filter, the `/api/evolution` `complete` flag, and
`engine/sra.py`. So an on-path activity that finishes with a stored **actual-finish date but a stale
sub-100% percent** (exactly the status desync this forensic tool exists to surface) was shaded
*complete* in the stepper yet **omitted** from the "Completed on the path" table — an **undercount**
of the burn-down, contradicting the panel's own stated meaning. Because the path-membership filter was
also strict, such a task could even be reported as *staying on* the path while the stepper showed it
done.

The committed Project2/Project5 goldens contain **zero** tasks with this desync (verified: 0 of 145
in each), so every pinned evolution number is unaffected — the defect is latent on well-formed files
and only bites the anomalous progress data the tool is meant to catch.

## Decision

Apply robust completeness **locally inside `compute_path_evolution`** via a private
`_effectively_complete(task)` = `task.is_complete or task.actual_finish is not None`:

1. After each version's `critical` set is resolved (from `_target_path_set` when a "Measure to"
   target is set, else `effective_critical_set`), **drop any robust-complete task** — a stored actual
   finish means it has left the go-forward path.
2. `completed_on_path` and the `_classify_left` "completed" reason use `_effectively_complete`.

This keeps the panel's `entered / left / stayed / completed_on_path` sets internally consistent (a
finished-with-actual task now leaves the path and is counted as completed, never both "stayed" and
"completed"), and aligns the burn-down with the rest of the page.

**Deliberately NOT changed:** the shared, parity-locked `effective_critical_set` and the shared
`metrics/_common.is_incomplete` keep the strict `percent >= 100` basis. `effective_critical_set` feeds
the Acumen/SSI **parity** suite (`tests/parity/test_fuse_hardfile_parity.py`), the briefing, the
diagnostic brief, Ask-the-AI, the counterfactual, and change-effects; touching it would require
re-validating parity. Localizing the robustness to the evolution burn-down fixes the reported symptom
with zero parity blast radius. A broader "robust everywhere" pass over the shared critical set remains
possible future work (with its own parity re-validation).

## Consequences

- The `/evolution` "Completed on the path" table no longer undercounts a finished-with-actual-date
  activity; such an activity leaves the path and is attributed "completed" consistently with the
  stepper. No behavior change on schedules where percent tracks the actual finish.
- Goldens unchanged (0 trigger tasks): `test_golden_pins` still pins 41/4 critical, 38 left, 3 stayed,
  entered (131,), `completed_on_path` count 4. Fuse Hard_File parity unchanged.
- New regression `test_completed_on_path_counts_actual_finish_below_100pct` builds a crafted two-version
  chain where an on-path task gains an actual finish at 90% and asserts it leaves the path and is
  counted — the exact case the goldens don't exercise.
- Lesser observations from the same audit are **not** addressed here (kept out of scope): a counted
  100%-but-no-actual-finish row still renders "—" for Actual finish (honest); the panel's basis line
  can read "driving path to UID X" for a pair where the target is absent in the newer version (the
  `completed_on_path` values stay valid); and dropping un-CPM-able versions can collapse a period
  (a skipped-notice banner already discloses this).
