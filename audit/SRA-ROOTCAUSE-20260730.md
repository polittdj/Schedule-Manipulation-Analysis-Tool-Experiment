# SRA root cause — the missing progress-override read (ADR-0309)

Date: 2026-07-30 · Reviewed commit at start: `b62ba01` (v1.0.124) · Method: measurement, against
committed reference artifacts only. Every number below was produced by running the tool; none is
transcribed from another report.

Companion: `audit/EXTERNAL-RECONCILIATION-20260730.md` (the four-way audit adjudication).
Supersedes the open question in `audit/SRA-PARITY-20260729.md` §8.

---

## 0. Headline

The SRA divergence is closed. Against SSI's own committed export, same inputs, 2000 iterations:

| metric | SSI oracle | before | **after** | gap |
|---|---|---|---|---|
| deterministic finish | 2029-04-19 | 2029-04-19 | 2029-04-19 | exact |
| deterministic percentile | 5.75 % | 40.70 % | **6.65 %** | 0.9 pp |
| σ (calendar days) | 64.744 | 125.5 | **65.5** | **1.2 %** |
| mean offset | +111.45 d | +26 d | **+109 d** | 2.4 d |
| P10 | +34 d | −146 d | **+27 d** | 7 d |
| P50 | +124 d | +29 d | **+123 d** | 1 d |
| P80 | +160 d | +133 d | **+160 d** | 0 d |
| P90 | +179 d | +187 d | **+176 d** | 3 d |

The cause was **not** a wrong formula, a wrong distribution, or the stored-date realignment. It was
that `engine/cpm.py` never read MS Project's `<Resume>` — the date MS Project itself records for
where an in-progress task's remaining work restarts.

---

## 1. The oracle was already in the repository

`audit/SRA-PARITY-20260729.md` §8 asked the operator for a new artifact (an SSI re-run with risks
disabled). It was not needed. Both halves of the comparison were already committed:

* **Output** — `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-7-29_11-57-1.xlsx`:
  focus `152 - QJ29ZvAvtEjBcpqHDer1`, 2000 iterations, risks/opportunities = Yes, Current Finish
  47227 (= 2029-04-19), and a 245-row histogram summing to exactly 2000 occurrences.
* **Input** — `00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp` carries SSI's entire SRA *input*
  set as MS Project custom fields:

  | field | alias | populated |
  |---|---|---|
  | `Flag6` | SSI SRA Event | 1 task — **UID 152** |
  | `Number13` | SRA Risk Ranking Factors | 1722 non-summary |
  | `Duration8` / `Duration9` | Best / Worst Case Duration | **919** non-summary, **0** of them complete |
  | `Number4` / `Duration4` | SSI SRA Risk Probability / Schedule Impact | **2** tasks |

  The register is exactly two risks: UID 900 (p = 0.6, `PT424H0M0S` = 53 working days) and UID 7552
  (p = 0.9, `PT800H0M0S` = 100 working days).

Both are now read by `tests/parity/test_sra_ssi_oracle_uid152.py`, the first SRA test whose expected
values come from the reference tool rather than the tool's own arithmetic.

**Conversion corroboration.** Converting the `.mpp` with the committed MPXJ produced **21,838,873
bytes**, byte-identical in size to the independent external conversion. Parsed identity matched on
every field: `Longstar Master IMS`, 2126 tasks / 1723 non-summary / 2699 relationships, 480 min/day
Mon–Fri, project start 2017-06-07 08:00, status date 2025-03-10 17:00, focus stored finish
2029-04-19 10:07:36.

## 1.3 The workbook's summary cells are a trap (independently re-derived)

`audit/SRA-PARITY-20260729.md` §1 found this; it reproduces exactly:

```
SSI reported StdDev  = 107.81976615712615
unweighted pop stdev = 107.81976615712644   over the 245 DISTINCT dates
SSI reported Mean    = 47322 ; unweighted mean = 47322.1918 -> 2029-07-23
```

`Mean Date` and `Standard Deviation` discard the `Occurrences` weights; `% Cumulative Probability`
does not (`1/2000 = 5e-4`). **The parity target is the occurrence-weighted histogram** — mean
+111.45 d, σ 64.744 d. Matching 107.82 would be matching an artifact of SSI's own export, and the
tool's working-day σ sits misleadingly close to it. `test_the_summary_cells_are_not_the_parity_target`
pins this so the trap cannot be walked into later.

**One correction to the prior evidence file:** it quotes SSI's deterministic percentile as 5.65 %
(strict `<`). The tool computes `bisect_right(...)/n`, i.e. `<=`. The apples-to-apples figure is
**5.75 %**. It does not change any conclusion.

