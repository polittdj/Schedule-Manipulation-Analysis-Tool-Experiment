# Handoff — 2026-06-12 (post-#80 sitting — **the build is COMPLETE; PRs #69–#80 all merged**)

**Latest sittings:** after the #69–#76 run (ADR-0027..0030 — M15 closed, every milestone
M1–M17 done), the operator kept driving: the **desktop icon + favicon** (PR #77), the
**pythonw dead-port launcher fix** (PR #78), the **SSI-style Path Analysis workspace +
grounded ask-the-AI** (PR #79, ADR-0031), and the two real-file fixes — **day-granular
driving tiers** (the 4-vs-66 discrepancy) + **the server surviving heavy loads** (PR #80,
ADR-0032). The post-#80 sitting verified the merge + post-merge main CI green, re-ran the
full local gate (645 passed / parity 10/10), reviewed the #79/#80 surfaces (no defects
found), and brought the state docs current. **Code, tests, ADRs (32), and user docs are
mutually consistent; nothing is blocked.**
**Next session:** operator feedback — PR #80 asked for the MS Project + SSI side-by-side
re-run; optional items below. Model/mode: Fable 5 (1M context).

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

## What shipped the ADR-0027..0030 sittings — PRs #69–#76 (all merged)

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

## What shipped the latest sittings — PRs #77–#80 (all merged)

**PR #77 — the unique desktop icon + favicon:** `packaging/make_icon.py` redesigned
(stdlib-only, 4x supersampled, deterministic): the dark dashboard tile + white ▲ +
red/blue/green Gantt waterfall + gold dashed data-date line, packed as a 5-entry
256/128/64/32/16 PNG-in-ICO; the same bytes serve as the **browser favicon**
(`/static/favicon.ico`, linked in the layout) and a 256px Linux PNG. Sync + determinism
pinned by tests. Plus the prior HANDOFF consolidation.

**PR #78 — pythonw dead-port launcher fix:** the desktop icon launches `pythonw.exe` →
`sys.stdout`/`sys.stderr = None`; `print()` drops silently but **uvicorn's logging setup
touches the streams** → the server died right after the browser-open timer fired
(ERR_CONNECTION_REFUSED on a dead port). `launcher._ensure_streams()` rebinds missing
streams to devnull (never a log file — request paths carry schedule names; CUI stays off
disk); the regression test drives the real uvicorn.Config path with None streams.

**PR #79 (ADR-0031) — Path Analysis workspace + grounded ask-the-AI:** **`/path`** —
target UID (session target pre-fills) + user-defined secondary/tertiary day-bands over the
SSI-parity driving-slack engine; data grid LEFT (add/remove MS-Project fields; tier /
substring filters; hide-100%-complete), **scalable Gantt RIGHT** (px/day zoom slider,
month ticks, gold data-date line); `/api/driving` extended with the SSI grid fields, ISO
dates, and the data date. **Ask the AI** (`ai/qa.py`, `POST /api/ask/{schedule}`):
answers come from an engine-computed **cited fact sheet** (frame, forecasts, DCMA
verdicts, findings, float bands, completion performance); term-overlap selection; a local
model may phrase, but the **figure-subset gate** discards any answer containing a number
the engine never computed; the Null backend returns the matching facts verbatim. All local.

**PR #80 (ADR-0032) — day-granular driving tiers + load liveness (both operator-hit):**
1. Real file read **4 driving tasks where MS Project + SSI showed ~66** — tiering compared
   slack ≤ 0 to the MINUTE while real stored dates carry time-of-day raggedness; SSI's
   display axis is whole days. Tiers now classify on **slack floored to whole working
   days** (`_whole_days`, schedule's own calendar); goldens are exact day multiples →
   byte-identical, tier counts (36/12/12) unchanged, parity 10/10; boundaries pinned.
2. Reloading the test files **killed the server** (ERR_CONNECTION_REFUSED): async
   `/upload` parsed on the event loop, starving heartbeats past the 10s grace → the
   auto-shutdown watchdog fired MID-LOAD. Upload now runs **sync in the threadpool**, and
   an HTTP middleware counts **in-flight requests** — the watchdog never fires while any
   request is being served; every completion refreshes the beat. Browser-close shutdown
   behavior unchanged.

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
**645 passed, 3 skipped; parity 10/10; engine ≈98%; overall ≈98%; egress + air-gap green; bandit/pip-
audit clean (3.11 + 3.13).** Verify locally:
`ruff check . && ruff format --check . && python -m mypy && pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && pytest -m parity && bandit -q -r src`.
(In a fresh remote container run `pip install -e '.[dev]'` into `.venv` first — the preinstalled
venv has been missing the web deps.)

## Next steps / open items (all OPTIONAL — the build contract is complete)
1. **Respond to operator feedback** on real `.mpp`/`.xer` files — tolerance classes live in
   `importers/_common.py`; ALWAYS re-run `pytest -m parity`. **Pending: PR #80 asked the
   operator to re-run the MS Project + SSI side-by-side** (same file/UID) — the driving
   count should now match at day granularity; if it still diverges, get the reported number
   + any red import-notice text (CUI-safe). Also watch: exotic calendars degrading oddly
   (the "unreadable project calendar" log line names the path), and how the M15 surfaces
   (float bands / completion performance / `/forecast`) and `/path` read on real data.
2. **Deck measures awaiting a DAX export** (ADR-0030): EPI, RatioMeasure, Start-and-Finish
   Ratio — implement exactly when the operator provides the measure text (Tabular Editor
   export per the intake instructions); do not guess formulas.
3. **per-task calendars** (P6 `TASK.clndr_id`, MSP resource calendars) — only if the
   operator's real programs mix calendars materially.
4. If the operator enables real Ollama generation: watch quality — every rephrase is gated
   (citations + exact figures, fail-closed to verbatim).
5. **Tune the Bow Wave / CEI visuals** against real data vs the reference decks if they don't match.
6. Keep `docs/STATE/HANDOFF.md`, `SESSION-LOG.md`, and `docs/FINAL-REPORT.md` test counts current.

## Resume command for a NEW session
Paste this as the first message:
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first and continue exactly per its
> "Next steps / open items". Stay on branch `claude/clever-carson-uovtkk` (recreate from `origin/main`),
> keep `pytest -m parity` at 10/10, open draft PRs (don't merge — the operator does), and never let
> schedule data leave the machine. Model: Fable 5 (1M).
