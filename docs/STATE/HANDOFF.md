# Handoff — 2026-09-20 (d) (R-75 **CLOSED** (ADR-0516) — Acumen Fuse's Total Float field divides the stored slack by the ACTIVITY's own day — a task calendar's, raw elapsed days for an elapsed duration, else the project's — never the crew's calendar and never the engine's execution calendar; the three parity callers pass it; the DURATION fields' divisor registered as R-76 — **v1.0.280**)

STATUS (current) — `main` @ **`9d5541af`** (#704, R-04 / ADR-0515, **MERGED** 2026-09-20 08:24:02Z by the operator; the squash TREE-IDENTICAL to PR #704's FINAL head `bee00008`, tree `c6b4fbad…` — re-verified this session, this clone's `HEAD^{tree}` == `origin/main^{tree}`). **`main`'s OWN run for `9d5541af` — CI 1956 (`35499451753`, created 08:24:04Z; no installer-smoke, that diff touched no `installer/**`) — read by its JOBS this session:** `cui-guard` 08:24:19Z · `browser` 08:42:22Z · `floor` 08:53:47Z (tests 08:46:59Z, parity 08:53:45Z) · `test (3.13)` 09:11:46Z (tests + coverage 09:05:56Z, engine gate, parity 09:11:36Z, bandit, pip-audit) — **FOUR GREEN**; `test (3.11)` tests + coverage green 09:12:28Z, engine gate 09:12:29Z, parity step IN PROGRESS at the last read; `check` not yet listed — the session log's follow-up carries the last two, and the next session re-reads them by their jobs before trusting this line. This unit ships on the designated branch **`claude/dreamy-euler-vjd862`** (started on the squash) as a draft PR the OPERATOR merges (number in the session log's follow-up) — `src/` changed, the wheel and nine installers are rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0516**. Version **1.0.280**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-75's mechanism was decided on the corpus before the first edit, and the corpus decided it against
the obvious reading.** Every Hard_File workbook with detail grids prints a Total Float beside every
activity — **771** rows over five snapshots (45 / 61 / 61 / 102 / 110 / 110 / 141 / 141) once each
workbook is matched to the SAVE it was made from (the 7/15 analyst report `HA296F~1.XLS` is the rev-5
`updated3`, 141 / 141 against 129 / 141 on rev 2; the 7/9 Analysis Report is rev 2, 110 / 110). The
ACTIVITY's own day — 1440 for an elapsed duration, else the task's own calendar's working minutes per
day, else the project's — reproduces every one. The project day misses exactly ten (94 on `updated`;
14 / 146 on `updated2` and `updated3`; 14 / 146 / 302 / 385 / 389 on the 24-hour file). The CREW's
calendar is refuted by name: UID 14's 16-hour crew reads −4 for −3; a task with no calendar of its own
stays on the project day even when its crew works 24 hours (24-hour file UID 13: −10 shown, the crew's
1440 reads −3); UID 389's crew is on the project pattern while its task is on 24 Hours (−14, not −41).
The engine's EXECUTION calendar (ADR-0474 / ADR-0503) is refuted too: the task ∩ crew intersection's
870 minutes read 3 for UID 94's 2, the crew under a 24-hour task calendar reads −4 for UID 14's −3.
**The elapsed activity's field is RAW:** the 24-hour file displays UID 146 at −13.333333333333334 for a
stored −19,200 minutes where UID 14, on a 24 Hours task calendar with the SAME minutes, reads −13 — the
one non-integer cell in 771, and the first reader of the grids had filtered it to integers and read
"140 of 140" for the elapsed case. UID 302 sits on an own-day tie (34.5 → 34, half-even on the task's
axis too).

* **Shipped:** `_common.activity_day_minutes(schedule, task, by_uid)` and
  `acumen_total_float_field(task, minutes, day)`; dcma14's "6. High Float" / "7. Negative Float" parity
  sites and the ribbon's Negative Float read the field. No new `round()` (the ledger's 374 rows stand).
  The 24-hour Hard_File's DCMA-06 under parity reads **0** with Fuse (was 2: 302 / 385's 49,680 /
  44,796 minutes are 104 / 93 project-days and 34 / 31 days of their 24 Hours calendar).
* **Pinned:** `tests/parity/test_fuse_hardfile_float_divisor_oracle.py` — the 771 rows per workbook and
  save, the alternatives refuted by name, the raw cell, the 302 tie, the 7/15 ribbon's High Float 0 / 0
  and Negative Float 40 / 11 with the Negative Float grids UID-exact against
  `compute_dcma14(acumen_parity=True)`, the ribbon's own Negative Float unmoved at 49 / 15 (a wider
  population than the DCMA tile's — no baseline filter), and the R-76 evidence; synthetic pins on both
  parity paths and the ribbon site (`test_dcma14`, `test_schedule_quality`); the Forensic oracle
  (ADR-0515) re-pointed to the engine's rule and its READER corrected.
