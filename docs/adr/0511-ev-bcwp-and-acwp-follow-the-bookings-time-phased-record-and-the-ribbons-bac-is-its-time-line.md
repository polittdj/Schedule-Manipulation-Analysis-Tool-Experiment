# ADR-0511 — EV (BCWP) and AC (ACWP) follow the booking's TIME-PHASED record, not the task's scalars: a booking earns its baseline cost in the share of its booked work the record says was performed, and its spend is that record priced at the rate in force at the status date; the ribbon's BAC is the workbook's time line, not a definition (R-45 CLOSED)

- **Status:** Accepted — 2026-09-18 (the plan-forward's R-45, the report's §3 row after R-67 / ADR-0510; the second unit written under QC-3, ADR-0509).
- **Version:** **1.0.276** (`src/` changed: `model/assignment.py` + `model/resource.py` + `SCHEMA_VERSION` 2.17.0; `importers/mspdi.py` + `importers/json_schedule.py` + `importers/_common.py`; `engine/metrics/evm.py`; `web/evm.py`; `web/help.py` + `docs/METRIC-DICTIONARY.md`).
- **Extends:** **ADR-0473** (R-01 / the Hard_File EVM oracle; its "no per-task cost oracle in the export" is refuted here), **ADR-0492** (BCWS from the booking's time-phased baseline cost — the same record class, read for the ACTUAL side now), **ADR-0506** (rates resolved at the status date — the overtime rate joins the standard rate), **ADR-0508** (sum a record at the file's resolution, round once).
- **Shipped:** the four booking fields and the resource's overtime rate; `_earned_value` / `_actual_cost_of_work_performed` in `evm.py`; the progress-disagreement disclosure on SPI and the EVM page's note; the parity pins (`tests/parity/test_fuse_metric_history_oracle.py`), the synthetic pins (`tests/engine/metrics/test_evm.py`, `tests/importers/test_mspdi.py`, `tests/importers/test_json_schedule.py`), the schema freeze re-pinned.

## Context — what the row said, and what the export actually carries

R-45 read: *Hard_File_updated3's BAC / BCWP read 133,400 / 59,340 where Fuse's ribbon reads
121,800 / 53,715, and Fuse's ACWP is to-time-now (64,105 vs the file's 63,763 on updated2) — no
per-task cost oracle in the export.* Its first step: read the Detailed Metric Report's per-activity
cost columns, else ask the operator for a per-task export.

