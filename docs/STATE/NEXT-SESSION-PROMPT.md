# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected; it ALWAYS wins over this prompt). As of last close: **v1.0.178, highest ADR
0370, SCHEMA 2.11.0** — the 2026-08-08 (b) session root-caused and fixed the operator's
target-UID /integrity report (pair scope, ADR-0370: version-PAIR forensics run on
`scope_pair`/`cpm_pair_for`/`_pair_versions` — the filter applies, the Target UID anchors the
measurement and never truncates) and landed the same message's detail asks (was→now column ·
finding magnitudes · the "Logic changes — before → after" diagram · the "Change ledger" +
"Logic changes" export sheets on `/export/{fmt}/integrity?a=&b=`; shipped code changed, wheel +
nine installers rebuilt) on the draft PR for `claude/polaris-schedule-tool-resume-wm2ipt`; if
it has since squash-merged, restart the branch:
`git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
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
hand-edit). The 2026-08-07 audit's four P0s are CLOSED (ADR-0366..0369). The target-UID
/integrity defect is CLOSED (ADR-0370): the truncated-pair pipeline fabricated/zeroed/missed
changes; /integrity + its export + both ai/qa manipulation-facts sites now run on the pair
scope; the three GET-/target tests POST and assert their setup took; `ChangeEffect` carries
structured before→after fields; the effects tables carry "Was → is now"; the logic diagram and
the change-ledger export ship. FX fixture verdicts are FINAL.

⇢ DO THIS FIRST — the queue
1. The ADR-0370 exposure sweep: `/compare`, `/trend`'s findings roll-up (web/trend.py:162),
`/evolution`'s counterfactual (evolution.py:505) and app.py's other
detect_manipulation/path_counterfactual call sites still receive TARGET-TRUNCATED pairs — the
same class /integrity had; move them to `_pair_versions`/`cpm_pair_for` with the same
positive-control + named-failure discipline. (The reduce-FILTER pair-diff caveat is documented
in ADR-0370 — decide, don't drift.)
2. Phase 3 monolith split resumes at **mission 304** (stale census — RE-MEASURE the closure
first; expect sra ~700+ over its "264": the panel 235 + `_ssi_export_tables` 248 +
`_file_stored_risks` wait there). Then: how 290 · sra (re-measured) · what 257 · where 235 ·
portfolio 231 · evm 208 · forecast 204 — EACH slice per the ADR-0365 recipe.
3. Then the standing queue: stored-SRA-fields MSPDI fixture · driving-corridor fixture · the
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
1. **One session knob, two semantics** (ADR-0370): the Target UID is a population cut AND a
measurement anchor; a version-PAIR analysis must never inherit a population cut derived from
the logic being diffed. Enumerate every page where both meanings land.
2. **A test whose setup can fail silently tests nothing**: GET on the POST-only /target 405'd
silently and the "target set" pins rode the no-target path for their whole life — assert the
setup took (the 303 / the banner).
3. A revert that changes nothing "passes": anchor splices uniquely (`s.index(needle, after)`)
and put the landed-count assert INSIDE the mutation script, before the write (it refused a
no-op mutation this session).
4. ADR-0259 hash-dedupe vs memo tests: invalidation tests must change the bytes; the dedupe
twin deserves its own assert.
5. `round()` sends exact halves to EVEN (240 min → 0 wd); pin the half-day case by name.
6. MS Project XML import DERIVES Duration from stored dates — diff every round-trip.
7. An environment defect can masquerade as a product defect — **a pristine-main worktree with
two `pip -e` flips is the cheap decisive adjudicator** (used 2026-08-08 to clear five browser
failures as pre-existing).
8. A binding-wrap spy undercounts — patch the module that CALLS or count at a construction
choke point.
9. A mutation is "caught" only when the failure summary NAMES the test.
10. NEVER mutate the tree while a suite runs (docs included); restore from scratchpad `cp`,
never `git checkout`; verify by ANCHOR-GREP.
11. An EMPTY sweep is evidence only with a positive-control self-test; `grep -c` exits 1 on
zero — chain with `;` never `&&`.
12. Parity evidence is three-tiered — never report uniform "Acumen-equivalent"; the strongest
external-oracle tests SKIP without Java.
13. SMAT floors predecessor-less unstarted tasks at stored start; per-row counterfactuals are
non-additive BY DESIGN.
14. bandit B608 on HTML f-strings with "from" → house `# nosec B608 (HTML, not SQL)`.
15. `_parse_uid` maps 0 → "clear", so UID 0 can never be the focus via the form — derive a
real ≥1 summary UID in tests.

⇢ Measured-false / load-sensitive, do NOT re-chase
Baseline-PRESENCE as the parity population (F5) — 4 named ADR-0280 pin failures; the AFT's
filter is `Baseline Duration GreaterThan 0`, verbatim. The `/analysis` focus→tip family is
load-sensitive. The five playwright-only failures named above are pre-existing (pristine-main
adjudicated) and CI-invisible. `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` an
AIR-GAP VIOLATION (0.110.2 floor). TP4/goldens cannot render a driving corridor (ADR-0351),
/evolution's counterfactual (ADR-0352), or /integrity's artifact-cluster (ADR-0358) —
byte-identity is the guard there. Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—"
never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · full gate
before every commit (statics foreground; `node --check` per file; pytest to a file needs
`python -u`) · handoff rotation + SESSION-LOG + LESSONS-LEARNED in the same commit · wheel +
nine installers ONCE per shipped-code change (bump BEFORE the suite; REBUILD if code changes
after) · a number written mid-session is not a measurement (wc decides). Full local suite
~20 min (~28 with playwright installed) — run `python -u` in the BACKGROUND and read the tail;
CI registers checks ~11 min in; test jobs ~30 min.
