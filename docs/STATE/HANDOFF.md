# Handoff — 2026-09-22 (b) (R-77 **CLOSED** (ADR-0523) — the project axis is **working minutes in BOTH directions**; the row's own population did **not** reproduce and its named witness was **exact** — **v1.0.287**)

STATUS (current) — `main` @ **`d942832d`** (#711, R-74 / ADR-0522, **MERGED** 2026-09-22T05:01:19Z by the operator; head `3f1fa91c`, base `8279010d` — merge and the tree-equality check RE-VERIFIED this session against the API, not inherited; `HEAD^{tree}` == the PR final head's tree `ac2afe10`). **`main`'s OWN runs for `d942832d`, read by their JOBS this session:** installer-smoke 811 (`35689082248`) **success**; CI 1977 (`35689082290`) — `cui-guard` · `browser` · `test (3.11)` · `floor` all **success**, `test (3.13)` still in its parity step and `check` queued behind it when last read. Nothing about `d942832d` is red. 810 commits at session start. This unit ships on the designated branch **`claude/handoff-document-review-46tus2`** (already sitting on the squash; its stale remote-tracking ref pruned) — a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0523**. Version **1.0.287**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed

`datetime_to_offset` and `offset_to_datetime` are now a **segment-aware PAIR**, guarded on
`declared_segments`, plus `_tod_at_worked_start` — the start-role spelling at an internal block
boundary. ADR-0322's two-ruler rule (int→wall segment-aware, wall→int contiguous) is **superseded in
part**: its hazard was a property of the ASYMMETRY, and with both directions moved there is one ruler
again. `_wall_to_offset` moves with `datetime_to_offset` by construction — R-77's plan-forward asked
for the pair to move AND for `_wall_to_offset` to stay unchanged, which is not satisfiable.

**A THIRD rule, found AFTER the first push by the adversarial blast-radius sweep and fixed in the
same PR:** the intraday term is measured **relative to the project start's own worked position**.
ADR-0312 bounds only `start_tod + mpd <= 1440` and returns a legal 09:00 start UNCHANGED; anchoring
at the segments read that origin as 60, and an 08:00 start on a declared 24-hour day as **480** — an
axis shifted by a working day. It moves **no** measured figure: all 44 corpus files anchor at worked
position 0, so the relative form is algebraically identical there.

## The row was right about the mechanism and wrong about everything it counted

Rebuilt corpus, **22,105 activities** (reproduces ADR-0513 exactly). R-77 claimed **212 / 25 / 4** and
named EVM2 UID 23 as the witness.

* **4 reproduces exactly** — but only as a **PROJECTION** error at the stored instant. A pin projected
  and rendered by the SAME ruler cancels its own error, so the rendered census reads **0**. The first
  census built here was blind to exactly the class the row names.
* **212 and 25 reproduce under no constructible measure** (nearest: 104 / 2,506 and 23 / 34 / 0).
* **EVM2 UID 23 is EXACT on both axes** — start delta 0, finish delta 0.
* An identical census against **v1.0.281** returns the same figures, so it is **not drift** from the
  five ADRs since.
* **The class the row does not count is the defect: 15,224 of 22,105** rendered finishes sat exactly
  one gap EARLY — a 17:00 finish saturates `clamp(1020−480, 0, 480)` at 480 and expands back to 16:00.

## What it measured

Against **MS Project's own stored slack**, 44 files: total exact **10,610 → 11,041** of 12,680;
free exact **3,004 → 3,094** of 3,315, high **198 → 134**, low **113 → 87**. Rendered instants exact
**22,453 → 41,950** of 44,210 (start 17,009 → 20,990, finish 5,444 → 20,960). The pristine column
reproduces ADR-0522's recorded figures to the digit, which is how the instrument is known to be the
same one. Goldens only: total **3,897 → 4,098** of 4,559; free **1,034 → 1,075** of 1,142, high
**69 → 40**, low **39 → 27**.

## How it was verified

**Red first on the pristine engine, BY NAME — 5 of 9 red, 4 declared controls green; 9 of 9 green
after.** **Mutation battery 4 of 4 red by name:** the guard removed (only the byte-identical control)
· the start-role spelling removed (only the block-boundary test) · the projection half reverted · the
expansion half reverted. The last two also redden
`test_an_offset_survives_a_trip_through_the_wall_and_back`, which is green on BOTH the pristine and
the shipped engine and red only when HALF the pair moves — the direct guard against ADR-0322's
two-ruler hazard. The patch was proven **behaviourally identical** to the validated shadow before it
touched the tree.

## Pins moved deliberately, each with its reason and prior value

* `test_free_float_bounded_by_total.py` — the free-slack rate `(1142, 1034, 69, 39)` → **(1142, 1075,
  40, 27)**; the total-float control `(4559, 3897)` → **(4559, 4098)**, docstring amended to say the
  AXIS moved, not the bound.
* `test_hard_file_stored_dates_oracle.py::_LARGE` — `tf_exact` **897 → 922** and **746 → 760**;
  File2's finish floor **LOWERED 1689 → 1655**.
* The R-73 assertion that `_stored_instant_offset == datetime_to_offset − 60` is **inverted to pin the
  agreement** — that 60-minute gap WAS the two-ruler disagreement, and there is now one ruler.

## Deliberately NOT done

**Three instants lost**, all `Hard_File_updated4` **UID 305** across its three copies — a completed
zero-duration milestone whose 13:00 instant MS Project spells with the LATER form though it is a
finish. **No rule in the file separates the two spellings:** over all **941** internal-boundary
instants, 81 milestones spell a finish EARLIER and 3 LATER, 306 non-milestones spell a start LATER
and 81 milestones EARLIER — milestone flag and zero duration each fail as a discriminator in both
directions. · **R-77's residual:** on `Large_Test_File2` **1,089 finishes became exact and none lost
exactness**, but **35** already-wrong unstarted finishes (−1,251 to −1,431 min, on the band edge)
moved 120–3,896 min further out past the within-a-day proxy, 1 entered, net −34; **23 of 35 sit on the
file's SECOND calendar** ("ZIN Project Calendar" — of its 138 activities 27 moved further, 9 closer).
This is the **only** measure in the unit that moves AWAY from the reference; the cross-calendar seam
is registered as R-77's residual, priced against R-56's chains, not re-opened here. · The **±1-minute**
class (828 instants, MS Project's sub-minute boundaries — R-65's family) · collapsing
`_stored_instant_offset` into `datetime_to_offset` now that they compute the same thing (same
function, different CONTRACT — the former is only ever a floor under `max()`).

## Traps this session paid for, BY NAME

**A shadow copy of `src/` is not the tree.** The standing recipe copies `src` only, so the vendored-MPXJ
discovery — which walks up from the PACKAGE's `__file__` — finds no `tools/mpxj`. The first suite run
under the shadow reported **22 failures and 3 errors** in `tests/importers` that all read as
consequences of the change; the pristine control was **486 passed**, and symlinking `tools/` turned 22
failures into **382 passed with the code unchanged**. **The recipe must add symlinks for `tools/` and
`00_REFERENCE_INTAKE/`.** · **`schedule_forensics.__version__` reports the INSTALLED distribution, not
the imported source** — the v1.0.281 worktree reported 1.0.286. Probe for a SYMBOL, with a named
positive AND a named negative. · **A pin projected and rendered by the same ruler cancels its own
error** — measure the CONVERSION, not the round trip. · **Never run two suites concurrently when either
binds a port or spawns a JVM** (MPXJ failures once, a Chromium audio test once; both passed alone). ·
**`pkill -f "<pattern>"` matches its own command line** — killed this session's shell twice; use the
`[p]attern` bracket trick. · **Red-first found three defects in the NEW TEST before it found any in the
code** — two "controls" carried red assertions, and the goldens test was VACUOUS (run from a scratch
dir, `parents[1]` missed `tests/fixtures/` and the population was empty; its own population guard
caught it).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** §3 in order: **R-69** · **R-71** (T3) ·
**R-80** (T3, S — the 10 unassessed terminal `.catch` sentences, per-site verdicts BEFORE any edit) ·
R-13 · R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)).
**R-77's residual** (the second-calendar family on `Large_Test_File2`) is unpriced and belongs beside
R-56's chains. **Outstanding operator ruling: where the 2026-09-21 (c) foreign kickoff came from.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
