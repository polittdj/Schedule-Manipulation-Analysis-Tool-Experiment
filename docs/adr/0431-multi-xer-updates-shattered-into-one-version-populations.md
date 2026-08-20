# ADR-0431 — Multi-.xer updates shattered into one-version populations: the P6 Project ID is a per-copy value, not a project identity

**Status:** Accepted · **Date:** 2026-08-20 · **Extends:** ADR-0185 (Activity-ID identity), ADR-0258 (active-project scoping)

## Context

Operator report (2026-08-20): with multiple `.xer` files loaded, Mission Control's cross-version
visuals stay dark — "Needs at least two loaded versions of the active project — load another
schedule update to activate this visual" — while the S-Curve reads "1 / 1". The same workflow
with `.mpp`-derived MSPDI versions activates everything.

Root cause, proven by executable check before any code changed
(`tests/web/test_xer_version_grouping.py` observed RED on the unmodified tree):

| Link in the chain | Where | Fact |
| --- | --- | --- |
| Cross-version populations are ACTIVE-project-scoped | `web/state.py::_analysis_population` (ADR-0258) | with >1 population loaded, only the active one's versions reach `ordered()` |
| Loose files group into projects by title | `engine/projects.py::_norm_title` | case-fold + trim of `Schedule.project_title`, nothing else |
| XER filled `project_title` from `proj_short_name` | `importers/xer.py` | P6's **Project ID** — unique per EPS, so the standard per-update copy workflow gives every monthly export a NEW one |
| MSPDI fills it from `<Title>` | `importers/mspdi.py` | a document property that survives copies (or is absent → all files pool as `(untitled files)`) |

Two same-project synthetic updates with per-copy Project IDs (`JUICE-M02` → `JUICE-M03`)
reproduced the exact symptom: `[('title:juice-m02', ('v1',)), ('title:juice-m03', ('v2',))]` —
two one-version populations, every `< 2` gate firing. The irony is structural: because
`proj_short_name` is mandatory, a `.xer` never even reached the untitled POOL that would have
grouped it. ADR-0185 already documented this exact copy workflow renumbering `task_id`; the same
workflow renames the short name, and grouping had anchored on it.

## Decision

Three legs, each independently pinned:

1. **The XER project identity is the P6 project NAME** — the selected project's root `PROJWBS`
   row's `wbs_name` (`proj_node_flag=Y`, or the row whose parent is blank / outside the project's
   own rows), the true analogue of the MSPDI `<Title>`, which survives per-update copies.
   `proj_short_name` stays the fallback when no usable root exists, and `Schedule.name` keeps its
   historical short-name-first derivation, so display strings are unchanged
   (`tests/importers/test_xer.py`: preferred path, fallback, multi-project scoping). Because
   grouping is format-agnostic on `project_title`, an `.mpp` Title and a `.xer` project name that
   match now group CROSS-FORMAT — the operator's forward-looking `.mpp` ↔ `.xer` comparison works
   at the population level (`test_mspdi_and_xer_of_one_project_group_cross_format`).
2. **The operator can COMBINE loaded projects explicitly** — `POST /project/combine`
   (`SessionState.combine_projects`) re-labels the selected populations with one shared ingestion
   folder, the strongest grouping signal `engine.projects` knows, so the regular pipeline
   (data-date ordering, tiebreak notices, duplicate review) applies to the combined set unchanged
   and the combined Project becomes active. Rendered as a Portfolio panel only when there are two
   or more populations. Fail-soft on unknown/too-few pids and a blank name. Automatic grouping
   still never merges differing names on its own — this route IS the operator saying so.
3. **Mission Control's degrade note names where the other files went** — with files grouped into
   other Projects, "load another schedule update" alone was a silent mystery while updates sat
   loaded. The note now appends the count and the two remedies (combine in Portfolio, or switch
   the active Project); the base sentence stays one exact-match text node so its i18n catalog
   entry keeps translating.

## Consequences

- Same-project `.xer` updates whose root project name is stable form one multi-version population
  automatically; every cross-version view (Mission Control, /trend, /cei, /evolution, /compare)
  activates.
- Files whose internal names genuinely differ still separate — honestly — and the operator has a
  one-click merge with a visible explanation on the wall.
- `test_project_title_is_the_project_short_name` became
  `test_project_title_falls_back_to_the_short_name_without_a_projwbs_root` — the fallback pin.

## Deliberately NOT done

- **No filename-stem or date-stripping heuristics** — ADR-0258 rejected guessing, and this ADR
  keeps that: identity comes from the file's own declared name or from the operator.
- **Sibling pages' degrade notes** (/trend, /cei, /evolution, /volatility, /integrity gates)
  still print the bare two-version sentence; only Mission Control (the reported surface) gained
  the other-projects tail. Carried forward as a follow-up.
- **No un-combine control** — a combine is reversed by wipe/re-upload, matching folder uploads,
  which carry the same signal from ingestion. Recorded so the absence reads as a decision.
- **UNVERIFIED against the operator's actual JUICE files** (not in the repo): if their per-update
  exports rename the project NAME as well as the ID, automatic grouping still separates them and
  the combine override is the remedy. The operator should re-load those files on this build.
