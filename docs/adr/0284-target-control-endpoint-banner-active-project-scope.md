# ADR-0284 — the Analysis-Target control and endpoint banner scope to the active project (Fix E)

Status: accepted (2026-07-24) — closes the deferred "Fix E" from ADR-0281

## Context

ADR-0258 established that with more than one project loaded, only the **active** project's versions
enter any analysis population (no cross-project mixing anywhere but Portfolio), funnelled through
`SessionState.ordered()` / `ordered_versions()`. Two page-chrome helpers were missed by that
narrowing and kept iterating **`state.schedules.values()`** — every loaded version across **every**
project:

- **`_render_target_control`** built the milestone dropdown from all projects' milestones. Because it
  keys the dropdown by `unique_id` and keeps the first label seen, a UniqueID that exists in more
  than one project (e.g. a "Project Complete" milestone at UID 100 in both) could show a **foreign
  project's label** while a different project is active — a real cross-project identity leak.
- **`_endpoint_banner`** computed its "N of M activities shown; K omitted" population over all
  projects, so with a Target endpoint active the omitted-count described the whole session, not the
  project actually being analysed, and a UID present only in a *non-active* project still marked the
  endpoint "found."

A characterization test (`test_target_control_and_banner_scope_to_active_project`) was committed
`xfail(strict=True)` under ADR-0281 to pin the leak until this fix.

The operator's decision (2026-07-24): the target dropdown should list **only the active project's**
milestones (Option "active project only"), not every project's with per-project-scoped UIDs. A target
milestone from another schedule is not meaningful for the active schedule's CPM/analysis, and scoping
by construction removes the leak.

## Decision

Both helpers now iterate **`state.ordered_versions()`** (the active project's versions, ADR-0258
narrowing applied, operator-excluded versions dropped) instead of `state.schedules.values()`:

- The dropdown lists milestones across the **active project's** versions only (still the union across
  *versions*, so a milestone deleted in a later version stays selectable) — no other project's
  milestone, and no foreign label for a shared UniqueID, can appear.
- The banner's `total` / `kept` / omitted counts, and its "endpoint found" check, are computed over
  the active project's population.

`ordered_versions()` takes the session `RLock` (reentrant), so calling it from the render path is
deadlock-safe whether or not the caller already holds the lock. The `xfail` marker is removed; the
test now asserts the fix directly.

## Consequences

- With a single project loaded (or one populated project) `ordered_versions()` returns every loaded
  version — **behaviour is unchanged** for the common case; only genuine multi-project sessions are
  affected, and there the change is the intended fix.
- A Target UID that exists **only** in a non-active project now reads as "not found" in the banner
  while that project is inactive. That is correct under the active-project-only model: the UID is not
  in the analysed population. Switching the active project (or clearing the endpoint) restores it.
- The UID box still measures to *any* UniqueID within the active project's versions; the dropdown is
  the milestone shortcut, now leak-free.

## Verification

`tests/web/test_dashboard_perf_contract.py::test_target_control_and_banner_scope_to_active_project`
(previously `xfail`): with Alpha + Beta both carrying UID 100 and Beta active, the control omits
Alpha's "ALPHA COMPLETE" label and the banner reports Beta's 2 activities, not all 4. The full web
suite and the single-project golden dashboard payloads are unchanged.
