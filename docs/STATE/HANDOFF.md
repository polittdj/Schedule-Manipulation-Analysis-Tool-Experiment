# Handoff — 2026-09-16 (d) (R-57 **CLOSED** (ADR-0502) — a BOOKING's own leveling delay is honoured on that leg alone, on **ADR-0474 / ADR-0501's type axis**; the row's "delay that leg alone" was a REGRESSION for 18 of the 24 delayed bookings and the census caught it before it was believed — **v1.0.268**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`ed977f29`** (#689, R-61 / ADR-0501). **`main`'s own runs for `ed977f29` are SETTLED — read to conclusion this session, not inherited: CI 1902 (`35133877304`) `completed` / SUCCESS, all six jobs (`cui-guard` 18:21:36Z · `browser` 18:38:57Z with the R-52 interop gate run-and-NOT-skipped on `main` itself · `floor` 18:46:41Z · `test (3.11)` 18:56:21Z · `test (3.13)` 19:01:31Z · `check` 19:01:36Z). NO installer-smoke run exists for `ed977f29` and that ABSENCE IS CORRECT, not a missing check** — #689 was docs+tests only and `installer-smoke.yml` is path-filtered to `installer/**`; the pattern is visible in the run list (`0b010936`, `93593ef5` and `4b213dd8` each have one, the four docs-only heads have none). **#690 is still OPEN** (the docs-only merge record of #689) — the operator has not merged it; this unit branched from `ed977f29` and does not depend on it. Highest ADR **0502**. Version **1.0.268** — this unit changed `src/`, so the wheel and the nine installers were rebuilt in lockstep. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-57 asked for `Assignment/LevelingDelay` to be read and "that leg alone" delayed. The
mechanism is real, the row's oracle is reached — and two things in the row were wrong, both
found by measurement before any code changed.**

**The population is wider than the row.** The row names Hard_File UID 398's two bookings and
UID 188. **Six of the fifteen goldens carry the field — 24 delayed bookings on 17 tasks**,
every `Large_Test_File` snapshot included. This is ADR-0500's lesson applied *before* the fact
instead of after it.

**"Delay that leg alone" is right for 6 of the 24 and a REGRESSION for the other 18.**
Implemented exactly as written it cost `Large_Test_File` **93 of its 1,666**
finishes-within-a-day and took UIDs 5266 / 5267 / 5270 from EXACT to days late. The first cut
was measured against the whole golden census before it was believed, and the census refuted it.

**The delay rides ADR-0474 / ADR-0501's type axis — it does not cut across it:**

| the leg | its delay | count |
| --- | --- | --- |
| has its OWN span (`FIXED_UNITS`, ratio < 1) | **PUSHED** — starts late, still owes all its work | **6** (all Hard_File) |
| SPANS THE TASK (ratio 1.0) | **ABSORBED** — starts late, still ends with the task | **18** (all Large_Test_File) |

The absorb half is measured, not assumed: on **16 of those 18** the file's own
`Assignment/Finish` **IS** its `Task/Finish`; the two that are not are co-bookings finishing
earlier either way.

