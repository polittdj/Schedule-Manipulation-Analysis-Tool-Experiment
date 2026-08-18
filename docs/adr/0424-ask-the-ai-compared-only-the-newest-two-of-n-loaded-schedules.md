# ADR-0424 — Ask-the-AI compared only the newest two of N loaded schedules

- **Status:** Accepted
- **Date:** 2026-08-18
- **Supersedes / extends:** ADR-0392 (cross-version population facts), ADR-0150
  (manipulation-forensics facts), ADR-0371 (pair-scope populations)

## Context

Operator report, 2026-08-18:

> In the schedule integrity page when there are more than two schedules loaded into the tool the
> tool only does a comparative analysis of the last two schedules when you Ask the AI a question
> such as "When looking at the 32 schedules is there a pattern of schedule manipulation. Provide
> me the answer in the form of an email directed at a program manager and make it high level." I
> want it to do a comparative analysis of each of the schedules starting at the earliest and
> working its way forward to the latest two at a time. This doesn't just apply to the Schedule
> Integrity page but all of the Ask the AI sections on every page.

**Reproduced before any change.** A synthetic 4-version workbook was built from the Project5
golden with a duration halved in the FIRST update and again in the SECOND, leaving the newest pair
byte-identical in content. `build_workbook_fact_sheet` returned 27 facts:

- **zero** carried a manipulation signal;
- neither shortened activity (`Excavate elevator pit`, `Form column piers and spread foundations`)
  appeared anywhere in the evidence;
- 5 of 27 facts named more than one version, and 4 of those were ADR-0392's series facts;
- the only statement on the subject was
  *"No incomplete activity on the critical path had its duration shortened between v03.mpp and
  v04.mpp."*

That last line is the serious half. It is not merely missing evidence — it is an **affirmative
negative**, scoped to one of three available comparisons, that reads as a workbook verdict. A model
asked "across these schedules, is there a pattern of manipulation?" and given that evidence answers
"no" **correctly**, from what it was handed.

**Control (a differential probe needs a control expected to move).** Each early pair, compared
directly, yields 1 manipulation finding and 3 forensics facts; the newest pair yields 0 and 1. The
detector was never broken — nothing ever asked it about those pairs.

**Why ADR-0392 did not already cover this.** ADR-0392 made the population a fact and added the
S-curve and schedule-logic-finish **series** across every version. Those are *per-version* readings.
Manipulation is a **diff** signal: it exists only between two snapshots, so covering it needs the
*pairs* walked, not the versions read. The newest-two limit therefore survived ADR-0392 in exactly
the dimension the Schedule Integrity page exists for.

Two sites carried the limit, both feeding Ask-the-AI:

| site | code | reached by |
| --- | --- | --- |
| `qa.build_workbook_fact_sheet` | `prior, current = ordered[-2], ordered[-1]` | `POST /api/ask` |
| `qa.manipulation_forensics_facts` | `prior, current = ordered[-2], ordered[-1]` | `POST /api/ask` **and** `POST /api/ask/{name}` |

The report named the Schedule Integrity page, but the Ask panel is one shared component
(`chrome._ask_panel_html`, rendered by `_page` on every page). `/integrity` passes no
`ask_schedule`, so its panel defaults to the "Workbook — all N versions" scope and hits `/api/ask`.
The defect was every page's; the operator's "this applies to all of the Ask the AI sections" is
literally correct.

## Decision

Add a **consecutive-pair comparison series**: walk the workbook oldest to newest, two at a time,
running the full manipulation detector on **every** adjacent pair.

- **`engine/pair_series.py`** — `compute_pairwise_series(schedules, cpms) -> PairwiseSeries`, a
  series of `PairStep` rows (one per update) carrying that update's cited findings and what the
  computed finish did across it, plus `recurrence`: per signal type, how many steps fired it, its
  longest **unbroken run**, and how many findings it accounts for.
- **`ai/pair_facts.py`** — `pairwise_comparison_facts(...)`, stating that series as cited facts:
  a **pinned** `PAIRWISE COMPARISON SERIES` (every step enumerated), a **pinned**
  `MANIPULATION-SIGNAL RECURRENCE` tally, and bounded per-step detail facts.

Four design points, each paid for by a measurement:

1. **Recurrence is the answer to "is there a pattern".** One duration cut is an event; the same
   signal in 24 of 31 updates is a pattern. The facts state counts, runs and spans — arithmetic the
   reader can re-derive — and say explicitly that the tool asserts the counts and the changes
   behind them, **not why they were made**. The tool never asserts intent.
2. **Detail facts are allocated round-robin, oldest step first.** A "top N by severity" or
   "most recent first" cut would have rebuilt the newest-first bias being removed. Every
   signal-bearing step gets one entry before any step gets a second, and when the bound truncates,
   the series fact **says so**.
