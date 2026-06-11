# Handoff — 2026-06-11 (full-audit + operator-features sitting)

**This session:** operator-requested full quality audit (3-agent fan-out; ~25 real findings fixed)
+ features: session-wide **target UID**, **light/dark theme**, **20-file batch cap** (PR #68).
**Next session:** operator feedback + the deferred audit items below; only the externally-gated
**M15 (.pbix)** remains blocked. Model/mode: Fable 5 (1M context).

> READ THIS FILE FIRST to resume. Durable state lives here + `docs/STATE/SESSION-LOG.md` (append-only
> per-session history) + `docs/adr/` (decisions) + `docs/PLAN/RTM.md` (requirements). Never rely on
> chat history — everything important is committed to git.

## Repo / branch / PR mechanics (how this build runs)
- Repo: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`. Everything ships to **`main`** via PRs.
- Work branch is always **`claude/clever-carson-uovtkk`**, recreated from `origin/main` for each new PR
  (the prior branch is deleted on squash-merge). To start fresh work:
  `git fetch origin main && git checkout -B claude/clever-carson-uovtkk origin/main`.
- Commit identity must be `Claude <noreply@anthropic.com>` (a Stop hook checks this — if it flags
  unverified commits run `git config user.email noreply@anthropic.com && git config user.name Claude`
  then `git rebase --exec "git commit --amend --no-edit --reset-author" origin/main`). **Force-push is
  blocked**; to publish a rebased branch whose remote tip moved, do an empty `git merge -s ours <old-tip>`
  so the push is a fast-forward (used this trick once already).
- After each push, open a **draft PR**. The operator merges PRs themselves (do NOT merge). Watch CI via
  the github MCP tools; CI **success is not delivered by webhook** — verify it explicitly. `send_later`
  is NOT available in this environment, so for the post-merge `main` run, use a short background
  `sleep` then re-check `actions_list`/`get_check_runs`. Unsubscribe once a PR is merged.
- CI: ruff + ruff format + mypy --strict + pytest (cov ≥70 overall, engine ≥85) + `pytest -m parity`
  (10/10, **non-negotiable**) + bandit + pip-audit, on push-to-main + every PR, Python 3.11 & 3.13.

## Build status
**DONE** — M1–M14, M16, M17 complete + a full audit remediation + a large run of operator-driven
enhancements. **M15 (.pbix enrichment) is the ONLY remaining milestone, BLOCKED** pending the operator
depositing `NSATDeploymentRevisionAlpha.pbix` (git-ignored CUI, R-12). Do not fabricate `.pbix` content.

## What shipped earlier sittings (PRs #58–#67)
- **#58** Full-audit remediation (ADR-0024): dropzone native form-submit; Windows `.mpp` temp-file fix;
  POST-only wipe/example; never-uncited citation; SPI(t); cached UID maps; one `_Analysis`/CPM per
  schedule; O(weeks) CPM date math (equivalence-swept); 2s Ollama probes; CI push-main-only + action
  bumps + pip cache; conftest golden fixtures; CSS/JS → `static/`; pyproject 1.0.0.
- **#59 / #60** Java discovery without admin: `SF_JAVA`→`JAVA_HOME`→PATH→**portable `tools/jre/` drop-in**
  (gitignored)→`%LOCALAPPDATA%\Programs`→machine roots, newest-version wins; actionable not-found error.
- **#61** Compare ordered by **data date** (not load order) + Net Finish Impact on the page.
- **#62** (ADR-0025) Trend across 10+ versions; Executive Briefing; **MS-Project-style Gantt** (timeline
  column, add/remove fields, milestones/summaries/critical/data-date). New `engine/trend.py`,
  `ai/briefing.py`.
- **#63** Docs/state refresh.
- **#64** Real-world `.mpp` tolerance (see lessons) + **schedule-level DCMA findings stay cited** (root-
  cause of the operator's "Internal Server Error") + resilient `/trend` `/compare` `/briefing` (skip &
  name unschedulable versions) + grid **per-column filters** + trace "show completed" toggle + waterfall
  driving Gantt + milestone diamonds.
- **#65** (ADR-0025 line) **Bow Wave / CEI** animated view (`engine/bow_wave.py`, `/cei`,
  `static/cei.js`): per-snapshot monthly finish bars (baselined/scheduled/finished), dashed
  data-date marker, "CEI – x.xx" callout, **Prev/Next + Auto-play movie**; CEI = finished ÷ what the
  prior snapshot planned for the month after its data date. Plus **Trend focus UID**
  (`/trend?target=<uid>`) and **de-overlapped chart labels** (strip common filename prefix, rotate −35°).
- **#67** Bow Wave / CEI hardening: capped month axis sheds the OLDEST months first (the newest
  status month + CEI period never fall off); CEI exactly 0.00 styles red/fail (falsy-zero bug).
  All of #58–#67 are **merged to `main`**.

## What shipped this sitting (PR #68) — full audit + operator features
**Features (operator-requested):**
- **Session-wide Target UID** (header form, `POST /target`, `SessionState.target_uid`): report
  page gains a Target-activity panel (dates/floats/%/flags/variance-vs-baseline) + auto-runs the
  driving trace; `/trend` focuses on it by default (explicit `?target=` — even blank — overrides);
  `/compare` adds the focus-movement panel; wipe clears it; redirects are local-only.
- **Light/dark theme**: all CSS on custom properties + `html[data-theme=light]`; `static/theme.js`
  applies the localStorage choice pre-paint; SVG charts route `var()` colors via `style` so they
  re-theme live. Toggle in the header.
- **Batch cap 10 → 20** (`MAX_FILES` in `importers/loader.py`); upload flash names dropped overflow.
**Audit fixes (3 parallel review agents; every fix has a regression test):**
- **§6 citation crash class closed for good**: empty DCMA populations are NA (never 0%→FAIL with
  no offenders); DCMA09 NA without a status date; ALL citation fallbacks (recommendations,
  briefing, narrative `_clean_bill`) terminate at the first task rows — a summary-only template
  renders a report instead of 500ing. BEI counts early completions (DCMA numerator = all finished
  by status).
- **Summary-UID targets**: `recommend(target_uid=summary)` and `/api/driving` no longer
  KeyError/500 — named note instead; `/api/driving` returns 422 (not 500) for logic-cycle files.
- **XER importer got MSPDI's tolerance classes** (shared in `importers/_common.py`): ALAP/dateless
  constraints → ASAP; dangling/self/duplicate TASKPRED dropped+counted; physical % clamped;
  **`complete_pct_type`-aware percent complete** (actual dates rule; CP_Drtn derives from
  remaining/target — phys-only read imported finished duration-type work as 0%); UTF-16 BOM.
- **MSPDI percent lags** (`LagFormat` 19/20): tenths of a **percent of the predecessor duration**,
  not tenths of a minute; links now build in a second pass. xsd:boolean "true"/"false" accepted.
- **NaN/Infinity numerics** are noise (absent), not crashes/EVM poison. Upload decode unified with
  file-path importers (`decode_xer_bytes`, utf-8-sig).
- **Manipulation**: erased actuals (date→None, progress un-statused) raise `MANIP_ACTUAL_ERASED`
  (HIGH). Schedule-quality metrics attach their offender lists (briefing cites real offenders).
- **CUI**: pydantic `hide_input_in_errors`; redaction covers `.json` names, UNC paths, quoted/
  whole-string spaced filenames, non-str log extras. `Save .json` round-trips milestones/
  summaries/WBS/durations/costs/calendar exactly.
- **Web polish**: trend focus chart never fabricates 0-points for versions missing the activity;
  the page's resolved focus always drives `/api/trend`; driving-path legend readable (tier
  backgrounds scoped to bars); unknown-schedule page is 404; Ollama probe timeout falsy-zero trap.
All under **ADR-0026**.

## Lessons learned (carry forward)
- **The curated goldens (Project2–Project5) are self-contained; real `.mpp` exports are NOT.** The MSPDI
  importer (the `.mpp`→MSPDI→model path) was stricter than both the CPM engine and the XER importer.
  Real files need tolerance for: **external/cross-project predecessor links** (drop), self/duplicate
  links (drop), **ALAP** and **dateless constraints** (→ASAP), **timezone-tagged dates** (→naive local),
  **out-of-range %-complete** (clamp 0–100), **negative scheduled/actual costs** (keep; clamp only the
  baseline/BAC to ≥0). All in `importers/mspdi.py` + `importers/_common.py` + `model/task.py`.
- **The §6 "every statement cited" gate is a real crash surface.** A schedule-level DCMA check (Critical
  Path Test, CPLI) that FAILS had no per-activity offenders → uncited finding → `UncitedStatementError`
  → every page for that schedule 500'd. Fixed by citing the tested/most-negative-float activities AND a
  fallback in `recommendations._dcma_findings` (cite the finish-controlling chain for any offender-less
  failed check). **Any new finding source must guarantee a citation.**
- **Multi-version views must degrade, never 500** on one bad file — see `_solvable_versions()` in
  `web/app.py` (skip + name unschedulable versions).
- **Parity is the guardrail for all of this:** every tolerance/normalization only fires on constructs the
  curated files lack, so goldens parse byte-identically (145 tasks, 176/178 links) and `pytest -m parity`
  stays 10/10. Run it after any importer/engine change.
- **Acumen "summary" count excludes the UID-0 project row** (briefing uses 18, not 19).

## Operator environment (CRITICAL — this caused most friction)
- **Windows, work laptop, NO admin rights.** Cannot run MSI installers (`winget` Java install exits 1602).
  → Java via the **portable JRE zip extracted into `…\tools\jre\`** (no admin). Steps are in
  `docs/USER-GUIDE.md` + `README.md`.
- Install folder: `C:\Users\dpolitte\Documents\Schedule-Manipulation-Analysis-Tool-Experiment`.
  PowerShell needs the `.\` prefix: `.\.venv\Scripts\Activate.ps1`. Editable install — after
  `git pull origin main` no reinstall is needed unless deps changed.
- The launcher prints `…serving the dashboard at http://127.0.0.1:<RANDOM-PORT>`; the dark
  **"▲ SCHEDULE FORENSICS"** page is the real tool. A separate **OLD program on `127.0.0.1:5000`**
  (white, "Schedule Manipulation Analysis **Tool**", JSON paste box) is a stale pre-greenfield app — NOT
  this codebase; tell the operator to ignore `:5000`.
- Operator workflow: merge each PR on GitHub, then `git pull origin main` + relaunch. They paste
  PowerShell logs/screenshots; red import notices name the file + reason (CUI-safe) — ask for that text.

## Green state
**562 passed, 3 skipped; parity 10/10; engine ≈98%; overall ≈98%; egress + air-gap green; bandit/pip-
audit clean (3.11 + 3.13).** Verify locally:
`ruff check . && ruff format --check . && python -m mypy && pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && pytest -m parity && bandit -q -r src`.

## Next steps / open items
1. **Respond to operator feedback** on real `.mpp`/`.xer` files — tolerance classes now live in
   `importers/_common.py` (shared by both importers); ALWAYS re-run `pytest -m parity`.
2. **Deferred audit items** (documented in ADR-0026, in rough priority order):
   - the **480-min day** is hardcoded in day-based thresholds/conversions (`metrics/_common.py`
     `FORTY_FOUR_DAYS_MIN`, `driving_slack` tier bands, `minutes_to_days` call sites) — only bites
     non-8h calendars (JSON imports today; MSPDI/XER calendar parsing is still deferred ADR-0008);
   - **CP_Units** percent from TASKRSRC quantities (currently duration-approximated);
   - AI backend: the settings-selected Ollama backend never drives the cached narrative/briefing
     (NullBackend always used), and `reattach` re-verifies citations but not figures — wire a
     per-request backend + a number-preservation check before enabling real generation;
   - trend `shortLabels` collapses identical filenames to "…" (label by data date as fallback).
3. **Tune the Bow Wave / CEI visuals** against the operator's real data vs the reference decks
   (`engine/bow_wave.py` axis window `_MONTHS_BEFORE/AFTER`; `static/cei.js` layout) if they don't match.
4. **M15 (.pbix)** stays blocked until the file is deposited in `00_REFERENCE_INTAKE/` (then
   `importers/pbix.py`: unzip → DataModel/Layout, local-only; fold into dashboard; ADR; close last RTM row).
5. Keep `docs/STATE/HANDOFF.md`, `SESSION-LOG.md`, and `docs/FINAL-REPORT.md` test counts current.

## Resume command for a NEW session
Paste this as the first message:
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first and continue exactly per its
> "Next steps / open items". Stay on branch `claude/clever-carson-uovtkk` (recreate from `origin/main`),
> keep `pytest -m parity` at 10/10, open draft PRs (don't merge — the operator does), and never let
> schedule data leave the machine. Model: Fable 5 (1M).
