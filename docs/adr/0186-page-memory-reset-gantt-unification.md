# ADR-0186 — Per-page selection memory, universal Reset view, Gantt feature unification

## Status

Accepted. Operator 2026-07-10: (1) "When a user goes to any one of the pages and inputs
information such as Target UID or whatever I want those selections to remain in the tool's
memory so that if they switch to another page and then come back the information they input is
still there as well as the views." (2) "On all of the Gantt charts as well as on all of the
various pages I want you to add a reset button that clears all of the selections that you have
made and takes you back to the default view." (3) "I WANT ALL VIEWS OF ALL GANTT CHARTS TO
MATCH THE VIEW AND THE FUNCTIONALITY OF THE GANTT CHART FOUND ON THE DASHBOARD PAGE WHEN YOU
SELECT A SPECIFIC PROJECT FILE… ADD THE ONES THAT DONT EXIST" — explicitly including the
Critical-Path Evolution page and its CP Gantt.

## Decisions

1. **`static/persist.js` — two-layer page memory**, loaded by the shared layout on every page,
   all state in `localStorage` (this machine only — air-gap safe):
   - *Query-string memory* (`sf-qs:<path>`): server-applied selections travel in the query
     string (`?target=`, `?file=`, `?group_field=`, `?tier=`, A/B pickers …). Leaving a page
     with a query string saves it; returning through a bare nav link `location.replace`s to the
     remembered query so the server re-renders the remembered view. `/groups` is excluded (the
     group filter is session-wide server state; replaying an old `?apply`/`?clear` would fight
     it) and one-shot `clear`/`apply` params are never replayed.
   - *Control memory* (`sf-ui:<path>`): every value-bearing control (text/number/checkbox/
     radio/select/range/textarea) is recorded on change/input and restored on the next visit,
     then a change/input event is dispatched so the page's own listeners repaint; a
     `sf-restored` window event lets boot-time-only readers react (path.js re-traces a
     remembered Target UID). Excluded: file/password/hidden inputs, the nav Target-UID /
     language / wipe forms (server session state), and `data-sf-nopersist`.
   - *Known limitation*: SFChecklist popup selections (per-column value filters, tier and
     Columns pickers) live in page JS Sets, not form controls, and are NOT remembered by this
     layer — persisting them needs checklist-level state and is future work. The Reset button
     still clears them (a bare reload resets in-memory state).
2. **Universal Reset view** — persist.js injects one `⟲ Reset view` button (top-right of
   `<main>`, i18n'd) on EVERY page: clears the page's `sf-qs`/`sf-ui` keys plus the page's own
   persisted column-picker keys (`sf-res-drill-cols`, `sf-findings-drill-cols`,
   `sf-whatif-*-cols`, `sf-ribbon-drill-cols`, `sf-driving-tiers-cols`), then loads the bare
   path — the default view. Global preferences (theme, UI size, Timescale config) are not page
   state and keep their own resets.
3. **Shared Task Information dialog (`static/taskinfo.js`, `window.SFTaskInfo`)** — the
   MS-Project tabbed popup extracted verbatim from app.js (ADR-0183) with two entry points:
   `open(act)` for pages whose rows already carry the full `_activity_rows` payload, and
   `openFrom(file, uid)` which fetch-caches `/api/analysis/<file>` (the server resolves session
   key OR display label) and joins by UniqueID — with an honest "UID n is not present in
   <file>" dialog on a miss (e.g. a removed task's ghost row). app.js now delegates.
4. **Gantt unification** (add what's missing, never duplicate):
   - `/path` — row-click Task Information (via the page's schedule picker), Find-UID jump +
     flash, dates-on-bars toggle, and an `sf-colmove` model listener so a header column move
     survives repaints (previously the DOM fallback was undone by the next paint).
   - `/driving-path` corridor — row-click Task Information sourced from the STEPPED version's
     file, Find-UID jump, dates-on-bars toggle.
   - `/sra` grid — Task Information on the non-editable UID/name cells (rows already carry the
     full payload; editable cells keep click-to-edit), show-completed-tasks toggle (same rule
     as the Activities grid), Find-UID jump, dates-on-bars (bars + BC/WC envelope untouched).
   - `/evolution` CP Gantt — click a bar or its name label for Task Information (critical rows
     cite the CURRENT version's file; "left the path" ghost rows cite the PRIOR version's file,
     where their geometry comes from), dates-on-bars at the SVG bar ends. Its search filter IS
     the find; zoom/pan/stepper/hide-completed already existed.
   - Deliberately NOT added: dependency link lines on the corridor and evolution charts — those
     payloads carry no per-row logic data, and drawing connectors between consecutive bars
     would fabricate logic that may not exist (Law 2). The SRA grid's links likewise stay off
     pending a real need (its rows carry predecessors, so it is cheap to add later).
5. **Find-UID flash CSS generalized** (`tr.row-found` was `#grid`-scoped); `Reset view` added
   to the i18n catalog (ES/FR/DE/PT).

## Consequences

- Selections and views survive page switches on every page; one obvious button returns any
  page to its default; every Gantt now opens the same Task Information dialog and carries the
  dashboard Gantt's find/dates-on-bars/show-completed interactions where they were missing.
- Verified end-to-end in Chromium (17 checks, zero console errors): control + query-string
  memory, reset, evolution/SRA/path Task Info with provenance footers, SRA hide-completed
  (145→114 rows), path auto-retrace of a remembered target.
