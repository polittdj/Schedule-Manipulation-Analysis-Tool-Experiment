# ADR-0197 — Mission Ops redesign step 3 (first page shell): chapter 01 "Where we stand"

## Status

Accepted. Step 3 of the Mission Ops redesign restyles each chapter's page *content* to the design
spec, one chapter per PR. This is the first — chapter 01 "Where we stand" = the Analysis report at
`GET /analysis/{name}` — which sets the template later chapters copy. Presentation only: no
`engine/` / `importers/` / `ai/` change; every figure is read from what the report already computed.

## Context

The Analysis report opened straight into dense panels with no headline. The redesign wants each
chapter to lead with a **data-driven takeaway** (a sentence with a number), a **KPI strip**, and
composition **bars** before the detail. A gotcha from step 2: the chapter kicker + Continue footer
never fired on `/analysis` because chapter 01 has an empty `titles` tuple and the route passes the
schedule name as the `_page` title, so `_TITLE_TO_CHAPTER.get(name)` was `None`.

## Decisions

- **Explicit chapter binding for dynamic-title pages.** `_page` gains a `chapter: _Chapter | None`
  parameter; `_chapter_kicker` / `_story_footer` take an optional override. A new `_CHAPTER_BY_NUM`
  lets a route name its chapter. `analysis()` passes `_CHAPTER_BY_NUM["01"]`, so the
  `CHAPTER 01 · WHERE WE STAND` kicker, the STORY-SO-FAR dash, and the `Continue → Chapter 02`
  footer now render on `/analysis`. (General mechanism — later dynamic-title chapters reuse it.)
- **`_where_we_stand_header(key, sch, analysis)`** prepends to `_analysis_body`:
  - **Takeaway h1** — a real sentence: "`N% complete against a M% baseline plan at the data date —
    computed finish D, K days behind/ahead of the baseline finish.`" Each clause is a computed
    figure or is omitted (no baseline → "with no baseline finish to compare against").
  - **6-KPI strip** (reusing `_stat_cards`): Activities · Earned complete (+ plan-at-DD) · Critical
    (incomplete) · Computed finish · vs baseline ±Nd · Data date.
  - **Activity status mix** bar (Complete / In progress / Planned) from `compute_activity_makeup`.
  - **Float remaining** bar (0d / 1-4d / 5-9d / 10+d) bucketed from `activity_rows` total float over
    the incomplete population, captioned "N incomplete activities".
  - A reusable `_status_stack` renders each single stacked bar + labelled legend.
- **Data sources are all pre-existing** (no CPM math added): counts from `compute_activity_makeup`;
  finish from `offset_to_datetime(project_start, cpm.project_finish, cal)`; baseline variance from
  `compute_finish_forecasts(sch, analysis.cpm).planned_finish` (handed the cached CPM — no re-solve);
  plan-at-DD from `analysis.compliance["forecast_to_be_finished"]` (baseline-scheduled-by-DD %, an
  honest count-based proxy, labelled as such); float bands from `activity_rows[*].total_float_days`.
  Missing inputs render as an em dash — never a fabricated 0.
- The page-wide **export bar** moved from the route into the header (so it sits below the takeaway,
  not above the kicker). Every prior section — the interactive `#viz`/`#gantt`/`#grid` scaffold and
  its control IDs, the DCMA-14 board, `#floatHist`, `#scatterChart`, findings, AI narrative, the
  `/export/xlsx/analysis/` link, target panel — is untouched.

## Consequences

- The Analysis report now reads as a chapter: kicker → takeaway → KPIs → composition bars → detail
  → Continue. Verified in Chromium across all four views (console rail / daylight top bar / apollo /
  jarvis), zero console errors; figures internally consistent (status segments sum to the activity
  total; float bands sum to the incomplete count). Full gate green.
- The full **chart-contract toolbar** (`▦ DATA / ⤓ EXCEL / ⛶ ENLARGE` + provenance chip on every
  visual) is a cross-cutting concern deferred to a dedicated follow-up so it lands once for all
  charts rather than per page. The per-chapter takeaway pattern established here is the template for
  chapters 02–12 (one page shell per PR).
- Version 1.0.6 → 1.0.7 (cache-bust); wheel + nine installers rebuilt in lockstep.
