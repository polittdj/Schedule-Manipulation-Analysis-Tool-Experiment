# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.173, highest ADR 0361,
SCHEMA 2.11.0** — ADR-0359 (fired risk REPLACES the affected duration — SSI's Sensitivity
export pinned it; distribution within 1-3 d of the weighted histogram), ADR-0360 (export
reuse 140 s → 0.1 s + PREPARING feedback + register seeding + /sra bars drill + full field
catalog), ADR-0361 (unrestricted AI mode + the known-pass/known-fail battery) pushed on the
draft PR for `claude/polaris-resume-handoff-div159`; if it has since squash-merged, restart
the branch: `git fetch --prune origin && git remote set-head origin -a &&
git checkout -B <branch> origin/main` (then `git branch --unset-upstream`). Fresh container:
`pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser tests
skip-gate). Run ruff as **`python -m ruff`** and always **`ruff check .` — THE WHOLE TREE**.
Model protocol: ADR-0240 stands — parity-, engine-, testimony- or CUI-relevant work stays on
the strongest model. Use the skills (`.claude/skills/`): `full-gate`, `prove-able-to-fail`,
`metric-parity`, `ui-change`, `cui-guard`, `render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–4
(`components.py` ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · **`integrity.py`
ADR-0358** — `app.py` 20,192 → 17,910). ADR-0353 SRA-LEGACY · ADR-0354 V3 (duration literals =
vendored MPXJ `Duration.convertUnits`; `%`/`e%` pass-through and the 364-day elapsed year are
MPXJ's OWN behaviour — never "fix" toward intuition; EVALUATOR_VERSION stays 2) · ADR-0355
(Codex hardenings; DATE literals still share the None shape — a FUTURE unit) · ADR-0356 (SSI
delta = STALE SETUP, engine exonerated σ 2.5%; `POST /sra/load-from-schedule`; the workbook's
Mean/StdDev cells are UNWEIGHTED — the occurrence-weighted histogram is the only oracle) ·
ADR-0357 (1440 boundary) · ADR-0359 (fired risk REPLACES the affected duration; risk-affected
tasks sample their 3-point when not fired — measured on SSI's own Sensitivity export, never
re-open toward additive) · ADR-0360 (export == screen via the run-reuse cache) · ADR-0361
(unrestricted AI is opt-in and ungated BY DESIGN; Law 1 unmoved) · P0 floors (ADR-0346: `pydantic>=2.6`, `fastapi>=0.110.2` — 0.110.0/1 are an
AIR-GAP VIOLATION; do not "restore" old floors) · P1 intake manifest + hardened CUI hook
(ADR-0347).

⇢ DO THIS FIRST — the standing queue
Battery phase 2 (same pair pattern, framework in tests/test_projects/test_pass_fail_battery.py):
cei · hmi · fei/bri · evm · schedule_quality · forecast · SRA-readiness. Then phase 3 next
family: **`margin` (379 by the stale ADR-0350 census — RE-MEASURE the closure first)**, then trend 348 · ssi 335 · mission 304 · how 290 · sra 264 · what 257 · where 235 ·
portfolio 231 · evm 208 · forecast 204. EACH slice: behaviour-seeded closure (prefix is a
finder, closure is the definition) · span-scoped pre-flight coverage probe BEFORE quoting any
render diff · verbatim cut + `X as X` re-exports · add the module to LAYER_ORDER +
VIEW_MODULES + EXTRACTED (contract test fails until it does) + widen `test_bar_drill` /
`test_presentation_fixes` · run ALL THREE standing sweeps (monkeypatch over every name the
module BINDS, imported or defined; `"app.py"`/`__file__`/getsource source-text readers;
attribute-READS of names app.py no longer binds) · per-definition byte-identity + non-blank
multiset + falsified render diff · the five guard mutations (restore from scratchpad `cp`,
NEVER `git checkout`; assert the ORIGINAL anchor ABSENT after every mutation). Then: a
driving-corridor fixture (would also light /evolution's counterfactual; /integrity's
`artifact-cluster` wants its own SNET-at-data-date fixture) · the three `page-lede`-less pages
(/briefing, /path, /compare) · `/groups` "Activities" counting summary rows (ADR-0343) · the
nine installers vs `-c constraints/known-good.txt` (62 lockstep tests, own unit) · the P80/P90
~20-cal-d recurring-calendar-exception residual on the Large_Test_File2 family (own unit +
oracle) · Phase 6 docs.
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
   proves it still fails loudly). Slice 4's three sweeps were all empty — and mutation 1
   (dropped re-export) is what made that trustworthy.
3. The render diff's meaning is decided PER FAMILY by the pre-flight probe: driving 0/60,
   evolution partial, integrity 6/79 both members. Never quote N/N without the probe.
4. NEVER mutate the tree while a full suite runs — settle the tree, THEN launch.
5. `grep -c` exits 1 on zero count — chain mutation-absence checks with `;` never `&&`.
6. A parity delta is a claim about INPUTS before it is a claim about engines — diff inputs
   first; the SSI workbook's Mean/StdDev cells are UNWEIGHTED.
7. GitHub outage + ci.yml's per-ref concurrency = new runs queue behind an un-cancellable
   zombie; wait it out server-side, then cancel + rerun (or an empty re-anchor commit).
8. bandit B608 false-positives on HTML f-strings containing "from" — house fix is
   `# nosec B608 (HTML, not SQL)` on the closing triple-quote line.

⇢ Measured-false / load-sensitive, do NOT re-chase
The `/analysis` focus→tip family is load-sensitive — do NOT chase. `pydantic>=2` is NOT a safe
floor (2.6 is). CC-01's "74 call sites" was never a call-site count (AST says 53; mechanism
unreachable on all committed schedules; ADR-0348 records it). The `/groups` Activities column
counting summary rows is RECORDED (ADR-0343), queued, not a new find. TP4/goldens cannot render
a driving corridor (ADR-0351) or /evolution's counterfactual (ADR-0352) or /integrity's
artifact-cluster (ADR-0358) — per-definition byte-identity is the guard there, not renders.

Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate before every commit (statics
foreground; `node --check` per file; pytest to a file needs `python -u`) · handoff rotation +
SESSION-LOG + LESSONS-LEARNED in the same commit · wheel + nine installers ONCE per
shipped-code change (bump version BEFORE the suite; REBUILD if code changes after;
`pyproject.toml` metadata ships in the wheel, so a bounds change is a shipped change) · never
`git checkout <file>` to undo a mutation — `cp` from a scratchpad copy · a number written
mid-session is not a measurement — re-read it before it lands in a handoff. Full local suite
~21 min; CI registers checks ~11 min in; `test (3.11)`/`(3.13)` ~30 min.
