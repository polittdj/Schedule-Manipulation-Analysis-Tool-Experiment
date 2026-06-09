# Metric catalog — formulas, thresholds, citations

Phase 1 extraction of every schedule/EVM metric the tool must define and (where in scope)
reproduce. Feeds the §6.A in-tool **metric dictionary** (plain-language + formula + citation),
the §6.E **DCMA audit**, and the §6.B/§6.C **parity** work. Sources (Drive IDs in
`INTAKE-MANIFEST.md`):

| Doc | Role | Version |
|---|---|---|
| `DeltekDECMMetricsOct2025.xlsx` | **Primary formula/threshold source** — DCMA/DECM compliance metrics | Deltek **EVMS-DECM Metrics V7.0** |
| `DeltekAcumen811MetricDevelopersGuide.pdf` | Acumen metric **engine** reference (formula syntax, fields, scoring) | Acumen **8.11** (Dec 2025) |
| `DeltekAcumen811CostDataCsvStructure.pdf` | Cost-data **field dictionary** (EVM fields used in formulas) | Acumen **8.11** |

> **Two metric frameworks — keep them distinct (and both cited):**
> 1. **DCMA 14-point + Acumen "Schedule Quality" summary** — the framework the **Project 2-5
>    golden exports actually used** (Logic, Leads, Lags, Hard Constraints, High Float, Negative
>    Float, Invalid dates, Missed activities, CPLI, BEI, …). Golden values in
>    `PARITY-TARGETS.md`. **This is the primary parity target.**
> 2. **DECM V7.0 (32 EIA-748 guidelines, 143 metrics)** — the broader EVMS-compliance library in
>    the `.xlsx`. The DCMA-14-equivalent **schedule** checks sit under **Guideline 6** (+ a few in
>    G3/G8). The rest are EVMS **cost** compliance (implement as an optional/extended audit).

Legend: Threshold like `X=0`, `X/Y≤5%` is the pass/fail rule (numerator X over denominator Y).
Type `A`=automatic/computed, `M`=manual, `A/M`=either. Level `ACT`=activity, `WP`=work package,
`CA`=control account. `WP_RL`=work-package rounding level. Leads = negative lags. Formulas
quoted as stated in the source; spot-check any single formula against the native sheet before
relying on byte-exact text (the `.xlsx` export merged cells).

---

## 1. Schedule health — DCMA-14 ribbon (PRIMARY parity framework)

These are the checks Acumen's "Fuse® Analyst Report" ribbon computed for Project2/Project5
(golden values in `PARITY-TARGETS.md §B`). Implement these to exact parity first.

| # | Check | Definition | Typical threshold |
|---|---|---|---|
| 1 | **Logic** | Incomplete tasks missing a predecessor and/or successor | ≤ 5% |
| 2 | **Leads** | Relationships with negative lag | 0 |
| 3 | **Lags** | Relationships with positive lag | ≤ 5% |
| 4 | **Relationship Types** | % FS vs SS/FF/SF (SF discouraged; FS preferred) | FS ≥ 90% |
| 5 | **Hard Constraints** | Tasks with hard/mandatory constraints | ≤ 5% |
| 6 | **High Float** | Incomplete tasks with total float > 44 working days | ≤ 5% |
| 7 | **Negative Float** | Incomplete tasks with total float < 0 | 0 |
| 8 | **High Duration** | Incomplete tasks with baseline duration > 44 working days | ≤ 5% |
| 9 | **Invalid Dates** | Actual dates in the future / forecast dates in the past (vs status date) | 0 |
| 10 | **Resources** | Tasks with $/hours but missing resource (if cost/resource-loaded) | — |
| 11 | **Missed Activities** | Tasks that should have finished by status date but slipped/incomplete | ≤ 5% |
| 12 | **Critical Path Test** | Does a 600-day test-delay on a critical task push the finish ~600 days? (pass/fail) | pass |
| 13 | **CPLI** | Critical Path Length Index = (crit path length + total float) / crit path length | ≥ 0.95 |
| 14 | **BEI** | Baseline Execution Index = tasks completed / tasks baselined-to-complete | ≥ 0.95 |

*(Confirm each exact threshold/definition against the SSI/Acumen docs in Phase 2; Acumen's
"Schedule Quality" summary (`PARITY-TARGETS.md §A`) adds Logic Density™, Insufficient Detail™,
Merge Hotspot, Number of Lags/Leads as separate metrics.)*

---

## 2. DECM V7.0 — Guideline 6 (schedule) metrics (formulas)

Activity-level (ACT), % of activities unless noted. These are the authoritative DECM formulas
for the schedule checks; cite metric IDs in the tool.

