# ADR-0042 — PBIX page 13: the Carnac forecast cards

Date: 2026-06-16 · Status: accepted

## Context

M18 item 6 (PBIX visual reproduction). Pages 1 (ADR-0038), 4/5 (ADR-0039), 6/7/12
(ADR-0040), 8/9 (ADR-0041) are done. This PR delivers the deck's **Carnac** page (PBIX
13) — the forecasting KPI cards: earliest start, latest finish, project duration,
Forecasted End Date, avg tasks/month, remaining duration, "SPI 2", Tasks Completion
Forecast, Earned Schedule (ES), and Estimated End Date (ES — To-Go Activities).

(The deck's *Carnac2* page — Estimated End Date by data-date period, the forecast drift —
was already shipped as the `/forecast` drift table + animation in ADR-0037.)

## Decisions

1. **Reproduced as a card row on the existing `/forecast` page**, not a new route. The
   deck's Carnac *is* our forecast page (it already shows the three forecast methods + the
   drift). Adding the KPI cards at the top — via the existing `_stat_cards` helper —
   reproduces page 13 with **no new route, no new JS, and no air-gap surface change** (the
   cards are static HTML). The method table + drift stay below, unchanged.

2. **New engine helper** (`engine/forecast.py`): `compute_carnac_summary(schedule, cpm,
   forecasts)` → `CarnacSummary` (a lightweight frozen dataclass, **not** `MetricResult`).
   Every figure is **reused** from the CPM and the existing `ForecastSet` — the three
   method finishes (CPM / rate / earned-schedule), `rate_per_month`, `spi_t`,
   `remaining_count` — plus three derived working-day spans computed from the stored dates:
   earliest start, project duration (earliest start → CPM finish), and remaining duration
   (data date → CPM finish). No new forecasting math; a missing input reads `None` → "—"
   in the view (never fabricated).

3. **Faithful label mapping** for two ambiguous deck cards (the DAX is XPress9-compressed
   and not extractable — ADR-0030/0033, so these are documented reconstructions):
   - **"SPI 2"** → our count-based **SPI(t)** (the canonical Earned-Schedule index).
   - **"Tasks Completion Forecast"** → the **to-go activity count** (tasks the forecast
     must still complete). "Forecasted End Date" is the completion-rate finish and
     "Estimated End Date (ES)" is the IEAC(t) finish, so reading this third card as a count
     avoids a fabricated duplicate date.

4. **Earned-Schedule definition unified (DRY).** `forecast.py` had its own private
   `_earned_schedule` duplicating the count-based ES construction already public in
   `metrics/evm.py` (`earned_schedule`, factored out in ADR-0041). Since the Carnac helper
   needed ES in working days, `_earned_schedule` now **delegates** to
   `metrics.evm.earned_schedule` — the forecast IEAC(t), the SPI(t) metric, and the WBS
   breakdown now share one Earned-Schedule definition. The golden forecast pins (P2 ES
   2029-03-08 / SPI(t) 0.45, P5 ES 2029-02-01 / SPI(t) 0.47, exact-ratio IEAC) are
   unchanged, confirming numerical equivalence.

5. **Export** — the forecast export (`/export/{fmt}/forecast`) gains a "Forecast summary
   (Carnac)" table (`carnac_table`) ahead of the method table.

## Scope / safety

Pure presentation over the existing forecast/CPM outputs plus one additive tested helper
and a DRY refactor guarded by the golden pins; no new route/JS so the air-gap test is
unchanged; parity 10/10; engine coverage 97% (forecast.py 97%, no uncovered lines).
Carnac cards cross-check the golden P5 forecast exactly (CPM 2027-12-07, rate 2028-06-10,
ES 2029-02-01, SPI(t) 0.47, to-go 99, project span 462 wd).

## PBIX reproduction status

Pages **1, 4, 5, 6, 7, 8, 9, 12, 13 reproduced** (ADR-0038 → ADR-0042). The remaining deck
pages are restatements of metrics already surfaced elsewhere: page 2 (Performance KPIs —
BEI/CEI/MEI/SPI), page 3 (Schedule vs Activities line), page 10 (Complete-ToGo), page 11
(Actual Summary cumulative curves). RatioMeasure stays unimplemented (dangling deck
binding — ADR-0033). The reproduction spine of M18 item 6 is complete.
