# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.176, highest ADR
0365, SCHEMA 2.11.0** — ADR-0365 (phase 3 slice 7: the SSI run machinery into `web/ssi.py`;
the census flagship `_ssi_panel` measured OUT of the family — it is /sra page family; three
descents into `components.py`; 14/14 byte-identity; 96/96 routes) pushed on the draft PR for
`claude/polaris-resume-handoff-lw8osf`; if it has since squash-merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR
activity and drive CI to green before new work — installers changed, so the SEVEN-check set
applies (check · floor · linux · windows · browser · test 3.11 · test 3.13; the test jobs
run ~30 min). Fresh container: `pip install -e ".[dev]"` plus `pip install build`
(playwright optional, browser tests skip-gate). Run ruff as **`python -m ruff`** and always
**`ruff check .` — THE WHOLE TREE**. Model protocol: ADR-0240 stands — parity-, engine-,
testimony- or CUI-relevant work stays on the strongest model. Use the skills
(`.claude/skills/`): `full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`,
`cui-guard`, `render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–7
(`components.py` ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py`
ADR-0358 · `margin.py` ADR-0363 · `trend.py` ADR-0364 · **`ssi.py` ADR-0365** — `app.py`
20,192 → 16,581; the `_HB` trio, the `_focus_rows`/`_focus_panel` pair AND the three ssi
descents (`_REMAIN_DAYS_DP` · `_affected_avg_remaining_days` · `_ssi_matrix_counts`) live in
`components.py` now; `_HB_CONSUME_SEC` stays in app.py DELIBERATELY — dead constant, no
closure claims it; `web.trend` sorts AFTER `web.state` but `web.ssi` sorts BEFORE it — the
ssi re-export block is mid-list). The operator's `AlltheProjects` intake uploads are
inventoried (manifest 416 files, mismatches stay 99 — regenerate, never hand-edit).
ADR-0353 SRA-LEGACY · ADR-0354 V3 (duration literals = vendored MPXJ `Duration.convertUnits`;
`%`/`e%` pass-through and the 364-day elapsed year are MPXJ's OWN behaviour — never "fix"
toward intuition; EVALUATOR_VERSION stays 2) · ADR-0355 (Codex hardenings; DATE literals still
share the None shape — a FUTURE unit) · ADR-0356 (SSI delta = STALE SETUP, engine exonerated σ
2.5%; `POST /sra/load-from-schedule`; the workbook's Mean/StdDev cells are UNWEIGHTED — the
occurrence-weighted histogram is the only oracle) · ADR-0357 (1440 boundary) · ADR-0359 (fired
risk REPLACES the affected duration; risk-affected tasks sample their 3-point when not fired —
measured on SSI's own Sensitivity export, never re-open toward additive) · ADR-0360 (export ==
screen via the run-reuse cache) · ADR-0361 (unrestricted AI is opt-in and ungated BY DESIGN;
Law 1 unmoved) · ADR-0362 (battery phase 2 COMPLETE — do not re-add; `_dated`/`_wide` enriched
variants exist for fixture-floor metrics) · P0 floors (ADR-0346: `pydantic>=2.6`,
`fastapi>=0.110.2` — 0.110.0/1 are an AIR-GAP VIOLATION) · P1 intake manifest + hardened CUI
hook (ADR-0347).

⇢ DO THIS FIRST — the standing queue
Phase 3 monolith split, next family: `mission` (304 by the stale ADR-0350 census — RE-MEASURE
the closure first; slice 7 proved the census can misassign a family's BIGGEST member: the
panel left ssi entirely, and `sra`'s "264" is really ~700+ — the panel 235, `_ssi_export_tables`
248, `_file_stored_risks` and both risk-field constants are all measured /sra-family, waiting).
Then: how 290 · sra (re-measured) · what 257 · where 235 · portfolio 231 · evm 208 ·
forecast 204. EACH slice: behaviour-seeded closure (prefix is a finder, closure is the
definition — and it can PARTITION and it can EVICT the flagship) · span-scoped pre-flight
coverage probe BEFORE quoting any render diff (prove the oracle deterministic across
PROCESSES first; the launch token is `{hex16}.{wipe_gen}` — a hex-only normalizer flaps 48
labels; a member at 0 moved may be an ORACLE gap: ask what would EXECUTE it and widen — the
margin exports, `/trend?target=`, `/compare [target-set]`, the sra exports + templates, the
seeded `[ssi-api]` (SRAConfig.seed=12345 — byte-stable) and the crafted v4/v2 setup loads
are ALL proven-deterministic and stay in the harness) · verbatim cut + `X as X` re-exports ·
add the module to LAYER_ORDER + VIEW_MODULES + EXTRACTED + widen `test_bar_drill` /
`test_presentation_fixes` · ALL THREE standing sweeps WITH a positive-control self-test ·
per-definition byte-identity + non-blank multiset + falsified render diff · the five guard
mutations (restore from scratchpad `cp`, NEVER `git checkout`; assert the ORIGINAL anchor
ABSENT after every mutation; a mutation is "caught" only when the failure summary NAMES the
test — assert `1 failed`, never just a non-zero exit). Then: the stored-SRA-fields MSPDI
fixture (named oracle gap — lights the stored-fields cluster end-to-end AND the /sra slice's
members) · driving-corridor fixture · the three page-lede-less pages (/briefing, /path,
/compare) · /groups Activities counting summary rows (ADR-0343) · installers vs known-good
constraints · the P80/P90 recurring-calendar-exception residual (own unit) · Phase 6 docs.
Operator only: license · branch-protection contexts · proprietary reruns · OR-04 · whether
the July mpp/ oracle should re-export under replace semantics.

