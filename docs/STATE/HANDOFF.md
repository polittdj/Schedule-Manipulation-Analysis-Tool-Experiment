# Handoff — 2026-06-12 (PRs #81–#91 MERGED; **M18 IN FLIGHT**; PR #92 OPEN — AI at full power pt 1)

**This sitting:** **#90 merged** (the eday fix), then **#91 merged** (M18 items 1–3,
ADR-0034: the **stored-date CPM mandate** — unstarted MANUAL tasks pin at their stored
start, unstarted logic-unbound auto tasks floor there, `CPMResult.date_driven` + the
cited **"N dates are not supported by logic"** finding, `Task.is_manual` model v2.1.0;
the **Path-Analysis stored-date display** — completed work at ACTUAL dates, per-row
`date_driven`, trace-coverage status line; the **full-width layout**). Post-merge main
CI green. Then **PR #92 (ADR-0035) — AI at full power, part 1**: `AIConfig.qa_mode`
(**interpretive default** — the model may analyze/derive grounded in the cited facts;
strict = the old wholesale figure-discard, still selectable), the **ask panel on EVERY
page** via the page shell (`_ask_panel_html` + `static/ask.js`, scope select = workbook
or any version; the /path-local panel removed, same ids/endpoint), **workbook-wide
facts** (`build_workbook_fact_sheet` reusing the briefing's cited statements +
latest-pair manipulation signals + latest forecasts; `POST /api/ask`), and the standing
**"AI can err — verify against citations"** disclaimer. The narrative/briefing
`reattach` gates and loopback-only egress are UNCHANGED. **VERIFICATION OWED: the
Duration Bomb .mpp is NOT in this container** — on operator re-deposit, confirm computed
finish **2027-03-04**, completed tasks visible on /path, and the logic finding citing
the template tasks. Model/mode: Fable 5 (1M context).

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
**COMPLETE — all milestones M1–M17 delivered** (M15 closed by PR #74/ADR-0030 after the operator
deposited the `.pbix`). The deck stays git-ignored CUI in `00_REFERENCE_INTAKE/pbix/` on the machine
that received it; it does NOT travel between cloud sessions (R-12) — if a future session needs it
again, ask the operator to re-deposit. Its DAX is XPress9-compressed: the reconstructed formulas are
in the metric dictionary; EPI / RatioMeasure / Start-and-Finish-Ratio await a DAX export.

## What shipped earlier sittings (PRs #58–#68)
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
- **#68** (ADR-0026) Full audit (3-agent fan-out; ~25 findings fixed: §6 citation crash class
  closed via NA-on-empty-populations + terminal citation anchors; BEI early completions;
  XER got MSPDI's tolerance classes + `complete_pct_type`-aware percents + UTF-16; MSPDI
  percent lags; NaN/Infinity = noise; `MANIP_ACTUAL_ERASED`; CUI redaction + JSON round-trip
  fidelity) + operator features: **session-wide Target UID** (`POST /target`, report panel +
  auto-trace, trend default focus, compare movement), **light/dark theme** (`theme.js`,
  CSS variables, live-re-theming SVG), **batch cap 10 → 20**.
  All of #58–#68 are **merged to `main`**.

## What shipped this session — PRs #69–#80 (all merged)

**PR #69 (ADR-0027) — the four ADR-0026 deferred items, MERGED:**
1. **Calendar-true day math**: every day↔minute boundary derives from
   `calendar.working_minutes_per_day` — the DCMA "44 working days" tripwire is now
   `forty_four_days_min(schedule)` (`metrics/_common.py`; DCMA06/DCMA08/Insufficient Detail),
   DCMA12 injects `100 working days` on the schedule's calendar, driving-slack tier bands +
   `driving_slack_days` convert per-calendar, and `float_analysis` day rendering does too.
2. **XER `CP_Units`** percent complete from TASKRSRC quantities (`_units_percent_by_task`):
   actual (`act_reg_qty`+`act_ot_qty`) ÷ at-completion (actual+`remain_qty`), summed per task;
   actual dates still rule; quantity-less / zero-at-completion falls back to the duration share.
3. **AI figure gate + per-request backend**: `reattach` keeps a rephrase only if it preserves
   the source's numeric figures exactly (`preserves_figures`, multiset; fail-closed to the
   verbatim sentence) — with that in place, the settings-selected backend now actually drives
   the prose: the report narrative is polished once per (schedule, backend, model)
   (`SessionState.polished`, `_polished_narrative`), the briefing builds with the routed
   backend, generation failure degrades deterministic (never a 500), and routing is cached 15s
   (`SessionState.backend_cache`, reset on settings save) so a down Ollama can't slow renders.
4. **Trend labels**: identical filenames no longer collapse to "…" — a label that empties
   after the common-prefix strip falls back to the version's data date (`trend.js shortLabels`).

