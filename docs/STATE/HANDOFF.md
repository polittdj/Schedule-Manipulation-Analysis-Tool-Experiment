# Handoff — 2026-09-20 (b) (R-03 **CLOSED** (ADR-0514) — Acumen Fuse's Total Float field is the stored slack rounded HALF-TO-EVEN to whole days; dcma14's two parity roundings are the reference's own rule, named as `acumen_whole_day_float`; the probe fixture extended to the 44-day side — **v1.0.279**)

STATUS (current) — `main` @ **`85f0c6ce`** (#702, R-72 / ADR-0513, **MERGED** 2026-09-20 02:57:43Z by the operator; the squash TREE-IDENTICAL to PR #702's FINAL head **`044cf15a`**, tree `8e0c283c…`, compared with `git rev-parse <sha>^{tree}`). PR #702's FINAL head's EIGHT checks were read to conclusion this session — CI `35481909671`: `cui-guard` 01:38:39Z · `browser` 01:55:53Z · `floor` 02:06:27Z · `test (3.11)` 02:25:29Z · `test (3.13)` 02:26:13Z · `check` 02:26:19Z; installer-smoke `35481909587`: `linux` 01:39:19Z · `windows` 01:43:59Z — eight of eight green (its FIRST head `dc862dbf` had read `floor` / `test (3.11)` / `test (3.13)` red on the three `+12 wd` counterfactual pins ADR-0513 legitimately moved to +6 — re-derived in `044cf15a`). **`main`'s OWN runs for `85f0c6ce`:** CI 1949 (`35485335370`) and installer-smoke 787 (`35485335341`), created 02:57:46Z — read by their JOBS in the docs-only follow-up (a red cell on a tree identical to the green PR head is the runner's claim). This unit ships on the designated branch **`claude/dazzling-knuth-68vcoq`** (restarted on the squash with `--prune`) — the code + docs commit and the docs-only follow-up carrying the draft PR's number (the operator merges; never marked ready here) — EIGHT checks (`installer/**` changed); read the FINAL head's checks. **The gate:** statics green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`, `mypy --strict` (165 files), `bandit`, `node --check` per file; the new oracle module (2 passed, 32 s), the dcma14 / schedule-quality / DCMA-audit modules (42), the Fuse parity oracles + ribbon (113), the extended probe guard (11); red by name under two mutants of the helper; the wheel built after the last `src/` edit; lockstep 68 passed; the report guard green with the two row edits; **the full suite and `-m parity` run in a separate worktree at the code commit and are READ TO CONCLUSION before the follow-up (the previous unit's worktree suite died at 57 % unread — CI caught what it would have)**. Review cover remains ABSENT (Codex quota exhausted — its bot said so on #702 at 02:57Z). Highest ADR **0514**. Version **1.0.279**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

**R-03's premise fell to the reference's own exports.** The row read dcma14's two Acumen-parity
classifications (`round(eff / mpd) < 0`, `> 44`) as a banker's-rounding defect at an exact half day and
asked for a −0.5 d / 44.5 d fixture and an operator's Fuse run. Reading everything first (QC-2): the
negative-side fixture already existed (`NEGFLOAT_SubDay_Probe.xml`, PR #576, never run, its ask dropped
from the operator list); both metric libraries define "6. High Float" / "7. Negative Float" with an
EMPTY formula and a bare `Total Float > 44` / `< 0` filter on `Baseline Duration > 0` — the FIELD's
grain is the whole question; the 44-file corpus holds **772** exact half-day floats in dcma14's parity
population and **none** at the tie (near the thresholds only 5283's −0.29 d, 45.0 d exactly, 45.27 d),
so a census cannot decide the tie — nor rounding against truncation. The oracle was the intake: Fuse
prints a Total Float beside every activity of its detail grids, and the 13 Large Test File workbooks
hold 1,140 such grids — **3,637** distinct activities, none displayed with two values — every one the
stored slack rounded **half-to-even** (LTF 1,513 / 1,513; LTF2 2,124 / 2,124). The first snapshot's
**196** half-day floats split **118** odd-part rounded UP (513.5 → 514, 579.5 → 580) and **78**
even-part rounded DOWN (24.5 → 24, 514.5 → 514, 630.5 → 630); half away from zero misses the 78,
truncation the 118 and 154.75 → 155. The Analyst Quick Add Metrics workbook's complete "6. High Float"
/ "7. Negative Float" sets are UID-exact against `compute_dcma14(acumen_parity=True)` on both
snapshots (**814 / 35** and **660 / 112**) with 5283 absent — the filters read the field.

* **Shipped:** no flip. `_common.acumen_whole_day_float(minutes, mpd)` names the rule (half-to-even,
  the measurement in its docstring); dcma14's two parity sites and the ribbon's Negative Float
  (`schedule_quality.py`, ADR-0473) call it; R-04's sweep exempts them. `tests/parity/
  test_fuse_total_float_field_oracle.py` pins the display oracle (populations 1,513 / 2,124, the 196
  with their 118 / 78 split, the alternatives refuted BY NAME) and the set oracle (both snapshots,
  5283 absent). `test_dcma14.py` pins the synthetic ties with the delta against `round_half_up` beside
  them (it would read −1 / 45). The probe fixture carries the **44-day side** (UIDs 109–113: +45.00
  control, +44.75 / +44.50 / +44.25 discriminators, +44.00 control, a 46-day driver, the +8 d control
  on its own FNLT, every control label naming its metric) and its guard pins the DCMA-06
  discrimination and the two ties by value (11 passed).
* **Measured:** every existing figure unchanged — the dcma14 / schedule-quality / DCMA-audit modules
  42 passed, the Fuse parity oracles + ribbon 113 passed; the goldens byte-identical.

## How it was verified

Nine QC-3 assumptions in ADR-0514's table: eight held, one **UNVERIFIED at the tie itself** (the
filter's reading exactly at −0.5 / 44.5 is inferred from the field's rule and the set identity; no corpus
activity occupies it — the probe's run is the direct confirmation). Red first, by name, on two mutants
of the helper on a shadow copy (the package asserted by mutcheck): half away from zero → the tie pin
`{2, 3, 4} != {3, 4}` and the display oracle red on the 78 even halves; truncation → `{4} != {3, 4}`
and the display oracle red on the odd halves and the non-tie fractions. The set oracle stays green under
both **by design** (its teeth are the population and the set identity, not the tie — said so in the
ADR). Control green (2 passed, 32 s).

## Deliberately NOT done

`round_half_up` anywhere in the classifications (refuted on 196 half-day displays) · truncation (refuted
118 + 154.75 → 155) · a raw-slack filter (refuted by 5283) · the 20260423 library's generic "Negative
Float" / "High Float 44d" variants without the baseline filter (the DCMA ones are modelled) · the
truncated grids as oracles · `margin.py` / `wbs_breakdown.py`'s 1-dp `round()` displays (R-04's) · the
operator's Fuse run of the probe as a blocker (optional confirmation: expected 102 and 111 NOT counted).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-04** (T1, M — the
327 `round()` sites by exposure; the three `acumen_whole_day_float` callers are exempt, and each
displayed figure is read against the reference tool's OWN rule for it, measured per figure, never assumed
to be half-up) · R-73 · R-09 · R-74 · R-69 · **R-71** · R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits
on the operator's reading (question (f)); the probe fixture's Fuse run is the operator's optional
confirmation of ADR-0514's assumption 5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
