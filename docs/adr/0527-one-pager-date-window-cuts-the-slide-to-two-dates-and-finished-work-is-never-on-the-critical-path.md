# ADR-0527 — A One-Pager date window cuts the slide to two dates and names everything it leaves off; finished work is never on the critical path (R-71's flag half CLOSED)

**Status:** Accepted · **Date:** 2026-09-24 · **Extends:** ADR-0446, ADR-0465, ADR-0526 (One-Pager), ADR-0476 / ADR-0512 (recorded-complete work) · **Closes:** R-71's flag half

## Context

### 1. The date window (operator request 2026-09-23)

> "Add the ability for the user to input two different dates on the One-Pager Timeline and the
> One-Pager Compare page that will reformat the OnePager to that date range. Keep all other
> functionality the same … This just formats the timescale and omits tasks that fall outside of
> this date range."

Three rulings were asked and given before any code (2026-09-23):

| Question | Ruling |
| --- | --- |
| A task that straddles a window edge | **Keep it, cut at the edge**; its label keeps its TRUE finish date; only a task wholly outside is omitted, and named |
| Which position puts a compared row on a windowed slide | **Prior OR current** — an item that slipped OUT of the window stays on it, its arrow running to the edge (hiding those is how a slip gets buried) |
| What the window scopes | **Everything about the slide** — slide, PowerPoint, takeaway counts, per-swimlane summary, ▦ DATA, ⤓ EXCEL — with the window and every omitted item named on the page and in the Excel notes; no window = today's behaviour, byte-identical |

### 2. R-71's flag half (operator ruling 2026-09-23)

`TaskTiming.is_critical` is documented as the pure CPM property `total_float <= 0`. The ruling:
**keep `is_critical` pure**; the record-aware answer stays in `is_effective_critical`; only
`CPMResult.critical_path` drops recorded-complete activities.

## Decision

### The window

* `reports/onepager.py`: `Window`, `overlaps`, `window_items`, `plot_window` (the span is exactly
  `[first, last + 1 day)` — never widened to whole months or to today; today is drawn only inside
  it), `timescale` (one header builder for both slides; the no-window branch is the ADR-0446 header
  unchanged, the windowed one labels an edge month only when its label fits its VISIBLE part),
  `windowed_doc`, and `build_layout(window=…)` — a straddling bar is cut to `[X0, X1]` with its
  3-pt floor kept INSIDE the chart, and the notes name every cut item.
* `reports/onepager_compare.py`: `row_in_window` (prior OR current), `window_compare` (rows scoped,
  per-swimlane summaries and totals RECOUNTED over what stays; the matcher's findings about the lists
  kept whole), `build_compare_layout(window=…)` — a side wholly outside the window is not drawn
  (`None`, which both painters already skip), a side running past an edge is cut, and the finish's
  arrow runs to the edge it crosses with its true `±N cal d`.
* Web: a plain POST form (From / To / Apply dates / Show all dates) on both pages — no script, so the
  strict CSP and the byte-frozen painters are untouched; a typed One-Pager date (`5/1/27`, `05/2027`)
  is read too; a blank, unreadable or reversed window is refused BY NAME and the current window kept;
  an empty window keeps its own controls on the page (a window with nothing in it must not hide the
  button that clears it); clearing a list clears its window.

### R-71

