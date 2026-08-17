# Next-session kickoff prompt

Copy everything below the line into the new session.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the work queue. As of last
close: v1.0.211, highest ADR 0417, SCHEMA 2.11.0.

⇢ STATE OF THE BRANCH. ADR-0409/0410/0411/0412 are merged on main (PRs #595, #596).
ADR-0413..0417 are on branch `claude/polaris-audit-resume-3ubkxc` — check whether its PR merged
before you branch. `git fetch origin` before you branch, number an ADR, or commit.

⇢ WHAT THIS ARC IS. Operator directive 2026-08-16: *"a complete deep dive audit of the entire
repository … create tests, both pass and fail … create solutions … test those in a sandbox to
verify prior to implementing any changes. Triple verify everything in independent ways … Test,
pass and fail tests required for all functionality of all pages … Skip nothing. Verify
everything."* It is NOT finished. **Nine defects are now fixed** (ADR-0409 HOOK-02 · ADR-0410
MF-01 · ADR-0411 MF-02 · ADR-0412 launch dead-ends · ADR-0413 REC-01 · ADR-0414 MC-01 ·
ADR-0415 TST-01 · ADR-0416 JS-01 · ADR-0417 SRA export scope). ~40 findings remain REPORTED =
unverified hypotheses, and the ledger's legend says so for a measured reason — this audit has
produced finder output wrong in BOTH directions, including twice more last session (a finder's
mutation proof with the wrong diagnosis; an ADR whose justification was true of one module and
false of the tree).

⇢ RESUME ORDER — start at 0, do not re-triage.

0. **BROWSER-ORPHAN-01** (*high*, LEAD-VERIFIED, new) — **four browser test modules never run in
   CI**, and when they finally do, **5 tests FAIL** (proven pre-existing on `origin/main`
   ff89731). They hardcode `/opt/pw-browsers`, absent on a GitHub runner, so they skip in the
   matrix; CI's `browser` job runs only `test_r11_panel_contract.py`. ADR-0406 fixed this very
   pattern in one module. Two-part fix: diagnose each failure (the four panelkit ones look like
   a stale `download.url` assertion — the download now arrives as a client-side `blob:` with the
   right `suggested_filename`, so it WORKS; the histogram one is UNDIAGNOSED), then repoint the
   modules at a runner-compatible resolver AND give them a CI job. **Do not loosen an assertion
   before diagnosing it.** To reproduce: `pip install playwright` (chromium is already at
   `/opt/pw-browsers`), then run the full suite.
1. **IMP-01** (*high*) — two importer interpretations said to "materially move every displayed
   number" (a fallback path). Verify before anything else in the importer dimension.
2. **The three MIXED-POPULATION claims** — `ANALYSIS-HEADER-MIXED-POPULATION`,
   `RIBBON-MIXED-POPULATION`, `ANALYSIS-EXPORT-QUALITY-UNSCOPED`: counts computed on the RAW
   schedule while the page claims the scoped one. **One scoped-vs-raw probe can settle all
   three** — and note SRA-EXPORT-STALE-SCOPE (ADR-0417) was exactly this family, so the
   technique is proven: change the scope, then diff two surfaces against each other.
3. **The route × test gap-fill** — 137 routes (enumerated twice independently); **5 have no
   success test, 16 have no failure-mode test**. Scoped, NOT built. This is the operator's
   "pass AND fail tests for all functionality of all pages" requirement.
4. **Never audited at all: page modules A/B · docs/config/CI · AI figure-gates.**
5. The remaining REPORTED rows: CPM-01..04 · MF-03/04/06..10 · MC-02..08 ·
   `ASK-UNRESTRICTED-WRONG-VERSION` · `ISDIGIT-INT-500` · IMP-02..06 · MAN-01..03 · REC-02 ·
   JS-02..06.

