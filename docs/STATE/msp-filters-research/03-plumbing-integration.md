I now have a complete picture of the plumbing. Here is the integration design.

---

# Feature #10 — Integration design: session-wide saved filters/groups, HIGHLIGHT mode, A→Z ordering

Scope of this section: how a faithfully-reproduced `SavedFilter` (a recursive criteria tree) and `SavedGroup` (multi-clause) plug into the **existing** session-wide scope plumbing so they reach every page and every file; how grouping becomes session-wide like the filter; how HIGHLIGHT mode marks instead of drops; and the A→Z ordering pass. The tree model (`model/saved_view.py`) and the faithful evaluator (`engine/msp_filters.py`) are contracts I *consume* here — their internals are a sibling topic. I reference them by the two entry points I need:

- `engine/msp_filters.select_saved(sch, saved_filter, prompt_values) -> frozenset[int]` — the saved-filter analogue of `grouping.select()` (`grouping.py:118`): the UIDs matching the tree, honoring recursive AND/OR, all 12 leaf ops, field-to-field, null/empty, and prompt substitution. It does **not** have `select()`'s `MAX_FIELDS` guard (`grouping.py:120`) — `_MCTasks` has 8 clauses.
- `model.saved_view.SavedFilter` / `SavedGroup` — frozen pydantic, `name: str`, plus the tree / clauses. Both carry `display_name` (accelerator `&` stripped) and `is_task_filter` / `show_summary_rows`.

---

## 0. The plumbing being extended (established facts, with lines)

- **`SessionState.active_filter: tuple[Criterion, ...]`** — `app.py:548`. `Criterion = (field, str|Sequence[str])`, a **flat AND-list** of field-in-values (`grouping.py:30`). This is the *only* filter representation today.
- **`scope(sch)`** — `app.py:591` — the single chokepoint every page funnels through. Fast-path guard `if not self.active_filter and self.target_uid is None: return sch` (`604`); reduce via `filter_schedule(sch, self.active_filter)` (`609`); optional target truncation (`610-615`); memoized by `id(sch)` in `_scoped` (`552`, `616`).
- **`filter_schedule`** — `grouping.py:127` — computes `kept = set(select(...))` (`134`) then **drops** every non-matching task and every relationship touching a dropped task (`135-139`). This is the "reduce" behavior HIGHLIGHT must bypass.
- Reach: `ordered()` (`659`) maps `scope` over every version (`666`); `analysis_for` (`697`) and `summary_for` (`709`) call `scope` (`701`, `719`). So **anything applied inside `scope()` reaches every page and every file automatically.**
- **`set_filter`** (`619`) replaces `active_filter` and clears `_scoped`, `analyses`, `summaries`, `polished` (`623-627`). **`set_target`** (`629`) mirrors it. **`wipe`** resets via `set_filter(())` at `app.py:5762`.
- **`_filter_banner`** (`772`) renders on **every** page — emitted in the layout body at `app.py:1809` — iterating `active_filter` as `(fld, value)` (`778`).
- **Grouping is per-page today**: `breakdown` is a `/groups` query param only (`groups_view` `app.py:3461`, `_groups_breakdown_table` `13570` → `group_values` `grouping.py:142`); `/forecast` has its own `group_field` param (`3505`). No session group state exists.
- **`/groups` route** `app.py:3448-3487`: parses filter rows into `param_criteria` (`3467-3473`), and `apply`/`clear` **mutate the session** via `set_filter` (`3476-3479`).
- **A→Z precedent**: `app.py:7282` `["WBS", *sorted(x for x in available_fields(sch) if x != "WBS")]`. But `available_fields` (`grouping.py:67`) returns `STANDARD_FIELDS` in insertion order then custom in file order; `_groups_field_options` (`app.py:13502`) renders that order verbatim. Value pickers are **already** sorted: `distinct_values` (`grouping.py:169`) and `group_values` (`157`).
- **Highlight idiom** (reuse target): `.path-grid tr.pv-selected` row shade + `td:first-child` inset bar, `.gantt-bar.pv-bar-selected`/`.g-ms.pv-bar-selected` outline — `app.css:1045-1048`, all tokens, 4-theme-safe. Driven by `selectedUid` (single UID) in `path.js:50`, applied in `paintOne` (`421-424`) and re-applied on every repaint by `reskinSelection` (`600-609`).
- **Registry home**: `Schedule.custom_field_labels` (`model/schedule.py:49`) is the pattern; add `saved_filters: tuple[SavedFilter, ...]` and `saved_groups: tuple[SavedGroup, ...]` as sibling frozen fields (populated by the importer from the MPXJ sidecar; sibling topic).

