# ADR-0030 — M15: `.pbix`-informed enrichment (float bands, completion performance, MEI, the three-method finish forecast)

- **Status:** accepted
- **Date:** 2026-06-12
- **Drivers:** the operator deposited `NSATDeploymentRevisionAlpha.pbix` (the externally-gated
  M15 input, R-12). Requirement (intake item 1 / build prompt §6.A): extract the deck's
  **extra metrics and how they're calculated** and its **example visuals**, and **expand /
  improve** on them in the tool.

## How the deck was read (CUI handling)

The `.pbix` lives in `00_REFERENCE_INTAKE/pbix/` — **git-ignored, local-only, never
committed or quoted**. It was read in-session with the standard library only (`zipfile` +
the UTF-16 `Report/Layout` JSON): 14 report pages, ~120 visual containers, and the measure
references each visual binds were enumerated. The **DataModel is XPress9-compressed**
(self-identified in its header) — no stdlib decoder exists, so the **DAX bodies were not
extractable**. Every adopted measure is therefore a **documented reconstruction** from its
name, its visual context, and standard industry definitions; the metric dictionary states
each formula (source tag: "Reference Power BI deck measure, reconstructed"), and committed
artifacts carry no deck content beyond generic scheduling vocabulary.

## What was adopted (and improved)

1. **Float bands** (`engine/metrics/float_bands.py`, deck "Float Analysis" page): incomplete
   work at **0 / < 5 / < 10 working days** of total and free float — counts + shares,
   cumulative bands, band edges on the schedule's own calendar (ADR-0027/0028), offender
   UIDs attached (§6; the deck's cards cite nothing). The 0-day total band reproduces the
   Acumen "Critical" parity counts (41/37) — a built-in cross-check.
2. **Completion performance** (`engine/metrics/completion_performance.py`, deck "Metrics" /
   "Completion Metrics" pages): completed-work split **ahead / on schedule / behind**
   baseline; **average days ahead / late / net variance** (calendar days, the Net-Finish-
   Impact axis); **longer / shorter than planned** and the **duration ratio min/avg/max**;
   **MEI** (Milestone Execution Index — BEI restricted to milestones, NA without due
   milestones); **% schedule elapsed since the latest actual finish** (staleness). Honest
   populations throughout (only activities carrying the needed dates; never a fabricated 0).
3. **The three-method finish forecast** (`engine/forecast.py` + `/forecast`, the deck's
   forecasting pages): the deck triangulates the end date three ways; the tool does the
   same with fully-specified methods — **(a) schedule logic** (the CPM finish), **(b)
   completion-rate extrapolation** (to-go count ÷ historical completions-per-month), and
   **(c) earned-schedule IEAC(t) = AT + (PD − ES) / SPI(t)** on the working-time axis
   (the existing SPI(t) machinery). A method with missing inputs shows **no date** — never
   fabricated. Improvements over the deck: a per-version **forecast-drift table** (the
   forecasts re-run across all loaded versions — sliding forecasts are the bow-wave
   signature), an explicit basis line per method, and the §6 citation anchor
   (finish-controlling activities).

Report page gains the float-band and completion-performance panels; `/api/analysis` carries
both families; `/api/forecast` serves the forecast set per version; 22 new metric-dictionary
entries (regenerated `docs/METRIC-DICTIONARY.md`).

## What was deliberately NOT adopted

- **Ambiguous measures** whose formulas cannot be reconstructed from name + context:
  `EPI`, `RatioMeasure`, `Start and Finish Ratio`. Implementing a guess would fabricate a
  formula (Law 2). If the operator exports the DAX text (Tabular Editor / copied measure
  definitions, per the intake instructions), they can be added exactly.
- **Already-covered ground**: BEI/SPI/SPI(t)/CEI, baseline compliance, schedule % complete,
  task-makeup counts, finishes-by-month (the Bow Wave view), per-data-date slippage curves
  (the Trend view), constraint breakdown (DCMA05 + the grid).
- **Visuals**: the deck's custom Gantt/timeline visuals are covered by the existing
  MS-Project-style Gantt; milestone-trend analysis is covered by the Trend focus-UID
  movement chart; histogram/box-and-whisker needs are served by the float bands and the
  duration-ratio min/avg/max; one novelty visual (an aquarium) was admired and declined.

## Consequences

**M15 is complete — every milestone (M1–M17) is now done; no blocked work remains.**
631 passed, 3 skipped (16 new tests: hand-verified band edges on a 10-hour calendar,
the completion splits/averages/ratios, MEI/staleness incl. NA honesty, hand-computed ES and
rate forecasts, golden pins for all three families, and the new web surfaces); parity 10/10
untouched; coverage ≈98% overall / ≈98% engine; ruff + format + mypy --strict + bandit
clean; zero new dependencies; the `.pbix` never left the machine.
