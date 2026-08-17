# Next-session kickoff prompt

Copy everything below the line into the new session.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the work queue. As of last
close: v1.0.212, highest ADR 0420, SCHEMA 2.11.0.
⇢ STATE OF THE BRANCH. ADR-0409..0420 are merged or in flight on
`claude/polaris-audit-continuation-i1cxqq` (draft PR). **`git fetch origin` and check whether that
PR merged before you branch** — if it did, branch fresh from `origin/main`; if it did not, continue
on it. Fetch before you branch, number an ADR, or commit. *(This file is written BEFORE the PR can
merge, so this paragraph is the one thing in it that is guaranteed stale — verify it, do not trust
it. Two consecutive sessions have now opened with a stale kickoff.)*
⇢ WHAT THIS ARC IS. Operator directive 2026-08-16: *"a complete deep dive audit of the entire
repository … create tests, both pass and fail … create solutions … test those in a sandbox to
verify prior to implementing any changes. Triple verify everything in independent ways … Test,
pass and fail tests required for all functionality of all pages … Skip nothing. Verify
everything."* It is NOT finished. **Twelve ADRs' worth of defects are fixed** (0409 HOOK-02 · 0410
MF-01 · 0411 MF-02 · 0412 launch dead-ends · 0413 REC-01 · 0414 MC-01 · 0415 TST-01 · 0416 JS-01 ·
0417 SRA export scope · 0418 BROWSER-ORPHAN-01 · **0419 IMP-01** · **0420 the MIXED-POPULATION
class**). ~35 findings remain REPORTED = unverified hypotheses, and the ledger's legend says so for
a measured reason — this audit has produced finder output wrong in BOTH directions, and the LEDGER
ITSELF has now been wrong about a POPULATION three times (0418: "four modules" were 23; 0420:
"three surfaces" were 8; and see item 1 below).
⇢ RESUME ORDER — start at 1, do not re-triage.
1. **THE ROUTE × TEST GAP-FILL** — the ledger says 137 routes, **5 with no success test, 16 with no
   failure-mode test**. This is the operator's "pass AND fail tests for all functionality of all
   pages" requirement and it is the LAST ledger count nobody has recomputed. **Re-derive it with a
   computed census BEFORE working it** — twice now a stated population has been smaller than the
   real one, and both times the row was counting the symptom rather than the thing.
2. **Never audited at all: page modules A/B · docs/config/CI · AI figure-gates.** The AI
   figure-gates just became more interesting: ADR-0420 found `_schedule_facts` — the fact sheet the
   AI is *allowed to cite* — was built on a raw population against a scoped CPM. That layer has had
   no dedicated pass.
3. The remaining REPORTED rows: CPM-01..04 · MF-03/04/06..10 · MC-02..08 ·
   `ASK-UNRESTRICTED-WRONG-VERSION` · `ISDIGIT-INT-500` · IMP-02..06 · MAN-01..03 · REC-02 ·
   JS-02..06.
