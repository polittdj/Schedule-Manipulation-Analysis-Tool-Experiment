# Kickoff prompt — next session

**`main` @ `3db94b14` (#694, R-59 / ADR-0504, v1.0.270) — its OWN CI was read TO CONCLUSION: run 1915 (`35254782501`) SUCCESS, all six jobs (`cui-guard` 17:46:59Z · `browser` 18:04:08Z · `floor` 18:12:51Z · `test (3.13)` 18:31:26Z · `test (3.11)` 18:33:52Z · `check` 18:33:58Z), and installer-smoke 753 (`35254782608`) SUCCESS 17:51:32Z. Nothing about `3db94b14` is outstanding. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one.**

**R-64 is CLOSED — ADR-0505, draft PR [#695](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/695) (the OPERATOR merges; if it is merged when you arrive, `main` has moved past `3db94b14` — read ITS own six jobs AND its installer-smoke run to conclusion, since the diff touches `installer/**`, and expect EIGHT checks on the PR; a red cell on a tree identical to the green PR head is the RUNNER's claim — compare tree hashes before believing it; do NOT open a docs-only PR to record the merge). R-66 is CLOSED with it. The row's MECHANISM was refuted before a line changed — "milestone 387 hangs on `PredecessorUID` −65535" — by 387's own XML (its one link is UID 386) and by a census of every link in the 44 corpus files (11,979 across the 15 goldens, 21,609 across the 29 fresh `.mpp` conversions: ZERO unresolvable, cross-project, external or negative-UID links); −65535 is the `ResourceUID` of MS Project's unassigned-work placeholder on the milestone's own assignment. The day was lost at milestone **181**, fifteen links above 404: a project-axis zero-duration task driven by a 16-hour crew that finished at Tuesday 08:00 kept only the integer minute, which the axis renders as Monday 17:00, and the crew successor 189 was started there. **A zero-duration project-axis task now carries its driving predecessor's wall instant** (`_carried_instant` in `engine/cpm.py`'s forward pass: the latest instant among its lag-0 link drivers, a raw constraint date, a manual stored start or a recorded actual start; carried only when some driver's instant is one the axis LOST; the integer offsets untouched; exposed on `TaskTiming.early_start_wall` / `early_finish_wall`, late walls `None`), and a wall-path successor starts from it. Do not re-derive it, do not "snap" a milestone to its calendar (the corpus's own witnesses: updated2's 387 at 23:00, the 24-hour snapshot's 156 on a Sunday), and do not add the projection guard or the stored-floor candidate back (both proved inert / unreachable and were DELETED).**

**Measured:** Hard_File EVERY activity finishes on its stored instant (exact 40 → 110 of 110; stored slack exact 39 → 101; Critical 108 → 110); updated / updated2 / updated3 110 of 110 within a day; the 24-hour snapshot's project finish 11-17 01:00 → the stored 11-19 01:00 EXACT (its own oracle row now); Project2 / Project5 / EVM / the Large Test Files unmoved. Across the 44 files: 220 finishes toward the stored instant, 41 away — two named mechanisms, neither the rule's (the two lunch-hour milestones 168 / 7107 and their copies; one chain below the out-of-sequence UID 187 in the non-golden `logic_reestablished` file). The `/analysis` page on Hard_File differs in its two float panels only; `/api/analysis` in 65 rows' float figures; Project5 and Large_Test_File byte-identical on every surface.

**Baselines to attribute against: full suite 5,572 green / 0 failed / 7 skipped on the final tree (measured 5,571 / 1 / 7 at the code commit `ae8ee1de` in a separate worktree, the 1 being the version-pin guard fixed by the docs commit; 5,579 collected = 5,561 + 17 + 1); `-m parity` 171 / 0 (170 + the oracle's 24-hour row). Version 1.0.271; highest ADR 0505; schema 2.15.0.**

**R-59 is CLOSED — ADR-0504 (#694, `main` @ `3db94b14`).** The `/analysis` Working-calendar panel names EVERY calendar the base pass runs on, read off the engine's own execution plans: `plan_calendars(schedule) -> PlanCalendars` in `engine/cpm.py` beside `off_project_calendars` — `axes` / `legs` / `elapsed` / `population`; dedup by object, registered first by uid, derived after by name. Do not re-derive it, and do not "widen" `off_project_calendars` (structurally blind to a crew's calendar; kept as public API only).

**R-58 is CLOSED — ADR-0503 (#693).** A task calendar meets a crew calendar on their INTERSECTION (`_calendar_intersection` behind `_task_shape` and `booking_calendar`); the slack axis stays the TASK calendar (ADR-0474). **R-57 is CLOSED — ADR-0502 (#691):** a BOOKING's own `Assignment/LevelingDelay` is honoured on that leg alone, on the TYPE AXIS (a leg with its OWN span is PUSHED, a leg that SPANS THE TASK ABSORBS). **R-61 CLOSED / SETTLED — ADR-0500 / ADR-0501.** R-47 CLOSED (ADR-0495). R-46 CLOSED (ADR-0492). R-60 CLOSED (ADR-0491): regenerate a golden ONLY through `tools/regenerate_timephased_goldens.py`.

**Environment, re-measured 2026-09-17 (c): run the full sweep with `-v`, never `-q`.** This container
has NO pytest-timeout, so a stalled test never becomes a failure; the hang signal is no new results
while the load average is ~0. Expect **7 skips** locally: the urlparse pair, three INCIDENTAL_SVG
axis cases, and the two `test_pptx_libreoffice_interop` skips that are CORRECT here (no
libreoffice-impress; CI installs it and treats a skip as a FAILURE). The clone arrives SHALLOW —
`git fetch --unshallow origin` FIRST (~60 s). Install with `uv pip install --python
/usr/local/bin/python3 --system -e '.[dev]' build playwright` (never `playwright install`);
re-`uv pip install -e .` after a version bump. `/root/.local/bin/ruff` 0.15.8 shadows CI's
`/usr/local/bin/ruff` **0.16.8** on PATH — run both. Keep the token-guardian's `token_audit.py` in
the SCRATCHPAD (`ruff check .` is whole-tree). A `.pth` editable install lets `PYTHONPATH` shadow the
package for a mutation battery — assert the imported module IS the copy every time (a `-p mutcheck`
plugin does it) — and the same trick runs the working tree's tests against a pristine worktree's
`src/` for the red-first proof. Take the pristine baseline in a SEPARATE WORKTREE (`git worktree
add <scratch> origin/main`), never by mutating the tree under measurement; **run the full suite in a
worktree at the CODE commit while the docs are written in the working tree** (with `PYTHONPATH` on
the worktree's `src/` and the plugin asserting it). **Sequence every test edit BEFORE the mutation
battery starts — a battery whose oracle is re-pinned mid-run is discarded** (paid for this session).
The wheel must be built AFTER the last `ruff format` (the lockstep pin). Four-theme screenshots:
serve with uvicorn on a free loopback port, `chrome_kwargs()` from `tests/web/browser_chrome.py`, set
`data-theme` on the root. The 29 intake `.mpp` files convert in ~70 s total with the vendored MPXJ
(`java -cp tools/mpxj/classes:"tools/mpxj/lib/*" MpxjToMspdi <in> <out>`, into the scratchpad).

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt.

## The next §3 unit is R-63.

**R-63** (T3, S) — the vendored converter's output depends on the CONVERSION date, not only the save:
`CurrentDate`, and a resource's `MaxUnits` / `OverAllocated` / `AvailableFrom` / `AvailableTo` /
`StandardRate` / `OvertimeRate` resolve at "now" from the availability and cost-rate tables (measured
2026-09-14: the same Hard_File_updated3 save converted 07-09 and 09-14 differs on exactly those 32
lines; `MaxUnits` feeds the resource-loading view's capacity) — two operators converting one file a
month apart get different loading figures (ADR-0491). First executable step: write the availability
and cost-rate tables themselves (MSPDI `AvailabilityPeriods` / `Rates`) and have the importer resolve
capacity at the STATUS date; red-first on a resource whose availability changes across the schedule.
Oracle: the loading view's capacity independent of the conversion date. **Before pricing it:** convert
the same save on two fabricated "now"s (the JVM's clock can be faked with `-Duser.timezone`-style
options only for the zone — read `MpxjToMspdi.java` and MPXJ's availability resolution first; the
kickoff's claim that the tables can simply be written is TESTIMONY), census which of the 29 `.mpp`
files carry a non-trivial availability or rate table at all, and read every consumer of `MaxUnits` in
`engine/` and `web/` (the loading view, the SRA?) before writing a line. The R-64 lesson applies:
walk from the observed difference to its first cause in the converter's own output.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481 (OR-11e) ·
ADR-0482 (OR-12) · ADR-0483 (OR-13) · ADR-0484 (/scorecards) · ADR-0485 (OR-14) · ADR-0486 (OR-15) ·
ADR-0487 (R-56) · ADR-0488 (OR-16 / OR-16b) · ADR-0489 (/margin) · ADR-0490 (R-49) · ADR-0491 (R-60) ·
ADR-0492 (R-46) · ADR-0493 (OR-17 in part) · ADR-0494 (OR-18) · ADR-0495 (R-47) · ADR-0496 (OR-19) ·
ADR-0497 (OR-20) · ADR-0498 (R-52) · ADR-0499 (R-50) · ADR-0500 (R-61 refuted) · ADR-0501 (R-61
settled on the `.mpp` corpus) · ADR-0502 (R-57, v1.0.268) · ADR-0503 (R-58, v1.0.269) · ADR-0504
(R-59, v1.0.270) · **ADR-0505 (R-64 CLOSED with its mechanism corrected, R-66 CLOSED with it — the
carried milestone instant; v1.0.271; this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away
census across EVERY golden AND the 29 `.mpp` files before the ADR → mutation proofs by name → the full
gate → an ADR → the state docs → a draft PR): **R-63** (above) · **R-62** (every absent slack the
writer dropped is a zero, completed tasks included) · **R-65** (the 1–28-minute gap granularity) ·
**R-67** (147's Saturday late start on the elapsed axis — now with its mechanism CONFIRMED as
ADR-0505's backward mirror: a milestone's LATE instant from a wall-path successor's late-start need;
witnesses 147's 08-01 13:00, the 24-hour snapshot's 156 (stored LF 11-02 09:00 vs 17:00, −4,740 vs
−4,320), 94's 6,510 vs 6,360, 404's 9,420 vs 9,480) · **R-45** · then R-03 · R-04 · R-09 · R-13 ·
R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards — the operator's order picks the
next screen.
⇢ Traps paid for, by name (2026-09-17 (c) first): **a number that appears in the file is not
evidence of the mechanism it is attached to — the ELEMENT it sits in is** (−65535 was a
`ResourceUID`, not a `PredecessorUID`) · **walk the engine's own network to the FIRST disagreement;
never trust the row's head** (387 was nine links below it) · **a lost wall instant is a class,
not a file** (R-66 was R-64's class — close both, say so in both) · **a test that cannot fail on the
pristine tree is a control: label it or rebuild it** (free float on a crew task's Standard axis) ·
**never edit an instrument a measurement is using** — a battery whose oracle moved mid-run is
discarded, not read · **a guard that cannot change an outcome is dead code** — delete it and record
the invariant · **name every AWAY mover's mechanism before the ADR** (the lunch-hour milestones, the
out-of-sequence 187) · **a milestone sits at the driving instant, UNSNAPPED — from the corpus's own
stored instants, never from belief about MS Project**.
(2026-09-17 (b):) **an over-claimed LIMITATION is as false as an over-claimed rule** · **read the
plans, not the inputs to the plans** · **a derivation from the engine's own maps owes the population
filter explicitly** · **probe the pristine tree before writing what the red run "would show"** ·
**write the seam tension down** · **the version bump and the handoff's version pin ride ONE push**.
(2026-09-17:) **a row's WITNESS is testimony too** · **a five-value oracle beats a finish** · **the
rig can be wrong twice before the engine is** · **a survivor that is not dead code is a missing
pin** · **count the artefacts of every sweep** (28 ≠ 29) · **name a residual with its mechanism** ·
**a battery that prints no verdict has run no mutant**. (2026-09-16 (d):) **an audit row's REMEDY
is testimony too** · **a SURVIVOR is worth more than the cuts that go red** · **a line that cannot
fire must be DELETED** · **a disclosure that over-claims is worse than none** · **`ruff format`
after the wheel build breaks the lockstep pin**. (2026-09-16 (c):) **a residual must name the
POPULATION it was measured against** · **a completed task cannot adjudicate a scheduling rule** ·
**print the PLAN, sorted, with every leg's finish** · **an instrument that cannot detect its own
failure reports a confident zero** · **a non-mutation is not a survivor**. (Earlier, still live:)
**a register row can be RIGHT about the arithmetic and WRONG about the mechanism** · **run the
census before pricing the fix** · **proving a patch inert requires proving it FIRED** · **test a
vendor-rule claim at the vendor's scale** · **a parallel implementation in a test is an oracle for
itself** · **an additive change to a metric catalog is NOT additive to the guards** · **an error
message is a statement by the INSTRUMENT** · **a converter that exits 0 on refusal** — assert the
artefact exists · **prove a CI fragment under the CI shell** · **a gate that can SKIP silently
measures nothing** · **a model's memo about its own error is testimony** · **rebuild the wheel after
the LAST edit** · **a verdict quoted on the page is evidence** · **"replaced" for an identical paste
is a false statement of change** · **a register's step can name a column that is EMPTY** · **pin the
population from the reference tool's own count** · **the branch you stack on can move — and MERGE —
under you** · **a figure with no test behind it is testimony however many ADRs repeat it** · **a
number written mid-session is not a measurement** · **provenance is a diff, not a report** ·
**`git log -1 -- tools/mpxj` changes when the converter changes** · a fixed bug is evidence against
the hypothesis it lived under · negative pins are green on the pristine tree by construction; prove
them with a mutant · read every green in a battery as a finding about the instrument · MS Project's
stored dates are a per-activity CPM oracle · `LevelingDelay` is tenths of a minute · MPXJ writes no
zero · `Large_Test_File.mpp` ≠ `Large Test File.mpp`.
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0505:) the BACKWARD carry (a
milestone's late instant — R-67's, with its own witnesses) · a completed milestone's recorded instant
on a single-calendar file (the two-ruler lunch hour: a 14:24 milestone renders 15:24; the carry needs
an instant the axis LOST so single-calendar files stay byte-identical) · a lagged driver's instant (a
lag lives on the integer axis) · `late_*_wall` on a carried milestone · the projection guard and the
stored-floor candidate (inert / unreachable — deleted) · EVM2's UID 25 finish (stored a day after its
start; not the row's) · (ADR-0504:) a per-booking `booking_calendar` listing as the disclosure's
source · widening `off_project_calendars` · re-implementing the plan builder's filters in `web/` ·
importing `_plan_shapes` into `web/` · the elapsed clock as a calendar line · a `calendar_basis` on
`/api/analysis` · a calendar table on the panel · (ADR-0503:) intersecting a MATERIAL / COST leg ·
re-anchoring the slack axis on the intersection · a `CPMResult` disclosure for the intersection ·
registering the derived calendar in `Schedule.calendars` · intersecting a crew that names NO
calendar · (ADR-0502:) pushing an absorbing leg's delay · a post-delay snap in `_leg_finish` ·
(ADR-0500/0501:) "a fixed-duration leg spans the task's window" (315-to-0) · a fixed-duration leg on
the task's axis · (ADR-0498:) the exported `.pptx` as a malformed package · (ADR-0496:) the tool's
gateway key path as the cause of the 401 · (ADR-0495:) re-gating the SPI(t) population on a
baseline · (ADR-0492:) re-deriving BCWS on the crew calendar · (ADR-0491:) an ELAPSED reading of a
split gap · dropping the baseline timephased series from the converter · a task-level `<Splits>`
model field · regenerating a golden from the intake path's CURRENT bytes · the KPI-tile selector on
/margin (ADR-0489) · a quantity-or-rate rule for material / cost spans (ADR-0487) · a data-date
floor (refuted twice) · the DCMA08 baseline basis (R-48) · Fuse's ACWP-to-time-now and updated3's
BAC (R-45) · R-20 / UI-03 (ADR-0477) · the HELD and CLOSED rows of the report.
⇢ Residuals registered, none taken: **R-67** (the backward mirror, above) · **R-65** · **the two
lunch-hour milestones** (LTF2's 168 and Leveled's 7107 now sit on their predecessor's finish; the
predecessors themselves ~20 h / ~70 h early for reasons of their own) · **404's slack 9,420 vs 9,480**
(R-67's family) · **`Hard_File_updated_with_logic_reestablished`'s UID 187** (60 % complete, started
out of sequence before its predecessor's stored finish — ADR-0391's floor keeps the logic start; 34
successors ride it; not a golden, no row) and its negative float chain (−7,440 vs a stored 0) · the
`24Hour Calendar` intake file (23 of 126 exact, unmoved; no row) · **the daylight telemetry HUD**
(the fixed CPU / RAM / GPU / DISK widget overlays the right edge of every full-width panel at 1440 px
in daylight — pre-existing chrome, no row; the operator's call) · the task-level `LevelingDelay`
reader's truncation (`// 10`; measure before changing) · the all-bookings-delayed task start (no
witness; UNVERIFIED) · `test_driving_path_whole_schedule_browser.py:104` is WIDTH-RACY (#667; never
fix it by widening a wait) · `/settings` scrolls sideways (an over-wide `<select>`) · UID 5306's
chain on the leveled SSI golden (a 2:36 daily gap read as 2) · ADR-0489's own (the KPI selector; the
callout collapsed; two charts at 569 px) · ADR-0488's · ADR-0486's · ADR-0485's · ADR-0483's ·
OR-11b · OR-11d · the working-minute axis · the hint bubble · ADR-0484's in-grid rows.
⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve);
EIGHT checks when `installer/**` changes (this PR does), SIX for docs-only; `pull_request_read`
`get_status` returns `pending / 0` on a fully green PR (the legacy API) — use `get_check_runs`; a
`check_suite.completed` event can carry a superseded `head_sha` — re-read the current head; a red
cell on `main` for a tree identical to the green PR head is the runner's claim — compare tree hashes
first; the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER `git log
origin/main..HEAD`; after a squash-merge restart the branch with `git fetch --prune origin && git
remote set-head origin -a && git checkout -B <branch> origin/main`, never amend or rebase the squash
commit. `actions_list` with a branch filter can return a stale page for a workflow — filter by the
workflow file (`ci.yml` / `installer-smoke.yml`) and check the `head_sha`; a run object's
`updated_at` can sit at its creation time while its jobs finish — read the JOBS. Review cover is
still absent — Codex quota EXHAUSTED; the mutation batteries and the full gate are all this repo gets.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md`
FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the roadmap by testimony tier,
pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every session (ADR-0393). `git fetch
origin` before you branch, number an ADR, or commit.
