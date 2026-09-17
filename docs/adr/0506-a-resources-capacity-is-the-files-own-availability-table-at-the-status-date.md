# ADR-0506 — A resource's capacity is the file's own availability table, resolved at the schedule's status date: the converter's `MaxUnits` was the JVM's clock, and the same save converted a month apart carried two different loading figures (R-63 CLOSED; R-68 registered)

- **Status:** Accepted — 2026-09-17 (the plan-forward's R-63, the report's §3 row after R-64 / ADR-0505).
- **Version:** **1.0.272** (`src/` changed: `model/resource.py` (`AvailabilityPeriod`, `Resource.availability`, `value_in_effect` / `units_in_effect`, `Resource.units_at`), `model/__init__.py` (SCHEMA_VERSION **2.16.0**), `importers/mspdi.py` (`_availability_periods`, `_standard_rate_in_effect`, `_parse_resources(root, as_of)`), `importers/json_schedule.py` (the Save round trip), `engine/resources.py` (capacity per working day from the table), `web/resources.py` (the explainer and the roster footnote name the basis). Wheel and the nine installers rebuilt in lockstep. No converter change: the tables were already written.)
- **Extends:** **ADR-0491** (which registered R-63 from the golden regeneration's measurement and kept the goldens' 07-09 resource sections by splice — the sections this ADR now reads correctly), ADR-0125 (the loading engine and its capacity formula), ADR-0474 (the resource calendar in the base pass — the other half of "the resource's own statement"), the operator's 2026-08-20 XER max-units rule (the data-date resolution this ADR generalises).
- **Shipped:** the model, importer, engine and page changes above; `tests/importers/test_mspdi_resource_availability.py` (9 pins), `tests/engine/test_resources.py` (+4), `tests/model/test_resource.py` (+4), `tests/model/test_schema_freeze.py` and `tests/importers/test_json_schedule.py` (the 2.16.0 freeze and the maximal round trip), `tests/parity/test_r63_availability_table_oracle.py` (16 parity pins on the four tabled goldens, the 09-14 conversion replayed verbatim), `tests/web/test_resources_availability_table.py` (2, rendered through the real app); `tools/conversion_clock_probe.py` (the clock measurement, reproducible with `faketime` + a JRE); the report's R-63 row closed and **R-68** registered; the state docs.

## Context — what the row said, and what the file says

R-63 read: *the vendored converter's output depends on the CONVERSION date, not only the save:
`CurrentDate`, and a resource's `MaxUnits` / `OverAllocated` / `AvailableFrom` / `AvailableTo` /
`StandardRate` / `OvertimeRate` resolve at "now" from the availability and cost-rate tables (measured
2026-09-14: the same Hard_File_updated3 save converted 07-09 and 09-14 differs on exactly those 32
lines; `MaxUnits` feeds the resource-loading view's capacity) — two operators converting one file a
month apart get different loading figures* — first step *write the availability and cost-rate tables
themselves (MSPDI `AvailabilityPeriods` / `Rates`) and have the importer resolve capacity at the
STATUS date*. The kickoff added: the claim that the tables can simply be written is testimony.

**The mechanism was confirmed at the bytecode, and its first step was already the case.** MPXJ
16.2.0's `Resource.getMaxUnits()` is `getCurrentAvailabilityTableEntry().getUnits()`, and that entry
is `AvailabilityTable.getEntryByDate(LocalDateTime.now())`; `calculateAvailableFrom` /
`calculateAvailableTo` call `now()` themselves; `calculateOverallocated` is `peakUnits > getMaxUnits()`;
`calculateStandardRate` / `calculateOvertimeRate` read `getCurrentCostRateTableEntry(0)`, table A at
`now()`; `ProjectProperties.CurrentDate` defaults to `now()`. And `MSPDIWriter.writeResource` already
calls `writeAvailability` (every row of a table whose range is not the default) and
`writeCostRateTables` (every populated table). This is MS Project's own semantics, mirrored: Microsoft's
field reference defines `MaxUnits` as *"the maximum amount that a resource is available … during the
current time period"* and the VBA `Resource.MaxUnits` as *"the current row of the Resource Availability
grid — the row where the date range … includes the current date"*; `AvailableFrom` / `AvailableTo` are
that row's bounds, and *"if the availability period for the current date is not defined"* they are the
day after the previous row's end. A `.mpp` even stores that current-row `MaxUnits` at save time
(`Resource.getCachedValue(MAX_UNITS)` reads 100 / 100 / 50 / 25 for updated3's four tabled resources —
the 07-09 rows, the day the file was saved); MPXJ's getter ignores the stored value and recomputes it
at the reader's clock. For an interactive tool that is right; for a forensic snapshot it means the
converted file carries the converter's clock, not the save's.

**Measured executably, not inherited — `tools/conversion_clock_probe.py`, one save under frozen
clocks.** The updated3 golden's own git blob (`1908d073`, Revision 2, saved 07-09 10:12; ADR-0491's
provenance) converted under `faketime`:

