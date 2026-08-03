# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected). As of last session: **v1.0.160, highest ADR 0345**. **Nothing is in flight** —
three PRs merged 2026-08-03: #527 (`d57e230`, seven project skills), #529 (`f8a87d3`, the
ADR-uniqueness guard), #528 (`2262e6d`, ADR-0345 — a 13-claim external audit adjudicated by
measurement + the logging-isolation fix). `git fetch --prune origin && git remote set-head origin -a
&& git checkout -B <branch> origin/main` (then `git branch --unset-upstream`). Fresh container:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build`.

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

⇢ DO THIS FIRST — P0-2: bound the dependencies (the audit's root cause)
`pyproject.toml` has **no upper bounds and no lock/constraints file**, so the suite's pass/fail
depends on what pip resolves that day. **This is not theoretical — it is proven:** the SAME tree gives
pytest **8.0.2 fail / 8.4.2 fail / 9.1.1 pass** (ADR-0345). And `[tool.pytest.ini_options] minversion
= "8.0"` *declares* support for the failing range, while `filterwarnings` already **silences** the
starlette httpx deprecation instead of bounding it (starlette 1.3.1 tries `httpx2`, falls back to
`httpx` with a warning, and raises `RuntimeError` if neither is present). Both #529's ADR guard and
#528's autouse fixture are patches on symptoms of this. Deliver: a committed constraints file, upper
bounds where they are defensible, and a CI leg that installs at the declared floors so "we support
pytest 8.0" is tested rather than asserted. Clean installs already verified on **3.11.15 and 3.13.12**
(rc=0 both).
**Then P0-3:** `pytest.importorskip` in `tests/perf/test_observer_storm.py` (line ~136) and
`tests/web/test_launch_invalidation.py` — they use a bare `from playwright.sync_api import …` and
therefore ERROR rather than skip in a lean env; `tests/web/test_r11_panel_contract.py:817` shows the
right pattern.
**Then P1:** intake manifest + an extension↔content regression test (**89** mismatched tracked files,
ALL in `00_REFERENCE_INTAKE/`, product verified unaffected — 65/65 statics, both `.aft` at 1443/1403
metrics, 16 goldens + 1 XER + 20 `.mpp` intact) · reconcile risks **R-03/R-12** (both stale: the two
`.mpp` ARE tracked, twice each; the intake IS committed) · CUI hook hardening (it ALLOWS
`schedule.json`, `notes.txt`, `data.mpp.bak`, `sched.p6xml` — and `.json` is the tool's own Save
format) · pin GitHub Actions to SHAs (all on mutable `@v4`/`@v5`/`@v6` tags).
**Operator only:** license selection (LICENSE is expressly a placeholder granting no rights) ·
branch-protection required contexts (`check` needs only `test`, NOT `browser` — I cannot read repo
settings) · intake re-upload · proprietary-tool reruns to upgrade parity from engine==golden to
engine==Fuse.

⇢ THEN — Phase 4 continues, then 5 and 6
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
1. **A guard can pass on exactly the thing it protects.** Two sessions both minted **ADR-0344**; all
   four pre-existing `test_state_docs.py` assertions stayed GREEN over it (`max()` hides a duplicate;
   both docs legitimately contained the string). **When you add a guard, ask what corrupted state
   would still satisfy it.** Same shape as a `caplog` test that cannot fail on the pytest CI resolves.
2. **"Next free number" is a race with any concurrent branch.** Check the highest ADR on disk
   immediately before you commit, not when you start. `test_adr_numbers_are_unique` now enforces it.
3. **Audit the confident claims too, not just the hedged ones.** The external review's three
   "VERIFIED CONTROL" items all reproduced exactly; the one HIGH it was most specific about was
   **17× larger** than reported (1 polluting test → **17**, across three modules).
4. **A per-test fixture cannot undo a higher-scoped one.** My first regression test asserted a
   *pristine* logger and failed the full suite — `tests/perf`'s module-scoped `served` configures
   logging before any function-scoped fixture can snapshot it. **Assert the guarantee your mechanism
   provides.** And: *a new test that passes in isolation has not been tested — run the full suite.*
5. **A correction is a claim too.** I replaced "intermittent" with "deterministic locally" after 3/3
   failures; two later runs passed. **Load-sensitive** is the honest word.
6. **Audit your audit tooling.** My magic-byte sniffer produced 3 false positives — a 64-byte decode
   window splitting a multi-byte UTF-8 char. A surprising measurement is first evidence about your
   instrument.

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
