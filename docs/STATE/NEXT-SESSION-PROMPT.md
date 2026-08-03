# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected). As of last session: **v1.0.159, highest ADR 0344**. ADR-0306's three carried
UNSURE falsy-zero rows are CLOSED (ADR-0343, PR #525 → `f063463`). ADR-0344 committed **seven
project skills** under `.claude/skills/`. `git fetch --prune origin && git remote set-head origin -a
&& git checkout -B <branch> origin/main` (then `git branch --unset-upstream`) and start the next
unit. Fresh container: `pip install -e ".[dev]"` plus
`pip install playwright 'ruff==0.16.1' build`.

⇢ USE THE SKILLS — they exist so you do not re-derive them
`.claude/skills/` now carries the standing rituals as invoked procedures (see its `README.md`):
**`full-gate`** (the gate + real-vs-environment triage) · **`prove-able-to-fail`** (falsify any new
test/guard BEFORE trusting it) · **`render-verify`** (render and MEASURE the page; a tested Tier-1
recipe + the measured-box tier) · **`metric-parity`** (Law 2 vs the Bible and the oracles) ·
**`ui-change`** (the Mission Ops DoD) · **`cui-guard`** (Law 1) · **`session-close`** (ADR +
handoff rotation + logs + wheel/installers + PR). They are law-citing checklists, **not oracles** —
ADR-0240 still applies, and the lead re-verifies anything parity-, engine-, testimony- or CUI-relevant.

⇢ WHAT'S DONE — do NOT re-open
Phase 3 UI is closed (all three DoD ledgers: SVG captions, DOM captions, DD line). Phase 4's first
unit is closed: `/cei`'s `or 0` and `/groups`' `or 1` no longer fabricate a zero where the figure is
absent. `_stack_not_measured` is the ONE not-measured panel; `tests/web/test_absent_is_not_zero.py`
(11) derives its expectations from `group_values`/`non_summary` at test time and pairs every
fabricating branch with its true-positive twin.
**The 4 BUG rows of the falsy-zero sweep were re-verified as already closed** — including
`resources.py`'s `or [sd]`, which is **deliberately still in the tree** (ADR-0306 paired it with the
`over_allocated` fix that must now SURFACE the non-working-day bucket). Do not "fix" it.
**Do NOT re-search the skill catalogs** — ADR-0344 recorded both searches as empty of anything new.

⇢ NEXT — Phase 4 continues, then 5 and 6
**CC-01's rendering half** — *"74 sites" is an approximate grep, **RE-DERIVE it** before touching
anything*; ADR-0240 reserves this for a **Fable 5 Max** deep dive on the CPM date machinery ·
**SRA-LEGACY** (`audit/SRA-ROOTCAUSE-20260730.md`) · **V3** (`engine/msp_filters.py` hard-codes
`"d": 480` and discards the elapsed marker it captures in regex group 2; ADR-0310 reduced it from a
product decision to a **conformance fix**, but it MOVES saved-filter populations — it needs its
migration-report gate). Then **Phase 5** monolith split 2–3 (`app.py` **21,333** lines, `state.py`
**1,479** — measured) and **Phase 6** docs/operator queue. OR-04 stays with the operator.
Carried, measured, NOT fixed: the `/groups` breakdown's **"Activities" column counts summary rows**
(`len(uids)`), so the `Summary` row reads "19 activities" beside `—` completion and `—` BEI —
fixing it MOVES a displayed population figure (ADR-0343 §"Deliberately NOT done"). `/briefing`,
`/path` and `/compare` render a bare takeaway h1 with NO `page-lede`, while `/evm`, `/scurve`,
`/margin`, `/groups`, `/integrity` carry one.

⇢ THE TRAPS THIS SESSION PAID FOR — check for these BY NAME
1. **An audit that names its own blind spot is handing you the experiment.** Three rows sat UNSURE
   for five weeks behind one sentence — *"I did not execute the rendered page."* Rendering settled
   all three in an hour. **When a prior finding states the evidence it lacked, that sentence IS the
   task definition** — re-reading the source cannot resolve it.
2. **A MATCHING COUNT IS NOT AN IDENTIFICATION** (second consecutive session). 118 WBS rows read
   `0%` and matched the hypothesis; re-deriving the population per value cut it to **19** — the
   other 99 were honest zeros. *A number that matches your hypothesis is the moment to re-derive
   it, not the moment to write it down.*
3. **The defect class: a self-contradiction inside ONE viewport.** Takeaway said "no month could be
   scored", KPI cards said "—", and the panel between them drew "Latest scored month · 0 planned in
   the month". Invisible to grep (the `or 0` looks like every other `or 0`), invisible to a unit
   test of either half, glaring on render. **Cheap high-yield check: render any page that mixes an
   em-dash KPI strip with a chart, on an input where the figure is absent, and see if the two halves
   still agree.**
4. **Verify the premise of the queue item before working it.** A stale audit row and a deliberate
   exception look identical from the table; only the code says which.
5. **Read the emitter before writing the parser.** `_stat_cards` emits **value THEN label**, so a
   regex scanning forward from a label reports the NEXT card's value. The first KPI read claimed the
   page said `Planned = 0` when it said `—`.
6. **A revert that fails the WHOLE module proves nothing.** Two independent reverts: `/cei` → 2 of
   11 fail, `/groups` → 6 of 11 fail, each leaving the other surface AND its own true-positive twin
   green.

⇢ Measured-false, do NOT re-chase
The DD-line gap is 8 charts (only 1 was real work) · `margin_dashboard` is one chart (**two**, with
OPPOSITE answers) · the SRA "Finish date" charts want a DD line (their domain is ~17 MONTHS from the
data date) · `--danger` is the red token (**`--bad`** — `--danger` does not exist) ·
`pytest --timeout=` is available (it is NOT installed, and the usage error exits **0** through a
`| tail` pipeline) · source call sites == rendered charts (`curves.js` has ONE `axisTitles` call
site and renders THREE charts) · `/driving-path` is a fifth unconverted page (that is its EMPTY
STATE) · counting `<div class=panel` finds every panel (it misses the QUOTED form).
**Known intermittent: the `/analysis` focus→tip family** (`test_float_tip_dismiss` /
`test_float_tip_scroll`) — adjudicated, pre-existing, has NEVER failed on CI. Do NOT chase.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model/audit protocol · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING. Full gate before
every commit; statics FOREGROUND first (`node --check` PER FILE — a glob checks only the first);
proved-able-to-fail on every new behavioral test (revert the CALLER, confirm the revert changed the
RENDER, run the WHOLE module — a `-k` filter can silently deselect the very test you are targeting);
HANDOFF rotation + SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE (bump the
version BEFORE the suite, REBUILD if you touch code after; wheel at `dist/wheel/`, then
`tools/installer/build_installers.py`). NEVER `git checkout <file>` to undo a temporary test
mutation — `cp` from a scratchpad copy. The missing-value sentinel in `app.py` is the literal `—`,
never `&mdash;`. **`pgrep -f <pat>` self-matches exactly like `pkill -f`.** pytest stdout to a FILE
is block-buffered (use `python -u`) — an empty output file is not a stall. `cd` in a Bash call
persists across calls — use absolute paths. **A number written mid-session is not a measurement** —
re-read it before it lands in a handoff. Full local suite **~21 min**; CI takes ~11 min to register
checks and `test (3.11)`/`(3.13)` run ~30 min.
