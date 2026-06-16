# ADR-0040 — PBIX pages 6, 7, 12: Finish & Slippage month curves

Date: 2026-06-16 · Status: accepted

## Context

M18 item 6 (PBIX visual reproduction). Pages 1 (ADR-0038), 4 + 5 (ADR-0039) are done.
This PR delivers the deck's three **monthly-count curve** pages, grouped because they
share one engine and one axis:

- **Page 6 (Finishes)** — for a single version, a line of **actual** finishes vs
  **baseline** finishes per calendar month.
- **Page 7 (DATA Date Finishes)** — the multi-version sibling: one actual-finish curve
  per version (by data date) on a shared month axis — the bow wave drawn as a line
  family rather than animated bars.
- **Page 12 (Slippage)** — per version, the **start** curve and the **finish** curve;
  the whole profile sliding right across versions is the slippage signature.

## Decisions

1. **Shared month-axis primitives extracted** (`engine/month_axis.py`): the three
   trivial primitives the bow-wave already used in private — `month_index`,
   `month_label`, `bucket` — are now a small public module. `bow_wave.py` imports them
   (its intricate status-relative window / CEI-period cap logic stays put; only the
   primitives moved). This removes duplication and gives the new curves the *same*
   month bucketing as the bow wave, so the views line up.

2. **New engine helper** (`engine/month_curves.py`): `compute_month_curves(schedules)`
   → `MonthCurves` (shared `month_labels` + per-version `VersionCurves` with
   `baseline_finishes`, `actual_finishes`, `baseline_starts`, `actual_starts`, plus the
   `status_index` of the data-date month). Each activity is counted on its **most
   authoritative** date — actual start/finish where present, else the current scheduled
   date; baseline curves always read the baseline dates. The axis spans the full data
   range across every version, capped at 60 months (oldest months shed first so a stray
   far-future date can't explode the chart). Lightweight frozen dataclasses, **not**
   `MetricResult` — the metric-dictionary coverage test is unaffected (the established
   pattern from ADR-0038/0039).

3. **A new `/curves` page** (`_curves_body` / `_curves_data`, `static/curves.js`) — three
   dependency-free SVG line charts (Finishes, DATA Date Finishes, Slippage) over
   `/api/curves`. Reachable from the header nav (always) and from the dashboard's
   multi-version action row (with ≥2 versions). The page works with a **single** version
   (the curves show that version alone; a hint invites loading more). Per-version
   overlays use a fixed categorical palette; gridlines/labels stay theme-variable.

4. **Stored-date, no CPM gate** — the curves are pure stored-date views (no network
   solve), so the page contributes **every** loaded version, not just the CPM-solvable
   subset (unlike `/trend`, `/forecast`). One un-solvable file does not drop from the
   curves.

5. **Export wired** — `/export/{fmt}/curves` (xlsx + docx) via a new
   `month_curves_tables()` in `reports/tables.py` (per-version monthly start/finish
   columns), consistent with the other view exports.

## Scope / safety

Pure presentation over stored dates plus additive, tested engine helpers; parity
untouched (10/10); the air-gap test extended over the new page and `curves.js`; engine
coverage 97% (new modules at 100%); nothing leaves the machine. The bow-wave refactor is
mechanical (private→shared primitives) and verified green by its existing golden tests.

## Remaining PBIX pages (next PRs)

WBS-grouped Completion + SPI/ES pivots (8–9) · the Carnac forecast cards (13). Page 2
(Performance) and page 3 (Schedule vs Activities) are KPI/line restatements of metrics
already shown elsewhere; pages 10–11 (Complete-ToGo, Actual Summary) reuse the same
start-month bucketing introduced here.
