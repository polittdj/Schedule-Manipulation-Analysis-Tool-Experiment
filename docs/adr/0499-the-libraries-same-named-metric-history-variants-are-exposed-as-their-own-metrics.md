# ADR-0499 — The library's same-named Metric History variants are exposed as their own metrics, each naming the filter that makes it a different metric (R-50 CLOSED)

- **Status:** Accepted — 2026-09-16 (audit roadmap §3, R-50, worked as its own unit).
- **Version:** 1.0.267
- **Extends:** ADR-0473 (which recorded the finding and the three figures), ADR-0151/0152 (the committed non-CUI `.aft` Bible), ADR-0110 (the pinned formula table), ADR-0393 (QC-1 / QC-2).
- **Shipped:** `engine/metrics/schedule_quality.py` (three new `MetricResult`s), `engine/metrics/ribbon.py` (three `RibbonMetrics` fields + their drill sets), `engine/metric_catalog.py` (a new **Metric History** family), `web/help.py` (three dictionary entries + the three tiles' cross-references), `web/ribbon.py` (the **Metric History variants** panel), `web/app.py` (the ribbon workbook's last three columns), `docs/METRIC-DICTIONARY.md` (regenerated), `tests/parity/test_fuse_history_variants_oracle.py` (new), `tests/engine/test_aft_formula_audit.py` (three pins), `tests/engine/metrics/test_schedule_quality.py` (three filter units), `tests/web/test_ribbon_view.py` (four panel tests + two re-aimed guards).

## Context

The audit register has carried, since 2026-09-07 (ADR-0473):

> R-50 — the library's same-named Metric History variants — Insufficient Detail™ (incomplete, no
> milestones: 22 vs the tile's 43), Merge Hotspot (Predecessors >2) (planned only: 125 vs 156),
> Total # Predecessor Lags (planned only: 2 vs 5) — are not exposed; a reader of the History
> report cannot find them in the tool.

The tool knew about all three — three code comments say so in as many words — and exposed none of
them. An analyst holding a Metric History report and looking at the Schedule Quality Ribbon sees
the same NAMES carrying different numbers, with nothing on the screen to tell them the two are
different metrics rather than a defect in one of them. In a testimony context that is the worst
possible failure mode of a parity tool: it looks like a disagreement.

### What was measured, before anything was written

**The three variants are real library metrics with their own formulas.** The Bible
(`NASA Metrics_Complete_20260708.aft`, 5,427 `<Name>` values, 1,200 distinct) carries each as its
own `<Metric>`, and the discriminator is the `PrimaryFilter`, not the formula:

| Bible `<Metric>` | GUID | Formula (verbatim) | PrimaryFilter |
|---|---|---|---|
| `Insufficient Detail™` (Quality - Duration) | `c71b82fe…` | `SUM((OriginalDuration / (ProjectFinish-ProjectStart) > 0.1) * 1)` | Normal ✓ Milestone ✗ Planned ✓ InProgress ✓ **Complete ✗** |
| `Insufficient Detail™` (Schedule Quality — the tile) | `a80debf6…` | `SUM((OriginalDuration / (ProjectDuration) > 0.1) * 1)` | Normal ✓ Milestone ✗ Planned ✓ InProgress ✓ **Complete ✓** |
| `Merge Hotspot (Predecessors >2)` | `c5196e05…` | `SUM((NumberOfPredecessors+NumberofExternalPredecessors>2)*1)` | Normal ✓ Milestone ✓ **Planned ✓ InProgress ✗ Complete ✗** |
| `Merge Hotspot` (the tile) | `ec4ca664…` | same formula | Normal ✓ Milestone ✓ Planned ✓ InProgress ✓ Complete ✓ |
| `Total # Predecessor Lags` | `37c0df8f…` | `sum(numberoflags)` | Normal ✓ Milestone ✓ **Planned ✓ InProgress ✗ Complete ✗** |

**A trap this row paid for, recorded so no session pays it twice:** the `.aft` names metrics in
`<Name>` **elements**, never `Name="…"` **attributes**, and escapes the values (`&gt;`, `&amp;`).
An attribute regex returns **zero** for all three and reads exactly like *"these are Acumen
built-ins, not library metrics"* — a false negative that would have sent the unit down a path
where nothing could be pulled verbatim.

**Two corrections to ADR-0473's wording, both measured:**

1. **`IncludeMilestone` is not the discriminator for Insufficient Detail™.** ADR-0473 (and the
   comment it seeded in `schedule_quality.py`) says the variant is `IncludeComplete=false` **and**
   `IncludeMilestone=false`, which reads as though the tile were `IncludeMilestone=true`. It is
   not: **both** entries are `IncludeMilestone=false` in their `PrimaryFilter`; only the tile's
   (unused) `TripwireFilter` carries `true`. The discriminator is `IncludeComplete` alone. The
   filter is still applied here explicitly — a 0-duration milestone can never clear the 10% bar,
   but a milestone carrying a duration could, and the exclusion is the library's, not an accident
   of the data.
