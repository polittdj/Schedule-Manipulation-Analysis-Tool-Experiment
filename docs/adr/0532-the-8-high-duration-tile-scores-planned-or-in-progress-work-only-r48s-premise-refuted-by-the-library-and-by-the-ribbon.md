# ADR-0532 — The "8. High Duration" tile scores planned-or-in-progress work only: R-48's premise (`IncludeComplete=true` in the library) is refuted by the library itself and by a ribbon the repo already held (R-48 CLOSED)

**Status:** Accepted · **Date:** 2026-09-25 · **Extends:** ADR-0473 (R-48 registered: "the DCMA tile '8. High Duration' carries IncludeComplete=true in the library"), ADR-0518 (R-76: the tile is Fuse's Baseline Duration FIELD > 44 over the baselined-incomplete population — 87 / 927 and 86 / 904 on the Large Test File pair), ADR-0280 (the Acumen-parity DCMA population), ADR-0367 (milestones are not filtered as a class) · **Closes:** R-48

## Context — what the row said, and what the tree says

The register's R-48 row (ADR-0473, 2026-09-07) made three claims. Each was re-read from the
artifact this session, before anything else, because a register row's premise is testimony
(ADR-0530's lesson).

| The row's claim | Measured 2026-09-25 | Verdict |
| --- | --- | --- |
| the library's `8. High Duration` carries `IncludeComplete=true` | both entries (GUID `c6edc255` — Baseline Duration > 44; `eebc7193` — the EV variant against `Duration Upper Limit`) carry `IncludeComplete=false` in the PrimaryFilter AND the SecondaryFilter of BOTH committed snapshots (`NASA Metrics_Complete_20260423.aft`, `…_20260708.aft`), with `IncludePlanned` / `IncludeInProgress` = true, `IncludeMilestone` = true, `IncludeNormal` = true; their Remarks read "Includes normal activities and milestones that are planned or in-progress". Neither file has been edited since its upload (one commit each). Of the 60 Duration-named metrics, 25 do carry `IncludeComplete=true` — every one a completed-work metric (Missed Durations, Duration Ratio, Extended Durations, …); none is a High Duration metric. Each tile GUID occurs exactly once, inside its own `<Metric>`; the schema has no ribbon element that could override a filter | **REFUTED** — the origin of ADR-0473's reading is not recorded and was not reconstructed |
| DCMA08 scores incomplete activities only | `dcma14.py` builds `incomplete` (pure mode) and `ap_inc` (parity mode, baselined incomplete) and scores the tile on those; on ten progressed goldens no offender is a completed activity, in either mode | **held** |
| no Fuse figure in the repo discriminates (every Hard_File ribbon reads 0) | true of Hard_File — no snapshot carries a completed activity with a Baseline Duration field over 44 days (0 / 0 / 0 / 0 / 0). FALSE of the Large Test File pair, whose Analyst ribbon has been pinned since ADR-0518: Large Test File carries **77** completed activities with the field over 44 (UIDs 6337, 6116, 6543, 6544, 6545, 6546, 5770, 3905, …; 642 completed activities with a field over 0), Large Test File2 **78** (664). A tile admitting completed work would print **164 / 1,569** and **164 / 1,568** (0.10 / 0.10); the ribbon prints **87 / 927** and **86 / 904** (0.09 / 0.10). The COUNT separates the readings on both files; the two-decimal ratio on the first only | **REFUTED** — the row was written eleven days before the pin that answers it and was never re-read |

A third file is in the same class with no ribbon to read: Project5's completed UID 17 (60
baseline days) — the engine's tile reads 0 there in both modes, the inclusive reading would be
1 / 126; the AlltheProjects ribbon carries the Quick-Add metrics, not the DCMA tiles.

## Decision

1. **R-48 is CLOSED as refuted. No engine change.** The tile already scores planned-or-in-progress
   work only, as the library says and the ribbon shows.
2. **The finding is pinned**, so the premise cannot be re-registered from memory:
   `tests/parity/test_r48_high_duration_complete_oracle.py` (15 tests) —
   * the library: every `8. High Duration` entry of every committed `.aft` carries
     `IncludeComplete=false`, `IncludePlanned` / `IncludeInProgress` = true, `IncludeMilestone` /
     `IncludeNormal` = true in BOTH filters, and Remarks naming "planned or in-progress"
     (parametrized per library file; the predicate is a named helper so a mutated copy can be
     judged by the same code);
   * the ribbon: read at test time from the Analyst Quick-Add workbook, its count equals the
     engine's parity DCMA08 count and its ratio the engine's at two decimals; the fixture carries
     at least one completed activity with the field over 44; the inclusive count differs from the
     ribbon's on both files and the inclusive ratio on at least one;
   * the census: on ten progressed goldens no completed activity is a DCMA08 offender in either
     mode; Project5's UID 17 is recorded as the discriminating class beyond the ribboned pair.
3. **The register row and §1's tier-1 sentence are corrected** to say what was refuted and by what.

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| A1 | the library says `false` | every `8. High Duration` block × both filters × both snapshots, by regex and by `ElementTree` | **held** — 2 × 2 × 2, all `false` |
| A2 | no ribbon-level filter override exists | GUID occurrence census (each once, inside its Metric block); the schema's element names (no ribbon element); `git log` on both files | **held** |
| A3 | the ribbon discriminates | count completed activities with the field over 44 on the pair; compare 87 + 77 / 86 + 78 with the pinned counts | **held** — 164 ≠ 87 and 164 ≠ 86; the 2-dp ratio ties on File2 (0.10 either way), so the count is the discriminator there |
| A4 | "completed" (percent 100) is what Fuse calls Complete | the same census keyed on `actual_finish` instead | **held on this corpus** — 77 / 78 either way; UNVERIFIED at a margin the pair does not carry |
| A5 | the engine's offenders carry no completed activity | the census over ten goldens, both modes; then `is_incomplete` patched in memory to admit completed work | **held** — and the mutant is red by name: 164 against the ribbon's 87, three leak censuses, Project5's 1 against 0 |

## Consequences

* No reported figure moves. The row's own "first executable step" — a Fuse ribbon on a file with a
  completed activity of baseline duration > 44 d, pinned at whichever it reads — had been executed
  by ADR-0518 without anyone noticing it answered R-48. **A register row is not re-read when the
  evidence that settles it lands elsewhere; the row must name the oracle it waits on, and a session
  that pins an oracle must grep the register for the rows it answers.**
* The `IncludeInDCMA=false` flag on both tile entries is noted, not interpreted: the tile prints
  on the DCMA ribbon regardless, and no figure this session read depends on it.

## Verification

* **Red-first by mutation (the module is green on the pristine tree by construction):** M1 —
  `dcma14.is_incomplete` patched in memory to admit every activity: 5 of 15 red by name (the
  ribbon test 164 vs 87; the leak census on Large Test File, File2 and Project5; Project5's count
  1 vs 0), the library pins green. M2 — a scratch copy of the July library with one
  `IncludeComplete` flipped to `true` inside the first tile block: the shared predicate red naming
  `c6edc255` / `PrimaryFilter` / `IncludeComplete: true`; the control call on the committed file
  passes.
* **Green:** the module 15 / 15 on the tree; `tests/parity/test_fuse_duration_fields_oracle.py`'s
  87 / 927 and 86 / 904 pins unchanged.

## Deliberately NOT done

* No engine change — there was nothing to change.
* The origin of ADR-0473's `IncludeComplete=true` was not reconstructed; the two files it could
  have read both say `false` and have never changed.
* Project5's UID 17 is recorded, not oracled: no Fuse ribbon for that fixture carries the tile.
* The `IncludeInDCMA=false` flag on the tile entries — observed, left alone.
