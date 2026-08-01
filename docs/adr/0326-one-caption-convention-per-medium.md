# ADR-0326 — One caption convention per medium: the DOM visuals caption natively

- **Status:** Accepted
- **Date:** 2026-08-01
- **Implements:** `docs/STATE/PLAN-20260730.md` PR-9's **B1 half** (operator decision **B1**,
  `DECISION-BRIEFS-20260730.md` Decision B) — split out per the plan's "may split"; the rank-12
  toolbar/read-me sweep follows as its own PR
- **Related:** ADR-0298 (the SVG helper + the deferral this closes), ADR-0301 (captions come
  from the code), ADR-0303 (the caption stays fixed), ADR-0311 (rank 12's recorded `/workbench`
  blocker), ADR-0325 (batch 3b-i), ADR-0195 (design system)

## Context

Thirteen modules render DOM tables/grids or the HTML-Gantt family — no SVG axes — and
ADR-0298 deferred their caption mechanism as "a separate design decision, deliberately not
invented here." Rank 12's `/workbench` toolbar work was recorded blocked on that decision
(ADR-0311). The operator picked **B1** on 2026-07-30: **native `<caption>` on each data
table + one label slot in the SFGantt timescale header**, with a new executable ledger
detector and this ADR recording "one convention per medium."

## Decision

**A caption follows its medium's own semantics; only the voice is shared.** The voice is the
`.ch-atd` class — `.ch-at`'s DOM sibling: same `--sf-fs-axis-title` token, same uppercase +
tracking, `color:var(--muted)` where the SVG class styles `fill` (SVG `fill` does not paint
DOM text). A ledger test pins that the sibling reads the token, never a literal.

### Mechanism 1 — native `<table><caption>` (the tabular family)

`workbench.js` builds a `<caption class="ch-atd">` as the first child of both its tables:

| Table | Caption | Why (ADR-0301: derived from the code) |
| --- | --- | --- |
| ribbon `.wb-matrix` | Selected metrics × schedule version | the version columns carry only concrete per-version labels, so the column DIMENSION was the unnamed one; the row dimension restates `<th>Metric</th>` deliberately — a caption names the whole grid |
| drill `.wb-grid` | Activities behind {metric} — one row per activity | the row UNIT is the claim the h3 above does not carry |

Native `<caption>` is announced with the table by screen readers, is in-flow for print, and
cannot collide with sticky headers or scrolling cells — the exact hazards the briefs measured
for overlay approaches (B3, rejected).

### Mechanism 2 — the ONE SFGantt timescale slot (the Gantt family)

`gantt.js`'s shared `buildTierScale` now renders **one caption row above the tiers** whenever
the served page carries a `data-ts-caption` marker (`app.py`'s `_TS_CAPTION_MARK`, a hidden
span). The slot is its **own 18px row** — never an overlay — so it cannot collide with band
labels (`.g-scale-capped` shifts the tier tops; the fixed fallback branch shifts via CSS).
Because it is built WITH the header, every rebuild keeps it: the Timescale dialog's repaints,
`/evolution`'s animation frames, `/sra`'s post-save re-renders.

Four server-side one-line opt-ins label all four consumers **with zero consumer-module
edits**: `/path`, `/evolution`, `/driving-path`, `/sra` (the SSI grid). All four draw
calendar-date tiers, so one honest label serves them: **"Schedule dates"**. `/mission`'s
path-evolution TILE deliberately stays unmarked — a preview wall is chrome, not the primary
visual (record, not omission). `/analysis` (app.js's Gantt) is deliberately unmarked too and
the rendered proof asserts NO slot leaks onto it.

**The one deliberate frozen-file edit:** `gantt.js` is byte-frozen in `PAGE_SCRIPTS`
(`test_r11_panel_contract.py`). The slot is added there because the alternative — a
MutationObserver decorating headers after the fact — re-opens the timing/races class for
zero functional gain. Named re-baseline `2a4ccb61… → 9fa3a692…`; no other byte moved.

### The executable ledger (the B1 detector)

`test_axis_titles.py` gains three sets partitioning `NO_SVG_AXES`:
`DOM_TABLE_CAPTIONED` ({workbench.js}) · `TIMESCALE_CAPTIONED` (the four consumers) ·
`DOM_PENDING` (the seven still-open DOM visuals), with `gantt.js` named as the
slot-rendering primitive. Detectors are executable: a table-captioned module must build
`<caption class="ch-atd">`; a timescale-captioned module must call `SFGantt.buildTierScale`;
the slot must exist in `gantt.js` AND be fed (`_TS_CAPTION_MARK` served ≥ 4 pages, styled by
`app.css`). **`DOM_PENDING` reaching empty closes ADR-0298's deferral for good**; graduating
a module is a deliberate two-place edit, exactly like the SVG ledger.

## Consequences

- **Measured (real chromium, `test_dom_captions.py`):** the slot renders on all four opted-in
  pages — token 11px, uppercase, its box ENDS above the first tier band — and workbench's
  ribbon caption renders in the same voice; `/analysis` renders no slot. **Proved able to
  fail, watched:** a dropped marker fails the server pin AND the ledger count; the pre-slot
  `gantt.js` fails the ledger detector; during development the slot assertion itself failed
  three distinct ways (`/path`/`/driving-path` draw NO timescale without a target/trace — the
  fixture now sets target 143 and traces 142 → 143, and the vacuity is recorded in the test).
- `/workbench`'s recorded rank-12 blocker (ADR-0311) is CLEARED: per DESIGN-SYSTEM §3:78
  tables get `⤓ EXCEL` only (already shipped), so its remaining owed work is the read-me
  line + ▦/⛶ decisions in the toolbar sweep PR.
- The `/sra` page's timescale caption applies page-wide by design (one marker per page);
  the SSI grid is the page's only tier-scale visual today — a second tier-scale visual on
  a marked page would share the same axis meaning by construction (same schedule dates).
- DESIGN-SYSTEM §4 states the per-medium rule; the seven `DOM_PENDING` modules remain the
  DOM medium's open ledger, mirrored on the SVG `PENDING` (four modules, batch 3c).
- **Version 1.0.141 → 1.0.142**, wheel + nine installers regenerated (ADR-0148 lockstep).
