# Handoff — 2026-09-22 (c) (R-69 **CLOSED** (ADR-0524) and R-80 **CLOSED** (ADR-0525) — a late START is a start-role instant on the WALL path too, the blocker that deferred it had been dead five commits, and ten of eleven terminal-`.catch` sentences are conflations — **v1.0.288**)

STATUS (current) — `main` @ **`e0daccc4`** (#712, R-77 / ADR-0523, v1.0.287, MERGED 2026-09-22T15:03:30Z; its own runs were read to conclusion by the prior session and are NOT re-read here). 811 commits at session start. §0's anti-foreign-prompt block was RUN and the tree agreed on every point (`origin/main` e0daccc4, 811, `src` present / `app` absent, both workflows, version 1.0.287, highest ADR 0523). This unit ships on **`claude/determined-hopper-x13la6`** as a **draft PR the OPERATOR merges** — `src/` changed and the wheel + nine installers were rebuilt, so **EIGHT checks** apply (CI's `cui-guard` / `browser` / `floor` / `test (3.11)` / `test (3.13)` / `check`, plus installer-smoke's `linux` / `windows`). Highest ADR **0525**. Version **1.0.288**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## What landed — TWO rows

**R-69 (ADR-0524).** `_snap_start_role` gives the backward WALL pass the start-role spelling the
offset path already had. `_retreat_wall` lands a block-exact retreat on the block's END because
`_tod_at_worked` does; MS Project writes the START of the next block. Applied to `ls_w`, **never**
to `lf_w`, and with **no duration exception**.

**R-80 (ADR-0525).** Ten of the eleven remaining terminal-`.catch` sentences route their drawing
callback through ADR-0521's `SFLoad.drawn`. `ai_polish.js` does not — it was measured to cover
exactly one failure mode, and a control test fails if anyone "repairs" it.

## The rows were right about the mechanism and wrong about their numbers — again

* **R-69's BLOCKER had been dead for five commits.** It was priced "NOT a one-line fix" because
  "the contiguous projection of the 13:00 form reads 300 where 12:00 reads 240". ADR-0523 made
  `datetime_to_offset` — and with it `_wall_to_offset` — segment-aware the day before; both
  spellings now read **9360**. Three units have re-verified a row's *numbers*; nobody had
  re-verified the sentence that said why it was expensive. `_wall_to_offset`'s docstring still
  asserted the old behaviour, and that stale prose is the direct source of the mispricing. Both are
  now pinned.
* **R-69's population: 47, not 742** (Hard_File 10 not 14, updated 5 not 9, Large_Test_File **0**
  not 166), plus **24 late finishes** in a class the row says has none. An independent
  reconstruction on pinned v1.0.275 / v1.0.286 / v1.0.287 extracts re-derived the 47 and the 24 and
  found the row's figures track a RENDERED oracle (**659** on the tree it was registered against,
  149 per Large_Test_File copy) — a surface **nothing in the product reads**: `late_start` /
  `late_finish` have ZERO consumers outside `cpm.py`.
* **R-80's census: 27 sites / 23 files / 16 repaired / 11 residual**, not 26 / 22 / 16 / 10 — and
  the row's own enumeration lists 11 while calling it 10.

## The rule, measured from the files rather than assumed

MS Project's own spelling at an internal block boundary, read from the stored values (an oracle
independent of this engine): a **non-milestone late START** takes the LATER form on **754 of 780**
(96.7 %), a **late FINISH** the EARLIER form on **880 of 911** (96.6 %). The role rule holds harder
on the backward pass than on the early dates ADR-0523 measured (71.9 %).

## What it measured

44 files, 22,105 activities, against MS Project's stored values: wall late-START instants exact
**1,628 → 1,698**, late-FINISH **1,728 → 1,755**, stored Total Slack **10,568 → 10,572** (goldens
4,098 → 4,100). Per activity **70** late starts and **27** late finishes moved TOWARD the stored
instant and **NONE away**; **no early instant, no free float and no Critical flag moved at all**.
Two residuals other rows registered close for free: ADR-0510's **UID 147 Saturday 13:00** (carried
through 178's 72 ELAPSED hours) and R-57's "named rather than counted" 60 minutes on **UID 379**
(17,521 → **17,581** = the stored 175,810 tenths — the lunch hour had been float).

## How it was verified

R-69 red first **9 of 14 by name**, the 5 green ones being deliberate controls; battery **7 of 8
red by name**. R-80 red first **9 of 9** by slicing each site's function out of the tree's own bytes
and running it with a 200 + valid JSON and a throwing draw helper — every one printed its LOAD
sentence; battery **4 of 4 red by name** with a green control.

**Two mutants SURVIVED the first R-69 battery and both were findings.** One exposed a vacuous pin.
The other **refuted the rule**: the `duration > 0` guard justified from a 58/54 milestone split
governs a population this seam never reaches (fast-path carried instants), and removing it was
**+5 / −0** where a static simulation had priced it +9 / −36. A third survivor was a finding about
the CODE — a redundant `is_24x7` branch, proven byte-identical across 22,105 activities and deleted.

## Pins moved deliberately, each with its reason and prior value

