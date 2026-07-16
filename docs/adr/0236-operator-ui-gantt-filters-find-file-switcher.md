# ADR-0236 — Operator UI directives: Gantt filter fix, find-by-name, per-file switcher (PR-U1)

## Status

Accepted. The operator's 2026-07-16 NEXT-PROMPT directives ("put this to memory"): the Gantt
filter buttons "don't work", every Gantt needs find-a-task-by-name(-part), and per-file pages must
never read as if they mix all loaded files — "Where We Stand" needs a file chooser.

## Context / root cause

1. **The "dead" filter buttons were a self-close race, not broken wiring.** A read-only audit
   verified every filter control is `addEventListener`-wired with matching ids and the CSP allows
   inline JS — the markup was innocent. The real mechanism: the checklist popup is
   `position:fixed`, and a capture-phase `window` scroll/resize handler closes it; on a Gantt the
   freeze-column/sticky-scrollbar layers (and focusing the popup's search box, which scrolls it
   into view) fire exactly such an event in the same beat the popup opens — it closed before it
   ever painted, so the button looked dead.
2. Find existed only as **UID-exact** jumps (`gridFind`/`pathFind`/`dpFind`); /path alone had a
   name substring row filter.
3. The always-on provenance banner said "computed from the N loaded files (oldest first)" even on
   the per-file `/analysis` page ("Where We Stand"), implying mixed data, and the page offered no
   way to switch files.

## Decision

1. **checklist.js:** a 400 ms grace window after opening ignores scroll/resize-driven closes
   (`closeUnlessJustOpened`), and the search box focuses with `preventScroll` so opening cannot
   scroll-close itself. A real user scroll still closes the popup; in-popup list scrolling still
   never does. Verified in Chromium: the popup now stays open and filters apply.
2. **`SFGantt.findTask(container, query, status)`** — one shared find for every Gantt grid: a
   pure-integer query jumps to that UniqueID; any other text (or unknown UID) marks EVERY row
   whose text contains it (case-insensitive) with `row-found`, scrolls the first into view, and
   reports the match count. `gridFind`/`pathFind`/`dpFind` all route through it; the inputs became
   free-text "UID or name…". (/evolution already had a name search mode.) Chromium: "found" →
   6 rows marked, "6 matches".
3. **Per-file banner + switcher:** `_page(..., focus_file=)` lets a per-file page replace the
   N-files banner with "This page shows ONE file: <file> — switch file: <select>" plus the note
   that versions are compared on Trend/Compare/Evolution, never mixed. `/analysis` (Where We
   Stand) passes its key; the cross-version pages keep the honest aggregate wording (they ARE
   multi-file by design — the operator's animation-based comparison). Other per-file pages adopt
   the same parameter as they are touched.

## Consequences

- The filter dropdowns work on every Gantt (analysis grid, path, evolution, driving-path — all
  share checklist.js), find is name-capable everywhere, and "Where We Stand" both names its file
  and switches files in place.
- The remaining named pages from the directive (per-file focus on /cei, /volatility, /trend,
  /mission where sensible) ride later UI PRs via the same `focus_file` parameter — those pages
  are genuinely cross-version, so each needs a deliberate call on what "focus" means.
