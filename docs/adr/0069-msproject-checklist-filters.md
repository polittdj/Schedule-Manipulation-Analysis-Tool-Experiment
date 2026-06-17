# ADR-0069 — MS-Project-style dropdown checklist filters (select-all / clear / search)

Date: 2026-06-17 · Status: accepted

## Context

Operator backlog item B: *"MS-Project-style dropdown filters (select-all / deselect-some
checklists) replacing the substring filter inputs on the grid + path tier filter."*

State before: the `/analysis` activity grid filtered each column with a **substring text input**
(with a `>n` / `<n` numeric-comparator escape hatch), and both tier filters (`/path` `#pathTier`,
the `/analysis` trace `#ganttTier` added in ADR-0068) were single-choice **`<select>`s** — so you
could show *one* tier but not, say, DRIVING + SECONDARY together. The operator wants the familiar
MS-Project column-filter UX: a dropdown listing the column's **distinct values as checkboxes**,
with **Select-all / Clear** and a search box.

## Decision

1. **One reusable component (`static/checklist.js`, `window.SFChecklist`).** `SFChecklist.filter(opts)`
   returns a button + a popup with a **search box**, **All / None** links, and a **checklist** of
   the supplied distinct values. `onChange` is called with the selected-value `Set`, or `null` when
   **all** are selected (column unfiltered); an **empty Set** hides every row. The popup is
   `position: fixed`, placed off the button's client rect so it **escapes the grid's `overflow:auto`
   clipping**, and closes on outside-click / Escape / scroll / resize. All / None act on the rows
   currently visible under the search, so "search + All" is a quick bulk select. Dependency-free and
   same-origin — loaded once from the page shell `<head>` so both the grid and the tier filters
   reuse it (added to the air-gap scan).
2. **`/analysis` grid (`app.js`).** The per-column substring inputs are replaced by
   `SFChecklist.filter` over each column's `distinctValues()` (numeric- and ISO-date-aware sort).
   `filters[key]` is now a selected-value `Set | null`; `rowMatches` is a simple membership test.
   The old `>n` / `<n` comparator syntax is retired with the substring inputs (MS Project uses the
   checklist; range filters can return later if asked).
3. **Tier filters become checklists.** `/path` `#pathTier` and the `/analysis` trace `#ganttTier`
   are now `<span>` mount points carrying a four-tier checklist (DRIVING / SECONDARY / TERTIARY /
   BEYOND); selecting a subset shows exactly those tiers. The page filter logic keys off the
   selection `Set` (`pathTierSel` / `ganttTierSel`).

## Scope / safety

Pure presentation (HTML/JS/CSS) — no engine/CPM/metric change, so **parity is untouched (10/10)**.
`checklist.js` is dependency-free and same-origin (air-gap scan extended over it and still passes).
Tests: a new `test_visuals` case pins that `checklist.js` is served + shell-loaded on both pages,
that `app.js`/`path.js` use `SFChecklist.filter` (the old substring input + single-tier `<select>`
reads are gone), and that the popup CSS is present. Full suite green; engine cov 97%;
ruff/format/mypy/bandit clean.

Remaining backlog (own PRs): the `/path` driving-chart visual defect (item A's first half, awaiting
the operator's screenshot), the Fuse year Trend/Phase view (D), the Data-Date/Slippage overlaid-line
redesign (E), and Bow-Wave running totals + target-UID highlight (F). Insufficient Detail™ /
Float Ratio™ / EPI / RatioMeasure stay deferred pending the exact Fuse/DAX definition.
