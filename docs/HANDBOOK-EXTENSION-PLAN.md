# Handbook & Assessment-Deck extension plan

Source-verified catalogue of measures, visuals, and an organization scheme to extend the tool,
mined from the **NASA Schedule Management Handbook** (public; 409 pp.) and two operator
**Assessment / Analysis** decks, compared against the tool's existing ~90 metrics
(`web/help.py`), nav (`web/app.py`), `engine/metrics/`, and the `Task`/`Schedule` model.

> **CUI note.** The decks may be CUI: only measure *names, definitions/formulas, and
> visualization concepts* were extracted — never schedule data, project names, or project-tied
> numbers. The decks are **not** committed (Law 1). The handbook is the public NASA document.

Inputs key: ✅ model already carries the input · ⚠️ derivable, needs new computation ·
❌ model does not carry it (needs a model/importer change).

---

## A. Missing metrics

### A1 — Health-check / structural (Deck-1 s.58–72; Handbook Fig. 6-9, pp.170–172) — feasible now

These reuse fields the model already has (rels, actuals, float from CPM, baseline, lag, wbs,
deadline, constraint, `is_level_of_effort`, `is_milestone`). The tool already has DCMA-01..07,
`merge_hotspot` (>2 preds), `logic_on_summary_tasks`, `insufficient_detail` — the below are NEW:

| Metric | Definition / rule | Inputs |
|---|---|---|
| Out-of-Sequence Logic | FS successor with actual start/finish before predecessor started | ✅ |
| Redundant Logic | link A→C where a path A→…→C (len ≥2) already exists | ✅ |
| Improper Logic (circular/reverse) | cycle in the dependency graph; reverse (lead) links | ✅ |
| Critical Diverge Hotspot | critical activity with > 2 successor links | ✅ |
| Critical Logic Hotspot™ | critical activity with > 2 preds AND > 2 succs | ✅ |
| Critical Merge Hotspot | critical activity with > 2 predecessor links | ✅ |
| LOE on the critical path | `is_level_of_effort` AND effective-critical (handbook: CP cannot include LOE) | ✅ |
| Milestone with duration > 0 | `is_milestone` AND baseline_duration > 0 | ✅ |
| Activity with duration = 0 | not milestone, not summary, duration == 0 | ✅ |
| Open Start / Open Finish | only FF/SF preds → open start; only SS/SF succs → open finish | ✅ |
| Unsatisfied Constraint | hard-constraint date the CPM date violates | ✅ |
| Deadline artificial neg-float | logic finish past a set deadline | ✅ (`deadline`) |
| Riding the Data Date | planned activity whose start == status date (bow-wave signature) | ✅ |
| Expected-finish-but-in-progress | percent == 100 AND no actual_finish | ✅ |
| Missing WBS | non-summary AND wbs empty (drops from rollups) | ✅ |
| Missing Baseline Start/Finish | baseline_start/finish is None (blocks BEI etc.) | ✅ |
| Hidden Duration (+ critical variant) | a predecessor lag > 35% of the activity's duration | ✅ |
| Zero-Days Float | total_float == 0; should not exceed ~15% | ✅ |
| High Float vs remaining duration | total_float > 10% of remaining project duration; ≤ 20% | ✅ |
| Inconsistent Vertical Integration | like tasks not rolling up consistently | ⚠️ hierarchy |
| Estimated Duration (placeholder) | MS Project "Estimated" duration flag | ❌ importer field |

### A2 — Deterministic performance (Handbook §7.3.3.1, pp.293–318) — medium

| Metric | Definition | Formula (verbatim) | Inputs |
|---|---|---|---|
| Schedule Variance (days) — per-activity + project SVt | baseline-expected vs actual progress, in days | activity: `actual_finish − baseline_finish` (days); project `SVt = ES − AT` | ✅ |
| TFCI (Total Float Consumption Index) | rate of total-float consumption → forecast | `(Actual Duration + CP Total Float) / Actual Duration` | ⚠️ |
| Predicted CPTF | total float likely at the baseline finish | `Planned Duration × (TFCI − 1)` | ⚠️ |
| TFCI forecast-finish date | forecast finish from CPTF | `Baseline Finish + Predicted CPTF` (calendar add) | ✅ |
| Float Erosion by WBS | per-WBS min/avg float; current vs plan vs prior, stoplight | grouping of existing float by WBS | ✅ |

> BEI, CEI, HMI, SPI, SPI(t), CPI, CPLI, ES, cumulative finish curves are **already in the tool
> and match the handbook formulas** (HB pp.299–308). Action: add the handbook §7.3.3 citation to
> their `help.py` `source=` fields (currently cited to Acumen/PASEG).

### A3 — SRA / stochastic (Deck 2; Handbook §6.3, §7.3.3.2) — ❌ separate epic

