# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.175, highest ADR
0364, SCHEMA 2.11.0** — ADR-0364 (phase 3 slice 6: the /trend family into `web/trend.py`;
the `_focus_rows`/`_focus_panel` pair descended into `components.py` with BOTH consumers
render-proven; 5/5 byte-identity; 80/80 routes) pushed on the draft PR for
`claude/polaris-resume-handoff-o4qcpx` (slice 5, ADR-0363/#550, already squash-merged); if it has since squash-merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). Fresh container:
`pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser tests
skip-gate). Run ruff as **`python -m ruff`** and always **`ruff check .` — THE WHOLE TREE**.
Model protocol: ADR-0240 stands — parity-, engine-, testimony- or CUI-relevant work stays on
the strongest model. Use the skills (`.claude/skills/`): `full-gate`, `prove-able-to-fail`,
`metric-parity`, `ui-change`, `cui-guard`, `render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–6
(`components.py` ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py`
ADR-0358 · `margin.py` ADR-0363 · **`trend.py` ADR-0364** — `app.py` 20,192 → 17,197; the
`_HB` trio AND the `_focus_rows`/`_focus_panel` pair live in `components.py` now, ready-made
for the /analysis and /compare slices; `_HB_CONSUME_SEC` stays in app.py DELIBERATELY —
dead constant, no closure claims it; `web.trend` sorts AFTER `web.state`, so its re-export
block closes the import section).
ADR-0353 SRA-LEGACY · ADR-0354 V3 (duration literals = vendored MPXJ `Duration.convertUnits`;
`%`/`e%` pass-through and the 364-day elapsed year are MPXJ's OWN behaviour — never "fix"
toward intuition; EVALUATOR_VERSION stays 2) · ADR-0355 (Codex hardenings; DATE literals still
share the None shape — a FUTURE unit) · ADR-0356 (SSI delta = STALE SETUP, engine exonerated σ
2.5%; `POST /sra/load-from-schedule`; the workbook's Mean/StdDev cells are UNWEIGHTED — the
occurrence-weighted histogram is the only oracle) · ADR-0357 (1440 boundary) · ADR-0359 (fired
risk REPLACES the affected duration; risk-affected tasks sample their 3-point when not fired —
measured on SSI's own Sensitivity export, never re-open toward additive) · ADR-0360 (export ==
screen via the run-reuse cache) · ADR-0361 (unrestricted AI is opt-in and ungated BY DESIGN;
Law 1 unmoved) · ADR-0362 (battery phase 2 COMPLETE: cei/hmi/fei-bri/evm/schedule_quality/
forecast/SRA-readiness all paired — do not re-add; `_dated`/`_wide` enriched variants exist
for fixture-floor metrics) · P0 floors (ADR-0346: `pydantic>=2.6`, `fastapi>=0.110.2` —
0.110.0/1 are an AIR-GAP VIOLATION; do not "restore" old floors) · P1 intake manifest +
hardened CUI hook (ADR-0347).

⇢ DO THIS FIRST — the standing queue
Phase 3 monolith split, next family: **`ssi` (335 by the stale ADR-0350 census — RE-MEASURE
the closure first; both re-measured slices partitioned THREE ways: margin 417+21, trend
424+55+shared)**, then mission 304 · how 290 · sra 264 · what 257 · where 235 · portfolio
231 · evm 208 · forecast 204. EACH slice: behaviour-seeded closure (prefix is a finder, closure is the definition — and
it can PARTITION: margin's closure held a descent trio and untouchable SRA names) ·
span-scoped pre-flight coverage probe BEFORE quoting any render diff (a member at 0 moved may
be an ORACLE gap: ask what would EXECUTE it — an export, a POST-lit branch, a query param —
and widen the oracle; the margin exports proved deterministic and stay in the harness) ·
verbatim cut + `X as X` re-exports · add the module to LAYER_ORDER + VIEW_MODULES + EXTRACTED
(contract test fails until it does) + widen `test_bar_drill` / `test_presentation_fixes` · run
ALL THREE standing sweeps (monkeypatch over every name the module BINDS, imported or defined;
`"app.py"`/`__file__`/getsource source-text readers; attribute-READS of names app.py no longer
binds) WITH a positive-control self-test · per-definition byte-identity + non-blank multiset +
falsified render diff · the five guard mutations (restore from scratchpad `cp`, NEVER `git
checkout`; assert the ORIGINAL anchor ABSENT after every mutation). Then: a driving-corridor
fixture (would also light /evolution's counterfactual; /integrity's `artifact-cluster` wants
its own SNET-at-data-date fixture) · the three `page-lede`-less pages (/briefing, /path,
/compare) · `/groups` "Activities" counting summary rows (ADR-0343) · the nine installers vs
`-c constraints/known-good.txt` (62 lockstep tests, own unit) · the P80/P90 ~20-cal-d
recurring-calendar-exception residual on the Large_Test_File2 family (own unit + oracle) ·
Phase 6 docs.
**Operator only:** license · branch-protection contexts · intake re-upload (optionally the
2026-08-06 artifacts as a second committed parity oracle) · proprietary reruns · OR-04 ·
whether R2 belongs in both SSI and tool runs.

⇢ THE TRAPS PAID FOR — check BY NAME before trusting any new pin
1. THE DISCRIMINATOR/IDENTITY-CASE TRAP fired four times on 2026-08-06 (identity fixtures
   0353 · identity calendar 0354 · identity population 0355 · self-agreeing oracle 0356).
   Always ask: do the fixtures make the two readings equal by construction? RUN THE MUTATION
   BEFORE TRUSTING THE PIN, and after mutating assert the ORIGINAL anchor is ABSENT — a
   suffixed replacement passes a count check while lying. Slice 4 proved the fix: the
   assert-original-absent rule COMPILED INTO the probe harness caught its own first suffixed
   mutation (`page-takeawayQ`).
2. An EMPTY sweep is evidence only if the harness has found things before (or a mutation
   proves it still fails loudly). Slice 5 compiled this in: the sweep harness SELF-TESTS by
   first locating the four known drvmod/evomod patch sites before its empty result counts.
3. The render diff's meaning is decided PER FAMILY by the pre-flight probe: driving 0/60,
   evolution partial, integrity 6/79, margin 13/13 (first full cover — after widening the
   oracle with the band POST + the instantiated margin exports). Never quote N/N without the
   probe, and treat "0 moved" as a claim about the ORACLE until the widening question is asked.
4. NEVER mutate the tree while a full suite runs — settle the tree FIRST, docs included
   (`test_state_docs` reads HANDOFF/SESSION-LOG mid-suite; slice 5 stopped and relaunched the
   suite for exactly this). And a mutate→restore harness must NEVER ride a foreground Bash
   call that can be timeout-backgrounded: the move RESTARTS the command — slice 6's
   falsification briefly ran twice concurrently. One short call per
   mutate→snapshot→restore cycle; after any interruption, verify backups by ANCHOR-GREP.
5. `grep -c` exits 1 on zero count — chain mutation-absence checks with `;` never `&&`.
6. A parity delta is a claim about INPUTS before it is a claim about engines — diff inputs
   first; the SSI workbook's Mean/StdDev cells are UNWEIGHTED.
7. GitHub outage + ci.yml's per-ref concurrency = new runs queue behind an un-cancellable
   zombie; wait it out server-side, then cancel + rerun (or an empty re-anchor commit).
8. bandit B608 false-positives on HTML f-strings containing "from" — house fix is
   `# nosec B608 (HTML, not SQL)` on the closing triple-quote line.
9. A synthetic fixture that "fails" a metric may be describing ITSELF: population-floor
   metrics (Missing Logic's 2/N structural open ends) and denominator-derived metrics
   (Insufficient Detail ÷ STORED-finish span) need an enriched fixture (`_dated`/`_wide`,
   ADR-0362) — enrich the fixture, never weaken the metric, never file the engine bug first.

⇢ Measured-false / load-sensitive, do NOT re-chase
The `/analysis` focus→tip family is load-sensitive — do NOT chase. `pydantic>=2` is NOT a safe
floor (2.6 is). CC-01's "74 call sites" was never a call-site count (AST says 53; mechanism
unreachable on all committed schedules; ADR-0348 records it). The `/groups` Activities column
counting summary rows is RECORDED (ADR-0343), queued, not a new find. TP4/goldens cannot render
a driving corridor (ADR-0351) or /evolution's counterfactual (ADR-0352) or /integrity's
artifact-cluster (ADR-0358) — per-definition byte-identity is the guard there, not renders.
`_wmpd_label`'s PAGE branch (mixed 480/1440 bases) is likewise fixture-unreachable — but its
EXPORT path is oracle-covered since ADR-0363; do not re-chase the page branch.
`test_manifest_projection_memo`'s `app_mod.non_summary` patch is VERIFIED CORRECT
(ADR-0364): the spied /api/dashboard projection never crosses a moved member — the sweep
will keep flagging it; clear it by the same verification, do not repoint it.

Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every commit (statics
foreground; `node --check` per file; pytest to a file needs `python -u`) · handoff rotation +
SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine installers ONCE per
shipped-code change (bump version BEFORE the suite; REBUILD if code changes after;
`pyproject.toml` metadata ships in the wheel, so a bounds change is a shipped change) · never
`git checkout <file>` to undo a mutation — `cp` from a scratchpad copy · a number written
mid-session is not a measurement — re-read it before it lands in a handoff (slice 5's 17,688 was pre-`ruff --fix`;
slice 6's 482 was pre-I001-fix — wc decides). Full local suite ~21 min — exceeds a 10-min foreground
timeout, so run it `python -u` in the BACKGROUND and read the tail; CI registers checks ~11
min in; `test (3.11)`/`(3.13)` ~30 min.