---

## 1. Coexistence — SavedFilter tree alongside the flat `active_filter`

### 1.1 Why they can't merge into one field

`active_filter` is `tuple[Criterion, ...]` — a flat AND of `(field, value-set)`. A `SavedFilter` is a **tree** with OR nodes, field-to-field comparands, prompts, 12 ordered leaf ops, and up to 8+ clauses. It is not expressible as `tuple[Criterion, ...]` and would trip `select()`'s `MAX_FIELDS=5` guard (`grouping.py:120`). So the two live **side by side** as two *sources* of one resolved scope, and `scope()` consumes whichever is set.

### 1.2 New `SessionState` fields (insert after `_scoped`, `app.py:552`)

```python
# --- Feature #10: saved (MS-Project) filters & groups, applied session-wide ---------------
# The session-wide SAVED FILTER: a faithful MS-Project criteria tree, the reproduction
# counterpart of the flat, field-based `active_filter` above. MUTUALLY EXCLUSIVE with it —
# setting one clears the other (two ways to name one session scope). None = no saved filter.
active_saved_filter: SavedFilter | None = None
# Operator answers for an interactive saved filter ("Date Range..." → 2 GenericCriteriaPrompts),
# keyed by the prompt's text. Empty until answered; passed straight to select_saved().
saved_filter_prompts: dict[str, str] = field(default_factory=dict)
# Filter MODE — applies to BOTH filter sources. "reduce" = today's behaviour (drop non-matching
# tasks). "highlight" = keep the full population, MARK the matching UIDs (scope() does NOT reduce;
# the match set is carried to grids/gantt via highlight_uids()).
filter_mode: str = "reduce"
# The session-wide SAVED GROUP (multi-clause), the grouping counterpart of the session-wide
# filter. Drives grid banding/ordering + the breakdown field on every page. None = file order.
active_saved_group: SavedGroup | None = None
# match-set memo, id(original) -> (original, matched-UIDs). Same identity-stability contract as
# `_scoped`; cleared by every setter below and by wipe. None value = "no filter" for that object.
_matched: dict[int, tuple[Schedule, frozenset[int] | None]] = field(default_factory=dict)
```

### 1.3 The unified match predicate (new private method on `SessionState`)

One place resolves *whichever* filter source is active into a UID set for a given schedule, memoized like `_scoped`:

```python
def _match_uids(self, sch: Schedule) -> frozenset[int] | None:
    """UIDs of `sch` matching the active filter — saved-filter tree OR flat field criteria —
    or None when no filter is set (⇒ every task). Prompt answers feed the saved-filter path.
    Cached by original identity; invalidated by every filter setter + wipe."""
    cached = self._matched.get(id(sch))
    if cached is not None and cached[0] is sch:
        return cached[1]
    if self.active_saved_filter is not None:
        matched: frozenset[int] | None = select_saved(
            sch, self.active_saved_filter, self.saved_filter_prompts
        )
    elif self.active_filter:
        matched = frozenset(select(sch, self.active_filter))
    else:
        matched = None
    self._matched[id(sch)] = (sch, matched)
    return matched
```

This lives under `_lock` transitively (callers hold it). The memo matters because `select_saved` re-walks the tree per file and can be called several times per request (scope + highlight + per-file table).

### 1.4 `scope()` integration (rewrite of `app.py:591-617`)

The critical semantic: **HIGHLIGHT mode does not reduce.** In highlight mode the filter changes only presentation, so `scope()` returns the population unchanged (target truncation still applies). Only reduce mode narrows the schedule.

```python
def scope(self, sch: Schedule) -> Schedule:
    with self._lock:
        matched = self._match_uids(sch)                       # None = no filter
        reducing = matched is not None and self.filter_mode == "reduce"
        if not reducing and self.target_uid is None:
            return sch                                         # nothing changes the population
        cached = self._scoped.get(id(sch))
        if cached is not None and cached[0] is sch:
            return cached[1]
        # reduce path: honor "show related summary rows" by unioning ancestors into the kept set
        if reducing:
            kept = matched if not self._show_summary_rows() else _with_ancestors(sch, matched)
            scoped = filter_to_uids(sch, kept)
        else:
            scoped = sch
        if self.target_uid is not None and any(
            t.unique_id == self.target_uid and not t.is_summary for t in scoped.tasks
        ):
            scoped = subschedule_to_target(scoped, self.target_uid)
        self._scoped[id(sch)] = (sch, scoped)
        return scoped
```