Criticality Index, Cruciality, Duration/Cost Sensitivity (tornado), **Schedule Sensitivity Index**
(`SSI = CriticalityIndex × σ(activity)/σ(project)`, HB p.254), probabilistic critical path,
confidence levels / completion range, JCL, probability of on-time delivery, coefficient of
variation, risk-based margin sufficiency. **Needs a Monte-Carlo engine + duration-uncertainty and
discrete-risk model fields the tool does not have.** Defer unless an SRA module is chartered.
(NB: the tool's existing "SSI driving-slack" is the unrelated MS-Project add-on, not this SSI.)

### A4 — Schedule margin (Handbook §7.3.3.1.6, pp.309–314) — ❌ needs a margin-task identity

Margin Consumption / Effective Margin / Margin Burndown ("zero out margin tasks, measure how far
the finish pulls in"). The compute reuses the existing `path_counterfactual` engine — cheap — **but
the model has no margin-task field.** Feasible once margin tasks are identifiable (a model field +
importer support, or an operator-supplied name convention).

---

## B. New visual types

| Visual | Source | Axes / data (from existing computed values) | Insight |
|---|---|---|---|
| Stoplight / tripwire chips | HB Figs 7-10..7-38; Deck-1 s.29,31 | each metric value → green/yellow/red vs its threshold (already in `MetricResult`) | the handbook's canonical presentation |
| Scatter plot (per-activity) | HB §6.3.2.5.2.1; Deck-2 s.18,144 | e.g. total_float × baseline_duration; %complete × float; colored by critical | clusters/outliers no count shows |
| Histogram / distribution | HB §6.3.2.5.2.2 | bins of total_float or finish-variance days | float-padding spikes, variance spread |
| Float Erosion table + per-WBS trend | HB Figs 7-34/7-35 | WBS rows × plan/current/prior float + stoplight | low-IMS-level issues before margin is hit |
| Tornado / driver bar (deterministic) | HB Fig 6-52; Deck-2 s.144,176 | activities ranked by driving-slack-to-finish; x = days | deterministic "what drives the finish" |
| BEI/CEI/HMI combined panel | HB Fig 7-21 | three series over versions (all already computed) | the handbook "are we executing?" panel |
| SV/SVt trend with favorable/unfavorable bands | HB Figs 7-12/7-13 | SVt days over versions, zero line | standard variance trend |
| Margin burndown | HB Figs 7-30..7-33 | planned vs actual margin over time | only if A4 lands |
| CDF / confidence S-curve | HB Figs 6-49/6-55 | confidence × date | out of scope without SRA |

---

## C. Handbook-framed organization

The handbook's five sub-functions: **Planning (§4) · Development (§5) · Assessment & Analysis
(§6) · Maintenance & Control (§7) · Documentation & Communication (§8)**, with a cross-cutting
**4 Reliability Dimensions** (Comprehensiveness, Construction, Realism, Affordability) and §6
Assessment's **6 checks in 2 tiers** (Requirements, Health, Risk-ID&Mapping; Critical/Structural,
Basis, Resource-Integration).

Proposed nav regrouping (this is a forensic/assessment tool, so §6 + §7.3.3 are home):

- **Assessment — "trust the schedule":** Health Check (rename of *Quality Ribbon*, + A1) ·
  Critical/Driving-Path & Structural Check (group Path Analysis, Driving Path, Critical-Path
  Evolution; add a *Shock Test* using `path_counterfactual`) · Requirements / Vertical-Traceability
  (WBS rollup + Missing-WBS / Inconsistent-Vertical-Integration).
- **Control — "achieve & track the plan":** Performance Metrics (group Bow Wave/CEI, BEI/HMI,
  Trend; + combined BEI/CEI/HMI panel + SV/SVt + TFCI) · Finish & Slippage · Forecast (+ TFCI) ·
  S-Curve · Year Phases · Float Erosion (+ Margin if A4).
- **Reporting & Briefing (§8):** Diagnostic Brief, Executive Briefing, Metric Dictionary.
- **Risks & Opportunities:** align to the handbook's Risk-ID & Mapping language; SRA is a future tier.

Tag each metric in `help.py` with its Reliability Dimension so the UI can present the framework.

---

## D. Prioritized build plan (PR-sized, easiest/highest-value first)

1. **This plan doc** + add handbook §7.3.3 citations to `help.py` for the metrics already present.
2. **Cheap new health checks** (A1, all ✅) — `engine/metrics/health_extra.py` + ribbon + dictionary + tests.
3. **Logic-integrity** checks (out-of-sequence / redundant / circular) — `engine/metrics/logic_integrity.py`.
   ✅ **DONE** — `compute_logic_integrity(schedule)` (parity-isolated `LogicCheck` dataclasses):
   **out-of-sequence** (FS successor that recorded progress before its predecessor finished) and
   **redundant logic** (a direct A→C a longer A→…→C path already implies; iterative reverse-topo
   transitive closure, skipped & flagged on a cyclic or oversize network). *Circular logic was
   dropped from this tranche on purpose:* CPM refuses a cyclic network (`CPMError`), so the panel —
   which renders only after CPM solves — would always read zero. Surfaced as a "Logic integrity"
   stoplight panel on /analysis next to the structural health checks.
4. **Schedule Variance (days) + project SVt** + **combined BEI/CEI/HMI** and **SV/SVt** trend panels.
5. **TFCI / Predicted CPTF / TFCI forecast-finish** — 4th method in `engine/forecast.py`.
6. **Scatter + histogram** generic chart components (reused across views).
7. **Float Erosion by WBS** table + trend.
8. **Stoplight/tripwire** rendering of existing metrics (presentation; thresholds already present).
9. **Handbook-framed nav reorganization** + Reliability-Dimension tags (after the metrics exist).
10. **Unsatisfied-constraint / deadline neg-float**, then **Inconsistent Vertical Integration**, then **Estimated-Duration** importer field.

**Deferred epics (need a decision / new inputs):** SRA/Monte-Carlo (A3) — needs a simulation
engine + uncertainty inputs; Schedule Margin (A4) — needs a margin-task identity.

**Verification pointers:** handbook pp.293–318 (deterministic perf), pp.249–259 (SRA), pp.170–172 /
Fig 6-9 (health); Deck-1 s.58–72 (metric-library names), s.99–107 (Shock Test); Deck-2 s.18,144
(chart catalog). Tool baseline: `web/help.py`, `engine/metrics/ribbon.py`,
`engine/metrics/dcma14.py`, `engine/metrics/evm.py`, `model/task.py`.
