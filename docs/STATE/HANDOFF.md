# Handoff — 2026-09-20 (e) (R-73 **CLOSED** (ADR-0517) — every started activity's remaining work is scheduled from its stored Resume, read in WORKING MINUTES of the calendar's own segments; the plan's first projection fell to the stored slack; the contiguous projection of the rest of the stored-date family registered as R-77 — **v1.0.281**)

STATUS (current) — `main` @ **`b0545572`** (#705, R-75 / ADR-0516, **MERGED** 2026-09-20 10:50:27Z by the operator; the squash TREE-IDENTICAL to PR #705's FINAL head `418a7da9`, tree `211074bc…` — re-verified this session with `git rev-parse <sha>^{tree}`, this clone's `HEAD^{tree}` == `origin/main^{tree}`). **PR #705's FINAL head, EIGHT checks read to conclusion:** CI `35503523545` — `cui-guard` 09:53:27Z · `browser` 10:11:07Z · `floor` 10:16:54Z · `test (3.13)` 10:41:46Z · `test (3.11)` 10:49:20Z · `check` 10:49:26Z; installer-smoke `35503523552` — `linux` 09:53:38Z · `windows` 09:57:43Z — **eight of eight green**. **`main`'s OWN runs for `b0545572`, by their JOBS:** CI 1959 (`35506181085`) `cui-guard` 10:50:48Z · `browser` 11:07:13Z · `floor` 11:13:40Z · `test (3.13)` 11:40:47Z · `test (3.11)` 11:37:26Z · `check` 11:40:54Z — six of six; installer-smoke 793 (`35506181084`) `linux` 10:51:08Z · `windows` 10:55:23Z. Nothing about `b0545572` is outstanding. This unit ships on the designated branch **`claude/document-review-continuation-bvzkwm`** (restarted on the squash; its stale remote ref pruned) as a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0517**. Version **1.0.281**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-73's premise was attacked before the first edit and the plan's projection FELL to an independent
oracle.** The row's remedy was "decide the stored instant's projection first". The first candidate
walked the remaining on the calendar's true segments from the Resume and projected the FINISH with the
contiguous ruler (ADR-0322's wall→int rule): the census read 1,111 started finishes "exact" — while the
stored slacks exact fell **11,177 → 9,930** and free slacks 2,367 → 2,041. The instrument had compared
the engine's contiguous projection with the stored finish's contiguous projection and agreed with itself
by construction; the stored slack, a working-minute quantity no ruler touches, refuted it. **The axis IS
working minutes** — `start + duration` counts them exactly — and the contiguous ruler is wrong only
where it PROJECTS a mid-day instant (15:00 on a 08-12 / 13-17 day is minute 420 there, 360 worked).
The shipped rule reads the stored Resume SEGMENT-AWARE (`_stored_instant_offset`) and adds the
remaining on the axis; that read is a floor under `max()` against the link bounds, so no restart can
precede a linked predecessor's finish — ADR-0322's two-offsets trap does not bite a floor.

* **Shipped:** every started, incomplete activity with a recorded actual start, a restart instant and a
  STORED remaining (or the SRA's override) resumes it at the later of its Resume and the link bounds for
  the remaining, on both paths; the backward pass retreats by the remaining (the total float is the
  finish slack); an in-sequence started successor keeps its RECORD as its predecessor's free-float
  anchor (EVM1 17's 0); a reschedule is disclosed only where it moves the finish past logic and the
  record's own plan; ADR-0309's floor is subsumed (kept for a reschedule on an activity without an actual
  start). An absent remaining is MPXJ's dropped zero — `ActualDuration == Duration` on all 10 in the
  corpus, in two shapes (Stop = Resume = the actual start on EVM1 17 / 267; = the finish on 302 / 385)
  no single reading fits — and keeps `actual_start + duration`.
* **Measured, pristine → this tree, 44 files, 22,105 activities:** started finishes exact 1,050 →
  **1,114** (64 toward, 0 away — the segment-aware instrument; the first probe's 776 was the contiguous
  ruler judging itself), within a day 1,107 → 1,126, starts 1,144 unchanged; 232 unstarted starts and
  248 finishes newly exact; late-finish instants exact 11,543 → **11,645**; stored slacks 11,177 →
  **11,383**; free slacks 2,367 → 2,428; Critical agreed 22,069 → **22,095**; no boolean measure lost a
  member; project finishes exact 27 → 28 (`24Hour Calendar.mpp` 2027-08-23 → the stored 2027-08-04);
  `date_driven` 525 → 490 (ten after-lunch Resumes that TIE their FF bound had been read past the tie).
  Witnesses (engine − stored, working minutes): 4616 −34,080 → 0 (float 161,760 → the stored 127,680),
  7378 +480 → 0 (306,720 / 60,240 exact), 5505 −14,400 → −1 (the minute grid), 1489 +60 → 0 (98,880),
  the 24Hour file's 17 +92,160 → 0 (3,180 → 70,860); EVM1's 18 / 17 unmoved; TP4 v3's 19 exact both.
  39 slacks on Large Test File2 read 30–60 min farther: their early finish's lateness no longer cancels
  part of a 1,450 / 4,330-minute late-finish error (R-56's chains). 45 started finishes remain off,
  every one named (the four split bookings, 5505's minute, the dropped-zero trio).
* **Pinned:** `tests/engine/test_started_work_resumes_remaining.py` (11 — 9 red on the pristine package
  by name, 2 controls); the R-72 module's in-sequence crew pin re-derived (Resume + 16 crew hours →
  Wednesday 17:00, float 2,880); the stored-dates oracle re-pinned UPWARD (LTF finish-within-a-day
  1,682 → 1,686, slacks 882 → 897; LTF2 741 → 746; the 24-hour snapshot 15 → 16), UID 1489 EXACT, an R-73
  witness on 4616 / 7378 / 5505 and EVM1's 18 / 17. **Battery 8 / 8 red by name** (the contiguous Resume,
  both triggers restricted, the percent fallback, the whole-duration retreat, the restart anchor, the
  disclosed contiguous progress, ADR-0309's floor re-applied), the control green.
* **Registered — R-77 (T2, M):** the rest of the stored-date family and the rendering project
  contiguously: 4 after-lunch actual starts, 25 pinned completed finishes (54–60 min late), 212
  unstarted finishes exactly one lunch gap off; the family and the rendering must move to a
  segment-aware pair together (ADR-0322's trap).

## How it was verified

Twelve QC-3 assumptions in ADR-0517: ten held, one fell (the projected finish), one held with a
mechanism (the dropped zero). Pristine baseline reproduced ADR-0513's population to the number.
`tests/engine` + `tests/parity` + `tests/test_projects` **1,563 passed** (`PYTEST_EXIT=0`, 6:22); the
CPM counterfactual's consumers in `tests/web` + `tests/importers` + the SRA **470 passed**;
`tests/installer` 68 after the rebuild; statics green on ruff 0.15.8 and 0.16.8 over the whole tree,
`ruff format`, `mypy --strict` 165 files, `bandit`, `node --check`. The final tree reproduces the chosen
candidate on all 22,105 activities (0 differing timings). The full suite is read in the session log
with the PR number.

## Deliberately NOT done

Reading an absent remaining as zero (fixes 302 / 385 on the 24-hour snapshot, breaks 17 / 267) · a
seconds-aware Resume (5505's minute is R-65's grid) · the late START of started work (R-71) · the
free-float cap (R-74) · the four split bookings (R-60's tail) · a finish-slack-only total for the
wide class (the retreat by the remaining already makes `min()` the finish slack) · the stored-date
family's projection and the rendering (R-77 — a family, not a site).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-76** (T1, S — the
duration fields' divisor: DCMA-08's population rule on the `.aft` and the Detailed Metric Reports' "8.
High Duration" marks first, then the 7/15 grids' 282 duration cells under the own-day rule with the
elapsed asymmetry stated) · R-09 · **R-74** · **R-77** (T2, M — the segment-aware pair; census the
212 / 25 / 4 and every rendered-time pin first) · R-69 · **R-71** · R-13 · R-18 · R-21 · R-22 · R-32 ·
R-39; R-68 waits on the operator's reading (question (f)); the probe fixture's Fuse run is the
operator's optional confirmation of ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
