# Handoff — 2026-09-18 (e) (R-70 **CLOSED** (ADR-0512) — the backward pass stops at finished work: a recorded-complete successor presents no late need and anchors no free float, a started successor presents its REMAINING portion, floored where the work resumes; R-71 / R-72 registered — **v1.0.277**)

STATUS (current) — `main` @ **`4d931ba7`** (#700, R-45 / ADR-0511, **MERGED** 2026-09-18 18:56Z by the operator; the squash TREE-IDENTICAL to this session's arrival HEAD, tree `912770e6…`, compared with `git rev-parse <sha>^{tree}`). PR #700's FINAL head was **`f193522a`** (the kickoff's `839f955e` and the prior handoff's `3a6b3c63` were both superseded by one more docs-only push): its EIGHT checks were read to conclusion this session — CI `35376823983`: `cui-guard` 17:52:10Z · `browser` 18:09:50Z · `floor` 18:19:17Z · `test (3.13)` 18:37:39Z · `test (3.11)` 18:42:34Z · `check` 18:42:41Z; installer-smoke `35376823989`: `linux` 17:52:28Z · `windows` 17:56:55Z — eight of eight green. **`main`'s OWN runs for `4d931ba7`:** CI 1938 (`35383096831`): `cui-guard` 18:56:51Z · `browser` 19:12:33Z · `floor` 19:25:42Z · `test (3.11)` 19:29:59Z green; `test (3.13)` and `check` were still running at 19:40Z — **read them to conclusion first** (the docs-only follow-up records what this session saw last); installer-smoke 776 (`35383096874`): `linux` 18:57:16Z · `windows` 19:01:22Z green. This unit ships on the designated branch **`claude/fervent-ramanujan-ttxvxk`** (started on the squash) as a **draft PR** the operator merges (never marked ready here) — expect EIGHT checks (`installer/**` changed); read the FINAL head's checks. **The gate:** statics green on both ruff binaries (0.15.8 and 0.16.8), `ruff format`, `mypy --strict` (165 files), `bandit` (exit 0), `node --check`; the 13 new pins + the oracle module + the four re-derived pins green; the wheel built after the last `src/` edit; lockstep 68 passed; the full suite and `-m parity` run in a separate worktree at the code commit `8e828bdb` — figures in the docs-only follow-up (the previous unit's baseline: 5,653 passed / 7 skipped at its code commit with 4 attributable failures; this unit adds 13 tests and one oracle test, and re-derives four). Review cover remains ABSENT (Codex quota exhausted). Highest ADR **0512**. Version **1.0.277**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-70 was right about the mechanism and wrong about half its remedy.** The engine bound
Hard_File_updated3's UID 188 to the completed 291's late-start need and read 09-08 for the stored
12-12 17:00 (walked on the engine's own network: integer 21,600, −12,305 minutes of float, five
activities above it following). Measured on the 44-file corpus (15 goldens + 29 conversions, 22,105
activities): every completed activity stores its late dates as its ACTUALS (8,644 / 8,644, slack 0,
never Critical) and every started one its late start as its actual start (1,159 / 1,159); dropping a
finished successor reproduces the stored late finish of all 40 predecessors of finished work from the
file alone (the binding rule 0 / 40). **"Drop a started successor" fell** to one witness — the
logic-reestablished 188 is stored at 187's **Resume**, 08-17 17:00 (not the record 08-05, not the
unfloored 08-12 13:00, not the next successor's 09-07) — and four candidates were measured on the 222
predecessors of started work: the remaining portion's late start FLOORED where it resumes **217**,
unfloored 215, resume 195, the record 193, dropping 138 (the five misses one activity's own clamped
date — R-71); the 22 SS links into started work refute the record and resume.

* **Shipped:** `_late_need` / `_remaining` / `rem_need` / `rem_ls_wall` in `engine/cpm.py` — a
  recorded-complete successor presents no late need and anchors no free float (188's FreeSlack ==
  TotalSlack); a started successor presents its remaining portion (late finish less remaining, never
  earlier than early finish less remaining; FF / SF keep the late finish; an absent remaining — the
  MPXJ writer's dropped zero on the 99 %-complete activities — reads the percent-derived remainder;
  the SRA's override IS the remaining); wall and fast paths; the carried-late binding check reads the
  same need. A started successor's free-float anchor stays its recorded start (EVM1 17 → 18 stores 0).
* **Measured, pristine → this tree, incomplete work:** 93 late finishes toward the stored instant,
  **0 away**, 39 newly exact; 36 slacks newly exact, 69 toward, 0 away; free slack 2,320 → 2,349;
  Critical agreed 21,877 → **22,061** of 22,105 (updated3_24hr 70 → **110 / 110**, updated3 103 → 109,
  updated2 107 → 109, Project2 124 → 126 — the pure-logic count is MS Project's own 41; Project2 /
  Project5 every incomplete late finish exact, 106 / 106 and 99 / 99; LTF / File2 slacks 874 → 876 and
  736 → 740). The movement AWAY is the record class alone (6,176 completed activities' computed late
  finishes — 18 coincidences before, 0 after — and 22 started late starts under R-08's held
  `LF − duration`), plus one file: the logic-reestablished conversion's Critical agreement 109 → 102,
  where the chain above the witness reads +4 days for a stored 0 (the pre-R-70 engine read −8) because
  the engine re-spans 187 for its full 120 h from the floor — **R-72**, exposed, not caused.

## How it was verified

Red first on the pristine package by name (11 of 13 synthetic pins, 2 controls; the oracle's witness
pin); **battery 12 / 12 red by name after ONE survivor** — the carried-late binding check reading the
whole task — exposed a milestone-between-crews case no pin covered (written, red on the pristine
engine and under the cut); four pins re-derived with dated reasons; the oracle's late-finish census
now counts incomplete work only (ADR-0507's decision 3 applied to the late dates). Six QC-3
assumptions recorded in ADR-0512's table: four held, three fell (drop-started, the free anchor, every
started task carrying a remaining).

## Deliberately NOT done

The record's own late dates — LS = AS / LF = AF on finished work, LS = AS on started work, and
MS Project's clamped LateFinish on 22 started activities (**R-71**, T3: it moves `is_critical` on every
finished activity) · the full-duration re-span of a floored started activity (**R-72**, T1: 7 of 192
floored starts finish more than a day late) · the importer's dropped-zero `RemainingDuration` · a free
float floored at zero (MS Project stores none negative) · the logic-reestablished file as a golden (the
floor's only file witness; pinned synthetically).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-72** (T1, M — the
floored started activity spans its REMAINING from the later of the floor and Resume; red-first on
187's 08-20 17:00; measure against ADR-0476's rejected variants on the whole corpus first — UID 1489's
136-day swing is the trap) · R-03 · R-04 · R-09 · R-69 · **R-71** · R-13 · R-18 · R-21 · R-22 · R-32 ·
R-39; R-68 waits on the operator's reading (question (f)). The design queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
