# Handoff — 2026-09-20 (f) (R-76 **CLOSED** (ADR-0518) — Acumen Fuse's duration FIELDS divide by the ACTIVITY's own CALENDAR day (Original / Baseline ignoring the elapsed flag, Remaining taking 1440 for it); the DCMA-14 parity population and the "8. High Duration" tile read the Baseline Duration FIELD, so a whole-day field of 0 leaves every population; Float Ratio™'s whole-day formula registered as R-78, the DCMA-09 tile's denominator as R-79 — **v1.0.282**)

STATUS (current) — `main` @ **`601be5d3`** (#706, R-73 / ADR-0517, **MERGED** 2026-09-20 17:44:09Z by the operator; the squash TREE-IDENTICAL to PR #706's FINAL head `62c65a4a`, tree `e409412d…` — re-verified this session with `git rev-parse <sha>^{tree}`, this clone's `HEAD^{tree}` == `origin/main^{tree}`). **PR #706's FINAL head, EIGHT checks read to conclusion:** CI `35518839525` — `cui-guard` 15:12:53Z · `browser` 15:28:41Z · `floor` 15:43:45Z · `test (3.13)` 16:02:26Z · `test (3.11)` 16:07:34Z · `check` 16:07:41Z; installer-smoke `35518839551` — `linux` 15:13:00Z · `windows` 15:18:05Z — **eight of eight green**. **`main`'s OWN runs for `601be5d3`, by their JOBS:** CI 1962 (`35526809555`) `cui-guard` 17:44:27Z · `browser` 18:00:26Z · `floor` 18:15:01Z · `test (3.13)` 18:32:48Z · `test (3.11)` 18:32:00Z · `check` 18:32:55Z — six of six; installer-smoke 796 (`35526809525`) `linux` 17:44:51Z · `windows` 17:49:40Z. Nothing about `601be5d3` is outstanding. This unit ships on the designated branch **`claude/blissful-cori-2nukng`** (branched from the squash; its never-pushed remote-tracking ref pruned) as a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0518**. Version **1.0.282**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-76's population rule was decided FIRST, on the reference's own ribbon, and it reached further
than the row.** The row asked which duration DCMA-08 reads and how Fuse divides its duration fields.
The `.aft`'s DCMA metric filters `Baseline Duration > 44` over `Baseline Duration > 0`, and the Large
Test File pair's ribbon reads 87 / 86 — the Metric History's "High **Baseline** Duration (44d)", not
"High Planned" (124 / 120) — over **927 / 904** (0.09 / 0.10; the engine's every-incomplete 1,024 / 998
would print 0.08 / 0.09). On the 24-hour Hard_File the filter "Baseline Duration > 0" reads the FIELD
on the activity's own day: UIDs 302 / 385 (a 480-minute baseline on a 1,440-minute calendar → 0) leave
every parity population — "7. Negative Float" **0.92 = 11 / 12** (the engine's 14 printed 0.79),
"9. Invalid Forecast Dates" **0.08 = 1 / 12**, and the tile's own detail grid lists UID 267 alone where
the unfiltered Quick-Add grid lists 267 / 302 / 385 (the engine's parity DCMA-09 read 3; now 1).

* **Shipped:** `_common.activity_calendar_day_minutes` (the task's own calendar's day, else the
  project's — NO elapsed axis) and `acumen_duration_field` (whole days, half-even, a call to
  `acumen_whole_day_float` — no new `round()`); dcma14's parity `_baselined` reads the Baseline field
  (> 0) on that day; DCMA-08 under parity is the field > 44 over the baselined-incomplete population;
  the pure-logic mode byte-identical (raw minutes against 44 project-days, 44 × 1440 for an elapsed
  baseline, every incomplete activity). `activity_day_minutes` (R-75) delegates to the new selector
  after its elapsed branch.
* **Measured — the fields, every duration cell the operator's workbooks display over the committed
  saves (the four Hard_File analysis workbooks 771 / 771 / 297, the AlltheProjects report 9,935 / 9,935 /
  1,085 — 10,706 floats reproduce 100 % first, the save check):** *Original* and *Baseline* are the
  minutes over the task's own CALENDAR day, half-even, the elapsed flag IGNORED (146's 2,880 elapsed
  minutes display **6**; Jacked Up Schedule 1's elapsed UID 20: 46,080 → **96**) — 0 Baseline misses, 1
  Original (Large Test File2's 5267 stores `PT107H59M36S`, 13.4992 → 13, where the model's minute grid
  holds 6,480 → 14; R-65's class); *Remaining* takes 1440 for an elapsed activity (146 → **2**, UID 20 →
  **32**) — the same 5267 and the two 99 % SUMMARIES 315 / 129 on the 24-hour snapshot whose
  RemainingDuration MPXJ dropped as a zero (Fuse 0; the percent fallback 247 / 242 → 1). Refuted by
  name: the project day (14 / 302 / 385 / 389 / Jacked Up 1's 19), 1440 for an elapsed Original (146, UID
  20), the floor (1,409 rows), half away from zero (the 240-minute baselines 99 / 642 display **0** — the
  tie is half-even at the field, and the population's reading follows it: 927, not 928). With the
  intake-only saves the same rules read 15,314 / 15,314 / 2,180 cells with the same residuals.
* **Measured — the corpus (44 files, 13,461 incomplete):** the population moves only on the three
  24-hour Hard_File copies (302 / 385); DCMA-08 membership moves only on `24Hour Calendar.mpp` UID 17
  (28,800-minute baseline: 60 project-days, 20 own-days; no Fuse oracle). Large Test File 87 / 86,
  Project2 1, Project5 0, every Hard_File snapshot 0 — unchanged and UID-exact against the Detailed
  Metric Reports' X-marks.
* **Pinned:** `tests/parity/test_fuse_duration_fields_oracle.py` (the 12,088 committed cells under the
  shipped helpers with exactly the three named residuals and the alternatives refuted by name; the
  minute-grid `Duration` read back from the MSPDI; the 24-hour ribbon's 0.92 = 11 / 12 and 0.08 = 1 / 12
  with the tile's grid (267) against the unfiltered one; the tile 87 / 927 → 0.09, 86 / 904 → 0.10,
  Project2 1 / 106, the Hard_File snapshots 0, the pristine denominators' 0.08 / 0.09; the R-78 and R-79
  registrations); `test_dcma14.py`'s synthetic pins on both modes (34.5 own-days not high, an elapsed
  90 project-days high, the 44.4-day field 44, a 480-minute baseline on 1440 out of every population, the
  denominator 6 not 8). **Red first on the pristine package, by name** (the helpers absent; (11, 14) ≠
  (11, 12); (87, 1024) ≠ (87, 927)); **battery 8 / 8 red by name**, the control green — the raw-minutes
  tile mutant red only on the synthetic pin, which is exactly the UNVERIFIED claim (no oracle activity
  sits in 44 < d < 44.5).
* **Registered — R-78 (T1, S):** Fuse's Float Ratio™ averages its WHOLE-DAY fields and reads N/A
  whenever a Remaining Duration field is 0 — recomputed from Fuse's own displayed fields it reproduces
  every numeric tile of the AlltheProjects ribbon to 4 dp (−10.9446 → −10.94, 14.0076, 0.7678, 0.2667,
  0.3427) and every N/A (9 / 9 ⇔ a zero field); the engine averages minutes and skips a zero remaining
  (−11.85 for −10.94 on the rev-5 updated3; 119.61 / 3.98 / 3.21 where Fuse reads N/A). **R-79 (T1, S):**
  the DCMA-09 tile's denominator is the baselined INCOMPLETE population (File2 322 / 904 → 0.36; the
  engine's 1,568 → 0.21) and it counts fields where the engine counts activities (322 vs 173).
  `duration_days_axis` is HELD with R-78 (its only consumer).

## How it was verified

Eleven QC-3 assumptions in ADR-0518: ten held, one fell (`duration_days_axis` as a divisor question —
the whole Float Ratio™ formula differs; registered). The plan and every instrument are in the session
record. Statics green on ruff 0.15.8 and `uvx ruff@0.16.8` (`check .` + `format --check .`, whole tree),
`mypy --strict` 165 files, bandit exit 0, `node --check` per file. The DCMA and parity consumers **197
passed**; `tests/engine` + `tests/test_projects` **1,353 passed**; `tests/installer` 68 (lockstep after the
rebuild); the report guard 8. `-m parity` and the full suite: **218 passed / 0 failed** in 7:05 (`PYTEST_EXIT=0`); **5,714 passed / 7 skipped / 0 failed** in 38:11 (`PYTEST_EXIT=0`, the three doc guards deferred to after the last doc edit) —
read within the session; the doc guards re-run after the last handoff edit.

## Deliberately NOT done

Float Ratio™'s formula, its N/A and `duration_days_axis` (R-78) · DCMA-09's parity denominator and
its field-vs-activity count (R-79) · reading an absent remaining as zero for the Remaining Duration
field (the two summaries are disclosed by name; ADR-0517's class keeps the CPM's reading) · the minute
grid (R-65) · the "≥ 1 own day" alternative for the population (no witness in the (0.5, 1) own-day band;
the exact tie is witnessed at the field, UID 642) · the pure-logic thresholds and the five project-day
display sites (ADR-0516 decision 3) · the AlltheProjects labels whose saves the repo does not hold
(EVM2 8 / 11, Hard_File_updated2 42 / 110, the five TP4 versions 7–13 / 15) and the intake-only `.mpp`
labels — excluded from the committed oracle by name.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-78** (T1, S — Float
Ratio™ on the whole-day fields with N/A on a zero divisor; decide the tool's own reading of the N/A
first, then `_scored` on `acumen_total_float_field` / `acumen_duration_field`, red-first on the rev-5
updated3 (−11.85 → −10.94) and the Large Test File (119.61 → N/A); `duration_days_axis` retires) ·
**R-79** (T1, S — the DCMA-09 tile's denominator `ap_inc`, red-first on File2 1,568 → 904 and the
24-hour file 84 → 12; then the field-vs-activity count from the tile's detail grid) · R-09 · **R-74** ·
**R-77** (T2, M — the segment-aware pair; census the 212 / 25 / 4 and every rendered-time pin first) ·
R-69 · **R-71** · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question
(f)); the probe fixture's Fuse run is the operator's optional confirmation of ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
