# Handoff — 2026-09-20 (R-72 **CLOSED** (ADR-0513) — out-of-sequence progress resumes its REMAINING work at its recorded start, from the later of the stored Resume and the logic bounds for the remaining; a start-type successor need binds no started predecessor; R-73 / R-74 registered — **v1.0.278**)

STATUS (current) — `main` @ **`5b605970`** (#701, R-70 / ADR-0512, **MERGED** 2026-09-19 00:12Z by the operator; the squash TREE-IDENTICAL to PR #701's FINAL head **`71372027`**, tree `4a807e3f…`, compared with `git rev-parse <sha>^{tree}`; the kickoff's `c5e31376` was one docs-only push stale). PR #701's FINAL head's EIGHT checks were read to conclusion this session — CI `35396337875`: `cui-guard` 21:21:32Z · `browser` 21:38:54Z · `floor` 21:47:12Z · `test (3.13)` 22:07:33Z · `test (3.11)` 22:13:08Z · `check` 22:13:16Z; installer-smoke `35396337876`: `linux` 21:22:04Z · `windows` 21:25:55Z — eight of eight green. **`main`'s OWN runs for `5b605970`, read by their JOBS:** CI 1945 (`35408559575`): `cui-guard` 00:13:01Z · `browser` 00:30:16Z · `floor` 00:40:20Z · `test (3.13)` 00:59:03Z · `test (3.11)` 01:04:07Z · `check` 01:04:13Z — **SIX OF SIX GREEN**; installer-smoke 783 (`35408559573`): `linux` 00:13:31Z · `windows` 00:15:44Z green. Nothing about `5b605970` is outstanding. This unit ships on the designated branch **`claude/dazzling-knuth-68vcoq`** (started on the squash; its origin ref had been pruned with the merge) — code commit **`6bfbeac0`**, the draft PR opened after the docs commit and recorded in the follow-up (the operator merges; never marked ready here) — EIGHT checks (`installer/**` changed); read the FINAL head's checks. **The gate:** statics green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`, `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the 18 new pins + the re-pinned oracle module + R-70's module green (45 passed); the wheel built after the last `src/` edit; lockstep 68 passed; the report guard green with the three row edits; **the full suite and `-m parity` are running in a separate worktree at `6bfbeac0`** — figures in the docs-only follow-up; baselines to attribute against: the previous unit's worktree run read 4 failed (attributable) / 5,667 passed / 7 skipped at its code commit, and this unit adds 18 synthetic pins + 1 oracle pin and re-pins the two Large Test File rows UPWARD. Review cover remains ABSENT (Codex quota exhausted). Highest ADR **0513**. Version **1.0.278**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-72's mechanism held and three of its premises fell.** The engine re-spanned an out-of-sequence
started activity for its FULL duration from the logic start (the floor could not bind — the logic
start was the later instant): the logic-reestablished 187 (60 %, 48 crew hours left) ran 120 h from
188's 08-17 17:00 finish to 08-27 08:00 for the stored 08-20 17:00, and the need 188 read from it
(R-70) sat four days late. Measured on the 44-file corpus (22,105 activities, 1,159 started):
MS Project's rule `Finish = Resume + RemainingDuration` holds on **1,113 of 1,159** from the file
alone (every started activity carries a Resume; every file scheduled with split-in-progress on).
The row's "floor" is a LINK on 186 of the 192 out-of-sequence activities and a CONSTRAINT on UID
4581 (its SNET lies after its actual start; MS Project resumes its work at the status date); the
whole-task logic start is the wrong bound for the remaining (UID 1489's ten FF links from finished
work put its whole-task start 26 days before its Resume); and the 1489 "trap" the kickoff named was
ADR-0476's FULL-duration re-span from a pinned start — Resume + remaining reproduces its stored
Finish. Six candidate rules were measured on the population before one was chosen (ADR-0513's table):
the WIDE `Resume + remaining` model for every started activity gains more but reads an after-lunch
Resume an hour late on the contiguous axis (ADR-0322's two-ruler rule; EVM1's finish date crosses
midnight) — registered as **R-73**, not taken. Its regressions exposed a second mechanism: an SS / SF
successor need bounds a started predecessor's late START, which is a record — UID 5535's late finish
read 2027-07-02 for the stored 11-05 on the pristine engine (73 predecessors, 84 links).

* **Shipped** (`engine/cpm.py`): such an activity starts at its RECORD; its remaining portion starts
  at the later of the stored Resume (else Stop) and the link bounds evaluated for the remaining
  (FS / SS as before, FF / SF retreating the remaining — the plan's tail on the wall path), never a
  constraint; its finish is that restart plus the remaining on its own legs (the SRA override IS the
  remaining; an absent remaining is the percent-derived remainder); the backward pass retreats it by
  the remaining; a start-type successor need binds NO started predecessor; a predecessor's free float
  anchors at the remaining portion's start; disclosed on `actual_start_driven` and, where the stored
  Resume places the work, `date_driven`. A source recording neither Resume nor Stop is unchanged.
* **Measured, pristine → this tree:** started finishes within a day 1,094 → 1,107 (exact 343 → 346;
  > 1 d late 25 → 18, early 40 → 34), starts exact 963 → **1,144**, the out-of-sequence class 192 → 0;
  incomplete work's late finishes exact 11,512 → 11,543, stored slacks 11,034 → 11,177, free slacks
  2,354 → 2,372, Critical agreed 22,061 → 22,069; 173 unstarted successors and 13 started finishes
  toward their stored dates, **one** figure away in 22,105 (UID 408's free float, above its total —
  **R-74**: MS Project's stored FreeSlack never exceeds its TotalSlack, 0 of 3,315; the engine's does on
  1,870); the witness file's Critical 102 → **110 of 110** and its project finish 11-15 08:15 → the
  stored **11-12 12:00**; Large_Test_File's stored slacks exact 876 → 882 (late finishes 921 → 922),
  File2 740 → 741; every other golden byte-identical.

## How it was verified

Red first on the pristine package by name (17 of 18 synthetic pins, 1 control; the oracle's witness
pin and its two re-pinned rows); **battery 21 / 21 red by name on the third run** after six survivors
across two runs — every one a missing WALL-PATH pin (an FF need, a Resume == Stop past the logic —
the first pin's Resume > Stop shape was ADR-0309's floor's, an equivalent mutant — a start-type need
on a crew predecessor, a crew successor's anchor), written, red on the pristine engine and under the
cut; the shadow run of `tests/engine` + `tests/parity` + `tests/test_projects` against the candidate
read 1,507 passed with the two Large Test File rows the only failures (both floors UP; 10 errors the
copy's missing `tools/mpxj`); the working tree's census reproduced the candidate's on every one of the
22,105 activities. Eleven QC-3 assumptions recorded in ADR-0513's table: five held, six fell.

## Deliberately NOT done

The general `Resume + remaining` model for every started activity (**R-73**, T1 M — held back by the
contiguous axis's hour on an after-lunch Resume, ADR-0322) · the free-float cap (**R-74**, T2 S) · the
record's own late dates, the 22 clamped late finishes and the Critical flag on finished work (**R-71**,
amended: the start-type needs and the out-of-sequence late start are taken) · the importer's
dropped-zero `RemainingDuration` (it reads 0 on 302 / 385 and the whole duration on EVM1's 17 and 267)
· UID 3849's holiday actual start · the witness file as a golden (pinned synthetically; 1489 / 4581 /
5535 on the Large Test File golden carry the oracle).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-03** (T1, S —
`dcma14.py`'s banker's rounding at exactly .5: build the −0.5 d / 44.5 d fixture, pin the current
classification with its delta, and ask the operator for the Acumen run that settles it) · R-04 · R-73
· R-09 · R-74 · R-69 · **R-71** · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's
reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
