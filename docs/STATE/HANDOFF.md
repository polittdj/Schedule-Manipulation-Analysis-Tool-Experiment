# Handoff — 2026-09-21 (b) (R-79 **CLOSED** (ADR-0520) — Acumen Fuse's DCMA-09 is TWO metrics with TWO populations and a FIELD numerator: the forecast tile over the baselined INCOMPLETE activities, the actual tile over the baselined STARTED-OR-COMPLETE ones, the Bible declaring both out loud — **v1.0.284**)

STATUS (current) — `main` @ **`85feef00`** (#708, R-78 / ADR-0519, **MERGED** 2026-09-21 12:31:32Z by the operator; the squash TREE-IDENTICAL to PR #708's FINAL head `44e93517`, tree `03aafb9e…` — re-verified this session, this clone's `HEAD^{tree}` == `origin/main^{tree}`). **`main`'s OWN runs for `85feef00`, by their JOBS, all read to conclusion THIS session** (the prior session read only two of six and left four in progress): CI 1968 (`35600035575`) `cui-guard` 12:31:48Z · `browser` 12:48:22Z · `floor` 13:05:08Z · `test (3.11)` 13:14:35Z · `test (3.13)` 13:23:06Z · `check` 13:23:11Z — **six of six green**; installer-smoke 802 (`35600035633`) `linux` 12:32:18Z · `windows` 12:36:09Z. Nothing about `85feef00` is outstanding. This unit ships on the designated branch **`claude/friendly-maxwell-3zy2i9`** (branched from the squash) as a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0520**. Version **1.0.284**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**The row was right about the arithmetic, under-evidenced about the witness, and WRONG about the
remedy.** R-79 said the DCMA-09 tile's denominator is the baselined INCOMPLETE population and
prescribed "scope the parity DCMA-09 denominator" to it. The denominator claim holds. The remedy
does not: Fuse computes **two** metrics here, and **two populations cannot share one denominator**.

* **The Bible declares both populations out loud** — in BOTH committed `.aft` snapshots, in every
  `Metric` record, under `PrimaryFilter`: `9. Invalid Forecast Dates` carries
  `IncludeComplete=false` (planned-or-in-progress = **incomplete**) and `9. Invalid Actual Dates`
  carries `IncludePlanned=false` (**started-or-complete**), and the Remarks say the same in prose.
  Nobody had read it: the aft-audit row for `DCMA09` said **`NOT_IN_BIBLE`**.
* **The FIELD count is in the Formula**, not an inference — it SUMs two terms per activity, so
  File2's **322** is fields over **170** activities. ADR-0283's "documented divergence" was the
  tool being wrong.
* **Shipped:** `DCMA09` "Invalid Forecast Dates" + **`DCMA09_ACTUAL`** "Invalid Actual Dates",
  both keys in BOTH modes (a key set that varied by mode would break every consumer), exactly as
  `DCMA04` is already three keys. Parity counts FIELDS over the two baselined populations; an
  empty population reports no figure via `population == 0` (ADR-0519's carrier). `scorecards.py`
  BP9 ANDs the halves as BP7 already ANDs high/negative float. `metric_catalog`, `dcma_audit`,
  `help.py` + `docs/METRIC-DICTIONARY.md` follow; the aft-audit row moved to **MATCH** with both
  formulas pinned verbatim.
* **Measured — 26 / 26** (workbook, label) pairs across six workbooks, every count and every ratio
  plus the N/A. The discriminators, all on saves the repo holds: File2 **322 / 904** → 0.36 (every
  baselined 1,568 → 0.21; every incomplete 998 → 0.32) and **4 / 752** → 0.01 (the unfiltered
  started-or-complete 816 cannot print 0.01); `Hard_File_updated2` **30 / 58** → 0.52 — an EXACT,
  unique pin the row never had (84 → 0.36); the 24-hour file **1 / 12** → 0.08 (82 → 0.01); EVM1
  **8 / 8** → 1.00, which pins the FIELD count (5 activities) though not the completion filter.
* **Rendered, not inferred:** `/scorecards` BP9 shows *"forecast dates 322 of 904 (35.6%); actual
  dates 4 of 752 (0.5%)"*; `/standards` shows `Invalid Actual Dates` **—** / **NA** for `Hard_File`,
  which has no started-or-complete activity at all — exactly where Fuse prints N/A.
* **The split separated two defects the combined check conflated.** TP3's old count of 5 is 4
  forecast-side (stale stored forecasts 14 / 25 / 26 / 32) **plus 31 alone**, a completed task
  statused ten days into the future. Different finding, different remediation.

## How it was verified

Ten QC-3 assumptions attacked before the first edit; **three fell** — the row's prescribed remedy,
"every ribbon reading is an oracle", and "the corpus determines the completion-state rule". **Red
first by name** on the pristine tree (`engine 5 != Fuse 8` on EVM1; 27 of 30 red). **Mutation
battery 5 of 6 red by name**, control green: the old `ap_tasks` denominator · activities instead of
fields · the actual side over the forecast population · an unfiltered actual population · dropping
the finish-side field. Five further mutants proved the three negative pins can fail. **The sixth
mutant SURVIVED, and that is the finding:** swapping "started" from `actual_start is not None` to
`percent_complete > 0` leaves all 30 green, because three forecast-side and six actual-side rules
each reproduce 16 of 16 tiles and disagree on **0** of the **8,190** activities in all 24 committed
fixtures. Recorded UNVERIFIED in ADR-0520 and pinned by a census test. `/scorecards` regressed to
**HTTP 500** mid-unit (a `replace(..., 1)` landed the BP9 block in `compute_nasa_stat` instead of
`compute_gao_scorecard`) — caught by RENDERING the page against the pristine tree, by no unit test.

## Deliberately NOT done

The five TP4 versions and EVM2 as ENGINE oracles (ADR-0518/0519 measured Fuse to have scored LATER
saves; they stay evidence for the RULE from Fuse's own cells) · the two restricted-filter ribbons as
whole-schedule oracles (excluded by a measured signature, not a claim) · a rounding decision for
either ratio (**no tie at 2 dp anywhere in the corpus**; the display path is unchanged) · renaming
`DCMA09` to a `_FORECAST` suffix · `Wrong Status` as a third engine metric (0 / 0 on both export
projects, so it teaches nothing) · moving the status-date-less N/A onto the population carrier (that
case is "cannot be assessed", not "no population", and keeps `NOT_APPLICABLE`).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-09** ·
**R-74** (T2, S — free float above the total) · **R-77** (T2, M — the stored-date family and the
rendering projected CONTIGUOUSLY; census the 212 / 25 / 4 and every rendered-time pin FIRST) ·
R-69 · **R-71** (T3) · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's
reading (question (f)); the probe fixture's Fuse run is the operator's optional confirmation of
ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
