# ADR-0155 — SSI Directional-Path options, Drag Analysis (ENGINE==SSI), Ribbon Insufficient Detail™ + status colors, per-page Excel exports

## Status

Accepted. The 2026-07-08 path-tools work order (second operator message of the day).

## Decisions

### 1. Drag Analysis — a new engine module, validated before pinning

`engine/drag.py` computes Devaux DRAG for every driving-path activity: capped by the
activity's **remaining** working duration and by the minimum driving slack of **concurrent**
activities (CPM windows overlap). Validated EXACTLY against the operator's SSI export before
any pin: all 20 Path-01 Drag values reproduce UID-for-UID — including the in-progress
remaining-duration cap (UID 35: 16 of 25 days) and the zero drag on both parallel zero-slack
pairs (60/61, 65/66). Gate: `test_ssi_drag_exact`; the `ssi_uid67` golden's drag map is
upgraded from provenance-only to gated. "Run Drag Analysis" appears on Path Analysis (adds
the Drag column live) and on the Driving Path page's Excel export.

### 2. SSI Directional Path Tool options in the engine

`compute_driving_slack` gains: **direction** (`PathDirection.PREDECESSORS` (default) /
`SUCCESSORS` / `BOTH`) — the successor trace runs the same link-gap propagation forward over
the descendant closure (algorithmically symmetric; the default remains byte-identical to the
parity-pinned behavior); **ignore_constraints** — re-traces on a `strip_constraints()` copy
(ASAP, no dates) with its own CPM; **ignore_leveling_delay** — traces on the recomputed
pure-logic CPM offsets instead of stored dates (SSI: "pretend that all activities have a
0 day leveling delay"). Either ignore option implies pure-CPM date arithmetic; both are
documented at the point of use.

### 3. Options in the UI, per page semantics

- **Path Analysis** (the target-relative SSI workspace) gets the full panel, mirroring the
  operator's SSI screenshots: Path Direction (Predecessors/Successors/Both), Dependency Range
  (Driving Slack ≤ x d / Get all dependencies), Ignore constraints, Ignore leveling delay,
  and Output (Waterfall / With Summaries / Separate parallel paths — the last from a server
  branch decomposition of the on-path set, `parallel_paths` in the payload).
- **Driving Path** (A→B corridor) and **Critical-Path Evolution** (paths to the finish/target
  over versions) are *directional by construction*, so they get the applicable subset: Ignore
  constraints + Ignore leveling delay (every version re-solved via `_optioned_versions`, with
  an explicit "Trace options active" banner), plus their Excel exports. Direction/range/output
  remain Path Analysis concepts there — documented in the form helper.

### 4. Ribbon: Insufficient Detail™ + status colors

The Bible formula (`SUM((OriginalDuration/(ProjectFinish-ProjectStart) > 0.1) * 1)`) was
already implemented and ENGINE==FUSE-pinned in `schedule_quality` (ADR-0151: P2=1, P5=0) —
the deferral reason ("pending the exact formula") no longer held, so the Ribbon now surfaces
it per file, sourced from the same single implementation. Thresholded measures color
green/yellow/red: quality-metric thresholds where published (5% LE family), DCMA
zero-tolerance for Negative Float and Leads, DCMA-05 5% for Hard Constraints; the yellow
"warning" band (PASS but ≥80% of threshold) is a labeled display convention. Unthresholded
measures stay neutral. Float Ratio™ alone remains omitted pending its formula.

### 5. Excel exports on every requested page

`/export/{fmt}/ribbon` is new (all measures × all files); the Path Analysis export now
threads every SSI option (incl. the Drag column) so the spreadsheet mirrors the on-screen
trace; the Driving Path page links the full-trace export; Evolution already had one.

## Consequences

- Parity fully preserved: default trace paths are byte-identical (32 driving-slack/parity
  tests + the full gate green); the new drag gate raises the SSI-validated surface to
  path-membership + slack + drag.
- The successor/both traces and the ignore options are engine-computed, never display tricks —
  each re-solve is labeled on-page so a screenshot can't be mistaken for the stored schedule.