`test_free_float_bounded_by_total.py` and `test_segment_aware_axis_pair.py` — golden total slack
**(4559, 4098) → (4559, 4100)**, both movers UID 379; free slack `(1142, 1075, 40, 27)` unmoved. ·
`test_r57_assignment_leveling_delay_oracle.py` — UID 379 `17521 and stored 17581` → `== stored ==
17581`. · `test_r58_calendar_intersection_oracle.py` — 147's and 178's instants 12:00 → **13:00**,
both now the file's own; the carried relation (147 == 178's late start less 72 elapsed hours) is
unchanged. · `test_hard_file_stored_dates_oracle.py` — 178 / 179 / 180 late start → 13:00, 147
folded onto `stored_lf[147]`; its late FINISHES deliberately untouched.

## Deliberately NOT done

The **24 late finishes** in the mirror class (MS Project's own convention is the earlier form;
applying the start form to `lf_w` breaks **52** already-exact late finishes — pinned). · The
**milestone spelling in general** (58/54 corpus, 29/25 goldens — ADR-0523's residual stands). · The
**±1-minute** class (R-65) and the **completed-record** class (R-71), both visible in
Large_Test_File's deltas and neither this row's. · **`path.js:767` and `sra.js:497`** — real,
read, confirmed conflations that a literal-matching census cannot see (a VARIABLE and a SETTER),
named and deliberately NOT repaired: widening a registered population by accident is how a census
stops meaning anything. · **Extending ADR-0521's browser poison battery** to the ten — it poisons a
shared dependency global and these draw through module-local helpers, so the instrument does not
transfer; the node transplant is the substitute and the gap is named. · **i18n** for the new
sentences (ADR-0521 held the same).

## R-71 is PRICED, not closed — and its flag half needs one operator ruling

Censused here, independently and with red-before-green: **`is_critical AND NOT is_recorded_complete`
is UID-EXACT against MS Project's stored `Critical` on all 22,105 activities** (2,011 agree, 0
engine-only, 0 stored-only); drop the term and **10** engine-only disagreements appear, named
(Hard_File_updated2 UID 290, Hard_File_updated3 UID 261, Large_Test_File2 UID 6956, + twins). R-71's
premise holds against the bytes: **0 of 8,644** finished activities carry stored `Critical=1`, and
the negative control fires (2,011 incomplete do). Blast radius is tiny — `TaskTiming.is_critical`
has **2** reads in `src/` (`cpm.py:3205`, `float_analysis.py:90`), `CPMResult.critical_path` **2**
(`dcma14.py:596`, `web/path.py:51`), DCMA-12's target changes on **0 of 44** files because
`dcma14.py` already filters `not is_recorded_complete`, and `float_analysis` already exposes both
`critical_count` 2,021 and `critical_incomplete_count` 2,011 — a difference of exactly the 10.

**The ruling needed:** `TaskTiming.is_critical` is documented as "the pure CPM property
`total_float <= 0`". Honouring the record changes a documented field's MEANING. Does the field
change, or does the record-aware answer stay in `is_effective_critical` (which already returns False
for all 10) with `critical_path` alone filtered? Do not implement either without the ruling.

R-71's other limbs also re-censused: **8,644** completed (engine and file-only tests agree exactly,
symmetric difference 0) with LS == AS and LF == AF on **8,644 / 8,644**; **1,159** started with
LS == AS on 1,159 / 1,159; the clamped class is **22** rows / 4 UIDs {389, 5263, 5539, 6444} and the
5539 witness is byte-exact. **Two sub-claims fall:** the `<TotalSlack>` ELEMENT is **absent** on all
8,644 completed rows, so "TotalSlack 0" describes the importer's dropped-zero inference, not the
file (and on `evm/EVM2` it is `None` for UIDs 17/18/19); and UID 5263 is **not** confined to the
Large_Test_File2 family — it carries three distinct signatures across the Leveled and
Large_Test_File files too.

## Traps this session paid for, BY NAME

**A register row's BLOCKER is testimony too** — re-measure the reason a row was deferred, not only
its claim. · **Stale prose is load-bearing**: `_wall_to_offset`'s docstring kept a superseded rule
alive for a month. · **A surviving mutant is a finding about the RULE, not only the test** — two
survived and one refuted my own scoping. · **A simulation of a seam is not the seam** (+9/−36
predicted, +5/−0 measured). · **"A basename is not a key" cost 1,833 activities silently** — a
per-activity dump keyed on `path.name` collapsed 22,105 → 20,272 because two goldens share basenames
with two others, and the comparison still looked self-consistent. · **Every crude filter
under-reports, twice in one unit**: R-69's first census read 38 not 47 (it required "the same
working minute on EVERY calendar", and Hard_File's 24-hour crews have no lunch gap); R-80's
registered census matched a LITERAL and so could not see a variable or a setter. · **A harness that
prints "<nothing printed>" is a broken harness, not a clean site.** · **Do not mutate the tree a
battery is measuring — INCLUDING its docs**: an ADR added mid-gate makes that run's
`test_state_docs.py` meaningless, and a subagent independently caught the working tree changing
under its own measurement and pinned a clean extract instead.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** §3 in order: **R-71** (T3, M — flag
half priced above and BLOCKED on the operator's ruling; the record limbs are unbuilt) · R-13 · R-18
· R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)).
**R-77's residual** (the second-calendar family on `Large_Test_File2`) is unpriced and belongs
beside R-56's chains. **R-80's two out-of-population conflations** (`path.js:767`, `sra.js:497`)
need the operator's decision on whether to widen the row. **Outstanding operator ruling: where the
2026-09-21 (c) foreign kickoff came from.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
