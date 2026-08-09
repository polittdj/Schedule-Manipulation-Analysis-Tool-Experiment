# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.181, highest ADR
0373, SCHEMA 2.11.0** — the 2026-08-08 (e) session closed phase-3 slice 9 (ADR-0373): the /sra
page family → `web/sra.py` (1,848 lines; 30 names / 22 regions; app.py 16,384 → 14,597), with
TWO descents into `components.py` (`_TS_CAPTION_MARK`, `_schedule_risks`) and the
`test_axis_titles` marker-counter repointed in the same commit. Census: prefix 847/13 vs
closure 32/1,756 — `_ssi_panel` + `_ssi_export_tables` came IN exactly as ADR-0365 priced
(the prefix is a finder, the closure is the definition). Proven on a 294-label oracle
(double-render determinism ×2 processes; 294/294 byte-identical pristine vs cut; falsified in
the new locations 32/32 EXACT; the slice-7 v4/v2 setup-load sequences returned — and the
FIRST v4 payload, aimed at COMPLETED uids 12–15, measured two FALSE darks until re-aimed at
the live critical chain 22/23/24: a crafted payload must target incomplete, finish-moving
work). Mutation battery 6/6 named (enumeration guard's 9th/10th consecutive live catch);
mutation 2's first shape drew the re-export guard too (defensive overlap, a true positive).
Shipped code changed → wheel + nine installers rebuilt at v1.0.181; draft PR open on
`claude/polaris-schedule-tool-resume-vdowl5`; if it has since squash-merged, restart the
branch: `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR activity
and drive CI to green before new work — shipped code + installers, so expect the SEVEN-check
set (check · floor · linux · windows · browser · test 3.11 · test 3.13). Fresh container:
`pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser tests
skip-gate — installing it locally wakes ~19 tests NO CI job runs; five of them fail
PRE-EXISTINGLY, adjudicated on a pristine-main worktree 2026-08-08: the blob-URL download
reporting on /trend /curves /scurve /cei and the SRA single-bin histogram caption contrast —
do not chase as regressions). Run ruff as **`python -m ruff`** and always **`ruff check .` —
THE WHOLE TREE**. Model protocol: ADR-0240 stands — parity-, engine-, testimony- or
CUI-relevant work stays on the strongest model. Use the skills (`.claude/skills/`):
`full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`,
`render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–9 (`components.py`
ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 ·
`margin.py` ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365 · `mission.py` ADR-0372 ·
`sra.py` ADR-0373). The intake manifest is CURRENT at 433 files / 99 mismatches; the `.mpp`
census pin is 28 (regenerate, never hand-edit). The 2026-08-07 audit's four P0s are CLOSED
(ADR-0366..0369). The target-UID pair scope is CLOSED end-to-end (ADR-0370 + ADR-0371). FX
fixture verdicts are FINAL.

⇢ DO THIS FIRST — the queue

1. Phase 3 monolith split resumes at slice 10 — by the re-measured prefix census (wc-truth;
   each family still owes its OWN closure before cutting — slice 9 re-proved why: closure 32
   names where the prefix saw 13): **forecast 391** · what 289 · portfolio 253 · evm 239 ·
   where 235 · how 214 — EACH per the ADR-0365 recipe (closure before cut · span-scoped
   probe · the six-mutation battery · the ADR-0372 oracle recipe with three normalizers;
   the 294-label label set from slice 9 is the current widest reference).
2. Then the standing queue: stored-SRA-fields MSPDI fixture (would light ADR-0373's three
   oracle-dark members from a FILE) · driving-corridor fixture · the three page-lede-less
   pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs
   known-good constraints · P80/P90 recurring-exception residual · the doc-drift sweep
   (docs/PARITY-REPORT.md still says the reference .mpps are git-ignored and calls
   Project2.mpp "CUI intake" — superseded by ADR-0151/0152; docs/FINAL-REPORT.md blanket
   "Exact match" beyond the three evidence tiers; CLAUDE.md's phase-3 + single-E501 lines
   lag — mission.py AND sra.py joined the E501 list) · ~150 MB RSS retained per loaded 9 MB
   file (no per-file unload) · Phase 6 docs. Operator only: re-convert FX-03/FX-04 (open
   the authored .xml, VERIFY UID17=5d / UID131=1w before save — MS Project re-derives
   Duration from stored dates and silently un-edits otherwise; the finish MUST move) then
   re-run Fuse and replace the two oracles · one Acumen run on a crafted sub-day-negative-
   float schedule (closes the Negative-Float O1 oracle gap — the AFT has NO formula for it)
   · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
   re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME

1. A crafted oracle payload aimed at COMPLETED tasks measures the fixture's history, not the
   member's reach (ADR-0373): target incomplete, finish-moving work on the live critical
   chain; believe a 0-move probe dark only after a SECOND, stronger anchor also moves 0.
2. Patch the patcher with landed-count discipline (ADR-0373): an unanchored heredoc replace
   on a harness script misses SILENTLY and re-runs last hour's mutation — use exact-match
   edits that fail loudly.
3. Constants carry `#:` doc-comment blocks the ast span does NOT see — extend move regions
   by eye before any byte moves.