2. **The register's "2 vs 5" is "2 vs 8".** The tool's `Number of Lags` tile reads **8** on the
   Large Test File and 8 on File2 (measured: `number_of_lags.count`), not 5. And the two are not
   the same *unit*: the Bible's own Description for `Total # Predecessor Lags` is *"Total number of
   predecessor **relationships** with lags in the schedule"*, so it counts **links**, where the
   tile counts distinct **activities**. On this file the reference tool's `Activities w/Lags on
   Predecessor` row also reads 2, which is what makes the link/activity distinction invisible in
   the totals and visible only in a synthetic case.

### The oracle, and why it can refute rather than agree

Nothing in the engine produced any expected figure. Both sides of every comparison come from the
operator's own vendor workbooks:

* `Large Test File vs Large Test File2 - Acumen Fuse - Detailed Metric Report.xlsx` carries **one
  column per metric** (name in row 11, group in row 10) with an `X` on every activity the metric
  counted, the activity's UniqueID in column D, Fuse's total in row 12 and its **Record Count** —
  the rows that contribute a term to the aggregate — in row 14.
* `… - Acumen Fuse -Metric History Report.xlsx` carries the same three figures as labelled rows.

The two vendor reports are cross-checked **against each other first** (a transcription slip in
either is caught before the engine is judged), and only then is the engine asked to reproduce the
mark set **by UniqueID**, the count, and the population. Columns are addressed **by metric name**,
never by index: a column that moves in a re-export is a missing-label failure, not a silent read of
the neighbour.

| Metric | Large Test File | Large Test File2 |
|---|---|---|
| `Insufficient Detail™` variant | **22** of a 945 population | **21** of 919 |
| `Merge Hotspot (Predecessors >2)` | **125** of 916 | **123** of 906 |
| `Total # Predecessor Lags` | **2** links, carried by 2 activities | **2** links, 2 activities |
| (for contrast — the tiles) | 43 · 156 · 8 | 40 · 155 · 8 |

The engine reproduces **every mark, by UniqueID, on both files**, and its populations equal Fuse's
own Record Counts to the unit — a check the rule did not get to choose, because the Record Count is
in the vendor's file and is not derivable from the totals.

## Decision

Publish each variant as its own metric, under the library's own row label **with the filter in the
name**, so a figure read off a Metric History report can be found in the tool and the two can never
be read across:

* `insufficient_detail_history` — **Insufficient Detail™ (incomplete, no milestones)**
* `merge_hotspot_predecessors_gt2` — **Merge Hotspot (Predecessors >2, planned only)**
* `total_predecessor_lags` — **Total # Predecessor Lags (planned only)**

