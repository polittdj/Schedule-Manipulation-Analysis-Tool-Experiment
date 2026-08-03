# ADR-0343 — The three UNSURE falsy-zero rows, settled by rendering the page

**Status:** Accepted · **Date:** 2026-08-03 · **Extends:** ADR-0306 (an absent figure is not a zero) ·
**Audit:** `audit/FALSY-ZERO-SWEEP-20260729.md` (the three UNSURE rows)

## Context

ADR-0306 closed the four **BUG** rows of the 2026-07-29 falsy-zero sweep and left three **UNSURE**
rows open. The sweep was explicit about why it could not settle them, and the reason was the same
for all three:

> "Whether that is a Law-2 fabrication depends on how the cell is rendered — I did not establish
> whether the surrounding template distinguishes 0 from '—'." … "I classify UNSURE rather than BUG
> only because I did not execute the rendered page."

So the only thing that could settle them was rendering the pages. This session did, and **both
surfaces fabricate.**

### Row 1 + 2 — `/cei`, `_work_piling_header` (`app.py` `planned`/`finished`)

`cei_planned` and `cei_finished` are `int | None`. `bow_wave.py` sets them — together with
`cei_period` — only inside its `lo <= period <= hi` block, which is reached only when the
**preceding** snapshot carries a status month. Two ordinary inputs miss it: a version series where
the prior file has no `<StatusDate>` (`order_versions` sorts undated files last, so the *newest*
snapshot's predecessor is undated too), and a series whose data date's following month falls outside
the profiled window.

`or 0` turned that absence into a measured zero, and the zero was consumed by an **unguarded**
`_status_stack` call. Rendered, with two undated versions loaded:

| Surface | What it said |
|---|---|
| takeaway `<h1>` | "**No month could be CEI-scored** across the 2 loaded versions" |
| KPI "Latest CEI" / "CEI month" | "—" / "—" |
| KPI "Planned that month" / "Finished that month" | "—" / "—" |
| the panel below them | "**Latest scored month**" · "Finished **0**" · "Short of plan **0**" · "**0 planned in the month**" |

One page, in one viewport, saying both. The KPI strip and the takeaway were already right; a single
panel contradicted them, and it is the panel that draws a *bar* — the surface an analyst reads as
measured.

### Row 3 — `/groups`, `_groups_breakdown_table` (`total = len(tasks) or 1`)

`group_values` scans **every** task, summary rows included, but the row's completion is computed
over `non_summary(group)`. A value carried only by rollup rows therefore arrives with an **empty**
population, and `or 1` supplied a denominator for a numerator that is also 0 — rendering `0%`,
i.e. *"nothing in this group is complete"*, in the cell beside a BEI cell already rendering `—` for
that same empty population. Measured on the committed goldens:

| Fixture | field | rows | empty-population rows rendering `0%` | honest `0%` rows |
|---|---|---|---|---|
| Project5 | WBS | 145 | **19** | 99 |
| Project5 | Activity Type | 2 | **1** (`Summary`, 19 activities) | 0 |
| Project2 | WBS | 145 | **19** | 106 |
| Project2 | Activity Type | 2 | **1** | 0 |

The first count taken was **118** — every row whose cell read `0%`. Re-deriving the population per
value cut it to **19**: 99 of those rows are honest zeros over real activities. A matching cell
value is not an identification.

## Decision

**Where the population is empty or the figure absent, the surface says so — it does not divide by a
fabricated denominator or draw a bar from a fabricated numerator.** This is ADR-0306's rule applied
to the presentation layer, and it is the rule `engine/metrics/dcma14.py` already applies to its own
denominators (`NOT_APPLICABLE if population == 0`). The sweep's own systemic note named the split:
*"the engine's metric layer gets the empty-population case right … the web presentation layer
reaches for `or 1` divisor guards instead."*

1. **`_stack_not_measured`** — a sibling of `_status_stack` that reuses the *same* panel shell with
   the bar replaced by a stated absence. One panel chrome, not two, and the panel keeps its place in
   the two-up grid so the sibling does not reflow into the gap. `_work_piling_header` calls it when
   either CEI figure is `None`, under the heading **"Monthly plan vs done"** — the old heading
   asserted a scored month.
2. **`planned`/`finished` keep their `None`.** The takeaway's guard gains
   `and planned is not None and finished is not None`; since `cei = round(done / planned)` is `None`
   whenever `planned` is absent *or* zero, the conjuncts cannot change which branch a schedule
   takes — they state the precondition the f-string already relied on. The two KPI cards now test
   the same locals they print rather than re-reading the source fields.
3. **The breakdown's completion cell** renders `<span class=muted>—</span>` when the non-summary
   population is empty, matching the BEI cell in its own row.

## Consequences

Verified by rendering the pages on both sides of the change and diffing (launch nonce normalised):

| Page | Result |
|---|---|
| `/cei`, golden pair (a month IS scored) | **byte-identical** |
| `/groups?breakdown=Critical`, `…=% Complete` | **byte-identical** (no empty-population value) |
| `/groups?breakdown=WBS` | 19 cells `0%` → `—`; the other 126 rows unchanged |
| `/groups?breakdown=Activity Type` | 1 cell `0%` → `—`; the other row unchanged |

No engine figure moves; no golden moves; `pytest -m parity` is unaffected — this is entirely a
presentation-layer change.

**`tests/web/test_absent_is_not_zero.py` (11 tests)** pins both halves of both fixes. Every
expectation is *derived* from the engine at test time (`group_values` / `non_summary`), not
transcribed, so a fixture change cannot leave the assertions quietly true; the module asserts the
whole-table invariant (*a percentage appears iff the value has a non-summary activity behind it*)
rather than sampling. Each fabricating branch is paired with its **true-positive twin** — the
goldens' really-scored month still reports `3 of 3` and CEI `1.00`, and the 99/106 genuinely-0%
WBS rows still read `0%`. A fix that stops inventing a zero must not also stop reporting a real one.

**Proved able to fail, once per surface, independently:**

| revert | result |
|---|---|
| `/cei` caller back to `or 0` + an unconditional bar | **2** fail — both `/cei`-unscored tests; the 9 others pass, including the scored twin |
| `/groups` caller back to `or 1` | **6** fail — the empty-population tests on both fixtures; the honest-zero twin still passes |

Neither revert fails the whole module, which is the point: N-of-N failing on a shared revert is also
what one test run N times looks like.

## Deliberately NOT done here

**The breakdown's "Activities" column still counts summary rows.** It renders `len(uids)` straight
from `group_values`, so the `Summary` row reads "19 activities" while its completion and BEI are
both `—`. That is a *count that includes rows the other two columns exclude* — a real inconsistency,
but a different one: fixing it moves a displayed population figure rather than removing a fabricated
one, and the honest reading ("19 activities carry this value; none of them are measurable
activities") is at least not a false statement about completion. Recorded, measured, and left for a
round that can weigh the column's contract properly.