4. One session knob, two semantics (ADR-0370/0371): a "queued exposure class" is a CENSUS,
   not a list — enumerate every caller of the old accessor in the same round.
5. An anchored computation can be truncation-INVARIANT — measure before pinning; the honest
   record for an unpinnable-but-correct move is an ADR paragraph, never a vacuous test.
6. Measure the control on EVERY engine a sweep re-bases: one fixture gave three DIFFERENT
   lie shapes.
7. A test whose setup can fail silently tests nothing: POST /target and assert the 303 in
   every test whose name claims a target was set (GET is a 405).
8. A revert that changes nothing "passes": anchor splices uniquely and put the landed-count
   assert INSIDE the mutation script, before the write.
9. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes; the dedupe
   twin deserves its own assert.
10. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
11. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
12. An environment defect can masquerade as a product defect — a pristine-main worktree with
    two `pip -e` flips is the cheap decisive adjudicator; an oracle label serving live
    telemetry is weather (ADR-0372) — normalize VALUES (keep shape) BEFORE the first
    byte-identity claim, adjudicate every unexpected mover by payload diff.
13. A binding-wrap spy undercounts — patch the module that CALLS or count at a construction
    choke point.
14. A mutation is "caught" only when the failure summary NAMES the test (pytest exit ≠
    failing test — assert the test RAN).
15. NEVER mutate the tree while a suite runs (docs included); restore from scratchpad `cp`,
    never `git checkout`; verify by ANCHOR-GREP.
16. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
    zero — chain with `;` never `&&`.
17. Parity evidence is three-tiered — never report uniform "Acumen-equivalent"; the
    strongest external-oracle tests SKIP without Java.
18. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals
    are non-additive BY DESIGN.
19. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
20. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form — derive a
    real ≥1 summary UID in tests.
21. A scratchpad-resident harness must HARDCODE the repo root — a walk-up from outside the
    repo loops silently at `/`; any root-walk must fail loudly.

⇢ Measured-false / load-sensitive, do NOT re-chase
Baseline-PRESENCE as the parity population (F5) — 4 named ADR-0280 pin failures; the AFT's
filter is `Baseline Duration GreaterThan 0`, verbatim. The `/analysis` focus→tip family is
load-sensitive. The five playwright-only failures named above are pre-existing
(pristine-main adjudicated) and CI-invisible. `pydantic>=2` is NOT a safe floor (2.6 is);
`fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens cannot render a driving
corridor (ADR-0351), /evolution's counterfactual (ADR-0352), or /integrity's
artifact-cluster (ADR-0358) — byte-identity is the guard there. The period-over-period
metric families match UIDs across versions on the FOCUSED scope by design — a documented
residual (ADR-0371), parity-oracled, do not re-base without its own adjudication. ADR-0373's
three oracle-dark members (`_SRA_RISK_PROB_FIELD` / `_SRA_RISK_IMPACT_FIELD` /
`_file_stored_risks`) are route-covered in Python — the MSPDI fixture is the named gap, not
a regression. Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never
weaken a test) · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every
commit (statics foreground; `node --check` per file; pytest to a file needs `python -u`) ·
handoff rotation + SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine
installers ONCE per shipped-code change (bump BEFORE the suite; REBUILD if code changes
after) · a number written mid-session is not a measurement (wc decides). Full local suite
~20 min (~28 with playwright installed) — run `python -u` in the BACKGROUND and read the
tail; CI registers checks ~11 min in; test jobs ~30 min.
