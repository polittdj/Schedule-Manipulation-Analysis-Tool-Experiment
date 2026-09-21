# ADR-0520 — Acumen Fuse's DCMA-09 is TWO metrics with TWO populations and a FIELD numerator: the forecast tile over the baselined INCOMPLETE activities, the actual tile over the baselined STARTED-OR-COMPLETE ones (R-79 CLOSED)

**Status:** Accepted · **Date:** 2026-09-21 · **Extends:** ADR-0280 (the parity population),
ADR-0367 (milestones inside the duration predicate), ADR-0518 (the Baseline Duration FIELD),
ADR-0519 (`population == 0` is the "no figure" carrier) · **Amends:** ADR-0283 (which scoped
DCMA-09 to the baselined population but left it one combined check) · **Supersedes:** the
`NOT_IN_BIBLE` verdict pinned for `DCMA09` in `tests/engine/test_aft_formula_audit.py` ·
**Closes:** audit row **R-79**

## Context

R-79 registered one arithmetic claim and one prescribed remedy. Both were written down and
attacked before the first edit (QC-3). The claim held and reached **much** further than the row.
The remedy **fell**.

### 1. The row's claim — right, and under-evidenced

The row said Large Test File2's "9. Invalid Forecast Dates" tile reads **322 / 0.36**, which
"reproduces only with 904" — the baselined-INCOMPLETE population — where the engine's parity mode
divides by every baselined activity (1,568 → 0.21), and named the 24-hour Hard_File's 1 / 0.08
with 12 (the engine's 84 → 0.01) as the second witness.

Both figures are correct. But the row's evidence was two ratios, and `322 / n → 0.36` only bounds
`n` to **[883..907]**. Sweeping **every** committed workbook for the tile — 43 of the 98
xlsx-shaped files in the intake carry it — produced eight non-zero (count, ratio) pairs, and
three of them sit on saves this repo holds and prior units matched by measurement:

| save | Fuse | `n` that reproduces | baselined-incomplete | every baselined | every incomplete |
| --- | --- | --- | --- | --- | --- |
| Large Test File2 | 322 / 0.36 | [883..907] | **904** ✓ | 1,568 ✗ | 998 ✗ |
| Hard_File_updated2 | 30 / 0.52 | **[58..58]** | **58** ✓ | 84 ✗ | 76 ✗ |
| 24-hour Hard_File | 1 / 0.08 | [12..13] | **12** ✓ | 82 ✗ | 19 ✗ |
| EVM1 | 8 / 1.00 | [8..8] | 8 ✓ | 8 — | 11 ✗ |

`Hard_File_updated2` pins the denominator **exactly and uniquely at 58**, which no other candidate
reaches. EVM1's 8 does not discriminate the completion filter (all 11 of its activities are
incomplete, so baselined and baselined-incomplete coincide) but it does pin the **field** count and
the baseline filter. The five TP4 versions and EVM2 reproduce too, but ADR-0518/0519 measured Fuse
to have scored **later saves** than the committed fixtures, so they are corroboration for the RULE
from Fuse's own displayed cells, never engine oracles.

### 2. The Bible says it out loud — and it was never read

The population is not an inference from ratios. Both committed `.aft` snapshots declare it, in
every `Metric` record, under `PrimaryFilter` / `SecondaryFilter` / `TripwireFilter`:

| metric | `IncludePlanned` | `IncludeInProgress` | `IncludeComplete` | ⇒ population |
| --- | --- | --- | --- | --- |
| `9. Invalid Forecast Dates` | true | true | **false** | **incomplete** |
| `9. Invalid Actual Dates` | **false** | true | true | **started-or-complete** |

…and the Remarks say the same in prose: *"Includes normal activities and milestones that are
**planned or in-progress**"* / *"…that are **in-progress or complete**"*. Both also carry
`IncludeNormal=true`, `IncludeMilestone=true`, `IncludeSummary=false` — the universal filter
ADR-0280/0367 already applies, whose duration predicate is the Baseline Duration FIELD (ADR-0518).

### 3. The FIELD count is readable in the formula

ADR-0283 recorded "Fuse's Metric History counts FIELDS, so its 42 = these 21 activities × 2" as a
**documented divergence** the tool would live with. It is not a divergence; it is the formula:

```
9. Invalid Forecast Dates  SUM((((EarlyStart<ProjectTimeNow) * (ActualStart="")) +
                                ((EarlyFinish<ProjectTimeNow) * (ActualFinish=""))) * 1)
9. Invalid Actual Dates    SUM(((ActualStart>ProjectTimeNow) + (ActualFinish>ProjectTimeNow)) * 1)
```

Each SUMs **two terms per activity**, so an activity whose stored start *and* stored finish both
precede the data date with no actuals contributes **2**. Large Test File2 displays 322 fields over
**170** activities. Fuse is right and the tool was wrong; the parity numerator now counts fields.
A field count may exceed its activity population — Fuse's own EVM1 tile is 8 fields over 8
activities, **1.00**.

### 4. The row's prescribed REMEDY fell

The row said to "scope the parity DCMA-09 denominator to the baselined-incomplete population".
That fixes the forecast side and **silently puts the actual-side count over the forecast
denominator**. Two populations cannot share one denominator, and the corpus proves they are
different: File2's actual tile is 4 / 0.01, which needs `267 < n ≤ 800`; the baselined-incomplete
904 prints 0.00, and the *unfiltered* started-or-complete 816 is outside the window while the
baselined 752 is inside. The split is not a preference; it is forced by the arithmetic.

