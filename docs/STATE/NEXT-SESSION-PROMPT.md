# Next-session kickoff prompt

Copy everything below the line into the new session.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the work queue. As of last
close: v1.0.211, highest ADR 0418, SCHEMA 2.11.0.
⇢ STATE OF THE BRANCH. ADR-0409..0417 are merged on main (PRs #595, #596, #597). ADR-0418 is on
`claude/polaris-browser-orphan-01-3824ij` (draft PR) — **check whether it merged before you
branch.** `git fetch origin` before you branch, number an ADR, or commit.
⇢ WHAT THIS ARC IS. Operator directive 2026-08-16: *"a complete deep dive audit of the entire
repository … create tests, both pass and fail … create solutions … test those in a sandbox to
verify prior to implementing any changes. Triple verify everything in independent ways … Test,
pass and fail tests required for all functionality of all pages … Skip nothing. Verify
everything."* It is NOT finished. **Ten defects are now fixed** (ADR-0409 HOOK-02 · ADR-0410
MF-01 · ADR-0411 MF-02 · ADR-0412 launch dead-ends · ADR-0413 REC-01 · ADR-0414 MC-01 ·
ADR-0415 TST-01 · ADR-0416 JS-01 · ADR-0417 SRA export scope · **ADR-0418 BROWSER-ORPHAN-01**).
~40 findings remain REPORTED = unverified hypotheses, and the ledger's legend says so for a
measured reason — this audit has produced finder output wrong in BOTH directions, and last
session the LEDGER ITSELF was wrong twice: it under-counted an orphan population by 19 modules
(it counted failures, not orphans), and its "undiagnosed histogram failure" turned out to be a
correct product with a BLIND oracle, not a broken product.
⇢ RESUME ORDER — start at 1, do not re-triage.
1. **IMP-01** (*high*) — two importer interpretations said to "materially move every displayed
   number" (a fallback path). Verify before anything else in the importer dimension.
2. **The three MIXED-POPULATION claims** — `ANALYSIS-HEADER-MIXED-POPULATION`,
   `RIBBON-MIXED-POPULATION`, `ANALYSIS-EXPORT-QUALITY-UNSCOPED`: counts computed on the RAW
   schedule while the page claims the scoped one. **One scoped-vs-raw probe can settle all
   three** — and SRA-EXPORT-STALE-SCOPE (ADR-0417) was exactly this family, so the technique is
   proven: change the scope, then diff two surfaces against each other.
3. **The route × test gap-fill** — 137 routes (enumerated twice independently); **5 have no
   success test, 16 have no failure-mode test**. Scoped, NOT built. This is the operator's
   "pass AND fail tests for all functionality of all pages" requirement. NOTE: re-derive those
   counts with a computed census before working them — last session proved a ledger count can
   be counting the symptom rather than the thing.
4. **Never audited at all: page modules A/B · docs/config/CI · AI figure-gates.**
5. The remaining REPORTED rows: CPM-01..04 · MF-03/04/06..10 · MC-02..08 ·
   `ASK-UNRESTRICTED-WRONG-VERSION` · `ISDIGIT-INT-500` · IMP-02..06 · MAN-01..03 · REC-02 ·
   JS-02..06.