⇢ DO-NOT-FIX-BLIND LIST. **MF-05** — an empty-population PASS may be CORRECT Acumen parity;
"fixing" it without the reference export would BREAK parity. Needs an operator-supplied oracle.
**MC-01's parity leg is UNVERIFIED by design** (ADR-0414): no committed SSI export exposes a fired
negative impact, so the shipped semantic is the documented-additive one; if an SSI opportunity
export arrives, `tests/engine/test_register_opportunity.py` is the module to re-baseline,
deliberately and in daylight. **ADR-0417's leg** still needs a non-degenerate SRA fixture (the
shipped example puts every percentile on one date). **NEW — ADR-0419's leg:** whether an MSPDI
"default times" working day is 480 or the file's own `<MinutesPerDay>` is UNVERIFIED; the fix only
collapsed two contradictory readings into one and did not decide that question. It needs a real MS
Project file that actually carries the construct — **zero of the 56 committed MSPDI documents do**.
⇢ BEFORE ANYTHING: CLAUDE.md carries QC-1 (prove or refute before reporting: red before green,
mutation-prove the teeth, sandbox it, say UNVERIFIED rather than assert silently) and QC-2 (read
everything, assume nothing; inherited claims incl. this file are testimony, not evidence).
ADR-0393, pinned by tests/test_standing_rules.py.
⇢ THE AGENT POOL DIES. Fan-out hit credit exhaustion twice. The last FOUR sessions ran **entirely
solo** and closed nine defects — that is the proven mode. Budget for solo work; say plainly which
dimensions got deep treatment and which got a lighter pass.
⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
**New last session:** *"is it WRONG" and "can it be REACHED" are two measurements* — IMP-01 is a
real 2× duration error AND unreachable from all 56 committed MSPDI files; reporting either half
alone misinforms · *a ledger row naming N surfaces may be naming N members of a CLASS* — a computed
census turned three rows into eight sites, and the three named ones were not the worst (the AI fact
sheet was) · *a test that re-derives what the route SHOULD compute cannot fail* — it passed against
the broken route until repointed at the shipped workbook bytes · *a red for the WRONG REASON is not
a red* — a `StopIteration` from a mis-cased label satisfied red-before-green in letter while the
assertion had never once run; only the mutant proved teeth · *a differential probe needs a control
expected to MOVE* — "STATIC" is also what a probe that never applied the filter reports.
**Standing:** a count may be counting the SYMPTOM, not the thing · an oracle that gives the same
verdict in both worlds is BLIND, not stale · a claim verified against ONE module is a claim about
that module · a mutant that misses its subject proves nothing · print "mutation landed: True" as
part of every mutant · a self-baseline absorbs what you are measuring · a control the CSP kills is
invisible to every markup test · compute a call-site list, never hand-maintain it · a suggested fix
is a hypothesis · "measured, then pinned" fixtures inherit the bug · compare two surfaces against
each other · never measure a tree a battery is mutating · never mutate an instrument a measurement
is using · monkeypatch per CALL SITE · use `python -m ruff` · **`ruff format` also formats python
code blocks inside MARKDOWN — an ADR failed CI 40 s in; and a PARTIAL gate is not a gate, so re-run
the WHOLE gate after the LAST file changes, not the last code change** · **`| tail` masks exit codes** — paid
TWO sessions running; last time a piped web-suite run buffered to 0 bytes for 20 minutes. Redirect
to a file. · fetch before numbering AND committing · `wc` decides.
⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` and
`pip install build` first. **`pip install playwright` if you will touch browser tests** — 94 tests
skip without it (they no longer skip for a missing BROWSER, only for the missing PACKAGE).
Full suite ~29 min. `pytest -m parity` ~10-11.5 min (measured 610 s). Browser census
`pytest $(python tools/browser_modules.py)` ~6-7 min. CI measured end-to-end: browser ~6 min, floor
~36 min, test (3.13) ~56 min, test (3.11) ~71 min — so budget **~75 min for a full CI verdict**,
and cancel-in-progress: true means **never push while you need a run's signal**. The installer
build needs an UNSHALLOW clone (`git fetch --unshallow origin`) or it refuses on ADR-0397's
graft-boundary guard; `python -m build --wheel --outdir dist/wheel && python
tools/installer/build_installers.py` takes ~2 min and rewrites all nine installers.
⇢ OPERATOR-OWNED, not agent work: V-1/V-2/V-3 gateway verification · DISC-01 · the CEI/HMI vendor
export blocking PO-04/05 · **an SSI export showing a fired negative-impact (opportunity) register
entry, which would settle ADR-0414's parity leg** · **an MS Project MSPDI file carrying a
`DayWorking=1` weekday with no `<WorkingTimes>`, which would settle ADR-0419's leg** · branch
cleanup. Note: the operator's desktop launcher is a LOCAL "POLARIS" wrapper NOT in this repo — it
refuses before invoking Python, so ADR-0412's relocation cannot run on that path; the shipped
"Schedule Forensics" shortcut must be used.
⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model protocol (the LEAD re-verifies every finding before reporting) · full gate before
every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same commit · wheel + nine
installers ONCE per shipped-code change (ADR-0148) — **ADR-0419/0420 DID change `src/`, so
v1.0.212 was cut and all nine installers rebuilt; check `git status src/` before assuming you owe
one.**
Skills: full-gate, prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change,
session-close.
