# Kickoff prompt — next session

**`main` @ `80ae617e` (#692, the docs-only record of #691's merge) — its OWN CI was read TO CONCLUSION: run 1908 (`35175117266`) SUCCESS, all six jobs (`cui-guard` 02:37:38Z · `browser` 02:55:06Z · `floor` 03:03:03Z · `test (3.13)` 03:07:16Z · `test (3.11)` 03:15:54Z · `check` 03:16:18Z), and NO installer-smoke run exists for it, which is CORRECT (three `docs/STATE/` files; the workflow is path-filtered — verified against the `main` run list, whose newest is 746 for `2c549d8d`). Nothing about `80ae617e` is outstanding; do NOT re-read it. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one — the merge-record treadmill was deliberately ended, so this head block will lag `main` by design.**

**R-58 is CLOSED — ADR-0503, draft PR the draft PR opened from this branch (its number is recorded in the follow-up docs-only commit) (the OPERATOR merges; if it is merged when you arrive, `main` has moved past `80ae617e` — read ITS own six jobs to conclusion and expect EIGHT checks on the PR, since the diff touches `installer/**`). A task calendar meets a crew calendar on their INTERSECTION — `_calendar_intersection` behind `_task_shape` and `booking_calendar`: weekdays ∩, intraday blocks pairwise ∩, holidays ∪, an extra working day only when both work it; a calendar the other restricts nothing of stands for the intersection BY IDENTITY (a 24-hour task calendar → the crew's object, as ADR-0474 had it); WORK crews that NAME a calendar only (a MATERIAL / COST booking and a crew the file names no calendar for keep the task calendar); disjoint calendars fall back to the task calendar (UNVERIFIED — no witness); the slack axis stays the TASK calendar (ADR-0474). Do not re-derive it.**

**The row's witness was WRONG and the correction is the finding:** Hard_File UID 14 is on `24 Hours`
(calendar 10) in all seven snapshots — the intersection the engine already modelled exactly, which is
why ADR-0491 found its span reproduced. The task on `Standard+Sat.` (calendar 12: 07:00-12:00,
12:30-19:00, 19:30-23:30, Mon–Sat) is **UID 94**, an 8-hour FIXED_UNITS activity on the same 16-hour
crew. **Population, on the engine's own `_task_shape`:** 301 tasks in the 15 goldens carry an
off-pattern task calendar with a WORK booking — 294 non-24-hour (293 of them Large Test File tasks
under same-pattern crews that restrict nothing) plus UID 14's seven — and exactly ONE task's crew
cuts into its calendar: **UID 94 in 5 snapshots, 3 recorded-complete** (ADR-0476's pin adjudicates
nothing). The 29 `.mpp` files add the same task in one more save.

**Measured:** UID 94 16:30 → MS Project's **17:00** on both unstarted snapshots; on `updated` ALL FIVE
stored values (Start, Finish, LateStart 08-14 14:30, LateFinish **Friday** 08-14 23:00 where the task
calendar alone wrote **Saturday** 23:30, TotalSlack 2,190 on the task calendar); UID 157 exact with
it. Hard_File exact finishes 38 → 40, exact stored slack 37 → 39; `updated` 106 → 108, 99 → 101;
**12 activities moved, 0 away, 13 goldens BYTE-IDENTICAL**, project finishes and every disclosure
unmoved; the `.mpp` corpus 26 of 29 byte-identical, 18 task-moves on the three Hard_File saves, none
away.

**Registered, NOT taken — do not treat as settled:** **R-67** — on the base `Hard_File` snapshot UID
94's slack reads 6,510 against 6,360 and the 150 minutes are milestone 147's stored LateStart of
**Saturday 08-01 13:00**, an instant MS Project keeps on the ELAPSED axis inside the weekend (ADR-0476's
day-boundary class); the engine's integer axis has no Saturday, 147 reads Monday 08:00, 157 reads its
late finish two hours late on the crew's axis, 94 inherits. ADR-0474's backward arithmetic is EXACT
when fed the stored Saturday. Its first step is in the row. Also: the empty-intersection fallback
(UNVERIFIED), an exception day's own hours (the model records a date only), and a crew the file names
no calendar for (not intersected — its calendar is unknown, not the project's).

**Traps this unit paid for:** **a row's WITNESS is testimony too** — read the activity's own XML before
pricing the rule it is said to prove (UID 14 vs UID 94: one dump) · **a five-value oracle beats a finish**
— the late finish on the Friday-not-Saturday is the weekday intersection OBSERVED; a rule with only a
30-minute finish to show has 30 minutes of evidence · **the rig can be wrong twice before the engine is**
— "150" was the start-slack gap (the finish-slack gap is 120) and "301 non-24-hour" was 294 + 7;
recompute every expectation from the rig's own numbers · **a survivor that is not dead code is a
missing pin, and its case is the finding** — M06b (the identity shortcut for a task calendar that
CONTAINS the crew's) survived the first battery; the pin that killed it is the only test of a Mon–Sat
task over an ordinary Mon–Fri crew · **an instrument's own name-collision is the corpus lesson in new
clothes** — `Large Test File.mpp` / `Large_Test_File.mpp` sanitised to one name skipped a file; count
the artefacts (28 ≠ 29), never trust the loop · **name a residual with its MECHANISM** (147's Saturday),
not its symptom ("R-58 partly done") · **`set -u` + `local a=$1 b=$a` is an unbound variable** — the
first battery run died on line 9 and reported nothing; a battery that prints no verdict has run no
mutant.

**Baselines to attribute against: full suite and `-m parity` figures: in the follow-up docs-only commit (5,546 / 170 collected). Version 1.0.269; highest ADR 0503; schema 2.15.0.**

**R-57 is CLOSED — ADR-0502 (#691, `main` @ `2c549d8d`). A BOOKING's own `Assignment/LevelingDelay`
is honoured on that leg alone, on ADR-0474 / ADR-0501's TYPE AXIS — do not re-derive it and do not
"fix" the absorb half.** A leg with its OWN span (`FIXED_UNITS`, ratio < 1) is PUSHED by its delay; a
leg that SPANS THE TASK (ratio 1.0) ABSORBS it (on 16 of the 18 absorbing bookings the file's own
`Assignment/Finish` IS its `Task/Finish`). The row's literal remedy cost `Large_Test_File` 93 of its
1,666 finishes-within-a-day before the census refuted it. Population 24 delayed bookings on 17 tasks
across 6 goldens, 6 push (all Hard_File) / 18 absorb (all Large_Test_File). Working minutes of the
leg's own calendar; NEAREST minute (the task-level reader still TRUNCATES `// 10` — named in
ADR-0502, never measured; measure before changing it); part of the leg's dedup identity; never on a
MATERIAL / COST booking; does NOT move the task's start (a task whose bookings are ALL delayed has NO
witness in the corpus — UNVERIFIED). Disclosed on `assignment_leveling_driven` only when the delayed
leg PLACES the finish. **R-66** (registered, open): on the base `Hard_File` UID 381 finishes a full
working day early (08-20 11:59 vs 08-21 11:59), 396 inherits it, 398 lands early by exactly 240
working minutes — the reason R-57's oracle is met on `updated` and not on the base; the defect is
upstream of leveling.

**R-61 is CLOSED — ADR-0500 (refuted) and SETTLED — ADR-0501 (the 29 `.mpp` files).** ADR-0474's type
rule stands: a non-`FIXED_UNITS` leg spans ratio 1.0 × the effective duration on its leg calendar, and
a WORK booking's recorded window is never read (ADR-0487). Generalized, "the window is the rule" is
refuted 315-to-0 on the goldens; over the `.mpp` corpus 369 of 483 candidate legs are byte-identical
and the rest differ by 1–28 minutes (**R-65**, the gap-arithmetic granularity residual). ADR-0500's
refutation witness (UID 5231, recorded-complete) was invalid and is corrected; the corpus's one decisive
case (File2 UID 5263, started) is exact through `date_driven`. A sixth row in the census test is the
signal to re-read both ADRs.

## R-47 is CLOSED (ADR-0495). The population is Fuse's Record Count — do not re-gate it on a baseline.

The Detailed Metric Report's per-activity SPI(t) column is EMPTY on every activity row; it carries the
total and a **Record Count (717 / 726)**, and the engine's sum of ratios over that count reproduces
8.22 / 8.14 exactly. Every started activity with a non-zero actual span is admitted; an unbaselined one
scores 0. **Held (operator-owned):** the VALUE of a completed-unbaselined term — only a Fuse run on a
small file with a completed, never-baselined activity would discriminate it. Do not build on either
assumption.

## R-46 is CLOSED (ADR-0492). BCWS is the file's own series — do not re-derive it.

The Bible's `PV (BCWS) = sum(BCWSPV)` is each activity's BCWS as MS Project stores it (the assignment
baseline-cost series, `TimephasedData` Type 5, `Assignment.baseline_cost_pieces`, SCHEMA 2.14.0);
`evm._planned_value` sums a task's series through the status date and prorates a block the status date
falls inside in working minutes of the booking's calendar — **`cpm.booking_calendar`, which since
ADR-0503 returns the same INTERSECTION object the plan builder's leg runs on**. The three Hard_File
ribbons are exact (16,000 / 64,240 / 110,440). R-45 (updated3's BAC / BCWP / ACWP) stays open.

## R-60 is CLOSED (ADR-0491). Read the ADR before touching a leg, a golden or the converter.

The vendored converter writes MSPDI `TimephasedData` on every ingest; a WORK booking's zero-work blocks
bound its `work_pieces`; the engine's `_Leg` carries `gaps` and honours, in WORKING minutes of the leg's
calendar forward and backward, every gap **no other WORK booking of the task works through**. Every
MSPDI golden except EVM1/2 was regenerated from ITS OWN save by
`tools/regenerate_timephased_goldens.py` — `tests/fixtures/golden/PROVENANCE.json` names each save,
pinned by `tests/guards/test_golden_provenance.py`. Regenerate a golden ONLY through that tool.

**Environment, re-measured 2026-09-17: run the full sweep with `-v`, never `-q`.** This container has
NO pytest-timeout, so a stalled test never becomes a failure; the hang signal is no new results while
the load average is ~0. Expect **7 skips** locally: the urlparse pair, three INCIDENTAL_SVG axis cases,
and the two `test_pptx_libreoffice_interop` skips that are CORRECT here (no libreoffice-impress; CI
installs it and treats a skip as a FAILURE). The clone arrives SHALLOW — `git fetch --unshallow origin`
FIRST (~60 s). Install with `uv pip install --python /usr/local/bin/python3 --system -e '.[dev]' build
playwright` (never `playwright install`); re-`uv pip install -e .` after a version bump.
`/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff` **0.16.8** on PATH — run both. Keep the
token-guardian's `token_audit.py` in the SCRATCHPAD (`ruff check .` is whole-tree). A `.pth` editable
install lets `PYTHONPATH` shadow the package for a mutation battery — assert the imported module IS the
copy every time (a `-p mutcheck` plugin does it) — and the same trick runs the working tree's tests
against a pristine worktree's `src/` for the red-first proof. Take the pristine baseline in a SEPARATE
WORKTREE (`git worktree add <scratch> origin/main`), never by mutating the tree under measurement. The
29 `.mpp` files convert with `java -Xmx1g -cp 'tools/mpxj/classes:tools/mpxj/lib/*' MpxjToMspdi <in>
<out>` (~15 min for all; assert the artefact exists; give `Large Test File.mpp` and
`Large_Test_File.mpp` DIFFERENT output names). The wheel must be built AFTER the last `ruff format`
(the lockstep pin).

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt.

## The next §3 unit is R-59.

**R-59** (T3, S) — `off_project_calendars` and the `/analysis` calendar disclosure name TASK calendars
only; the crews' calendars the CPM honours since ADR-0474 — and, since ADR-0503, the derived
intersection a task calendar meets a crew calendar on — are undisclosed on the page, so the analyst
reads "single calendar" under a multi-calendar result. First executable step: list the crew calendars a
plan uses beside the task calendars (uid-deduplicated; a derived intersection carries uid −2 and both
names, e.g. `Standard+Sat. ∩ Customer Service Team`, and must be named as such, never as either parent)
and pin the `/analysis` sentence on Hard_File — RENDER it (`render-verify`), in all four themes. The
oracle is the sentence on the page. It is a `web/` change: the design system's DoD applies, and it
must not touch `engine/`. Read `engine/cpm.py`'s `off_project_calendars`, `_plan_shapes` and
`execution_calendar_of` and ADR-0474 / 0503 before writing a line.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481 (OR-11e) ·
ADR-0482 (OR-12) · ADR-0483 (OR-13) · ADR-0484 (/scorecards) · ADR-0485 (OR-14) · ADR-0486 (OR-15) ·
ADR-0487 (R-56) · ADR-0488 (OR-16 / OR-16b) · ADR-0489 (/margin) · ADR-0490 (R-49) · ADR-0491 (R-60) ·
ADR-0492 (R-46) · ADR-0493 (OR-17 in part) · ADR-0494 (OR-18) · ADR-0495 (R-47) · ADR-0496 (OR-19) ·
ADR-0497 (OR-20) · ADR-0498 (R-52) · ADR-0499 (R-50) · ADR-0500 (R-61 refuted) · ADR-0501 (R-61
settled on the `.mpp` corpus) · ADR-0502 (R-57, v1.0.268) · **ADR-0503 (R-58 CLOSED — the
intersection; the witness corrected to UID 94; v1.0.269; this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away
census across EVERY golden AND the 29 `.mpp` files before the ADR → mutation proofs by name → the full
gate → an ADR → the state docs → a draft PR): **R-59** (above) · **R-64** (Hard_File milestone 387
hangs on an external predecessor, UID −65535) · **R-63** (the converter resolves `CurrentDate`,
`MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time) · **R-62** (every absent slack the
writer dropped is a zero, completed tasks included) · **R-65** (the 1–28-minute gap granularity) ·
**R-66** (UID 381's day on the base snapshot) · **R-67** (147's Saturday late start on the elapsed
axis — 157's late finish and 94's float) · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 ·
R-22 · R-32 · R-39. The design queue is 19 artboards — the operator's order picks the next screen.
⇢ Traps paid for, by name (2026-09-17 first): **a row's WITNESS is testimony too** — one XML dump
settles which activity a row is about · **a five-value oracle beats a finish** · **the rig can be
wrong twice before the engine is** — recompute every expectation from the rig's own numbers · **a
survivor that is not dead code is a missing pin** and its case is the finding · **count the artefacts
of every sweep** (28 ≠ 29) · **name a residual with its mechanism** · **a battery that prints no
verdict has run no mutant** (`set -u` + `local a=$1 b=$a`). (2026-09-16 (d):) **an audit row's REMEDY
is testimony too** — price it against the whole population before writing a line (R-57: right for 6 of
24, a regression for 18) · **a SURVIVOR is worth more than the cuts that go red** (M6, the backward
pass, three exact stored slacks) · **a line that cannot fire must be DELETED**, and "the corpus is
byte-identical without it" is weak when the corpus never reaches the line · **a disclosure that
over-claims is worse than none** · **`ruff format` after the wheel build breaks the lockstep pin**.
(2026-09-16 (c):) **a residual must name the POPULATION it was measured against** · **a completed task
cannot adjudicate a scheduling rule** · **print the PLAN, sorted, with every leg's finish** before
believing a diagnosis about one leg · **an instrument that cannot detect its own failure reports a
confident zero** (pair by index, assert the pair count) · **a non-mutation is not a survivor** (a stub
inserted before the real definition loses the name). (Earlier, still live:) **a register row can be
RIGHT about the arithmetic and WRONG about the mechanism** · **run the census before pricing the fix**
· **proving a patch inert requires proving it FIRED** · **test a vendor-rule claim at the vendor's
scale** · **a parallel implementation in a test is an oracle for itself** · **an additive change to a
metric catalog is NOT additive to the guards** (R-50: four full-suite reds no targeted run saw) · **an
error message is a statement by the INSTRUMENT** · **a converter that exits 0 on refusal** — assert
the artefact exists · **prove a CI fragment under the CI shell** · **a gate that can SKIP silently
measures nothing** · **a model's memo about its own error is testimony** · **rebuild the wheel after
the LAST edit** · **a verdict quoted on the page is evidence** · **"replaced" for an identical paste is
a false statement of change** · **a register's step can name a column that is EMPTY** · **pin the
population from the reference tool's own count** · **the branch you stack on can move — and MERGE —
under you** · **a figure with no test behind it is testimony however many ADRs repeat it** · **a number
written mid-session is not a measurement** · **provenance is a diff, not a report** · **the rig can be
wrong before the engine is** · **`git log -1 -- tools/mpxj` changes when the converter changes** · a
fixed bug is evidence against the hypothesis it lived under · negative pins are green on the pristine
tree by construction; prove them with a mutant · read every green in a battery as a finding about the
instrument · MS Project's stored dates are a per-activity CPM oracle · `LevelingDelay` is tenths of a
minute · MPXJ writes no zero · `Large_Test_File.mpp` ≠ `Large Test File.mpp`.
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0503:) intersecting a MATERIAL / COST leg
(no calendar to intersect with; ADR-0487's window rule stands) · re-anchoring the slack axis on the
intersection (refuted by UID 94's own 6,360 / 2,190) · a `CPMResult` disclosure for the intersection (a
calendar rule, not a stored input) · registering the derived calendar in `Schedule.calendars` (derived
data) · intersecting a crew that names NO calendar (unknown ≠ the project's) · (ADR-0502:) pushing an
absorbing leg's delay (93 finishes-within-a-day) · a post-delay snap in `_leg_finish` (31,479-combination
sweep: inert) · (ADR-0500/0501:) "a fixed-duration leg spans the task's window" (315-to-0) · a
fixed-duration leg on the task's axis (0 toward / 5 away) · (ADR-0498:) the exported `.pptx` as a
malformed package · (ADR-0496:) the tool's gateway key path as the cause of the 401 · (ADR-0495:)
re-gating the SPI(t) population on a baseline · (ADR-0492:) re-deriving BCWS on the crew calendar ·
(ADR-0491:) an ELAPSED reading of a split gap · dropping the baseline timephased series from the
converter · a task-level `<Splits>` model field · regenerating a golden from the intake path's CURRENT
bytes · the KPI-tile selector on /margin (ADR-0489) · a quantity-or-rate rule for material / cost spans
(ADR-0487) · a data-date floor (refuted twice) · the DCMA08 baseline basis (R-48) · Fuse's
ACWP-to-time-now and updated3's BAC (R-45) · R-20 / UI-03 (ADR-0477) · the HELD and CLOSED rows of the
report.
⇢ Residuals registered, none taken: **R-67** (above) · **R-66** · **R-65** · the task-level
`LevelingDelay` reader's truncation (`// 10`; measure before changing) · the all-bookings-delayed task
start (no witness; UNVERIFIED) · `test_driving_path_whole_schedule_browser.py:104` is WIDTH-RACY (#667;
never fix it by widening a wait) · `/settings` scrolls sideways (an over-wide `<select>`) · UID 5306's
chain on the leveled SSI golden (a 2:36 daily gap read as 2) · ADR-0489's own (the KPI selector; the
callout collapsed; two charts at 569 px) · ADR-0488's · ADR-0486's · ADR-0485's · ADR-0483's · OR-11b ·
OR-11d · the working-minute axis · the hint bubble · ADR-0484's in-grid rows ·
`Hard_File_updated_with_logic_reestablished`'s negative float chain (−7,440 vs a stored 0; not a golden,
no row).
⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); EIGHT
checks when `installer/**` changes (this PR does), SIX for docs-only; `pull_request_read` `get_status`
returns `pending / 0` on a fully green PR (the legacy API) — use `get_check_runs`; a
`check_suite.completed` event can carry a superseded `head_sha` — re-read the current head; a red cell
on `main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER `git log
origin/main..HEAD`; after a squash-merge restart the branch with `git fetch --prune origin && git remote
set-head origin -a && git checkout -B <branch> origin/main`, never amend or rebase the squash commit.
Review cover is still absent — Codex quota EXHAUSTED; the mutation batteries and the full gate are all
this repo gets.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md`
FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the roadmap by testimony tier,
pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every session (ADR-0393). `git fetch
origin` before you branch, number an ADR, or commit.