Every workbook under `00_REFERENCE_INTAKE/` was opened, every sheet (91 `.xlsx`, the Hard_File
family sheet by sheet with the parity test's own std-lib reader). The Detailed Metric Report carries
X-marks, no cost columns. But two artefacts the row never named ARE oracles:

* **`Hard_File_updated3 vs Hard_File_updated4 24 hour calendar Field Map.fieldmap.xml`** — Fuse's
  MS Project field map: `BCWP → BCWP (EV)`, `BCWS → BCWS (PV)`, `ACWP → ACWP (AC)`, `Baseline Cost →
  Baseline Cost` AND `Baseline Cost → Budget Cost`. Fuse's EV / PV / AC are MS Project's own
  earned-value fields; its BAC is `sum(BaselineCost)` over the same population as everything else
  (the Bible's remarks on BAC / EV / AC each read *"Includes normal activities, milestones and LOEs
  that are planned, in-progress, or complete"*).
* **`Hard_File_updated2 vs update3 Forensic Analysis Report.xlsx`** — Fuse's per-activity diff of
  the two snapshots: `Projects` (whole-file Budget / Actual / Remaining / Total Cost per snapshot),
  `Actual-Cost` (7 activities, both values), `Remaining-Cost` (11), `Total-Cost` (6), `Baseline-Cost`
  (**0 changes**), `Percent-Complete`, `Activity-Status`, `Baseline-Finish` (290 and 291 moved).

### BAC 121,800 — the Ribbon View's time line, not a definitional BAC

Fuse's `Projects` sheet gives updated3's **whole-file Budget Cost 133,400** (marked `=`, unchanged
from updated2), Actual 67,703, Remaining 124,304, Total 192,007 — the committed golden's sums to the
unit (67,703.08 / 124,304.34 / 192,007.42). So Fuse scored the same save, and its whole-file BAC IS
the engine's. The Ribbon View's `Time Line` header is five monthly ribbons, serials 46204 … 46327
(2026-07-01 … 2026-11-01): the workbook was built around updated2, which finishes 2026-11-06;
updated3 finishes 2026-12-12. The **15 activities of updated3 that START on or after 2026-12-01**
(UIDs 7, 9, 13, 14, 36, 141, 144, 145, 146, 409 and the milestones 407, 410, 156, 411, 155) carry
Baseline Cost **11,600**, Baseline Work **160 h**, Cost 11,600, Work 160 h and no actuals — exactly
every ribbon delta at once: Budget / Total / Remaining Cost −11,600, Baseline / Total Work −160 h,
Actual Cost and Actual Work unchanged. The "finishes in December" variant reads 16,400 / 184 h (it
adds UID 389, which starts 11-30) and is refuted. Fuse's own per-activity Detailed View of updated3
(`Analysis Report`, sheet `Hard_File_updated32`) lists none of the 15; its view of updated2 lists
every one. **The engine's BAC is correct; the ribbon's 121,800 is the BAC of the activities inside
the workbook's time line.** No engine change; the reconciliation is pinned.

### EV 53,715 — the booking's time-phased record

updated and updated2 are EXACT under `BAC × % complete` (16,800 / 49,700), so the 5,625 lives in what
updated3 changed. UID 290 ("Review expertise of potential vendors", 100 % complete, EV method
% complete, physical % 0): its one booking is written `Work 40 h` (25 regular + 15 overtime),
`ActualWork 31 h` (`PercentWorkComplete 78`), but its time-phased record holds **16 h regular
(Type 2) + 6 h overtime (Type 3) = 22 h**. `22 / 40 × 12,500 = 6,875`, and `59,340 − 12,500 + 6,875 =
53,715` — exact. The rule — a booking earns its baseline cost in the share of its BOOKED work that
its RECORD says was performed (overtime counted in both), the budget no booking carries earning at
the task's percent — reproduces **16,800 / 49,700 / 53,715 on all three snapshots**. Every scalar
form was measured and refuted: the booking's `PercentWorkComplete` (56,590), actual work over
baseline work (51,885; 47,700 on updated2 where the oracle says 49,700), `BAC × % complete`
(59,340). MS Project's documented BCWP is *"the cumulative value of the task's timephased percent
complete multiplied by the task's timephased baseline cost, up to the status date"* (Microsoft Learn,
the MSPDI `BCWP` element), and its assignment BCWP *"the percentage of work complete multiplied by
the baseline costs"* — the record, not the scalar. MPXJ 16.2.0 reads no task, assignment or
resource `BCWP` / `BCWS` / `ACWP` from a `.mpp` (a dumper over the three saves: 0 of 142 tasks), so
there is no stored per-task oracle; the rule reconstructs the reference's figure from the record
the file does carry.

### AC 66,245 / 64,105 — the same record, priced at the status date

The two deltas — **+341.92** on updated2 and **−1,458.08** on updated3 — sum to **1,800.00**, UID
290's actual overtime cost (6 h × 300). `16 h × 200 + 6 h × 300 = 5,000` is what the record says 290
spent; the scalar says 6,800. The +341.5 is the Logistics Apprentice (resource 7): cost-rate table A
reads 10 / 15 until 2026-08-31 and 30 / 45 from it; UID 210's 17.077 h were worked 08-20 / 08-24 and
its `ActualCost` scalar prices them at 10 (170.77); the reference prices them at **30** (512.31) —
the row in force at the STATUS DATE, the same row ADR-0506 already resolves `standard_rate` to
(*"the apprentice's rate 10 → 30"*). The rule — every WORK booking with a record spends its
performed regular minutes at the standard rate and its performed overtime at the overtime rate, both
the status-date rows; a MATERIAL / COST booking, or a booking without a record, spends its recorded
actual cost; a task's actual cost no booking carries is added — reads **20,800.00 / 64,104.61 /
66,244.61**, which the ribbon prints as **20,800 / 64,105 / 66,245** (the ribbon prints whole
units). Pricing each block at the rate in force on its own date reads 63,763.07 / 65,903.07 and is
refuted. The row's "ACWP to-time-now" is refuted by sign: neither file has an actual past its status
date, and updated2's ACWP exceeds its actual cost.

## The plan, and what was attacked before the first edit (QC-3)

| assumption | check | verdict |
| --- | --- | --- |
| the row's four figures | re-read off the ribbon sheets and off the goldens' XML | held (121,800 / 53,715 / 133,400 / 59,340; ACWP 64,105 / 66,245 vs 63,763.08 / 67,703.08) |
| "no per-task oracle in the export" | every sheet of every Hard_File workbook opened | **fell** — the Forensic report's per-activity change sheets and the field map |
| Fuse scored the committed save | the Forensic `Projects` totals vs the golden's sums | held to the unit |
| BAC's population is a Fuse definition | the Bible's remarks; the ribbon's other deltas; the 15 December starters | **fell** — the time line |
| "finish in the window" vs "start in the window" | both measured on the file | start (11,600 / 160 h); finish refuted (16,400 / 184 h) |
| EV is `BAC × % complete` | three snapshots | **fell** on updated3 alone; the record rule exact on 3 / 3 |
| the booking's `PercentWorkComplete` is the share | measured | refuted (56,590) |
| ACWP is "to time now" | the sign of the deltas; actuals past the status date (none) | **fell** |
| rates price at the work's date | measured | refuted (63,763.07 / 65,903.07); the status-date row exact |
| integer-minute storage keeps the unit match | per-block minutes vs seconds on the three oracles, then the shipped form | **fell** — per-block rounding read 64,105.33 (the right side by luck); the shipped per-booking rounding-once read **64,104.17**, which prints 64,104 against the ribbon's 64,105; the record is stored in SECONDS (64,104.61 / 66,244.61 print as 64,105 / 66,245) |
| the cap `min(1, performed / booked)` is needed | 44-file census | inert but for one 0.048 h speck (Large Test Files, UID 5259, no baseline cost); kept as MS Project's ≤ 100 %, pinned synthetically |
| the rule moves more than 290 | 44-file census, 1,079 budgeted tasks | EV: 290 (in every copy of updated3 and the 24-hour snapshots) plus four in-progress tasks on the 24-hour snapshots (267 / 302 / 385 at 99 % with fully performed bookings → their whole baseline cost; 389 at 67 % → 3,200 of 4,800) — **no Fuse oracle for that snapshot: UNVERIFIED**; AC: 290 and 210 only; EVM1 / EVM2 carry no record and are byte-identical (the fallback path, 5 started budgeted bookings) |
| a booking's Σ baseline cost never exceeds its task's | census | 0 of 1,079 |

## Decisions

1. **The model carries the booking's record**: `Assignment.performed_work_seconds` (Type 2) and
   `performed_overtime_seconds` (Type 3), each the block sum at the file's own SECONDS resolution
   (the one seconds-valued field in the model: a recorded quantity, not an axis duration), `None`
   when the booking carries no time-phased work at all;
   `Assignment.baseline_cost` and `actual_cost` (the booking's own scalars, currency units);
   `Resource.overtime_rate`, table A's row in force at the status date like `standard_rate`.
   `SCHEMA_VERSION` 2.17.0; the Save `.json` round-trips every field; a Save written before this
   version reads `None` and takes the fallback.
2. **EV (BCWP)** = Σ over bookings with a baseline cost of `min(1, (performed + overtime) / booked
   work) × baseline cost` where the record exists, else `baseline cost × task %`; plus `(task
   baseline cost − Σ booking baseline costs, floored at 0) × task %`. A task with no record anywhere
   reads exactly as before.
3. **AC (ACWP)** = Σ over the task's bookings when every one records an actual cost: a WORK booking
   with a record spends `performed / 60 × standard_rate + overtime / 60 × overtime_rate` (an
   unrecorded overtime rate prices overtime at the standard rate); every other booking its recorded
   actual cost; plus the task's actual cost no booking carries. A task whose bookings do not all
   record an actual cost reads its own actual cost (the Bible's blank-as-0), exactly as before —
   the census instrument `evm_acwp_or_zero_sites` stays at 1.
4. **The disagreement is disclosed, not hidden**: the started, budgeted activities whose EV under the
   record differs from `BAC × % complete` ride SPI as count / population / offender UIDs (the
   ADR-0473 shape), and the EVM page prints them — on updated3, UID 290: a task reported 100 %
   complete whose booking performed 22 of 40 hours. That gap is the forensic signal this tool exists
   for.
5. **BAC is unchanged**; the ribbon's 121,800 is pinned as the engine's BAC over the activities that
   start before the workbook's last ribbon ends (read from the ribbon header), and the engine's
   133,400 as Fuse's own whole-file Budget Cost (read from the Forensic `Projects` sheet).

## Verification (QC-1)

- **Red first on the pristine package** (a worktree at `60d75e93`, the `-p mutcheck` plugin asserting
  the package under test): the two parity pins red by name (updated3's EV 59,340 and updated2's
  ACWP 63,763.08 against the ribbon; the window pin); the importer's two pins; the Save round-trip
  pin; the schema freeze's three; the engine module's two synthetic pins by name once its fixtures
  were built per call (a module-level fixture on the new fields had errored at collection instead).
- **Mutation battery 13 / 13 red by name** on fresh shadow copies of the FINAL `src/` (control green,
  the package asserted on every row): M01 EV ignores the record · M02 the cap · M03 overtime dropped
  from the share · M04 overtime priced at the standard rate · M05 AC ignores the record · M06 the
  remainder · M07 a non-work booking's actual · M08 the disclosure · M10 an absent booking actual left
  unknown · M11 the overtime series · M12 the fixed remainder · M13 the overtime rate from the scalar ·
  M14 the record rounded per booking to minutes (the ribbon pin: 64,104 for 64,105).
- **Measured, pristine → this tree** (44 files, 1,079 budgeted tasks): EV moves on 290 alone in the
  Hard_File_updated3 family and on 267 / 302 / 385 / 389 of the 24-hour snapshots (UNVERIFIED — no
  ribbon for that save); AC moves on 290 and 210; every other file byte-identical, EVM1 / EVM2
  (no record; 5 started budgeted bookings on the fallback) among them. Σ booking baseline cost
  never exceeds its task's (0 of 1,079); the cap fires on one 0.048 h speck (Large Test Files,
  UID 5259, no baseline cost).
- **The three ribbons:** EV 16,800 / 49,700 / 53,715 exact; AC 20,800.00 / 64,104.61 / 66,244.61
  → 20,800 / 64,105 / 66,245; CPI 0.81 / 0.78 / 0.81 exact; SPI 1.05 / 0.77 / 0.49 exact; TCPI
  1.04 / 1.21 exact (updated3's ribbon TCPI 1.23 recomputes only on the time line's 121,800; the
  engine's 1.19 stands on the whole file's BAC, and the pin says so).
- Statics green on both ruff binaries, `ruff format`, `mypy --strict` (165 files), `bandit` (exit 0);
  the wheel built after the last `src/` edit; the nine installers rebuilt; lockstep 68 passed. The
  full suite and `-m parity` run in a separate worktree at the code commit; their figures follow in
  the docs-only follow-up commit.

## Deliberately NOT done

The 24-hour snapshots' four in-progress movers (no oracle — a Fuse ribbon of `Hard_File_updated4
24 hour calendar` would settle them) · MS Project's per-task `BCWP` / `ACWP` themselves (MPXJ 16.2.0
does not read them; the operator's own export would be the direct oracle) · a per-booking rate
table (B to E) · a BCWS read from the record (ADR-0492's series already is) · the ribbon's
time-line population as a tool feature (a Fuse workbook artefact, not a schedule fact).
