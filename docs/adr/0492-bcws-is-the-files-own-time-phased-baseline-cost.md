# ADR-0492 — BCWS is the file's own time-phased baseline cost: the importer reads a booking's baseline-cost series, the engine sums it through the status date and prorates a straddling block on the booking's calendar (R-46)

- **Status:** Accepted — 2026-09-15 (the plan-forward's R-46, the row the kickoff put first after R-60).
- **Version:** 1.0.260
- **Extends:** ADR-0473 (the linear time-phased BCWS this ADR keeps for the budget no series carries, and the registration of R-46), ADR-0491 (the converter's timephased data — the series this ADR reads was written by that unit and never read), ADR-0474 (the booking-calendar rule, now public), ADR-0487 (the "honour what the file records" line this ADR extends from spans and splits to planned value).
- **Shipped:** `model/assignment.py` (`CostPiece`, `Assignment.baseline_cost_pieces`), `model/__init__.py` (SCHEMA_VERSION 2.14.0), `importers/mspdi.py` (`_baseline_cost_pieces`, the Type-5 series gathered per booking), `importers/json_schedule.py` (round trip, strict), `engine/cpm.py` (`booking_calendar`, `working_minutes_between` — public names for the plan builder's own rule and ruler), `engine/metrics/evm.py` (`_planned_value` rewritten: the series where the file carries it, `_piece_planned`, `_linear_share` for the remainder), `web/help.py` + `docs/METRIC-DICTIONARY.md` (the SPI definition says the basis), `docs/PARITY-REPORT.md` (the BCWS and SPI rows), the audit report (R-46 CLOSED), `tests/parity/test_fuse_metric_history_oracle.py` (the `updated` tolerance 150 → 0; the updated2-vs-updated3 ribbon read for the first time), `tests/engine/metrics/test_evm.py`, `tests/engine/test_booking_calendar.py` (new), `tests/importers/test_mspdi.py`, `tests/importers/test_json_schedule.py`, `tests/model/test_schema_freeze.py`.

## Context

R-46 (ADR-0473): the cost-based SPI's planned value read 16,150 on Hard_File_updated where the Fuse
ribbon reads 16,000, attributed to "one activity straddling the status date on a 16-hour resource
calendar, prorated on the project calendar", and the register's first step was to prorate that
activity on its crew's calendar. The Bible's formula is `PV (BCWS) = sum(BCWSPV)` — Fuse sums each
activity's BCWS as MS Project stores it, and MS Project's BCWS is the activity's time-phased
baseline cost through the status date. Since ADR-0491 the vendored converter writes the timephased
data on every ingest and the regenerated goldens carry it — including the assignment baseline-cost
series (`TimephasedData` Type 5, 250 blocks on Hard_File_updated) that nothing in the tool read.

### What was measured first (QC-1 / QC-2)

The register's claim was re-measured before it was believed: a probe summed the Type-5 blocks of
each Hard_File golden by the same status-date rule the ribbon states, beside the engine's figure.

| Snapshot (status) | Fuse PV (BCWS) | Type-5 blocks finishing ≤ status | Straddling blocks | Engine before |
| --- | --- | --- | --- | --- |
| Hard_File_updated (2026-08-11 17:00) | **16,000** | **16,000.00** | 0 | 16,150 |
| Hard_File_updated2 (2026-09-10 17:00) | **64,240** | **64,240.00** | 0 | 64,240 |
| Hard_File_updated3 (2026-10-12 17:00) | **110,440** | 106,440.00 | 1 (UID 270, 4,800) | 110,440 |

The series IS the oracle. The 150 on `updated` is one task, UID 187 ("Determine required skill
sets for various support options", 120 h at 50 an hour, baseline 08-05 08:00 → 08-14 17:00): its
crew, "Customer Service Team", works 06:00–08:00 / 08:00–17:00 / 17:00–23:00, and MS Project
front-loads its 120 h on that calendar — 14 h on the first day, then 16 h a day — so 72 of 120 h
(3,600 of 6,000) are planned by the status date, where a proration over eight project days reads
five of eight (3,750). On `updated3` the two figures agree for two reasons the linear rule got
right by construction, not by rule: UID 270's three project days are ONE merged block (the writer
merges equal days; 10-09 08:00 → 10-13 17:00, 4,800) the status date falls inside — two of three
days, 3,200 — and UID 257's 800 of baseline cost has **no assignment series at all** in updated2 /
updated3 (its series was there in `updated`, where the Type-5 total equals the 133,400 BAC; in the
later saves the total is 132,600 — a booking baselined and since removed) and Fuse counts it whole
once its baseline finish has passed. 106,440 + 3,200 + 800 = 110,440.

Provenance of the oracle: 16,000 and 64,240 are the `Hard_File_update vs update2_Fuse - Excel`
ribbon (status 46245 / 46275) the oracle module already read; **110,440 was only ADR-0473's
testimony until this session** — it lives in `Hard_File_update2 vs update3_Fuse - Excel .xlsx`
(Ribbon View, status 46307), a workbook no test had opened, and is now pinned from it. The
register's own step (re-derive MS Project's distribution on the crew calendar) was not taken as
written: it reproduces UID 187 (72 of 120 crew-hours) and would miss every contour the file records
— a leveling delay inside the baseline, a split, a non-flat work contour, a merged block on a
calendar the rule approximates (R-58) — where reading the series matches by construction.

## Decision

**The importer reads a booking's baseline-cost series.** `_baseline_cost_pieces` takes the
assignment's Type-5 blocks: every block with a value becomes one `CostPiece` (start, finish, cost in
currency units — the file writes hundredths, like every MSPDI cost element), in time order whatever
the file order; a block with no `Value` or a zero one is nothing planned (a night, a weekend, a gap)
and carries no piece; a block with no dates, or an inverted one, is not a block; a pair recorded in
several rows gathers every row's pieces. The series is read as recorded — a merged block stays one
piece. A `Value` that is not a number fails the import loud, the module's contract for every
numeric field (`parse_float`), never a fabricated piece. `Assignment.baseline_cost_pieces` (`()` =
not recorded: an XER, an earlier Save, a conversion made before ADR-0491) rides the JSON Save both
ways, strictly (a piece missing its cost or a date is refused). `SCHEMA_VERSION` 2.13.0 → 2.14.0.

**The engine sums the series through the status date, and accrues what no series carries by the
linear rule.** `_planned_value` walks each cost-loaded task's bookings: a block finishing on or
before the status date counts whole, one starting at or after it counts nothing, and a block the
status date falls inside contributes the share of its working time that has elapsed — in working
minutes of the calendar the booking is scheduled on (`cpm.booking_calendar`, the plan builder's
own rule from ADR-0474 stated once and made public: the resource's calendar when the file carries
one whose pattern differs from the project's and the task does not ignore resource calendars; the
task's calendar when it has one that is neither the project pattern nor 24x7; else the project's),
measured by `cpm.working_minutes_between` (the recorded-span ruler of ADR-0487 / 0491, given a
public name). A block that calendar sees no working time in is measured by elapsed time, the only
ruler left. The task's baseline cost less its series' total — whole when the file records no
series — accrues by ADR-0473's rule: linear over the task's baseline span in working time of the
project calendar, whole once the baseline finish has passed, nothing before the baseline start. A
series exceeding the task's baseline cost stands as recorded; nothing is subtracted.

**The ribbon pins move from tolerance to exact.** The `updated` row's 150-unit tolerance is 0; the
updated2-vs-updated3 ribbon's PV (BCWS) is read and pinned (64,240 / 110,440), with the two
mechanisms named on the golden (UID 270's 3,200 inside its merged block, UID 257's 800 by the
linear rule, UID 187's 3,600 on `updated`). The SPI definition in `help.py` says the basis; the
dictionary is regenerated.

**Refused, and named:** re-deriving the distribution on the crew calendar instead of reading the
series (see Context); reading the baseline-WORK series (Type 4) or a task-level series (Type 10 —
none in the corpus) as cost; subtracting a series that exceeds the task's baseline cost.

## Verification

**Red first, on the pristine engine with the new tests in place:** 10 failed / 137 passed across
the four collectable modules and two modules that cannot import (`test_schema_freeze`,
`test_booking_calendar`: no `CostPiece`, no `booking_calendar`). The oracle's `updated` row is red
BY NAME — `('Hard_File_updated', 'BCWS')`, `150.0 <= 0.0`, `16150.0 - 16000.0` — and the updated3
row on the absent attribute; the three engine rules, the two importer tests and the JSON
round-trip, strictness and introspection guards red on the absent field.

**Green, then the corpus census, per task, pristine engine → this engine, every golden:** exactly
ONE task moved in the whole corpus — Hard_File_updated UID 187, 3,750 → 3,600, toward the ribbon;
BCWS 16,150 → **16,000**, SPI 1.04 → **1.05** (= the ribbon). Hard_File 0 → 0; updated2 64,240;
updated3 (both goldens) 110,440; updated3_24hr / updated4_24h 133,400 (every block before the
status date); the Large Test File family and Project2 / Project5 carry no cost; EVM1 / EVM2 /
Project2 / Project5 / TP4 carry no series and read exactly the old rule under the new code (EVM1
4,880 / EVM2 7,720, `new == old` executable). **Rendered, not read:** `/evm` on Hard_File_updated
shows SPI **1.05** in the takeaway header and the cost table on this tree and **1.04** on the
committed tree, the same page rendered from `git archive HEAD` under `PYTHONPATH`.

**Mutation battery on a shadowed copy of the package** (a `-p mutcheck` plugin asserts the copy is
what imports on every test; control 182 passed), each mutant run over the six touched modules
unfiltered: **18 mutants, 17 red by name on the first pass** — the series ignored (5: the three
rules and both ribbon rows), a straddling block counted whole / counted nothing / prorated by
elapsed time (2 each: the straddle rule and the updated3 ribbon), the project calendar prorating
every block (1: the straddle rule's round-the-clock case), the remainder never accrued (6), the
series not subtracted from the budget (5), baseline WORK read as cost (20 — the ISO durations fail
`parse_float` loud, the importer's contract), hundredths read as units (4), zero blocks kept (2),
both sorts dropped (1), the JSON writer / reader dropping the series (2 / 2), `booking_calendar`
answering the project always (5) / ignoring `ignore_resource_calendar` (1) / a 24x7 task calendar
no longer yielding to the crew (2), the schema version unbumped (1). **One survivor**, "a piece
without a cost reads as zero": the mutated line sits BELOW the guard that refuses a missing cost,
so it is unreachable — an equivalent mutant, not a test gap; re-cut with the guard removed it is
red by name on exactly the strictness test (18 / 18). Boundary mutants (`<=` at the status date)
are equivalent by arithmetic (a block finishing at the status date prorates to its whole) and were
not cut.

**The gate:** ruff 0.15.8 and 0.16.7 clean on the whole tree, `ruff format --check` clean, mypy
strict 165 files clean, bandit exit 0, the audit-report guard, the parity-report guard and the
state-doc guards green; the full suite and the parity gate on the final head are recorded in the
SESSION-LOG's close entry.

## Consequences

- BCWS and the cost SPI read what MS Project stores, on every file the converter has written
  since ADR-0491; a file without the series (an XER, a pre-0491 conversion, an earlier Save) reads
  exactly as before. The three Hard_File ribbons are exact; R-46 is CLOSED.
- The booking-calendar rule has one public home. R-58 (the intersection the rule approximates)
  now governs the planned-value proration too — closing it moves both consumers together.
- `SCHEMA_VERSION` 2.14.0: a Save written by this build carries `baseline_cost_pieces`; earlier
  Saves open unchanged (the field is optional and defaults to none).
- R-45 stays open: the updated3 ribbon's BAC / BCWP / ACWP (121,800 / 53,715 / 66,245) still
  disagree with the file's task-level cost fields; only its PV (BCWS) is pinned.

## Deliberately NOT done

- **A status date inside a block whose daily amounts are not equal.** The writer merges equal
  days only, and every status date in the corpus sits at a day's end, so the proration inside a
  merged block is exact on every golden; a mid-day status date inside a block on a calendar the
  rule approximates (R-58) has no oracle and is UNVERIFIED — the ruler is the booking calendar's
  working time, pinned by name.
- **A series that exceeds the task's baseline cost** — no file in the corpus does it; the pieces
  stand and nothing is subtracted, pinned as the decided behaviour, UNVERIFIED against a reference
  tool.
- **Type 4 (baseline work) and Type 10 (task baseline cost).** Not cost, and none in the corpus,
  respectively. The EVM goldens' source `.mpp` was never committed, so they cannot be regenerated
  with a series (PROVENANCE.json) and keep the linear rule.
- **Fuse's ACWP-to-time-now and updated3's BAC / BCWP** — R-45, its own row.