| clocks | changed lines | elements | resources touched | `<Tasks>` / `<Assignments>` / `<Calendars>` | `AvailabilityPeriods` / `Rates` tables |
| --- | --- | --- | --- | --- | --- |
| the committed golden vs 2026-07-09 14:56:59 | **2** (`CurrentDate`'s seconds) | — | — | byte-identical | byte-identical |
| 07-09 vs 07-09 again (determinism) | 2 (`CurrentDate`'s seconds) | — | — | byte-identical | byte-identical |
| 07-09 vs 2026-09-14 | **18** (9 pairs) | `CurrentDate`, `MaxUnits` ×2, `OverAllocated` ×2, `AvailableTo`→`AvailableFrom` ×2, `StandardRate`, `OvertimeRate` | UIDs 1, 3, 7 | byte-identical | byte-identical |
| 07-09 vs 2026-11-01 | **26** (13 pairs) | the same kinds | UIDs 1, 2, 3, 6, 7 | byte-identical | byte-identical |

ADR-0491's "32 lines" was the same 9 pairs counted in `diff`'s normal format (seven hunks of 4 or 6
lines); the golden IS the 07-09 output to the second. The tables are the save's; the scalars are the
clock's — and each is exactly the row the clock sits in: UID 1 "Customer Service Team" is 1 unit
through 2026-08-01 and 2 from 08-02 (`MaxUnits` 1 on 07-09, 2 on 09-14), UID 3 "Technology Lead"
0.5 → 1 on 08-11, UID 2 "Customer Service Lead" 1 → 2 on 09-29, UID 6 "Logistics" 0.25 → 1 → 0.5
across 10-08 / 10-10, UID 7 "Logistics Apprentice" rate 10 → 30 at 2026-08-31 08:00.

**The corpus, censused at two clocks (the 29 intake `.mpp` files converted at 07-09 and 12-31):**
every `<Tasks>` section identical between the clocks; **6 of 29** files carry a table — the three
Hard_File_updated2 / updated3 / updated4 saves (2 / 4 / 4 resources with rows whose units VARY,
one rate table each; `MaxUnits` moved on 2 / 4 / 4 resources) and the three tampered
`Project5_FX04 / FX05 / FX06` saves (32 resources each with ONE bounded row of constant units;
only `AvailableFrom` / `AvailableTo` moved — for a clock outside a resource's only row the getter
returns null and the writer prints `MaxUnits` 1, the default, which is also that row's units); 23
carry none and differ between the clocks on `CurrentDate` alone. Among the 15 goldens, five entries
carry tables (updated2, updated3 twice, the two 24-hour snapshots) — 18 tabled resources.

**What consumed the scalar:** `engine/resources.py`'s per-bucket capacity (`max_units × working
minutes/day × working days in the bucket`), the `/resources` roster's Max units column, its JSON
payload and the Excel export; `standard_rate` has no consumer beyond the Save round trip;
`OverAllocated`, `AvailableFrom`, `AvailableTo` and `CurrentDate` are read by nothing.

## Decision

**The model carries the table.** `AvailabilityPeriod(available_from, available_to, units)` — one row of
MS Project's Resource Availability grid as the file records it (the 1984-01-01 "NA" start reads as
`None` through the importers' shared pre-1985 sentinel; the 2049-12-31 23:59 "NA" end is kept as
written) — and `Resource.availability: tuple[AvailabilityPeriod, ...]`, in time order, `()` for a
resource the file writes no table for. `SCHEMA_VERSION` 2.15.0 → **2.16.0**; the Save `.json` writes
and reads it; the freeze test and the maximal round trip pin it.

**The importer resolves at the schedule's own "now", never the converter's.** `_parse_resources(root,
as_of)` with `as_of` = the status date, else the project start (the XER rule of 2026-08-20):
`max_units` is the table's units in force at `as_of` and `standard_rate` is cost-rate table A's
(`RateTable` 0) rate in force at `as_of`; the scalar `<MaxUnits>` / `<StandardRate>` are read ONLY for a
resource with no table (every golden but four). Tables B–E, `OvertimeRate`, `CostPerUse` and the rate
formats are not read (the model carries one rate; no consumer reads a per-booking table). A row
without `AvailableUnits` states nothing and is dropped, never read as zero capacity.

**One resolution rule — `value_in_effect`: the latest row that has begun by the instant, else the
earliest.** A row is a statement in force until the next row begins; a `None` start has always begun;
before every row's start the earliest row governs (a table whose every row starts in the future states
its first row rather than nothing). **A row's stated end is deliberately not consulted.** The first cut
carried a "row containing the instant" check ahead of that rule; on every table the corpus carries the
rows are contiguous, so the two paths always agreed, and the start-bound mutant of the containing
check **SURVIVED** the first battery — a second code path that could not change an outcome, deleted
(the ADR-0502 / ADR-0505 lesson, paid a third time). `available_to` stays on the model as the file's
own statement, for the reading R-68 may need.

**The engine earns each working day's capacity from the row in force that day.** `_period_working_days`
now returns the days per bucket; for a tabled resource `cap = wmpd × Σ units_at(day)` over the bucket's
working days (the day probed at 00:00 — MS Project's rows begin at 00:00 and end at 23:59, so a day
never straddles two rows); for every other resource the formula is unchanged. So a crew that doubles
on 08-02 has one unit of capacity in July's bucket and two in September's, at every granularity. The
roster's Max units and the payload's `max_units` are the status-date row (the importer's scalar); the
explainer and the roster footnote say so.

**Refused, and named:** a zero-availability reading of a day outside every row (R-68 — below); the
XER `RSRCRATE` rows onto the model (the XER scalar is already resolved at the data date, so that path
already meets the row's oracle, and the corpus carries no P6 witness); regenerating the goldens'
resource sections (the splice keeps the 07-09 scalars, and the tables beside them are what the
importer now reads); a "varies" marker on the roster (not asked; the footnote names the basis).

## What it measured

**The corpus, pristine tree → this tree, one instrument** (`compute_resource_loading` on every golden
and on both clocks' conversions of the 29 intake files — 73 file entries, 2,601 resource rows, 7,966
month buckets):

| figure | pristine → this tree |
| --- | --- |
| resources carrying a table | 230 (18 on the goldens, 106 per conversion clock — 10 varying, 96 single-row FX) |
| roster max units moved | **28** (the five tabled goldens' 18; the 07-09 conversions' 10; the 12-31 conversions' 0 — a 12-31 clock sits in every table's last row, which is the status-date row on all three saves) |
| bucket capacities moved | **78** of 7,966 |
| over-allocation flags moved | **17, every one CLEARED** — months the 07-09 scalar's one unit called over-booked that the crew's stated two units cover |
| standard rates moved | 8 (the apprentice, 10 → 30 on every tabled entry) |
| booked load moved | **0** (asserted per bucket — the load is the file's, untouched) |
| the two clocks' conversions of one file importing to DIFFERENT loadings | **3 of 29 → 0 of 29** — the row's oracle |
| loaded day-buckets outside every row of a tabled resource | 810 — the three FX saves' 113 / 179 / 113 at either clock (R-68) |

Per golden (the roster figure, the bucket capacities moved of the resource's buckets, the flags):
updated2 — UID 1 **1 → 2** (3 of 4, one flag cleared), UID 3 **0.5 → 1** (1 of 1), UID 7's rate 10 → 30;
updated3 (both copies) — UID 1 1 → 2 (4 of 5, two flags), UID 2 **1 → 2** (4 of 5), UID 3 0.5 → 1, UID 6
**0.25 → 0.5** (2 of 2; the three-row table's last row), UID 7's rate; updated3_24hr / updated4_24h —
the same five resources (UID 1 3 of 4 with two flags, UID 2 3 of 4 with one). Hard_File, updated,
Project2 / Project5, the Large Test Files and EVM: no table, nothing moved.

**Rendered, not inspected — the real app, four goldens × seventeen routes, pristine → this tree:**
**56 of 68 renders byte-identical** once the per-process launch token is set aside; the twelve that
differ are the `/resources` family (month / day / week) and nothing else — on Project5 and
Large_Test_File the explainer and the footnote only (9 lines); on updated2 and updated3 also the
payload, the roster, the KPI strip, the picker's ⚠ markers and the takeaways: on the day bucket *"5 of
them are over-allocated in at least one day"* → **4**, on the week bucket 4 → **3**. `/analysis`,
`/api/analysis`, `/api/driving`, `/driving-path`, `/margin`, `/curves`, `/dashboard`, `/integrity`,
`/path`, `/ribbon`, `/wbs`, `/scorecards`, the CSV export and the home page: byte-identical on all four.

## How it was verified

* **Red first, on the pristine package (a separate worktree at `origin/main` `778da99c`, the package
  asserted by the `-p mutcheck` plugin):** four modules cannot import (`AvailabilityPeriod` does not
  exist); **20 pins red by name** on the modules that collect — the ten golden cases read the 07-09
  row (`1.0 == 2.0`, `0.5 == 1.0`, `0.25 == 0.5`), the three rate cases read 10, the two daily-capacity
  pins read one unit in September, the 09-14 replay imports a different resource table, the two
  rendered pins show 1 and one unit-day, the two Save pins fail the writer's field census and the
  round trip. One control is named as such (`test_a_resource_without_a_table_keeps_the_files_scalar_
  max_units`, green on both trees by construction).
* **Mutation battery, 16 cuts on a shadow copy of `src/`, the control green, every cut
  checksum-verified — 16 / 16 red by name** on the final code: M01 the scalar read despite a table →
  18 · M02 the project start governs, never the status date → 18 · M03 the table resolved at
  `datetime.now()` → 6 · M04 the engine ignores the table → 6 · M05 a row begins the minute after its
  start → 3 · M06 the last row always governs → 9 · M07 the earliest begun row governs → 25 · M08 every
  rate table's rows feed the rate → 1 · M09 the scalar rate read despite table A → 5 · M10 / M11 the
  Save writer / reader drops the table → 2 / 1 · M12 no time sort → 1 · M13 a row without units read as
  zero → 1 · M15 `units_at` answers `None` for everyone → 8 · M16 the schema version not bumped → 1 ·
  M19 the table never carried → 21. **The first run was not this battery:** its M05 (the containing
  check's start bound) SURVIVED — an equivalent mutant that exposed dead code, deleted before the
  second run — and its M08 was a malformed cut (an `IndentationError`, `rc 4`, no verdict), rebuilt;
  the second run began only after the code and every test were final.
* **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files, and the tool), `bandit` (exit 0), `node --check` per file.
* **The full gate**, measured in a separate worktree at this unit's code commit `ce94c253`: @@GATE@@

## Consequences

- **R-63 is CLOSED-0506.** The row's oracle — the loading view's capacity independent of the conversion
  date — is measured on the corpus (0 of 29 two-clock pairs differ) and pinned on the real file (the
  09-14 conversion's nine changed pairs replayed verbatim on the updated3 golden import to the same
  resources and the same loading).
- **R-68 is registered (ASK):** a day outside every row of a resource's table. The three tampered
  Project5_FX saves book crews on 113 / 179 / 113 loaded days past their single bounded rows (HVAC
  Contractor 10 / 20 / 10 of them). The engine holds the latest row begun in force there — the figure the
  converter's scalar gave, so nothing moved — and MPXJ's own reading is a null (printed as the default
  1); whether MS Project counts such a day as ZERO availability, every one of them over-allocated, is
  UNVERIFIED: no MS Project verdict is in the corpus (`OverAllocated` in a conversion is MPXJ's
  clock-dependent computation, never MS Project's stored flag). The end bound the reading would need is
  already on the model.
- **`Resource.max_units` now means "the table at the status date" on a tabled resource** — the
  docstring says so, the roster footnote says so, and a Save `.json` written by this version reopens
  with the table. A Save written before this version carries only its scalar, which this version reads
  as before.
- The goldens are NOT regenerated: their 07-09 resource sections were kept by ADR-0491's splice on
  purpose, and the tables beside those scalars are what the importer reads now — the 07-09 scalar is
  the premise each parity pin asserts before the claim.
- Version **1.0.272**; SCHEMA_VERSION **2.16.0**; the wheel and the nine installers rebuilt after the
  last `ruff format` (the lockstep pin green, 68 passed).

## Deliberately NOT done — registered, or named

* **A zero-availability reading outside every row** — R-68, the operator's reading of MS Project's
  Resource Graph on `Project5_FX04`'s HVAC Contractor decides it; a red-first pin on that file follows
  the answer.
* **The XER path's `RSRCRATE` rows onto the model.** The XER importer already resolves the scalar at the
  data date (2026-08-20), so a P6 file already meets the row's oracle; carrying its rows would
  time-phase P6 capacity with no P6 witness in the corpus. The model field is source-agnostic when one
  arrives.
* **Rate tables B–E, `OvertimeRate`, `CostPerUse`, the rate formats, `OverAllocated`, `AvailableFrom` /
  `AvailableTo`, `CurrentDate`** — none is read; the last four are the clock's and must never be read as
  a file's statement (the fixture headers keep their 07-09 values, harmlessly).
* **A Java-gated CI test that converts the golden's blob fresh** — CI's checkout is shallow (no blob), and
  a test that skips without the blob measures nothing; the clock measurement lives in the committed
  probe tool and in this record, and the CI-safe form of it is the replayed diff.
* **A "varies over time" marker on the roster** and the Excel export's Max units column beyond the
  status-date row — not asked; the footnote and the explainer name the basis.
