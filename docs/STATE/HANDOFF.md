# Handoff — 2026-09-17 (d) (R-63 **CLOSED** (ADR-0506) — a resource's capacity is the file's OWN availability table, resolved at the status date; the converter's `MaxUnits` was the JVM's clock, and the same save converted a month apart carried two loading figures; **R-68 registered** (a day outside every row) — **v1.0.272**, schema **2.16.0**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`778da99c`** (#695, R-64 / ADR-0505, **MERGED** 21:03Z; the squash is **TREE-IDENTICAL** to the reviewed PR head `0ac20dbe`, tree `e8c5760f…`, compared with `git rev-parse <sha>^{tree}`, and to this session's starting checkout). **`main`'s OWN runs for `778da99c` — read this session, not inherited: installer-smoke 755 (`35274461873`) SUCCESS 21:07:52Z (it EXISTS, correctly — #695 rebuilt the installers); CI 1917 (`35274461874`): `cui-guard` 21:03:37Z · `browser` 21:20:57Z · `floor` 21:26:19Z · `test (3.13)` 21:39:35Z · `test (3.11)` 21:51:47Z · `check` 21:51:52Z.** This unit ships on branch `claude/loving-heisenberg-u4kgzs` (the designated branch, restarted on the squash with `--prune` + `remote set-head` + `checkout -B`) as **draft PR (opened after this push; its number is recorded in the follow-up docs-only commit)** (the operator merges; never marked ready here; EIGHT checks — `installer/**` changed). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0506**. Version **1.0.272**. Schema **2.16.0** (`Resource.availability` + `AvailabilityPeriod`). QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-63 read: the converter's output depends on the CONVERSION date; first step "write the availability
and cost-rate tables themselves".** The mechanism was CONFIRMED at the bytecode (MPXJ 16.2.0's
`Resource.getMaxUnits` → `getCurrentAvailabilityTableEntry` → `LocalDateTime.now()`; the rates via
`getCurrentCostRateTableEntry(0)`; `AvailableFrom` / `AvailableTo` / `OverAllocated` / `CurrentDate` the
same clock — MS Project's own "current row of the Resource Availability grid" semantics, mirrored), and
**its first step was already the case**: `MSPDIWriter` already writes `AvailabilityPeriods` and `Rates`.
Measured executably with `faketime` (`tools/conversion_clock_probe.py`, committed): the updated3
golden's own git blob under a faked 07-09 clock reproduces the committed golden **to the second**; 09-14
and 11-01 change **9 and 13 element pairs** (ADR-0491's "32 lines" was `diff`'s normal-format count of
the same 9 pairs) — `CurrentDate`, `MaxUnits`, `OverAllocated`, `AvailableFrom` / `AvailableTo`,
`StandardRate`, `OvertimeRate` on UIDs 1 / 3 / 7 then 1 / 2 / 3 / 6 / 7 — while `<Tasks>`,
`<Assignments>`, `<Calendars>` and every table are byte-identical. **The tables are the save's; the
scalars are the clock's.** A `.mpp` even stores MS Project's own current-row `MaxUnits` at save time
(`getCachedValue`: 100 / 100 / 50 / 25 on updated3's four tabled resources — the 07-09 rows); MPXJ's
getter ignores it. Censused at two clocks over the 29 intake `.mpp` files: 6 carry a table (updated2 /
updated3 / updated4-24h with VARYING rows, 2 / 4 / 4 resources + one rate table each; the three tampered
`Project5_FX0x` saves with 32 single bounded rows of constant units — MPXJ returns null outside a
resource's only row and prints the default 1); every `<Tasks>` identical between the clocks.

**Shipped.** `AvailabilityPeriod` + `Resource.availability` (schema 2.16.0, the Save round trip); the
MSPDI importer resolves `max_units` from the table and `standard_rate` from cost-rate table A at the
schedule's own "now" — the status date, else the project start — reading the scalar `<MaxUnits>` /
`<StandardRate>` only for a resource with no table; **one resolution rule** (`value_in_effect`: the
latest row begun by the instant, else the earliest — the containing-row check ahead of it was a second
path that could not change an outcome, its mutant SURVIVED, deleted; `available_to` stays as the file's
statement); the loading engine earns each working day's capacity from the row in force that day (a crew
that doubles on 08-02: one unit in July's bucket, two in September's); the roster's Max units is the
status-date row and the footnote says so.

| figure (pristine → this tree, 15 goldens + the 29 `.mpp` files at two clocks = 73 entries, 2,601 resource rows, 7,966 month buckets) | |
| --- | --- |
| resources carrying a table | 230 |
| roster max units moved · bucket capacities moved · rates moved | **28** · **78** · 8 |
| over-allocation flags moved | **17, every one CLEARED** (months the 07-09 scalar's one unit called over-booked that the stated two units cover) |
| booked load moved | **0** (asserted per bucket) |
| the two clocks' conversions of one file importing to DIFFERENT loadings | **3 of 29 → 0 of 29** — the row's oracle |
| updated2 / updated3 / the 24-hour snapshots | Customer Service Team **1 → 2**, Customer Service Lead 1 → 2, Technology Lead 0.5 → 1, Logistics **0.25 → 0.5** (a three-row table), the apprentice's rate 10 → 30 |
| Hard_File, updated, Project2 / 5, the Large Test Files, EVM | no table — nothing moved |

**Rendered, not inspected — the real app, four goldens × seventeen routes:** 56 of 68 renders
byte-identical (the launch token aside); only the twelve `/resources` renders differ — text on every
golden, figures on updated2 / updated3 (the day takeaway *"5 of them are over-allocated"* → 4, the week
4 → 3, the KPI strip, the picker's ⚠ markers, the payload, the roster).

## How it was verified

* **Red first, on the pristine package (a separate worktree at `778da99c`, the `-p mutcheck` plugin
  asserting it):** four modules cannot import; **20 pins red by name** (`1.0 == 2.0`, `0.5 == 1.0`,
  `0.25 == 0.5`, the rate 10, one unit-day in September, the 09-14 replay importing a different table,
  the two rendered pins, the two Save pins); one control named as such.
* **Mutation battery 16 / 16 red by name** on a shadow copy (control green, every cut checksum-verified):
  M01 18 · M02 18 · M03 (`datetime.now()`) 6 · M04 6 · M05 3 · M06 9 · M07 25 · M08 1 · M09 5 · M10 2 ·
  M11 1 · M12 1 · M13 1 · M15 8 · M16 1 · M19 21. **The first run was not this battery:** M05 SURVIVED
  (an equivalent mutant — the dead containing-row check, deleted) and M08 was a malformed cut (an
  `IndentationError`, no verdict), rebuilt; the second run began after the code and every test were final.
* Statics green on **both** ruff binaries, `ruff format`, `mypy --strict` (165 files + the tool),
  `bandit` (exit 0), `node --check` per file; the wheel built AFTER the last format (lockstep pin green,
  68 passed).

**Gate on the code commit `ce94c253` — MEASURED in a separate worktree (never in the tree the docs were written in; `PYTHONPATH` on the worktree's `src/`, the `-p mutcheck` plugin asserting it):** the full suite and `-m parity` were STILL RUNNING at this push (5,616 collected = the previous 5,579 + 37: the three new modules' 27, the engine's 4, the model's 4, the freeze test's 2; `-m parity` collects 187 = 171 + the new oracle's 16, by `--collect-only`); 3,362 verdicts in with 5 failures, every one attributable — the four installer lockstep pins (red by construction in a worktree that carries `main`'s old installers beside the new `src/`; 68 / 68 green on the final tree after the rebuild) and the handoff version-pin guard (the docs commit carries the pin; the module is green on the final tree). **The final figures are recorded in the follow-up docs-only commit, with the PR number.**

## Deliberately NOT done

**A zero-availability reading of a day outside every row (R-68, ASK)** — the three tampered
`Project5_FX0x` saves book crews on **113 / 179 / 113** loaded day-buckets past their single bounded rows
(HVAC Contractor 10 / 20 / 10); the engine holds the latest row begun in force there (the converter's
own figure — nothing moved), MPXJ's reading is a null printed as the default 1, and whether MS Project
counts such a day as ZERO availability is UNVERIFIED (no MS Project verdict in the corpus; a
conversion's `OverAllocated` is MPXJ's clock-dependent computation) — the operator's Resource Graph on
`Project5_FX04` decides it, question (f) in the report's §5 · **the XER `RSRCRATE` rows onto the model**
(the XER scalar is already resolved at the data date; no P6 witness) · **rate tables B–E, `OvertimeRate`,
`CostPerUse`, the rate formats** (not modelled) · **`OverAllocated` / `AvailableFrom` / `AvailableTo` /
`CurrentDate`** (the clock's — never read) · **regenerating the goldens' resource sections** (the splice
keeps the 07-09 scalars; the tables beside them are what the importer reads, and the scalar is the
premise each parity pin asserts) · **a Java-gated CI test on the golden's blob** (CI's checkout is
shallow; a skip measures nothing — the probe tool and the replayed diff carry the measurement) · a
"varies" marker on the roster (not asked).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-62** (every absent
slack the writer dropped is a zero, completed tasks included) · **R-65** (the 1–28-minute gap
granularity) · **R-67** (the backward mirror of ADR-0505's carried instant — the natural next engine
unit) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; **R-68** waits on
the operator's reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
