# ADR-0495 — Fuse's SPI(t) population is every started activity with a non-zero actual span, baseline or not: an unbaselined member is the formula's blank-as-0 term, not an exclusion (R-47 CLOSED)

- **Status:** Accepted — 2026-09-15 (the plan-forward's R-47, the row the kickoff put first after OR-18).
- **Version:** 1.0.263
- **Extends:** ADR-0176 (the reverse-engineered per-activity SPI(t) and its three proven rules — this ADR adds the fourth and corrects the population), ADR-0473 (R-47's registration; the CPI blank-actuals disclosure this ADR mirrors).
- **Shipped:** `engine/metrics/evm.py` (`_spi_t_acumen` — the population no longer requires a baseline; an unbaselined member is a 0 term and rides `offender_uids`), `web/evm.py` (`_unbaselined_note`, re-exported from `web.app`), `web/help.py` + `docs/METRIC-DICTIONARY.md` (the definition states the rule), `tests/parity/test_fuse_metric_history_oracle.py` (the SPI(t) row of every Metric History sheet with a committed fixture — 18 oracles — and the Detailed Metric Report's Record Count as the population pin), `tests/engine/metrics/test_evm.py`, `tests/web/test_evm_view.py`.

## Context

R-47 (ADR-0473): `spi_t_acumen` read **8.24 / 8.17** on Large Test File / File2 where the Fuse
Metric History reads **8.22 / 8.14** — the only two of the corpus's SPI(t) oracles the engine did not
match. The register's first step was to "diff the per-activity ratios against the Detailed Metric
Report's SPI(t) column by UID; the candidates are zero-span completions and the in-progress
dilution". No test pinned 8.24 or 8.22: the figures were ADR-0473's testimony (QC-2), so the
session read them out of the workbook first — the 'SPI(t)' row (row 328) of
`Large Test File vs Large Test File2 - Acumen Fuse -Metric History Report.xlsx` carries **8.22 / 8.14**
(and the same pair sits on `AlltheProjects - Metric History Report.xlsx`'s `Large-Test-File` /
`Large-Test-File2` sheets, with 8.22 again on `Large-Test-File-Leveled` and `Large-Test-File-2`).

### What was measured first (QC-1 / QC-2)

**The register's step could not be taken as written.** Both Detailed Metric Reports for the pair
(`… - Acumen Fuse - Detailed Metric Report.xlsx`, created 7/15/2026, and `… - Detailed Metric
Report.xlsx`, created 7/21/2026 — 756 metric columns, 2,126 / 2,125 activity rows keyed by UID in
column D) carry the SPI(t) column (`NR`) **empty on every activity row**: the column holds only the
project total (row 12: 8.22 / 8.14) and a **Record Count** (row 14: **717 / 726**) — the number of
activities Fuse admitted to the average. That count, not a per-activity ratio, is the discriminating
number, and it was the one number in the workbook nothing had read.

The engine's own terms were then laid beside it:

| File (status) | Fuse SPI(t) | Fuse Record Count | Engine before (members → value) | Sum of the engine's ratios | Sum ÷ Fuse's count |
| --- | --- | --- | --- | --- | --- |
| Large Test File (2025-02-07 17:00) | **8.22** | **717** | 716 → 8.24 (609 completions + 107 in progress) | 5,896.9713 | 5,896.9713 / 717 = 8.2245 → **8.22** |
| Large Test File2 (2025-03-10 17:00) | **8.14** | **726** | 723 → 8.17 (632 completions + 91 in progress) | 5,908.2441 | 5,908.2441 / 726 = 8.1381 → **8.14** |

The whole residual is **one and three missing contributors whose terms are 0**: the engine's sum of
ratios divided by Fuse's count reproduces both figures exactly. The engine's population rule since
ADR-0176 required a baseline start AND finish (`baseline_start is None or baseline_finish is None
→ skip`), and the two files carry exactly these started activities with **no `<Baseline>` element at
all** (2 on File, 4 on File2 — no partial baselines anywhere among the started activities):

| UID | Name | File | State | Actual span | Under the baseline gate | Under Fuse's count |
| --- | --- | --- | --- | --- | --- | --- |
| 7260 | `DPsh83rHAyIaiD8XYnO0` | both | in progress (83 % / 8 %), started 2024-12-23 | open | skipped | a member, 0 term |
| 7262 | `dH18W6KApKWC8TAOWb50` | File2 | complete, 2025-02-12 08:00 → 2025-04-08 17:00 | 55 d | skipped | a member, 0 term |
| 7551 | `G4afE8kOleATkD8qyqeP` | File2 | complete, 2017-06-07 08:00 → 17:00 | 9 h | skipped | a member, 0 term |
| 7183 | `2TS72P2Q9EOAovcnBEYh` | both | completed milestone, 2025-01-30 08:00 → 08:00 | **zero** | skipped | **excluded** (zero span) |

"Started, non-zero actual span, baseline or not" counts **717 / 726** — Fuse's Record Count to the
activity; "started with a baseline OR in progress without one" counts 717 / 724 (refuted by File2);
"zero-span completions as 0 terms" counts 807 / 816 (refuted by both). The workbook's own X-mark
columns corroborate the membership: `Completed (w/o Baseline Duration)` reads **0 on File and 2 on
File2** — UIDs 7262 and 7551, the two completed tasks the gate skipped (the milestone 7183 is not a
task and sits in neither count); `Start/ed` reads 807 / 816 = the engine's started population;
`Scheduled Activities` 1,723 / 1,722 = the engine's non-summary population.

**Why the term is 0.** The Bible formula is `(BaselineFinish - BaselineStart) / (ActualFinish -
ActualStart)` for a completion; with both baseline fields blank the numerator is (blank − blank),
and Acumen evaluates a blank as 0 — the same evaluation ADR-0176 proved on a blank `ActualFinish`
(the in-progress 0 term, `updated`'s 0.80 = 0.93 × 6 ÷ 7) and ADR-0473 proved on a blank actual cost
(CPI's `sum(ACWPAC)`). A blank numerator over a positive actual span is a 0 term; a blank
denominator (in progress) is the 0 term already reproduced. An activity Fuse *skipped* would not be
in its Record Count; these are.

**Corpus census before the rule changed** (every MSPDI fixture, 27 files; the simulated rule beside
the shipped one, then re-run through the real engine after the change — identical): **5 moved, all
in the started-unbaselined class, none away from an oracle.** Large Test File → 717 / 8.22 (UID
7260), File2 → 726 / 8.14 (7262, 7260, 7551), the two older Large Test File saves (`ssi_uid152`,
`ssi_uid152_leveled`) → 717 / 8.22 (7260; consistent with `AlltheProjects`' `Large-Test-File-Leveled`
8.22 but NOT pinned as oracles — they are different saves, ADR-0473), and the synthetic
`TP3_Outage_DCMA_Seeded` 11 / 0.53 → 12 / 0.48 (UID 34 'Craft onboarding & badging', complete, never
baselined — no Fuse figure exists for TP3 and no test pinned 0.53). Every other fixture with a Fuse
SPI(t) oracle was exact before and stays exact: EVM1 0 · EVM2 0.56 · TP4 v1–v5 0.5 / 0.5 / 0.67 /
0.7 / 0.63 · Project2 0.83 · Project5 0.91 · Hard_File N/A · updated 0.80 · updated2 1.14 · updated3
1.25 · updated4-24h 1.31 · Jacked-Up 1 / 2 N/A. No oracle-bearing fixture carries a started
activity without a baseline except the Large Test File pair — which is why ADR-0176's three rules
were exact on the Hard_File series and the fourth went unseen.

## Decision

**The population of `spi_t_acumen` is every STARTED activity (an actual start) whose completed
actual span is non-zero, baselined or not.** A completed member with a baseline contributes
(BF − BS) / (AF − AS) as before; a completed member **without** a baseline contributes **0**; an
in-progress member contributes 0 whether or not it is baselined (unchanged for the baselined case);
a zero-span completion is excluded whether or not it is baselined (unchanged for the baselined
case); a never-started activity contributes nothing (unchanged). The members scored 0 for want of a
baseline ride the result as **`offender_uids`** — the same channel ADR-0473 gave CPI's blank
actuals — and the EVM page discloses them under the schedule-performance scorecard
(`_unbaselined_note`: *"N of P started activities carry no baseline — SPI(t) — Acumen scores each
as 0 …: UID …"*), so the reader sees what pulls the figure toward 0 instead of an average silently
carrying members the file never planned. `help.py` (and the generated dictionary) state the rule and
the new oracle pair.

Nothing else moves: the count-based Earned-Schedule SPI(t), SVt, the per-group field forecast (which
calls the same `compute_evm_indices`, so the WBS / resource breakdowns inherit the rule) and every
other metric are untouched.

## Verification (QC-1)

- **Red-first, by name, on the pristine tree:** `test_acumen_spi_t_engine_equals_fuse[LargeTestFile]`
  (8.24 ≠ 8.22) and `[LargeTestFile2]` (8.17 ≠ 8.14); `test_acumen_spi_t_population_equals_the_fuse_record_count`
  `[LargeTestFile]` (716 ≠ 717) and `[LargeTestFile2]` (723 ≠ 726);
  `test_spi_t_acumen_counts_started_work_without_a_baseline_as_a_zero_term` (0.75 ≠ 0.38, six
  synthetic activities covering each branch). The other 17 oracle parametrizations were green on
  the pristine tree (5 failed / 17 passed), which is the census's "nothing else moves" as a test.
  After the change: 22 passed. The pre-existing ADR-0176 unit test still passes.
- **The oracles are read from the vendor workbooks with the std-lib**, never transcribed: the
  'SPI(t)' row of three Metric History workbooks (the twelve-project `AlltheProjects`, the Large
  Test File pair, the Hard_File updated2/3 pair) and the 'Record Count' row of the Detailed Metric
  Report (streamed with `iterparse`, stopped at row 14 — the 9 MB of activity rows never
  materialised). A Fuse 'N/A' must be the engine's NOT_APPLICABLE (Hard_File, Jacked-Up 1 / 2).
- **Mutation battery on a shadowed copy of the package** (`PYTHONPATH` shadow, a `-p mutcheck`
  plugin asserting both `engine.metrics.evm` and `web.evm` are the copy; control 23 passed):
  **5 / 5 RED by name** — M1 the pre-ADR baseline gate restored (6 red: both values, both
  populations, the unit, the page note) · M2 a zero-span unbaselined completion scored as 0 (718 /
  727 → 5 red) · M3 a never-started unbaselined activity admitted (5 red — the Large Test File
  pair carries never-started unbaselined activities too) · M4 the disclosure dropped (the unit and
  the page note) · M5 in-progress unbaselined members excluded (716 / 725 → 5 red).
- **The page, measured in Chromium** (TP3 loaded, `/evm`, four themes × 1,440 / 900 px): the note
  is a laid-out box inside its panel in every theme's muted ink (11 px), and the document's scroll
  width with the note shown equals its width with the note hidden (1,440 / 900 — no sideways
  scroll added). The server test pins the words: TP3 shows `data-sf-unbaselined="1"` naming UID 34;
  Project5 (every started activity baselined) shows no note.
- Statics clean under both ruff binaries (0.16.7 / 0.15.8), `ruff format --check`, mypy strict,
  bandit, `node --check`. Targeted suites 214 passed (EVM engine + view, the dictionary sync, the
  parity-report sync, the monolith-split contract, the pass/fail battery, the field forecast, the
  `.aft` formula audit, the Hard_File parity, the Metric History oracle). Version 1.0.263, wheel +
  nine installers rebuilt, installer tests 68 passed; `tools/mpxj` unchanged (`163d1942`). The full
  suite and `-m parity` on the final tree: the SESSION-LOG entry.

## Consequences

- R-47 is **CLOSED**; the register row records the mechanism. ADR-0176's rule list gains a fourth
  proven rule; its "population = STARTED, baselined activities" wording is superseded here (the ADR
  itself is history and is not edited).
- The Acumen SPI(t) now carries a disclosure channel (`offender_uids`) like CPI / TCPI; readers of
  the result who treated `offender_uids` as "failing activities" should read it as "members whose
  term the file cannot know" for this metric, as for CPI.
- The two older Large Test File saves and TP3 read 8.22 / 0.48 from now on; nothing pinned their old
  values.

## Deliberately NOT done — measured, left alone, or beyond what the corpus can settle

- **The VALUE of a completed-unbaselined member's term is pinned as 0 by the formula's own
  evaluation, and the corpus cannot discriminate it from a substituted duration at 2 dp.** File2's
  total is the only oracle with such members (7262 / 7551), and with those two scored ≈1 instead of
  0 it would read 5,910.2 / 726 = 8.1408 → 8.14 — the same 2-dp figure. What the corpus DOES settle
  is the membership (Fuse's 726 to the activity) and, on Large Test File, the in-progress
  unbaselined term (7260 alone moves 8.24 → 8.22). A substituted duration is not in the formula and
  would need an oracle the corpus lacks: a Fuse run on a small file carrying a completed,
  never-baselined activity. Registered as an operator-owned item, not built on an assumption.
- The two `ssi_uid152*` Large Test File saves are NOT pinned as Fuse SPI(t) oracles (different
  saves, ADR-0473); their 8.22 is recorded as consistent, not proven.
- The Detailed Metric Report's per-activity SPI(t) column stays unread as a per-activity oracle —
  it is empty; the register's step was a hypothesis about the workbook.
- TP3's 0.53 → 0.48 is not pinned by an oracle (a synthetic file); the rule proven on the
  operator's file governs it.