Two engine additions this consumes (put in `grouping.py`, next to `filter_schedule`):

- **`filter_to_uids(schedule, kept: frozenset[int]) -> Schedule`** — refactor the body of `filter_schedule` (`grouping.py:134-139`) so both callers share the exact same reduction rule (matching tasks + relationships **among** them, project frame preserved). `filter_schedule` becomes `filter_to_uids(schedule, frozenset(select(schedule, criteria)))`. This guarantees the saved-filter reduce path is byte-for-byte identical to the field-criteria one — no divergence in what "reduce" means.
- **`_with_ancestors(schedule, kept)`** — adds each matching task's summary ancestors (`show_summary_rows` faithfulness). Metrics don't change (they run `non_summary()` anyway), but the grid shows the WBS context MSP would.

`_show_summary_rows()` reads `self.active_saved_filter.show_summary_rows` (field filters have no such flag ⇒ `False`).

### 1.5 The highlight accessor (new method, the presentation side)

Independent of `scope()` — in highlight mode `scope()` didn't reduce, so the grid needs the match set separately:

```python
def highlight_uids(self, sch: Schedule) -> frozenset[int] | None:
    """When a filter is active in HIGHLIGHT mode, the UIDs of `sch`'s matching tasks (to shade
    rows / outline bars). None when no filter is active or mode is "reduce" (reduce already
    dropped the non-matches, so nothing to mark)."""
    with self._lock:
        if self.filter_mode != "highlight":
            return None
        return self._match_uids(sch)
```

### 1.6 Setters + invalidation (mirror `set_filter` at `app.py:619`)

All clear the three scope-dependent caches plus the two new memos. Mutual exclusivity is enforced in the setters, not the callers:

```python
def set_saved_filter(self, saved: SavedFilter | None, prompts: dict[str, str] | None = None) -> None:
    with self._lock:
        self.active_saved_filter = saved
        self.saved_filter_prompts = dict(prompts or {})
        self.active_filter = ()                     # mutual exclusivity: a saved filter clears field rows
        self._invalidate_scope()

def set_filter_mode(self, mode: str) -> None:
    with self._lock:
        self.filter_mode = "highlight" if mode == "highlight" else "reduce"
        self._invalidate_scope()                    # reduce<->highlight CHANGES the population → full clear

def set_saved_group(self, group: SavedGroup | None) -> None:
    with self._lock:
        self.active_saved_group = group
        # grouping is ordering/banding only — it does NOT change any metric population, so it
        # deliberately does NOT clear analyses/summaries/_scoped; only the group-render memo.
        self._group_cache_clear()
```

- **Modify `set_filter` (`app.py:623-627`)** to also `self.active_saved_filter = None; self.saved_filter_prompts = {}` (the reverse mutual-exclusivity) and `self._matched.clear()`.
- Extract the shared body of `set_filter`/`set_saved_filter`/`set_filter_mode` into `_invalidate_scope()` = `self._scoped.clear(); self._matched.clear(); self.analyses.clear(); self.summaries.clear(); self.polished.clear()`.
- **Modify `wipe` (`app.py:5762`)** to also null the saved filter/group/mode: after `st.set_filter(())` add `st.set_saved_filter(None); st.set_saved_group(None); st.filter_mode = "reduce"`.

### 1.7 `/groups` route wiring (extend `groups_view`, `app.py:3448-3487`)

Keep the existing field-row `apply`/`clear` path. Add query params `saved_filter`, `saved_group`, `mode`, and prompt inputs `prompt_<n>`:

```python
qp = request.query_params
mode = "highlight" if qp.get("mode") == "highlight" else "reduce"
if "clear" in qp:
    st.set_filter(()); st.set_saved_filter(None); st.set_saved_group(None)
elif (name := qp.get("saved_filter")):
    saved = _find_saved_filter(versions, name)          # union lookup by name, §4
    prompts = {p.text: qp.get(f"prompt_{i}", "") for i, p in enumerate(saved.prompts)} if saved else {}
    if saved is not None:
        st.set_filter_mode(mode); st.set_saved_filter(saved, prompts)
elif "apply" in qp:
    st.set_filter_mode(mode); st.set_filter(param_criteria)   # field rows, existing path
if (gname := qp.get("saved_group")) is not None:
    st.set_saved_group(_find_saved_group(versions, gname) if gname else None)
```