The delay runs in **working minutes of the leg's own calendar**, is read to the **NEAREST**
minute (17 / 24 against MS Project's own `Assignment/Start`; truncation 14, and rounding is
never worse on any single booking — all 7 misses are sub-minute, 12–78 s, R-65's class), joins
the leg's **dedup identity** (or a leveled crew collapses onto its unleveled twin and vanishes),
is **never read on a MATERIAL / COST booking** (ADR-0487: its leg IS its window), and does
**not move the task's start** (`Task.Start == min(Assignment.Start)` on 17 / 17).

**Measured across every golden.** `Large_Test_File`, `Large_Test_File2`,
`Large_Test_File_Leveled`, `Project2`, `Project5`, `Hard_File_updated3` and the SSI golden are
**BYTE-IDENTICAL** on every column. Only `Hard_File_updated` moves: **exact finishes 58 → 61,
exact stored slack 93 → 99**. UID 398 lands on MS Project's own **2026-08-27 11:59**; UID 188
goes from **15 h 45 m early to 66 seconds**.

**The row's oracle is reached on `Hard_File_updated`, NOT on the base `Hard_File` — and the
blocker there is not leveling.** UID **381** finishes a full working day early on that snapshot
(08-20 11:59 vs the stored 08-21 11:59), 396 inherits it, and 398 then lands early by **exactly
the 240 working minutes 396 is** (computed in the pin, not copied). ADR-0474's task-delay
arithmetic is EXACT on **both** snapshots when fed the stored predecessor finish. Registered as
**R-66** rather than hidden inside R-57.

**Shipped:** `Assignment.leveling_delay_minutes` (schema **2.15.0**), the MSPDI reader and the
Save-`.json` reader/writer, `_Leg.delay` / `_LegShape.delay` through the plan builder and
**both** passes, `CPMResult.assignment_leveling_driven`,
`tests/engine/test_assignment_leveling_delay.py` (10 pins),
`tests/parity/test_r57_assignment_leveling_delay_oracle.py` (8 pins), **ADR-0502**, the closed
R-57 row, the new R-66 row, the `round_calls_outside_engine_metrics` census 328 → 329, and the
**v1.0.268** wheel + nine installers.

## How it was verified

* **Red before green.** Both modules fail on the pristine tree: `Assignment` refuses
  `leveling_delay_minutes`, `CPMResult` carries no `assignment_leveling_driven`.
* **The pristine baseline was taken in a SEPARATE WORKTREE at `origin/main`**, never by mutating
  the tree under measurement.
* **Mutation battery: 9 cuts, 9 red BY NAME, control green before AND after**, each cut
  checksum-verified to have changed the file and the file checksum-verified restored.
* **M6 SURVIVED the first pass** — dropping the delay from the **BACKWARD** pass left every
  other check green. It is not cosmetic: it is worth **three exact stored slacks** on
  `Hard_File_updated` (99 → 96) on UIDs **321 / 381 / 396**, the very chain that feeds 398.
  Killed by a pin naming those three.
* **A line that could not fire was DELETED rather than shipped.** The first `_leg_finish`
  re-snapped after the delay. Swept over **31,479** delay / span / gap combinations — 6 landing
  exactly on a segment end — it never moved a leg finish, because the work that follows is
  itself an `_advance_wall`, which counts a segment END and the next segment's start
  identically. The corpus agreed but only weakly (its one segment-end delay sits on an
  *absorbing* leg and never reaches `_leg_finish`), so the sweep is what settles it.
* **The disclosure's first cut over-claimed and was tightened.** Ranking legs by the
  project-start sort order falsely named `Hard_File_updated2` UID 398, whose delay is inert;
  it is now measured from the task's REAL early start.
* Statics green on **both** ruff binaries (0.15.8 **and** 0.16.8), `ruff format`,
  `mypy --strict`, `bandit` (exit 0).

**Gate on the final tree: 5,508 passed / 0 failed / 7 skipped in 38:22**, and **`-m parity` 150 passed / 0 failed** in 5:54. Both deltas ATTRIBUTED, not assumed: the previous unit's 5,490 and 142, plus this unit's two modules — 10 engine pins and 8 parity pins, the parity module collecting **exactly 8** under `-m parity` (`--collect-only`). 5,490 + 10 + 8 = 5,508; 142 + 8 = 150. The 7 skips are the documented set (the urlparse pair, three INCIDENTAL_SVG axis cases, and the two `test_pptx_libreoffice_interop` skips that are correct in this container — CI installs the filter and treats a skip there as a FAILURE, ADR-0498). Run with `-v` and a stall monitor per the environment note a previous unit paid 2h16m for; load stayed 0.9–2.5 throughout, no stall.

**The FIRST full run failed by exactly one test and the failure was real:** `ruff format` touched `engine/cpm.py` AFTER the wheel was built, so `test_embedded_wheel_is_in_lockstep_with_the_source_tree` went red — the lockstep pin doing precisely its job. The wheel and the nine installers were rebuilt and **the whole suite re-run on the resulting tree** rather than inferring the one-test delta; the figures above are that second, clean run.

## Deliberately NOT done

**R-66** (UID 381's day on the base snapshot), the **task-level** reader's truncation
(ADR-0474 still does `// 10` where this one rounds — the inconsistency is named in ADR-0502,
**not measured**, and not changed here), and the **all-bookings-delayed** task start, which has
**no witness anywhere in the corpus** and is marked UNVERIFIED rather than claimed. No UI
change; `web/` untouched.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-58**
(a non-24-hour task calendar intersected with a crew calendar, Hard_File UID 14) · **R-59** ·
**R-64** · **R-63** · **R-62** · **R-65** · **R-66** (this unit's residual) · **R-45** · then
R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards.

**Review cover is still absent** — Codex quota EXHAUSTED; the mutation batteries and the full
gate are all this repo gets.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
