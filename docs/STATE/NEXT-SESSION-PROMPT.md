# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.186, highest ADR
0378, SCHEMA 2.11.0** — the 2026-08-09 (e) session closed phase-3 slice 14 (ADR-0378): the
/performance family → NEW `web/performance.py` (383 lines; **four movers in ONE contiguous
block**, app.py 10761–11092: `_perf_version_block` · `_performance_data` ·
`_how_we_execute_header` · `_performance_body`) and — first time since ADR-0364 — **NO descent**
(the one shared name the walk surfaced, `_sources_line`, is called by the ROUTE, not by a mover;
routes live in `create_app` and import downward). app.py 11,735 → 11,403 wc-truth. **The closure
was CENSUS-EXACT for the first time in phase 3** (4 names / 326 ast lines both ways, 1.00×,
against 1.15× mildest and 3.6× widest before) — but only because ADR-0375's ruling-lag finding had
already been hand-folded into the queue; the referrer walk stays the definition. **The
export-contributes-no-movers streak ENDED at five**: `export_performance` reads
`_performance_data`, so both export formats sit inside the family's proven surface — and a
page-only probe anchor UNDERSTATES such a member (the first anchor rode the TableSet title, which
reaches the page and DOCX but not xlsx sheet content: 6 labels instead of 9). Proven on the same
498-label oracle (ADR-0372 recipe + ADR-0375 title-stripped TP4 pool; target UID 22; three
normalizers, each made LOUD; determinism ×2 processes 0 flapping): 498/498 byte-identical pristine
vs cut; probe 4/4 render-proven ZERO dark (fifth consecutive) — `_perf_version_block` 9 ·
`_performance_data` 9 · both headers 3; falsified in new locations 4/4 EXACT label lists; multiset
51 added / 0 removed — zero code lines removed; battery 6/6 named (enumeration guard's 19th/20th
consecutive catches) plus a seventh for the spy repoint. **The dropped-import sweep reported 0
readers and was WRONG** — it was a regex over the alias `app_mod` while two P3-memo spies spell it
`app_module`; the SUITE caught it (2 failed / 3544 passed on the first run), both spies were
repointed to performance.py and proven load-bearing, and the sweep is now alias-agnostic (bare NAME
across tests/). The zero-reader-repoint streak ENDS at four. Monkeypatch sweep: ONE hit, `compute_activity_makeup` — slice 12's standing
ADR-0291 adjudication, re-verified green post-cut, NOT a new one (`non_summary` is not bound here).
Shipped code changed → wheel + nine installers rebuilt at v1.0.186; draft PR open on
`claude/polaris-v1-resume-w49pj3` (this container's designated branch); if it has since
squash-merged, restart the branch: `git fetch --prune origin && git remote set-head origin -a &&
git checkout -B <branch> origin/main` (then `git branch --unset-upstream`). If still open,
subscribe to its PR activity and drive CI to green before new work — shipped code + installers, so
expect the SEVEN-check set (check · floor · linux · windows · browser · test 3.11 · test 3.13).
Fresh container: `pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser
tests skip-gate — installing it locally wakes ~19 tests NO CI job runs; five of them fail
PRE-EXISTINGLY, adjudicated on a pristine-main worktree 2026-08-08: the blob-URL download reporting
on /trend /curves /scurve /cei and the SRA single-bin histogram caption contrast — do not chase as
regressions). Run ruff as `python -m ruff` and always `ruff check .` — THE WHOLE TREE (two ruffs
live on PATH; `python -m` pins the pip-installed one). Model protocol: ADR-0240 stands — parity-,
engine-, testimony- or CUI-relevant work stays on the strongest model. Use the skills
(`.claude/skills/`): `full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`,
`render-verify`, `session-close`. ⇢ WHAT'S DONE — do NOT re-open Monolith split: phases 1–2
(`state.py`, `chrome.py`) + phase 3 slices 1–14 (`components.py` ADR-0350 · `driving.py` ADR-0351 ·
`evolution.py` ADR-0352 · `integrity.py` ADR-0358 · `margin.py` ADR-0363 · `trend.py` ADR-0364 ·
`ssi.py` ADR-0365 · `mission.py` ADR-0372 · `sra.py` ADR-0373 · `forecast.py` ADR-0374 ·
`portfolio.py` + two retroactive headers ADR-0375 · `analysis.py` + the `_target_panel` descent
ADR-0376 · `evm.py` + the `_metric_scorecard_table` descent ADR-0377 · `performance.py` ADR-0378).
The question-word censuses (what/how/where) are RETIRED. The intake manifest is CURRENT at 433
files / 99 mismatches; the `.mpp` census pin is 28 (regenerate, never hand-edit). The 2026-08-07
audit's four P0s are CLOSED (ADR-0366..0369). The target-UID pair scope is CLOSED end-to-end
(ADR-0370 + ADR-0371). FX fixture verdicts are FINAL. ⇢ DO THIS FIRST — the queue

1. Phase 3 monolith split resumes at slice 15 — by the post-cut census (wc-truth; each family
still owes its OWN closure before cutting; membership NAMED because the prefix is a finder, not
the definition): resources 306 (`_resources_body` 157 + `_resources_explainer` 20 +
`_resource_loading_json` 51 + `_who_is_overloaded_header` 78) · scurve 212 · path 194 (incl.
`_what_drives_header` 80) · compare 166 (incl. `_what_changed_header` 79) — EACH per the ADR-0365
recipe (closure before cut · span-scoped probe · the six-mutation battery · the ADR-0372 oracle
recipe with three normalizers; the 498-label oracle with the TITLE-STRIPPED TP4 pool is the current
widest reference — the title-strip is load-bearing; **the export fmts are `xlsx` and `docx`, NOT
csv; `{name}` keys drop the `.xml`**; the fingerprint is 88 ALL-stages / 69 loaded-stages;
/openapi.json is the 60th parameterless GET; keep the [grouped] labels). groups (430 by prefix)
stays OUTSIDE the phase-3 list while ADR-0343 feature work is queued against it.
2. Then the standing queue: stored-SRA-fields MSPDI fixture (would light ADR-0373's three
oracle-dark members from a FILE) · driving-corridor fixture · the three page-lede-less pages
(/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good constraints
· P80/P90 recurring-exception residual · the doc-drift sweep (docs/PARITY-REPORT.md still says the
reference .mpps are git-ignored and calls Project2.mpp "CUI intake" — superseded by ADR-0151/0152;
docs/FINAL-REPORT.md blanket "Exact match" beyond the three evidence tiers; CLAUDE.md's phase-3 +
single-E501 lines lag — mission.py, sra.py, forecast.py, portfolio.py, analysis.py, evm.py AND
performance.py joined the E501 list) · ~150 MB RSS retained per loaded 9 MB file (no per-file
unload) · Phase 6 docs. Operator only: re-convert FX-03/FX-04 (open the authored .xml, VERIFY
UID17=5d / UID131=1w before save — MS Project re-derives Duration from stored dates and silently
un-edits otherwise; the finish MUST move) then re-run Fuse and replace the two oracles · one Acumen
run on a crafted sub-day-negative-float schedule (closes the Negative-Float O1 oracle gap — the AFT
has NO formula for it) · license · branch-protection contexts · proprietary reruns · OR-04 · July
mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME

1. A census CAN be exact and still not be membership (ADR-0378): slice 14's closure matched its
prefix 1.00×, but only because a prior ADR's ruling had been hand-folded into the queue. The
referrer walk assigns membership — always.
2. A page-only probe anchor UNDERSTATES a member that feeds an export (ADR-0378): the TableSet
title reaches the page and the DOCX body but NOT xlsx sheet content, so a nine-label member
measured six. Anchor on what the export's own tables render — ADR-0373's stronger-anchor round is
not just for 0-move members.
3. A shared name does NOT force a descent (ADR-0378): adjudicate by WHO refers to it. A route-only
referrer never blocks — routes live in `create_app` and import downward.
4. SWEEP BY BARE NAME, never a module-qualified regex (ADR-0378): the dropped-import sweep aimed at
`app_mod.<name>` and missed two `app_module` spies, reporting 0 readers with its positive control
LIVE. A positive control proves the sweep RUNS, not that its PATTERN is right. A repointed spy owes
a prove-able-to-fail round — revert the patch target; it must fail.
5. A quiescence guard can match its own shell (ADR-0378): `pgrep -f pytest` fired on a clean tree
because the checking shell carries the heredoc in its argv (`[p]ytest` fails identically). Scan
`/proc` for python processes excluding this pid; adjudicate the match before deleting the guard.
6. A population fingerprint is only as good as its stated SCOPE (ADR-0377): 88 spans ALL FOUR
stages; the three loaded stages measure 69. Carry the scope with the number.
7. `/openapi.json` is the 60th parameterless GET (ADR-0377) — enumerate `app.routes` by method +
path, never by route class.
8. A normalizer that can fail silently is a FLAP FACTORY (ADR-0377) — make every normalizer raise
on a zero-match. Adjudicate every flap by PAYLOAD DIFF before touching the harness.
9. A descent's SECOND family can be probe-proven live (ADR-0377).
10. A page family's closure can run 3.6× its prefix (ADR-0376): price the cut by referrer walk.
11. Never MEASURE a tree a battery is mutating (ADR-0376); md5-verify against snapshots first.
12. The monkeypatch sweep's adjudication list GROWS as families move (ADR-0376/0378).
13. A census family can be a PHANTOM (ADR-0375).
14. The oracle's fixture POPULATION is a render condition (ADR-0375): title-strip the TP4 uploads.
15. A header stranded by ruling-lag moves retroactively once its family's module exists (ADR-0375).
16. A render-CONDITIONAL member needs its condition IN the oracle (ADR-0374).
17. The installer lockstep guard makes the rebuild a PREREQUISITE of the final suite run (ADR-0374).
18. A crafted oracle payload aimed at COMPLETED tasks measures the fixture's history (ADR-0373).
19. Patch the patcher with landed-count discipline (ADR-0373) — exact-match edits that fail loudly.
20. An anchor that collides is not span-scoped (ADR-0377): assert count == 1 IN FILE and the anchor
line INSIDE the member's ast span, before every probe.
21. Constants carry `#:` doc-comment blocks the ast span does NOT see — extend regions by eye.
22. One session knob, two semantics (ADR-0370/0371): a "queued exposure class" is a CENSUS.
23. An anchored computation can be truncation-INVARIANT — measure before pinning.
24. Measure the control on EVERY engine a sweep re-bases.
25. A test whose setup can fail silently tests nothing: POST /target and assert the 303 (GET is 405).
26. A revert that changes nothing "passes": anchor splices uniquely, landed-count assert INSIDE the
mutation script, before the write.
27. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes.
28. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
29. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
30. An environment defect can masquerade as a product defect — a pristine-main worktree is the cheap
decisive adjudicator; normalize live telemetry by VALUE before the first byte-identity claim.
31. A binding-wrap spy undercounts — patch the module that CALLS.
32. A mutation is "caught" only when the failure summary NAMES the test (pytest exit ≠ failing test).
33. NEVER mutate the tree while a suite runs; restore from scratchpad `cp`, never `git checkout`.
34. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on zero.
35. Parity evidence is three-tiered — the strongest external-oracle tests SKIP without Java.
36. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals are
non-additive BY DESIGN.
37. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
38. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form.
39. A scratchpad-resident harness must HARDCODE the repo root — a walk-up loops silently at `/`.

⇢ Measured-false / load-sensitive, do NOT re-chase Baseline-PRESENCE as the parity population (F5)
— 4 named ADR-0280 pin failures; the AFT's filter is `Baseline Duration GreaterThan 0`, verbatim.
The `/analysis` focus→tip family is load-sensitive. The five playwright-only failures named above
are pre-existing (pristine-main adjudicated) and CI-invisible. `pydantic>=2` is NOT a safe floor
(2.6 is); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens cannot render a driving
corridor (ADR-0351), /evolution's counterfactual (ADR-0352), or /integrity's artifact-cluster
(ADR-0358) — byte-identity is the guard there. The period-over-period metric families match UIDs
across versions on the FOCUSED scope by design — a documented residual (ADR-0371), parity-oracled.
ADR-0373's three oracle-dark members (`_SRA_RISK_PROB_FIELD` / `_SRA_RISK_IMPACT_FIELD` /
`_file_stored_risks`) are route-covered in Python — the MSPDI fixture is the named gap, not a
regression. Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test)
· READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every commit (statics
foreground; `node --check` per file; pytest to a file needs `python -u`) · handoff rotation +
SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine installers ONCE per shipped-code
change (bump BEFORE the suite; REBUILD if code changes after; the rebuild PRECEDES the final suite
run) · a number written mid-session is not a measurement (wc decides). Full local suite ~20 min
(~28 with playwright installed) — run `python -u` in the BACKGROUND and read the tail; CI registers
checks ~11 min in; test jobs ~30 min.