⇢ DO-NOT-FIX-BLIND LIST. **MF-05** — an empty-population PASS may be CORRECT Acumen parity;
"fixing" it without the reference export would BREAK parity. Needs an operator-supplied oracle.
Also note **MC-01's parity leg is UNVERIFIED by design** (ADR-0414): no committed SSI export
exposes a fired negative impact, so the shipped semantic is the documented-additive one. If an
SSI opportunity export ever arrives, `tests/engine/test_register_opportunity.py` is the module
to re-baseline — deliberately, in daylight. Same for ADR-0417's unverified leg: proving a filter
moves the *exported* SRA percentiles needs a fixture that is not degenerate (the shipped example
puts every percentile on one date).

⇢ BEFORE ANYTHING: CLAUDE.md carries QC-1 (prove or refute before reporting: red before green,
mutation-prove the teeth, sandbox it, say UNVERIFIED rather than assert silently) and QC-2 (read
everything, assume nothing; inherited claims incl. this file are testimony, not evidence).
ADR-0393, pinned by tests/test_standing_rules.py.

⇢ THE AGENT POOL DIES. Fan-out hit credit exhaustion twice (1 of 16 agents; then 4 of 13). Round
3 DID complete 5/5 in ~79 min. Last session ran **entirely solo** and closed five defects — that
is a viable mode. Budget for solo work; say plainly which dimensions got deep treatment.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
**New last session:** *a claim verified against ONE module is a claim about that module* — say
"in `web/risks.py`", never "ever" · *a mutant that misses its subject proves nothing* — two
SURVIVED verdicts were battery defects, not code defects; before believing SURVIVED, confirm the
mutation touches the file the assertion reads and moves the observable it reads · *a self-baseline
absorbs what you are measuring* (`assert n == after_page` cannot see anything added inside
`after_page`) · *a control the CSP kills is invisible to every markup test* — for a control the
evidence is that clicking it CHANGES something · *a hand-maintained list of call sites is a stale
list waiting to happen; compute it* · *measure whether it IS a class before fixing it as one*.
**Standing:** a defence-in-depth twin hides a layer's death · a suggested fix is a hypothesis ·
"measured, then pinned" fixtures inherit whatever the code did that day — read fixture NAMES as
claims · compare two surfaces against each other · separate a safety PROPERTY from the OUTCOME it
was wired to · advice a user cannot follow is a bug · never measure a tree a battery is mutating ·
never mutate an instrument a measurement is using · monkeypatch per CALL SITE · use `python -m
ruff` · `| tail` masks exit codes · fetch before numbering AND committing · `wc` decides.

⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` and
`pip install build` first. Full suite ~19–30 min; `pytest -m parity` ~11.5 min (measured 690 s),
exceeds 900 s under load. CI ~60 min, cancel-in-progress: true — never push while you need a
run's signal. The installer build needs an UNSHALLOW clone (`git fetch --unshallow origin`) or it
refuses on ADR-0397's graft-boundary guard. NOTE: last session installed `playwright` (a declared
`browser` extra) into the container, so browser-gated test modules RUN there instead of skipping;
a fresh container skips them again.

⇢ OPERATOR-OWNED, not agent work: V-1/V-2/V-3 gateway verification · DISC-01 · the CEI/HMI vendor
export blocking PO-04/05 · **an SSI export showing a fired negative-impact (opportunity) register
entry, which would settle ADR-0414's parity leg** · branch cleanup. Note: the operator's desktop
launcher is a LOCAL "POLARIS" wrapper NOT in this repo — it refuses before invoking Python, so
ADR-0412's relocation cannot run on that path; the shipped "Schedule Forensics" shortcut must be
used.

⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model protocol (the LEAD re-verifies every finding before reporting) · full gate before
every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same commit · wheel +
nine installers ONCE per shipped-code change (ADR-0148). Skills: full-gate, prove-able-to-fail,
metric-parity, render-verify, cui-guard, ui-change, session-close.