`critical_path = tuple(tid for tid in order if timings[tid].is_critical and not
is_recorded_complete(task_by_id[tid]))`. `is_critical` untouched. DCMA-12's own copy of the filter
(ADR-0476) could no longer be reached from any product path — `CPMResult` is built in exactly one
place — and was removed, its reason moved into a comment that points at the engine rule.

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | How it was attacked | Verdict |
| --- | --- | --- | --- |
| A1 | The window can be added with the no-window slides byte-identical | 600 seeded layouts (300 Timeline + 300 Compare, 24 .pptx renders) digested on the pristine tree → `e34820f5…`; re-run after every edit | **held** (identical after every edit) |
| A2 | Neither JS painter nor the .pptx painter needs to change — clamping in the layout suffices | read both painters and `reports/pptx.py`: they paint coordinates only and already skip `None` shapes, ghosts and arrows | **held** — no static file touched, no digest/locator re-baseline |
| A3 | "Clamp to the chart" keeps every shape inside it | fuzz: 3,751 windowed layouts | **FELL on first run** — 88 bars ending exactly on the window's first day were drawn BACKWARDS past `X0` (the 3-pt floor applied after the cut). Fixed: the floor is kept inside; 0 of 3,751 after |
| A4 | Cut shapes read correctly on the page | rendered both pages in Chromium through the REAL form, 4 themes | **FELL** — on Compare a bar spanning the whole window had its end-anchored label pushed LEFT of the chart over the swimlane names ("Overall GTA Window" over "BobbySon"): ADR-0526 allows an inside label only on a row with no prior side. Fixed for windowed slides only (no-window geometry unchanged): a row whose ghost and arrow are off the slide, or whose shapes leave no room outside, carries its label on its solid bar when it fits. Clipped windowed Compare labels 378 → **20** of 7,161 fuzzed; Timeline 0 of 6,945 |
| A5 | R-71: `is_critical ∧ ¬recorded-complete` is UID-exact against MS Project's stored Critical | re-censused independently on the 15 committed goldens keyed on PATH: 7,935 flagged activities | **held** — 4 engine-only disagreements before (Hard_File_updated2 UID 290, Hard_File_updated3 UID 261 ×2 golden copies, Large_Test_File2 UID 6956 — the handed-over witnesses), **0** after |
| A6 | R-71's blast radius is `dcma14.py` + `web/path.py` | census matched the SEAM (every `critical_path` reference, every `CPMResult(` construction), not the sentence | **held**, and found DCMA-12's filter copy now unreachable (removed) |
| A7 | The /path headline moves only by the finished activities | measured on all 15 goldens, pristine vs changed | **held** — the chain count drops by exactly 1 on the 4 witness files; the minimum-float figure is unchanged on all 15 |
| A8 | An inherited test docstring is fact | `test_recorded_completed_window.py` said "the corpus no longer holds a finished activity on the critical path" | **FELL** — four goldens did; the docstring is corrected in the re-baseline |

## Verification

* Red-first: `tests/reports/test_onepager_window.py` (13) — 12 red on pristine (the byte-identity
  pin is green by construction and proven by mutant); `tests/web/test_onepager_window_page.py` (11)
  — 11/11 red on pristine; `tests/engine/test_r71_critical_path_record.py` (3) — 2 red on pristine
  (the "a claim without actuals stays" control is proven by mutant).
* Mutation: R-71's three rules (no filter / percent-only filter / changed `is_critical`) each red by
  name; the rig re-baseline red by name with the engine rule removed; the inside-label fix red by
  name when reverted. The window battery (run on a separate model in a scratch copy, harness proven to import the copy): **35 mutants, 32 red on the first run**; two survivors (M8a / M9 — a windowed edge month's label position and the windowed/unwindowed timescale switch) were one missing test — a 55-day window never produces a sliver month — now `test_an_edge_month_sliver_is_labelled_only_as_its_visible_part_allows`, both red by name after it; the third (M23b, nudging the pre-existing ADR-0446 `6.5`-pt month-letter threshold) is out of this change's scope and recorded below.
* Rendered: both pages in Chromium through the real form, pristine-shape before / window / cleared,
  4 themes, 0 shapes outside the chart, 0 page errors; "Show all dates" restores the original.

## Deliberate re-baselines

* `test_dcma12_never_injects_its_delay_into_work_that_has_already_finished`: the rig's path
  `(1, 2)` → `(2,)`, with `timing(1).is_critical is True` pinned beside it (the ruling, stated).

## Deliberately NOT done

* No JS or CSS change — the date control is a server form reusing `.op-title-form`.
* The census `test_ui_control_effect_census` harvests zoom / fit / pan-family controls only; a plain
  date form is invisible to it BY CONSTRUCTION. Its effect is driven by the page tests instead.
* 20 of 7,161 fuzzed windowed Compare labels still clip: DUPLICATE NAME rows with ONLY a full-width
  ghost — no solid bar to carry a label (the same family as the carried "clipped end-anchored
  labels" residual).
* The ADR-0446 month-letter threshold (`fit >= 6.5`) survives a one-tenth nudge (M23b): the byte-identity pin covers one fixture, which never crosses that band (a 129-month span does). Pre-existing; a boundary test would close it.
* `is_critical`, `is_effective_critical`, and every float / date figure: unchanged (the ruling).
* R-71's record limbs (LS = AS / LF = AF pins, the 22 clamped late finishes) stay OPEN — the ruling
  closed the flag only.