### 06A204b — Open starts/finishes (dangling logic) · `X/Y = 0%` · A
Incomplete non-LOE tasks/milestones with an open start or finish.
```
Filters: IsLevelOfEffort = False
SUM( IF( ActivityType="Milestone",
  IF( ( ((NumberOfPredecessors+NumberofExternalPredecessors=0)*(INT(PrjMinBStart)<>INT(BaselineStart)))
      + ((NumberOfSuccessors+NumberofExternalSuccessors=0)*(INT(PrjMaxBFinish)<>INT(BaselineFinish))) >0),1,0),
  IF( ( ((NumberOfFSPredecessors+NumberOfSSPredecessors+NumberofExternalPredecessors=0)*(INT(PrjMinBStart)<>INT(BaselineStart)))
      + ((NumberOfFSSuccessors+NumberOfFFSuccessors+NumberofExternalSuccessors=0)*(INT(PrjMaxBFinish)<>INT(BaselineFinish))) >0),1,0) ) )
```

### 06A205a — Lags · `X/Y ≤ 10%` · A
`SUM( IF(NumberofLags>0,1,0) )` · Tripwire `AND(NumberofLags>0)`

### 06A208a — Summary tasks carrying logic · `X = 0` · count
`SUM(IF( ( ((NumberOfPredecessors>0)*(Start>=_PeriodStart)) + ((NumberOfSuccessors>0)*(Finish<=_PeriodFinish)) )>0 ,1,0) )`

### 06A209a — Hard constraints · `X/Y = 0%` · A
MSP set: MandatoryStart/Finish, MustStartOn/MustFinishOn, StartOnOrBefore, FinishOnOrBefore,
StartAndFinish. (OPP/P6: only MandatoryStart/MandatoryFinish.)
`SUM(IF( (ActivityConstraint="MandatoryStart")+(…)+(ActivityConstraint="StartAndFinish") >0,1,0) )`

### 06A210a — LOE with discrete successors · `X/Y = 0%` · A
`Filter: IsLevelOfEffort=True; SUM( (NumberOfDiscreteSuccessors>0)*1 )`

### 06A211a — High total float, inadequate rationale (sampled) · `X/Y ≤ 20%` · M
"High float" = `TotalFloat > 44` working days (tripwire). Numerator = sampled high-float items
with inadequate rationale.