**PR #70 (ADR-0028) — MSPDI/XER project-calendar parsing, MERGED:**
- Importers fill `Schedule.calendar` from the source's project calendar: **work weekdays**
  (source day 1=Sun..7=Sat → `weekday_from_source`), **per-day minutes** (span sums; differing
  days use the **dominant/modal** total — single-block model approximation), **holidays**
  (full non-working exceptions; working exceptions skipped + logged; weekend holidays dropped;
  ranges capped at 366 days).
- **MSPDI**: `Project/CalendarUID` resolved with a cycle-safe **base-calendar chain** (derived
  calendars inherit the base week; exceptions collect across the chain); legacy `DayType=0`
  and modern `<Exceptions>` both read; `DayWorking` with no times → 480. `.mpp` via MPXJ gets
  this for free.
- **XER**: `PROJECT.clndr_id` → CALENDAR row (fallback `default_flag=Y`); packed `clndr_data`
  read with anchored patterns (`(0||<1-7>()` day nodes, `s|HH:MM|f|HH:MM` spans,
  `(0||N(d|<serial>)` exceptions, Excel serial epoch 1899-12-30); grid-less rows walk
  `base_clndr_id`, then `day_hr_cnt`, then default.
- **Fail-soft**: any calendar surprise logs + degrades to the 8h/Mon-Fri default — never sinks
  the file. `Save .json` round-trips **holidays** now. Goldens' calendar IS the textbook
  standard (verified + pinned) → parity untouched.

**PR #71 (ADR-0029) — XER per-task cost roll-up:**
- `xer._costs_by_task` sums TASKRSRC assignment costs + PROJCOST expenses per task:
  `actual_cost` = act_reg+act_ot+expense act (ACWP basis); `cost` = actual + remaining
  (at-completion total); `budgeted_cost` = Σ target_cost **clamped ≥ 0** (the BAC/EV rule;
  credits in actual/remaining preserved). **Absence is honest**: fields set only when the
  file carried a value — cost-less `.xer` identical (EVM stays NA); the curated fixture has
  no cost columns (pinned). Cost-loaded `.xer` now drives real SPI/CPI/TCPI.

**PR #72 (merged) — self-review fix:** **recurring MSPDI exceptions** (Occurrences ≠ day
span) are skipped + logged instead of contiguously expanding into weeks of false holidays
(one weekly "Fridays off" pattern erased ~36 working days).

**PR #73 (merged) — calendar visibility:** the report page shows a **Working calendar** panel
(name, h/day + exact minutes, work week, holidays w/ 10-date preview) and `/api/analysis`
carries a `calendar` object — the imported time basis is verifiable on the page.

**PR #74 (merged, ADR-0030) — M15, the last milestone:** deck read locally (Layout JSON;
DataModel XPress9-compressed → reconstructed formulas, ambiguous measures deferred pending DAX
export); adopted **float bands** (0/<5/<10d, calendar-aware, offenders cited; 0-day band ==
Acumen Critical 41/37), **completion performance** (ahead/on/behind, avg days, duration
ratios, **MEI**, staleness), and the **three-method `/forecast`** (CPM / completion-rate /
IEAC(t)) with the per-version drift table; 22 metric-dictionary entries; RTM A6 +
FINAL-REPORT closed.

