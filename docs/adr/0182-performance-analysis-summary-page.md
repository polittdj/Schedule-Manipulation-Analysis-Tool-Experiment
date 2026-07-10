# ADR-0182 — Performance Analysis Summary page (G1–G7 workbook recreation)

## Status

Accepted. Operator 2026-07-10: "I uploaded the file into the repo called
PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx … deep dive each worksheet and recreate
the visuals on each … as many visuals as possible be automated. If the metrics needed … don't
exist but can be created using the metadata in the schedules provided then create them. Make
sure to provide labels and legends and descriptions and callouts just as you have on the other
visuals. Create new pages if you need to or add to existing ones."

## Context — the workbook deep-dive

The reference workbook (committed by the operator to `00_REFERENCE_INTAKE/references/`) carries
10 worksheets, 18 charts + 1 chartEx (an Excel histogram), in seven graph families. Reverse-
engineered sheet by sheet (chart XML series references + cached cell values):

- **G1_Characteristics_WorkToGo** — a monthly census: per month, the activities ACTIVE in it,
  split normal/milestone/summary, completed vs to-go, and longest-path membership (2 charts).
- **G2&G3_BowWave** (two status snapshots) — per month baselined/scheduled/actual starts and
  finishes, late-start/late-finish buckets (≤30 / 31–60 / >60 days), BEI/HMI curves (their CEI
  rows are EMPTY — a cross-version measure, not fabricated), 6-mo status markers, cumulative
  curves (4 charts per sheet).
- **G4_Workoff Burden** — per month, baseline execution categorized (BL-plan / early / workoff
  of past-due baseline / past-due→forecast / future-BL-delayed) with the not-yet-done backlog
  as NEGATIVE bars at its baselined month (2 charts).
- **G5_DurationRatioS Curve** — per completed task DRM = actual÷baseline duration: the
  cumulative-probability S-curve (scatter) + a "middle 70%" histogram (chartEx) with
  min/avg/max/n callouts.
- **G3/G6/G7 Quad sheets** — portfolio scatter quads, one dot per project: HMI vs CEI (manual
  entry from Acumen in the sample), To-Go Starts ratio vs To-Go Finishes ratio, and BEI vs
  "% Critical Path To-Go" (= critical to-go ÷ T&M to-go).

## Decisions

1. **`engine/metrics/performance_summary.py`** computes every family from schedule metadata
   alone (std-lib only): `work_to_go_census` (G1, effective-critical set = longest path),
   `activity_flow` (G2+G3 — monthly counts, late buckets, cumulative curves, and per-month
   BEI = cumulative actual ÷ cumulative baselined + monthly HMI hit rates with a 3-month
   rolling average; index curves STOP at the data date and no per-month CEI is fabricated,
   matching the workbook), `workoff_burden` (G4 — above-axis at the actual/forecast month,
   negative mirror at the baselined month), `duration_ratio` (G5 — completed normal tasks;
   the complete task's stored duration IS its actual duration; middle-70% histogram; tasks
   without a baseline duration are counted and disclosed, never imputed), and
   `to_go_snapshot` (G6/G7 — to-go starts/finishes ÷ the baseline's post-data-date remainder,
   plus the critical share of to-go work). A 30-year month-axis safety cap guards against
   corrupt far-future dates (truncation is disclosed on the page).
2. **New `/performance` page** (nav: Assessment → "Performance Summary"): 14 SVG visuals in
   the tool's house style — G1×2, G2×3 (starts, finishes, cumulative S-curves), G3×2 index
   charts, G4×2 mirrored burden charts, G5 S-curve + histogram + stat chips, and the three
   portfolio quads with ONE DOT PER LOADED VERSION. Every tile carries a hover explainer
   (WHAT / HOW TO READ / DECIDE), legends, data-date markers, and honest N/A text when a
   measure is undefined. A version picker scopes G1–G5 (quads stay portfolio-wide); one Excel
   export ships all five datasets (`/export/{fmt}/performance`). Dataset embedded server-side
   (`#perfData`) — no fetch, air-gap preserved; `static/performance.js` is dependency-free.
3. **Quad measure sources**: HMI (tasks) per version using the PREVIOUS loaded version's data
   date as the period floor; CEI (Finish) rescaled 0–1 (the engine metric is a percent); BEI
   from `compute_bei` (matches the Fuse-pinned 0.27/0.59/0.47 on the Hard_File series). Guides:
   0.95 practice band on HMI/CEI/BEI axes, 1.0 parity on the to-go ratios, and the portfolio
   MEDIAN (labeled as such) on the critical-share axis, which has no published threshold.
4. **Metric dictionary**: `duration_ratio`, `to_go_start_ratio`, `to_go_finish_ratio` added to
   `web/help.py` (source: the reference workbook) and `docs/METRIC-DICTIONARY.md` regenerated.
5. **Bug fix (found wiring the quads): HMI values were being discarded as N/A.**
   `hmi.py` returns `CheckStatus.NOT_APPLICABLE` on BOTH branches by design (informational
   metric, no pass/fail bar), so ADR-0179's `field_forecast` — and the new quad — must gate on
   `population == 0`, not on the status. Fixed in both; regression-pinned
   (`test_hmi_real_value_surfaces_across_versions`: a group with a real hit rate was rendering
   N/A on the Forecast page).

## Consequences

- Verified in Chromium on the operator's four-version Hard_File series: all 14 charts paint
  (legends, DD markers, negative-mirror burden bars, quad dots + guides, 5 DRM stat chips),
  zero console errors; the quads read HMI 0.27/0.52/0.08, CEI 0.18/0.16/0.13, BEI
  0.27/0.59/0.47 (Fuse-pinned), to-go ratios climbing 1.0 → 3.09/2.96 with critical share
  0.31 → 0.72 — the bow-wave story of that series, quantified.
- Pinned by `tests/engine/metrics/test_performance_summary.py` (7 tests — every family on a
  hand-checkable synthetic) and `tests/web/test_performance_view.py` (mounts, embedded
  dataset, index-curves-stop-at-DD, version picker, export + guards).
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
