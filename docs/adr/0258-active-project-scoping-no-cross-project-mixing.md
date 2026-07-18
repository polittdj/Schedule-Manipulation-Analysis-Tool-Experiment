# ADR-0258 — Active-project scoping: no cross-project mixing outside Portfolio

## Status

Accepted. Implements the master-prompt "Portfolio View, Multi-File Data Integrity" workstream's
core residual gap on top of ADR-0225's grouped ingestion. Operator decisions taken in-session
(2026-07-18): scope = full residual gap set with the US map deferred; multi-project UX =
auto-select-newest with an always-on banner switcher (consistent with ADR-0225's standing
"never block, nag, or ask" rule, chosen over a literal "block until chosen" reading).

## Context

ADR-0225 grouped loaded files into Projects — but only as a *display* layer on `/portfolio`.
`SessionState.ordered()` / `ordered_versions()` still fed **every loaded file across all
Projects** into one version series, so with several projects loaded (the operator's real run:
five), every multi-version page — trend, S-curve, CEI, evolution, forecast, performance — blended
unrelated projects into one "series". The provenance banner (ADR-0150, operator 2026-07-16)
honestly listed the mixed files, but the numbers themselves were cross-project nonsense.

## Decision

- **Analysis populations are ACTIVE-population-only.** `SessionState.active_project` stores a
  stable `Project.pid` (new on `engine.projects.Project`: `folder:<name>` /
  `title:<normalized title>` / `file:<session key>` — derived only from inputs that don't change
  as more files load). `ordered()`/`ordered_versions()` restrict to the resolved active
  population's keys (and drop ADR-0259 excluded keys). With **0–1 populations loaded and nothing
  excluded the filter returns `None`** — the fast path, and the proof single-project sessions
  behave byte-identically to before (existing suites pass unchanged; Law 2 untouched — no engine
  math changed anywhere).
- **Title-less loose files pool into ONE explicit "(untitled files)" population**
  (`SessionState.populations()`, sentinel pid `untitled:`). They carry no project-identity
  signal, and the full 2384-test suite proved the alternative wrong: treating each ADR-0225
  needs-attention singleton as its own analysis population shattered the tool's original core
  workflow (drop N untitled exports of one schedule — the bundled example, the tool's own older
  JSON saves) into N one-file "projects". So: **identified Projects (folder/title) never mix,
  with each other or with untitled files; all untitled loose files analyze together, loudly
  labeled "(untitled files)" in the banner** (Portfolio keeps listing each as its own
  needs-attention row per ADR-0225 — that operator rule is unchanged). A session of only
  untitled files is one population — the pre-scoping behavior exactly.
- **Manifest views split off.** New `all_versions()` serves the session MANIFEST (home's
  loaded-schedules table + dashboard health cards — each card is self-contained per file, nothing
  blends). `/portfolio` (via `projects()`) stays the ONLY cross-project analysis page.
- **Auto-select newest, never block.** After an accepted upload with >1 Project, the Project
  containing the last accepted file becomes active, said loudly in the import manifest. The
  always-on banner gains a PROJECT strip: active title, switcher dropdown, project count,
  Portfolio link, pending-review count. The switch posts `/project/select` with an explicit
  `next_url` (the app sends `Referrer-Policy: no-referrer`, so Referer-based returns are
  impossible — validated local-path-only, no open redirect). Portfolio rows gain "Analyze this
  project". A session-wide Target UID that doesn't resolve inside the newly selected project is
  cleared through `set_target` (its scope memo resets); one that resolves is kept.
- **Cache discipline (deep-perf P1-safe).** Selection is population-only: the per-key
  `analyses`/`summaries` caches stay valid across a switch; **no new invalidation was added
  anywhere** (`_invalidate_scope` untouched).
- **Title collisions across origins get notices, never merges.** A folder "X" plus a loose file
  titled "X" stays two Projects (a folder is exactly one Project by the operator's rule; merging
  would be a guess) — but both rows now carry a notice saying why two same-named Projects exist.
  The reported "filename equals folder name" fault was pinned by test: a folder "X" *containing*
  "X.mpp" is one Project, no collision.

## Consequences

- Loading N files across three real projects yields exactly three selectable Projects; every
  analysis page draws from ONE of them; switching visibly changes the population; `/portfolio`
  still shows all — the master prompt's Phase-1/Phase-2 acceptance, encoded in
  `tests/web/test_project_scope.py` and browser-verified live (Chromium, two projects + a
  byte-identical dup: zero failures, zero new console errors).
- Multi-project sessions see different numbers on multi-version pages than before **by design** —
  that was the defect. Single-project sessions are unchanged.
- Known pre-existing follow-up (surfaced, not caused, by scoping — verified on an untouched
  single-file load): the `/mission` wall's multi-version tile APIs (scurve/cei/trend/evolution)
  return 4xx console noise when the population has one version. The tiles should degrade to a
  "needs ≥2 versions" note; deferred, documented in HANDOFF.
- Tests: engine pid/collision pins; web scoping acceptance (three projects, switch, fail-soft
  unknown pid, open-redirect guard, single-project no-op, wipe reset). Version 1.0.66 → 1.0.67;
  wheel + 9 installers in lockstep.
