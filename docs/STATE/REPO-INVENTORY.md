# Repository Inventory — POLARIS / schedule-forensics

> **Version/ADR stamps refreshed 2026-07-17 (v1.0.59, ADR-0250; ADR-0250 deep-audit remediation).** For
> the reference-intake catalog, `00_REFERENCE_INTAKE/INDEX.md` is now the authoritative per-file
> map (what each file is, which tests it verifies, duplicates, reorganization rules).
>
> **What this is.** A durable, single-place map of everything in this repo — every package, what it
> does, how it connects, the test/fixture ground truth, the docs/ADR arc, the committed reference
> material (the real `.xer` samples were removed by the operator on 2026-07-15 and will return
> later; only the synthetic `tests/fixtures/xer/` remains), and the build/CI/installer toolchain.
> Read this first to recall "what is here and how to use it." It is assembled from a parallel
> read-only inventory of the whole tree. `docs/STATE/HANDOFF.md` remains the live "where we are /
> what's next" (**version/ADR numbers there are authoritative when this map lags**); this is the
> standing map.

## Repo map (top level)

```
schedule-forensics/
├── src/schedule_forensics/         the tool (std-lib-only runtime, loopback-only)
│   ├── model/                      frozen pydantic Task/Schedule/Calendar/Resource (unique_id identity)
│   ├── importers/                  mspdi / xer / json_schedule / mpp_mpxj (MPXJ .mpp→MSPDI) + loader
│   ├── engine/                     CPM + metrics/ (DCMA-14, CEI, HMI, float, EVM, …) + driving-slack,
│   │                               trend, grouping, manipulation, margin, sra, cache/summary/memory
│   ├── ai/                         AIBackend protocol (Null/Ollama/OpenAICompat), citations, qa, narrative
│   ├── web/                        app.py (all routes + SessionState + HTML), i18n, help, static/*.js|css
│   ├── exhibits/                   offline report/exhibit generation
│   ├── launcher.py                 the `schedule-forensics` entry point (binds 127.0.0.1, opens browser)
│   └── net_guard.py                egress guard (no forbidden HTTP client may enter the runtime)
├── tests/                          engine / web / importers / ai / parity / guards / installer / exhibits
│   └── fixtures/golden/            SSI + Acumen ground-truth goldens (gzipped MSPDI + case.json)
├── docs/                           STATE/ (HANDOFF, SESSION-LOG, this file), adr/ (0001..), DESIGN-SYSTEM,
│                                   METRIC-DICTIONARY (generated), PLAN/ (BUILD-PLAN, RTM, INSTALLER-SPEC)
├── tools/mpxj/                     vendored MPXJ native-.mpp toolchain (MpxjToMspdi.java + jars + classes)
├── tools/installer/               build_installers.py — generates the 9 one-file installers from the wheel
├── installer/                     the 9 tier1/2/3 × ps1/sh/command installers (embedded-wheel, lockstep)
├── 00_REFERENCE_INTAKE/            committed non-CUI reference material (see its section below)
├── .github/workflows/ci.yml       CI gates; .githooks/ CUI pre-commit guard; pyproject.toml toolchain
└── CLAUDE.md                       project instructions (the two non-negotiable laws)
```

The two non-negotiable laws (from `CLAUDE.md`): **(1) Data sovereignty / CUI** — no schedule content
leaves the machine, AI is loopback-only and fails closed, std-lib-only runtime, never commit real CUI.
**(2) Fidelity over speed** — numbers must match the reference tools; parity is gate-locked.

---

## Engine

Read-only inventory of `src/schedule_forensics/engine/` for the forensic schedule-analysis tool. Flow of the whole system: **importer → `Schedule` model → engine (CPM + metrics + forensic analyses) → `web/app.py` → server-rendered HTML/JS**, with the `ai/` layer polishing already-computed figures. Everything below is deterministic, offline, and std-lib-only (Laws 1 & 2).

### 0. CPM model conventions (shared by every module)

These invariants are defined in `model/` (`task.py`, `schedule.py`, `calendar.py`, `units.py`, `relationship.py`) and honored everywhere in the engine:

- **Working-minute time axis.** All durations, floats, lags are integer **working minutes** (`480` = one 8-hour day; `model/units.py:MINUTES_PER_DAY`). Integer minutes are exact — no binary-float drift (ADR-0005 determinism). Days conversion happens **only at the presentation boundary** via `minutes_to_days()` (`Decimal` + `ROUND_HALF_UP`). The DCMA "44 working days" tripwire is defined in *days* and converts on each schedule's own calendar (`metrics/_common.py:forty_four_days_min`, `FORTY_FOUR_DAYS = 44`).
- **`unique_id` is the sole cross-version identity.** Never the row id (renumbers), never the name (non-unique). `Schedule.tasks_by_id` / `resources_by_id` are cached `MappingProxyType` views; `model_copy`/`__getstate__` drop those caches so they can never go stale or break the SRA pickle offload.
- **Derived, never stored.** CPM early/late dates, total/free float, driving slack, and all DCMA/EVM metrics are computed by the engine and deliberately **not** stored on `Task`. Optional date/cost fields default to `None` = "source didn't provide it" (never assume 0).
- **Inactive-task exclusion (ADR-0128).** `_scheduled_tasks` / `metrics/_common.non_summary` drop both **summary rollups** (`is_summary`) and **inactive tasks** (`is_active=False`) from the CPM network and every metric denominator — matching MS Project / Acumen. Their links drop with them. The forensic diff/manipulation layer reads `schedule.tasks` directly, so a *deactivation between versions* is still detected.
- **Effective total float / critical (Acumen fidelity, ADR-0080/0010).** `metrics/_common.effective_total_float(task, recomputed)` prefers the source tool's **stored, progress-aware Total Slack** (`Task.stored_total_float_minutes`) over recomputed pure-logic CPM float when the file carries it; `is_effective_critical` prefers `Task.stored_is_critical`. This is why DCMA float counts and "Critical" match Acumen on progressed files (verified 41/37 goldens). Pure-logic CPM float is used for independent path analysis.
- **Constraint model** (`ConstraintType`): SNET/FNET = forward floors; SNLT/FNLT = backward caps; MSO/MFO = pins (forward pin + backward cap); a `deadline` is a backward cap; **ALAP is refused** (raises `CPMError`) rather than mis-scheduled.

---

### 1. Core CPM engine

**`cpm.py`** (`engine/cpm.py`) — the trust-root forward/backward-pass solver; every stochastic/counterfactual path funnels through it (Law 2).
- Dataclasses: `TaskTiming(unique_id, early_start, early_finish, late_start, late_finish, total_float, free_float, is_critical)`; `CPMResult(timings: Mapping[int,TaskTiming], project_finish: int, critical_path: tuple[int,...], date_driven: tuple[int,...])` with `.timing(uid)`. `CPMError(ValueError)`.
- Public helpers: `compute_cpm(schedule, *, required_finish_offset=None, duration_overrides=None) -> CPMResult` — the single solver. `duration_overrides` (UID→minutes) is the **sole hook** the SRA/margin/counterfactual layers use to re-solve under changed durations, guaranteeing zero divergence. `required_finish_offset` imposes a backward-pass target (drives negative float for driving-slack).
- Date/offset conversion: `datetime_to_offset(start, target, calendar)`, `offset_to_datetime(start, minutes, calendar)` (inverse on the working grid), plus internal `_count_working_days`, `_advance_working_days`, `_next_working_day` (week-jump + holiday compensation, O(weeks+holidays)). Elapsed-duration ("eday") tasks bypass calendars via `_elapsed_finish_offset`/`_elapsed_start_offset` (wall-clock, 1440 min/day).
- Link math (module-public, reused by driving-slack): `es_lower_bound`, `lf_upper_bound`, `link_slack` (FS/SS/FF/SF, lag-aware). `_topo_order` = Kahn sort, ties broken by ascending UID (determinism), raises `CPMError` on cycle.
- Constraint/stored-date resolution: `_constraint_bounds` (es_floor/es_pin/lf_cap), `_stored_date_bounds` (ADR-0034 — unstarted manual tasks *pin* at stored start, unstarted logic-unbound auto tasks *floor* there; the affected UIDs go to `CPMResult.date_driven` and surface as the "dates not supported by logic" finding).
- Critical path = `total_float <= 0` (pure CPM). Summary logic is lowered onto leaves via `lower_summary_relationships` before the pass.

**`summary_logic.py`** (`engine/summary_logic.py`) — reproduces MS Project's honoring of logic attached to **summary** tasks (ADR-0043) by *lowering* each summary endpoint onto its non-summary WBS-descendants (segment-prefix hierarchy: `6.1` parents `6.1.2` but not `6.10`).
- `summary_leaf_descendants(schedule) -> dict[int, tuple[int,...]]`; `summaries_with_logic(schedule) -> tuple[int,...]` (the best-practice violation the recommender flags); `lower_summary_relationships(schedule) -> tuple[Relationship,...]` (cross-product expansion, dedup, **no-op when no summary carries logic** → parity-preserving, byte-identical CPM on the goldens). Called by `cpm.compute_cpm` and `recommendations`.

---

### 2. Float analysis & driving-path family

**`float_analysis.py`** — presentation layer over `CPMResult`. `FloatResult` (per-task float in minutes+Decimal days, `is_critical` pure-CPM, `is_critical_incomplete` = Acumen "Critical"), `ScheduleFloatSummary` (task/critical/critical-incomplete/negative-float counts). `analyze_floats(schedule, cpm?)`, `summarize_floats(schedule, cpm?)`. Documents that this uses *pure-logic* `is_critical`, so on a progressed file it can name a different UID set than the `is_effective_critical` metric surfaces (audit F-04). Critical-incomplete validated 41/4 (Project2/Project5_TAMPERED).

**`path_trace.py`** — pure graph ops over the UID-keyed logic network (summaries excluded). `ancestors_of(schedule, target)` (transitive predecessors — what can drive the focus, target excluded), `descendants_of(schedule, source)` (mirror), `subschedule_to_target(schedule, target)` (restrict schedule to target+ancestors), `topo_order(schedule, uids)` (deterministic, ties by UID, raises on cycle). The "which tasks / what order" layer under driving-slack.

**`driving_slack.py`** — the **SSI MS Project add-on parity** engine (§6.C, ADR-0011), bit-matched against the SSI golden export (Project5/UID 143; Large Test File UID 152, 783/783 activities, driving path 61/61).
- `compute_driving_slack(schedule, target_uid, *, secondary_max_days=10, tertiary_max_days=20, cpm_result=None, direction=PathDirection.PREDECESSORS, ignore_constraints=False, ignore_leveling_delay=False) -> dict[int, DrivingSlackResult]`. Method: trace focus ancestors (or descendants); take each task's **as-scheduled stored** start/finish (progress-aware — SSI runs inside MSP), lunch-aware via `_stored_offset`/`Calendar.intraday_worked_minutes` (ADR-0117); accumulate slack = min over successor links of (link free float on the **successor's own calendar** + successor's slack) (ADR-0118). `DrivingSlackResult(unique_id, driving_slack_minutes, driving_slack_days: Decimal, on_driving_path, tier)`; `PathTier` = DRIVING(<1 day)/SECONDARY/TERTIARY/BEYOND. `PathDirection` = PREDECESSORS/SUCCESSORS/BOTH. `date_basis()` returns the display axis (stored dates, CPM fallback). `strip_constraints()` powers "ignore constraints". `driving_path(schedule, results)` = on-path UIDs topo-ordered. Day-tier provenance is NASA SMH Rev 2-sourced (path-tier practice) with operator-overridable day values.

**`driving_path.py`** — driving corridor **between two chosen UIDs A→B** and its evolution across versions (built on driving-slack). `driving_path_between(schedule, source, target, ...) -> DrivingPathBetween` (`path`, `source_present`, `target_present`, `connected`, `drives`, `source_slack_days`). A *drives* B when A is on B's driving path; else *connected* but not driving (reports the slack). `compute_driving_path_evolution(schedules, cpms, source, target, ...) -> DrivingPathEvolution` of `DrivingPathSnapshot`s (entered/left/stayed, `change_note` via `_transition`: "A now drives B", "A stopped driving B", etc.).

