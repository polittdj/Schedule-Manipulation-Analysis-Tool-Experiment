# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.177, highest ADR
0369, SCHEMA 2.11.0** — the 2026-08-08 session landed the 2026-08-07 audit's FOUR P0s
(sub-day effect fidelity ADR-0366 · parity milestone-population adjudicated ADR-0367 ·
/briefing memoisation ADR-0368 · integrity disclosure ADR-0369; shipped code changed, wheel +
nine installers rebuilt) on the draft PR for `claude/polaris-schedule-tool-resume-u67l5w`; if
it has since squash-merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
origin/main` (then `git branch --unset-upstream`). If still open, subscribe to its PR
activity and drive CI to green before new work — shipped code + installers, so expect the
SEVEN-check set (check · floor · linux · windows · browser · test 3.11 · test 3.13). Fresh
container: `pip install -e ".[dev]"` plus `pip install build` (playwright optional, browser
tests skip-gate). Run ruff as **`python -m ruff`** and always **`ruff check .` — THE WHOLE
TREE**. Model protocol: ADR-0240 stands — parity-, engine-, testimony- or CUI-relevant work
stays on the strongest model. Use the skills (`.claude/skills/`): `full-gate`,
`prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`,
`session-close`.

⇢ WHAT'S DONE — do NOT re-open
Monolith split: phases 1–2 (`state.py`, `chrome.py`) + phase 3 slices 1–7 (`components.py`
ADR-0350 · `driving.py` ADR-0351 · `evolution.py` ADR-0352 · `integrity.py` ADR-0358 ·
`margin.py` ADR-0363 · `trend.py` ADR-0364 · `ssi.py` ADR-0365 — `app.py` 20,192 → 16,581).
The intake manifest is CURRENT at 433 files / 99 mismatches and the `.mpp` census pin is 28
(six FX conversions included — regenerate, never hand-edit). The 2026-08-07 audit's four P0s
are CLOSED (ADR-0366..0369): change effects carry exact minutes and render signed "<1 wd"
(legacy day-rounding pinned incl. 240→0 banker's); the parity milestone population is
CONFIRMED CORRECT per the AFT verbatim (presence-of-baseline is MEASURED-FALSE — 4 named
ADR-0280 pin failures; TP4 "parity 0 vs Fuse 1" was a cross-metric comparison, ribbon
mirrors Missing Logic and matches) with the four misleading docstrings fixed; /briefing is
memoised per epoch (single-entry, byte-identical warm render, one DCMA audit per build);
/integrity discloses target-unavailable with a banner, lists skipped-revert identities, and
the DECM-29I401a finding states old→new dates + calendar-day deltas. FX fixture verdicts are
FINAL (Days Late excludes milestones + clamps at zero; Missing Logic counts both open ends;
FX-06 magnitude now renders).

⇢ DO THIS FIRST — the queue
1. Phase 3 monolith split resumes at **mission 304** (stale census — RE-MEASURE the closure
first; expect sra ~700+ over its "264": the panel 235 + `_ssi_export_tables` 248 +
`_file_stored_risks` wait there). Then: how 290 · sra (re-measured) · what 257 · where 235 ·
portfolio 231 · evm 208 · forecast 204 — EACH slice per the ADR-0365 recipe (closure ·
pre-flight probe · verbatim cut + re-exports · LAYER_ORDER/VIEW_MODULES/EXTRACTED · three
sweeps with positive control · byte-identity + falsified diff · five guard mutations,
named-failure rule).
2. Then the standing queue: stored-SRA-fields MSPDI fixture · driving-corridor fixture · the
three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
installers vs known-good constraints · P80/P90 recurring-exception residual · the audit's
doc-drift sweep (docs/PARITY-REPORT.md still says the reference .mpps are git-ignored and
calls Project2.mpp "CUI intake" — superseded by ADR-0151/0152; docs/FINAL-REPORT.md blanket
"Exact match" beyond the three evidence tiers; CLAUDE.md's phase-3 + single-E501 lines lag) ·
~150 MB RSS retained per loaded 9 MB file (no per-file unload) · 3 web tests calling GET
/target where only POST exists (silently not exercising focus) · Phase 6 docs. Operator only:
re-convert FX-03/FX-04 (open the authored .xml, VERIFY UID17=5d / UID131=1w before save — MS
Project re-derives Duration from stored dates and silently un-edits otherwise; the finish
MUST move) then re-run Fuse and replace the two oracles · one Acumen run on a crafted
sub-day-negative-float schedule (closes the Negative-Float O1 oracle gap — the AFT has NO
formula for it) · license · branch-protection contexts · proprietary reruns · OR-04 · July
mpp/ re-export decision.

⇢ THE TRAPS PAID FOR — check BY NAME
1. A revert that changes nothing "passes": a `s.index()` splice matched the FIRST occurrence
and RE-DECLARED the still-guarded function below the cut — anchor splices uniquely
(`s.index(needle, after)`) and grep the mutated property into evidence before trusting a
revert run.
2. ADR-0259 hash-dedupe vs memo tests: a byte-identical re-upload leaves the session
untouched, so an identity-keyed memo LEGITIMATELY survives — invalidation tests must change
the bytes, and the dedupe twin deserves its own assert.
3. `round()` sends exact halves to EVEN: a true half-day effect (240 min at 480/day) rounds
to 0 — pin the half-day case by name when pinning legacy rounding.
4. MS Project XML import DERIVES Duration from stored dates — a duration-only fixture gets
silently un-edited on .mpp conversion; diff every round-trip before trusting its exports.
5. An environment defect can masquerade as a product defect (the Java-loader story) — re-run
the exact repro on a known-good runtime first.
6. A binding-wrap spy undercounts (from-imports bound before the wrap) — patch the module
that CALLS (state, not app) or count at a construction choke point inside the callee.
7. A mutation is "caught" only when the failure summary NAMES the test — assert `1 failed`,
never a bare non-zero exit.
8. NEVER mutate the tree while a suite runs (docs included; the parity gate alone is
11.6 min); restore from scratchpad `cp`, never `git checkout`; verify by ANCHOR-GREP.
9. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
zero — chain with `;` never `&&`.
10. Parity evidence is three-tiered (runtime external oracle / transcription / engine-pinned)
— never report uniform "Acumen-equivalent"; the strongest external-oracle tests SKIP without
Java — check whether CI installs a JDK.
11. SMAT floors predecessor-less unstarted tasks at stored start (`_stored_date_bounds`);
per-row counterfactuals are non-additive BY DESIGN (never sum rows; the joint solve is the
truth).
12. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.

⇢ Measured-false / load-sensitive, do NOT re-chase
Baseline-PRESENCE as the parity population (F5) — 4 named ADR-0280 pin failures; the AFT's
filter is `Baseline Duration GreaterThan 0`, verbatim. The `/analysis` focus→tip family is
load-sensitive. `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` an AIR-GAP
VIOLATION (0.110.2 floor). TP4/goldens cannot render a driving corridor (ADR-0351),
/evolution's counterfactual (ADR-0352), or /integrity's artifact-cluster (ADR-0358) —
byte-identity is the guard there. The stored-SRA-fields cluster is oracle-dark but
unit-covered (ADR-0365) — the FIXTURE is the queue item. Standing rules (binding): Law 1 CUI
· Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING,
VERIFY EVERYTHING · full gate before every commit (statics foreground; `node --check` per
file; pytest to a file needs `python -u`) · handoff rotation + SESSION-LOG + LESSONS-LEARNED
in the same commit · wheel + nine installers ONCE per shipped-code change (bump BEFORE the
suite; REBUILD if code changes after) · a number written mid-session is not a measurement
(wc decides). Full local suite ~20 min — run `python -u` in the BACKGROUND and read the
tail; CI registers checks ~11 min in; test jobs ~30 min.