* **Measured, 44 files:** 1,578 activities carry an off-pattern task calendar or an elapsed duration;
  **34** change their whole-day float (the Hard_File family, `24Hour Calendar.mpp` 17: 148 → 49,
  `Jacked Up Schedule 1.mpp` 19 / 20); the Large Test File pair's 138 off-pattern task calendars are
  480-minute days (0 movers; 814 / 35, 660 / 112 unmoved); DCMA-06 membership moves only on the
  24-hour Hard_File, DCMA-07 nowhere, the ribbon's Negative Float on no file.
* **ADR-0515's Forensic reader was wrong and is fixed:** Fuse's xlsx writer omits the cell reference on
  consecutive cells and writes it only where it SKIPPED a column — an empty ratio at a zero 'before',
  and every date-sheet row. The document-order reader slid such rows (the after value into the ratio
  slot, the row dropped as non-numeric): 70 Hard_File float rows, 6 LTF float rows and 4 / 7 LTF
  duration rows were never compared, and the (1, 14) divisor assertion never ran. Column-addressed
  now: **810 / 855 / 1,514** rows, every one half-even under the own-day rule; date sheets 1,225 /
  1,516 unchanged.
* **Registered — R-76 (T1, S):** Fuse's Original / Remaining Duration fields divide by the task's own
  day too (14: 1, not 3; the 24-hour file's 302 / 385 / 389: 2 / 3 / 1), an ELAPSED original duration
  on the PROJECT day (146: 6) but its remaining on 1440 (2); two remaining rows (315 / 129: shown 0 for
  247 / 242 minutes) a different mechanism; the DCMA-08 parity site and `duration_days_axis` priced
  against it (two corpus crossings of 44 days, no Fuse oracle behind either).

## How it was verified

Ten QC-3 assumptions in ADR-0516: eight held, one UNVERIFIED and said so (elapsed-over-task-calendar
precedence — 0 of 16 elapsed activities carries a task calendar), one FELL (the elapsed field
"rounded" — the −13.333… cell). Red first BY VALUE on the pristine engine: the 24-hour DCMA-06
(302, 385) against the ribbon's 0; the synthetic parity sets [1, 2, 3, 6] / [4, 5, 7, 8] against
{3, 6} / {5, 7, 8}; the ribbon (1, 2, 3) against (1, 3). Green after (13 passed). Five mutants of the
helper on shadow copies (the import asserted): the project day always → 5 pins red; the elapsed axis
ignored → 3 (146 by name); the elapsed activity rounded → 3; half away from zero on the own day → 2
(302's 34 → 35, 44.5 → 45); the execution calendar → 2 (94 / 14 / 13). The 23 modules consuming the
DCMA or ribbon sets + the ledger guard 327 passed; statics green on ruff 0.15.8 and 0.16.8 over the
whole tree, `mypy --strict` 165 files, bandit, `node --check`. The full suite ran within the session and is read in the
session log's follow-up; CI's `test` jobs on the PR's FINAL head are the verdict.
Fell in the unit's own plan: the first grid reader (a filter on the judged value), the ribbon-equals-
DCMA-tile premise (49 / 15 against 40 / 11 — different populations, pinned as unmoved, not equal).

## Deliberately NOT done

The five whole-day display sites outside `engine/metrics` (the brief's two float sentences, the
driving view's two at 1 dp, the recommendations' one) and the pure-logic DCMA thresholds stay on the
PROJECT day — priced and HELD: the tool's own reading on the schedule's declared day, MS Project's slack
display convention (UNVERIFIED: no MS Project-rendered export; a view export showing UID 14's Total
Slack settles it) · rounding the elapsed field (the reference does not) · the duration fields (R-76 —
DCMA-08's population rule first) · the LTF field oracle's document-order reader (its grids are
full-width and all 3,637 rows match by value) · a separate pin on `HARD_F~3.XLS` (a duplicate) ·
the Free Float sheet (R-74's row).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-73** (T1, M — the
general `Resume + remaining` model: decide the stored instant's projection FIRST, ADR-0322's two-ruler
rule refuses a second ruler; the wide model's away movers were the after-lunch Resumes) · **R-76**
(T1, S — the duration fields' divisor: DCMA-08's population rule on the `.aft` and the Detailed
Metric Reports' "8. High Duration" marks first, then the 7/15 grids' 282 duration cells under the
own-day rule with the elapsed asymmetry stated) · R-09 · **R-74** · R-69 · **R-71** · R-13 · R-18 ·
R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)); the probe fixture's
Fuse run is the operator's optional confirmation of ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
