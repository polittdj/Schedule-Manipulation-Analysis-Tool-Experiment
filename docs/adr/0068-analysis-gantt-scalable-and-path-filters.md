# ADR-0068 — /analysis Gantts go scalable (px/day + scroll); path tier filter + full wrapped names

Date: 2026-06-17 · Status: accepted

## Context

Operator backlog, the **bugs-first** tranche (item A scaling defect + item C path filters):

- **Bug (item A):** the per-project **`/analysis`** page rendered BOTH its **driving-path trace**
  (`#gantt`) and its **activity Gantt** (`#grid` timeline column) by squeezing the whole project
  span into a **fixed-width column as a percentage of span** (`renderGantt` used
  `((start_ord-lo)/span)*100`; `timelineCell`/`monthTicks` used `pct(range, t)`). There was **no
  adjustable scale and no scroll**, so on a long program every bar collapsed into a few
  unreadable pixels. The `/path` workspace already had the right model — a user-adjustable zoom
  in **pixels per day** with **horizontal scroll** — so the fix is to bring `/analysis` to that
  same model.
- **Feature (item C):** `/analysis` should also get a **Primary/Secondary/Tertiary tier filter**
  on the trace, **hide-completed**, an **adjustable time scale**, and **full wrapped task names**;
  `/path` should get **full wrapped task names** (it already had tiers / hide-completed /
  px-per-day zoom).

The separate `/path` driving-chart defect (its bars/tiers reading wrong) is a *visual* one that
cannot be verified inside the air-gapped container; a screenshot is owed by the operator and that
half is tracked as a follow-up commit on the same draft PR.

## Decision

1. **`/analysis` Gantts use the `/path` px-per-day + scroll model (`static/app.js`).** A shared
   `buildAxis(items, anchorDate)` builds a horizontal time axis from each row's ISO `start`/`finish`
   (padded ±2 days, stretched to include the data date) and returns `x(ms)→px` plus the full `width`
   the track/scale must occupy. `pxPerDay()` reads a single page-level **Scale** slider (`#vizZoom`,
   2–40 px/day, default 8). `timelineCell` and `monthTicks` were rewritten to position bars,
   milestones, the data-date line, and month ticks in **pixels**; the grid table now scrolls
   horizontally (`#grid { overflow-x: auto }`). The driving-path trace (`renderGantt`) was
   rewritten the same way: a name column + a px-wide track per row inside one `.gantt-scroll`
   horizontal scroller, on the same axis. Bars now keep a true, legible time scale at any zoom.
2. **Pixel-true alignment.** The timeline header (`.g-head`) and body cells (`.g-cell`) share
   **zero horizontal padding** so the month ticks line up exactly over the bars (both hold a
   px-wide div driven by the same `axis.x`); the trace header spacer matches the row name column
   width so its scale lines up over the tracks.
3. **`/analysis` trace gains a tier filter + adjustable scale + wrapped names.** A `#ganttTier`
   `<select>` (all / DRIVING / SECONDARY / TERTIARY / BEYOND) filters the trace rows; the existing
   **show-completed** toggle (unchecking = hide-completed) is preserved; the `#vizZoom` slider is
   the adjustable scale; trace task names are no longer truncated to 22 chars — they wrap to full
   text (`.gantt-name`). The activity grid Name column wraps too (`td.name-cell`).
4. **`/path` task names wrap (`static/path.js`).** The Name column cell is tagged `pv-name` and
   wraps to its full text (`.path-grid td.pv-name`); the other columns stay nowrap.

No API change: both pages still read the same `/api/driving` payload (which already carries ISO
`start`/`finish`, `finish_ord` for the waterfall sort, tier, and the robust `complete` flag) and
`/api/analysis`.

## Scope / safety

Pure presentation (HTML/JS/CSS) — no engine/CPM/driving-slack/metric change, so **parity is
untouched (10/10)**. The JS stays dependency-free and same-origin (air-gap intact). Tests: new
`test_visuals` cases pin that `app.js` uses the scalable model (`pxPerDay`/`buildAxis`/
`gantt-scroll`, no `% of span` math remains), that `/analysis` exposes the `#vizZoom` scale and
`#ganttTier` filter with the horizontal-scroll CSS, and that the Name column wraps on both `/path`
and `/analysis`. Full suite **908 passed**, 3 skipped; engine cov 97%; overall 95%;
ruff/format/mypy/bandit clean.

Remaining (own PRs): the **`/path` driving-chart visual defect** (item A second half — awaiting the
operator's screenshot), MS-Project dropdown checklist filters (item B), the Fuse year Trend/Phase
view (item D), the Data-Date/Slippage overlaid-line redesign (item E), and Bow-Wave running totals
+ target-UID highlight (item F).
