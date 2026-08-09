# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.182, highest ADR
0374, SCHEMA 2.11.0** — the 2026-08-09 session closed phase-3 slice 10 (ADR-0374): the
/forecast page family → `web/forecast.py` (830 lines; 9 names / one contiguous block; app.py
14,583 → 13,814), NO descents, no stays beyond the routes — the first multi-member slice with
ZERO oracle-dark members. Census: prefix 391/4 vs closure 9/778 — and the prefix had filed
`_where_it_lands_header` (77 lines, chapter 09's header, sole referrer `forecast_view`) under
the WHERE family: the census numbers are finders for SIZING, never membership (where re-prices
235 → 158). The 2-family ruling: `_field_forecast_panel` (forecast_view + evm_view) moved with
its eponymous family — route referrers never block, no mover referenced it, 2 < the components
threshold of 3; /evm reaches it via the re-export, and when /evm is cut the panel is already
below it. Proven on a **420-label oracle** (double-render determinism ×2 processes; 420/420
byte-identical pristine vs cut; falsified in the new locations 9/9 EXACT — label LISTS, not
counts; anchors on the live critical chain BY DESIGN, target UID 22; NEW four [grouped] labels
— /forecast + /evm ?group_field=Resource + both field-forecast exports — without which
`_group_rollup_panel` (renders ONLY when a field is chosen) would be dark by construction:
read each member's render CONDITION off the route BEFORE building the oracle). Mutation
battery 6/6 named (enumeration guard's 11th/12th consecutive live catch); mutations 2 and 5
in-body from the start (ADR-0373's defensive-overlap finding applied, not re-derived).
Shipped code changed → wheel + nine installers rebuilt at v1.0.182; draft PR open on
`claude/polaris-schedule-tool-resume-5t4g8w`; if it has since squash-merged, restart the
branch: `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR activity
and drive CI to green before new work — shipped code + installers, so expect the SEVEN-check
set (check · floor · linux · windows · browser · test 3.11 · test 3.13). Fresh container:
`pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser tests
skip-gate — installing it locally wakes ~19 tests NO CI job runs; five of them fail
PRE-EXISTINGLY, adjudicated on a pristine-main worktree 2026-08-08: the blob-URL download
reporting on /trend /curves /scurve /cei and the SRA single-bin histogram caption contrast —
do not chase as regressions). Run ruff as **`python -m ruff`** and always **`ruff check .` —
THE WHOLE TREE** (two ruffs live on PATH; `python -m` pins the pip-installed one). Model
protocol: ADR-0240 stands — parity-, engine-, testimony- or CUI-relevant work stays on the
strongest model. Use the skills (`.claude/skills/`): `full-gate`, `prove-able-to-fail`,
`metric-parity`, `ui-change`, `cui-guard`, `render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–10 (`components.py`
ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 ·
`margin.py` ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365 · `mission.py` ADR-0372 ·
`sra.py` ADR-0373 · `forecast.py` ADR-0374). The intake manifest is CURRENT at 433 files /
99 mismatches; the `.mpp` census pin is 28 (regenerate, never hand-edit). The 2026-08-07
audit's four P0s are CLOSED (ADR-0366..0369). The target-UID pair scope is CLOSED end-to-end
(ADR-0370 + ADR-0371). FX fixture verdicts are FINAL.

⇢ DO THIS FIRST — the queue

1. Phase 3 monolith split resumes at slice 11 — by the post-cut prefix census (wc-truth;
   each family still owes its OWN closure before cutting — slice 10 re-proved why twice:
   closure 9 names where the prefix saw 4, and one member filed under the WRONG family):
   **what 289** · portfolio 253 · evm 239 · how 214 · where 158 — EACH per the ADR-0365
   recipe (closure before cut · span-scoped probe · the six-mutation battery · the ADR-0372
   oracle recipe with three normalizers; the 420-label set from slice 10 is the current
   widest reference — its [grouped] labels are the only execution proof for
   `_group_rollup_panel`, keep them). When /evm is cut, `_field_forecast_panel` is already
   below it in `forecast.py`.
2. Then the standing queue: stored-SRA-fields MSPDI fixture (would light ADR-0373's three
   oracle-dark members from a FILE) · driving-corridor fixture · the three page-lede-less
   pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs
   known-good constraints · P80/P90 recurring-exception residual · the doc-drift sweep
   (docs/PARITY-REPORT.md still says the reference .mpps are git-ignored and calls
   Project2.mpp "CUI intake" — superseded by ADR-0151/0152; docs/FINAL-REPORT.md blanket
   "Exact match" beyond the three evidence tiers; CLAUDE.md's phase-3 + single-E501 lines
   lag — mission.py, sra.py AND forecast.py joined the E501 list) · ~150 MB RSS retained per
   loaded 9 MB file (no per-file unload) · Phase 6 docs. Operator only: re-convert FX-03/
   FX-04 (open the authored .xml, VERIFY UID17=5d / UID131=1w before save — MS Project
   re-derives Duration from stored dates and silently un-edits otherwise; the finish MUST
   move) then re-run Fuse and replace the two oracles · one Acumen run on a crafted
   sub-day-negative-float schedule (closes the Negative-Float O1 oracle gap — the AFT has NO
   formula for it) · license · branch-protection contexts · proprietary reruns · OR-04 ·
   July mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME

1. The prefix census can file a member under the WRONG family (ADR-0374):
   `_where_it_lands_header` sat in the "where" number while belonging to /forecast — a
   name's leading word is not its referrer graph; only the closure assigns membership.
2. A render-CONDITIONAL member needs its condition IN the oracle (ADR-0374):
   `_group_rollup_panel` renders only when `group_field` is set — read each member's render
   condition off the route BEFORE building the oracle, or a false dark burns a
   stronger-anchor round ("aim at states that can render").
3. The installer lockstep guard makes the rebuild a PREREQUISITE of the final suite run
   (ADR-0374): a suite started before the rebuild honestly fails the lockstep family —
   sequence bump → build → docs → THEN the one suite whose counts you quote.
4. A crafted oracle payload aimed at COMPLETED tasks measures the fixture's history, not the
   member's reach (ADR-0373): target incomplete, finish-moving work on the live critical
   chain; believe a 0-move probe dark only after a SECOND, stronger anchor also moves 0.
5. Patch the patcher with landed-count discipline (ADR-0373): an unanchored heredoc replace
   on a harness script misses SILENTLY and re-runs last hour's mutation — use exact-match
   edits that fail loudly.
6. Constants carry `#:` doc-comment blocks the ast span does NOT see — extend move regions
   by eye before any byte moves.
7. One session knob, two semantics (ADR-0370/0371): a "queued exposure class" is a CENSUS,
   not a list — enumerate every caller of the old accessor in the same round.
8. An anchored computation can be truncation-INVARIANT — measure before pinning; the honest
   record for an unpinnable-but-correct move is an ADR paragraph, never a vacuous test.
9. Measure the control on EVERY engine a sweep re-bases: one fixture gave three DIFFERENT
   lie shapes.
10. A test whose setup can fail silently tests nothing: POST /target and assert the 303 in
    every test whose name claims a target was set (GET is a 405).
11. A revert that changes nothing "passes": anchor splices uniquely and put the landed-count
    assert INSIDE the mutation script, before the write.
12. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes; the dedupe
    twin deserves its own assert.
13. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
14. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
15. An environment defect can masquerade as a product defect — a pristine-main worktree with
    two `pip -e` flips is the cheap decisive adjudicator; an oracle label serving live
    telemetry is weather (ADR-0372) — normalize VALUES (keep shape) BEFORE the first
    byte-identity claim, adjudicate every unexpected mover by payload diff.
16. A binding-wrap spy undercounts — patch the module that CALLS or count at a construction
    choke point.
17. A mutation is "caught" only when the failure summary NAMES the test (pytest exit ≠
    failing test — assert the test RAN).
18. NEVER mutate the tree while a suite runs (docs included); restore from scratchpad `cp`,
    never `git checkout`; verify by ANCHOR-GREP.
19. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
    zero — chain with `;` never `&&`.
20. Parity evidence is three-tiered — never report uniform "Acumen-equivalent"; the
    strongest external-oracle tests SKIP without Java.
21. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals
    are non-additive BY DESIGN.
22. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
23. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form — derive a
    real ≥1 summary UID in tests.
24. A scratchpad-resident harness must HARDCODE the repo root — a walk-up from outside the
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
after; the rebuild PRECEDES the final suite run) · a number written mid-session is not a
measurement (wc decides). Full local suite ~20 min (~28 with playwright installed) — run
`python -u` in the BACKGROUND and read the tail; CI registers checks ~11 min in; test jobs
~30 min.