The stored value is a **copy of the model** (like `active_filter` stores criteria, not a file reference), so the scope survives unloading the originating file.

An interactive saved filter with unanswered prompts (`saved.prompts` non-empty and any `prompt_i` blank) should render the prompt form and **not** apply — mirroring MS Project's modal prompt. That gating lives in `_groups_body` (sibling UI topic); the state contract here is just "prompts dict feeds `select_saved`."

### 1.8 Banner (extend `_filter_banner`, `app.py:772`)

Branch on the active source and mode; add a group line. Emitted unchanged at `app.py:1809`.

```python
def _filter_banner(state: SessionState) -> str:
    parts: list[str] = []
    if state.active_saved_filter is not None:
        parts.append(_saved_filter_banner(state))     # name + human-readable tree + mode wording
    elif state.active_filter:
        parts.append(_field_filter_banner(state))      # existing 778-792 body, extracted
    if state.active_saved_group is not None:
        parts.append(_group_banner(state))             # "Grouped by <display_name>" + clear link
    return "".join(parts)
```

Mode wording differs: reduce → "every metric on every page (all files) is **scoped to** …"; highlight → "every grid on every page **highlights** the N tasks matching …" (metrics are **not** scoped in highlight mode — say so, for forensic honesty). Reuse the manage/clear links (`app.py:790-791`).

---

## 2. Session-wide grouping (mirroring the filter)

Today grouping is a per-page `breakdown`/`group_field` query param. Feature #10 promotes it to session state (`active_saved_group`, §1.2) so a group chosen on `/groups` bands every page's grid — the operator's session-wide choice.

**Key distinction from the filter:** grouping is **ordering/banding + optional per-group breakdown**, never a population change. So `set_saved_group` deliberately does **not** invalidate `analyses`/`summaries` (§1.6) — metric values are identical; only presentation order changes. This keeps grouping cheap and avoids recomputing CPM on a regroup.

Derivation the render layer performs from `active_saved_group` (a `SavedGroup` with ordered clauses, each `field / ascending / groupOn / interval / startAt`):

- **Ordering key per task** = tuple over clauses of `field_value(sch, task, clause.field)` (reuse `grouping.field_value`, `grouping.py:84`), with `groupOn=2` intervals bucketed (e.g. `% Complete` → the `_percent_bucket` bands, `grouping.py:48`) and `ascending` honored per clause. This is a pure presentation sort — no engine change.
- **Breakdown field** for the `/groups` scorecard and `/forecast` rollup = the group's **first clause field**. This lets `active_saved_group` drive the existing `_groups_breakdown_table` (`app.py:13570`) and `_group_rollup_panel` (`6776`) that already accept a single field, so those panels become session-wide by reading `state.active_saved_group` when their own query param is absent:
  - `_groups_body` (`13703-13707`): `breakdown = breakdown or _group_first_field(st.active_saved_group)`.
  - `forecast_view` (`3505`): `group_field = group_field or _group_first_field(st.active_saved_group)`.

A new engine helper for the composite case (faithful multi-clause grouping) — `grouping.group_by_clauses(sch, group) -> list[tuple[key, uids]]` — generalizes `group_values` (`142`) to a clause tuple and preserves MSP clause order/direction. `group_values` stays for the single-field breakdown. This is the one place multi-clause fidelity is realized; the render layer just iterates its output.

**Field name resolution caveat** (from the spec, `MSP-FILTERS-SPEC.md:32-37`): group clauses reference **raw MSP field names** (`Text9`, `Number19`, `Duration`, `Outline Number`). `field_value` resolves custom fields only by the operator's **renamed label** (`grouping.py:86-88`). So the raw-name→value resolver the spec flags as the integration challenge is a prerequisite for both filters and groups; `group_by_clauses` and `select_saved` both route field lookups through it (sibling `engine/msp_filters.py` topic). Groups whose clause field is unresolved on a given file degrade to "ungrouped" for that file rather than erroring.

---

## 3. HIGHLIGHT mode — mark, don't drop

The state side is done in §1: `filter_mode="highlight"` makes `scope()` return the full population (§1.4) and `highlight_uids(sch)` returns the match set (§1.5). What remains is carrying that set to the grid + gantt, reusing the `pv-selected` visual idiom (`app.css:1045-1048`) with a **distinct** class so it never collides with the interactive single-click selection.

