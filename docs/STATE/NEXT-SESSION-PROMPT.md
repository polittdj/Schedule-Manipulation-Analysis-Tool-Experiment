# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.179, highest ADR
0371, SCHEMA 2.11.0** — the 2026-08-08 (c) session closed the ADR-0370 exposure sweep
(ADR-0371): a caller-by-caller census found TEN surfaces still diffing target-truncated pairs;
on the control pair the truncation FABRICATED a HIGH "activities deleted" accusation while
hiding the real cut. /compare + its export, /evolution + /api/evolution + its export, both
whatif exports, and /export/mission's evolution tables now run WHOLESALE on `_pair_versions()`;
/trend's signal roll-up, `build_brief`'s pair questions and `build_briefing` section 3.1 take
surgical `pair_*` populations (per-version value series keep the ADR-0268 focus by design;
/api/evolution + whatif-added are behavior-invariant consistency moves, recorded in the ADR).
Shipped code changed → wheel + nine installers rebuilt; draft PR open on
`claude/polaris-schedule-tool-resume-wm3gvt`; if it has since squash-merged, restart the
branch: `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR
activity and drive CI to green before new work — shipped code + installers, so expect the
SEVEN-check set (check · floor · linux · windows · browser · test 3.11 · test 3.13). Fresh
container: `pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser
tests skip-gate — installing it locally wakes ~19 tests NO CI job runs; five of them fail
PRE-EXISTINGLY, adjudicated on a pristine-main worktree 2026-08-08: the blob-URL download
reporting on /trend /curves /scurve /cei and the SRA single-bin histogram caption contrast —
do not chase as regressions). Run ruff as **`python -m ruff`** and always **`ruff check .` —
THE WHOLE TREE**. Model protocol: ADR-0240 stands — parity-, engine-, testimony- or
CUI-relevant work stays on the strongest model. Use the skills (`.claude/skills/`):
`full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`,
`session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–7 (`components.py`
ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 ·
`margin.py` ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365). The intake manifest is
CURRENT at 433 files / 99 mismatches; the `.mpp` census pin is 28 (regenerate, never
hand-edit). The 2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369). The target-UID pair
scope is CLOSED end-to-end: /integrity (ADR-0370) AND the full exposure sweep (ADR-0371 —
compare/trend/evolution/whatif/mission-export/brief/briefing; 11 pins in
tests/web/test_pair_scope_exposure_sweep.py; mutation matrix 8/8 named). FX fixture verdicts
are FINAL.

⇢ DO THIS FIRST — the queue
1. Phase 3 monolith split resumes at **mission 304** (stale census — RE-MEASURE the closure
first; expect sra ~700+ over its "264": the panel 235 + `_ssi_export_tables` 248 +
`_file_stored_risks` wait there). Then: how 290 · sra (re-measured) · what 257 · where 235 ·
portfolio 231 · evm 208 · forecast 204 — EACH slice per the ADR-0365 recipe.
2. Then the standing queue: stored-SRA-fields MSPDI fixture · driving-corridor fixture · the
three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
installers vs known-good constraints · P80/P90 recurring-exception residual · the audit's
doc-drift sweep (docs/PARITY-REPORT.md still says the reference .mpps are git-ignored and
calls Project2.mpp "CUI intake" — superseded by ADR-0151/0152; docs/FINAL-REPORT.md blanket
"Exact match" beyond the three evidence tiers; CLAUDE.md's phase-3 + single-E501 lines lag) ·
~150 MB RSS retained per loaded 9 MB file (no per-file unload) · Phase 6 docs. Operator only:
re-convert FX-03/FX-04 (open the authored .xml, VERIFY UID17=5d / UID131=1w before save — MS
Project re-derives Duration from stored dates and silently un-edits otherwise; the finish
MUST move) then re-run Fuse and replace the two oracles · one Acumen run on a crafted
sub-day-negative-float schedule (closes the Negative-Float O1 oracle gap — the AFT has NO
formula for it) · license · branch-protection contexts · proprietary reruns · OR-04 · July
mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME
1. **One session knob, two semantics** (ADR-0370/0371): the Target UID is a population cut AND
a measurement anchor. A "queued exposure class" is a CENSUS, not a list — ADR-0370 named four
sites, the census found TEN. When a fix separates two meanings of one knob, enumerate every
caller of the old accessor in the same round.
2. **An anchored computation can be truncation-INVARIANT** (driving-slack chains ⊆ the target
cone): measure before pinning — the honest record for an unpinnable-but-correct move is an ADR
paragraph, never a vacuous test.
3. **Measure the control on EVERY engine a sweep re-bases**: one fixture gave three DIFFERENT
lie shapes (fabricated HIGH deleted-task · inverted entered/left · counterfactual starved to
None).
4. **A test whose setup can fail silently tests nothing**: POST /target and assert the 303 in
every test whose name claims a target was set (GET is a 405).
5. A revert that changes nothing "passes": anchor splices uniquely and put the landed-count
assert INSIDE the mutation script, before the write.
6. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes; the dedupe
twin deserves its own assert.
7. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
8. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
9. An environment defect can masquerade as a product defect — **a pristine-main worktree with
two `pip -e` flips is the cheap decisive adjudicator**.
10. A binding-wrap spy undercounts — patch the module that CALLS or count at a construction
choke point.
11. A mutation is "caught" only when the failure summary NAMES the test.
12. NEVER mutate the tree while a suite runs (docs included); restore from scratchpad `cp`,
never `git checkout`; verify by ANCHOR-GREP.
13. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
zero — chain with `;` never `&&`.
14. Parity evidence is three-tiered — never report uniform "Acumen-equivalent"; the strongest
external-oracle tests SKIP without Java.
15. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals are
non-additive BY DESIGN.
16. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
17. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form — derive a
real ≥1 summary UID in tests.

⇢ Measured-false / load-sensitive, do NOT re-chase
Baseline-PRESENCE as the parity population (F5) — 4 named ADR-0280 pin failures; the AFT's
filter is `Baseline Duration GreaterThan 0`, verbatim. The `/analysis` focus→tip family is
load-sensitive. The five playwright-only failures named above are pre-existing (pristine-main
adjudicated) and CI-invisible. `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` an
AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens cannot render a driving corridor (ADR-0351),
/evolution's counterfactual (ADR-0352), or /integrity's artifact-cluster (ADR-0358) —
byte-identity is the guard there. The period-over-period metric families (CEI/HMI trends,
bow-wave, volatility) match UIDs across versions on the FOCUSED scope by design — a documented
residual (ADR-0371), parity-oracled, do not re-base without its own adjudication. Standing
rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ
EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every commit (statics
foreground; `node --check` per file; pytest to a file needs `python -u`) · handoff rotation +
SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine installers ONCE per
shipped-code change (bump BEFORE the suite; REBUILD if code changes after) · a number written
mid-session is not a measurement (wc decides). Full local suite ~20 min (~28 with playwright
installed) — run `python -u` in the BACKGROUND and read the tail; CI registers checks ~11 min
in; test jobs ~30 min.
