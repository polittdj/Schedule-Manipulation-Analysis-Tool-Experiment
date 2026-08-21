# ADR-0438 — /driving-path opens on the complete schedule of ANY loaded file: the /path workspace embeds, the File picker spans every Project

**Status:** Accepted · **Date:** 2026-08-21 · **Extends:** ADR-0432 (/path whole-schedule default), ADR-0258 (active-project scoping), ADR-0416 (no inline handlers)

## Context

Operator ask (2026-08-21), verbatim in intent: on the driving path page, *show the full schedule
of whichever project or schedule the user chooses — any of the ones loaded — the full-schedule
Gantt by default like in What-drives-the-date, with the same columns by default.*

Measured baseline: `/driving-path` with no UIDs rendered a form plus the idle hint ("Enter a
source and a target UniqueID…") and nothing else; its File picker rendered only the **active**
project's solvable versions (ADR-0258 scoping through `_solvable_versions`), keyed by display
label — so a schedule in any other loaded Project was not reachable from this page at all.
`/path` already had the whole-schedule default (ADR-0432) with the operator's column set.

## Decision

1. **The no-target state embeds the SAME workspace `/path` renders** — `_path_body` + `path.js`,
   appended by the route after the trace form/hint. "Same columns by default" is true **by
   construction** (one `FIELDS` table in one script serves both pages) and is still asserted
   **rendered**: the browser test reads `/path`'s header row as the oracle and requires
   `/driving-path`'s to equal it, never retyping the list. The workspace's Schedule select
   offers **every loaded session key** (`all_versions()`), preselecting the page's chosen file,
   else the active project's latest (the same anchor the tiers use); switching redraws
   client-side with no reload, and a UID click traces exactly as on `/path`.
   `_path_body` gained only a keyword `selected:` (default `None` keeps `/path` byte-identical —
   the r11 freezes over `/path` did not move).
2. **The trace form's File picker spans every loaded schedule**, grouped by Project
   (`<optgroup>`) when more than one is loaded. The option **value** became the session key —
   unique where filename labels can collide across folders — while `?file=` accepts key OR
   legacy label via the existing `_find_schedule`, so bookmarked label URLs keep working
   (pinned). A cross-project pick resolves through `cpm_scoped_for(key, …)` (per-key analysis is
   not population-gated — the same fact `/api/driving/{name}` already relied on); an unsolvable
   pick degrades to the named skipped-notice and the population fallback.
3. **The tiers export key is the chosen file's own key**, cross-project included (the export
   route resolves any loaded key), replacing the label search that could only see the active
   population.
4. **The workspace renders ONLY when no target is traced.** A traced page belongs to the
   tiers/corridor views and their single `panelkit.js` include; the embed's own include serves
   the no-target state, keeping "one panelkit per page" true in both states (pinned both ways).
   The `?target=<absent from every version>` branch still renders zero controls and zero
   panelkit — the r11 absence census now names exactly that branch, since the no-target branch
   legitimately carries controls.
5. **Deliberate re-baseline** of the r11 `/driving-path` form freeze
   (`bee3c73c… /1905 → ccd40241… /1925`): the diff is exactly the option values (labels → keys)
   plus the select's title text.

Verification: 7 source pins red-first (`tests/web/test_driving_path_whole_schedule.py` — six
observed red on the unmodified tree; the absence invariant proven by mutation `if True`), the
rendered proof in chromium (`…_browser.py` — observed red by mutation `if False` suppressing the
embed, restored green), and a four-theme measured render (console/daylight/apollo/jarvis: grid
box, 3 rows/3 bars, 2 optgroups each).

## Consequences

- The page is useful the moment it opens — the complete schedule of the chosen file, MS-Project
  reading order, one pick away from any loaded Project's schedule — and the A→B corridor form
  keeps its role above it.
- Tracing A→B **in a file from another Project** now works end to end (scoping, tiers, banner,
  Excel export), one file at a time.

## Deliberately NOT done

- **`/path` is untouched** — its picker stays the ACTIVE population's versions: that page is the
  analysis chapter anchored on the active project (ADR-0199/0258), and widening it was not asked.
- **"All files (chronological)" still means the active population** for the corridor trace —
  cross-Project versions are never mixed into ONE evolution corridor (ADR-0258's rule); choosing
  another Project's file scopes the page to that single schedule instead.
- **No auto-submit on the File select** and no merging of the two selects: the form's File scopes
  the server-side trace, the workspace's Schedule drives the client-side Gantt; at page load they
  agree (the chosen file preselects both), and each is labeled by its job.
- **Whole-schedule mode still has no Excel/Word export** (ADR-0432's boundary): the export bar
  returns the moment a trace exists.