### 06A212a — Out-of-sequence · `X = 0` · count
`SUM(IF( IsDCMAOutOfSequence=true, DCMAOutOfSequenceCount, 0) )` (uses Acumen's DCMA OOS fields).

### 06A501a — Missing baseline dates · `X/Y ≤ 5%` · A
`SUM(IF( ( ((BaselineStart="")*(Start>=_PeriodStart)) + ((BaselineFinish="")*(Finish>=_PeriodFinish)) >0),1,0) )`

### 06A504a/b — Actual start/finish changed vs previously reported · `X/Y ≤ 10%` · A
504a `SUM( IF(INT(PreviousActualStart)<>INT(ActualStart),1,0) )` (filter PreviousActualStart≠"");
504b same with Finish. Paired snapshot variant detects deletion next period via `SnapASNext="-"`.

### 06A505a/b — Missing actual start (in-progress) / actual finish (complete) · `X/Y ≤ 5%` · A
505a `Filter 0<PhysicalPctComplete<1; SUM((ActualStart="")*(Start>=_PeriodStart))`;
505b `Filter PhysicalPctComplete=1; SUM(IF(ActualFinish="",1,0))`.

### 06A506a — Invalid actual dates (actuals after status date) · `X/Y ≤ 5%` · A
`SUM(IF( (INT(ActualStart)>INT(ProjectTimeNow))+(INT(ActualFinish)>INT(ProjectTimeNow)) >0,1,0) )`

### 06A506b — Invalid forecast dates (forecast before status date) · `X = 0` · count
`SUM(IF( (NOT(ISNUMBER(ActualStart))*(INT(EarlyStart)<INT(ProjectTimeNow))) + (NOT(ISNUMBER(ActualFinish))*(INT(EarlyFinish)<INT(ProjectTimeNow))) >0,1,0) )`

### 06A506c — Forecast "riding" the status date 2 consecutive periods · `X/Y ≤ 1%` · A
Stall indicator; compares EarlyStart/Finish proximity to TimeNow across current + previous
snapshot (full formula in source).

### G6 manual/structural schedule metrics
| ID | Question | Threshold |
|---|---|---|
| 06A101a | Each non-LOE WP/PP/SLPP has task(s) in both IMS and EV cost tool (auto) | `X/Y=0%` |
| 06A102a | Authorized **risk-mitigation** activities incorporated into IMS | `X/Y≤10%` |
| 06A301a | Lower-level baseline/forecast dates traceable to higher-level IMS | `X/Y=0%` |
| 06A301b | IMS baseline finish aligns with contractual/CLIN (POP) finish | `X=0` |
| 06A401a | Tool critical path = longest duration / least float | `X=0` |
| 06A401b | Key contractual milestones/events present in IMS | `X/Y=0%` |
| 06I101b | Schedule-margin tasks represent risk impact (TaskSubtypeID=SCHEDULE_MARGIN) | `X=0` |
| 06I201a | Schedule Visibility Tasks (SVTs) identified/controlled | `X=0` |

---

## 3. EVM performance indices (schedule-relevant; build scope)

Compute and display these (units/signs per §3). Derive from the cost fields in §6.

| Index | Formula | Notes |
|---|---|---|
| **SPI (cost-based)** | BCWP / BCWS | Schedule Performance Index |
| **SPI(t) / SPIt (time-based)** | Earned Schedule / Actual Time | "Earned Schedule" method |
| **CPI** | BCWP / ACWP | Cost Performance Index |
| **BEI** | tasks completed / tasks baselined-to-complete-by-status-date | DCMA #14; P2 0.74 → P5 0.59 |
| **CPLI** | (critical-path length + total float) / critical-path length | DCMA #13; ≥ 0.95 |
| **CEI** | completed-on-time / forecast-to-complete (start & finish variants) | "Current Execution Index" |
| **TCPI(BAC/EAC)** | (BAC−BCWP)/(BAC−ACWP) or /(EAC−ACWP) | per-CA fields `CA_TCPIeac`, `CA_CPIcum` |

## 4. DECM V7.0 — EVMS cost-compliance guidelines (extended/optional audit)

Catalogued for completeness; implement as an extended EVMS audit beyond the core schedule scope.
`$ ratio` = numerator/denominator are dollar sums.

| Guideline | Representative metrics (ID → check → threshold) |
|---|---|
| **G3** Schedule/cost integration | 03A101a baseline dates WAD↔IMS `≤5%`; 03A101c BAC↔WAD `≤10%`; 03A101e EV%C IMS↔cost `=0%`; 03A101f/g IMS↔cost-tool dates `≤0–5%`; 03A101h OBS / 03A101i WBS align `≤5%`; 03A102a/03A103a/b sub-reconciliation `≤5%` (M) |
| **G8** Time-phased PMB/SLPP | 08A101a TP-PMB↔IMS `≤10%`; 08I101a SLPP duration ≤1d `≤10%`; 08I102a/103a SLPP ACWP/BCWP `≤2%` |
| **G9** Work-auth timing | 09A101a auth before baseline start `≤10%`; 09A102a auth before actuals `≤10%`; 09A103a elements of cost defined `≤10%` |
| **G10** Work packaging/EVT | 10A102a single EVT per WP `≤5%`; 10A103a 0-100 EVT single-period `≤5%`; (+104a/105a/109b/201a/302a/b/303a) |
| **G12** Level of Effort | 12A101a LOE supportive `≤15%`; 12I101a LOE has SV `=0%`; 12A401a proactive LOE mgmt `≤5%` |
| **G14** MR / UB | 14A101a MR excluded from PMB `=0%`; 14A201a UB in PMB `=0%`; 14A202a UB scope `≤20%`; 14I101a sub MR traceable `≤5%` |
| **G16** Direct cost recording | 16A501a–d ACWP/BCWP cur/cum consistency `<5%`/`≤5%`; 16A502a actuals on completed work `<5%` |
| **G22** CV/SV generation | 22A101a CV/SV at CA level `=0%` (M); 22I102a BCWPCUM>BAC `=0%` |
| **G23** Variance analysis | 23A101a required VARs `≤2%`; 23A201a rate/volume & price/usage var formulas; 23A301a SV addresses critical/near-critical/driving path `<20%`; 23A401a root-cause/corrective `<15%` |
| **G25** WBS/OBS summarization | 25A101a sum through WBS / 25A102a through OBS `=0%` (BCWS/BCWP/ACWP/BAC/EAC, >$100 tol) |
| **G26** Corrective actions | 26A201a tracked `<20%`; 26A202a monitored to closure `<10%` |
| **G27** EAC/ETC | 27A102a TP-ETC aligns w/ remaining IMS `<10%`; 27A103a EAC exists `=0%`; 27A104b ETC on completed WP `X=0`; 27A105a ACWPCUM>EAC `≤0%`; 27A106a EAC reflects performance (`|TCPIeac−CPIcum|>0.1`) `<25%`; 27I101a ETC for incomplete BAC>0 `=0%` |
| **G29** Reconciliation/replanning | **29I401a baseline dates changed to mask variances** (snapshot detector) `X=0`; 29A401a open-WP BAC change `X=0`; 29A601a rolling-wave detail planning `≤10%`; 29I402a–d LOE budget time-phasing `=0%` |
| Other (G1,2,4,5,7,11,13,15,17–21,24,28,30–32) | mostly manual/structural (single WBS/OBS, overhead, summarization, material accounting, change control). Automated: 05A101a/102a/103a one OBS/CAM/WBS per CA. |

> **Forensic relevance (§6.D):** `29I401a` (baseline dates changed to mask variances) and the
> `06A504*` (actual dates changed/deleted next period) snapshot detectors are direct
> **schedule-manipulation** signals — prioritize these for the manipulation-trend analysis.

## 5. Acumen formula engine (for parity-accurate implementation)

- Each metric: **Inclusions → Filters → Formula**, with up to 3 formulas (**Primary** = array
  count/value; **Secondary** = ratio/% , often "percentage of primary"; **Tripwire** = per-record
  Boolean flag). CA/WP metrics add a **Secondary Tripwire** (evaluates underlying activities).
- Shorthand: `IF(c,1,0)≡(c)`; `SUM(IF(a)*IF(b))≡SUM((a)*(b))`; OR via `+ … >0`; AND via `AND(...)`.
- Functions: `IF, SUM, AND, MAX, AVERAGE, COUNTIF`; Acumen-specific `FISCALPERIODNUM(date,Project)`
  (needs fiscal calendar) and `SNAP(period).<field>` cross-snapshot lookups (`SNAP(-1)` = previous;
  powers all "changed/deleted next period" detectors).
- Key schedule fields: `IsOutOfSequence`, `IsDCMAOutOfSequence`, `DCMAOutOfSequenceCount/Links`,
  `Number of FF/FS/SF/SS Predecessors/Successors`, `Number of External Pred/Succ`,
  `Number of Discrete Successors`, `Number of Lags/Leads`, `Maximum FF/FS/SF/SS Lag`,
  `Project Critical Path Test`, `Project Minimum Float`, `Previous Actual Start/Finish`,
  `BaselineStart/Finish`, `Early/Late Start/Finish`, `ActivityConstraint`, `ProjectTimeNow`.
- Scoring: metrics tagged Bad/Neutral/Good, weights −10…+10, scorecard normalized 0–100; failing
  a "Good" metric doesn't penalize, any "Bad" prevents positive contribution. `<1E-05` ≈ "very
  small positive, distinct from exactly 0". Phase analyzer uses `_PeriodStart/_PeriodEnd` with
  prorating on/off.

## 6. Cost-data field dictionary (`…CostDataCsvStructure.pdf`)

CSV import template, 8 ordered blocks (the EVM fields the formulas reference):
- **Calendars / CalendarDets** (PeriodNumber, HoursInPeriod).
- **CPRs:** ReportStart/End, **CBB, TAB, PMB, ManagementReserve, DistributedBudget,
  UndistributedBudget** (→ G14).
- **Control Accounts / Work Packages:** WbsID/ObsID; Actual/Baseline/Early/Late/Forecast Start &
  Finish; **AcwpCum/Cur, BcwpCum/Cur, BcwsCum/Cur** (+ `…Hours`); **Bac, Eac, Etc,
  PercentageComplete**; **PerformanceMethod** (None, PercentComplete, ZeroHundred, HundredZero,
  FiftyFifty, LevelOfEffort, Milestone, PlanningPackage…); Status; indices **CPICur/Cum,
  SPICur/Cum, TCPIBacCur/Cum, TCPIEacCur/Cum**; TimePhase Acwp/Bcwp/Bcws/Etc Start & Finish.
- **Milestones; Summary Totals; Time Phase Periods** (Resource L/M/O/S; UnitID 1=$/2=Hours).

## 7. Completeness / caveats
- All 3 docs fully read by the extraction agent (large files retrieved+parsed in full).
- `.xlsx` = single worksheet, **143 metrics across G1–G32**, reconstructed by Metric-ID anchor;
  merged cells mean a given formula's exact text should be spot-checked against the native sheet
  before relying on byte-exact reproduction (numerators/denominators/thresholds are reliable).
- DECM library = **V7.0**; Acumen tooling = **8.11**. Acumen Fuse **v8.11.0** parity version is
  not printed in the exports — confirm out-of-band.
- The DCMA-14 ribbon (§1) is the **primary parity target**; DECM cost guidelines (§4) are an
  extended audit.

