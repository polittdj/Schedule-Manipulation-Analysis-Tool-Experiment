# ADR-0327 — The Library/Setup pages wear the panel toolbar (rank 12, second slice)

Status: accepted (2026-08-01)
Amends: ADR-0311 (rank 12 first slice — the recorded toolbar/read-me debt)
Builds on: ADR-0298/0304/0305 (panel contract + the two ⛶ layouts), ADR-0325/0326 (the two
recorded blockers, cleared), DESIGN-SYSTEM §3 (toolbar contract) and §3:78 ("Tables get
`⤓ EXCEL` only"), PLAN-20260730 PR-9 row (decisions A1 · B1 · C1 — this is the PR-9b half)

## Context

ADR-0311 recorded what rank 12 still owed: *"The `▦` / `⤓` / `⛶` toolbar and read-me line on
every visual, which the DoD requires and none of the six has,"* with two hard blockers —
`/margin` waited on the AXIS-TITLES batch for `margin_dashboard.js` (cleared by ADR-0325) and
`/workbench` waited on the DOM caption decision (cleared by ADR-0326, which also recorded that
per §3:78 the workbench tables' ⤓ **already ships** as the panel's own labeled export links).
The six pages are /margin, /workbench, /standards, /groups, /card/{name}, /wbs/{name}. Each
page's visuals and exports were re-surveyed fresh on this tree before editing (the ADR-0311
lesson: a conformance sweep driven by assumed shapes reports conforming pages as broken).

## Decision

Every data-visual panel on the six pages joins the shipped contract — one `panelkit.js`
include per page, `_panel_head` + `_shell_tools` per visual, a muted read-me line per visual —
with the ⤓/▦ decisions resolved panel-by-panel from the survey, never by blanket rule:

1. **⤓ EXCEL only where an existing export covers what the panel draws** (dead/lying ⤓ is a
   defect class):
   * `/margin` — all three data panels (burn-down, MET, per-version figures) point at the ONE
     margin workbook (`/export/xlsx/margin`): the per-version figures are its first sheet and
     the erosion summary its second.
   * `/standards` §1 DCMA-14 points at the per-schedule analysis workbook — its DCMA-14 sheet
     is the table's measured data (the formula/threshold/source columns are pinned dictionary
     metadata, not measurements; `docs/METRIC-DICTIONARY.md` carries them).
   * `/wbs/{name}` — both pivots point at the WBS workbook, whose two sheets
     (`wbs_breakdown_tables`) are EXACTLY these two pivots.
2. **⤓ refused, with the reason recorded** (each refusal also asserted by test):
   * `/margin` risk-sufficiency panel — its Zero-margin toggle is live state a STATIC
     `data-export` cannot follow (the round-10 /performance defect class); the page's export
     bar carries the parameterized export.
   * `/workbench` head strip — the ribbon's Excel/Word exports already ship as the panel's own
     labeled links (how ADR-0326 recorded §3:78 satisfied); a head glyph would be a second
     affordance for the same URL inside one panel (the round-11 inert-duplicate class). The
     drill's export rebuilds `&cols=<live selection>` per render — same static-attribute bar.
   * `/standards` §2 Fuse / §3 SEM — **no export anywhere carries those families** (the
     workbench workbook stops at DCMA-14/Schedule Quality/Float; the performance workbook
     ships different datasets). Recorded as the residual below.
   * `/groups` — page-wide: no covering export exists, and the preview can show an UNAPPLIED
     URL-preview scope while every export route reads the APPLIED session scope.
   * `/card/{name}` — the ID-card KPI set is no workbook's sheet, and the pivots panel is
     1-of-4 covered (completion performance is an analysis-workbook sheet; makeup, status and
     constraint appear in no export) — a panel-level ⤓ would hand back less than the panel
     draws (the /forecast methodology precedent).
3. **No ▦ DATA anywhere on the six** — every candidate panel's numbers are already visible
   as tables on the same page (the home-shell precedent: the table IS the data): the margin
   charts' figures are the per-version panel; the wbs combo chart's figures are the ES table
   directly beneath it; the rest are tables outright. `▦` stays reserved for a visual whose
   underlying table is otherwise hidden — no `.sf-drawer` was invented this round.
4. **⛶ ENLARGE on every data-visual panel** (the house pattern every shipped contract page
   follows — §3:78's "⤓ only" governs the data glyphs, not the panel-level focus affordance);
   operator-control forms (margin rate/band, the filter builder) and status notices (the
   no-filter Active-scope branch, empty states) get NO toolbar — they are not data visuals.
5. **Read-me line per visual**: panels that lacked any explainer gained one (margin
   per-version figures, card pivots, standards §1, the groups breakdown); existing explainers
   were kept verbatim (minimal diff). On /standards §1 the old counts note became the
   `.sf-take` (same figures verbatim — they re-render in the table below) with the new
   read-me after it, the canonical take → read-me order.
6. **Provenance chips**: whole-series (`_series_prov_chip`) on cross-version panels
   (margin, workbench, groups Active scope), this-file (`_prov_chip`) on single-file panels
   (standards, card, wbs, groups preview). The margin risk panel carries none — the fetched
   result echoes its own run parameters, and a static chip could contradict them.
7. **The include obeys the r11 dead-promise law**: empty states ship no script; /groups and
   /wbs gate the include on a contract control actually being in the ASSEMBLED body (a
   summaries-only preview or the no-groups branch renders none; a session-target focus panel
   above the wbs body carries its own). `_panel_head` gained `h2_attrs` so /margin's
   deliberately translation-pinned `data-no-i18n` headings survive the conversion unchanged.

## Consequences

* The six pages' focus panels (`_target_panel`), which already rendered head-strip markup,
  now actually have panelkit.js to drive them on /card and /wbs — the round-5 "markup alone
  is not evidence" gap closes as a side effect.
* No JS file changed — every byte-frozen `PAGE_SCRIPTS` baseline and the 16-site axisTitles
  census hold as-is. No engine code touched; no displayed figure moves.
* The promotion census is unchanged on every page (7/2/5/5/3/3 panels on the test fixtures,
  verified equal on the pre-change tree) — nothing new joins jarvis's broad `.panel` fight.
* `tests/web/test_r12_library_toolbar.py` pins the round r11-style: include exactly-once +
  empty-state absence, ⤓ liveness with count pins (no vacuous pass), per-panel glyph anatomy,
  the refusals, the read-mes, the loaded-terms gate (control first), and the measured ⛶
  overlay lift in real chromium on /margin and /card. Proved able to fail: 12 of 14 tests
  fail on the pre-change tree; the two that pass on both are the invariant guards (clean
  empty states; the unchanged census).

## Residuals (recorded, not owed by this round)

* A Fuse-index/SEM export does not exist, so /standards §2/§3 stay ⤓-less; adding a
  `/export/{fmt}/standards` workbook would let them join (new endpoint — out of a toolbar
  sweep's scope).
* /card's pivots would take a ⤓ if the analysis workbook ever gains makeup/status/constraint
  sheets.
* ADR-0311's remaining DoD item for these pages, `data-noprint` (decision C1), ships as its
  own PR-4 per the plan.