They ride the existing metric machinery rather than a parallel one: `compute_schedule_quality`
computes them (single formula, one place), `RibbonMetrics` carries them, `ribbon_offender_map`
drills them to the activities behind the figure, the metric catalog lists them, the help dictionary
defines them (so the column header's ⓘ call-out states the filter), the ribbon workbook exports
them, and the three same-stemmed tiles now name their variant in their own definitions.

**They get their OWN panel, not three more ribbon columns.** The Ribbon and the Metric History are
different reports; a reader who finds a tile and its variant side by side in one matrix is being
invited to make exactly the comparison this row exists to prevent. The panel says so in its
explainer — *"A tile and its variant will normally disagree — that is the point, not a defect."*

**Thresholds are the library's, not invented.** All three Bible entries carry colour bands with
`Fail=false`; `Insufficient Detail™`'s bands are identical to the tile's (0 / 0.05), so the variant
inherits the tool's existing 5% treatment of that same published threshold, and the other two stay
`NOT_APPLICABLE` exactly as their tiles do. The cells speak the **existing** ribbon tooltip
vocabulary through the shared `_ribbon_cell_class` / `_ribbon_cell_title` — never a second tooltip
system.

## Consequences

**Verified.**

* **Red first, by name.** `tests/parity/test_fuse_history_variants_oracle.py` failed **8 of 11** on
  the pristine tree (the three green were the vendor-report cross-check, which must pass without
  the engine): *"`Insufficient Detail™` is not exposed as its own metric — a reader of the Metric
  History report cannot find its figure (22) in the tool (R-50)"*. Two standing coverage guards
  went red on their own as the metrics appeared —
  `test_every_emitted_metric_is_documented` (all three undocumented) and
  `test_audit_covers_every_documented_metric` — and were satisfied by documenting, never by
  narrowing.
* **Mutation battery 14 of 14 red BY NAME**, on a shadow copy of `src/` with a `-p mutcheck`
  plugin asserting the modules measured ARE the copy: M1 keep milestones · M2 keep completed ·
  M3 merge-variant all statuses · M4 threshold `>3` · M5 lags count activities not links ·
  M6 lags drop the planned filter · M7 population = all tasks · M8 the oracle addresses a column by
  the wrong label · M9 the page drops the panel · M10 the drill map loses the keys · M11 the export
  drops the columns · M12 the help entry removed · M13 the pinned NASA formula altered · M14 the
  panel loses its row labels. **M11 SURVIVED the first pass** and the survivor was a hole in the
  *test*, not the code: it asserted the workbook carried the three HEADERS, and a header with
  nothing written beneath it survives the column being dropped from the row (the writer simply
  emits a shorter row). The test now addresses each value by its own header's column letter.
* **Corpus census, 15 goldens, before vs after on a pristine `git archive HEAD` tree measured by
  the same script: 8,805 pre-existing values compared — `schedule_quality`, `RibbonMetrics`,
  every DCMA check with its citation UIDs, float bands, completion performance, and every task's
  six CPM values — ZERO moved, ZERO removed, 90 added** (exactly the six new keys × 15 goldens).
  The change is additive by measurement, not by assertion.
* **Rendered, not inspected.** `/ribbon` with the golden pair loaded, in a real Chromium, in all
  **four themes** (console / daylight / apollo / jarvis) at **1440 px and 390 px**: the panel
  exists exactly once in every combination, **document overflow is 0 px in all eight** (no sideways
  scroll added), each header carries its ⓘ definition call-out, and clicking a variant cell opens
  the existing drill — *"10 activities behind Merge Hotspot (Predecessors >2, planned only) —
  Project2.mspdi.xml"* — with UID / name / duration / % complete / start / finish.
* **The first full-suite run on the final tree found FOUR failures the targeted runs could not
  see** — every one a real consequence of this change, none an environment skip or a flake — and
  they were repaired before any push. The suite that found them: **5,475 passed / 4 failed / 7
  skipped in 37:23**. After the repairs the gate on the final tree is **5,479 passed / 0 failed /
  7 skipped in 39:48**, and **`-m parity` 131 passed / 0 failed in 5:43** — up from 120, a delta
  attributed rather than assumed: this unit's oracle collects **exactly 11** under `-m parity`.

**SIX guards were re-aimed in this commit, and every one of them had to be.** Two were found by
the targeted runs; **four more only by the full suite**, which is the reason the suite runs before
the push and not after it:

| guard | what it pinned | why the change moved it |
|---|---|---|
| `test_ribbon_row_labels_wear_the_left_edge` | row labels **page-wide** (2) | a second matrix over the same two schedules → now counted **per panel** |
| `test_ribbon_cells_carry_threshold_tooltips_never_re_judged` | every `.rib-cell`'s tooltip vocabulary | needed **no change** once the new cells used the shared title helper — the reason to reuse it |
| `test_catalog_shape_and_families` | `("DCMA-14", "Schedule Quality", "Float")` | the new **Metric History** family is deliberate (see above) |
| `test_api_workbench_matrix_is_chronological_and_validated` | the same family list **and** `len(metrics) == 21` | → 24; both pins kept, so a metric still cannot enter or leave unnoticed |
| `test_every_extracted_name_is_reexported_by_app_as_the_same_object[ribbon.py]` | the monolith-split contract | `_HISTORY_VARIANT_COLS` / `_history_variants_panel` now re-exported `X as X` |
| `test_panelkit_click_census_and_jarvis_probe_on_ribbon` | `.panel` count on `/ribbon` (4) | → 5, **and strengthened**: both matrices are now proved click-driven BY NAME, and the `[data-sf-big]` count is pinned at 2 so a third panel must force a decision rather than ride along unproved |

That last repair needed a DOM change: the two matrices share one `data-export` (one workbook, all
measures), so `.panel[data-export="/export/xlsx/ribbon"]` became ambiguous under Playwright's
strict mode. The variants panel carries `id=metricHistoryVariants` — a real anchor, not a
test-only hook — and the ribbon panel is addressed as the one that is *not* it. **M15: deleting
that id turns `test_panelkit_click_census_and_jarvis_probe_on_ribbon` red by name**, so the new
assertions have teeth like the other fourteen.

**Two of those six were page-wide counts, and had to be re-aimed rather than re-numbered.** Both read the WHOLE PAGE and were
under-specified the moment it grew a second matrix — the page-level twin of the phase-2 trap in
`CLAUDE.md`. `test_ribbon_row_labels_wear_the_left_edge` counted row labels page-wide (2) and now
counts them **per panel**, because a page-wide total of 4 cannot tell *"both panels label both
rows"* from *"one panel labels four rows and the other labels none"*; M14 proves the re-aimed
guard still has teeth. `test_ribbon_cells_carry_threshold_tooltips_never_re_judged` scans every
`.rib-cell` on the page and needed no change once the new cells used the shared title helper — the
reason to reuse it rather than write a second vocabulary.

**What this does NOT claim.** The three variants are pinned on the Large Test File / File2 pair,
the only files in the corpus whose Detailed Metric Report carries these columns. No Hard_File or
Project2/5 Fuse export scores them, so their figures on those goldens are the engine's own and are
unpinned. `Critical w/Insufficient Detail™`, `Merge Hotspot w/Predecessor Lags`, the successor-side
lag family and `Max/Min Predecessor Lag (days)` are further same-stemmed library metrics that
remain unexposed; they were out of R-50's scope and are named here so a later row can price them.
