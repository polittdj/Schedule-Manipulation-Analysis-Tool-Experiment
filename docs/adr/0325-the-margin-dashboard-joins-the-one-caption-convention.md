# ADR-0325 — Batch 3b-i: the margin dashboard joins the one caption convention

- **Status:** Accepted
- **Date:** 2026-08-01
- **Implements:** `docs/STATE/PLAN-20260730.md` PR-8 (AXIS-TITLES batch 3b-i, operator decision
  **A1**: `margin_dashboard` first, the rest as 3c)
- **Related:** ADR-0298 (one helper, one token, the ledger), ADR-0301 (captions come from the
  code), ADR-0302 (the optional `y2Label`), ADR-0303 (the caption stays fixed, the data yields),
  ADR-0316 (the blob-driven-module `defer` family), ADR-0195 (design system)

## Context

`margin_dashboard.js` renders the Executive Margin Dashboard's two SVG charts — the NASA
Margin/Contingency Burn-Down and the Margin Erosion Trend — and sat in the AXIS-TITLES `PENDING`
ledger. Each chart drew a local bottom-right `"status date"` quasi-caption (`txt(svg, R, B + 12,
"status date", …)`) — exactly the second-convention fragmentation ADR-0298 exists to retire — and
its in-SVG legends started at `(L + 4, T + 2)`, the corner the shared helper's Y caption owns
(`L + 4, T + 9`). ADR-0301 batch 2 had flagged this module as one that "will want" the secondary
axis caption once it existed.

## Decision

### Captions derived from the rendering code (ADR-0301), both charts

| Chart | X caption | Y caption | Why the Y reads that way |
| --- | --- | --- | --- |
| Burn-down | Status date | Days (margin + contingency) | the bars **stack margin in WORK days with contingency in calendar non-working days** (weekends + holidays to the target — the reference workbook's own stack), so the caption counts "days" without asserting a single basis a mixed stack does not have |
| Erosion trend | Status date | Effective margin (working days) | the line plots `effective_margin_wd` only — one series, one basis |

Both X captions are the retired quasi-captions' own words: each chart plots one point/bar per
loaded version at that version's status date. The old local captions are deleted; the helper is
the only caption writer.

### `y2Label` dropped (decision A1's sub-answer)

ADR-0301 batch 2 predicted this module would want ADR-0302's secondary-axis caption. Checked
against the rendering code: **neither chart has a second scale.** The burn-down's requirement
line, band, and planned ticks all read on the same left axis; the erosion chart is
single-series. Per A1 — "drop `y2Label` where the code shows one scale" — no `y2Label` is
passed.

### The legends yield the corner (ADR-0303's law)

The helper's placement is FIXED; the colliding element moves. Both legends start one
caption-height lower — `(L + 4, T + 2)` → `(L + 4, T + 24)` — so the Y caption owns the
top-left corner. Measured (below): no text-vs-text overlap remains in any theme × scale combo.

### Not-axis-charts, recorded not improvised

The module's third SVG — the risk-sufficiency **P10–P90 spread strip** (`renderRisk`) — is a
one-dimensional number line: no plot rect, no tick axes; its P-labels and D/E markers are data
annotations. It is deliberately NOT captioned by the axis helper. (A1 also recorded the SRA
tornados as not-axis-charts; those belong to batch 3c's modules.)

### The blob-driven module gains `defer` (ADR-0316 family, third member)

`margin_dashboard.js` renders synchronously at parse time, and now touches
`SFChartFrame.axisTitles` — but `_LAYOUT` emits `chartframe.js` AFTER `</main>`. Without
`defer` the page threw `SFChartFrame is not defined` and rendered **neither chart**: the
visual pass measured "no captions rendered" in **all twelve** theme × scale combos before the
fix. Same defect and same fix as `resources.js` (round 10) and `performance.js` (ADR-0316);
the module's own pre-existing guarded `SFChartFrame.scan()` call was the tell that it could
execute before the helper loads. Pinned by
`test_margin_dashboard_js_is_deferred_so_chartframe_exists_first` (watched fail on the
un-deferred tag).

### The call-site census: a deliberate, named 16 → 18 re-baseline

`AXIS_CALL_SITES` (the argument-object md5 freeze, `test_r11_panel_contract.py`) grows by the
two new sites — `margin_dashboard.js:233` (`06f121de…`) and `:309` (`ebda9aa1…`). The sixteen
prior entries are **byte-identical** (additions, not moves); the count assertions and test name
move 16 → 18. A1 recorded "deliberate md5 re-baseline is the accepted procedure" for exactly
this. Proved able to bite: the pre-change census run against this tree fails with 18 ≠ 16.

### `/margin` joins the measured visual pass, with its own serve

The golden Project2/Project5 pair legitimately renders NO margin chart (no margin-named
activities, no status-dated months) — measuring `/margin` against it would prove nothing. The
pass now boots a **second app instance** loaded with four synthetic status-dated versions whose
margin erodes 40 → 10 wd (the same shape `test_margin_dashboard_view.py` pins), so the
burn-down AND the erosion trend (2+ points, a projected zero-margin date) both really render;
`localStorage` being per-origin, the theme/scale write lands after navigating to that origin.

## Consequences

- **Measured:** 720 caption renders across 4 themes × 3 scales × 7 pages, zero problems —
  size/uppercase/inside-svg/contrast pass and no text collisions, `/margin` included.
  `KNOWN_COLLISIONS` stays empty.
- `PENDING` **5 → 4**: `sra.js`, `sra_jcl.js`, `sra_ssi.js`, `volatility.js` (batch 3c).
- The erosion chart's "zero margin YYYY-MM" annotation is data-dependent (it sits at the
  projected date's x); the served combos measure it clean at the right edge. If a future
  dataset parks it under the Y caption, that is ADR-0303's data-label-yields case, to be fixed
  in `margin_dashboard.js`, never by moving the caption.
- The burn-down's wrapped legend rows now float one row lower over the plot's top band; bars
  are marks, not text, and the tallest bar tops out ≈23 px below the plot top by the 1.08
  head-room factor, so the band stays readable — and the pass would flag any text collision.
- **Version 1.0.140 → 1.0.141**, wheel + nine installers regenerated (ADR-0148 lockstep).