The engine's own comment asserted the opposite — *"each date condition self-excludes the wrong
completion state, so the single combined loop reproduces Acumen's two separately-filtered
metrics"*. The **numerator** half of that is true and was re-verified (170 + 3 = the 173 the
combined loop produced). The **denominator** half was never true.

### 5. Two ribbons disagree, and the reason is measured, not asserted

`Large Test File vs Large Test File2 - Acumen Fuse Analysis Quick Add Metrics` and
`… - Acumen Fuse Quick Add Metrics ` read Large Test File2's forecast tile **0** where three other
workbooks read 322. They are neither a second metric (ADR-0519's trap) nor a second save. Measured over all 16
numbered tiles of both projects, the restricted pair is **never higher**, is strictly LOWER on
8 (Large Test File) and 11 (File2) of them (High Float 66 vs 814, Resources 66 vs 866, Missed
Activities 4 vs 1,115), and is equal only where the whole-schedule value is 0 — except one
equal NON-zero tile, the project-level scalar `13. CPLI` (0.97 / 0.59), which an
activity-population filter cannot move. That is the signature of the same save under a
**restricted activity filter**. They are excluded by name, and the oracle asserts the signature so the exclusion can
never decay into a bare claim.

## Decision

DCMA-14 check 9 becomes **two** `MetricResult`s, exactly as check 4 is already three
(`DCMA04_FS` / `_SF` / `_SSFF`). Both keys are present in **both** modes — a key set that varied
by mode would break every consumer that enumerates it.

* **`DCMA09` "Invalid Forecast Dates"** — the forecast terms alone. Parity: FIELD count over the
  **baselined incomplete** activities. Default: activity count over the full non-summary set.
* **`DCMA09_ACTUAL` "Invalid Actual Dates"** — the actual-date terms alone. Parity: FIELD count
  over the **baselined started-or-complete** activities; an empty population reports no figure via
  `population == 0` (ADR-0519's carrier), exactly as Fuse prints **N/A** for `Hard_File`, which
  carries no started or complete activity at all.
* Both remain scored on the file's **stored** start/finish dates (ADR-0176), with recomputed CPM
  only as the fallback for a file carrying no stored dates.
* `offender_uids` stays the **activity** list in both modes; the UI renders it under the literal
  label "N activities", so a field count of 322 beside 170 activities is honest.
* `scorecards.py`'s BP9 row reads BOTH halves and combines them the way BP7 already combines high
  float with negative float (PASS only when both pass, NA only when neither can be assessed).
* `tests/engine/test_aft_formula_audit.py`'s `DCMA09` row moves from **`NOT_IN_BIBLE`** to
  **`MATCH`**, and a `DCMA09_ACTUAL` row joins it. The Bible carried both formulas all along; the
  row said otherwise because nobody had looked.

## UNVERIFIED — recorded, not hidden

**The corpus does not determine the completion-state boundary.** Three forecast-side rules
(`is_incomplete` i.e. percent < 100 · no actual finish · percent < 100) and six actual-side rules
(actual start present · percent > 0 · either actual · and their unions with "complete") each
reproduce **16 of 16** Fuse tiles, and they disagree on **0** of the **8,190** activities in all
**24** committed fixtures. The engine uses the repo's DCMA convention (`is_incomplete`). The
mutation battery confirms it: mutating "started" from `actual_start is not None` to
`percent_complete > 0` leaves all 30 oracle tests **green**. The surviving mutant names the
unverified claim. What would settle it: a Fuse-scored save carrying a complete activity with no
actual start, or a started activity at 0 %. `tests/parity/test_fuse_invalid_dates_oracle.py`
pins the census at zero disagreement so the day a fixture discriminates, the guard says so.

## Consequences

* Parity reproduces both Fuse tiles exactly — **26 of 26** (workbook, label) pairs across six
  workbooks, every count and every ratio, plus the N/A.
* The split separated two defects the combined check had been conflating. TP3's old count of 5
  is 4 forecast-side (14 / 25 / 26 / 32 — stale stored forecasts) **plus 31 alone**, a completed
  task statused ten days into the future. Different finding, different remediation.
* Default-mode denominators are unchanged (both sides keep the full non-summary population); only
  the numerator splits, and the two counts still sum to the old combined count.
* `audit_schedule` now returns **17** checks, not 16.

## Deliberately NOT done

The five TP4 versions and EVM2 as ENGINE oracles (Fuse scored later saves; they remain evidence
for the RULE from Fuse's own cells) · the two restricted-filter ribbons as whole-schedule oracles
· a rounding decision for the ratio (the corpus contains **no tie** at 2 dp on either tile, so
half-up vs half-even is untested here and the display path is unchanged) · renaming `DCMA09` to a
`_FORECAST` suffix (it would break the golden case keys for no gain; the existing hardfile parity
pin already equates `DCMA09` with Fuse's forecast tile) · `Wrong Status` as a third engine metric
(the Metric History label maps to this family but reads 0 / 0 on both projects the export suite
carries, so it teaches nothing) · a status-date-less N/A moved onto the population carrier (that
case is "cannot be assessed", not "no population", and keeps `NOT_APPLICABLE`).
