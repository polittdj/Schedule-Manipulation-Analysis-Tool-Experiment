# ADR-0170 — Split the MEI/BEI/EPI/BRI trend chart into per-index visuals

## Status

Accepted. Closes backlog #71. Operator asked (screenshots) to split the "Quality Trend combined
visual" into separate visuals; on 2026-07-09 the operator confirmed the target is the
**MEI / BEI / EPI / BRI** combined chart (the page carries several combined charts, so this was
disambiguated first).

## Context

`/trend`'s `trend.js` drew MEI, BEI, EPI and BRI as four series on **one** `multiLineChart` axis.
Those indices carry different scales and meanings (milestone execution, baseline execution,
execution performance, baseline realism), so a shared axis flattened and obscured each series —
the operator couldn't read any one trend.

A separate execution panel — **BEI / CEI / HMI** — is *intentionally* combined to mirror the NASA
Schedule Management Handbook's Fig 7-21 single-axis execution view, and must stay combined; the
disambiguation confirmed #71 does NOT touch it.

## Decision

Replace the single `multiLineChart("MEI / BEI / EPI / BRI across versions", …)` call with a loop
that emits one single-series `lineChart` per index — MEI / BEI / EPI / BRI — each with its own
title (`"<index> across versions"`), color, per-index description, and 2-dp value formatter, and
each shown only when that index has a value in some version. The `multiLineChart` helper is
unchanged and still backs the deliberately-combined charts (BEI/CEI/HMI, FEI, HMI, CEI, Float
Ratio). No engine or data change — same `data.versions[i].indices` payload.

## Consequences

- Live-verified in Chromium (Hard_File pair): the combined "MEI / BEI / EPI / BRI across versions"
  chart is gone; four separate per-index charts render (MEI/BEI/EPI/BRI), the BEI/CEI/HMI execution
  panel stays combined, zero console errors. Pinned by
  `tests/web/test_trends_animation.py::test_health_indices_are_split_into_separate_charts`.
- `src/` changed (`static/trend.js`) → wheel + 9 installers rebuilt in the same commit (ADR-0148
  lockstep). Laws untouched (presentation-only; the figures are the engine's, offline).
- Remaining from the operator work order: Resources day/week/month bucketing + overallocation
  drill (#74), SRA editable-grid Gantt (#80).
