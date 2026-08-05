# Handoff — 2026-08-05 (monolith split phase 2: the page chrome moves out; ADR-0349; v1.0.164)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0349, **v1.0.164**.
> **ADR-0297's queued phase 2 is CLOSED.** `web/app.py` **21,348 → 20,255**; the page chrome is
> **`web/chrome.py` (1,294 lines)**, extracted verbatim. Wheel + nine installers rebuilt at
> **v1.0.164**. The `HANDOFF.md` STATUS line that still claimed PR #535 was open is corrected in
> the archived section (it merged as `e9a48c9`).
>
> ## THE SEAM WAS MEASURED, NOT EYEBALLED
> An AST pass over `app.py`'s **344** top-level symbols took the transitive closure of `_page`:
> **30 names, and it is CLOSED** — nothing the moved code calls stays behind. That property is
> what made the cut safe *and* what made it small. Four of the thirty were nowhere near the
> chrome region and came anyway because the closure demanded it: `_e` (**473** call sites),
> `_expandable_more`, and `_criteria_text`/`_criterion_value_list`/`_OP_TEXT` from line ~18.7k —
> the last confirmed by its own docstring, "*for chips/banner*". `_ask_panel_html` cost nothing:
> it references only `_e`, so the AI **panel** moved without dragging the AI **backend** block.
>
> ## THE TRAP WAS NOT PHASE 1'S
> ADR-0297's hazard was **monkeypatching**. It did not bite — a targeted search found **zero**
> tests patching any of the thirty. Phase 2's hazard is **source-text guards**: tests that
> `read_text()` a module by path and assert on what they find. Moving `_LAYOUT` did not make them
> fail honestly. One raised `ValueError` (loud, fine) — but `test_bar_drill`'s
> `count('…drilldown.js…') == 1` would have gone from counting **one** include to **zero**, and
> `test_presentation_fixes`'s `assert '"&mdash;"' not in src` would have gone on passing over a
> file that no longer holds the code it guards. **A guard that stopped guarding still reports
> success.** Same shape as phase 1's silent patch, different door.
>
> ## TWO DIRECTIONS, KEPT DISTINCT
> Guards whose subject is the **layout's internal script order** (`test_axis_titles` ×2,
> `test_dd_line_ledger`) now read `chrome.py` — order is only meaningful inside the module that
> defines it. Guards whose subject is the **whole view layer** now read **both** modules:
> `test_bar_drill`'s once-only include exists to catch a page re-including `drilldown.js` in
> `app.py`, which is exactly where such a re-include would land. Pointing it at `chrome.py` alone
> would have kept it green while re-opening the hole it guards — that was caught and reverted
> mid-change.
>
> ## PROOF: EVERY SERVED PAGE IS BYTE-IDENTICAL
> All **31** HTML routes rendered with the example schedule, before and after, in the SAME
> interpreter (pre-split `app.py` swapped back, `chrome.py` parked): **31/31 identical SHA-256**.
> The oracle was then proved sensitive — one character changed in `_LAYOUT` moves **30 of 31**
> hashes (the 31st is `/whatif`'s 404, which renders no layout). For a change whose served bytes
> are provably unchanged, this dominates a browser pass. Verbatim was proved separately and
> mechanically: non-blank-line multiset **20,179 → 20,179**; the only six lines that left were
> imports `ruff --fix` removed from `app.py` because their sole consumers had moved.
>
> ## What landed
> * **`web/chrome.py`** — `_LAYOUT` + `_bust_static`, the always-on banners, the story spine +
>   nav, the explainers, `_ask_panel_html`, `_e`, and **`_page`**. `app.py` re-exports all 35
>   names with `X as X`. `chrome.py` takes the **E501 exemption** (31 over-long lines are the
>   HTML itself) — ADR-0297 predicted exactly this for the HTML-carrying phases.
> * **Deliberately left in `app.py`:** `_STATIC_DIR` (the mount; a test imports it from
>   `web.app`), `_OAT_MAX_ACTIVITIES` (ADR-0297 already ruled), the AI **backend** block, and
>   `_TS_CAPTION_MARK` — a page-*body* constant that merely sits between `_story_footer` and
>   `_page`. **Adjacency is not cohesion.**
> * **`tests/web/test_monolith_split_contract.py` (+3)** — re-exports resolve to the SAME objects
>   (`is`, not `==`), `chrome` never imports `app`, and `_LAYOUT` is defined exactly once, in the
>   file the source-text guards read. That last one is a **signpost for phase 3**: when `_LAYOUT`
>   moves again it fails and names the three guard files to repoint in the same commit.
>
> ## Verification
> * **Five mutations, each proved to fail the right test**, each verified-mutated by re-reading
>   the file and restored byte-identically from a scratchpad copy (never `git checkout`): dropped
>   re-export → names `_guide`; stale shadowing copy → names `_TITLE_TO_CHAPTER`; **deferred**
>   `from …web.app import` inside a chrome function → caught by the AST check *and it imports
>   cleanly*, which is the whole point (the module-level form detonates on its own); a second
>   `_LAYOUT` elsewhere → fails and names the guards; `gantt.js` moved out of the layout head
>   (the real ADR-0340 defect) → fails both repointed guards against `chrome.py`.
>
> ## Next
> **Phase 3** — the ~11k lines of `_*_body`/`_*_panel`/`_*_data` presentation helpers → per-page
> modules; routes stay in `app.py` until the helpers are out. It moves ~9× phase 2's code, so
> sweep for **both** traps before cutting, the way the closure was computed here, and reuse the
> before/after render diff (it is cheap and decisive). Then: the three pages with no `page-lede`
> (`/briefing`, `/path`, `/compare`); `/groups` "Activities" counting summary rows (ADR-0343);
> the nine installers not installing with `-c constraints/known-good.txt` (62 lockstep tests, own
> unit); Phase 6 docs/operator queue.
> **Reserved for Fable 5 Max (ADR-0240), do NOT start on Opus:** **SRA-LEGACY**
> (`audit/SRA-ROOTCAUSE-20260730.md`) · ADR-0348's **`tod + per_day == 1440`** residual (no
> oracle in the corpus) · **V3** (`engine/msp_filters.py` — moves saved-filter populations;
> needs its migration-report gate).
> **Operator only:** license selection · branch-protection required contexts · intake re-upload ·
> proprietary-tool reruns (engine==golden → engine==Fuse) · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — passes in isolation, never red on CI.
> Do NOT chase. Do NOT re-derive CC-01's "74 call sites" (ADR-0348 records it). `pydantic>=2` is
> NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP VIOLATION (0.110.2 is the floor).
> **Run `ruff check .` — the WHOLE tree**, as **`python -m ruff`** (a stale 0.15.8 shim at
> `/root/.local/bin/ruff` shadows the 0.16.1 `.[dev]` installs). Never `git checkout <file>` to
> undo a test mutation — `cp` from a scratchpad copy.
>
> **New this session:** *splitting a module silently narrows every test that names the file.*
> Moving code cannot break a `read_text()` guard's syntax, only its subject — so the guard keeps
> passing while its reach shrinks to nothing. Before the next cut, list the guards that name the
> file, not just the callers that import from it.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
