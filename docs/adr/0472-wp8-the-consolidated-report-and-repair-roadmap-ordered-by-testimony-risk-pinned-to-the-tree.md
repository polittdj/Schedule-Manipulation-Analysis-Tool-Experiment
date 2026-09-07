# ADR-0472 — WP8: the consolidated audit report and repair roadmap, ordered by testimony risk and pinned to the tree — a report that can go red is a measurement; one that cannot is a rumour

- **Status:** Accepted — 2026-09-07 (POLARIS² audit campaign, WP8 — the closing work package; SOLO lead, fix-as-verified)
- **Version:** 1.0.242
- **Extends:** ADR-0440..0471 (the campaign), ADR-0393 (QC-1/QC-2), ADR-0405 (FINAL-REPORT truthfulness), ADR-0406 (the chromium resolver), ADR-0451 / ADR-0466 / ADR-0467 / ADR-0470 (the residuals this report closed or retired), ADR-0455 (the route-coverage instrument)
- **Ledger:** `docs/STATE/AUDIT-2026-08-27.md` (WP8 section) · **Report:** `docs/STATE/AUDIT-2026-08-27-REPORT.md`
- **Shipped:** the report (docs) · `tests/guards/test_audit_report_wp8.py` (8, NEW) · `docs/FINAL-REPORT.md` (the headline tempered) · `tests/web/test_docs.py` (the headline pin) · the ledger's WP8 section and design table

## Context

The campaign's last work package was a document: order every ledger row's verdict by what a wrong
number would cost in testimony, price each open residual with its first executable step, and land it
without code unless a residual was fixed as verified. Two things shaped how it was built.

**A report is a claim about the code, and this repo's claims drift.** The campaign's own ledger carried
a figure — "176 `round(` sites outside `engine/metrics`" (ADR-0467) — that no definition reproduces:
AST `round` calls outside `engine/metrics` number **325** (44 files); outside all of `engine/` 193;
`web` + `reports` + `importers` 175; `web` alone 161 — on the ADR-0467 tree (`d61f6395`) and on this one.
A count with a method is a measurement; a count without one is a rumour, and it had been copied into
three handoffs and a kickoff. So the report carries a **census table whose nine figures a guard
recomputes by the stated method on every run**, a register the guard checks against every row id the
ledger carries, and a roadmap the guard checks for a price or an owner and a first step on every row.
The guard was observed red before the report existed, then red by name under four mutations of the
report (a census value 325 → 324; a register row dropped; an OPEN row unpriced; a T5 row moved above a
T1 row).

**QC-2 says inherited residuals are unverified until re-verified.** Each "observed, not fixed blind"
item the kickoff carried was re-measured on this tree before it was priced:

| inherited claim | re-measured | disposition |
| --- | --- | --- |
| "other browser modules still carry expression-string waits" (ADR-0466 §3) | 15 `wait_for_function` sites under `tests/`, 15 function strings, 0 expression strings; the three on `b8e8aa42` were `test_trend_design_browser.py`'s own | **CLOSED** (R-33) |
| /volatility's four themes not each screenshotted (ADR-0451) | a four-theme DOM census: 13 `.panel` · 2 chips · widest 1440 · 10 cf-bars · zero page errors, identical per theme | **CLOSED** by census, not screenshots — named (R-36) |
| /card's artboard read from markup, not executed (ADR-0470) | the canvas executed over loopback HTTP for `setScreen('ic')`, four themes, zero page errors; the markup reading confirmed | **CLOSED** (R-37) |
| TEST-01's chromium build pins (the 2026-08-13 plan) | 0 `/chromium-1194/` path pins in tests; 2 documentary mentions | **CLOSED** (R-35) |
| `evm.py`'s `actual_cost or 0.0` · `dcma14`'s parity roundings · the record's schema · `workbench` 400 vs 422 · IMP-05 · TX-03 · JS-05 · the `.catch` conflation | 1 site · 2 sites · no `v`/correlation key · one status code · the import note in place · the probe route in place · 56 tokens · 13 modules | **priced** (R-01 · R-03 · R-13 · R-39 · R-02 · R-12 · R-28 · R-09) |
| DOC-01 — FINAL-REPORT's "COMPLETE and parity-green" headline | still unqualified at line 8 while §6.B tempered it | **FIXED** (docs): tempered under a red-first pin in `test_docs.py`; the census carries it as 0 |
| ENG-DEAD-01 — `actual_start_driven` unconsumed | consumed by four modules | **CLOSED** by grep (§4 of the report) |

**One new row.** Measuring the migrated /wbs page (ADR-0471) by the document's own `scrollWidth` instead
of element boxes found that EVERY page scrolls horizontally ~280–300 px at a 1440-px viewport: the
hidden tooltip box `[data-sf-hint]::after` (absolute, `left:0`, 340 px, `visibility:hidden`) on
right-aligned hosts — the Reset-view button of every `.viz-controls` row — counts in scrollable
overflow, `body` overflow-x is `visible`, and headless hides the scrollbar the operator would see.
Attributed by computed style on the pseudo-element, recorded as **UI-03** in the ledger and R-20 in
the roadmap, priced S with a red-first pin named — and NOT fixed here: a chrome-wide CSS change on 75
hint hosts per page needs its own render sweep across the census's 34 page states.

## Decisions

1. **The report is pinned to the tree** by `tests/guards/test_audit_report_wp8.py`: coverage (every
   ledger row id), pricing (every roadmap row priced or owned, with a first step), ordering (tiers
   monotone), and a nine-figure census recomputed by the stated methods. A figure the guard cannot
   re-derive fails the guard; so does one the tree no longer matches. Re-measure, never edit by hand.
2. **Testimony tiers order the roadmap** — T1 a cited figure could be WRONG · T2 a right figure could be
   MISREAD · T3 the RECORD · T4 controls and rendering · T5 process · T6 organizational — and within a
   tier rows run cheapest-first. The tiers are the report's §0 and the guard's monotonicity check.
3. **Closed by measurement is a verdict; closed by assumption is not.** The four closures above each
   cite an executable measurement made this session; the four round-3 rows (R-06) and the runner's
   ordering (R-34) stay HELD and unpriced because nothing local can settle them.
4. **The `176` is retired**, not corrected: the ledger's WP8 section records that it could not be
   reproduced and the census replaces it.

## Deliberately NOT done (measured, left alone)

- UI-03's CSS fix (above) · every OPEN roadmap row (each priced with its first step — that is the
  plan-forward the operator asked for, not a work queue this session may start) · NUM-01's parity
  wording (R-18: NOT re-read this session — stated as UNVERIFIED rather than assumed closed).

## Consequences

- The campaign closes with every verdict registered, every open residual priced and owned, and a
  guard that turns the report red when the tree moves under it.
- Version 1.0.241 → **1.0.242** with ADR-0471; wheel + nine installers rebuilt in lockstep as the LAST
  step after the last source edit.