⇢ DO-NOT-FIX-BLIND LIST. **MF-05** — an empty-population PASS may be CORRECT Acumen parity;
"fixing" it without the reference export would BREAK parity. Needs an operator-supplied oracle.
Also **MC-01's parity leg is UNVERIFIED by design** (ADR-0414): no committed SSI export exposes a
fired negative impact, so the shipped semantic is the documented-additive one; if an SSI
opportunity export ever arrives, `tests/engine/test_register_opportunity.py` is the module to
re-baseline, deliberately and in daylight. Same for ADR-0417's unverified leg (needs a
non-degenerate SRA fixture) and **ADR-0418's runner leg** — `chrome_kwargs()` returning `{}` is
proven locally, but "playwright then finds a browser on a GitHub runner" is attested only by CI's
existing green `browser` job. **The first CI run of the ADR-0418 branch closes that leg — look at
it.** The `browser` job now runs 24 modules (~6 min), not one.
⇢ BEFORE ANYTHING: CLAUDE.md carries QC-1 (prove or refute before reporting: red before green,
mutation-prove the teeth, sandbox it, say UNVERIFIED rather than assert silently) and QC-2 (read
everything, assume nothing; inherited claims incl. this file are testimony, not evidence).
ADR-0393, pinned by tests/test_standing_rules.py.
⇢ THE AGENT POOL DIES. Fan-out hit credit exhaustion twice (1 of 16 agents; then 4 of 13). The
last two sessions ran **entirely solo** and closed six defects between them — that is a viable
mode. Budget for solo work; say plainly which dimensions got deep treatment.
⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
**New last session:** *a count may be counting the SYMPTOM, not the thing* — 4 modules failed, 23
were orphaned; a census built from what went red under-reports by construction, because a skip is
silent · *an oracle that gives the same verdict in both worlds is BLIND, not stale* — before
repairing a failing check, break its subject deliberately and confirm the verdict CHANGES; if it
does not, the bug is in the instrument · *a screenshot's resolution is part of the measurement*
(1.17:1 at 1×, 3.07:1 at 5× for the same caption) · *joining two populations by a non-unique key*
scores items against each other's evidence — make the pairing structural, not keyed · *restoring a
population is part of a repair* — a fix that quietly took a sweep from 5 to 2 is a weaker check
wearing a passing badge · *print "mutation landed: True" as part of every mutant* — a `sed` whose
delimiter collided with its own pattern applied nothing and its "SURVIVED" concealed a weak
assertion.
**Standing:** a claim verified against ONE module is a claim about that module · a mutant that
misses its subject proves nothing · a self-baseline absorbs what you are measuring · a control the
CSP kills is invisible to every markup test · a hand-maintained list of call sites is a stale list
waiting to happen — compute it · a defence-in-depth twin hides a layer's death · a suggested fix is
a hypothesis · "measured, then pinned" fixtures inherit whatever the code did that day · compare
two surfaces against each other · advice a user cannot follow is a bug · never measure a tree a
battery is mutating · never mutate an instrument a measurement is using · monkeypatch per CALL
SITE · use `python -m ruff` · **`| tail` masks exit codes** (paid again last session: a piped
`ruff format --check` failure surfaced as a bare "exit 1" and cost a 6-minute re-run) · fetch
before numbering AND committing · `wc` decides.
⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` and
`pip install build` first. **`pip install playwright` if you will touch browser tests** — without
it 94 tests skip (they no longer skip for a missing BROWSER, only for the missing PACKAGE).
Full suite ~19–31 min; `pytest -m parity` ~11.5 min (measured 690 s), exceeds 900 s under load.
The browser census alone (`pytest $(python tools/browser_modules.py)`) is ~7 min. CI ~60 min,
cancel-in-progress: true — never push while you need a run's signal. The installer build needs an
UNSHALLOW clone (`git fetch --unshallow origin`) or it refuses on ADR-0397's graft-boundary guard.
⇢ OPERATOR-OWNED, not agent work: V-1/V-2/V-3 gateway verification · DISC-01 · the CEI/HMI vendor
export blocking PO-04/05 · **an SSI export showing a fired negative-impact (opportunity) register
entry, which would settle ADR-0414's parity leg** · branch cleanup. Note: the operator's desktop
launcher is a LOCAL "POLARIS" wrapper NOT in this repo — it refuses before invoking Python, so
ADR-0412's relocation cannot run on that path; the shipped "Schedule Forensics" shortcut must be
used.
⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model protocol (the LEAD re-verifies every finding before reporting) · full gate before
every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same commit · wheel +
nine installers ONCE per shipped-code change (ADR-0148) — **ADR-0418 changed no `src/`, so no
rebuild happened and v1.0.211 stands; check `git status src/` before assuming you owe one.**
Skills: full-gate, prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change,
session-close.
