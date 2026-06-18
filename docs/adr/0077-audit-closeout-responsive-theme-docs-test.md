# ADR-0077 — Audit close-out: responsive reflow (A9), theme polish (A10), docs-drift test (A11)

Date: 2026-06-18 · Status: accepted

## Context

The final three items of the external audit work order (A1–A8 + CSP shipped in
#133–#136 / ADR-0073–0076):

* **A9 (WCAG 1.4.10 reflow).** Only one media query existed; the header (13 nav links + 2 forms +
  2 buttons) didn't collapse and several card grids hard-coded `minmax(440px,1fr)` columns, so at
  **200% zoom** (a real AA criterion) the page needed horizontal scrolling.
* **A10.** The theme toggle had no `aria-pressed`, and a first visit hard-coded **dark**, ignoring
  the OS `prefers-color-scheme`.
* **A11.** `docs/STATE/HANDOFF.md` is the single source of truth a session resumes from, but the
  state-doc test only checked the *latest ADR token* in one file — so an ADR could ship while the
  append-only SESSION-LOG was skipped, and the doc could drift.

## Decision

Presentation-only, dependency-free, same-origin:

1. **Responsive reflow (`base.css`).** A `@media (max-width:760px)` block wraps the header + nav
   (`flex-wrap`) and collapses the wide grids (`.dash-cards`/`.brief-cards`/`.card-cols`/
   `.qual-drill-grid`) to a **single column**. Because 200% zoom roughly halves the CSS viewport,
   this also satisfies the zoom-reflow criterion — no horizontal page scroll on a normal window
   zoomed to 200%.
2. **Theme polish (`theme.js`).** The toggle now sets **`aria-pressed`** (true when light is active),
   and a **first visit follows the OS** color scheme (`prefers-color-scheme: light`) instead of
   hard-coding dark; a saved choice still wins and still applies before first paint (no flash).
3. **Docs-drift test (`tests/test_state_docs.py`).** Anchored on the ADR files (local ground truth,
   no network), the latest ADR must now appear in **both** HANDOFF **and** the append-only
   SESSION-LOG — catching an ADR that ships without its session being logged (the drift class the
   audit flagged). The HANDOFF-staleness half (wrong PR number) was already corrected by the
   #128–#136 doc updates.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. Air-gap unchanged. Tests
(`tests/web/test_accessibility.py`, `tests/test_state_docs.py`): the responsive `max-width:760px`
block collapses the grids; `theme.js` carries `aria-pressed` + `prefers-color-scheme`; the latest
ADR is referenced in both durable docs. Full gate green; ruff/format/mypy/bandit clean.

**The external audit (A1–A11) is now fully addressed** (A1/A2/A6/A8 #133, A7 #134, A3 #135, A4/A5
#136, A9/A10/A11 here). A3 data-table fallbacks beyond the curves page remain an easy follow-up with
the shared `SFA11y.table` helper. The operator's feature backlog (`/path` chart screenshot bug; D
Fuse year Trend/Phase; E Data-Date/Slippage overlaid lines; F Bow-Wave totals) is next; the deferred
Fuse-proprietary metrics still await the exact DAX.