---

## 2. Diagnosis

### 2.1 The measured signature pointed at a missing floor, not a wrong shape

Running the tool with SSI's own inputs, **P90 agreed within 8 days while P10 was 180 days out.** An
over-wide distribution is symmetric; a distribution missing a lower bound is not. That ruled out the
distribution family and the Best/Worst rule before any code was read.

### 2.2 Decomposition localised it to duration uncertainty

| config (2000 iters) | det pctile | mean off | σ cal d | min |
|---|---:|---:|---:|---|
| A durations + both risks | 40.70 % | +26 | 125.5 | −279 d |
| **B durations only** | **90.65 %** | **−143** | **99.0** | −279 d |
| C risks only, durations point-mass | 5.05 % | +173 | 58.5 | **0 d** |
| SSI oracle | 5.75 % | +111.45 | 64.74 | −114 d |

**The risk register alone was already nearly right** (5.05 % vs 5.75 %; σ 58.5 vs 64.74; minimum
exactly the deterministic date). Duration uncertainty alone put **90.65 %** of iterations *before*
the deterministic date. This reproduces the prior evidence file's "risks only → +176, σ 55.8" and
"duration-only σ 99 cal" independently.

### 2.3 The excess variance came from work behind the data date

SSI's implied duration-only spread is `√(64.74² − 55.8²) ≈ 33` cal d; the tool produced 99.
Restricting uncertainty to the 661 of 919 activities starting on/after the data date:

```
B   all 919 uncertain                      : sigma 99.018
B'  only the 661 starting >= the data date : sigma 21.139
```

A 4.7× variance inflation from the 258 activities behind the data date, with SSI's ≈33 between the
two. Mechanism: the tool floated the whole 8-year network from 2017-06-07, so a short draw anywhere
upstream cascaded to the focus; SSI does not.

### 2.4 The cause: `cpm.py` had no status-date concept at all

`grep -c "status_date\|status_offset" src/schedule_forensics/engine/cpm.py` → **0**. ADR-0106's
Decision text requires sampling remaining duration on a *"forward pass anchored at the status date"*.
That clause was never implemented. Consequences on the reference file:

* ordinary `compute_cpm` put UID 152 at **2025-06-30**, **1,388 calendar days** before its stored
  finish, and `_build_ssi_result` added that constant back as a display correction;
* the all-ML basis was a further **370 working days** shorter (92 in-progress tasks fed remaining
  rather than full duration), so ADR-0106's *"all-ML reproduces `compute_cpm`"* was **false**:

  | solve (focus UID 152) | offset | naive date |
  |---|---:|---|
  | ordinary `compute_cpm` | 979,919 | 2025-06-30 11:59 |
  | all full duration | 979,919 | 2025-06-30 11:59 |
  | all remaining duration | 802,319 | 2024-01-11 11:59 |
  | exact `_ml_minutes` | 802,319 | 2024-01-11 11:59 |

---

## 3. Why the two prior attempts failed — and why the premise was wrong

ADR-0108 declined this fix because two attempts to reschedule remaining work from the data date each
regressed EVM1's correct finish and broke Project2/5 parity, concluding the ahead/behind judgement
*"cannot be reverse-engineered safely from two data points."*

**Correct about the unconditional floor. Wrong that the judgement needed deriving.** MSPDI stores
`<Stop>` and `<Resume>`; the importer read `Stop` and discarded `Resume`. The two EVM goldens are the
whole proof, and they are exactly the two cases an unconditional floor cannot separate:

| | EVM2 UID 20 | EVM1 UID 18 |
|---|---|---|
| percent complete | 80 % | 25 % |
| remaining | 480 min | 1080 min |
| `Stop` | 2012-08-29 17:00 | 2012-08-17 15:00 |
| `Resume` | **2012-09-13 08:00** | **2012-08-17 15:00** (== Stop) |
| MSP stored finish | 2012-09-13 17:00 | 2012-08-21 17:00 |
| tool before | 2012-08-30 (**−14 d**) | 2012-08-21 (exact) |
| tool after | **2012-09-13 (exact)** | 2012-08-21 (unchanged) |

`Resume + 480 remaining working minutes = 2012-09-13 17:00` — the stored finish, exactly. EVM1
UID 18 has `Resume == Stop`, so it must not move; **an unconditional floor moves it, and that is the
regression that killed both prior attempts.**

Blast radius, measured across every committed fixture before writing the change:

```
EVM1 4 tasks with Stop+Resume, 0 with Resume!=Stop      Project2  28 /  3
EVM2 6 /  1                                             Project5  35 /  2
TP1-TP4, commercial_construction: 0 / 0
SRA Large Test File2: 1099 / 113  — and 92 of 92 in-progress tasks have Resume != Stop
```

