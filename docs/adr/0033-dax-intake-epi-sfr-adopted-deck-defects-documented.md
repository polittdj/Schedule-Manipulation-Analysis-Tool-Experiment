# ADR-0033 — DAX intake: EPI and Start-to-Finish Ratio adopted verbatim; deck defects documented

Date: 2026-06-12 · Status: accepted

## Context

ADR-0030 (M15) adopted the reference deck's measure set from its Layout, but three
measures were deferred because the `.pbix` DataModel is XPress9-compressed and their
DAX could not be read: **EPI**, **RatioMeasure**, **Start-and-Finish Ratio**. The rule
was *do not guess*. On 2026-06-12 the operator exported the deck as a Power BI Project
and deposited the **SemanticModel** (TMDL — all 122 measures in plain text; kept local
in `00_REFERENCE_INTAKE/`, never committed).

## Decisions

1. **EPI — adopted verbatim** (`completion_performance.epi`). Deck DAX:
   `(COUNT actual starts + COUNT actual finishes) / (COUNT actual starts + COUNT
   baseline finishes)`. One documented deviation: the tool's population is non-summary
   activities (the deck counts raw `Schedule` table rows, which can include WBS
   summary rows depending on how the table was loaded).
2. **Start-to-Finish Ratio — adopted verbatim**
   (`completion_performance.start_finish_ratio`). Deck DAX (model name: *"Start to
   Finish Ratio"*; the Layout binding spells it *"Start and Finish Ratio"*):
   `COUNT(rows with Start AND Finish) / COUNT(rows with Actual Start AND Actual
   Finish)`. NA-shaped (0 of 0) until the first activity completes.
3. **RatioMeasure — does not exist.** The semantic model contains no such measure
   (122 enumerated); the deck visual's binding is dangling. Nothing to implement;
   the PBIX reproduction spec is updated accordingly.

## Deck defects found during intake (documented, NOT adopted)

Reading the source DAX surfaced authoring defects in the deck — recorded here because
the operator cross-checks the tool against this deck:

- **`Current Execution Index` (deck)** divides `SUM(Baseline Finish)` by
  `SUM(Actual Finish)` — sums of **calendar date serial numbers**. The ratio of two
  date-serial sums is not an execution index; it hovers near 1.0 by construction.
  The tool's CEI keeps the metric dictionary's defensible definition
  (completed_on_time / forecast_to_be_finished per period — the bow-wave CEI).
- **`% Schedule Elapsed Since Latest Actual Finish` (deck)**: the variable named
  `LatestActualFinish` actually reads `MIN(Baseline Start)` — the earliest baseline
  start. The deck's measure is therefore "% of schedule elapsed since the project
  began". The tool's staleness metric implements what the *name* means (elapsed since
  the latest actual finish) and keeps it.
- **`SPI` (deck)** = `Schedule % Complete / % Schedule Elapsed…` — inherits the
  defect above; it is a crude %-complete-vs-calendar proxy, not an earned-schedule
  SPI. The tool keeps its EVM SPI and earned-schedule SPI(t).
- **`BEI` (deck)** = all actual finishes / all baseline finishes, with no data-date
  cutoff — a global ratio, not the DCMA BEI. The tool keeps the golden-verified DCMA
  BEI (finished by the data date / baselined to finish by the data date).

## Consequences

- The last *do-not-guess* deferrals from ADR-0030 are closed; the PBIX reproduction
  spec (`docs/PLAN/PBIX-VISUALS.md`) has no DAX-blocked items left.
- Where deck numbers and tool numbers differ on these four defective measures, the
  deck is the outlier — the brief/comparison surfaces should say so, with this ADR as
  the citation.