**`drag.py`** — DRAG (Devaux's Removed Activity Gauge): working days each on-path activity personally adds to the target. `compute_drag(schedule, results, *, cpm_result=None) -> dict[int, DragResult]` (`drag_minutes`, `drag_days`, `remaining_minutes`, `capped_by_uid`). Rule: `drag = min(remaining duration, minimum driving slack among CONCURRENT overlapping activities)`; parallel zero-slack pairs get 0 drag. Validated exact against SSI Directional Path export (focus UID 67, all 20 Path-01 Drag values; UID 35 = 16d; parallel pairs 60/61, 65/66 = 0d).

---

### 3. Cross-version trend / evolution / curve family

**`diff.py`** — the deterministic UID-keyed structural delta (§6.B). `diff_versions(prior, current) -> VersionDiff` (`added_tasks`, `deleted_tasks`, `changed_tasks: tuple[TaskDiff]`, `added_links`, `removed_links`). `TaskDiff.changed(field) -> FieldDelta|None`. Tracks 18 fields (durations, baseline/actual/forecast dates, %, constraint, cost, work, resource_assignments, `is_active`). Summaries excluded; links keyed `(pred, succ, type, lag)`. Substrate for `manipulation`, `change_effects`, `path_evolution`.

**`manipulation.py`** — cited forensic manipulation signals across a version pair (§6.D, M11). `detect_manipulation(current, prior, *, current_cpm=None, prior_cpm=None) -> tuple[Finding,...]` emits (via `recommendations.Finding`): deleted tasks (HIGH if on prior critical path), deactivated tasks (audit F-13), deleted logic, shortened durations on incomplete work, **constraint tightening** (new hard MSO/MFO/SNLT/FNLT that now clamps ≤0 float), **calendar loosening** (net working-time gain), baseline-date changes (DECM 29I401a), actual-date edits/erasures (DECM 06A504a/b), added logic, cost changes (actual-cost *decrease* = HIGH), work changes (actual-work *decrease* = HIGH), resource-assignment plan edits. `assignment_change_rows(prior, current) -> tuple[AssignmentChange,...]` (Fuse "Resources" sheet parity, 32/17 rows verified). `trend_across_versions(schedules, cpms?) -> tuple[TrendPoint,...]` (per-version finish + completed/in-progress/critical counts, ≤10 snapshots).

**`trend.py`** — Acumen Fuse Diagnostic Executive Briefing "Trend Analysis". `order_versions(schedules)` (by status_date, undated last, stable). `compute_quality_trend(schedules, cpms?) -> tuple[MetricTrend,...]` over the 9 §A schedule-quality metrics with `MetricTrend.sentence()` ("Missing Logic: increases … best X (0) … worst Y (3)"), best/worst index, per-version offenders. `compute_hmi_trend` → `HMISeries` (period-over-period). `compute_cei_trend` → `CEISeries` (+ start/critical/adjusted variants). `compute_float_ratio_trend` → `FloatRatioSeries` (value + period delta).

**`path_evolution.py`** — critical-path evolution across versions (M18 item 7). `effective_critical_set(schedule, cpm)` (progress-aware: stored Critical flag, incomplete/active/non-summary). `compute_path_evolution(schedules, cpms, target_uid=None) -> PathEvolution` of `CriticalSnapshot`s (critical/entered/left/stayed, finish delta, `duration_changed`, `shortened_on_path`, `removed_logic_count`, `completed_on_path`, per-activity `PathChange` attribution). With `target_uid`, uses the 0-driving-slack chain instead. `_classify_entered`/`_classify_left` name the upstream slip that consumed float (reuses `detect_manipulation`). `_effectively_complete` = 100% OR stored actual finish (ADR-0051).

**`path_counterfactual.py`** — "finish if work cut from the critical path were restored". `compute_path_counterfactual(prior, current, prior_cpm, current_cpm, *, target_uid=None) -> PathCounterfactual|None`. Isolates activities that **left the effective-critical path without completing** and whose own duration/logic/constraints changed, reverts exactly those, re-runs CPM, reports `finish_delta_days` (>0 = the changes pulled finish in / masked a slip). `RevertedActivity`, `GainedFloatActivity` (unchanged leavers — nothing to revert), `uncomputable` flag on a cyclic revert.

**`change_effects.py`** — per-change counterfactual EFFECT on a chosen target (operator 2026-07-08). `compute_change_effects(prior, current, current_cpm=None, *, target_uid=None) -> ChangeEffectsReport|None`. Reverts each detected change (removed/added link, duration, constraint) **one at a time**, re-runs CPM, records working-day movement of the target (auto-picks last critical activity via `_last_critical_uid`) and project finish; also an aggregate. `ChangeEffect(kind, label, citation_uids, target_finish_delta_days, project_finish_delta_days, is_reschedule_artifact)`. Handles MS Project "reschedule uncompleted work" SNET-at-data-date artifacts (deferred, measured last so the `_MAX_CHANGE_EFFECTS=60` cap starves noise not real edits), cyclic reverts (`skipped_unsolvable`), and cap disclosure. Worked example: restoring FS 188→187 moves UID 155 +23 working days.

**`bow_wave.py`** — monthly finish-profile bow-wave + forecast-anchored CEI (§6.D). `compute_bow_wave(schedules, target_uid=None, track_uids=()) -> BowWave` (shared month axis clamped ±18/12 mo around status dates, cap 48). Per `SnapshotProfile`: baselined/scheduled/finished counts per month, pairwise `cei = finished_by_end / prior-forecast-for-period` (distinct from EVM `cei_finish`, ADR-0052), per-month drill UID lists, target + up-to-20 tracked activities.

**`s_curve.py`** — cumulative planned (baseline-finish) vs actual/forecast (current-finish) progress curves per version on a shared month axis (cap 60). `compute_s_curve(schedules, track_uids=()) -> SCurve` / `SCurveVersion` / `TrackedActivity`. Pre-window finishes fold into the running count so shedding oldest months never drops progress.

**`month_curves.py`** — deck Finishes / DATA-Date-Finishes / Slippage pages (PBIX 6/7/12). `compute_month_curves(schedules) -> MonthCurves` / `VersionCurves` (baseline vs actual finishes and starts per month; actual-where-present else scheduled).

**`month_axis.py`** — shared primitives for the curve views: `month_index(d)` (year*12+month-1), `month_label(ym)` ("Mar-27"), `bucket(dates, lo, n)`.

---

### 4. `engine/metrics/` — the Acumen Fuse v8.11.0 / DCMA-14 / EVM / SSI metric set

**`_common.py`** — the shared primitive `MetricResult(metric_id, name, count, population, value, unit, status, threshold, direction, offender_uids)` (frozen; every metric is auditable and cites offender UIDs). `CheckStatus` (PASS/FAIL/NOT_APPLICABLE — NA never a fabricated 0), `Direction` (LE/GE/EQ), `evaluate`, `percent`, `non_summary` (the canonical population), `is_incomplete`, `effective_total_float`, `is_effective_critical`, `forty_four_days_min`, `duration_days_axis`, `to_offset`.

**`__init__.py`** — re-exports the public metric API (`compute_dcma14`, `compute_bei`, `compute_evm_indices`, `compute_baseline_compliance`, `compute_schedule_quality`, `compute_cei`, `compute_hmi`, `compute_fei`/`compute_bri`, `compute_float_ratio`, `compute_float_bands`/`compute_float_sums`, `compute_change_metrics`, `compute_net_finish_impact`, `compute_completion_performance`, `compute_ribbon`/`ribbon_offender_map`, `compute_activity_makeup`/`compute_constraint_distribution`, `compute_wbs_breakdown`, `dcma_pass_rate`/`population_share`).

**`dcma14.py`** — the primary Acumen-parity ribbon (M7); `compute_dcma14(schedule, cpm_result=None) -> dict[str, MetricResult]` returns 16 keyed checks (DCMA01–14, DCMA04 split FS/SSFF/SF). Notables: DCMA02/03 count *activities* not links (Fuse convention); DCMA06/07 use `effective_total_float` (stored slack — 44/44 verified P2/P5, closing the ADR-0012 residual); DCMA09 Invalid Dates uses the Bible formula on stored dates (verified 21/0 on Hard_File_updated2/3); DCMA12 `_critical_path_test` injects a 100-day delay on the lowest-UID critical activity and checks the finish moves by exactly that (elapsed-safe, QC D3); DCMA13 `_cpli` = (remaining CP length + project float)/remaining length (ADR-0086); DCMA14 delegates to `compute_bei` = complete-among-baselined-due Normal tasks (ADR-0176; verified P2 0.74, P5 0.59, Hard_File 0.27/0.59/0.47).

**`schedule_quality.py`** — Acumen "Schedule Quality" §A summary (distinct denominators). `compute_schedule_quality(schedule, cpm?) -> dict[str, MetricResult]`: Missing Logic (6/6), Logic Density (2×links/activities, half-up 2dp), Critical (`is_effective_critical`, 41/37), Hard Constraints, Negative Float, Insufficient Detail (Bible: duration/project-calendar-span > 0.1; verified 43 on Large Test File), Number of Lags/Leads (distinct activities), Merge Hotspot (≥3 predecessors, 10/10).

**`evm.py`** — EVM indices + baseline-compliance (M8, §C). `compute_baseline_compliance(schedule, cpm?)` (Forecast-to-be-Finished/Started, Completed/Started On-Time/Late, Not Completed/Started, BFC/BSC — BSC uses the Half-Step-Delay actual-start-vs-baseline-*finish* numerator, ADR-0083; on-time bars carry the 95% GE bar, ADR-0161). `compute_evm_indices` (SPI/CPI/TCPI cost-based = NA without cost; CEI Finish/Start; count-based SPI(t) via `earned_schedule()`; `_spi_t_acumen` the Bible per-activity duration-efficiency average, verified 0.80/1.14/1.25). `earned_schedule(schedule, tasks) -> EarnedSchedule|None` (shared by SPI(t), WBS breakdown, forecast). `compute_schedule_variance` → `ScheduleVariance` (handbook §7.3.3.1 SVt = ES−AT, plus per-activity finish/start variance; parity-isolated dataclass).

**`cei.py`** — Current Execution Index, forecast-anchored, period-over-period (needs two snapshots). `compute_cei(prior, current) -> dict[str, MetricResult]`: `cei_tasks`, `cei_milestones`, plus variants `cei_task_starts`, `cei_critical`, `cei_tasks_adjusted` (early-completion credit) (ADR-0101, all EXACT vs Acumen; Large Test File 24/129=0.19, 1/6=0.17).

**`hmi.py`** — Hit-or-Miss Index (period baseline execution, ADR-0087). `compute_hmi(current, previous_time_now) -> {hmi_tasks, hmi_milestones}` — hits = complete-in-period among baselined-to-finish-this-period; offenders = misses.

**`fei_bri.py`** — single-snapshot SEM Bible indices. `compute_fei(schedule)` (FEI starts/finish = to-go forecast vs baseline in the remaining window; validated starts numerator 828 EXACT), `compute_bri(schedule)` (Baseline Realism Index cumulative = baselined-due actually finished; 0.51, denominator 1228 EXACT).

**`sem.py`** (PR-M2, ADR-0238) — the full Bible *Schedule Execution Metrics* family. `compute_sem(schedule, prior=None) -> dict[str, MetricResult]` returns the ten SEM metrics in Bible order: Completed Activities, Workoff Burden (SEM01), BRI Current (SEM02), BRI Cumulative (reused verbatim from `fei_bri`), BPI Current (SEM04), BEI Current (SEM05), BEI Cumulative (SEM06), TC-BEI (SEM07), FRI Current (SEM08 — PreviousFinish join to the prior version by UniqueID; NA without one), Delta (SEM09 — computed from its own formula, never as a difference of rounded outputs). Formulas verbatim from the committed `.aft` (the formula-audit test pins all nine strings); Value-Task population, 30-calendar-day current window from `status_date`, zero-denominator = value 0 per the Bible's else-arm but status NA (never presented as scored). Key fidelity: BEI numerators count ALL actual finishes (can exceed 1; SEM BEI-Cumulative ≠ DCMA BEI, both ship separately labeled per the ADR-0176 precedent); TC-BEI's denominator excludes already-finished baselined-to-go work. **Fuse-validated cell-for-cell on both golden pairs** (P2/P5_TAMPERED in the CI parity pins; Large Test File/File2 incl. FRI 0.19 in the sandbox oracle); the vendor's exported Delta cells were proven irreproducible from the vendor's own formula (export artifact, documented in ADR-0238) — the formula-faithful values are pinned. Surfaced on the `/standards` page (PR-M1, ADR-0237: DCMA-14 + NASA/Acumen-Fuse execution indices + SEM, one formula-first row per metric, values/threshold/verbatim formula/source from the help.py dictionary).

**`float_ratio.py`** — Float Ratio™ (Bible verbatim): mean-of-ratios `AVERAGE(TotalFloat/RemainingDuration)` + aggregate ratio-of-means, over Normal planned/in-progress tasks; each term on its own axis (float always working-minutes, elapsed remaining on 1440; QC D7). Offenders = very-tight (<0.1). `compute_float_ratio(schedule, cpm?) -> {float_ratio, float_ratio_aggregate}`.

**`float_bands.py`** — low-float band metrics (M15, ADR-0030). `compute_float_bands` (6 metrics: total/free float `≤0`, `<5`, `<10` working days, cumulative, offender UIDs) and `compute_float_sums -> FloatSums(total_days, free_days)`. **Uses raw recomputed CPM float** by validated design (0-day total band reproduces Fuse "Zero Days Float" P2 41/P5 4; ADR-0151) — deliberately differs from DCMA-06/07's stored-preferring float.

**`change_metrics.py`** — Acumen §E Schedule-Network / Change metrics (M8), version pair by UID. `compute_change_metrics(current, prior?, *, cpms?) -> dict[str, MetricResult]` (SN01–19: Total/Added/New-Critical/No-Longer-Critical/Finish-Start-Slips/Remaining-Duration-Increases/Float-Erosion/Completed/In-Progress; ENGINE==FUSE verified, one documented UID-96/99 swap from the stored-vs-recomputed-critical basis). `compute_net_finish_impact` → HSD10 (−148 days engine-CPM basis; reconciles day-exact to Fuse −134 stored basis).

**`completion_performance.py`** — deck Completion Metrics (M15). `compute_completion_performance(schedule) -> dict[str, MetricResult]`: ahead/on-schedule/behind splits, avg days ahead/late, longer/shorter-than-planned, duration-ratio min/avg/max, `mei` (Milestone Execution Index), `epi` (Execution Progress Index, ADR-0033), `start_finish_ratio`, `elapsed_since_last_finish` (staleness).

**`ribbon.py`** — Acumen Fuse Ribbon assembly (calibrated to exports). `compute_ribbon(schedule, cpm, audit) -> RibbonMetrics` (missing_logic ALL statuses, logic_density half-up, critical `is_effective_critical`, hard/negative/lags/leads from the audit, merge_hotspot >2 preds, avg/max float on effective float, insufficient_detail from schedule_quality, `incomplete_float_count` for NA-detection). `ribbon_offender_map` gives the click-drill activity sets.

**`derived.py`** — Layer-A derived metrics (pure functions of already-computed figures, cited in `web/help.py`). `population_share(count, pop)` and `dcma_pass_rate(passed, failed)` (half-up 1dp; `None` on empty — never fabricate).

**`schedule_card.py`** — deck Metrics landing page (PBIX 1). `compute_activity_makeup(schedule) -> ActivityMakeup` (milestone/normal/summary split excluding UID-0; complete/in-progress/planned). `compute_constraint_distribution(schedule) -> tuple[ConstraintCount,...]`.

**`wbs_breakdown.py`** — per-top-level-WBS completion + Earned-Schedule (PBIX 8/9, ADR-0041). `compute_wbs_breakdown(schedule) -> tuple[WBSGroup,...]` (per group: completion split, duration ratios, SPI(t)/ES/AT via `earned_schedule`). `_top_level`, `_NO_WBS` reused by `float_erosion`/`forecast`.

**`health_extra.py`** — extra structural health checks (parity-isolated dataclasses, NASA SMH Fig 6-9). `compute_health_checks(schedule, cpm) -> HealthChecks` of `HealthCheck`s: critical merge/diverge hotspots, LOE-on-critical-path, milestone-with-duration, zero-duration task, hidden duration (lag > 35% duration), estimated durations, missing WBS, missing baseline finish.

**`logic_integrity.py`** — `compute_logic_integrity(schedule) -> LogicIntegrity`: out-of-sequence FS progress (successor started before predecessor finished) and redundant logic (direct A→C when a ≥2-hop path exists; skipped on cyclic/oversize networks, bounded `_REDUNDANT_MAX_TASKS/EDGES`). Feeds `scorecards`. Parity-isolated.

**`constraint_health.py`** — `compute_constraint_health(schedule, cpm) -> ConstraintHealth`: unsatisfied date constraints (CPM early date runs past a SNLT/FNLT/MSO/MFO cap) and deadline-breach negative float (`early_finish > deadline`). Parity-isolated.

**`vertical_integration.py`** — `compute_vertical_integration(schedule) -> VerticalIntegration`: summaries whose stored span doesn't envelope their WBS descendants (stored dates only, inactive excluded). Parity-isolated.

**`margin.py`** — schedule margin (buffer named "margin"). `is_margin_task(task)`, `compute_margin(schedule, cpm, *, margin_uids=None) -> MarginAnalysis` (total vs **effective** margin = zero every margin task's duration, re-run CPM, measure finish pull-in — via `duration_overrides`), `compute_margin_trend(versions, *, margin_uids=None) -> tuple[MarginPoint,...]`. Parity-isolated. **F3a/3b (ADR-0230):** an opt-in `margin_uids: frozenset[int] | None` (default `None` = today's name-based selection) threads the operator's *confirmed* margin-task overlay through all margin computations; `NEAR_MISS_KEYWORDS` (reserve/contingency/integrated-return) + `margin_candidates(schedule, cpm) -> tuple[MarginCandidate,...]` surface primary + near-miss candidates (duration, total float, criticality) for the confirm/deny UI.

**`float_erosion.py`** — `compute_float_erosion(schedule, cpm, wbs_field=None) -> FloatErosion` of `WBSFloat`s (per-top-level-WBS min/avg total float, critical count, red/yellow/green stoplight; `_LOW_FLOAT_DAYS=10` = PPC Handbook Fig 3.4-3 band; progress-aware float; groupable by any custom field, ADR-0150). Parity-isolated.

**`field_forecast.py`** — per-field group execution metrics for the Forecast page (ADR-0179). `compute_field_forecast(schedules, field) -> tuple[GroupMetrics,...]` — each (field-value group × version) gets BEI/HMI/CEI-Finish/Start/both SPI(t)s over a sub-schedule, plus `sei` (start execution index, the leading indicator) and `no_completed_work` flag (never fabricates a finish index — NDIA/DCMA N/A convention). Helpers `_groups`, `_sub_schedule`, `_sei` reused by `forecast.compute_group_rollup`.

**`performance_summary.py`** — the operator's PerformanceAnalysisSummary workbook (7 graph families, ADR-0182). `work_to_go_census`→`WorkToGoCensus` (G1), `activity_flow`→`ActivityFlow` (G2 bow-wave + G3 BEI/HMI curves), `workoff_burden`→`WorkoffBurden` (G4 baseline-execution categories with below-axis backlog), `duration_ratio`→`DurationRatioData` (G5 DRM S-curve/histogram), `to_go_snapshot`→`ToGoSnapshot` (G6/G7 to-go ratios + critical share). Shared `month_axis`, per-month drill UID lists; nothing imputed (`None` = N/A).

---

### 5. Audit, recommendations, scorecards, catalog

**`dcma_audit.py`** — independent cited DCMA-14 audit (§6.E, M10). `audit_schedule(schedule, cpm?) -> ScheduleAudit` (`checks: tuple[AuditCheck]`, `passed/failed/not_applicable`, `.failed_checks`). `Citation(source_file, unique_id, task_name)` — the tool-wide provenance record. `_IMPROVEMENTS` maps each check to plain-language remediation. Wraps `compute_dcma14`, cites offenders via `_cite_offenders`.

**`recommendations.py`** — the structural risk/opportunity/concern recommender (§6.E, M10). `recommend(current, prior=None, *, cpms?, target_uid=None) -> tuple[Finding,...]`. `Finding(category: Category{RISK/OPPORTUNITY/CONCERN}, severity, metric_id, title, detail, course_of_action, citations, likelihood, impact_days, float_days, driving_float_days)` with `risk_score = impact_score × likelihood_score` (5×5 matrix). `_quantify` attaches deterministic matrix fields from CPM citations (tightest float, negative-float exposure = impact_days, driving slack to target, CERTAIN when real exposure). Findings from: DCMA audit (`_HIGH_SEVERITY_DCMA` = 07/11/12/13/14), logic-unsupported dates (`cpm.date_driven`), logic-on-summary, baseline compliance, version-change (`compute_change_metrics`/`compute_net_finish_impact` incl. HSD10 finish-slip), driving-path opportunity. `SEVERITY_ORDER`, `Severity`, `Likelihood`, `likelihood_rank`/`severity_rank`/`impact_rank` shared with `manipulation`.

**`scorecards.py`** — NASA STAT / GAO-10 / SRA-readiness assessment scorecards (consolidation layer, **no new metric math**). `compute_scorecards(schedule, cpm, audit) -> (Scorecard, Scorecard, Scorecard)` via `compute_nasa_stat`, `compute_gao_scorecard`, `compute_sra_readiness`. Each `ScorecardCheck(key, label, status[PASS/FAIL/INFO/NA], detail, provenance, offender_uids)` re-presents gate-locked DCMA/logic-integrity numbers or trivial cited model scans; `Scorecard.score` = passed/scored. Plus `reserve_recommendation(cdf, committed_offset, ...) -> ReserveRecommendation` — nearest-rank percentile reserve sizing over the SRA finish CDF (P70/P80 headline; ADR-0106, no new statistics).

**`metric_catalog.py`** — the Metric Workbench library (ADR-0204, **no new math** — aggregates the audit + ribbon). `catalog_entries()`/`catalog_families()` (stable metadata), `evaluate_catalog(schedule, cpm, audit=None) -> dict[str, CatalogRow]` (DCMA rows straight from `audit_schedule`, ribbon extras from `compute_ribbon`+`ribbon_offender_map`; `applicable=False` where a value is an NA placeholder, incl. the two float extras on an empty incomplete population).

---

### 6. Schedule Risk Analysis (Monte-Carlo) family

**`sra.py`** — seeded, std-lib-only Monte-Carlo SRA (ADR-0106), **parity-isolated** — every iteration re-solves through `compute_cpm(..., duration_overrides=...)` (zero divergence guarantee; with all activities at most-likely the sim finish == deterministic finish, test-pinned). Two paths:
- **Legacy whole-project**: `compute_sra(schedule, cpm, *, config=SRAConfig, overrides=None, risks=()) -> SRAResult`. `SRAConfig(iterations, seed, auto_low/most_likely/high, distribution["triangular"|"pert"], target_uid, occurrence_mode, use_risk_register, correlation)`. Inputs: manual 3-point `ActivityRisk`, else auto triangular on **remaining** duration (Deltek "Realistic" 90/100/110). Outputs: finish CDF/S-curve, P10/50/80/90 + mean (offsets and ISO dates), deterministic percentile, histogram, per-activity `ActivitySensitivity` (Criticality Index / Spearman duration sensitivity / SSI), hard-constraint flags, `RiskDriver` tornado. Stats primitives (`_percentile` NIST rule, `_spearman` via average-rank Pearson, `_sample_triangular` inverse-CDF, `_sample_beta_pert`).
- **SSI path** (ADR-0123, mirrors SSI Tools' add-in): `compute_sra_ssi(schedule, *, config, three_point=None, risks=()) -> SSIResult` (focus-event finish distribution, Gaussian-copula correlation, `RiskFactorTable`/`factor_to_bc_wc`, `ScheduleRisk` additive-days impacts, `_occurrence_schedule` random_each/exact_overall, 5×5 `_prob_rating`/`_consequence_rating`, date-axis realignment to the focus's stored finish). `compute_oat_sensitivity(...) -> tuple[OATSensitivity,...]` deterministic one-at-a-time BC/WC swing (2N solves; validated to reproduce SSI). Documented: std-lib Mersenne-Twister ≠ commercial-tool RNG, so the stochastic distribution is not bit-exact but the BC/WC formula and OAT swing are.

**`sra_conclusions.py`** — plain-language Hulett-style conclusion cards from an `SRAResult`/`SSIResult` (deterministic templates; every digit in a `finding` also in its `evidence`, mirroring the AI citations gate). `conclusions_from_sra(sch, cpm, result)` / `conclusions_from_ssi(sch, result)` → tuple of `Conclusion(topic, severity, finding, meaning, evidence)`: planned-date realism, P50/P80 commitment, contingency, predictability spread, hidden drivers (risk-critical vs plan-critical), top duration drivers, costliest risks, constraint warning, input quality, sampling precision, correlation. `conclusions_as_dicts` for the web payload.

---

### 7. Forecast & margin dashboards

**`forecast.py`** — multi-method "when will it really end?" (M15, ADR-0030). `compute_finish_forecasts(schedule, cpm?) -> ForecastSet` of 4 `FinishForecast`s: CPM logic, as-scheduled (stored dates — surfaces the ADR-0108 progress-aware gap), completion-rate extrapolation, Earned-Schedule IEAC(t) = AT+(PD−ES)/SPI(t). `compute_carnac_summary(schedule, cpm, forecasts) -> CarnacSummary` (PBIX 13 KPI cards). `compute_group_rollup(schedule, field) -> GroupRollup|None` (ADR-0188/0189) — recalculates the project forecast bottom-up from per-group data: group-weighted IEAC(t) and bottleneck completion-rate finish, with credibility-weighted (Bühlmann Z=0 pooled) `EstimatedGroupForecast`s for no-history groups (SEI-discounted, reference-class P25/P75 bounds — quantified, never silent).

**`margin_dashboard.py`** — NASA Margin/Contingency Burn-Down + Margin Erosion Trend (MET). `compute_margin_dashboard(versions, target_uid=None, gold_rule_per_year=30.0) -> MarginDashboard` of `MarginMonth`s (effective margin work-days to the target via zeroed-margin re-solve, margin calendar-days, contingency non-working-days, NASA Gold-Rule requirement `days-to-go×30/365`, %-available/%-effective, below-requirement trigger, carried-forward planned margin). `_erosion` least-squares-fits effective margin vs status date → erosion work-days/month + projected zero-margin date + disclosed R². **F3a/3b (ADR-0230):** `MarginMonth` gains `total_margin_wd` (sum-of-durations, shown alongside effective — the two differ when margin has float), `consumed_pct`, and `corrective_action` (the NASA 50%-consumed threshold, Handbook §7.3.3.1.6 / §7.3.4 — verbatim "the corrective action threshold is set where the margin is 50% consumed"); the dashboard/trend accept the same opt-in `margin_uids` overlay (cross-version union) and the burn-down JS adds a planned-depletion line + corrective caret.

**`msp_filters.py` + `msp_field_resolver.py`** (feature #10 PR-A, ADR-0231) — faithful MS Project **filter evaluation**, semantics taken verbatim from the MPXJ 16.2.0 bytecode. `msp_field_resolver.resolve_field(schedule, task, raw_field, *, field_enum=None) -> ResolvedField(value, kind)` maps a raw MS Project field name (`Text9`, `Actual Finish`, `Duration8`) to a typed task value + `FieldKind`: core scheduling fields (table, no coercion) or custom families via the two-hop label lookup (`Schedule.custom_field_by_raw_name`); source-absent fields (Board Status/Sprint) + row ID → `UNRESOLVED`. `msp_filters.evaluate_filter(schedule, task, filt, prompts=None) -> bool` / `select(...) -> tuple[int,...]` implement the exact operator set (asymmetric LHS/RHS normalization — DATE day-truncate on the field but not the literal, DURATION `None`→0; null-sorts-greater compareTo; three string regimes EQUALS/CONTAINS/CONTAINS_EXACTLY; inclusive order-independent IS_WITHIN; field-to-field; interactive prompts; recursive short-circuit AND/OR; `criteria is None` = match-all). Durations compare on the integer working-minute axis (exact). **Not yet wired into the UI** — PR-C/D do that. Ground truth + build plan: `docs/STATE/MSP-FILTERS-SPEC.md`, `msp-views-leveled.json`, `msp-filters-research/`.

---

### 8. Infrastructure / plumbing

**`cache.py`** — local SQLite cache of parsed schedules + summaries, keyed by **(file content hash, engine version)**. `engine_version()` = content hash of `importers`+`model`+`engine` source, so any code change auto-invalidates (no manual bump; a stale number can never reach the analyst). `ScheduleCache` (WAL, thread-safe short-lived connections, **fails soft** to a miss), `content_hash`, `default_cache_dir` (`$SF_CACHE_DIR` else `~/.cache/schedule-forensics`, outside repo — CUI never committed), `get_default_cache()` (lazy singleton). Serialization is `model_dump_json` (not pickle; bandit-clean). Changes speed, never the answer (test-enforced hit==fresh).

**`summary.py`** — per-version rollup tier (Feature 2). `compute_summary(sch) -> VersionSummary(task_count, status_date_iso, finish_iso, effective_margin_days, dcma_pass, dcma_fail, unsolvable)` (one CPM pass + margin + DCMA-14; never raises — unsolvable network yields a flagged summary). Pure function of the engine → a summary-backed portfolio row equals a full compute.

**`memory.py`** — resident-footprint estimate (Feature 2, warn-not-block). `estimate_schedule_bytes`/`estimate_resident_bytes`/`format_bytes`; `_PER_TASK_BYTES=6144`, `DEFAULT_WARN_BYTES=16 GiB`.

**`projects.py`** — pure grouping of ingested files into Projects (v4 grouped ingestion; no I/O, no metric math). `group_into_projects(records: list[IngestRecord]) -> tuple[Project,...]` — folder uploads → one Project per top folder; loose files grouped by document Title; title-less loose files → own needs-attention Project. `ProjectVersion`s ordered oldest-first by status_date with a file-mtime tiebreak flag (reuses `trend.order_versions` contract).

**`resources.py`** — resource loading & over-allocation (ADR-0125). `compute_resource_loading(schedule, cpm, granularity="month") -> ResourceLoading` — time-phases each assignment's work uniformly across the task's CPM span, buckets by day/week/month, capacity = `max_units × wmpd × working-days-in-bucket`, flags over-allocated buckets, carries per-task contributors (click-a-bar drill). `ResourcePeriod.over_allocated`, `ResourceLoad`, `GRANULARITIES`.

**`__init__.py`** — re-exports the engine's public surface (`compute_cpm`, `CPMResult`/`CPMError`/`TaskTiming`, `datetime_to_offset`/`offset_to_datetime`, `audit_schedule`, `diff_versions`, `compute_driving_slack`/`driving_path`, `analyze_floats`/`summarize_floats`, `detect_manipulation`/`trend_across_versions`, `ancestors_of`/`topo_order`, `recommend`, `compute_quality_trend`/`order_versions`).

---

### Cross-cutting parity/ground-truth ties (summary)

- **Acumen Fuse v8.11.0**: DCMA-14 ribbon, Schedule-Quality §A, §C baseline-compliance/EVM, §E change metrics, HMI/CEI/FEI/BRI, SPI(t)-Acumen, Ribbon — validated against the committed golden Project2/Project5 exports and the Hard_File_updated series (`00_REFERENCE_INTAKE/`, `tests/parity/`, `fuse_exports_2026-06.json`). Formulas pinned to the NASA Acumen metric library ("the Bible", `NASA Metrics_Complete_*.aft`, `tests/engine/test_aft_formula_audit.py`).
- **SSI MS Project add-on**: `driving_slack.py` (783/783, driving path 61/61), `drag.py` (UID-67 export), `sra.py` SSI path (`compute_sra_ssi`/`compute_oat_sensitivity`).
- **DCMA 14-Point / GAO-16-89G / NASA STAT / SMH Rev 2 / PPC Handbook**: `dcma14.py`, `scorecards.py`, `health_extra.py`, `logic_integrity.py`, `constraint_health.py`, `vertical_integration.py`, `float_erosion.py`, driving-slack day-tiers.
- **Hulett / ICEAA INT-02 / GAO / NASA SEM**: `sra.py`, `sra_conclusions.py`, `scorecards.reserve_recommendation`, `margin_dashboard.py`.

No files were modified.

---

## Importers, Model, Web, AI

A read-only inventory of the ingestion, domain-model, web, AI, and top-level-runtime layers of the POLARIS forensic schedule tool at `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment`. Flow: **importer → `Schedule` model → engine → `web/app.py` → server-rendered HTML + vendored JS**, with the AI layer polishing already-computed, cited figures.

---

### 1. `importers/` — native ingestion into the domain model

All parsing is **stdlib-only** (no `requests`/`lxml`; `xml.etree.ElementTree` + `csv`-style splitting), converting each source format's units into the model's canonical axes (integer working minutes, naive local datetimes). Malformed input raises `ImporterError` (a `ValueError` subclass) with CUI-safe messages.

- **`__init__.py`** — re-exports the public surface: `load_schedule`/`load_schedules`, `parse_mspdi`(`_text`), `parse_xer`(`_text`), `parse_json`(`_text`)/`to_json_text`, `parse_mpp`, `decode_xer_bytes`, `supported_extensions`, `MAX_FILES`, `ImporterError`.

- **`loader.py`** — the multi-file dispatch entry point (`/upload` and CLI). `_PARSERS` maps extension → parser (`.mpp`/`.mpt`→`parse_mpp`, `.xml`/`.mspdi`→`parse_mspdi`, `.xer`→`parse_xer`, `.json`→`parse_json`). `load_schedule(path)` dispatches by lower-cased suffix (loud `ImporterError` on unsupported); `load_schedules(paths, max_files=MAX_FILES)` parses a batch preserving order. `MAX_FILES = 100` (docstring history: spec asked 10 → raised to 20 → 100). No cross-version merging — versions are matched later by `unique_id` only.

- **`_common.py`** — shared source-faithful converters used by MSPDI + XER:
  - `parse_datetime` (ISO-8601, pre-1985 sentinel → `None`, strips tz to naive local — mixing aware/naive broke `order_versions`);
  - `iso_duration_to_minutes` (`PnDTnHnMnS`, `Decimal`+`ROUND_HALF_UP`, ISO "D"=24h) and `hours_to_minutes` (XER decimal-hours, sign preserved = lead);
  - `parse_float`/`parse_percent`/`clamped_percent_or_none` (NaN/Inf treated as noise → `None`/clamped);
  - calendar helpers `weekday_from_source` (1=Sun..7=Sat → `date.weekday()`), `clock_minutes`, `working_time_span` (midnight-00:00→1440 handling for 24h calendars), `working_span_minutes`, `dominant_day_minutes` (ADR-0028 single-block model), `excel_serial_to_date` (P6 serial days);
  - `DATE_REQUIRING_CONSTRAINTS` frozenset (SNET/FNET/SNLT/FNLT/MSO/MFO) shared so both importers collapse a dateless date-constraint to ASAP identically.

- **`mspdi.py`** (parity-critical path; `.mpp` routes through here) — parses MS Project XML into `Schedule`. Key points:
  - **Security**: rejects any doc containing `<!DOCTYPE`/`<!ENTITY>` before parsing (XXE / billion-laughs defense, ADR-0008); `_strip_namespaces` drops the MS project ns.
  - Enum code maps: `_CONSTRAINT_BY_CODE`, `_RELATIONSHIP_BY_CODE`, `_RESOURCE_BY_CODE`, `_ELAPSED_DURATION_FORMATS`, `_PERCENT_LAG_FORMATS`.
  - `_parse_task` builds each `Task` (UID required; `is_summary` also true for UID 0; ALAP/dateless-constraint → ASAP normalization). `_stored_slack_minutes` reads `TotalSlack` (÷10, MSP stores tenths-of-minute) into `stored_total_float_minutes`; `_bool_or_none("Critical")` → `stored_is_critical` (Acumen stored-float parity).
  - **Extended attributes / custom fields**: `_parse_extended_attribute_defs` maps `FieldID` → display label (`Alias` else `FieldName`); `_task_custom_fields` emits populated `(label, value)` pairs; `custom_field_labels` on the schedule = fields populated on ≥1 task in declared order.
  - **Calendars**: `_parse_project_calendar` / `_build_calendar` walk the base-calendar chain (cycle-safe), collect holidays (`DayWorking=0`) + extra working days (`DayWorking=1`), intraday `day_segments` (lunch gaps), skipping recurring exceptions (`_exception_range` via `Occurrences`); `parse_calendar_registry` builds the per-task UID→Calendar registry for SSI driving-slack parity (ADR-0117/0118).
  - **Relationships**: `_build_links` (percent-lag resolved against predecessor duration after all tasks parse) then `_in_file_links` drops external/cross-project/self/duplicate links (dedup on `(pred,succ,type)`) and logs a count.
  - `_parse_resources` / `_parse_assignments` (sums work per task+resource, keeps first units, per-assignment `RemainingWork`).

- **`xer.py`** — Primavera P6 tab-delimited (`%T`/`%F`/`%R`/`%E`) parser; fields read **by name**. `decode_xer_bytes` handles UTF-16 BOM → UTF-8 → cp1252. Enum maps `_CONSTRAINT_BY_XER`, `_RELATIONSHIP_BY_XER`, `_RESOURCE_BY_XER`, `_MILESTONE_TYPES`. **Stable identity (ADR-0185)**: `_stable_uid_map` remaps raw `task_id` → `CRC32(task_code) & 0x7FFFFFFF` so cross-version joins survive P6 renumbering — **all-or-nothing** (any missing/dup code or CRC collision falls the whole file back to raw `task_id`). `_parse_task` sets `stored_total_float_minutes` from `total_float_hr_cnt` (D12), `_percent_complete` honors `complete_pct_type` (Phys/Units/Drtn with actual-date override), Activity ID carried as a `custom_fields` `("Activity ID", code)` entry. Costs rolled up via `_costs_by_task` (TASKRSRC + PROJCOST → cost/actual/budget NamedTuple `_TaskCosts`), units-% via `_units_percent_by_task`. Calendar parsed from packed `clndr_data` (`_parse_clndr_data`, regexes `_CLNDR_DAY_RE`/`_CLNDR_SPAN_RE`/`_CLNDR_EXCEPTION_RE`). `_parse_relationships` drops dangling/cross-project/self/dup links (raw-id scope check, then `uid_map` translation), logs a WARNING count (affects DCMA logic-density denominators, D25).

- **`json_schedule.py`** — the tool's own round-trippable format. `parse_json`/`parse_json_text` accept a **friendly** doc (`_from_friendly`) or fall back to strict pydantic `model_validate`. Strict integer parsing (`_int` rejects fractional `unique_id` — D24), naive datetimes (`_dt`). `to_json_text` is **lossless by contract** (a model-introspection guard test fails if a new field lacks a writer): writes the full per-task `calendars` registry, resources, stored float/critical, custom fields, notes, work, costs, dates — everything except runtime `source_file`. `_calendar`/`_calendar_out` round-trip working-day/`day_segments` driving-slack inputs.

- **`mpp_mpxj.py`** — native `.mpp`/`.mpt` has no Python parser, so it shells to the **vendored MPXJ Java runner** (`tools/mpxj`) out-of-process (`java -cp classes:lib/* MpxjToMspdi <in> <out>`), producing MSPDI XML fed to `parse_mspdi_text`. `_find_java` (SF_JAVA → JAVA_HOME → PATH → portable `tools/jre` → user/machine install scans, newest wins); `_mpxj_home` (SF_MPXJ_HOME else walk up to `tools/mpxj`). **Batch JVM optimization**: `mpxj_batch_session()` context manager runs ONE heap-capped `MpxjToMspdi --server` JVM (`_MpxjServer` with a daemon reader thread + tagged `@@SF@@ ` status protocol, `_LazyBatch`, `contextvars`), reused for a whole folder ingest; transparently falls back to per-file `_convert_one_shot` on any server trouble (`_ServerDown`) — identical result either way. Windows-hardened: `CREATE_NO_WINDOW` + `stdin=DEVNULL` to avoid console-window hangs under `pythonw`.

---

### 2. `model/` — frozen, strict, UniqueID-keyed pydantic v2 trust root

Only *source-of-truth* fields; **CPM dates/float/DCMA/EVM are derived by the engine, never stored** (`_base.py` docstring). `SCHEMA_VERSION = "2.8.0"` in `__init__.py` (bumped on any field change; freeze test enforced — 2.7.0 → 2.8.0 with ADR-0234's `Task.priority` / `Task.outline_number` / `Task.stop` group-fidelity fields).

- **`_base.py`** — `StrictFrozenModel(BaseModel)` with `ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)`: immutable+hashable, no coercion, unknown field is an error, CUI kept out of ValidationError text.

- **`task.py`** — `Task`; `unique_id: int` is the **sole cross-version identity**. `ConstraintType` StrEnum; `_HARD_CONSTRAINTS` (MSO/MFO/SNLT/FNLT) for the DCMA hard-constraint check. Durations are integer working minutes (`duration_minutes` ge 0; `remaining_`/`baseline_duration_minutes` optional). Flags: `is_milestone`, `is_summary` (excluded from CPM/DCMA denominators), `is_level_of_effort`, `is_active`, `is_manual` (MSP manually-scheduled, ADR-0034), `is_estimated_duration`, `duration_is_elapsed`. Source-stored Acumen-parity fields: `stored_total_float_minutes`, `stored_is_critical` (`None`=not carried). Optional dates default `None` ("source didn't provide" — never 0). `custom_fields` tuple of `(label,value)` with `custom_field_map`/`custom_field(label)` accessors. Progress **properties** `is_complete`/`is_in_progress`/`is_not_started`/`has_hard_constraint`. `resource_assignments` tuple of `Assignment`.

- **`saved_view.py`** (feature #10 PR-A, ADR-0231) — frozen models mirroring MPXJ's `GenericCriteria` tree: `Criterion` (leaf comparison or `AND`/`OR` branch), `Operand` (literal / field-ref / prompt / null), `SavedFilter` (`criteria: Criterion | None` — `None` = match-all), `SavedGroup` + `GroupClause`. The faithful *shape* of a source definition; the engine (`msp_filters`) owns the semantics.

- **`schedule.py`** — `Schedule`; container with referential-integrity `@model_validator` (unique task/resource UIDs, relationship endpoints must exist → unconstructable if inconsistent). Fields include `project_title` (real Title, distinct from `name`'s filename fallback), `source_file` (citations), `status_date` (absolute ProjectTimeNow for cross-version ordering), `calendar` + `calendars` registry, `custom_field_labels`, and (ADR-0231, #10) `custom_field_by_raw_name` (raw MS Project field name → stored label, the bridge for faithful filter evaluation), `saved_filters`, `saved_groups` (populated from the MPXJ views sidecar since #10 PR-B, ADR-0232). All round-trip through the JSON format (SCHEMA_VERSION 2.8.0). **Caches**: `@cached_property tasks_by_id` / `resources_by_id` return `MappingProxyType` (immutable, frozen model can't go stale); `task_by_id`/`resource_by_id`/`predecessors_of`/`successors_of` helpers. `model_copy` and `__getstate__` **drop these caches** — `MappingProxyType` can't pickle, and the SRA offload pickles the whole Schedule into a worker (2026-07-07 fix).

- **`calendar.py`** — `Calendar`; single contiguous working block per weekday (`working_minutes_per_day` default `MINUTES_PER_DAY`=480), `work_weekdays`, `holidays`, `working_days` (extra worked days), `day_segments` (intraday lunch gaps). `intraday_worked_minutes`, `is_working_day`/`is_worked`/`extra_working_days_in` serve the driving-slack parity path (ADR-0117/0118); broader engine uses the single project calendar (ADR-0028).

- **`resource.py`** / **`assignment.py`** / **`relationship.py`** — `Resource` (UID, `ResourceType` WORK/MATERIAL/COST, `max_units`, `standard_rate`); `Assignment` (resource_id + `work_minutes` + `units` + `remaining_work_minutes` None-vs-0 distinction, Fuse parity ADR-0176); `Relationship` (predecessor/successor by UID, `RelationshipType` FS/SS/FF/SF, `lag_minutes` negative=lead, `@model_validator` rejects self-loops, `is_lead`/`is_lag` props).

- **`units.py`** — the presentation boundary. `MINUTES_PER_DAY=480`. `minutes_to_days`/`days_to_minutes` use `Decimal`+`ROUND_HALF_UP` (never binary float — U3 forensic reproducibility). Formatters `format_days`/`format_signed_days`/`format_minutes_as_days`/`format_percent`/`format_signed_percent`/`ratio_to_percent`. Imports no model layer (so model may depend on it).

Note: there is no separate `resource.py`-vs-`is_active` module — `is_active` is a `Task` field (excluded from CPM/metrics/driving-slack when False).

---

### 3. `web/` — the entire UI in one large FastAPI file plus i18n/help and vendored assets

- **`app.py`** (~15,244 lines; exempt from E501). Imports the whole engine + AI + reports surface at the top (lines 37–285).
  - **`SessionState`** (`@dataclass`, `web/app.py:493`) — in-memory, per-process, no disk persistence: `schedules` (key→Schedule), `file_meta` (folder/mtime for Project grouping), `ai_config`, `flash`, and the **caches** `analyses`/`summaries`/`content_hashes`/`polished`/`backend_cache`/`second_cache`/`translations`. Session-wide state: `active_filter` (tuple of `Criterion`), `target_uid`, `language`, `ram_warn_bytes`, and the full SRA/SSI input set (`sra_risks` `UnifiedRisk` register, factors, overrides, focus). A reentrant `_lock: RLock` makes cache/filter mutations atomic (D18 fixed a live KeyError under concurrent filter+render on the Starlette threadpool).
  - **`_Analysis`** (`app.py:429`, frozen) + **`_compute_analysis(sch)`** (`:447`) — the per-schedule chokepoint: one `compute_cpm` pass threaded into `audit`, `compliance`, `float_bands`, `completion`, `findings`, `narrative` (always the deterministic NullBackend one), `activity_rows`.
  - **`scope`/`analysis_for`/`summary_for`/`ordered`** (`:580`–`:711`) — `scope(sch)` is the single funnel: applies `active_filter` (`filter_schedule`) then, if a `target_uid` is set and present, truncates to that endpoint + its drivers (`subschedule_to_target`), memoized by `id(sch)` and reset on `set_filter`/`set_target`/wipe. `analysis_for(key, sch)` caches `_compute_analysis(scope(sch))`, identity-checked. `summary_for(key, sch)` is the cheap Portfolio tier (finish/margin/DCMA `VersionSummary`), backed by the SQLite cache keyed on `content_hashes` only when unscoped. `ordered()` returns scoped, data-date-ordered versions; `ordered_versions()` returns raw `(key, sch)` pairs; `projects()` groups files into `Project`s via `engine.projects.group_into_projects`. `set_filter`/`set_target` clear `analyses`/`summaries`/`polished`/`_scoped`.
  - **Story spine / nav** (`_Chapter` `:1365`, `_SPINE` `:1383`) — a three-act / twelve-chapter narrative (LOAD → OVERVIEW → ACT I SITUATION → ACT II DIAGNOSIS → ACT III OUTLOOK → SETUP). `@analysis`/`@wbs` routes resolve to the first loaded schedule (`_resolve_route`). `_render_nav` builds the spine + session controls + `_render_target_control` (global Analysis-Target selector: milestone dropdown across versions + any-UID box, posts `/target`, also drives SRA/SSI focus) + theme (four Mission-Ops views) + Size + Language selectors. `_chapter_kicker`/`_story_footer` add the CHAPTER kicker and STORY-SO-FAR progress dashes + Continue→next-chapter footer. `_STORY_ORDER`/`_STORY_CHAPTERS` drive the progression.
  - **`_page(...)`** (`:1747`) renders the bare-jinja `_LAYOUT` (`:320`, `autoescape=False` because body/banner are pre-built HTML; **`title` is escaped at the boundary** to close reflected-XSS from filenames, F-06/ADR-0130), wrapping body with filter/endpoint/sources banners + kicker + explainer + ask panel + story footer. `_bust_static` appends `?v=<pkg version>` to every `/static/` URL (fixed-port upgrade cache-busting).
  - **Routes** (all sync `def`, on the Starlette threadpool) — home/upload/example/download; per-schedule `/analysis`, `/card`, `/wbs`; the twelve chapter pages (`/portfolio`, `/mission`, `/ribbon`, `/integrity`, `/scorecards`, `/path`, `/driving-path`, `/evolution`, `/volatility`, `/trend`, `/curves`, `/cei`, `/performance`, `/evm`, `/resources`, `/forecast`, `/scurve`, `/compare`, `/sra` (+ risk register / SSI / OAT / grid / import-export), `/risks`, `/brief`, `/briefing`, `/margin`, `/workbench`, `/groups`, `/settings`, `/help`); a large `/export/{fmt}/...` family (xlsx/docx/csv via `reports/`); `/api/...` JSON feeds for the charts; and the AI endpoints `/api/ask/{name}`, `/api/ask` (workbook), `/api/driving-path`, `/api/ai/narrative`, `/api/ai/briefing`, `/api/translate`. Session controls `/target`, `/language`, `/session/wipe`, `/session/ram-threshold`; liveness `/api/heartbeat`, `/api/system`, `/api/shutdown`, `/healthz`.
  - **CSP air-gap** (`_CSP` `:1950`, `_SECURITY_HEADERS` `:1957`) — `default-src/connect-src/img-src 'self'` (+`data:` for images) so a page can never fetch/beacon a remote host; `object-src 'none'`, `frame-ancestors 'none'`, `base-uri/form-action 'self'`; `style-src`/`script-src` allow `'unsafe-inline'` (inline `style=` widths + two inline handlers; tightening is a tracked follow-up). Applied to **every** response via the `_liveness` middleware (`:2008`), which also counts in-flight requests so the auto-shutdown watchdog never kills the server mid-import, refreshes the heartbeat, and sets `Cache-Control: no-cache` on `/static/`. Static served from the vendored `_STATIC_DIR` (`app.mount("/static", StaticFiles...)`, `:2006`) — no CDN.
  - **`create_app`** (`:1972`) wires `SessionState`, optional `auto_shutdown`/`idle_grace` browser-gone watchdog, and the lazy `OllamaLauncher`. **`serve`** (`:15211`) refuses a non-loopback host (Law 1), wires graceful shutdown (Quit / `/api/shutdown` / watchdog flip `should_exit`), swallows Ctrl-C.

- **`i18n.py`** — EN/ES/FR/DE/PT. `_TERMS` = `english → {lang: translation}` hand catalog; `CATALOG` derived per language; `LANGUAGES` endonyms. Public: `normalize(lang)`, `catalog_for(lang)` (empty for EN, shipped to client as `SF_I18N`), `translate(text, lang)` (catalog hit else source). The client `static/translate.js` does non-destructive DOM/attribute translation, sending misses to the AI fallback `/api/translate`.

- **`help.py`** — the in-tool metric dictionary. `MetricDoc` dataclass (id/name/definition/formula/source/importance/indicates/threshold/examples/use_case/citation_basis); `METRIC_DICTIONARY` dict; public `metric_doc`, `field_or_metric_doc`, `field_help_payload(keys)`, `reliability_dimension(metric_id)`, `documented_metric_ids`, and **`render_dictionary_markdown()`** which regenerates `docs/METRIC-DICTIONARY.md` (a test enforces sync). A coverage test asserts every engine-emitted metric id has an entry.

- **`static/*.js` + `*.css`** (58 files — 54 JS + 4 CSS, all vendored, `node --check`ed, no bundler/CDN) — CSS: `base.css`/`app.css`/`hud.css` + `sf-themes.css` (four themes: console/daylight/apollo/jarvis, ADR-0195). JS loaded globally in `_LAYOUT`: `theme.js`, `translate.js`, `drilldown.js`, `taskinfo.js`, `gantt.js`, `timescale.js`, `persist.js`, `a11y.js`, `heartbeat.js`, `chartframe.js` (the shared chart frame — fullscreen/zoom toolbar, one hover call-out for the whole app, air-gap-safe), `globe.js`/`sysmon.js` (local telemetry HUD), `hints.js`/`vizhints.js`, `story.js`; plus per-page chart modules (`trend.js`, `sra*.js`, `path*.js`, `curves.js`, `scurve.js`, `cei.js`, `evolution`/`volatility`, `ask.js`, `ai_polish.js`, etc.). Every data visual is expected to honor the chart contract (headline/axes/legend/DD line/hover/provenance/toolbar) per `docs/DESIGN-SYSTEM.md`.

- **`web/system.py`** / **`web/offload.py`** — local machine telemetry snapshot (optional psutil/nvidia-smi, `/proc`, no network) for the HUD; and the SRA Monte-Carlo worker-process offload (`run_maybe_offloaded`, `OFFLOAD_TASK_THRESHOLD`, `shutdown_offload`).

---

### 4. `ai/` — pluggable local AI, CUI fail-closed, every figure re-verified against engine citations

- **`backend.py`** — the `AIBackend` `Protocol` (`name`, `is_local`, `is_available`, `list_models`, `pull_model`, `generate`). `AIConfig` (frozen dataclass): `classification` (default CLASSIFIED), `backend` (default `"ollama"`, model `qwen2.5:7b-instruct`, endpoint `127.0.0.1:11434`), `qa_mode` (`annotate` default | `strict` | `interpretive`, ADR-0129), OpenAI-compat endpoint, dual-model `second_backend`/`second_model`, `gen_timeout` (default 3600s). Deterministic decoding constants (`temperature 0`, `seed 0`, `top_p 1`). `Classification` StrEnum. **`route_backend`** is the fail-closed gate: CLASSIFIED → only a **local** backend (ollama/openai when available, else Null); cloud only when UNCLASSIFIED + `backend=="cloud"` + a cloud backend supplied, and then behind a `Banner` naming the endpoint. Anything ambiguous → Null + local banner (never auto-cloud). `banner_for` mirrors the intent banner.

- **`null.py`** — `NullBackend`: deterministic offline default, always available, `generate` returns the prompt **unchanged** (the already-cited engine text emitted verbatim). Fail-closed target of `route_backend`.

- **`ollama.py`** / **`openai_compat.py`** — the two LOCAL backends over **stdlib `urllib` only** (net_guard forbids `requests`/`httpx`). Both **loopback-validate the endpoint at construction** (`is_local_http_endpoint`, else `CUIEgressError`). A shared no-redirect / no-proxy opener (`_NoRedirect`, empty `ProxyHandler`) refuses any 3xx bounce and skips the system/corporate proxy so a CUI request body can never leave the box. `OllamaBackend` (`/api/tags`, `/api/generate`, `/api/pull`, deterministic options, bounded probe timeout); `OpenAICompatBackend` (`/v1/models`, `/v1/chat/completions`, LM Studio/llamafile/vLLM, no pull). `probe_error_text` for settings diagnostics.

- **`ollama_process.py`** — `OllamaLauncher`: optionally starts a local `ollama serve` **lazily** (only when the operator enables Ollama in AI Settings) and stops it on exit **only if we started it**; loopback-pinned `OLLAMA_HOST`, never `ollama pull` (no network). All process I/O injectable for tests.

- **`citations.py`** — the citation-enforcement core. `CitedStatement` (text + `Citation` tuple, `rendered()` appends compact tag) and `Narrative`. `assert_all_cited` (hard gate — `UncitedStatementError` if any fact lacks a citation). `figure_tokens`/`_TOKEN_RE` — the single figure tokenizer (ISO dates as **whole** tokens so month/day fragments can't become derivation operands, D1; sign-aware, M6). `preserves_figures` (multiset equality of figures) and `introduces_loaded_terms` (`_LOADED_TERMS`: fraud/deliberate/concealed/... — rejects a rephrase that injects an accusation the engine never made, ADR-0132/H2). `reattach(texts, sources)` carries the engine's citations onto model prose and keeps the rephrase **only** if non-empty ∧ figure-preserving ∧ no introduced loaded term, else falls back to the verbatim engine sentence; re-verifies coverage.

- **`narrative.py`** — `build_narrative(current, prior, target_uid, backend, ...)`: assembles cited statements from `recommend` findings + `detect_manipulation` (vs prior), `_clean_bill` for a well-formed schedule (always cited — falls back to finish drivers → first rows → the file itself). A live model rephrases via `polish_prompt`/`clean_polish` (instruction-wrapped, D17); Null backend emits verbatim; `reattach` re-verifies either way.

- **`qa.py`** — Ask-the-AI grounded Q&A (the largest AI module, ~909 lines). Builds cited **fact sheets** entirely from engine output: `build_fact_sheet` (single schedule: frame, finish-driving concentration, forecasts, DCMA checks + 14-point pass rate, findings, float bands, completion performance), `build_workbook_fact_sheet` (across every version, reusing the briefing), `manipulation_forensics_facts` (cross-version "what was changed to keep UID X from slipping" — path duration shortenings, path counterfactual, per-change `compute_change_effects`, ADR-0150/0162). `relevant_facts` (what the analyst is shown; stem overlap + `_INTENT_ALIAS`) vs `model_evidence` (fuller cited picture for a live model). **`answer_question(backend, facts, question, mode)`** is the mode-gated, **role-aware figure gate** (F-11/ADR-0137, hardened ADR-0138): `_figure_roles` splits **value** figures (tokens outside every cited name/`UID n` span) from **identifier** figures (name/UID digits), collision-safe; `_classify_figures` returns verified derivations / identifier-reused / unverified / unit-misused, checking identifiers **before** derivation (no laundering, D4), span-based (D6), with the ADR-0145 unit-role step (`_unit_role`, `_PCT_UNIT_RE`/`_PLAIN_UNIT_RE`). `strict` discards any answer with an unsourced/re-roled/unit-contradicting figure or non-ratio derivation; `annotate` keeps it with `[AI-derived]`/`[Derived]`/`[role]`/`[unit]` footers; `interpretive` returns verbatim, ungated. `figure_agreement` is the deterministic dual-model cross-check (footers stripped).

- **`derivation.py`** — Layer B verified reconstruction. `verify_derivation(target, sourced)` reconstructs a model-emitted number from the cited **values** over a closed whitelist (percent-of, percent-change, ratio, difference, sum) in priority order; **integer targets must reconstruct exactly** (`_EXACT_EPS`), decimals at 1 dp; `RATIO_KINDS` are the only ones strict mode trusts; operands capped (`_MAX_OPERANDS=64`, D23). Returns a `Derivation` (value/kind/expression).

- **`driving_facts.py`** — when a question names a UID with driving/path/slack intent (`_UID_RE`, `_INTENT`), runs the exact engine (`compute_driving_slack`/`driving_path`) and injects the answer as cited facts so the small model narrates rather than attempts multi-hop traversal; the citation figure-gate discards any wrong count.

- **`briefing.py`** / **`brief.py`** — the leadership-facing Executive Briefing (7 numbered sections, `BriefingSection`/`BriefingTable`, every figure engine-computed + cited, model may only rephrase via `reattach`) and the Diagnostic Brief (outliers/conflicts/questions narrative + Word export via `reports/docx`). Both consumed by `web/app.py` routes and the workbook fact sheet.

---

### 5. `exhibits/` + top-level runtime

- **`exhibits/`** — the critical-path-volatility exhibit pack (ADR-0184). `payload.py` is the pydantic-v2 **contract** (`ExhibitPayload` + `RunManifest`/`FileEntry`/`TaskUpdateCell`/`TaskSummary`/`UpdateSummary`/`Transition`; `canonical_json` sort-keys/compact so embedded/static/CLI outputs are byte-identical; `run_id_for` = sha256 with no timestamps). One builder feeds three consumers — the static pack (`render_svg.py` + `report_html.py` + `csvout.py`, all stdlib), the interactive `volatility.js`, and the headless CLI `cli.py` (`schedule-forensics-report`, deterministic, documented exit codes). **The CP-basis engine artifacts (CIC, τ-b, null-model churn, recompute deltas) do NOT exist in the engine yet** — renderers are developed against golden fixture payloads and live wiring is parked (`audit/PARK-LIST.md`); `--inputs` runs exit 4 until it lands. No engine output is fabricated.

- **`launcher.py`** — console entry point `schedule-forensics` / `main()`. Picks a free **loopback** port (`find_free_port`), refuses non-loopback hosts (Law 1), `_ensure_streams()` rebinds `stdout`/`stderr` to devnull under windowless `pythonw` (never a log file — CUI off disk), lazily manages Ollama, serves `create_app(auto_shutdown=True)` and opens the browser on a timer. `multiprocessing.freeze_support()` for PyInstaller + the SRA offload worker.

- **`net_guard.py`** — the Law-1 egress guard. `FORBIDDEN_RUNTIME_DISTRIBUTIONS` (requests/httpx/aiohttp/urllib3/websockets/... + cloud SDKs openai/anthropic/boto3/...) and `FORBIDDEN_CLOUD_MODULES`. `assert_local_only()` (called on startup + the §7 acceptance test) raises `CUIEgressError` if any forbidden distribution is a **declared runtime dependency** or any cloud SDK is importable. `is_loopback_host` and `is_local_http_endpoint` (scheme **and** host must be local-HTTP — closes `file://localhost`/`gopher://` gaps) are the predicates every local-AI backend and the launcher/serve use.

**Cross-cutting invariants observed everywhere:** `unique_id` is the only cross-version key; durations are integer working minutes with `Decimal` rounding only at the presentation boundary; models are frozen/strict/closed with engine-derived analytics never persisted; the AI is loopback-only, fail-closed, and never emits a figure the engine didn't compute (in narrative/briefing and strict/annotate Q&A); and no schedule content is logged (paths/counts only).

Relevant files (all under `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment/src/schedule_forensics/`): `importers/{__init__,loader,_common,mspdi,xer,json_schedule,mpp_mpxj}.py`; `model/{_base,task,schedule,calendar,resource,assignment,relationship,units,__init__}.py`; `web/{app,i18n,help,system,offload}.py` + `web/static/*` + `web/examples/house_build.json`; `ai/{backend,null,ollama,openai_compat,ollama_process,citations,narrative,qa,derivation,driving_facts,briefing,brief,__init__}.py`; `exhibits/{__init__,payload,cli,csvout,render_svg,report_html}.py`; `launcher.py`; `net_guard.py`.

---

## Tests & Fixtures

The suite lives entirely under `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment/tests/`, is built test-first (TDD; `docs/PLAN/RTM.md` is the requirement→test map), and is configured in `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths=["tests"]`, `addopts="-ra --strict-markers --strict-config"`, a single custom marker `parity`, and one upstream warning filter (starlette's `TestClient` importing `httpx`). Coverage (`[tool.coverage.run]` branch-mode, `source=["schedule_forensics"]`) is CI-enforced only — overall `>=70` (`--cov-fail-under=70`) and engine `>=85` (`coverage report --include='*/engine/*' --fail-under=85`); a plain local `pytest -q` collects no coverage. `pyproject.toml` `fail_under=70.0` mirrors the CI overall floor.

### Directory structure and what each area covers

Test-file counts by area (files named `test_*.py`):

| Area | Path | # files | Coverage |
|---|---|---|---|
| Engine (core) | `tests/engine/` | 63 | CPM solver, driving slack/path, drag, trend, diff, manipulation, recommendations, SRA, forecasting, float analysis/erosion, bow-wave, path evolution/counterfactual, scorecards, plus the reference/audit tests below |
| Engine metrics | `tests/engine/metrics/` | 17 | one file per metric family: `dcma14`, `cei`, `hmi`, `fei_bri`, `float_ratio`, `float_bands`, `schedule_quality`, `evm`, `completion_performance`, `margin`, `wbs_breakdown`, `change_metrics`, `field_forecast`, `derived`, `health_extra`, `performance_summary`, `schedule_card` |
| Web/UI | `tests/web/` | 110 | the single-file FastAPI app (`web/app.py`) — every route/page/panel, chart contract, drill tables, i18n, air-gap/CSP (route+asset walk enumerated from `app.routes`/disk), startup Law-1 wiring (`test_startup_guards.py`), upload resilience & caching, single-compute chokepoint, accessibility, themes, SRA views, export endpoints; JS harnesses under `tests/web/js/*.mjs` run through `node` |
| Importers | `tests/importers/` | 10 | `mspdi`, `xer`, `json_schedule`, common intake, MPXJ `.mpp` path, loader dispatch, inactive-baseline handling, golden parity-input parse |
| AI | `tests/ai/` | 14 | `AIBackend` protocol + Null/Ollama/OpenAICompat backends, citation reattachment (figure-preservation gate), narrative/briefing/translation, Ask-the-AI Q&A modes (strict/annotate/interpretive), derivation, driving/manipulation facts, Ollama process mgmt |
| Parity gate | `tests/parity/` | 6 | the `pytest -m parity` acceptance gate (details below) |
| Guards | `tests/guards/` | 3 | egress/local-only, endpoint-scheme, pre-commit CUI blocklist |
| Installer | `tests/installer/` | 1 | the nine one-file installers + wheel lockstep (details below) |
| Model | `tests/model/` | 7 | frozen pydantic `Task`/`Schedule`/`Calendar`/`Resource`/`Relationship`, schema-freeze, pickle round-trip |
| Exhibits | `tests/exhibits/` | 3 | the exhibits render/CLI layer, an SSI-token-ambiguity lint gate, and the `schedule-forensics-report` CLI's Law-1 startup guards (`test_cli_guards.py`) |
| Reports | `tests/reports/` | 1 | export endpoints/report generation |
| Test-project battery | `tests/test_projects/` | 1 | the synthetic TP1–TP4 battery pinned to its generator |
| Top-level | `tests/` | 9 | `test_smoke.py` (layer imports), `test_units.py` (minutes↔days boundary), `test_launcher.py`, `test_packaging.py`, `test_logging_redaction.py`, `test_windowless_subprocess.py`, `test_coverage_misc.py`, `test_parity_report_sync.py`, `test_state_docs.py` |

Notable individual engine tests: `test_aft_formula_audit.py` (definitional check of `web/help.py` formulas vs the NASA `.aft` "Bible"), `test_chain_acumen_reference.py` (Project5 anchored to the 2345 Metric History Report), `test_evm_acumen_reference.py` (EVM1/EVM2 forward-looking validation, deliberately **not** `parity`-marked), `test_fuse_reference.py`, `test_ssi_leveled_uid152.py`, `test_metric_catalog.py`, `test_cpm_stored_dates.py`, `test_cpm_date_equivalence.py`.

### `tests/fixtures/` layout

`tests/fixtures/.gitkeep` plus:
- `mspdi/commercial_construction.xml`, `xer/commercial_construction.xer` — synthetic small samples used by `importers/test_mspdi.py`, `test_xer.py`, `test_loader.py`, `web/test_adr0188_batch.py`.
- `test_projects/TP1_Library_Progressed.xml`, `TP2_Bridge_4x10_Calendar.xml`, `TP3_Outage_DCMA_Seeded.xml`, `TP4_DataCenter_v1…v5.xml` — the deterministic synthetic battery, regenerated byte-identically by `tools/make_test_projects.py`; `test_projects/test_battery.py::test_generator_is_deterministic_and_matches_the_committed_fixtures` asserts the generator reproduces them exactly. Their expected numbers double as the operator manifest `docs/TEST-PROJECTS.md`. Also consumed by `ai/test_brief.py`, `engine/test_data_date_finish_gap.py`, `engine/test_ribbon.py`, `engine/test_fuse_reference.py`.
- `exhibits/fixtures/payload_small.json` — golden payload for the exhibits render/determinism/air-gap/CLI tests.
- `golden/` — the parity oracles (below).

Per the historical `tests/README.md`, `tests/fixtures/` is the only place a schedule-format file may live (`.gitignore` re-allows the blocked extensions only there). Note this README predates ADR-0151/0152, which additionally committed the non-CUI reference intake suite under `00_REFERENCE_INTAKE/`; the golden fixtures themselves are the synthetic/anonymized MSPDI conversions.

### `tests/fixtures/golden/` — every golden set

Each golden set holds a schedule fixture (plain `.mspdi.xml`, or gzipped `.mspdi.xml.gz` for the large ones) plus a `case.json` carrying the transcribed reference values, provenance (`_source`), and documented deltas/divergences.

**`golden/project2_5/`** — the primary Acumen Fuse oracle.
- Files: `Project2.mspdi.xml` (711 KB), `Project5.mspdi.xml` (750 KB), `case.json`, `fuse_exports_2026-06.json`.
- Provenance: the non-CUI "Commercial Construction" sample (ADR-0003/0005), 145 rows = UID-0 project summary + 144 activities (UID 2–145, UID 1 absent). Project5 was refreshed to the authoritative `Project5_TAMPERED.mpp` (ADR-0112, 4 stored-critical, superseding a stale 37-critical capture).
- `case.json` holds per-project denominators, `schedule_quality`, `dcma14`, `baseline_compliance`, `cei`, and the `change_P2_to_P5` block, with a `_deltas`/`_scores_deferred` section documenting the stored-vs-pure-CPM residuals (e.g. missing-logic scope, SN01 header count, net-finish-impact basis).
- `fuse_exports_2026-06.json` is the verbatim ENGINE==FUSE transcription (keys: `Project2`, `Project5`, `change_P2_to_P5`, `_documented_divergences`) from the operator-delivered Fuse v8.11.0 suite (Metric History / DCMA / Detailed / Quick Add + two Forensic Analysis Reports), each value drawn from ≥2 independent places (ADR-0151).
- Gated by: `parity/test_parity_gate.py` (schedule-quality, DCMA-14, baseline-compliance, change-metrics, net-finish-impact, SSI driving slack/drag), `parity/test_fuse_export_parity.py` (the ENGINE==FUSE §A/§B/§C/§E gate incl. the 96↔99 no-longer-critical swap and the −148 vs −134 net-finish reconciliation), `importers/test_golden_parity_inputs.py` (parse validation), `test_parity_report_sync.py` (pins `docs/PARITY-REPORT.md` headline numbers to `case.json`), plus `conftest.py`'s session-scoped `golden`/`golden_project2`/`golden_project5` fixtures reuse these two files across the whole suite.

**`golden/ssi_uid67/`** — SSI driving-path + drag oracle, focus UID 67 "Pour roof slab" on Project5_TAMPERED.
- File: `case.json` only (reuses `project2_5/Project5.mspdi.xml`).
- Provenance: SSI Directional Path Tool export (Predecessors; Driving Slack ≤ 0d; Waterfall), delivered 2026-07-08 (park-list A-5). 20-task Path-01, all at 0 driving slack, plus a gated `ssi_drag_days_by_uid`.
- Gated by: `parity/test_parity_gate.py::test_ssi_driving_slack_uid67_exact` (membership + path order + tiers, UID-exact) and `test_ssi_drag_exact` (Devaux DRAG reproduces all 20 SSI drag values, incl. remaining-duration cap on in-progress UID 35 and zero-drag parallel pairs).

**`golden/ssi_uid145/`** — SSI "get all dependencies" oracle, focus UID 145 "Issue final request for payment".
- File: `case.json` only (reuses Project5).
- Provenance: SSI Directional Path Tool "Get all dependencies" export (108 UIDs), re-pinning SSI parity on the authoritative file after ADR-0112 (ADR-0115). Includes `tier_counts_default_bands` (DRIVING 2 / SECONDARY 3 / TERTIARY 8 / BEYOND 95) and full working-day slack per UID.
- Gated by: `parity/test_parity_gate.py::test_ssi_driving_slack_uid145_exact` (exact set, integer driving-slack days per UID, whole-day check, tier band counts, path 144→145).

**`golden/ssi_uid152/`** — SSI large-scale oracle, focus UID 152 on the operator's master IMS.
- Files: `Large_Test_File.mspdi.xml.gz` (696 KB gz), `case.json`.
- Provenance: SSI Directional Path Tool export for "USA OTB Master IMS" (2,126 tasks, progressed + resource-leveled), delivered 2026-07-08 (needs-list A-4); task names anonymized in the source. 76-task Path-01 all at 0 days; a `ssi_drag_days_by_uid_provenance_only` block is recorded but deliberately NOT gated (ADR-0158 — the 0.5-day near-path convention the engine reads as 1.0d).
- Gated by: `parity/test_parity_gate.py::test_ssi_driving_slack_uid152_exact` (membership + per-UID days, zero mismatches).

**`golden/ssi_uid152_leveled/`** — SSI leveled-file oracle, focus UID 152.
- Files: `Large_Test_File_Leveled.mspdi.xml.gz` (774 KB gz), `case.json`.
- Provenance: SSI Directional Path Tool exports for "Large Test File Leveled.mpp" delivered 2026-07-14, settings Predecessors + Ignore-constraints ON + Ignore-leveling-delay ON, near-path bands parent+10/20d; Drag not computed. Carries `critical_path_01_slack_by_uid` (60 tasks), secondary/tertiary path UID lists, and `all_dependencies_driving_slack_by_uid` (783 tasks).
- Gated by: `engine/test_ssi_leveled_uid152.py` (both tests `parity`-marked): critical path (60 tasks, all 0-day) UID-exact, and the full 783-task driving set membership exact with slack magnitudes ≥775/783 exact and worst-case ≤1.01d (documented calendar-handoff rounding).

**`golden/fuse_hardfile/`** — second ENGINE==FUSE oracle (Hard_File series).
- Files: `Hard_File.mspdi.xml.gz`, `Hard_File_updated.mspdi.xml.gz`, `Hard_File_updated2…3.mspdi.xml.gz`, `Hard_File_updated3_24hr.mspdi.xml.gz`, `case.json`.
- Provenance: Acumen Fuse v8.11.0 export suite for Hard_File.mpp + four progressive updates (deliveries 2026-07-08 / 07-09, ADR-0159/0176), transcribed verbatim from the Metric History / Detailed Metric / Forensic Analysis reports; the gz files are MPXJ-converted MSPDI of the intake `.mpp` (anonymized business-process task names, non-CUI). Uniquely covers an elapsed in-progress activity (needs-list D7: Normal-Tasks-To-Go-In-Progress 0→1). `case.json` carries per-snapshot `exact` metric blocks, `fuse_values` (BEI, SPI(t)), `fuse_uid_sets` (invalid-forecast-dates, critical-path splits, negative-float, missing-logic), `_documented_divergences` (negative-float 34/33 vs 0/0, missing-logic 10 vs 8, duration-0, superset 187/400/412), and `forensic_changes` (cost/work/resource change UID sets).
- Gated by: `parity/test_fuse_hardfile_parity.py` (exact metrics UID-for-count; elapsed-in-progress; updated-series UID-exact critical/DCMA09/negative-float sets + BEI/SPI(t) values; missing-logic superset divergence exact; Fuse Forensic change-tracker UID-exact incl. the resources sheet). The `_24hr` variant is exercised by `importers/test_mspdi.py`.

**`golden/ssi_hardfile_uid155/`** — SSI driving-path oracle on the Hard_File series, focus UID 155.
- File: `case.json` only (reuses the `fuse_hardfile/*.gz` schedules, ADR-0159).
- Provenance: SSI Directional Path "get all dependencies" exports (2026-07-08, backlog #67) for base + updated. Strict 9-task Path-01 with ordered chain 141→156→36→9→144→145→146→411→155; `ssi_drag_days_by_uid_provenance_only` recorded, NOT gated.
- Gated by: `parity/test_ssi_hardfile_uid155.py` (strict 0-day set == SSI Path 01 UID-for-UID on both snapshots, ordered chain, tier DRIVING, whole-day zeros).

**`golden/evm/`** — cost-loaded EVM reference.
- Files: `EVM1.mspdi.xml` (85 KB), `EVM2.mspdi.xml` (93 KB).
- Provenance: operator-supplied (non-CUI) cost-loaded schedules exported from Acumen Fuse, statuses 2012-09-01 / 2012-09-12; 14 Acumen activities (11 tasks/milestones + 3 summaries, root excluded).
- Gated by: `engine/test_evm_acumen_reference.py` (deliberately **not** `parity`-marked — a forward-looking harness green on the confirmed metrics, documenting residuals awaiting a faithful MS Project progress-scheduler) and referenced by `engine/test_aft_formula_audit.py`.

### The parity gate (`pytest -m parity`)

The `parity` marker (declared in `pyproject.toml`, enforced by `--strict-markers`) is the §6.B acceptance gate: the engine's numbers must match Acumen Fuse v8.11.0 and the SSI MS Project add-on on the committed golden fixtures, matched by **UniqueID only**. Modules carrying `pytestmark = pytest.mark.parity` are `tests/parity/test_parity_gate.py` (the consolidated golden re-assertion), `test_fuse_export_parity.py`, `test_fuse_hardfile_parity.py`, `test_ssi_hardfile_uid155.py`, plus the two `parity`-marked tests in `engine/test_ssi_leveled_uid152.py` and the `parity`-decorated `test_ssi_drag_exact`. Two assertion classes: **exact** (engine == golden, the majority) and **documented residual** (engine asserted at its intended value AND the delta to the golden asserted to be exactly what `case.json._deltas` / the ADRs record — so a residual silently changing fails the gate, and closing one forces the golden assertion to tighten). This encodes Law 2 (fidelity over speed): divergences are asserted exactly, never force-matched.

### The egress guard (`tests/guards/test_egress.py`)

The §7/Law-1 local-only acceptance check over `schedule_forensics.net_guard`. It asserts the shipped package declares no forbidden remote-HTTP/cloud runtime dependency (`forbidden_runtime_dependencies() == set()`), no cloud SDK is importable (`importable_cloud_sdks() == set()`), and `assert_local_only()` passes clean; then it monkeypatches a fake `requests` dependency and a fake `openai` importable spec to prove `assert_local_only()` raises `CUIEgressError`. It also unit-tests requirement parsing (drops `extra`-gated dev deps, skips blank specs, handles absent metadata) and the loopback-host classifier (`127.0.0.1`/`localhost`/`::1` allowed; `8.8.8.8`, `example.com`, `10.0.0.5`, `0.0.0.0`, `::`, empty rejected). Its sibling `test_endpoint_scheme.py` extends this to the AI backends — `is_local_http_endpoint` must reject loopback-host-but-wrong-scheme URLs (`file://localhost/…`, `ftp://`, `gopher://`, `data:`), `OllamaBackend`/`OpenAICompatBackend` constructors raise `CUIEgressError` on them, and the stdlib opener refuses to follow redirects (`_NoRedirect`). `test_airgap.py` (in `tests/web/`) closes the loop at the served-page level: no absolute/protocol-relative/remote-asset references in any HTML page or static asset, a CSP with `default-src 'self'`/`connect-src 'self'`/`frame-ancestors 'none'` + nosniff/no-referrer/frame-deny headers, and all script/style refs same-origin `/static/`.

### The state-docs drift guard (`tests/test_state_docs.py`)

Pins the durable state to the ADR record. `_latest_adr_number()` scans `docs/adr/NNNN-*.md` for the highest sequence number; `test_handoff_references_latest_adr` asserts token `ADR-{latest:04d}` appears in `docs/STATE/HANDOFF.md`, and `test_session_log_references_latest_adr` asserts it also appears in `docs/STATE/SESSION-LOG.md`. So any change that adds an ADR must refresh both durable docs in the same commit — the guard exists because the handoff once stopped at ADR-0046/PR#102 while `main` had merged through ADR-0057/#113, resuming a session from a stale map.

### The installer lockstep test (`tests/installer/test_installers.py`)

Structural verification of the nine one-file installers (3 tiers × 3 OS families `ps1`/`sh`/`command`); `pwsh` isn't in the build container, so true Windows execution runs in `.github/workflows/installer-smoke.yml`. It checks: all tier/OS files exist with the specced configs (tier1 16 GB/no-GPU/llama3.2:3b, tier2 64/GPU/llama3.1:8b, tier3 128/GPU/llama3.3:70b); each OS family's body is byte-identical across tiers apart from the config block (no tier drift); the base64-embedded wheel decodes to a CRC-valid zip matching the `pyproject.toml` version and carrying ≥30 `web/static/` assets + a bundled example (the packaging gap the first end-to-end run caught); all three families embed the same wheel; installer Start/Stop wiring targets real launcher/`/api/shutdown` surfaces; no CUI/secret-shaped strings in the installer heads. The **lockstep** test `test_embedded_wheel_is_in_lockstep_with_the_source_tree` (ADR-0148) extracts every `schedule_forensics/**` file from the embedded wheel and compares it byte-for-byte against `src/schedule_forensics/**` in both directions (nothing drifted, nothing missing, `compared > 50`) — so any source change to a packaged file fails until the wheel + installers are regenerated (the "stuck-overlay" incident where a merged home.js fix shipped an hours-old wheel while the version check passed). Further tests pin PowerShell `Find-Python` array-safety (ADR-0191), no-admin Java/Python install (ADR-0192), and MPXJ deployment + single self-stopping icon (ADR-0193).

### conftest fixtures (`tests/conftest.py`)

Two mechanisms. (1) An **autouse** `_isolate_schedule_cache` fixture points `$SF_CACHE_DIR` at a per-test `tmp_path` dir and resets `schedule_forensics.engine.cache._DEFAULT_CACHE = None`, so every test gets an empty SQLite schedule cache — a test never reads/writes the operator's real `~/.cache/schedule-forensics`, cached bytes can't leak between tests, and a test that monkeypatches a parser to fail still re-parses. (2) **Session-scoped golden loaders**: `_load_golden` (`@cache`) parses `fixtures/golden/project2_5/{name}.mspdi.xml` at most once; exposed as the `golden` callable (`golden("Project5")`, for parametrized cases) and the named `golden_project2` / `golden_project5` fixtures. Because parsed `Schedule` objects are frozen/immutable, one parse of the ~16k-line MSPDI goldens is safely shared across the whole session (they were formerly re-parsed dozens of times). Individual modules layer their own module-scoped loaders (e.g. `importers/test_golden_parity_inputs.py`, `engine/test_evm_acumen_reference.py`) and `@cache`d gz-decompressors (`engine/test_ssi_leveled_uid152.py`).

---

## Docs, ADRs & Config

Read-only inventory of the documentation and project-configuration surface of the forensic schedule tool at `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment`. Nothing was edited.

---

### `README.md`

Public-facing overview. Declares the tool **built (M1–M17 complete)**, running end-to-end (ingest → CPM/forensic analysis → locally-rendered interactive report → cited local-AI narrative). Product is branded **POLARIS** (*Program Oversight & Logic Analysis for Risk & Integrity of Schedules*) in the running UI; the word "NASA" never appears in-app. Restates the **two laws** (data sovereignty / fidelity over speed). Documents install (`pip install -e .` → `schedule-forensics` launcher; Python 3.11+, optional Java 17+ for `.mpp`, optional Ollama for AI), launch (binds a free 127.0.0.1 port, opens browser, watchdog auto-shutdown ~10 min), and a 12-chapter "Mission Ops" report walkthrough (Import → Mission Control → Act I Situation → Act II Diagnosis → Act III Outlook), plus Path Analysis, Trend, Bow Wave/CEI, Forecast, Executive Briefing, Compare, Risk Analysis (SRA), Metric Workbench, and four themes. Points at `docs/STATE/HANDOFF.md` as the live source of truth and `00_REFERENCE_INTAKE/` as the committed non-CUI parity suite. Runtime is standard-library-only for I/O; the only runtime deps are pydantic, FastAPI, plain uvicorn, Jinja2, python-multipart.

---

### `CLAUDE.md` (project instructions)

**The two non-negotiable laws.**
1. **Data sovereignty (CUI).** No schedule content or derived metric leaves the machine; the AI is loopback-only and fails closed. Never commit real CUI (`.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx`). Key nuance (operator-confirmed CUI boundary): the *build/reference* inputs (`Large_Test_File.mpp`, SSI/Acumen exports, the NASA `.aft` metric library, golden inputs) are **NOT CUI** and, per ADR-0151/0152, are committed under `00_REFERENCE_INTAKE/`. Real CUI is only ever the operator's production schedules in the deployed local tool. The pre-commit guard blocks blocked-extension files everywhere except the `tests/fixtures/` synthetic allowlist and a blob byte-identical to `origin/main` (the `inherited_from_main` exception). Runtime I/O is std-lib only; a net-egress guard fails the build if a forbidden HTTP client enters the runtime, and an air-gap test fails if a served page references a remote asset.
2. **Fidelity over speed.** Numbers must match the reference tools (Acumen Fuse v8.11.0, SSI, MS Project) on the same inputs; parity is gate-locked (`pytest -m parity`).

**Commands (full gate, run before every commit):** `ruff check src/ tests/`; `ruff format --check .`; `python -m mypy src/` (strict); `bandit -q -r src` (only non-zero exit is failure); `python -m pytest -q` (CI-enforced coverage gates: engine ≥85%, overall ≥70%); `node --check src/schedule_forensics/web/static/*.js`. Parity-only: `python -m pytest -m parity`. Run app: `schedule-forensics`. `.mpp`→MSPDI via vendored MPXJ (Java). `web/app.py` is exempt from E501.

**Architecture (the big picture).** Flow: **importer → `Schedule` model → engine (CPM + metrics) → `web/app.py` (FastAPI) → server-rendered HTML + vendored JS charts**, with the AI layer polishing narrative over already-computed figures.
- `model/` — frozen pydantic models; `Task.unique_id` is the sole cross-version identity; durations are integer working minutes (480 = 1 day); CPM dates/float derived by the engine, never stored; optional fields default to `None` ("source didn't provide it").
- `engine/` — `cpm.py` (→`CPMResult`); `metrics/` (one module per family, each returning frozen `MetricResult`); `trend.py`, `grouping.py`, `driving_slack`, `manipulation`, `recommendations`. `_common.effective_total_float`/`is_effective_critical` prefer the source tool's stored, progress-aware Total Slack/Critical flag over recomputed CPM float (Acumen parity).
- `importers/` — `mspdi` (richest), `xer`, `json_schedule`; native `.mpp` has no Python parser (converted via vendored MPXJ/Java).
- `ai/` — `AIBackend` protocol; `NullBackend` (deterministic default), `OllamaBackend`, `OpenAICompatBackend` (both loopback-validated at construction; `route_backend` fails closed to Null). Narrative/briefing/translation re-verify every AI-emitted figure against engine citations (figure-preservation + accusatory-term rejection). Ask-the-AI Q&A is operator-mode-gated (strict/annotate/interpretive), with a role-aware value-vs-identifier figure split (ADR-0137/0138) and a unit-role semantic check (ADR-0145).
- `web/app.py` — the entire UI in one large file (routes + server-rendered HTML + Jinja layout); `SessionState` per-process session; `_compute_analysis`/`analysis_for` single-CPM-pass chokepoint; session-wide filter funnels through `SessionState.scope()`. Static JS/CSS vendored, strict CSP.
- `web/i18n.py` — EN/ES/FR/DE/PT hand-built catalog + AI fallback + client-side DOM translation.

Also documents "the Bible" (NASA Acumen metric library `.aft` as the authoritative formula source, committed, formula-pinned by `tests/engine/test_aft_formula_audit.py`); the design system (`docs/DESIGN-SYSTEM.md`, ADR-0195); durable state + drift guard (`tests/test_state_docs.py` fails unless the highest ADR appears in both HANDOFF and SESSION-LOG); and the branch/squash-merge/`inherited_from_main` workflow rules.

---

### `docs/STATE/` — durable state

- **`HANDOFF.md`** (~390 KB) — read-first single source of truth for "where we are / what's next," newest handoff on top followed by prior handoffs as a running stack. **Current status (at this map's last refresh, 2026-07-17):** version **1.0.51**, **highest ADR 0240**. Feature #10 (Groups & Filters) is OPERATOR-COMPLETE (PR-A 0231 → PR-B 0232 → PR-C 0233 → PR-C.2 0234 → PR-D `/groups` UI 0235); since then: **PR-U1** operator UI directives (Gantt filter-button fix + find-by-name + per-file switcher, 0236), **PR-M1** `/standards` Standards & Execution Indices page (0237), **PR-M2** the SEM engine family Fuse-validated cell-for-cell (0238), **PR-R1** AI figure-gate hardening (translate gate + number-words + stems, 0239), and the model/audit-protocol rule + intake INDEX + doc-truth pass (0240). HANDOFF.md is authoritative when this lags. **NEXT:** PR-R2 (wire the dead Law-1 defenses + air-gap route enumeration + version-pin guard) → PR-R3 (erosion basis, XER weekends, egress set, 24h-calendar golden) → PR-P1 perf → #13 XER per-task calendars → F3c → roles. Ground truth for #10 is preserved in `docs/STATE/MSP-FILTERS-SPEC.md` + `msp-views-leveled.json` + `msp-filters-research/`.
- **`SESSION-LOG.md`** (~467 KB) — append-only, one dated entry per session (A1, A2, …), newest at the bottom; running history. A1 (2026-06-05) is the Phase-0 greenfield scaffold + reference intake. The authoritative "current" state lives in HANDOFF; this is history.
- Also present: `AUDIT-2026-06-25.md`, `AUDIT-2026-07-13.md`, `AUDIT-2026-07-14.md` (audit backlogs/remediation roadmaps) and `NEXT-SESSION-PROMPT.md`.

Recent version arc visible in the HANDOFF stack: 1.0.34→…→1.0.51; the **SMAT v4** feature line (grouped ingestion + Portfolio F1/ADR-0225 → scale F2/ADR-0226 → margin F3a/b ADR-0230), then the **feature #10 Groups & Filters** arc (0231–0235), the operator-UI/metrics-page/SEM/figure-gate arc (0236–0239), and the governance pass (0240); roles F4 and F3c still ahead.

---

### `docs/DESIGN-SYSTEM.md` (Mission Ops rulebook, ADR-0195)

Governs any web-UI change. **Two design laws:** (1) nothing styles itself — every color/font/radius/shadow comes from a CSS custom property in `sf-themes.css` (a raw hex in markup is a build failure, except fixed CUI-marking and risk-heat colors); (2) every visual is an instrument — a chart without a takeaway headline, labeled data-date line, legend and Data/Excel/Enlarge toolbar is not done. Four themes (`console` dark default / `daylight` light / `apollo` CRT / `jarvis` HUD) via `html[data-theme]`, persisted in localStorage; semantic role tokens (`--accent`, `--ok`/`--warn`/`--bad`, NASA-red `#FC3D21` reserved for critical path / data-date line / alarm verdicts, `--muted`). Page anatomy: CUI bars top+bottom, compliance drawer, command header (wireframe-globe insignia = AI status light), each page a numbered **chapter** with kicker + takeaway h1 (a sentence with a number) + context line + Continue segue. The 12-chapter story spine is enumerated. Toolbar contract (▦ DATA / ⤓ EXCEL / ⛶ ENLARGE on every data visual), chart language (dotted grid, DD line always, series semantics, no pies/3D/dual-axes), voice rules, compliance chrome, and a Definition-of-Done checklist that runs before every UI PR. Integration is phased (tokens → global chrome → one page shell per PR → new panels; never big-bang, never touch `engine/` for a UI change). The pixel-truth reference is an operator-held prototype not committed.

---

### `docs/METRIC-DICTIONARY.md` (generated)

Generated from `schedule_forensics.web.help.METRIC_DICTIONARY` (regeneration one-liner in the header; a test enforces sync). A single ~100-row table: **Metric | Dimension | Definition | Formula | Source** covering every metric the tool emits, each tagged with a NASA Schedule Management Handbook reliability dimension (Comprehensiveness / Construction / Realism / Affordability). Families: DCMA 14-Point (Logic, Leads, Lags, FS/SS-FF/SF relationships, Hard Constraints, High Float, Negative Float, High Duration, Invalid Dates, Resources, Missed Activities, Critical Path Test, CPLI, BEI), Schedule-Quality summary (Missing Logic, Logic Density, Critical, Insufficient Detail, Merge Hotspot…), baseline-compliance/Half-Step-Delay (Completed/Started On Time/Late, BFC/BSC, CEI Finish/Start/Bow-Wave), EVM (SPI/CPI/TCPI, SPI(t) count-based **and** Acumen per-activity SPI(t)), change/Schedule-Network metrics (Activities Added, New/No-Longer Critical, Finish/Start Slips, Remaining-Duration Increases, Float Erosion, Net Finish Impact), Driving Slack / Driving Path, and the reconstructed Power-BI float bands (0 / <5 / <10 days). Sources cite PARITY-TARGETS sections, ADRs, the `.aft` Bible, and Fuse Metric-History parity verifications (e.g., SPI(t)-Acumen verified EXACT 0.80/1.14/1.25 on Hard_File_updated/2/3).

---

### `docs/PLAN/`

- **`BUILD-PLAN.md`** — Phase-2 plan (session A2). Purpose, architecture ASCII (ui → services → engine → model → importers), planned package layout, and 17 ordered session-sized milestones **M1–M17** with acceptance criteria: M1 build rails/egress guard/CI, M2 domain model+units, M3 MSPDI/XER importers, M4 native `.mpp`+MPXJ, M5 CPM, **M6 SSI driving-slack parity gate**, **M7 Acumen DCMA-14/SQ parity gate**, M8 EVM/baseline/change parity, M9 consolidated parity gate, M10 DCMA audit+recommendations, M11 diff+manipulation trends, M12 local AI+cited narrative, M13 web shell, M14 interactive visuals, M15 `.pbix` enrichment (done), M16 launcher/packaging, M17 docs/closeout. States the fidelity core (M1–M9) gates everything; cross-cutting QC/PM rules (TDD, coverage gates, citations everywhere, UID-only matching).
- **`RTM.md`** — Requirements Traceability Matrix. Every §6.A–§6.G requirement + units §3 + QC/PM §7 → module → test → parity evidence → milestone → status. Almost every row reads **✔** (Implemented+Tested+Validated). Notable evidence rows (refreshed 2026-07-17 to match the live parity gate): B2 parity "SSI UID-145 all-dependencies 108/108 + UID-67 Path-01 20/20 + UID-152 76/76; Acumen §A; §B 13/14; §C counts+BFC; §E … Net Finish Impact −148 engine-CPM (reconciles day-exact to Fuse stored −134); residuals formally accepted+locked (ADR-0014)"; overall coverage cited at 99%.
- **`INSTALLER-SPEC.md`** — one-file distributable installers, **BUILT 2026-07-02**, three RAM/GPU tiers (Tier1 16 GB `llama3.2:3b` / Tier2 64 GB `llama3.1:8b` / Tier3 128 GB `llama3.3:70b`). Nine files across Windows `.ps1` / Linux `.sh` / macOS `.command` (ADR-0144); Linux full-lifecycle + windows-latest tier1 smoke run in CI; documented defaults for the four open questions. Executing the Linux installer caught the wheel-not-packaging-`web/static` blocker (fixed via `[tool.setuptools.package-data]`).
- Other PLAN docs: `METRICS-CATALOG.md`, `PARITY-TARGETS.md`, `PARITY-INPUTS.md`, `SSI-DRIVING-SLACK.md`, `AI-DERIVED-METRICS-SCOPE.md`, `PBIX-VISUALS.md`, `INTAKE-MANIFEST.md`, `SETUP-DIRECTION.md`, `CLAUDE-CODE-SETTINGS.md`.

---

### `docs/adr/` — 251 files (ADR-0000 through ADR-0250), no separate index

Every ADR follows a `# ADR-NNNN: title` / Status / Date / Context / Decision format (Status typically "Accepted", many "operator-approved"). Rather than an index, the sequence numbers self-document the build's chronology. The **arc of key decisions, by theme:**

- **Foundations / stack (0000–0009):** 0000 record-ADRs; 0001 keep vendored MPXJ native-`.mpp` toolchain; 0002 greenfield-on-feature-branch; 0003 non-CUI attestation for the reference intake; **0004 architecture & tech stack** (Python 3.11, frozen UID-keyed pydantic, minutes→days boundary, MPXJ subprocess, pure-Python engine, pluggable local AI); **0005 parity strategy & golden fixtures** (golden-fixture acceptance gate); 0006 build rails (egress guard, hooks, CI); 0007 domain model/units; 0008 importers; 0009 native `.mpp`.
- **Fidelity core / parity (0010–0016, plus a long tail):** 0010 CPM+float; **0011 driving-slack SSI parity**; **0012 Acumen DCMA-14/schedule-quality**; 0013 EVM/baseline/change; **0014 parity acceptance gate + residual disposition** (the formally-accepted locked residuals); 0015 DCMA audit/recommendations; 0016 diff+manipulation trends. Recurring parity re-verification threads: 0080 DCMA stored total-slack/critical, 0084–0089 Bible formulas (Insufficient Detail / BEI / CPLI / HMI), 0098/0101 CEI Acumen parity, 0108–0112 EVM/AFT-Bible-audit/golden refresh, **0151 Fuse-export parity** (ENGINE==FUSE flip), 0159/0168 Fuse/SSI Hard_File golden, 0176 Acumen alignment (BEI/SPI(t)/DCMA-09).
- **Driving-slack / path (0011, 0031, 0032, 0045, 0091, 0096, 0115–0118, 0168, 0174):** anchored progress-aware backward pass, day-granular tiering, intraday lunch handling, per-task calendars, driving-path-between-two-UIDs, corridor animation, SSI UID-145/UID-155 goldens, driving-tier export/trace fidelity.
- **CUI / egress / packaging (0006, 0058, 0070, 0074, 0113, 0144, 0148, 0149, 0152, 0191–0193):** loopback-scheme validation, AI proxy bypass/diagnostics, CSP/security headers, CUI export marking, all-OS installers, deployment freshness, windowless subprocess spawns, **0152 CUI-guard `inherited_from_main`** (the narrowly-scoped merge exception for byte-identical origin/main blobs), no-admin portable-JDK install.
- **AI / figure-gate / roles (0017, 0035, 0036, 0129, 0132–0138, 0142, 0145):** cited narrative, interpretive Q&A everywhere, OpenAI-compat second backend + dual-model cross-check, **0129 Ask-AI figure-mode** (strict/annotate/interpretive), derived-metrics Layer-A/B, **0134/0137/0138 role-aware figure gate** (value-vs-identifier split + hardening), 0136 AI determinism, **0145 unit-role figure gate** (first semantic check).
- **Margin / SRA / EVM realism (0106, 0107, 0123, 0126, 0127, 0189, 0213, 0221, 0222):** Schedule Risk Analysis Monte-Carlo, **0107 schedule margin**, SSI risk/opportunity analysis, unified risk register, credibility-weighted estimates, assessment scorecards + reserve sizing, **0222 executive margin dashboard** (margin work continuing into the v4 F3a/b line).
- **Design system / Mission-Ops redesign (0146, 0175, 0194–0210):** HUD UI layer, POLARIS wordmark, **0195 four-theme tokens**, 0196 story-spine chrome, then **0197–0210 one page-shell ADR per chapter** (01–12), 0204 Metric Workbench.
- **Caching / scale / v4 (0122, 0186, 0225, 0226):** lazy Ollama lifecycle, page-memory reset, **0225 grouped ingestion + Portfolio (v4 F1)**, **0226 scale: SQLite parse+summary cache + lazy summary tier + RAM estimate + persistent batch JVM (v4 F2)**.
- **Latest (0219–0231):** presentation bug batch, ch01 critical basis, SRA calendar day-counts, executive margin dashboard, float-ribbon extras N/A-on-empty-population, 24-hour continuous-calendar parse, the v4 F1/F2 pair, **0227** operator bugfixes (upload/path-view/driving-slack), **0228** enlarged mosaic-chart tile-height release, **0229** Path-grid click-to-highlight, **0230** F3a/3b NASA margin (terminology + confirmed overlay + dual numbers + 50%-consumed flag), **0231** #10 PR-A faithful MS Project filter evaluator + saved-view model.

---

### Root config

- **`pyproject.toml`** — package `schedule-forensics` **v1.0.51** (version moves in lockstep with every src-changing PR; the wheel + 9 installers are rebuilt in the same commit), `requires-python >=3.11`, license Proprietary/"Do Not Upload". Runtime deps deliberately minimal and egress-safe: `pydantic>=2`, `fastapi>=0.110`, `uvicorn>=0.29` (plain, **not** `uvicorn[standard]` — avoids the forbidden `websockets` dist), `jinja2>=3.1.6`, `python-multipart>=0.0.18` (floors raised past published-CVE ranges, ADR-0250). Scripts: `schedule-forensics` (launcher) and `schedule-forensics-report` (headless exhibits). Extras: `[monitor]` = psutil (local reads only); `[dev]` = pytest/pytest-cov/ruff/mypy/bandit/pip-audit + httpx (dev-only, forbidden as runtime) + `setuptools>=83.0.0` (pinned to remediate PYSEC-2026-3447 per AUDIT-2026-07-13). `[tool.setuptools.package-data]` ships `web/static/*` + `web/examples/*` (the wheel-static fix). Ruff line-length 100 (E/F/I/B/UP/SIM/RUF; `web/app.py` ignores E501). mypy strict with pydantic plugin, psutil ignored. pytest `--strict-markers --strict-config`, `parity` marker registered, httpx-TestClient deprecation filtered. Coverage branch mode, `fail_under=70` (engine ≥85% enforced separately in CI). Bandit excludes tests/.venv/tools. Header comment: **do not add a cloud/remote-HTTP client to `dependencies` without an ADR** (egress guard fails CI).
- **`.gitignore`** — Law-1 CUI blocks at the VCS layer: `*.mpp/.mpt/.mpx/.xer/.xml/.pmxml/.csv/.xls/.xlsx/.pbix/.mspdi/.aft/.docx/.doc` (fail-closed). `00_REFERENCE_INTAKE/*` blocked except deposit-instruction docs and `.gitkeep` folder skeletons (folder contents stay ignored). Runtime data dirs (`session_data/`, `uploads/`, `exports/`, `local_parity/`) ignored. Deliberately does **not** globally ignore `*.json` (tracked config is JSON; schedule JSON blocked via runtime dirs). Only exception allowing schedule formats in-repo: `tests/fixtures/` (synthetic). MPXJ jars committed except the ~14 MB SQLite driver; portable `tools/jre/` and the v4 SQLite cache (`*.sqlite3*`) never committed.
- **`.githooks/pre-commit`** — the CUI pre-commit guard (Law-1 defense-in-depth behind `.gitignore`), activated by the SessionStart hook (`git config core.hooksPath .githooks`). Rejects any staged blocked-extension blob (regex `mpp|mpt|mpx|xer|xml|pmxml|csv|xls|xlsx|pbix|mspdi|pkl|pickle|aft|docx|doc`) even with `git add -f`. Two exceptions only: (1) `tests/fixtures/` synthetic fixtures; (2) `inherited_from_main()` — a staged blob byte-identical to `origin/main` at the same path (ADR-0152, so merges of already-public intake blobs aren't wedged). Scans adds/modifies/renames (`--diff-filter=AMR`); any new or modified schedule binary is still blocked; prints the offending paths and exits 1.
- **`.github/workflows/ci.yml`** — CI (stood up at M1). Triggers on push-to-main, all PRs, and manual dispatch; concurrency-cancel; `contents: read`. `test` job matrix over Python **3.11 and 3.13**: install `.[dev]` → ruff check → ruff format --check → mypy (strict) → **pytest with `--cov-fail-under=70`** → **engine coverage gate `--fail-under=85`** → **parity gate `pytest -m parity`** → bandit → pip-audit. A stable aggregate `check` job (needs `test`) gives branch protection one required context. Status-check context names (`test (3.11)`, `test (3.13)`, `check`) kept stable. `node --check` is local-only; Ollama never required in CI. A second workflow, `.github/workflows/installer-smoke.yml`, exercises the installers (Linux lifecycle + windows-latest tier1 smoke).

**Cross-cutting drift guard:** `tests/test_state_docs.py` fails unless the highest ADR number on disk (currently **0231**) appears in both `HANDOFF.md` and `SESSION-LOG.md`, and a doc-sync test enforces `METRIC-DICTIONARY.md` regeneration from `web/help.py`.

---

## 00_REFERENCE_INTAKE — reference material & how to use it

### Headline finding on `.xer` files (operator's special focus)

**There are NO `.xer` (Primavera P6) files anywhere in `00_REFERENCE_INTAKE/`.** I recursed every subfolder (`mpp/`, `ssi/`, `acumen_v8.11.0/`, `references/`, `pbix/`, `metrics_library/`, root) and confirmed the only extensions present are `.xlsx .pdf .mpp .afw .aft .zip .md .docx .ppt .jpg`. The intake's Primavera-format holdings are **zero**. The operator's recollection of "sample `.xer` files" in the intake is not borne out by the tree.

The **only** `.xer` in the entire repository is a synthetic, hand-authored, non-CUI test fixture:

- `tests/fixtures/xer/commercial_construction.xer` (its header comment: *"SYNTHETIC, NON-CUI TEST FIXTURE (M3). Hand-authored Primavera P6 XER. Contains no real schedule data."*)

I ran the tool's real importer on it as requested:

```
python -c "from schedule_forensics.importers import load_schedule; s=load_schedule('tests/fixtures/xer/commercial_construction.xer'); print(s.name, s.project_title, len(s.tasks), s.status_date)"
```

Result — **it parses cleanly**:

| field | value | source XER field |
|---|---|---|
| `name` | `CC-A` | PROJECT `proj_short_name` |
| `project_title` | `CC-A` | **PROJECT `proj_short_name`** |
| `len(s.tasks)` | `5` | TASK rows (2000–2004; incl. one `TT_WBS` + one `TT_FinMile` milestone) |
| `status_date` | `2025-02-01 17:00:00` | PROJECT `last_recalc_date` |

So the **XER Title path (`proj_short_name` → `project_title`) works**: the importer maps the P6 short name to `project_title` (here "CC-A"), reads `last_recalc_date` as the status/data date, and materialises all five TASK records including WBS-type and finish-milestone tasks. The fixture also exercises TASKPRED (FS/SS/FF/SF with +/- lag), RSRC/TASKRSRC cost rows, and PROJWBS — i.e. it is the regression anchor for the whole `xer` importer (`tests/importers/test_xer.py`). **If the operator wants XER import validated against real P6 exports, none are currently in the intake — they would need to be deposited under a new path (there is no `xer/` intake subfolder yet).**

---

### Per-file inventory (every file under `00_REFERENCE_INTAKE/`)

Paths are relative to `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment/00_REFERENCE_INTAKE/`.

#### Root files

| Path | Size | Format | What it is | Provenance | How used |
|---|---|---|---|---|---|
| `NASA Metrics_Complete_20260423.aft` | 10.1 MB | XML `<MetricLibraryFile>` | The NASA Acumen **metric library ("the Bible")**: 1,443 `<Metric>` elements, 899 carrying a `<Formula>` (941 `<Formula>` tags total incl. Advanced/Primary/Secondary/Tripwire variants) | ADR-0151/0152; CLAUDE.md CUI note (operator-confirmed **non-CUI**, committed to `main`). `FILE-NAMES.md`: "VALIDATED — live-Bible formula audit passes"; test constant `_BIBLE_SNAPSHOT = "NASA Metrics_Complete_20260423.aft"` | **Authoritative metric-formula source.** `tests/engine/test_aft_formula_audit.py` pins every tool metric in `web/help.py` to a verbatim NASA `Name`+`Formula` here (verdicts: match/variant/drift/not_in_bible) and asserts no Bible drift |
| `FILE-NAMES.md` | 3.5 KB | Markdown | Intake manifest — exact upload names + destinations; notes which paths tests probe literally | Repo doc (tracked) | Operator playbook; documents the `Project5.mpp`==`Project5_TAMPERED.mpp` duplication and that the `.aft` is "the Bible… 1,443 entries" |
| `DEPOSIT-HERE.md` | 5.9 KB | Markdown | Gate-1 deposit checklist + CUI stop-rule | Repo doc (tracked) | Governs what may be deposited; defines items 1–6 (pbix, mpp pair, Fuse golden, SSI golden, metric library, references) |
| `Project2.mpp` | 691 KB | MS Project binary | Baseline schedule of the golden P2→P5 chain (144 activities) | ADR-0003/0005 non-CUI commercial-construction sample; duplicate of `mpp/Project2.mpp` | MPP import testing (via MPXJ→MSPDI); the "before" file for Fuse/forensic parity |
| `Project5_TAMPERED.mpp` | 817 KB | MS Project binary | The **tampered** schedule (authoritative 4-stored-critical file, ADR-0112) | ADR-0112 (supersedes stale 37-critical capture); duplicate of `mpp/Project5_TAMPERED.mpp` | Manipulation-detection + forensic-diff ground truth; SSI focus-UID exports derive from it |
| `Project2 vs Project5_TAMPERED Forensic Analysis Report.xlsx` | 82 KB | XLSX (Acumen Fuse Forensic) | Fuse® **Forensic Analysis** comparison, sheets: Projects / Activities / Relationships / Leads-Lags / Resources / Calendars / Calendar Exceptions / ID | `FILE-NAMES.md`: "CLASSIFIED as PARK-LIST A-1 source"; feeds the §E float/critical re-pin | Per-activity Total-Float / Critical / cost ground truth for the network-change (§E) parity block |
| `Project2v5 Forensic Analysis Report.xlsx` | 81 KB | XLSX (Acumen Fuse Forensic) | Near-identical earlier Forensic Analysis export (same 8-sheet layout, "Project2 – 144 Activities, compared to 1 snapshot") | Acumen Fuse v8.11.0 export | Corroborating forensic comparison for the same pair |
| `P2-P5 - DCMA Report.xlsx` | 604 KB | XLSX (Fuse Summary Metric) | Fuse® Summary/DCMA report, "P-P5 – 288 Activities", created 6/21/2026. Sheets incl. Program-Summary, NASA_Quick-Library, Schedule-Errors/Warnings, Critical-Path, BEI-Incomplete | Acumen Fuse v8.11.0; ADR-0151 delivered suite | DCMA-14 + Schedule-Quality (§A/§B) golden numbers |
| `P2-P5 - Detailed Metric Report.xlsx` | 99 KB | XLSX (Fuse Detailed) | Per-file detailed metrics, sheets `Project2` and `Project5_TAMPERED` | Acumen Fuse v8.11.0 | Per-schedule metric ground truth |
| `P2-P5 - Metric History Report.xlsx` | 20 KB | XLSX (Fuse Metric History) | Cross-snapshot metric trend, sheet `Project2` | Acumen Fuse v8.11.0 | Trend/manipulation-series parity (the "2345 Metric History Report" referenced in `project2_5/case.json`) |
| `P2-P5 - Quick Add Metrics.xlsx` | 172 KB | XLSX (Fuse Analyst) | Ribbon View / Ribbon Analysis / per-project / Phase Analysis / dated Details sheets | Acumen Fuse v8.11.0 | Ribbon-scoped metric ground truth incl. dated (3-1/3-8/3-15-2026) phase details |
| `P-P5 - Quick Add Metrics .xlsx` | 26 KB | XLSX (Deltek Acumen Fuse Ribbon) | Ribbon View / Ribbon Analysis / Phase Analysis | Acumen Fuse v8.11.0 | Ribbon/phase metric ground truth (lighter variant of the above) |
| `SP-20240014019.pdf` | 14.5 MB | PDF handbook | NASA technical publication (also duplicated in `references/`) | Reference deck | Threshold/definition sourcing for health checks |
| `SP-20240014326.pdf` | 6.7 MB | PDF handbook | NASA technical publication (dup in `references/`) | Reference deck | Same |
| `evmimplementationhandbook-1-1.pdf` | 3.2 MB | PDF handbook | EVM Implementation Handbook (dup in `references/`) | Reference | EVM-metric definitions (`engine/metrics/evm.py`) provenance |
| `nasa-ibr-handbook-5-1.pdf` | 2.7 MB | PDF | NASA IBR Handbook (dup in `references/`) | Reference | IBR context |
| `nasa-wbs-handbook.pdf` | 4.4 MB | PDF | NASA WBS Handbook (dup in `references/`) | Reference | WBS scoping context |
| `pm-handbook-nasa-sp-2014-3705-2024jun.pdf` | 11.2 MB | PDF | NASA PM Handbook (dup in `references/`) | Reference | Programmatic context |
| `ppc-handbook-1-5-17.pdf` | 4.6 MB | PDF | Planning/Programming/Control Handbook (dup in `references/`) | Reference | Threshold sourcing |
| `sopi_6.0_final.pdf` | 1.4 MB | PDF | SOPI 6.0 (dup in `references/`) | Reference | Context |
| `srb-handbook-official-rev-c-...pdf` | 1.2 MB | PDF | Standing Review Board Handbook (dup in `references/`) | Reference | Context |
| `schedule-management-handbook-20240315-update.zip` | 24.5 MB | ZIP | NASA Schedule Management Handbook bundle (dup in `references/`) | Reference | Handbook source for schedule-quality thresholds |
| `.gitkeep` | 0 | — | Folder placeholder | — | — |

#### `mpp/` — native MS Project schedules (MPP import + parity inputs)

| Path (`mpp/`) | Size | What it is | Provenance | How used |
|---|---|---|---|---|
| `Project2.mpp` | 691 KB | Golden chain baseline (144 act.) | ADR-0003/0005 non-CUI sample; `FILE-NAMES.md` "tests probe these literal paths" | MPP→MSPDI import; §A/§B/§C/§E parity input |
| `Project3.mpp` | 691 KB | Chain step P3 | same | Chain-progression import/parity |
| `Project4.mpp` | 692 KB | Chain step P4 | same | Chain-progression import/parity |
| `Project5.mpp` | 817 KB | **Same tampered file as `Project5_TAMPERED.mpp`, second name** (per `FILE-NAMES.md`: "upload it twice") | ADR-0112 | Tests that probe the `Project5.mpp` path |
| `Project5_TAMPERED.mpp` | 817 KB | Authoritative tampered file (4 stored-critical) | ADR-0112 | Manipulation/forensic ground truth; SSI UID-67/145 exports derive from it |
| `Hard_File.mpp` | 1.3 MB | "Hard File" base schedule (282 activities) | Fuse suite delivered 2026-07-08 | Fuse parity (2nd oracle) + SSI UID-155 |
| `Hard_File_updated.mpp` | 1.3 MB | Updated snapshot (Time Now 8/11/2026) | same | Cross-snapshot Fuse parity (elapsed in-progress activity) |
| `Hard_File_updated2.mpp` | 1.5 MB | Third snapshot | same | `update vs update2` Fuse comparison exports |
| `Hard_File_updated3.mpp` | 1.3 MB | Fourth snapshot | same | `update2 vs update3` Fuse comparison exports |
| `Hard_File_updated3 24 hour calendar.mpp` | 1.3 MB | update3 on a 24-hour calendar | Added 2026-07-14 | Calendar-handling / `Hard_File_updated3_24hr` fixture source |
| `Hard_File_updated_with_logic_reestablished.mpp` | 1.2 MB | Logic-restored variant | same | Missing-logic recovery testing |
| `Large Test File.mpp` | 9.7 MB | Large real-world master IMS ("USA OTB Master IMS", 2,126 tasks) | closes needs-list A-4 | Parse/perf + SSI absolute driving-slack (UID 152) |
| `Large_Test_File.mpp` | 9.7 MB | Same large file, underscore name (tests probe literal path) | `FILE-NAMES.md` | SSI UID-152 driving-path parity |
| `Large Test File Leveled.mpp` | 9.4 MB | Resource-leveled variant of the large IMS | Added 2026-07-14 | `ssi_uid152_leveled` golden source (leveling-delay driving path) |
| `.gitkeep` | 0 | placeholder | — | — |

#### `ssi/` — SSI Directional Path Tool exports (driving-path / driving-slack GOLDEN)

All are single-sheet `Directional Path Export` workbooks. **Column schema (identical across files):** `Focus Task Name | Focus Task UID | Task Name | Unique ID | Start | Finish | Driving Slack | Drag | Trace Log Value (Path NN) | Project`.

| Path (`ssi/`) | Size | Focus UID / rows | Provenance (case.json) | How used |
|---|---|---|---|---|
| `Project5_TAMPERED_UID_67_Directional_Path_Analysis_2026-7-8-8-19-10.xlsx` | 11 KB | UID 67 "Pour roof slab", 20 Path-01 rows | `golden/ssi_uid67/case.json`; Predecessors, Driving Slack≤0d, Waterfall | Driving-path membership + **drag gated exact** (`test_ssi_drag_exact`) |
| `Large_Test_File_UID_152_Directional_Path_Analysis_2026-7-8-8-45-50.xlsx` | 15 KB | UID 152, 76 Path-01 rows (all slack 0d) | `golden/ssi_uid152/case.json`; drag provenance-only (ADR-0158) | `test_ssi_driving_slack_uid152_exact` |
| `Large Test File Leveled ... UID_152 ... 2026-7-14-17-21-13.xlsx` | 68 KB | UID 152, all-dependencies + driving slack | `golden/ssi_uid152_leveled/case.json` (2026-07-14) | Leveled driving-path parity (ignore-leveling-delay convention) |
| `Large Test File Leveled Critical - Secondary - Teritiary ... 2026-7-14-17-22-42.xlsx` | 19 KB | UID 152, tiered (critical/secondary/tertiary) | same golden dir | Tier-band (secondary/tertiary) validation |
| `Large Test File Leveled ... SSI Settings.jpg` | 80 KB | **Screenshot (JPEG)** of SSI tool settings | 2026-07-14 | Documents the exact SSI config (Predecessors, Ignore constraints/leveling delay, near-path bands) behind the leveled goldens |
| `Hard_File_Path_Trace_UID_155_...2026-7-8-13-30-7.xlsx` | 16 KB | UID 155, base Hard_File | `golden/ssi_hardfile_uid155/case.json` | Path-01 membership + ordered driving chain (141→156→36→9→144→145→146→411→155) |
| `Hard_File_Path_Updated_Trace_UID_155_...2026-7-8-13-30-7.xlsx` | 16 KB | UID 155, Hard_File_updated | same golden | Same, on the updated snapshot |
| `.gitkeep` | 0 | placeholder | — | — |

#### `acumen_v8.11.0/` — Acumen Fuse v8.11.0 exports + workspaces + 2nd metric library

| Path (`acumen_v8.11.0/`) | Size | Format | What it is | How used |
|---|---|---|---|---|
| `NASA Metrics_Complete_20260708.aft` | 9.86 MB | XML metric library | A **later** (2026-07-08) snapshot of the NASA Bible — differs from the root 20260423 file (fewer elements) | Reference only; the **root 20260423 is the pinned Bible**, not this one |
| `Hard_File_Fuse.afw` | 550 KB | Acumen **Fuse workspace** (binary) | Saved Fuse workspace for Hard_File | Re-openable Fuse project behind the Hard_File exports |
| `Hard_File_update vs update2_Fuse.afw` | 563 KB | Fuse workspace | update-vs-update2 comparison workspace | " |
| `Hard_File_update2 vs update3_Fuse.afw` | 459 KB | Fuse workspace | update2-vs-update3 comparison workspace | " |
| `Hard_File_Fuse - Metric History Report.xlsx` | 20 KB | XLSX | Metric history, sheet "Hard_File" (both snapshots side by side) | **Primary transcription source** for `golden/fuse_hardfile/case.json` (15 metrics ENGINE==FUSE) |
| `Hard_File_Fuse - Summary Metric Report.xlsx` | 463 KB | XLSX | Summary metrics | Corroborates the history report |
| `Hard_File_Fuse - Fuse Analysis Report.xlsx` | 20 KB | XLSX | Fuse analysis | Fuse-scoped metric ground truth |
| `Hard_File_Fuse - Quick Add Metrics .xlsx` | 13 KB | XLSX | Ribbon quick-add metrics | Ribbon metric ground truth |
| `Hard_File_update vs update2_Fuse - {Analysis, Detailed Metric, Excel, Metric History, Summary} Report.xlsx` | 22–489 KB | XLSX ×5 | The update→update2 comparison export set | Cross-version Fuse parity |
| `Hard_File_update2 vs update3_Fuse - {Analysis, Detailed Metric, Excel, Metric History, Metrics, Summary Metrics} Report.xlsx` | 20–91 KB | XLSX ×6 | The update2→update3 comparison export set | Cross-version Fuse parity |
| `Hard_File_updated vs update 2_ Forensic Analysis Report.xlsx` | 113 KB | XLSX | Forensic (network-change) comparison | §E-style forensic diff ground truth |
| `Hard_File_updated2 vs update3 Forensic Analysis Report.xlsx` | 101 KB | XLSX | Forensic comparison | " |
| `Hard_File_missing_logic.xlsx` | 10 KB | XLSX | Missing-logic activity listing (base) | DCMA-01 / missing-logic scoping ground truth |
| `Hard_File_updated_missing_logic.xlsx` | 21 KB | XLSX | Missing-logic listing (updated) | " |
| `.gitkeep` | 0 | placeholder | — | — |

#### `references/` — handbooks, decks, sample reports, templates

| Path (`references/`) | Size | Format | What it is / how used |
|---|---|---|---|
| `PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` | 848 KB | XLSX | **Sample analysis workbook to emulate** — sheets G1_Characteristics_WorkToGo, G2&G3_BowWave (2025MAR/2024SEP), G4_Workoff Burden, G5_DurationRatio S-Curve, G3_Quad_HMI&CEI, Portfolio. Source of visual/metric-grouping design (HMI/CEI quad, bow-wave, work-off) |
| `INT-02-Advanced-Schedule-Analysis.pdf` | 807 KB | PDF | Advanced schedule-analysis course — driving-path/analysis methodology provenance |
| `106 Advanced Schedule RiskPresentation Lisbon.ppt` | 879 KB | PPT deck | Advanced schedule-risk presentation — threshold/method sourcing |
| `Concepts, Methods & Techniques.docx` | 44 KB | DOCX | Methods write-up — narrative/definition source |
| `smp-template-20200225.docx` | 45 KB | DOCX | Schedule Management Plan template — report-shape reference |
| `schedule-management-handbook-20240315-update.zip` | 24.5 MB | ZIP | NASA Schedule Mgmt Handbook bundle |
| `SP-20240014019.pdf`, `SP-20240014326.pdf` | 14.5 / 6.7 MB | PDF | NASA technical publications |
| `evmimplementationhandbook-1-1.pdf` | 3.2 MB | PDF | EVM handbook — EVM formula provenance |
| `nasa-ibr-handbook-5-1.pdf`, `nasa-wbs-handbook.pdf`, `pm-handbook-nasa-sp-2014-3705-2024jun.pdf`, `ppc-handbook-1-5-17.pdf`, `sopi_6.0_final.pdf`, `srb-handbook-official-rev-c-...pdf` | 1.2–11.2 MB | PDF | NASA handbooks — threshold/definition sourcing for health checks |
| `.gitkeep` | 0 | placeholder |

#### Empty intake subfolders (deposit slots, only `.gitkeep`)

| Folder | Intended item | Status |
|---|---|---|
| `pbix/` | Power BI `.pbix` (item 1: extra metrics/DAX + visuals) | **empty** — no Power BI reference delivered |
| `metrics_library/` | Metric-library formulas (item 5) | **empty** — satisfied instead by the root `.aft` (per `FILE-NAMES.md`) |

---

### Per-format "how to use it"

**NASA `.aft` metric library ("the Bible") — `NASA Metrics_Complete_20260423.aft`**
XML `<MetricLibraryFile>` → `<Metrics>` → `<MetricGroup>` (e.g. "NASA_Quick Library") → 1,443 `<Metric>` elements. Each `<Metric>` carries `<Guid>`, `<Name>`, `<Description>`, `<Remarks>`, DCMA/scope flags (`IncludeComplete/InProgress/Milestone/Summary`, `IncludeInDCMA`), and formula tags: `<Formula>` (899 metrics have one; 941 `<Formula>` tags total counting `AdvancedPrimaryFormula`/`AdvancedSecondaryFormula`/`AdvancedTripwireFormula`/`HighlightFormula`). **Note: the schema uses `<Name>`+`<Formula>`, not `<FieldName>` — there are zero `<FieldName>` tags.** `tests/engine/test_aft_formula_audit.py` pins each tool metric (from `web/help.py::METRIC_DICTIONARY`) to a NASA `Name`+verbatim `Formula` here, tagging match/variant/drift/not_in_bible, and asserts the on-disk Bible still matches — a definitional guard, not parity. The `acumen_v8.11.0/NASA Metrics_Complete_20260708.aft` is a later snapshot and is **not** the pinned one.

**`.mpp` (native MS Project)** — no Python parser; the tool converts via vendored MPXJ (`tools/mpxj/`, Java 17+) to MSPDI XML, which the `mspdi` importer ingests. The golden fixtures under `tests/fixtures/golden/*/*.mspdi.xml(.gz)` are those conversions. Use these for MPP-import testing, CPM, and as the parity inputs whose engine numbers must match the Fuse/SSI exports. `Project5.mpp` and `Project5_TAMPERED.mpp` are byte-identical duplicates under two names.

**Acumen Fuse `.xlsx` exports** — every workbook opens with 4 banner rows ("Fuse® … Report", "P-P5 – 288 Activities" / "Hard_File_Fuse – 282 Activities", report type, "Created on: …") then the metric grid. They are the **GOLDEN target numbers** for §A Schedule-Quality, §B DCMA-14, §C baseline/HSD, and §E network-change parity. Values are transcribed verbatim into `tests/fixtures/golden/*/case.json` + `fuse_exports_2026-06.json` and asserted ENGINE==FUSE (`tests/parity/test_fuse_export_parity.py`, `test_fuse_hardfile_engine_equals_fuse`). `.afw` files are the re-openable Fuse workspaces behind them.

**SSI `.xlsx` (Directional Path Export)** — single sheet, columns `Focus Task Name | Focus Task UID | Task Name | Unique ID | Start | Finish | Driving Slack | Drag | Trace Log Value | Project`. Ground truth for **driving-path membership and per-task Driving Slack (days)** to a focus UID; `Trace Log Value` = "Path 01/02/03" tier bucketing. The engine reproduces the strict 0-day Path-01 set UID-for-UID; **Drag** is gated exact only for UID-67/145 and provenance-only elsewhere (ADR-0158). The accompanying `.jpg` documents the SSI tool settings that produced the leveled exports.

**Reference PDFs / PPT / DOCX / XLSX sample** — non-parity: handbooks source health-check thresholds and metric definitions; `PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx` is the visual/grouping template the tool's panels (bow-wave, work-off burden, HMI/CEI quad, duration-ratio S-curve) emulate.

**Empty:** `pbix/` (no Power BI reference deposited) and `metrics_library/` (superseded by the root `.aft`).

### Bottom line for the operator
- The intake is rich in **MS Project (`.mpp`)**, **Acumen Fuse (`.xlsx`/`.afw`)**, **SSI (`.xlsx`)**, and the **NASA `.aft` Bible** — but contains **no `.xer`/Primavera P6 files at all**.
- XER import is nonetheless proven working against the synthetic fixture `tests/fixtures/xer/commercial_construction.xer` (`proj_short_name`→`project_title` = "CC-A", 5 tasks, status_date 2025-02-01 from `last_recalc_date`). To parity-test XER on real data, a P6 `.xer` would need to be deposited (there is currently no `00_REFERENCE_INTAKE/xer/` slot).

---

## Tooling, Installers & CI

This section inventories the build/tooling/CI surface of the tool. Everything below is read-only observation; nothing was modified. All paths are relative to the repo root `/home/user/Schedule-Manipulation-Analysis-Tool-Experiment/`.

---

### 1. `tools/mpxj/` — the vendored MPXJ native-`.mpp` toolchain

Native `.mpp` is a binary OLE format with no pure-Python parser. The tool never runs a JVM in-process (no JPype); instead it shells out to a tiny vendored Java converter that reads the `.mpp` with MPXJ's `UniversalProjectReader` and writes **MSPDI XML**, which the pure-Python importer (`importers/mspdi.py::parse_mspdi_text`) then parses. This keeps the JVM entirely out of the Python process (stated as "Commandment 1" in the Java header).

**Files:**
- `tools/mpxj/MpxjToMspdi.java` — the converter source (97 lines).
- `tools/mpxj/classes/MpxjToMspdi.class` — the committed compiled class (this is what discovery checks for on disk).
- `tools/mpxj/lib/*.jar` — 25 dependency jars, pinned to **MPXJ 16.2.0** (`mpxj-16.2.0.jar`, ~3.4 MB) plus POI 5.5.1, Jackson 2.21, JAXB 3.0.2, jackcess 4.0.10, commons-*, log4j-api, etc. Total ~17 MB.
- `tools/mpxj/setup.sh` / `tools/mpxj/setup.ps1` — the (re)build scripts.

**`MpxjToMspdi.java` — two modes** (`tools/mpxj/MpxjToMspdi.java`):
1. **One-shot:** `MpxjToMspdi <input> <output>` — converts a single file and exits. Exit codes: `0` ok, `1` bad args, `2` MPXJ did not recognize the format.
2. **Batch/server:** `MpxjToMspdi --server` — a persistent, heap-capped JVM converting many files in ONE process. It prints `@@SF@@ READY`, then reads `"<input>\t<output>"` lines from stdin and writes one tagged status line per request (`@@SF@@ OK` / `@@SF@@ ERR <msg>`) until EOF or a `__QUIT__` line. Every status line carries the `@@SF@@ ` prefix (constant `TAG`) so stray JVM/Log4j stdout noise is never mis-read as a status. One unreadable file is caught (`catch (Throwable)`) and reported, never fatal — the same JVM keeps serving the rest of a folder ingest. This is "one JVM boot vs thousands" for a large folder.

**`setup.sh` / `setup.ps1`** (`tools/mpxj/setup.sh`, `tools/mpxj/setup.ps1`): require JDK ≥17 + Maven on PATH. They **generate a disposable `pom.xml` at run time** (because the repo's data-sovereignty `.gitignore` blocks all `*.xml` — the pom is build input, not source), run `mvn -q dependency:copy-dependencies -DoutputDirectory=lib -DincludeScope=runtime` to populate `./lib`, then `javac -cp 'lib/*' -d classes MpxjToMspdi.java`. Version overridable via `MPXJ_VERSION` (default `16.2.0`). Both print the `SF_MPXJ_HOME` export to enable native `.mpp`. The PowerShell version additionally notes that on Windows `.mpp` can alternatively be read through installed MS Project via a COM path.

**Python side — discovery + the persistent batch JVM** (`src/schedule_forensics/importers/mpp_mpxj.py`, the richest file in this area):
- `_find_java()` — locates `java` with progressively wider scans: `SF_JAVA` → `JAVA_HOME` → PATH → the repo-local portable `tools/jre` drop-in → user-scope Windows installs (`%LOCALAPPDATA%\Programs\...`, no admin) → machine-wide roots (`_WINDOWS_JAVA_ROOTS`) → POSIX globs (`/usr/lib/jvm/*`, macOS `JavaVirtualMachines`). Newest version wins (`_java_version_key`). Rescues the common Windows case where Java exists but isn't on PATH.
- `_mpxj_home()` — `$SF_MPXJ_HOME`, else **walks up every parent** from the module looking for `tools/mpxj/classes/MpxjToMspdi.class`. This handles both the repo checkout (`parents[3]`) and a deployed install where the installer copied `tools/mpxj` beside the venv (ADR-0193).
- **One-shot path** (`_convert_one_shot`): builds `java -cp <classes>:<lib/*> MpxjToMspdi <in> <out>`, run with `subprocess.run`, `stdin=DEVNULL`, `CREATE_NO_WINDOW` on Windows, 300 s timeout (`_CONVERT_TIMEOUT_S`). The `stdin=DEVNULL` + `CREATE_NO_WINDOW` pairing is deliberate: under windowless `pythonw.exe` a console child could flash a window and hang on an inherited stdin handle.
- **Persistent batch JVM** (`_MpxjServer`, `_LazyBatch`, `mpxj_batch_session`): `mpxj_batch_session()` is a context manager (ContextVar-scoped, re-entrant, thread-scoped) that converts every `.mpp` in the block through ONE heap-capped JVM (`java -Xmx<SF_MPXJ_XMX, default 1g> ... --server`). A daemon reader thread pumps tagged lines into a `queue.Queue` so `convert()` can wait with a timeout (a hung JVM can never block forever). It is **an optimisation only**: `_convert()` transparently falls back to the one-shot subprocess if the server never starts (`_try_start_server` returns `None`), dies mid-batch (`_ServerDown`), or reports OK but produces no file — parsed result is identical either way. `SF_MPXJ_NO_SERVER` forces the one-shot fallback (and is how the one-shot tests stay one-shot). `_LazyBatch` starts the JVM only on the first `.mpp` actually converted (a text-only ingest never spawns Java).
- Entry point `parse_mpp(path)`: validates the file exists and `MpxjToMspdi.class` is present (else `ImporterError` pointing at `setup.sh`/`SF_MPXJ_HOME`), converts into a `TemporaryDirectory`, reads the MSPDI as `utf-8-sig`, and delegates to `parse_mspdi_text(...)` recording the original filename as `source_file`.

Note: there is **no JDK/MPXJ job in CI** yet — `ci.yml`'s header explicitly defers it ("added when ingestion lands (M4)"). Parity/tests run against committed MSPDI/golden fixtures, so `.mpp`→MSPDI conversion is exercised locally/in-container, not on GitHub runners.

---

### 2. `tools/installer/` — installer generator (wheel → 9 one-file installers)

**`tools/installer/build_installers.py`** generates the nine installers (3 tiers × 3 OSes) from one wheel:
- Reads the wheel bytes, base64-encodes them; produces two payload encodings — a raw wrapped form (`{{WHEEL_B64}}`, for `.ps1`, in a `@'...'@` here-string) and a `#`-commented form (`{{WHEEL_B64_COMMENTED}}`, for `.sh`/`.command`, extracted by an embedded `awk` between `# ===BEGIN/END WHEEL_B64===` markers).
- `TIERS` table (the only tier-specific values): **tier1** = 16 GB / no GPU / `llama3.2:3b` / 2 GB; **tier2** = 64 GB / GPU / `llama3.1:8b` / 5 GB; **tier3** = 128 GB / GPU / `llama3.3:70b` / 43 GB.
- Substitutes `{{TIER_LABEL}}`, `{{TIER_SUFFIX}}`, `{{TIER_CONFIG}}`, `{{WHEEL_NAME}}`, and the payload into each template. Writes `.ps1` as `utf-8-sig` + CRLF, `.sh`/`.command` as `utf-8` + LF (chmod 0755). **Stdlib-only.**
- Usage: `python -m build --wheel --outdir dist/wheel` then `python tools/installer/build_installers.py dist/wheel/schedule_forensics-*.whl`.

**Templates** (bodies are per-OS-family identical across tiers by construction; only the CONFIG block differs):
- `tools/installer/template.ps1` — Windows PowerShell 5.1+; steps: machine-fit (RAM/GPU, warn-only) → Python 3.11+ (winget `Python.Python.3.12 --scope user` if missing, no admin) → wheel→own venv (`--force-reinstall`, import-check) → optional psutil → **copy repo `tools/mpxj` beside venv** (native `.mpp`) → optional Java 17 (portable Microsoft OpenJDK **zip** into `%LOCALAPPDATA%\Programs\Microsoft`, no UAC/admin — ADR-0192) → optional Ollama+model → ONE self-stopping Desktop/Start-Menu shortcut (`pythonw.exe -c "...launcher import main; main(port=8321)"`) + uninstaller + README. Has a `Find-Python` unary-comma fix (ADR-0191) so a python-only machine (no `py` launcher) doesn't unroll the 1-element array into a bare string.
- `tools/installer/template.sh` — Linux; installs to `$HOME/.local/share/ScheduleForensics`, `~/.local/bin` symlinks + `.desktop` entries, start/stop/uninstall scripts. Stop hits `POST /api/shutdown`.
- `tools/installer/template.command` — macOS; installs to `~/Library/Application Support/ScheduleForensics`, Desktop `.command` launchers; Python via Homebrew, Ollama via `brew install --cask ollama`; notes Apple-silicon unified memory as GPU.
- All three carry an `SF_INSTALLER_SMOKE=1` non-interactive mode (temp root, prompts skipped, no Ollama/Java, no shortcuts) — the CI smoke hook. App port is pinned to **8321**.

The **embedded-wheel lockstep**: the wheel is pure-Python, but the ~17 MB Java converter isn't in the wheel — each installer copies the repo's `tools/mpxj` next to the venv where runtime walk-up discovery finds it (ADR-0193); an honest warning fires if the installer is run outside the checkout.

---

### 3. `installer/` — the generated distributables

Nine generated files (~1.27 MB each, dominated by the embedded base64 wheel):
- `installer/install-tier{1,2,3}.ps1` (Windows), `.sh` (Linux), `.command` (macOS).
- `installer/README-DISTRIBUTABLE.md` — the recipient-facing tier/OS matrix + install/uninstall/privacy notes; documents regeneration.

**Lockstep is test-enforced** by `tests/installer/test_installers.py`:
- Each OS family shares a byte-identical body across tiers (no drift); tier CONFIG blocks match the spec.
- The embedded payload decodes to a **CRC-valid zip** whose version matches `pyproject.toml`, that contains `web/static/*` (≥30 assets) and `web/examples/*` (the packaging gap that once shipped a wheel crashing at `/static` mount).
- All three OS families embed the **same** wheel.
- `test_embedded_wheel_is_in_lockstep_with_the_source_tree` compares every `schedule_forensics/**` file inside the embedded wheel **byte-for-byte** against `src/` (ADR-0148, the "stuck-overlay" incident where a merged JS fix wasn't rebuilt into the installers) — any source change to a packaged file fails until the wheel + installers are regenerated.
- Plus regression guards for the PS1 python-only discovery fix, the no-admin Java/Python paths, MPXJ deployment + single self-stopping icon, and a "no CUI/secret-shaped content in installers" check.

---

### 4. `.github/workflows/ci.yml` — the CI gates

Triggers: `push` on `main`, all `pull_request`, `workflow_dispatch`. `permissions: contents: read`; concurrency-cancel per ref. **Matrix:** Python **3.11 and 3.13** on `ubuntu-latest` (`fail-fast: false`). Steps, in order, on `pip install -e '.[dev]'`:
1. `ruff check .`
2. `ruff format --check .`
3. `mypy` (strict, configured in pyproject: `strict=true`, `files=["src"]`, pydantic plugin)
4. `pytest --cov=schedule_forensics --cov-report=term-missing --cov-fail-under=70` (overall coverage ≥70%)
5. `coverage report --include='*/schedule_forensics/engine/*' --fail-under=85` (engine ≥85%)
6. `pytest -m parity -p no:cacheprovider` (Acumen Fuse v8.11.0 + SSI golden gate; the `parity` marker is declared in pyproject)
7. `bandit -q -r src`
8. `pip-audit --progress-spinner=off`

A stable aggregate job named **`check`** (`needs: test`) gives branch protection one context regardless of matrix dimensions. Note the local full gate in `CLAUDE.md` additionally lists `node --check src/.../static/*.js` — that step is **local-only and NOT in `ci.yml`** (54 vendored JS files under `src/schedule_forensics/web/static/`, no bundler). The egress guard (`src/schedule_forensics/net_guard.py`) and air-gap guarantees are enforced through the pytest suite (`tests/guards/test_egress.py`, `tests/guards/test_endpoint_scheme.py`, `tests/guards/test_precommit_blocklist.py`, `tests/web/test_airgap.py`), not a separate CI step.

**`.github/workflows/installer-smoke.yml`** — real-OS installer verification, triggered only on `installer/**`, `tools/installer/**`, or the workflow itself (the files are large; no need to run every commit):
- **windows-latest:** enables `git config --system core.longpaths true` before checkout (some `00_REFERENCE_INTAKE/ssi/` names exceed MAX_PATH); parses all three `.ps1` via `[Parser]::ParseFile` (syntax gate); smoke-runs tier1 (embedded wheel → venv → import; asserts `web/static` shipped); then re-runs tier1 with a failing `py.cmd` stub ahead of PATH to exercise the python-only discovery path (ADR-0191 regression).
- **ubuntu-latest:** `bash -n` syntax-checks the `.sh`/`.command` family, then smoke-runs tier1 **end-to-end**: install → `start` → poll `http://127.0.0.1:8321/` → fetch `/static/app.js` → `stop` (confirms server is actually down) → `uninstall` (confirms dir removed).

---

### 5. Launcher & entry points

**`pyproject.toml`** declares two console scripts (`[project.scripts]`):
- `schedule-forensics = "schedule_forensics.launcher:main"` — the one-command desktop launcher.
- `schedule-forensics-report = "schedule_forensics.exhibits.cli:main"` — headless exhibit-pack generator.

Package: `schedule-forensics` v**1.0.51** (lockstep-bumped every src PR; snapshot detail below may lag — pyproject.toml is authoritative), `requires-python >=3.11`, setuptools/wheel build backend, `packages.find` under `src`. Runtime deps: `pydantic>=2`, `fastapi>=0.110`, `uvicorn>=0.29` (plain, **not** `uvicorn[standard]` — avoids the forbidden `websockets` dep), `jinja2`, `python-multipart`. `[monitor]` extra = `psutil`; `[dev]` = pytest/pytest-cov/ruff/mypy/bandit/pip-audit/httpx (dev-only; httpx is a forbidden *runtime* dep) + `setuptools>=83.0.0` (pinned to clear PYSEC-2026-3447 in the dev venv's pip-audit). `[tool.setuptools.package-data]` ships `web/static/*` + `web/examples/*` (the runtime data the earlier packaging gap missed). `web/app.py` is E501-exempt.

**`src/schedule_forensics/launcher.py::main()`** — picks a free **loopback** port (`find_free_port`), refuses any non-loopback host (`is_loopback_host`, Law 1), opens the browser on a 1 s delay timer, and serves the FastAPI app (`web.app.serve` + `create_app(auto_shutdown=True)`) on 127.0.0.1. `_ensure_streams()` rebinds `sys.stdout`/`stderr` to devnull under `pythonw.exe` (else uvicorn's `isatty()` call crashes a windowless launch) — deliberately a devnull sink, not a log file, so CUI schedule names in request paths stay off disk. Lazily manages a local `ollama serve` via `OllamaLauncher` (started only when the operator enables the Ollama backend; stopped on exit / `atexit`). `multiprocessing.freeze_support()` at the bottom for a possible frozen build and the SRA Monte-Carlo worker offload.

**`src/schedule_forensics/exhibits/cli.py::main()`** — argparse CLI (`--inputs`/`--payload`/`--out`/`--target-uid`/`--basis`/`--format`/`--json-summary`/`--force`); never starts the web server; deterministic `run_id = sha256(...)[:16]`, no timestamps (two identical runs are byte-identical). Documented exit codes: `0` ok, `2` ingest fail, `3` no terminus, `4` engine artifacts missing (CP-basis engine not built — render from `--payload` meanwhile), `5` output dir not empty without `--force`.

---

### 6. Other build-adjacent tooling

- `tools/make_test_projects.py` — regenerates the synthetic MSPDI verification battery (TP1–TP4) into `tests/fixtures/test_projects/` (the only schedule-format path allowed in git), using an MS-Project-faithful block calendar so MSP re-derives identical dates; pinned by `tests/test_projects/`.
- `.githooks/pre-commit` — the CUI pre-commit guard (blocks `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` outside the `tests/fixtures/` allowlist and the `inherited_from_main` exception); activated by the SessionStart hook, mirrored by `tests/guards/test_precommit_blocklist.py`.
- `src/schedule_forensics/net_guard.py` — the fail-closed net-egress guard: `assert_local_only()` raises `CUIEgressError` if any forbidden HTTP/cloud distribution enters the *declared runtime* dependency closure (checked against declared runtime requirements, so build-time `requests`/`urllib3` in the dev venv don't false-positive); `is_loopback_host()` is the predicate the Ollama client uses. Backed by `tests/guards/test_egress.py`.

**Key numbers:** MPXJ 16.2.0 (24 jars, ~17 MB); 9 installers × ~1.27 MB; app port 8321; batch JVM heap cap 1g (`SF_MPXJ_XMX`); conversion timeout 300 s; JVM boot timeout 60 s; CI on Python 3.11 + 3.13; coverage gates overall ≥70% / engine ≥85%.