All 92 in-progress activities on the reference file record a reschedule — precisely the 92 that made
the all-ML basis 370 working days short.

---

## 4. The fix, and one defect found in it by measurement

ADR-0309: `Task.resume`, the MSPDI read, and `cpm._resume_bounds` — an early-**finish** floor at
`offset(resume) + remaining` when `resume > stop`, the deliberate sibling of the existing
`_stored_date_bounds` (ADR-0034) which already honours stored dates on *unstarted* tasks. When
`resume == stop` nothing is floored, so a file recording no reschedule is byte-identical to before.

**A first implementation was wrong and measurement caught it.** Using the *stored* remaining in the
floor pins an in-progress task's finish regardless of the sampled duration, which destroyed the
Monte-Carlo's upside variance: `det_pctile = 100.00 %`, σ 20.3, `max` = exactly the deterministic
date — no iteration could finish late. The floor must follow `duration_overrides`, because every
override producer builds an incomplete task's override from its remaining duration
(`_ml_minutes`, `_three_point`, or 0 for a zeroed margin task). Corrected, σ landed at 65.5.

Recording this because the wrong version *looked* like an improvement on three of the six headline
metrics.

---

## 5. Results

**Distribution** — see §0. Duration-only σ is now **33.3** cal d against the **≈33** derived as MS
Project's implied figure in the prior evidence file: a prediction made before the fix and met after.

**The equivalence is now true rather than retracted.** All four duration bases converge at
**1,447,808** working minutes. Ordinary `compute_cpm` places UID 152 at **2029-04-19 10:08** against
a stored finish of 2029-04-19 10:07:36 — **agreement to the minute, computed rather than imposed.**
The 1,388-day correction is no longer load-bearing, so external finding H1 / the repo's FINDING 3
("the agreement is an identity forced by the realignment") no longer applies.

**ADR-0108 partly closed, honestly re-scoped.** EVM2 finish 2012-10-01 → **2012-10-02** (Acumen
2012-10-04); Net Finish Impact −19 → **−20** (Acumen −22). **1 of 3 working days.** The remaining 2
are a *different* defect — the unstarted successor chain, UIDs 23/25/26/28/29/30 each starting 1–5
days before their stored dates — and are recorded as such rather than folded into the ADR's claim.

**Nothing regressed.** EVM1 unchanged. `pytest -m parity` green (44 passed before the new test, 49
with it), including Project2/Project5 which carry 3 and 2 rescheduled tasks — insulated because the
SSI driving-slack parity path already reads stored progress-aware dates
(`driving_slack.py:120-129`). That was measured before the change was written, not assumed after.

---

## 6. Still open

* **The other 2 working days of ADR-0108's EVM2 residual** — the unstarted successor chain. A
  separate, now-isolated defect.
* **The legacy `/sra` path's cross-basis defect.** `_build_result` sets
  `deterministic = cpm.project_finish` (full duration) while `_three_point` samples remaining, with
  no realignment — driving `deterministic_percentile → 1.0` on progressed files. It reaches
  `/api/sra`, the SRA Word/Excel report, `sra_conclusions`, and `scorecards.reserve_recommendation`,
  which converts offsets with no `stored_finish_correction` — so reserve dates and
  `/api/margin/risk` dates for the same file sit on two different date axes. No external audit
  covers this path. Carried.
* **A committed SSI export contradicts ADR-0307's Best-Case rule.** Verified independently here: on
  `SRA Large Test File2.mpp`, BC/ML by stored factor is 0.5001 / 0.4000 / 0.2999 / 0.2001 / 0.1002
  (n = 154/184/191/202/188) — ADR-0307's corrected rule, exactly. But
  `00_REFERENCE_INTAKE/SRA Sensitivity Analysis.xlsx` (Project5, focus 145) gives BC/ML of
  0.9 / 0.6 / 0.5 at WC/ML 1.5 / 1.2 / 1.1 — the *pre*-0307 rule, with the same Worst-Case column.
  Two SSI artifacts disagree under any single fixed table. **ADR-0307 stands for the artifact we
  match**, and the robust posture is the existing precedence (stored Best/Worst wins; the table+rule
  is the fallback for operator-entered factors only). Recorded rather than left unmentioned. Also
  corrects the prior file's claim that ADR-0123's validation was self-referential and that "every
  POLARIS match is factor 1" — ADR-0123 cites UID 107/39 at factor 5 and UID 35 at factor 2 from
  that export.
* **`resume` is read from MSPDI only.** The XER importer has no equivalent read; P6 stores
  suspend/resume differently. Unmeasured.
