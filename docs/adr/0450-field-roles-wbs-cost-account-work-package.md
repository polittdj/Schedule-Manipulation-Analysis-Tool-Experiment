# ADR-0450 — Field ROLES: the operator picks which field is the WBS, the Cost Account and the Work Package

- **Status:** Accepted — 2026-09-02 (operator item 5 of six)
- **Version:** 1.0.229
- **Shipped:** `engine/grouping.py` (`ROLE_LABELS`, `role_labels`, `resolve_roles`), `engine/metrics/wbs_breakdown.py` (`compute_wbs_breakdown(schedule, wbs_field=None)`), `web/state.py` (`field_roles`, `set_field_roles`, resolution in `_match_uids`, the mapping in the scope signature), `web/app.py` (`POST /fields/roles`, `_field_roles_panel` on /groups and /wbs, the WBS pivot/JSON/export follow the role, float erosion defaults to it, `/api/group-values` resolves a role name, the /groups field menu offers mapped roles), `tests/engine/test_field_roles.py` (4), `tests/web/test_field_roles_page.py` (3)

## Context

"The standard WBS field in MS Project or P6 is not always the field that the user will use for the project.
Sometimes the user will create a custom field and custom WBS. I also want the user to be able to filter for
Cost Account and Work Package in the same ways." The engine already had the shape once (ADR-0150: float
erosion groups by any field via `field_value`); nothing else honoured it, and the filters had no notion of a
Cost Account or Work Package at all.

## Decisions

1. **A session-level role map** `{wbs | cost_account | work_package → field label}` over every standard +
   custom field the loaded files offer. Blank = default (stored WBS column / role not offered). A field no
   loaded file carries is DROPPED, never guessed. Project-specific, so a wipe resets it (ADR-0332's default).
2. **The WBS role redirects the WBS pivots** — `/wbs/{name}`, `/api/wbs/{name}`, `/export/{fmt}/wbs/{name}`
   — and is the float-erosion default. `_top_level` of the mapped field's value; an unmapped task lands in
   `"(none)"`, last, exactly as with the stored column.
3. **Cost Account / Work Package are filter FIELDS BY NAME** when mapped: the /groups menu lists them,
   the autocomplete resolves them, and `resolve_roles` maps a criterion's role name to its column at match
   time. An unmapped role name stays as written and matches nothing — a stale filter can never fall back to
   the WBS column silently. The mapping joins the scope signature, so a role change re-keys the epoch.
4. **Found and fixed on the way (QC-2): the WBS pivot ignored the session scope.** The page, its JSON and
   its export read the RAW schedule while every banner promised "every metric on every page" is scoped; the
   three now read `st.scope(sch)`. No ADR recorded the unscoped reading as a decision.

## Consequences

- Picker on /groups (all three roles) and a compact WBS-only picker on the /wbs page; posts redirect back.
- Not done: the XER importer exposes only "Activity ID" as a custom field, so P6 users get the WBS path or
  Activity ID as role targets; P6 activity codes are not imported yet — stated, a follow-up.
