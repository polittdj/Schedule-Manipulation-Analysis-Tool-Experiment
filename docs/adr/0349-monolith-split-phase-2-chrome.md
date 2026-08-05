# ADR-0349 — Monolith split, phase 2: the page chrome moves to `web/chrome.py`

- **Status:** Accepted
- **Date:** 2026-08-05
- **Closes:** ADR-0297's queued **phase 2** ("the page chrome (`_LAYOUT`, nav/banner/page shell)
  → `web/chrome.py`")
- **Related:** ADR-0297 (phase 1, `state.py` — the binding precedent and the whole method),
  ADR-0195 (never big-bang — integrate in phases), ADR-0249 (the tests are the measure),
  ADR-0326/0340/0342 (the layout script-order guards this ADR had to repoint)

## Context

`web/app.py` stood at **21,348 lines** after ADR-0348. ADR-0297 extracted the session-state
machinery and left phases 2–3 named and ordered: **(2)** the page chrome, **(3)** the ~11k lines
of `_*_body` / `_*_panel` / `_*_data` presentation helpers. Phase 2 is next, and the method is
already settled by precedent: the extraction is **verbatim and behaviour-free** — every class,
function, constant, docstring and comment moves byte-for-byte, only the module boundary changes,
and `app.py` re-exports with the explicit `X as X` idiom so old import paths keep working.

## Decision

**Phase 2 extracts the page chrome — verbatim — into `web/chrome.py` (1,294 lines):** the
`_LAYOUT` skeleton and its `_bust_static` cache-bust boundary, the always-on banners
(`_banner_html`, `_filter_banner`, `_endpoint_banner`, `_flash_html`, `_global_sources_banner`),
the per-page explainers (`_EXPLAINERS`, `_explain`, `_guide`, `_page_explainer`), the Mission-Ops
story spine (`_Chapter`, `_SPINE`, `_render_nav`, `_render_target_control`, `_role_strip`,
`_chapter_kicker`, `_story_footer`, `_utility_takeaway`), the Ask-the-AI panel, and **`_page`**
itself — the single chokepoint every route returns through. `app.py` drops to **20,255 lines**.

**The seam was chosen by measurement, not by eye.** An AST pass over `app.py`'s 344 top-level
symbols computed the transitive closure of `_page`: **30 names, and it is closed** — nothing the
moved code calls stays behind in `app.py`. That property is what makes the cut safe, and it is
also what made it small. Four of the thirty sat outside the 397–1983 line region and came along
because the closure demanded it, not because they were nearby:

- `_e` (473 call sites in `app.py`) and `_expandable_more` — generic HTML primitives, leaves.
- `_criteria_text` / `_criterion_value_list` / `_OP_TEXT` — 40 lines from line ~18.7k. Not an
  arbitrary graft: `_criteria_text`'s own docstring reads "*for chips/banner*", and its only
  chrome consumer is `_filter_banner`. The seam found them; the docstring confirmed them.

`_ask_panel_html` moved too and cost nothing — it references only `_e`, so the AI *panel* came
across without dragging any of the AI *backend* machinery (`_active_backend`, `_ollama_or_none`,
the translation helpers) with it. That block, 693–1044, stayed put.

**Deliberately left in `app.py`:** `_STATIC_DIR` (the `StaticFiles` mount, app-level, and a test
imports it from `web.app`), `_OAT_MAX_ACTIVITIES` (ADR-0297 already ruled on it), the AI backend
block, and `_TS_CAPTION_MARK` — a page-*body* constant that merely sits between `_story_footer`
and `_page`. Adjacency is not cohesion; it belongs to phase 3.

`chrome.py` takes the **E501 exemption**. ADR-0297 declined it for `state.py` because that module
has no HTML in it, and predicted the opposite for the HTML-carrying phases: "these carry the HTML
f-strings and take the E501 exemption with them." `_LAYOUT` *is* the HTML — 31 lines in the moved
region exceed 100 columns, and re-wrapping them would have broken verbatim to satisfy a rule that
exists for code.

## The trap phase 2 actually hit — and it is not phase 1's

ADR-0297's hazard was **monkeypatching**: a test patching a callable through the old module's
namespace silently spies nothing after the call site moves. That trap did not bite here — a
targeted search found **zero** tests patching any of the thirty names, and the closure being
self-contained means no moved function calls anything left in `app.py`.

The hazard phase 2 hit instead is **source-text guards**. Several tests read a module's raw text
by path and assert on what they find:

