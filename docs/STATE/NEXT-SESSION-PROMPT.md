# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.185, highest ADR
0377, SCHEMA 2.11.0** — the 2026-08-09 (d) session closed phase-3 slice 13 (ADR-0377): the /evm
family → NEW `web/evm.py` (378 lines; **six movers in ONE contiguous block**, app.py 9816–10149:
`_threshold_legend` · `_evm_idx_str` · `_evm_days_str` · `_evm_explainer` ·
`_how_we_execute_evm_header` · `_evm_body`) PLUS one descent — `_metric_scorecard_table` (19
lines) → `web/components.py` under the ADR-0351/0365 **mover+stayer** rule (mover `_evm_body`,
stayer `_groups_body`; components' imports gain `MetricResult`). app.py **12,082 → 11,735**
wc-truth (the prior handoff's 12,096 was superseded by the measured tree — wc decides). The
closure ran 1.15× the prefix (299 → 343 ast lines) — the mildest undercount since mission, but
BOTH unprefixed members were exactly the shapes a census cannot see, so the referrer walk stays
the definition. The export route contributed NO movers (mission shape, FIFTH consecutive).
**The headline: the 88-count 4xx fingerprint spans ALL FOUR oracle stages, not "the three
loaded stages" as ADR-0375/0376's prose said** — the first check here read 69 and correctly
tripped adjudicate-before-use; the payload answer was that the population is IDENTICAL and the
prose scope was wrong (all seventeen 400s are `[empty]`-stage no-schedule guards; 69 = 12×404 +
57×422 IS ADR-0374's own three-state histogram). Compare **88 all-stages** or **69
loaded-stages** — never loaded-stages against 88. Proven on the same 498-label oracle
(ADR-0372 recipe + ADR-0375 title-stripped TP4 pool; target UID 22 live-chain; three
normalizers; determinism ×2 processes 0 flapping): 498/498 byte-identical pristine vs cut;
probe **7/7 render-proven ZERO dark** (fourth consecutive slice) with the descent moving **9**
labels — /evm ×6 PLUS /groups ×3, the first descent whose SECOND family was probe-proven live;
falsified in new locations 7/7 EXACT label lists; multiset 48/1 zero code lines removed;
battery 6/6 named (enumeration guard's 17th/18th consecutive catches). Monkeypatch sweep: ONE
hit, the standing `app_mod.non_summary` control (evm.py also binds it; adjudication re-verified
green post-cut — `compute_activity_makeup` is NOT bound here, so slice 12's second adjudication
did not grow). Shipped code changed → wheel + nine installers rebuilt at v1.0.185; draft PR
open on `claude/polaris-v1-resume-s4h74l` (this container's designated branch); if it has since
squash-merged, restart the branch: `git fetch --prune origin && git remote set-head origin -a &&
git checkout -B <branch> origin/main` (then `git branch --unset-upstream`). If still open,
subscribe to its PR activity and drive CI to green before new work — shipped code + installers,
so expect the SEVEN-check set (check · floor · linux · windows · browser · test 3.11 · test
3.13). Fresh container: `pip install -e ".[dev]"` plus `pip install build` (playwright optional,
browser tests skip-gate — installing it locally wakes ~19 tests NO CI job runs; five of them
fail PRE-EXISTINGLY, adjudicated on a pristine-main worktree 2026-08-08: the blob-URL download
reporting on /trend /curves /scurve /cei and the SRA single-bin histogram caption contrast — do
not chase as regressions). Run ruff as `python -m ruff` and always `ruff check .` — THE WHOLE
TREE (two ruffs live on PATH; `python -m` pins the pip-installed one). Model protocol: ADR-0240
stands — parity-, engine-, testimony- or CUI-relevant work stays on the strongest model. Use the
skills (`.claude/skills/`): `full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`,
`cui-guard`, `render-verify`, `session-close`. ⇢ WHAT'S DONE — do NOT re-open Monolith split:
phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–13 (`components.py` ADR-0350 ·
`driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 · `margin.py`
ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365 · `mission.py` ADR-0372 · `sra.py` ADR-0373 ·
`forecast.py` ADR-0374 · `portfolio.py` + two retroactive headers ADR-0375 · `analysis.py` +
the `_target_panel` descent ADR-0376 · `evm.py` + the `_metric_scorecard_table` descent
ADR-0377). The question-word censuses (what/how/where) are RETIRED. The intake manifest is
CURRENT at 433 files / 99 mismatches; the `.mpp` census pin is 28 (regenerate, never hand-edit).
The 2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369). The target-UID pair scope is CLOSED
end-to-end (ADR-0370 + ADR-0371). FX fixture verdicts are FINAL. ⇢ DO THIS FIRST — the queue

1. Phase 3 monolith split resumes at slice 14 — by the post-cut census (wc-truth; each family
still owes its OWN closure before cutting; membership NAMED because the prefix is a finder, not
the definition): **performance 326** (`_performance_body` 121 + `_performance_data` 75 +
`_perf_version_block` 47 + `_how_we_execute_header` 83) · **resources 306** (`_resources_body`
157 + `_resources_explainer` 20 + `_resource_loading_json` 51 + `_who_is_overloaded_header` 78)
· scurve 212 · path 194 (incl. `_what_drives_header` 80) · compare 166 (incl.
`_what_changed_header` 79) — EACH per the ADR-0365 recipe (closure before cut · span-scoped
probe · the six-mutation battery · the ADR-0372 oracle recipe with three normalizers; **the
498-label oracle with the TITLE-STRIPPED TP4 pool is the current widest reference — the
title-strip is load-bearing; the fingerprint is 88 ALL-stages / 69 loaded-stages; /openapi.json
is the 60th parameterless GET; keep the [grouped] labels**). groups (430 by prefix post-cut,
`_saved_*` included) stays OUTSIDE the phase-3 list while ADR-0343 feature work is queued
against it — ADR-0377's descent already serves it.
2. Then the standing queue: stored-SRA-fields MSPDI fixture (would light ADR-0373's three
oracle-dark members from a FILE) · driving-corridor fixture · the three page-lede-less pages
(/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
constraints · P80/P90 recurring-exception residual · the doc-drift sweep (docs/PARITY-REPORT.md
still says the reference .mpps are git-ignored and calls Project2.mpp "CUI intake" —
superseded by ADR-0151/0152; docs/FINAL-REPORT.md blanket "Exact match" beyond the three
evidence tiers; CLAUDE.md's phase-3 + single-E501 lines lag — mission.py, sra.py, forecast.py,
portfolio.py, analysis.py AND evm.py joined the E501 list) · ~150 MB RSS retained per loaded
9 MB file (no per-file unload) · Phase 6 docs. Operator only: re-convert FX-03/FX-04 (open the
authored .xml, VERIFY UID17=5d / UID131=1w before save — MS Project re-derives Duration from
stored dates and silently un-edits otherwise; the finish MUST move) then re-run Fuse and replace
the two oracles · one Acumen run on a crafted sub-day-negative-float schedule (closes the
Negative-Float O1 oracle gap — the AFT has NO formula for it) · license · branch-protection
contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME

1. A population fingerprint is only as good as its stated SCOPE (ADR-0377): the 88-count 4xx
histogram spans ALL FOUR stages; the three loaded stages measure **69**. A right number compared
at the wrong scope false-alarms every rebuild — carry the scope with the number.
2. `/openapi.json` is the 60th parameterless GET (ADR-0377) — a plain starlette `Route`, so an
`isinstance(APIRoute)` filter reads 59 and silently undercounts the class. Enumerate
`app.routes` by method + path, never by route class.
3. A normalizer that can fail silently is a FLAP FACTORY (ADR-0377): the whoami pid normalizer's
JSON parse died on a non-UTF-8 token placeholder under `except: pass` and four labels flapped.
Adjudicate every flap by PAYLOAD DIFF before touching the harness.
4. A descent's SECOND family can be probe-proven live (ADR-0377): the scorecard table moved
/groups labels in the same pre-flight that proved its /evm labels. If a mover+stayer
adjudication can be probe-proven, prove it — the closure names the referrer, the probe proves it
executes.
5. A page family's closure can run 3.6× its prefix (ADR-0376): panels carry no family prefix;
price the cut by referrer walk, never by the census number.
6. Never MEASURE a tree a battery is mutating (ADR-0376): a multiset diff once carried the
falsify battery's own marker as an "added" line — the never-mutate-a-running-suite trap has a
reverse form; md5-verify the tree against snapshots before any measurement you will quote.
7. The monkeypatch sweep's adjudication list GROWS as families move (ADR-0376):
`compute_activity_makeup` joined `non_summary` because analysis.py binds a name the ADR-0291
memo spies patch; the adjudication holds while the spied path stays in app.py — a
dashboard-family slice must repoint the spies to the module whose code CALLS them.
8. A census family can be a PHANTOM (ADR-0375): what/how/where were question-word header
groups; only the closure's referrer walk assigns membership.
9. The oracle's fixture POPULATION is a render condition (ADR-0375): five distinct TP4 Titles
→ five 1-version projects → ADR-0258 active population = latest only → multi-version pages
render placeholders and members false-dark. Adjudicate a 0-move by PAYLOAD before a
stronger-anchor round; title-strip the uploads into the untitled pool.
10. A header stranded by ruling-lag moves retroactively once its family's module exists
(ADR-0375); a header whose family module does NOT exist yet stays.
11. A render-CONDITIONAL member needs its condition IN the oracle (ADR-0374): read each
member's render condition off the RENDERED body BEFORE choosing anchors (slice 13 read the
BEI-FAIL clause / not-cost-loaded branch / non-empty `sv.worst` off the v5 body first).
12. The installer lockstep guard makes the rebuild a PREREQUISITE of the final suite run
(ADR-0374): sequence bump → build → docs → THEN the one suite whose counts you quote.
13. A crafted oracle payload aimed at COMPLETED tasks measures the fixture's history
(ADR-0373): target incomplete, finish-moving work on the live critical chain; believe a
0-move probe dark only after a SECOND, stronger anchor also moves 0 AND the payload diff says
the code rendered.
14. Patch the patcher with landed-count discipline (ADR-0373): an unanchored heredoc replace
on a harness script misses SILENTLY — use exact-match edits that fail loudly.
15. An anchor that collides is not span-scoped (ADR-0377): two slice-13 anchors matched twice
in app.py and were widened to multi-line exact spans. Assert count == 1 IN FILE and the anchor
line INSIDE the member's ast span, before every probe.
16. Constants carry `#:` doc-comment blocks the ast span does NOT see — extend move regions by
eye before any byte moves.
17. One session knob, two semantics (ADR-0370/0371): a "queued exposure class" is a CENSUS,
not a list — enumerate every caller of the old accessor in the same round.
18. An anchored computation can be truncation-INVARIANT — measure before pinning; the honest
record for an unpinnable-but-correct move is an ADR paragraph, never a vacuous test.
19. Measure the control on EVERY engine a sweep re-bases: one fixture gave three DIFFERENT lie
shapes.
20. A test whose setup can fail silently tests nothing: POST /target and assert the 303 in
every test whose name claims a target was set (GET is a 405).
21. A revert that changes nothing "passes": anchor splices uniquely and put the landed-count
assert INSIDE the mutation script, before the write.
22. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes; the dedupe
twin deserves its own assert.
23. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
24. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
25. An environment defect can masquerade as a product defect — a pristine-main worktree with
two `pip -e` flips is the cheap decisive adjudicator; an oracle label serving live telemetry
is weather (ADR-0372) — normalize VALUES (keep shape) BEFORE the first byte-identity claim,
adjudicate every unexpected mover by payload diff.
26. A binding-wrap spy undercounts — patch the module that CALLS or count at a construction
choke point.
27. A mutation is "caught" only when the failure summary NAMES the test (pytest exit ≠ failing
test — assert the test RAN).
28. NEVER mutate the tree while a suite runs (docs included); restore from scratchpad `cp`,
never `git checkout`; verify by ANCHOR-GREP.
29. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
zero — chain with `;` never `&&`.
30. Parity evidence is three-tiered — never report uniform "Acumen-equivalent"; the strongest
external-oracle tests SKIP without Java.
31. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals are
non-additive BY DESIGN.
32. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
33. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form — derive a
real ≥1 summary UID in tests.
34. A scratchpad-resident harness must HARDCODE the repo root — a walk-up from outside the
repo loops silently at `/`; any root-walk must fail loudly.

⇢ Measured-false / load-sensitive, do NOT re-chase Baseline-PRESENCE as the parity population
(F5) — 4 named ADR-0280 pin failures; the AFT's filter is `Baseline Duration GreaterThan 0`,
verbatim. The `/analysis` focus→tip family is load-sensitive. The five playwright-only
failures named above are pre-existing (pristine-main adjudicated) and CI-invisible.
`pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2
floor). TP4/goldens cannot render a driving corridor (ADR-0351), /evolution's counterfactual
(ADR-0352), or /integrity's artifact-cluster (ADR-0358) — byte-identity is the guard there.
The period-over-period metric families match UIDs across versions on the FOCUSED scope by
design — a documented residual (ADR-0371), parity-oracled, do not re-base without its own
adjudication. ADR-0373's three oracle-dark members (`_SRA_RISK_PROB_FIELD` /
`_SRA_RISK_IMPACT_FIELD` / `_file_stored_risks`) are route-covered in Python — the MSPDI
fixture is the named gap, not a regression. Standing rules (binding): Law 1 CUI · Law 2
fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING, VERIFY
EVERYTHING · full gate before every commit (statics foreground; `node --check` per file;
pytest to a file needs `python -u`) · handoff rotation + SESSION-LOG + LESSONS-LEARNED in the
same commit · wheel + nine installers ONCE per shipped-code change (bump BEFORE the suite;
REBUILD if code changes after; the rebuild PRECEDES the final suite run) · a number written
mid-session is not a measurement (wc decides). Full local suite ~20 min (~28 with playwright
installed) — run `python -u` in the BACKGROUND and read the tail; CI registers checks ~11 min
in; test jobs ~30 min.
