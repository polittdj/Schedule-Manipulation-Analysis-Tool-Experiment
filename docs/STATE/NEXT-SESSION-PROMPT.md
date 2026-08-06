# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected). As of last session: **v1.0.171, highest ADR 0356, SCHEMA 2.11.0** — one day closed
SRA-LEGACY (ADR-0353, #544), V3 (ADR-0354, #545), the Codex hardening (ADR-0355) AND the
operator's SSI-delta root-cause (ADR-0356: stale setup, engine exonerated at sigma 2.5%, the
grid now reads the file's own stored SRA fields + vintage warning), the last two on PR #546;
if it has since merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch> origin/main`
(then `git branch --unset-upstream`). Fresh container: `pip install -e ".[dev]"` plus
`pip install playwright build`. **`ruff` no longer needs a manual pin** — `pyproject.toml` bounds it
at `>=0.16.1,<0.17` — but a stale **0.15.8 shim** may sit at `/root/.local/bin/ruff` and shadow it,
so run the gate's ruff as **`python -m ruff`**, and run **`ruff check .` — THE WHOLE TREE** (CI runs
exactly that; `src/ tests/` is a strict subset that misses `tools/`).

⇢ USE THE SKILLS — they exist so you do not re-derive them
`.claude/skills/` carries the standing rituals as invoked procedures (see its `README.md`):
**`full-gate`** (the gate + real-vs-environment triage) · **`prove-able-to-fail`** (falsify any new
test/guard BEFORE trusting it) · **`render-verify`** (render and MEASURE the page) ·
**`metric-parity`** (Law 2 vs the Bible and the oracles) · **`ui-change`** (the Mission Ops DoD) ·
**`cui-guard`** (Law 1) · **`session-close`** (ADR + handoff rotation + logs + wheel/installers +
PR). They are law-citing checklists, **not oracles** — ADR-0240 still applies, and the lead
re-verifies anything parity-, engine-, testimony- or CUI-relevant.

⇢ WHAT'S DONE — do NOT re-open
Phase 3 UI is closed (all three DoD ledgers). Phase 4's first unit is closed (`/cei`'s `or 0`,
`/groups`' `or 1`; `_stack_not_measured` is the ONE not-measured panel). The 4 BUG rows of the
falsy-zero sweep were re-verified as already closed — including `resources.py`'s `or [sd]`, which is
**deliberately still in the tree** (ADR-0306). Do not "fix" it. **Do NOT re-search the skill
catalogs** (ADR-0344 recorded both searches as empty).
**P0 is CLOSED (ADR-0346).** Every requirement now carries an upper bound (`setuptools` is the one
named, tested exemption); `constraints/floor.txt` + `constraints/known-good.txt` are committed; CI's
new **`floor`** job installs at the declared floors, verifies they actually bound, and runs the suite
+ parity — and it is in `check`'s `needs`, so a false support range blocks merge without the
operator's branch-protection change. `tests/test_dependency_bounds.py` (7) keeps the three artifacts
from drifting. **Do not "restore" the old floors** — all three were measured false:
`pydantic>=2` is *unsatisfiable* beside `fastapi>=0.110` (fastapi excludes 2.0.0/2.0.1/2.1.0), 2.0.2–
2.5.3 fail the frozen-`Schedule` hash test (**2.6** is the floor), and — the one that matters —
**`fastapi>=0.110` declared support for an AIR-GAP VIOLATION**: 0.110.0/0.110.1 serve
`https://errors.pydantic.dev/<ver>/v/missing` inside 422 bodies on 10 routes (Law 1). **0.110.2** is
the first clean release and is now the floor. The floor job found this on its first run.

⇢ DO THIS FIRST — phase 3 families (ALL THREE ADR-0240 reserved items are CLOSED)
**SRA-LEGACY (ADR-0353), V3 (ADR-0354/0355), the SSI-delta root-cause (ADR-0356) and the 1440
boundary (ADR-0357 — blessed by the operator's 24Hour_Calendar.mpp oracle: next-midnight IS
MSP's convention, pinned in tests/engine/test_1440_boundary.py; 23:59 would CREATE a parity
break) are all CLOSED — do NOT re-open any of them.** Next: the twelve remaining page families
(`integrity` 402 first) under ADR-0350/0351/0352's rules, and **Phase 6** docs/operator queue.

⇢ WHAT'S DONE — do NOT re-open
**P0 (ADR-0346)** dependency bounding · **P1 (ADR-0347)** intake manifest + hardened CUI hook +
SHA-pinned actions · **CC-01 / external H2a (ADR-0348)** · **monolith split slices 1–3
(ADR-0350/0351/0352**: `components.py`/`driving.py`/`evolution.py`, `app.py` 20,192 → 18,128**)** ·
**SRA-LEGACY (ADR-0353)**: `compute_sra` computes its own all-ML anchor (the `cpm` parameter is
REMOVED — do not "restore" it), and the legacy date surface carries `stored_finish_correction`.
EVM2's deterministic date now displays the stored **2012-10-04** — that is the anchoring absorbing
ADR-0108's known 2-wd residual into the DISPLAY, deliberate and SSI-consistent; do NOT re-report
it as a date bug. **V3 (ADR-0354)**: duration literals implement the vendored MPXJ
`Duration.convertUnits` (bytecode-read) — `%`/`e%` pass-through and the **364-day elapsed year**
are MPXJ's OWN behaviour, mirrored deliberately; do NOT "fix" them toward intuition. Unknown
units fail CLOSED (the sidecar vocabulary is closed). Prompt answers store RAW and coerce per
schedule at `scope()`. Do NOT rename the 99 mislabelled intake
files, do NOT narrow `tests/fixtures/`, do NOT "simplify" the CUI hook's process substitution back
into a pipeline (it fails OPEN). On ADR-0348 specifically: **`offset_to_datetime` and every offset
are deliberately untouched** — 29 finish-role sites depend on the end-of-day spelling; a start-role
offset goes through **`span_start_datetime`**, and an AST census guard fails if one does not. The
`tod + per_day == 1440` boundary is **documented, not repaired** (no committed schedule reaches it;
repairing it needs an oracle the corpus does not contain).
**Operator only:** license selection (LICENSE is expressly a placeholder granting no rights) ·
branch-protection required contexts · intake re-upload · proprietary-tool reruns to upgrade parity
from engine==golden to engine==Fuse · OR-04.
Carried, measured, NOT fixed: the `/groups` breakdown's **"Activities" column counts summary rows**
(ADR-0343) · `/briefing`, `/path` and `/compare` render a bare takeaway h1 with NO `page-lede` ·
the nine installers do **not** install with `-c constraints/known-good.txt` (62 lockstep tests; own
unit).

⇢ THE TRAPS THIS SESSION PAID FOR — check for these BY NAME
1. **A declared range nobody runs is decoration — and one of ours hid a Law 1 defect.** The air-gap
   guard was correct and had been all along; no configuration had ever asked it the question. **Ask
   not "is there a test?" but "is there a configuration in which that test has ever been asked?"**
   Two correct controls that never meet prove nothing.
2. **A constraints file that does not bind is a silent no-op**, and the job goes green having tested
   the newest resolution — proving the opposite of its name. The `floor` job therefore asserts the
   INSTALLED versions. **Ask of every new job: what would make this pass while proving nothing?**
3. **A capture tool's default exclusions are part of your data.** `pip freeze` omits `setuptools`
   (and `pip`/`wheel`), so the first `known-good.txt` dropped the ONE pin that exists for a CVE
   remediation. 58 plausible lines look exactly like 59 — the guard caught it, reading would not have.
   Regenerate with `--all`. Same shape as July's 64-byte magic-byte window inventing 3 false positives.
4. **Fix what a new gate will find BEFORE you turn it on.** P0-3 (`importorskip`) had to land before
   P0-2's floor leg or the leg would have been red on day one from two bare playwright imports — and
   its first result would have taught nothing about dependency bounding.
5. **Silencing is not bounding.** `filterwarnings` was swallowing starlette's httpx→httpx2
   deprecation as the *whole* answer to a transition that will `RuntimeError` the web suite when the
   fallback drops. Pair a suppressed warning with the bound that handles what it warned about.
6. **A guard can pass on exactly the thing it protects** (ADR-0344's duplicate: all four
   `test_state_docs.py` assertions stayed GREEN over it). **"Next free number" is a race** — check the
   highest ADR on disk immediately before you commit; `test_adr_numbers_are_unique` now enforces it.
7. **A green suite over identity cases is a vacuous gate** (ADR-0353): every `test_sra.py` synthetic
   is unprogressed, so "full-duration anchor" ≡ "remaining anchor" by construction and 30+ green
   tests never touched the cross-basis defect. Ask of a two-instrument disagreement: do the
   fixtures make the instruments identical?
8. **`grep -c` exits 1 on a zero count** — an `&&`-chained "assert-absent then run" mutation step
   silently stops at the grep and the test never runs. Chain verification greps with `;`.

⇢ Measured-false, do NOT re-chase
The DD-line gap is 8 charts (only 1 was real work) · `margin_dashboard` is one chart (**two**, with
OPPOSITE answers) · the SRA "Finish date" charts want a DD line · `--danger` is the red token
(**`--bad`**) · `pytest --timeout=` is available (it is NOT installed, and the usage error exits
**0** through a `| tail` pipeline) · source call sites == rendered charts (`curves.js` has ONE
`axisTitles` call site, THREE charts) · `/driving-path` is a fifth unconverted page (that is its
EMPTY STATE) · counting `<div class=panel` finds every panel (it misses the QUOTED form) ·
**`pydantic>=2` is a safe floor** (it is not; 2.6 is).
**The `/analysis` focus→tip family** (`test_float_tip_dismiss` / `test_float_tip_scroll`) is
**load-sensitive** — not intermittent, not deterministic. Pre-existing, never red on CI. Do NOT chase.
**CC-01's "74 call sites"** was never a call-site count (75 src token hits minus the one `def`; the
AST count is **53**), and its named mechanism — non-working dates — is **unreachable** on all 14
committed schedules. Do not re-derive it a third time; ADR-0348 records the measurement.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model/audit protocol · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING. Full gate before
every commit; statics FOREGROUND first (`node --check` PER FILE — a glob checks only the first);
proved-able-to-fail on every new behavioral test (revert the CALLER, confirm the revert changed the
RENDER, run the WHOLE module — a `-k` filter can silently deselect the very test you are targeting);
HANDOFF rotation + SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE (bump the
version BEFORE the suite, REBUILD if you touch code after; wheel at `dist/wheel/`, then
`tools/installer/build_installers.py`) — **note `pyproject.toml`'s dependency metadata ships in that
wheel, so a bounds change is a shipped change even when `src/` is untouched.** NEVER
`git checkout <file>` to undo a temporary test mutation — `cp` from a scratchpad copy. The
missing-value sentinel in `app.py` is the literal `—`, never `&mdash;`. **`pgrep -f <pat>`
self-matches exactly like `pkill -f`.** pytest stdout to a FILE is block-buffered (use `python -u`).
`cd` in a Bash call persists across calls — use absolute paths. **A number written mid-session is
not a measurement** — re-read it before it lands in a handoff. Full local suite **~21 min** (**~26
min** at the floor, on pytest 8.0.0); CI takes ~11 min to register checks and `test (3.11)`/`(3.13)`
run ~30 min — the new `floor` job runs in parallel with them.