⇢ THE TRAPS PAID FOR — check BY NAME

1. The DISCRIMINATOR/IDENTITY-CASE trap (0353–0356): do the fixtures make the two readings
   equal by construction? RUN THE MUTATION BEFORE TRUSTING THE PIN; after mutating, assert
   the ORIGINAL anchor ABSENT (a suffixed replacement lies).
2. An EMPTY sweep is evidence only with a positive-control self-test. And a sweep HIT is a
   candidate, not a verdict: `test_manifest_projection_memo`'s `app_mod.non_summary` patch
   is VERIFIED CORRECT (ADR-0364, re-cleared ADR-0365 — it doubles as the live control) —
   the sweep will keep flagging it; clear it by the same verification, do not repoint it.
3. The render diff's meaning is decided PER FAMILY by the pre-flight probe: driving 0/60 ·
   evolution partial · integrity 6/79 · margin 13/13 · trend 5/5 · ssi 9 proven + 5 stated
   zeros (stored-fields cluster oracle-dark but unit-covered; `_REMAIN_DAYS_DP` 6→2dp
   value-invisible on whole-day fixtures). Never quote N/N without the probe; treat
   "0 moved" as a claim about the ORACLE first.
4. NEVER mutate the tree while a full suite runs — docs included (`test_state_docs` reads
   them mid-suite). And a mutate→restore harness must NEVER ride a foreground Bash call
   that can be timeout-backgrounded: the move RESTARTS the command. One background python
   orchestrator per harness; after any interruption, verify backups by ANCHOR-GREP.
5. `grep -c` exits 1 on zero — chain with `;` never `&&`. A non-zero pytest exit is NOT a
   failing test — collection errors exit non-zero too (slice 7's guessed-test-id false
   red); assert the summary names the test.
6. A parity delta is a claim about INPUTS before engines; the SSI workbook's Mean/StdDev
   cells are UNWEIGHTED.
7. GitHub outage + per-ref concurrency = runs queue behind an un-cancellable zombie; wait
   server-side, then cancel + rerun.
8. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
9. A synthetic fixture that "fails" a population-floor or span-derived metric is describing
   ITSELF — enrich the fixture (`_dated`/`_wide`), never weaken the metric.

⇢ Measured-false / load-sensitive, do NOT re-chase
The `/analysis` focus→tip family is load-sensitive. `pydantic>=2` is NOT a safe floor (2.6
is). CC-01's "74 call sites" was never a call-site count (ADR-0348). TP4/goldens cannot
render a driving corridor (ADR-0351), /evolution's counterfactual (ADR-0352), or
/integrity's artifact-cluster (ADR-0358) — byte-identity is the guard there. `_wmpd_label`'s
PAGE branch (mixed 480/1440 bases) is fixture-unreachable but its EXPORT path is
oracle-covered (ADR-0363). The stored-SRA-fields cluster (`_SRA_FACTOR/BC/WC_FIELD`,
`_file_stored_sra_inputs`) is oracle-dark under the golden pair but unit-covered
(ADR-0365) — the fixture, not the members, is the queue item.
Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every commit (statics
foreground; `node --check` per file; pytest to a file needs `python -u`) · handoff rotation +
SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine installers ONCE per
shipped-code change (bump BEFORE the suite; REBUILD if code changes after) · never
`git checkout <file>` to undo a mutation — `cp` from a scratchpad copy · a number written
mid-session is not a measurement (wc decides). Full local suite ~21 min — run `python -u` in
the BACKGROUND and read the tail; CI registers checks ~11 min in; test jobs ~30 min.
