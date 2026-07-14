# ADR-0218 — Click-to-drill on the Performance G2/G4 and CEI monthly bars

## Status

Accepted. Operator directive 2026-07-13: extend the categorical count-bar drill (ADR-0217) to "all
other bars in the tool" — the last two families deferred there because they touch parity-relevant
engine accumulators: the Performance-Summary G2 late buckets / G4 workoff-burden bars, and the Bow
Wave / CEI monthly finish bars.

## Context

ADR-0216 made the per-activity bars drillable and ADR-0217 the dashboard / WBS / trend count bars. Two
families were held back because their engine payloads carried only per-month **counts**, not the
activity-ID lists `_workbench_drill_rows` needs, and the accumulators that build those counts are the
same ones the Acumen-validated CEI parity (`24/129`, `1/6` EXACT) and the reference-workbook G2/G4
figures depend on. This ADR wires them, additively, without touching any count.

## Decision

For each family, add a **parallel UID accumulator** that is appended in lockstep with the existing
count increment — same predicate, same branch, same index — so a segment's UID-list length always
equals the count it accompanies, then tag each bar `rect` with `SFDrill.mark(...)`:

- **Performance G2 late buckets** (`FlowMonth` → `activity_flow`): six new per-month `*_uids` fields
  (`started_late_30/60/over`, `finished_late_30/60/over`), appended beside each `late_s[b][i]` /
  `late_f[b][i]` count. The shared `stackedBars` builder in `performance.js` now reads
  `r[key + "_uids"]` per segment and drills to the version's own file label.
- **Performance G4 workoff burden** (`BurdenMonth` → `workoff_burden`): twelve new `*_uids` fields, one
  per category. Backlog is a **negative** count mirrored below the axis; its UID list carries `|count|`
  activities (the same not-done work). `BurdenMonth` is now constructed field-by-field (a `**dict`
  splat no longer type-checks once the dataclass mixes `int` and `tuple` fields).
- **CEI monthly bars** (`SnapshotProfile` → `compute_bow_wave`): three new per-month UID-list fields
  (`baselined_uids` / `scheduled_uids` / `finished_uids`), bucketed by a `_bucket_uids` helper that
  mirrors `month_axis.bucket` exactly (dates outside the axis window are dropped, so the UID count
  equals the bar count). `cei.js` tags each grouped monthly bar with the activities finishing in that
  month for that series. The drill's `data-file` is the snapshot's own label.

## Consequences

- The Performance late-bucket / workoff-burden bars and the CEI monthly finish bars now open the same
  activity grid (filter / add-columns / Excel) as every other bar in the tool — the operator directive
  is fully satisfied.
- **Presentation only — no metric changed (Law 2).** Every UID list is derived with the *same
  predicate as the count it accompanies*; the CEI parity gate and the reference-workbook G2/G4/G5
  figures are byte-identical (parity suite green). The engine touches are additive `*_uids` fields on
  three frozen dataclasses, all defaulted, so no existing constructor breaks.
- Tests assert the invariant directly: on the hand-checkable synthetic fixtures, each `*_uids` list
  equals the exact activities behind its count (and `|count|` for the negative backlog), and the
  Performance-page blob + `/api/cei` payload carry the lists and resolve through the drill API.
- **Multi-version caveat (unchanged from ADR-0217):** `_workbench_drill_rows` resolves the **scoped**
  analysis and drops UIDs absent from the resolved version, so an active group/filter can thin a bar's
  drilled list; each bar's `data-file` is its own version, so this only bites under an active filter.
