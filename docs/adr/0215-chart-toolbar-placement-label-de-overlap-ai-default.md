# ADR-0215 — Chart toolbar off the data, inline-label de-overlap, and the default CUI AI model

## Status

Accepted. Operator directives 2026-07-13 (live-testing v1.0.25): (1) "the enlarge selector can't rest
over the data on any visual"; (2) "fix all visuals so that the data totals … don't overlap … if they
overlap make them callouts that show when the user hovers"; (3) "make it so that the CUI AI comes on by
default with [qwen2.5:7b-instruct] active and the tool set for CUI and local use only."

## Context

- **Chart toolbar (`chartframe.js` / `.cf-bar`).** The shared per-chart toolbar (⤢ full-screen · −/＋
  zoom · reset) was absolutely positioned `top:2px; right:6px` and hover-revealed, so it floated **over
  the top-right of the plotted data** on every visual. A reserved-padding fix still left a ~2px overlap
  (the toolbar box is ~26px tall) and would be fragile across the four themes' fonts.
- **Inline value labels (`trend.js` line charts).** `multiLineChart` / `lineChart` /
  `varianceTrendChart` drew a numeric label at **every** data point *and* a hover call-out. On a
  many-version schedule the per-point labels stacked into an unreadable pile (operator screenshot: a
  ~15-period HMI line with `0.50/0.40/0.35/0.00…` overprinted).
- **AI defaults (`AIConfig`).** CLASSIFIED (CUI) + `backend="ollama"` + loopback endpoint were already
  the defaults (fail-closed to Null via `route_backend`). Only the default **model** (`llama3.1:8b`)
  differed from the operator's deployed model.

## Decision

- **Toolbar in-flow.** `.cf-bar` becomes an in-flow block (`margin: 0 6px 4px auto`, `width:max-content`)
  — a DOM sibling that already sits above `.cf-scroll`, so it reserves its own height and can **never**
  overlap the plot, in any theme, with no magic padding. The chart still re-renders its innards inside
  `.cf-scroll`, so zoom/frame state survives a redraw.
- **Greedy label de-overlap.** Each trend line chart keeps a per-frame `placed[]` of drawn label
  positions and only draws an inline value when it clears the placed ones (`labelFits`); a suppressed
  value is **never lost** — every point carries a hover `<title>` call-out (the variance markers gained
  one). No "always label the latest point" bypass — that had reintroduced overlap where two series'
  final labels coincided.
- **Default model.** `AIConfig.model`, `OllamaBackend.DEFAULT_MODEL`, the settings-form default, and the
  setup-guide "standard model" all become **`qwen2.5:7b-instruct`**. CLASSIFIED + Ollama + loopback stay
  the defaults; `route_backend` still fails closed to Null if Ollama or the model is absent (no cloud,
  Law 1).

## Consequences

- The toolbar is always clear of the data and legible; dense line charts show a readable subset of
  labels with the full value one hover away. The deployed tool boots the local CUI AI on the operator's
  model with no per-launch reconfiguration.
- Presentation/config only — no engine or metric change (Law 2). Pinned by
  `tests/web/test_chart_readability_and_defaults.py` and the updated `tests/web/test_ai_wiring.py`.
- **Follow-up (next PR):** click-to-drill on the per-activity bar charts (volatility leaderboards, DRM
  histogram, SRA sensitivity tornado) plus bar-total label de-overlap — grouped as a "bars" PR.