**PR #75 (merged) — exact-ratio IEAC(t):** the forecast divided by the 2-decimal display
SPI(t) (golden P5 read 9 days early); the math now uses the exact ES/AT ratio (display still
rounds). Plus a /forecast falsy-zero display trap (#67 class).

**PR #76 (merged) — user-docs catch-up:** USER-GUIDE + README now cover the imported
calendar, the three new report panels, and the /forecast page (everything #70–#75 shipped).

**PR #77 (merged) — the unique desktop icon + favicon:** `packaging/make_icon.py` redesigned
(stdlib, 4x supersampled, deterministic): dark tile + white ▲ + Gantt waterfall + gold
data-date line, 5-entry 256..16 PNG-in-ICO; same bytes = `/static/favicon.ico` + Linux PNG;
sync/determinism pinned by tests. Installer: `packaging\windows\Install-Desktop-Shortcut.ps1`.

**PR #78 (merged) — the icon opened a dead port:** `pythonw.exe` starts with
stdout/stderr = None; uvicorn's logging setup touched them and the server died right after
the browser-open timer. `launcher._ensure_streams()` rebinds missing streams to devnull
(never a log file — request paths carry schedule names). Regression drives the real
uvicorn.Config with None streams.

**PR #79 (merged, ADR-0031) — Path Analysis + ask-the-AI:** `/path` over the SSI-parity
driving-slack engine: target UID (session target pre-fills), user secondary/tertiary
day-bands, data grid LEFT (add/remove MS-Project fields; tier/substring filters;
hide-100%-complete), **scalable** Gantt RIGHT (px/day zoom, month ticks, gold data-date
line); `/api/driving` extended with grid fields + ISO dates. **Ask the AI** (`ai/qa.py`,
`POST /api/ask/{schedule}`): engine-computed cited fact sheet; Null backend = matching
facts verbatim; a model answer containing any figure the engine never computed is
discarded wholesale.

**PR #80 (merged, ADR-0032) — real-file fixes:**
- **Driving tiers classify on whole working days** (slack floored on the schedule's
  calendar): real stored dates carry time-of-day raggedness, so chains SSI shows at
  "0 days" carried 30–450 minutes here and fell out of DRIVING (operator measured **4 vs
  SSI's ~66**). Goldens are exact day multiples → parity untouched; boundaries pinned.
- **The server killed itself mid-load**: async `/upload` parsed on the event loop, starving
  heartbeats past the 10s grace → the auto-shutdown watchdog fired. Upload now runs in the
  threadpool; an in-flight request counter holds the watchdog; completions refresh the beat.

**PR #81 (merged) — state-docs recovery:** the prior session's final HANDOFF consolidation
was stranded on the work branch after #80's merge snapshot; restored as base + updated for
the merged state (this file's lineage).

**PR #82 (merged) — the synthetic verification battery (`docs/TEST-PROJECTS.md`):**
`tools/make_test_projects.py` deterministically generates 8 fictional MSPDI files into
`tests/fixtures/test_projects/` with an **MS-Project-faithful block calendar**: **TP1**
progressed + ragged actual times (driving tiers to UID 43 = 13/1/2/2; completed UIDs carry
210/210/120 MINUTES that floor to DRIVING — the #80 4-vs-66 class as a fixture); **TP2**
4×10 Mon–Thu 600-min calendar + 4 holidays (float bands 7/12/13; the exactly-44-day task
stays OUT of High Duration — calendar-true boundary); **TP3** hand-seeded DCMA counts
(Logic 4 / Leads 2 / Lags 3 / FS 76% / Hard 2 / Neg-float 3 / High-dur 2 / Invalid 4 /
BEI 0.62); **TP4 v1–v5** monthly series whose v4 erases UID 19's actual start AND quietly
slips its baseline (both MANIP signals fire, pinned; honest v2→v3 fires neither). Plus the
MSP **VBA module** (SF_VerifyImport / SF_SaveAsMpp / SF_ImportFolderToMpp) and per-file
SSI/Fuse recipes with pinned expected values. The operator's MSP import caught a real
generator bug (top-down summary rollup gave UID 0 a year-0001 baseline) — fixed
deepest-first + a battery-wide date/duration sanity guard.

## Lessons learned (carry forward)
- **Real stored dates are ragged to the minute; SSI thinks in whole days.** Any tier/driving
  classification must compare on the floored-day axis or real files undercount the driving
  path drastically (4 vs 66). And **never run imports on the event loop** — heartbeats starve
  and the auto-shutdown watchdog kills the server mid-load (in-flight requests now hold it).
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

- **Re-create the branch from origin/main after EVERY merge** before new work — building on
  the stale pre-squash tip made PR #80 initially dirty (it dragged the merged #79 commits);
  repair = cherry-pick onto fresh main + `-s ours` absorb of the old tip (no force-push).
- **The Stop hook flags GitHub's own squash commits** (committer noreply@github.com) when the
  local branch sits on main with nothing pushed: resolve with
  `git reset --hard origin/claude/clever-carson-uovtkk` — never rewrite merged history.
- **The GitHub MCP token can expire mid-session** ("requires re-authorization"): PR
  state can still be inferred via `git ls-remote origin main` (tip changes on merge);
  creating PRs/reading CI needs the operator to re-authorize the connector.
- **Heavy work must never run on the event loop** and **classification must use SSI's
  whole-day axis** (see PR #80 above) — both bit on the operator's first real-file run.

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
**727 passed, 3 skipped; parity 10/10; engine ≈97%; overall ≈97%; egress + air-gap green; bandit/pip-
audit clean (3.11 + 3.13).** Verify locally:
`ruff check . && ruff format --check . && python -m mypy && pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && pytest -m parity && bandit -q -r src`.
(In a fresh remote container run `pip install -e '.[dev]'` into `.venv` first — the preinstalled
venv has been missing the web deps.)

## Next steps / open items — THE M18 WORK ORDER (operator, 2026-06-12)

**START HERE: merge/verify PR #92** (AI at full power part 1, ADR-0035: interpretive
Q&A + ask panel on every page + workbook facts + the standing disclaimer).
**Then ask the operator to re-deposit the Duration Bomb .mpp** (00_REFERENCE_INTAKE/
is empty in a fresh container) and verify the #91 mandate: computed finish
**2027-03-04** (was 8/5/2026), completed tasks visible on /path at their actual dates,
the "dates not supported by logic" finding counting/citing the template tasks, and the
hide-100% toggle acting on real rows. Continue the backlog in this order:

1. ~~Path Analysis completed tasks never show~~ (PR #91, merged; Duration Bomb
   re-verification owed, see above).
2. ~~Use the FULL screen width~~ (PR #91, merged).
3. ~~Sparse-logic CPM mandate~~ (PR #91/ADR-0034, merged; re-verification owed).
4. **AI at full power (operator):** ~~relaxed interpretive mode + ask panel on ALL
   pages (workbook-wide facts) + standing disclaimer~~ (PR #92/ADR-0035). REMAINING:
   **Executive Briefing reformat** for readability (sections/cards/tables) with
   Ollama polish; then the **second local AI model** (any OpenAI-compatible local
   endpoint, e.g. LM Studio/llamafile) and the dual-model cross-check / collaboration
   mode. Loopback-only egress stays non-negotiable.
5. **Forecast-drift ANIMATION** across versions (Bow-Wave-style stepper) and
   **locked Y-axis scales on ALL animated visuals** (scale = max of the metric across
   every loaded version, held through the animation — bow wave, drift, trend, path).
6. **PBIX visual reproduction** — docs/PLAN/PBIX-VISUALS.md is the spec (14 pages,
   engine coverage map; DAX intake complete, RatioMeasure is a dangling binding).
7. **CPM path-evolution animation** (Bow-Wave-style): per version pair, highlight
   tasks entering/leaving the critical path, duration changes on it, and
   schedule-optics signals (remaining-duration cuts beyond days worked; logic changes
   that absorbed a slip).
8. **Forecast explainer** (plain-English methodology + visuals) and **Trend page
   expansion** (space, per-metric drill-down to offenders per version, animation,
   Excel export of series).

1. **TP1-vs-SSI: CLOSED with full parity (2026-06-12).** All 18 traced tasks matched;
   live driving path UID-for-UID; non-zero slacks exact to SSI's display rounding;
   sub-day completed-task fractions are a documented model residual the whole-day floor
   absorbs (PARITY-REPORT + TEST-PROJECTS carry the verified tables). Remaining battery
   work: **Fuse re-run on a rebuilt TP3.mpp** (the Leads tasks-vs-links and
   Insufficient-Detail definitional rows), and **TP4 v1–v5 in the tool** (Compare must
   flag the UID-19 manipulation pair; Trend + Bow Wave/CEI on the five snapshots).
   The real-file 4-vs-66 re-test from #80 remains worthwhile but is now low-risk.
2. **Respond to operator feedback** on real `.mpp`/`.xer` files — tolerance classes live in
   `importers/_common.py`; ALWAYS re-run `pytest -m parity`. Watch how the new surfaces
   (Path Analysis, ask-the-AI, float bands, `/forecast`) read on real data.
3. **Deck measures awaiting a DAX export** (ADR-0030): EPI, RatioMeasure, Start-and-Finish
   Ratio — implement exactly when the operator provides the measure text; do not guess.
4. **per-task calendars** (P6 `TASK.clndr_id`, MSP resource calendars) — only if the
   operator's real programs mix calendars materially.
5. If the operator enables real Ollama generation: watch quality — narrative/briefing
   rephrases are figure-gated (`reattach`), ask-the-AI is figure-subset-gated (`ai/qa.py`).
6. **Tune the Bow Wave / CEI visuals** against real data vs the reference decks if they don't match.
7. Keep `docs/STATE/HANDOFF.md`, `SESSION-LOG.md`, and `docs/FINAL-REPORT.md` test counts current.

## Resume command for a NEW session
Paste this as the first message:
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first and work the
> M18 backlog in its listed order — start by checking PR #92 (AI at full power pt 1;
> open at handoff), then the Duration Bomb re-verification (re-deposit needed: computed
> finish must read 3/4/2027, completed tasks on /path, the new logic finding), then
> the Briefing reformat + the second local backend. Stay on branch
> `claude/clever-carson-uovtkk` (recreate from
> origin/main with `git fetch origin main && git checkout -B claude/clever-carson-uovtkk
> origin/main` after EVERY merge). Run `pip install -e '.[dev]'` into `.venv` first if
> tools are missing. Keep `pytest -m parity` at 10/10, run bandit UNPIPED, open draft
> PRs (don't merge — I do that), and never let schedule data leave the machine.
> The Duration Bomb .mpp and the SemanticModel zip live in 00_REFERENCE_INTAKE/ on the
> machine that received them — ask me to re-deposit if a fresh container needs them.
> Model: Fable 5 (1M context).
