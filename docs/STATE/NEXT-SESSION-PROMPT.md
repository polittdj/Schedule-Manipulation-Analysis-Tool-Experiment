# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue. As of
last close: **v1.0.218 · highest ADR 0430 · SCHEMA 2.11.0 · `main` = 9dda7ea** (the PR #605 squash).
**Nothing is in flight**: PR #605 merged, `claude/multi-schedule-comparative-analysis-vmh5ei` was
restarted from `origin/main`, tree clean, no scheduled triggers armed. **`git fetch origin` before you
branch, number an ADR, or commit — and RE-fetch before writing the docs**: the 08-20 session had its
ADR number taken TWICE by concurrent merges (0425 by #602, 0428 by #604) before landing on 0429/0430.

⇢ WHERE THE LAST TWO SESSIONS LEFT THE PRODUCT (do NOT re-open).
**ADR-0429 + ADR-0430 / v1.0.218 — the Starlight parity sweep**, an operator report widened to "fix
all mismatches", closed 52 of 54 ribbon cells. The ribbon's "Hard Constraints" had been showing the
DCMA-05 figure (parity-scoped to baselined incomplete) under a label that means the *Fuse ribbon*
metric (must/mandatory only, all statuses) — the NASA library carries BOTH under near-identical
names, so the DCMA card and the ribbon now legitimately differ, matching Acumen's own two products.
Also fixed: the pattern-less-calendar importer defect (112 holidays silently discarded) and ribbon
Negative Float (= STORED Total Slack < 0, Fuse-exact 6/6). Before that, **ADR-0424 / v1.0.214** fixed
Ask-the-AI comparing only the newest TWO of N loaded schedules. `engine/pair_series.py` and
`ai/pair_facts.py` are NEW modules that have never been through an audit dimension.

⇢ BLOCKED, OPERATOR-OWNED — the last 2 ribbon cells. Insufficient Detail V05/V06 (tool 0/4 vs Fuse
5) and TP2's 6-vs-7 are the SAME question. Six hypotheses were measured and refuted (calendar-day
scaling · week/7 · max-baseline-finish span · `Schedule.baseline_finish` span · fixed-480 · the
`.mpp`'s stored ProjectFinish read from the binaries with a compiled MPXJ probe). **Do not re-chase
them.** Unblock = the operator clicks the V05 "Insufficient Detail — 5" cell in the Fuse Starlight
workbook (or exports the ribbon to Excel) so the five counted activities are NAMED, then re-uploads.

⇢ WHAT THIS ARC IS. Operator directive 2026-08-16: "a complete deep dive audit of the entire
repository … create tests, both pass and fail … create solutions … test those in a sandbox to
verify prior to implementing any changes. Triple verify everything in independent ways … Test,
pass and fail tests required for all functionality of all pages … Skip nothing. Verify
everything." It is NOT finished. Fifteen ADRs' worth of defects are fixed (0409..0423).

⇢ RESUME ORDER — start at 1.

1. **INSTALLER VERSION VISIBILITY** — small, fully specified, and it just bit the operator. They
   re-ran the `install-tier2.ps1` already in their Downloads and it installed **v1.0.148** from a
   fully green run, because an installer embeds its wheel and never consults the repo. Two measured
   gaps: the banner is `Write-Host "Schedule Forensics installer — $TierLabel"` (tier, **no
   version**, so the telling number appears only after the tier/Python/venv steps), and
   `installer/README-DISTRIBUTABLE.md` has no "updating an install you already have" section. Print
   the embedded version in the banner, document the re-download-then-run path, and give it a guard
   that can FAIL (assert the rendered banner carries the wheel's version — a test that reads the
   template string only proves the template). Regenerates all nine installers; check `git status
   src/` before assuming a wheel/bump is owed (ADR-0148).
2. **PAGE MODULES A/B and DOCS/CONFIG/CI — still NEVER audited.** These are the last two whole
   dimensions with zero coverage. Everything else has had at least one pass.
3. **The AI figure-gates need an ADVERSARIAL pass.** The 08-16 arc opened the dimension and found
   two real defects (ADR-0421/0422) in the fact-ASSEMBLY path, but only READ the gate internals:
   `ai/qa.py::_figure_roles` (the value/identifier role split), `_classify_figures` (note
   `handled` is added on the first non-value occurrence, so a later occurrence in a `UID n` span
   is skipped), the `_MAX_GATED_FIGURES = 24` fail-closed bound, and `ai/derivation.py`'s Layer-B
   verifier. None has been attacked. Also unprobed: in **annotate** mode the gate scores against
   `model_evidence` (the FULL fact set) while the analyst is shown `relevant_facts` (a trimmed
   slice), so a figure sourced from a fact the analyst cannot see is not flagged. Fold in the
   reported-not-fixed finding here: **the Ask prompt is assembled from `f.text` and NEVER
   `f.rendered()`** (`ai/qa.py` ~910/931/942, all three modes), so a fact's citations reach neither
   the model nor the answer prose; ADR-0424 worked around it inside its own facts only, and the
   general fix changes what the figure gate sees.
4. **The 25-route adverse gap.** 19 are `POST /sra/*`. The fuzz that found ADR-0423 sent SINGLE
   hostile values per field — combinations, multi-field states and non-numeric classes (dates,
   enums, oversized bodies) are untested. `POST /sra/factor-table` is the one route the whole
   suite never touches at all.
5. Consider pinning the ribbon nf/id columns in `test_ribbon._FUSE` once the blocked leg settles.
6. Remaining REPORTED rows: CPM-01..04 · MF-02/03/04/06..10 · MC-02..08 · IMP-02..06 ·
   MAN-01..03 · REC-02 · JS-02..06 · TST-02/03.

⇢ THE CENSUS NUMBERS ARE SETTLED — do not re-derive them, but read what they mean.
137 routes (136 paths with methods + 1 `StaticFiles` mount; `/settings` carries two, so **137
(path, method) endpoints**). Coverage: **3 no-success · 25 no-adverse**, measured dynamically over
15,338 real requests. **Report it as a bracket: 25 <= gap <= 66.** The dynamic instrument sees
traffic, not assertions (lower bound); the older source-text instrument counted only
`status_code == 4xx` literals (upper bound). The working instruments are in the session
scratchpad pattern — re-derive rather than inherit if you need them again.

⇢ DO-NOT-FIX-BLIND LIST (unchanged). MF-05 — an empty-population PASS may be CORRECT Acumen
parity; "fixing" it without the reference export would BREAK parity. MC-01's parity leg is
UNVERIFIED by design (ADR-0414): no committed SSI export exposes a fired negative impact.
ADR-0417's leg needs a non-degenerate SRA fixture. ADR-0419's leg — whether an MSPDI "default
times" working day is 480 or the file's `<MinutesPerDay>` — needs an operator-supplied file; zero
of the 56 committed MSPDI documents carry the construct.
**NEW: `citations.reattach` drops `pinned`** (ADR-0392's population-frame flag). Real, and
measured **unreachable** today — `pinned` is set only in `version_facts.py` and reattach's three
call sites are narrative/briefing paths that never carry those facts. Deliberately NOT fixed: no
test can currently exercise it. If you make it reachable, fix it in the same change.

⇢ BEFORE ANYTHING: CLAUDE.md carries QC-1 (prove or refute before reporting: red before green,
mutation-prove the teeth, sandbox it, say UNVERIFIED rather than assert silently) and QC-2 (read
everything, assume nothing; inherited claims — including this file — are testimony, not evidence).
ADR-0393, pinned by tests/test_standing_rules.py.

⇢ THE AGENT POOL DIES. Fan-out hit credit exhaustion twice. The last six sessions ran entirely
solo and closed fifteen defects — that is the proven mode. Say plainly which dimensions got deep
treatment and which got a lighter pass.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
New last session (the parity sweep + this close): **an ADR token written as a RANGE does not
contain itself** — `ADR-0429/0430` does not match the guard's literal `ADR-0430`, so the handoff
would have gone red on a doc that reads correctly to a human; write each ADR out in full and
`grep -c` the token before committing (caught pre-commit, this session) · **a tree-wide renumber
sed rewrote UPSTREAM files' legitimate citations** when a concurrent merge took the number —
renumber by EXPLICIT FILE LIST only · **three blind oracles in one arc**: Fuse calibration
fixtures where two definitions coincide, a pinning test's no-overlap question, and an
all-non-working-week guard distinguishable only by IDENTITY (name/uid), never by the weekday
tuple · **the product often already knows its own defect** — ADR-0110's audit table had filed the
Hard-Constraints drift as "latent: no parity impact unless a schedule carries SNLT/FNLT", and
Starlight was that schedule · **a case-typo cannot prove a pin whose `_norm` lowercases** — drop a
TERM instead · **"it ran successfully" ≠ "it did what you wanted"**: a green installer run shipped
a 70-version-old build; verify the deployed ARTIFACT (`pip show`), never the deployment command ·
**a bounded sweep looks exhaustive and is not** — fuzzing the 25 "no adverse
coverage" routes found 6 of 12; the honest population was every field of every route · **a fix can
be wrong in the direction you did not test** — the first `isdigit()` fix closed every crash and
would have silently stopped resolving Arabic-Indic digits (650/788 code points); only the
guard-the-guard caught it, and under Law 2 that near-miss was the worse bug · **the product is
often its own oracle** — `/api/driving-path` vs `/api/ask`, and `_uid`'s own comment vs five sites
that ignored it · **a refuted hypothesis is a result** — `AI-DRIVE-01` was nothing like the row
predicted · **hook a CLASS method, not a name**, when import timing can defeat the patch; and a
wrapper sweep must rebind every module holding a reference, not just the defining one.
Standing: a count may be counting the SYMPTOM · an oracle that gives the same verdict in both
worlds is BLIND, not stale · a ledger row naming N surfaces may name N members of a CLASS · a test
that re-derives what the route SHOULD compute cannot fail · a red for the WRONG REASON is not a
red · a differential probe needs a control expected to MOVE · compute a call-site list, never
hand-maintain it · a suggested fix is a hypothesis · never measure a tree a battery is mutating
(use a detached worktree and ASSERT the imports resolve to it) · monkeypatch per CALL SITE · use
`python -m ruff` · **`ruff format` also formats python inside MARKDOWN — re-run the WHOLE gate
after the LAST file change, not the last code change** · `| tail` masks exit codes; redirect to a
file · fetch before numbering AND committing · wc decides.

⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` and
`pip install build` first. `pip install playwright` if you will touch browser tests — 94 tests
skip without it (missing PACKAGE, not missing browser). Full suite ~32 min (measured 31:36 at the
08-20 close: **4369 passed / 5 skipped**; those 5 skips are pre-existing). `pytest -m parity` ~9 min
(measured 538 s; re-run green after the 08-20 pin re-baseline, 72 passed).
Browser census `pytest $(python tools/browser_modules.py)` ~6–7 min. CI measured: browser ~6 min,
floor ~26 min, test (3.13) ~66 min, test (3.11) ~69 min — budget ~75 min for a full CI verdict,
and `cancel-in-progress: true` means never push while you need a run's signal. Installer build
needs an UNSHALLOW clone (`git fetch --unshallow origin`) or it refuses on ADR-0397's
graft-boundary guard; `python -m build --wheel --outdir dist/wheel && python
tools/installer/build_installers.py` takes ~2 min and rewrites all nine installers.

⇢ OPERATOR-OWNED, not agent work: V-1/V-2/V-3 gateway verification · DISC-01 · the CEI/HMI vendor
export blocking PO-04/05 · an SSI export showing a fired negative-impact (opportunity) register
entry (settles ADR-0414's parity leg) · an MS Project MSPDI file carrying a DayWorking=1 weekday
with no `<WorkingTimes>` (settles ADR-0419's leg) · branch cleanup. Note: the operator's desktop
launcher is a LOCAL "POLARIS" wrapper NOT in this repo — it refuses before invoking Python, so
ADR-0412's relocation cannot run on that path; the shipped "Schedule Forensics" shortcut must be
used.

⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
ADR-0240 model protocol (the LEAD re-verifies every finding before reporting) · full gate before
every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same commit · wheel + nine
installers ONCE per shipped-code change (ADR-0148) — check `git status src/` before assuming you
owe one.
Skills: full-gate, prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change,
session-close.