3. **Activities are named in the fact `text`, not only in the citations.** All three Ask prompt
   paths are assembled from `f.text` and never `f.rendered()`, so an activity living only in the
   citation tuple is invisible to the model — `"1 incomplete activities had their duration
   shortened"` reaches it with no way to say which.
4. **The diffs run on the PAIR population, never the scoped one** (see below).

`manipulation_forensics_facts` stays a **one-pair deep dive** — its per-change counterfactual
re-solves the network per detected change, which belongs aimed at the update under investigation,
not swept across the workbook. Its absence statements now name which comparison they are, out of
how many.

## The population trap this change walked into

The first working implementation put `pairwise_comparison_facts` inside
`build_workbook_fact_sheet`, which `/api/ask` calls with `_solvable_versions()` — the **scoped**
population, which a session Target UID truncates to the cone driving that target. The sweep runs
`detect_manipulation`, and ADR-0371 established that a *diff* on target-truncated populations reads
cone membership as file changes.

Measured on Project2 → Project5 with target UID 145 (109/108 tasks truncated vs 145/145 whole):

| | untruncated (control) | target-truncated |
| --- | --- | --- |
| `MANIP_DELETED_TASK` | *(none)* | **"13 activities deleted since the prior version"** (HIGH) |
| `MANIP_CONSTRAINT_ADDED` | present | **lost** |
| total signals | **5** | **5** |

A fabricated HIGH-severity finding, a lost real one — and **the total count is identical**, so a
count-based check is blind to both. `build_workbook_fact_sheet` therefore takes
`pair_schedules` / `pair_cpms` (the convention ADR-0371 already gave `build_briefing`) and the
per-version series keep the scoped population while the pair diffs take the unscoped one.

## The same defect class, found in this change's own first draft

`_series_fact` derived the version count as `len(steps) + 1`. An **uncomparable** pair removes a
step without removing the versions, so a 4-version workbook with one unsolvable file rendered:

> "PAIRWISE COMPARISON SERIES: **all 2 loaded version(s)** were compared … so this is the
> **complete set** of comparisons available in this workbook; **every update is here**…"

Four loaded, two claimed, and a completeness assertion that was flatly false — the same shape as
the affirmative negative this ADR exists to remove, written into the fix. `PairwiseSeries` now
carries `versions` explicitly, and the completeness sentence **retracts itself** when any pair was
uncomparable. Caught by re-reading the emitted text rather than the tests, all of which were green:
every one of them used a workbook where each pair compared, so `len(steps) + 1` was accidentally
right in every case that was exercised.

## Consequences

- A workbook question now has every update's comparison in evidence. On the operator's 32-schedule
  case that is 31 stated comparisons instead of 1.
- Single-file Ask scope also carries the series: scoping the panel to one file does not make the
  other versions stop existing.
- Cost is bounded and measured: 31 consecutive-pair diffs take **1.1 s at 5,000 tasks**
  (36 ms/pair) and 0.19 s at 1,000 tasks, reusing the CPM solves the routes already cache.
- The gate treats the new figures as **values**: a model writing "across the 6 loaded versions the
  tool made 5 consecutive comparisons; duration shortening fired in 2 of 5 steps" passes *strict*
  with zero unverified figures.
- `_SIGNAL_LABELS` is pinned by a **computed census** that reads the `MANIP_*` ids out of
  `manipulation.py` — a hand-maintained mirror of another module's constants goes stale silently.
- Law 2: a pair that cannot be compared is named in `PairwiseSeries.uncomparable`, never counted as
  a step with zero signals. "We could not look" and "we looked and found nothing" stay distinct.

## Verification

Red-before-green on the product itself (the 4-version probe above), then 37 tests across
`tests/engine/test_pair_series.py`, `tests/ai/test_pair_facts.py` and
`tests/web/test_ask_pairwise.py`. **Twelve mutations** were each confirmed to go red **by name**:
latest-pair-only · load-order instead of data-date order · an uncomparable pair counted as clean ·
`longest_run` returning the total · a dropped signal label · newest-first detail allocation · every
`pinned=True` removed · activities dropped from the fact text · the sweep routed through the
target-truncated population · both silence paths reverted to returning nothing · the version count
re-derived from the steps · the completeness claim left standing when pairs were skipped.

Two oracles were caught **blind** and rebuilt during that pass, both now carrying a control asserted
to move:

- the pinning test used a no-overlap question ("zzz qqq xyzzy"), which does not discriminate — the
  block sits directly behind the pinned population facts and so leads the ranked tail anyway. It
  now uses a question that fills the cap with genuinely-matching facts, plus a control that
  re-runs the selection with the pin removed and asserts the frame drops.
- the population test probed for the finding's own title, which the route's 12-fact response cap
  trims out; it now probes the compact label carried by the pinned facts, plus a control asserting
  the truncated populations really do fabricate.