### 3.1 New CSS (mirror `app.css:1045-1048`, tokens only, 4-theme-safe)

```css
.path-grid tr.pv-match td,
tr.pv-match td { background: color-mix(in srgb, var(--accent) 16%, transparent); }
.path-grid tr.pv-match td.sf-frozen-col { background: color-mix(in srgb, var(--accent) 16%, transparent); }
tr.pv-match td:first-child,
.pv-match-name { box-shadow: inset 3px 0 0 var(--accent); }         /* row / task-name marker */
.gantt-bar.pv-bar-match, .g-ms.pv-bar-match { outline: 2px solid var(--accent); outline-offset: 1px; }
```

Distinct-class rationale: `pv-selected` is transient click state; `pv-match` is session-derived. A row can be both (selected **and** matching); separate classes compose cleanly.

### 3.2 One carrier attribute + one shared pass (covers every grid at once)

Rather than touch every row-render call site, emit the match set **once per grid container** and apply it with a single always-loaded script — the same non-destructive-DOM-pass idiom `translate.js` uses:

- **Server:** every grid/gantt container that corresponds to a specific schedule emits `data-highlight-uids="<json array>"`, computed from `state.highlight_uids(sch_for_that_grid)` via a tiny helper `_highlight_attr(state, sch)` returning `""` when `None`. A page that renders one file emits it on that grid's wrapper; multi-file pages emit per-file wrappers (each carries its own file's set — match sets are per-file because `select_saved` evaluates per file).
- **New `static/highlight.js`** (add to `_LAYOUT`'s always-loaded scripts, alongside the existing global JS): walk every `[data-highlight-uids]`, parse the set, add `.pv-match` to descendant `[data-uid]` rows whose UID is in the set, `.pv-bar-match` to their `.gantt-bar`/`.g-ms`, and `.pv-match-name` to a name cell if present. This gives **server-rendered** grids (activity tables, variance tables at `app.py:7233+`, evo grid) highlighting for free wherever rows already carry `data-uid`.

### 3.3 Client-built grids (path.js)

path.js builds rows in JS, so a post-hoc DOM pass would be undone on repaint. Instead seed it the same way `selectedUid` is handled (survives repaint):

- Read the container's set once at init: `var matchSet = parseUids(view.getAttribute("data-highlight-uids"));` near `path.js:50`.
- In `paintOne` (`path.js:421-424`), extend the class expression: add `" pv-match"` when `matchSet.has(r.unique_id)` (alongside the existing `pv-selected` compute). Because `paintOne` runs on every repaint, the highlight survives filter/zoom/tier rebuilds automatically — no `reskinSelection` change needed.
- The gantt bar built per row (`path.js:607` region) gets `pv-bar-match` the same way.

### 3.4 Semantics note

In highlight mode the per-file table and preview scorecard in `_groups_body` (`app.py:13657-13701`) should show matched **counts** but keep the **full** population in the metric scorecard (metrics aren't scoped in highlight). The `_matched_sub`/count helper (§4) supplies the count; the scorecard uses `sch` unreduced. The banner (§1.8) states this explicitly.

---

## 4. A→Z ordering of every picker

Values are already A→Z (`distinct_values` `grouping.py:169`, `group_values` `157`). The gaps are the **field** picker and the two **new** saved-filter/saved-group pickers. Sort at the render helpers (non-invasive — leaves `available_fields` order intact for any membership/iteration callers), following the `app.py:7282` precedent.

1. **Field picker** — `_groups_field_options` (`app.py:13502`): change `for f in fields:` (`13505`) to `for f in sorted(fields):`. This covers both the filter-row `<select>` and the breakdown `<select>` (both call it, `13547`/`13550`), so every field dropdown becomes A→Z in one edit. (Optionally hoist `WBS` first per the `7282` precedent for consistency; MSP itself lists alphabetically, so pure `sorted()` is the faithful choice.)
2. **Saved-filter picker** (new): source list = `saved_filters_union(schedules)` sorted by `display_name` (accelerator `&` stripped, `MSP-FILTERS-SPEC.md:30`). New helper mirroring `available_fields_union` (`grouping.py:72`):
   ```python
   def saved_filters_union(schedules) -> tuple[SavedFilter, ...]:
       out, seen = [], set()
       for s in schedules:
           for f in s.saved_filters:
               if f.name not in seen:
                   seen.add(f.name); out.append(f)
       return tuple(sorted(out, key=lambda f: f.display_name.casefold()))
   ```
3. **Saved-group picker** (new): identical shape — `saved_groups_union(schedules)` sorted by `display_name.casefold()`. (Note the real file has duplicate group names like two `&No Group` and `Group `/`Group 2`, `views_leveled.json` — dedupe by name keeps the first; a stable A→Z sort handles the rest.)
4. `_find_saved_filter` / `_find_saved_group` (used by the route, §1.7) look up by exact `name` over the union.

`casefold()` gives a case-insensitive A→Z so `_MCTasks`, `CAM_Tasks`, `SVT-` sort predictably regardless of leading punctuation the operator used.

---

## 5. Exhaustive change-site table

| Concern | File:line | Change |
|---|---|---|
| New state fields | `app.py:552` (after `_scoped`) | add `active_saved_filter`, `saved_filter_prompts`, `filter_mode`, `active_saved_group`, `_matched` |
| Match predicate | `app.py` new method on `SessionState` | `_match_uids(sch)` (memoized) |
| Scope reduce/highlight | `app.py:591-617` | rewrite per §1.4 (reduce only when `filter_mode=="reduce"`; `filter_to_uids`; `show_summary_rows` ancestors) |
| Highlight accessor | `app.py` new method | `highlight_uids(sch)` |
| Setters | `app.py:619` (`set_filter`) | add reverse mutual-exclusivity + `_matched.clear()`; extract `_invalidate_scope()`; add `set_saved_filter`, `set_filter_mode`, `set_saved_group` |
| Wipe | `app.py:5762` | also clear saved filter/group + reset mode |
| Banner | `app.py:772` | branch saved/field/mode + group line (still emitted at `1809`) |
| `/groups` route | `app.py:3448-3487` | handle `saved_filter`/`saved_group`/`mode`/`prompt_*`; keep field `apply`/`clear` |
| Groups breakdown → session group | `app.py:13703-13707` | fall back to `active_saved_group` first field |
| Forecast group → session group | `app.py:3505` / `6776` | fall back to `active_saved_group` first field |
| Per-file / preview counts | `app.py:13606`, `13657` | route through a `_matched_sub`/count helper that honors saved-filter + highlight |
| Field picker A→Z | `app.py:13505` | `for f in sorted(fields):` |
| Reduce refactor | `grouping.py:127-139` | extract `filter_to_uids(schedule, kept)`; `filter_schedule` delegates |
| Ancestors | `grouping.py` new | `_with_ancestors(schedule, kept)` |
| Multi-clause grouping | `grouping.py:142` neighbor | `group_by_clauses(sch, group)` |
| Union helpers + A→Z | `grouping.py:72` neighbor | `saved_filters_union`, `saved_groups_union` (sorted by `display_name.casefold()`) |
| Evaluator (consumed) | `engine/msp_filters.py` (new, sibling topic) | `select_saved(sch, saved_filter, prompts)` + raw-field resolver |
| Model registry | `model/schedule.py:49` neighbor | `saved_filters`, `saved_groups` frozen tuples |
| Model types | `model/saved_view.py` (new, sibling topic) | `SavedFilter`, `SavedGroup`, `display_name` |
| Highlight CSS | `app.css:1048` neighbor | `.pv-match` / `.pv-bar-match` / `.pv-match-name` (mirror 1045-1048) |
| Highlight carrier | grid/gantt container render sites | emit `data-highlight-uids` via `_highlight_attr(state, sch)` |
| Highlight pass | `static/highlight.js` (new) + `_LAYOUT` | global DOM pass adding `.pv-match` to `[data-uid]` in the set |
| Highlight in path grid | `path.js:50`, `421-424`, bar build ~`607` | read `data-highlight-uids`, add `pv-match`/`pv-bar-match` in `paintOne` |

### Invariants this preserves

- `scope()` remains the **sole** population chokepoint — saved filters and highlight both resolve through it, so every page/file inherits them with zero per-page wiring, exactly like `active_filter` today.
- Reduce fidelity: field-criteria and saved-filter reduce share `filter_to_uids`, so "reduce" means one thing.
- Highlight never changes a metric — `scope()` returns the full population; only presentation marks matches (banner states this).
- Grouping never changes a metric — `set_saved_group` skips the analysis-cache invalidation, so regrouping is cheap.
- Mutual exclusivity keeps the banner and `scope()` unambiguous: exactly one filter source is ever active.
- A→Z is applied at render helpers only, leaving engine field order (and any order-pinned tests) untouched; value pickers were already sorted.

No files were modified — this is design output.