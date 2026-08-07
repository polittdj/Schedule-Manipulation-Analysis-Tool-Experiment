# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.176, highest ADR
0365, SCHEMA 2.11.0** — the 2026-08-07 triple session (full read-only audit · FX fixture
verdicts · intake guard re-greened) pushed DOCS + ONE TEST PIN only (no shipped code, no
version bump) on the draft PR for `claude/schedule-tool-audit-hhjbtp`; if it has since
squash-merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR
activity and drive CI to green before new work — docs-only, so the standard check set
(no installer legs). Fresh container: `pip install -e ".[dev]"` plus `pip install build`
(playwright optional, browser tests skip-gate). Run ruff as **`python -m ruff`** and always
**`ruff check .` — THE WHOLE TREE**. Model protocol: ADR-0240 stands — parity-, engine-,
testimony- or CUI-relevant work stays on the strongest model. Use the skills
(`.claude/skills/`): `full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`,
`cui-guard`, `render-verify`, `session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–7 (`components.py`
ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 ·
`margin.py` ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365 — `app.py` 20,192 → 16,581).
The intake manifest is CURRENT at 433 files / 99 mismatches and the `.mpp` census pin is 28
(six FX conversions included — regenerate, never hand-edit). The 2026-08-07 adversarial
READ-ONLY audit is COMPLETE (evidence package delivered to the operator, outside the repo):
UniversalProjectReader-rejects-.mpp REFUTED (28/28; the culprit was the host Java loader) ·
per-project dashboard recompute REFUTED at HEAD (warm / = 0 solves; upload precomputes) ·
non-additive row effects are CORRECT design (fresh joint solve; FX-05 {+0,−29}→0 is the
canonical exhibit) — do not "fix". FX fixture verdicts are FINAL: Fuse Days Late EXCLUDES
milestones and CLAMPS at zero; Missing Logic counts BOTH open ends of a dropped link;
Schedule Integrity's positive controls PASS (+10/+15 wd exact); the FX-06 baseline trap
PASSES (finding present, magnitude missing — queued below).

⇢ DO THIS FIRST — the audit's P0s, then the standing queue
1. **Sub-day effect display (audit F1/F7)**: `change_effects.py:117-123` `round()` makes a
   true 60-min (even exactly 240-min, banker's) effect render "no effect"
   (`web/integrity.py:280-286`); the duration label floor-divides. Keep exact minutes
   internally (ADD a minutes field, don't change the int-days field), render "<1 wd"
   signed, fix the label; fractional-day fixtures (60/235/240/241 min ±) — NO such test
   exists today. `prove-able-to-fail` applies.
2. **Parity milestone-population decision (audit F5)**: `_baselined` (dcma14.py:84-85)
   excludes ALL milestones; CLAUDE.md says "milestones kept"; Fuse's NASA-lib Missing
   Logic COUNTS TP4's milestone UID 26 (parity 0 vs Fuse 1; ordinary matches). DECIDE
   which Fuse metric parity mirrors, RE-PIN against the ADR-0280 Large-Test oracles
   BEFORE changing anything (a mistaken "fix" is worse than the drift), fix doc or code.
3. **/briefing memoisation (audit P1)**: 4 uncached CPM solves + duplicate audit EVERY
   request (build_briefing rebuilt by 4 callers; recommend() ignores precomputed audits).
   Memoise per epoch key + single-flight; byte-identical render diff is the guard.
4. **Integrity disclosure (audit F2/F4)**: target-unavailable banner instead of silent
   panel omission; list skipped-change identities; add old/new dates + day delta to the
   DECM-29I401a baseline finding (FX-06 renders no magnitude today).
Then phase 3 resumes at **mission 304** (stale census — RE-MEASURE the closure first;
expect sra ~700+ over its "264": the panel 235 + `_ssi_export_tables` 248 +
`_file_stored_risks` wait there). Then: how 290 · sra (re-measured) · what 257 · where 235
· portfolio 231 · evm 208 · forecast 204 — EACH slice per the ADR-0365 recipe (closure ·
pre-flight probe · verbatim cut + re-exports · LAYER_ORDER/VIEW_MODULES/EXTRACTED ·
three sweeps with positive control · byte-identity + falsified diff · five guard
mutations, named-failure rule). Then: stored-SRA-fields MSPDI fixture · driving-corridor
fixture · the three page-lede-less pages (/briefing, /path, /compare) · /groups
Activities (ADR-0343) · installers vs known-good constraints · P80/P90
recurring-exception residual · Phase 6 docs.
**Operator only:** re-convert FX-03/FX-04 (open the authored .xml, VERIFY UID17=5d /
UID131=1w before save — MS Project re-derives Duration from stored dates and silently
un-edits otherwise; F9; the finish MUST move) then re-run Fuse and replace the two
oracles · one Acumen run on a crafted sub-day-negative-float schedule (closes the
Negative-Float O1 oracle gap — the AFT has NO formula for it) · license ·
branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME
1. MS Project XML import DERIVES Duration from stored dates — a duration-only fixture
   gets silently un-edited on .mpp conversion; diff every round-trip before trusting its
   exports as an oracle.
2. An environment defect can masquerade as a product defect (the Java-loader story ran
   for weeks as "UniversalProjectReader is broken") — re-run the exact repro on a
   known-good runtime first.
3. A binding-wrap spy undercounts (from-imports bound before the wrap) — count at a
   construction choke point inside the callee (the CPMResult counter pattern).
4. A mutation is "caught" only when the failure summary NAMES the test — assert
   `1 failed`, never a bare non-zero exit (collection errors exit non-zero too).
5. NEVER mutate the tree while a full suite runs (docs included); mutate→restore rides
   ONE background orchestrator; restore from scratchpad `cp`, never `git checkout`;
   verify by ANCHOR-GREP after every restore.
6. An EMPTY sweep is evidence only with a positive-control self-test; the standing
   `app_mod.non_summary` memo patch is VERIFIED CORRECT and will keep tripping sweeps.
7. `grep -c` exits 1 on zero — chain with `;` never `&&`.
8. Parity evidence is three-tiered (runtime external oracle / transcription /
   engine-pinned) — never report it as uniform "Acumen-equivalent". And the strongest
   external-oracle parity tests SKIP without Java — check whether CI installs a JDK.
9. SMAT floors predecessor-less unstarted tasks at stored start (`_stored_date_bounds`)
   — an unmoored task does NOT slide to the data date; per-row counterfactuals are
   non-additive BY DESIGN (never sum rows; the joint solve is the truth).
10. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.

⇢ Measured-false / load-sensitive, do NOT re-chase
The `/analysis` focus→tip family is load-sensitive. `pydantic>=2` is NOT a safe floor
(2.6 is); `fastapi>=0.110` an AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens cannot
render a driving corridor (ADR-0351), /evolution's counterfactual (ADR-0352), or
/integrity's artifact-cluster (ADR-0358) — byte-identity is the guard there. The
stored-SRA-fields cluster is oracle-dark but unit-covered (ADR-0365) — the FIXTURE is
the queue item. Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0;
never weaken a test) · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate
before every commit (statics foreground; `node --check` per file; pytest to a file needs
`python -u`) · handoff rotation + SESSION-LOG + LESSONS-LEARNED in the same commit ·
wheel + nine installers ONCE per shipped-code change (bump BEFORE the suite; REBUILD if
code changes after) · a number written mid-session is not a measurement (wc decides).
Full local suite ~20 min — run `python -u` in the BACKGROUND and read the tail; CI
registers checks ~11 min in; test jobs ~30 min.