```python
app = (ROOT / "src" / "schedule_forensics" / "web" / "app.py").read_text(...)
head = app[app.index("_LAYOUT = Template(") : app.index("<main>{{ banner }}")]
```

Moving `_LAYOUT` did not make these fail honestly. One raised `ValueError: substring not found`
(loud, fine). But `test_bar_drill`'s `assert app_src.count('…drilldown.js…') == 1` would have gone
from counting **one** include to counting **zero** — and `test_presentation_fixes`'s
`assert '"&mdash;"' not in src` would have gone on passing over a file that no longer contains the
code it guards. **A guard that has stopped guarding still reports success.** That is the same
failure shape as phase 1's silent monkeypatch, arriving through a different door.

Four guards were repointed, and the two directions were kept distinct:

- Guards whose subject is **the layout's internal script order** (`test_axis_titles` ×2,
  `test_dd_line_ledger`) now read `chrome.py`. Order is only meaningful inside the module that
  defines it.
- Guards whose subject is **the whole view layer** now read *both* modules.
  `test_bar_drill`'s once-only include exists to catch a page re-including `drilldown.js` — in
  `app.py`, which is exactly where such a re-include would land. Pointing it at `chrome.py`
  alone would have kept it green while re-opening the hole it guards; that was caught and
  reverted mid-change. `test_presentation_fixes`'s `&mdash;` sentinel guard likewise now covers
  `chrome.py`, which owns `_e`.

## Proof of behaviour-freedom

- **Verbatim, mechanically proved.** A checker compares the multiset of non-blank lines in the
  original `app.py` against `app.py + chrome.py`, setting aside the generated re-export block and
  `chrome.py`'s authored preamble: **20,179 → 20,179**, every line present with the same
  multiplicity. The only six lines that left were imports (`html`, `importlib.metadata`,
  `Template`, `banner_for`, `SavedCriterion`, `SavedOperand`) that `ruff --fix` removed from
  `app.py` because their sole consumers had moved — each verified unused there and re-exported by
  nothing.
- **Every served page is byte-identical.** All 31 HTML routes were rendered with the example
  schedule loaded, before and after, *in the same interpreter and environment* (the pre-split
  `app.py` swapped back in and `chrome.py` parked): **31/31 identical SHA-256**. The oracle was
  then proved sensitive — a single character changed in `_LAYOUT` moved **30 of 31** hashes, the
  31st being `/whatif`'s 404, which renders no layout. For a change whose served bytes are
  provably unchanged, this dominates a browser pass: an identical response cannot render
  differently.
- `app._page is chrome._page`, `app._e is chrome._e` — the re-exports resolve to the same objects.

## The new guards, and that they can fail

`tests/web/test_monolith_split_contract.py` pins the three invariants the split rests on, all of
which rot silently rather than failing loudly. Each was proved able to fail by mutation, with the
file re-read afterwards to confirm the mutation landed and the tree restored byte-identically from
a scratchpad copy (never `git checkout`):

| Mutation | Result |
| --- | --- |
| drop `_guide`'s re-export from `app.py` | fails — `assert not ['_guide']` |
| leave a stale `_TITLE_TO_CHAPTER` copy in `app.py` | fails — names the drifted symbol |
| **deferred** `from …web.app import _mdY` inside a `chrome.py` function | fails — and note it **imports cleanly**, so only the AST check catches it |
| a second `_LAYOUT = Template(` elsewhere in `web/` | fails — and names the three guard files to repoint |

The third is the one worth keeping: a module-level back-import detonates on its own with a
circular-import error, but the lazy in-function form — precisely how someone would *work around*
the cycle — runs fine and needs the guard. The fourth is a signpost aimed at phase 3: when
`_LAYOUT` moves again, it fails and tells the next session which source-text guards must move in
the same commit.

The repointed guards were re-proved too: relocating `gantt.js` out of the layout head (the real
ADR-0340 defect) fails both `test_axis_titles` and `test_dd_line_ledger` against `chrome.py`.

## Consequences

- **Phase 3 remains**, unchanged in shape: the ~11k lines of `_*_body` / `_*_panel` / `_*_data`
  presentation helpers → per-page modules, each its own behaviour-free PR, with `create_app`'s
  routes staying in `app.py` until the helpers are out. It moves roughly nine times as much code
  as phase 2, so both traps — the monkeypatch namespace and the source-text guard — should be
  swept for *before* the cut, the way the closure was computed here.
- The before/after render diff is now a reusable oracle for phase 3
  (`scratchpad/render.py` in this session's notes); it is cheap and it is decisive.
- `CLAUDE.md`'s architecture note gains `chrome.py` alongside `state.py`.
