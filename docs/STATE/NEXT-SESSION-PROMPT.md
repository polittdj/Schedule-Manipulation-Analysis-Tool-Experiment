# Kickoff prompt — next session

**`main` @ `778da99c` (#695, R-64 / ADR-0505, v1.0.271) — its OWN CI was read TO CONCLUSION: run 1917 (`35274461874`): `cui-guard` 21:03:37Z · `browser` 21:20:57Z · `floor` 21:26:19Z · `test (3.13)` 21:39:35Z · `test (3.11)` 21:51:47Z · `check` 21:51:52Z; installer-smoke 755 (`35274461873`) SUCCESS 21:07:52Z. Nothing about `778da99c` is outstanding. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one.**

**R-63 is CLOSED — ADR-0506, draft PR @@PR@@ (the OPERATOR merges; if it is merged when you arrive, `main` has moved past `778da99c` — read ITS own six jobs AND its installer-smoke run to conclusion, since the diff touches `installer/**`, and expect EIGHT checks on the PR; a red cell on a tree identical to the green PR head is the RUNNER's claim — compare tree hashes before believing it; do NOT open a docs-only PR to record the merge).** The row's mechanism was CONFIRMED at the bytecode — MPXJ 16.2.0 resolves `MaxUnits` (`getCurrentAvailabilityTableEntry` → `LocalDateTime.now()`), `AvailableFrom` / `AvailableTo`, `OverAllocated`, the rates (`getCurrentCostRateTableEntry(0)`) and `CurrentDate` at the JVM's clock, MS Project's own "current row of the Resource Availability grid" semantics mirrored — and **its first step was already the case**: the writer already writes `AvailabilityPeriods` and `Rates`. Measured with `faketime` (`tools/conversion_clock_probe.py`, committed): the updated3 golden's own blob under a faked 07-09 clock reproduces the committed golden to the second; 09-14 / 11-01 change 9 / 13 element pairs (ADR-0491's "32 lines" was the same 9 pairs in normal diff format); every task, assignment, calendar and table byte-identical. **The model carries the table (`Resource.availability` of `AvailabilityPeriod`, schema 2.16.0, the Save round trip); the MSPDI importer resolves `max_units` (the table) and `standard_rate` (cost-rate table A) at the STATUS date, else the project start, reading the scalar `<MaxUnits>` / `<StandardRate>` only for a resource with no table; ONE resolution rule (`value_in_effect`: the latest row begun by the instant, else the earliest — the containing-row check was dead code, its mutant SURVIVED, deleted; `available_to` is carried as data); the loading engine earns each working day's capacity from the row in force that day; the roster's Max units is the status-date row.** Do not re-derive it, do not read the scalars as a file's statement, and do not touch the converter for it.

**Measured, pristine → this tree, over 73 file entries (15 goldens + the 29 `.mpp` files at two clocks; 2,601 resource rows, 7,966 month buckets):** 230 tabled resources; 28 roster figures, 78 bucket capacities, 8 rates moved; 17 over-allocation flags CLEARED; the load never moved; the two clocks' conversions of one file import to different loadings for 3 of 29 files under the pristine importer and **0 of 29** under this one (the row's oracle). The four tabled goldens: Customer Service Team 1 → 2, Customer Service Lead 1 → 2, Technology Lead 0.5 → 1, Logistics 0.25 → 0.5 (a three-row table), the apprentice's rate 10 → 30. Rendered through the real app: only the twelve `/resources` renders differ (56 of 68 byte-identical).

**Baselines to attribute against:** @@GATE@@ Version 1.0.272; highest ADR 0506; schema 2.16.0.

**R-64 is CLOSED — ADR-0505 (#695, `main` @ `778da99c`); R-66 CLOSED with it.** A zero-duration project-axis task carries its driving predecessor's wall instant (`_carried_instant` in `engine/cpm.py`'s forward pass; exposed on `TaskTiming.early_start_wall` / `early_finish_wall`); do not re-derive it, do not "snap" a milestone to its calendar, and do not add the projection guard or the stored-floor candidate back. **R-59 CLOSED — ADR-0504** (`plan_calendars(schedule)` in `engine/cpm.py` names every calendar the base pass runs on; do not "widen" `off_project_calendars`). **R-58 CLOSED — ADR-0503** (a task calendar meets a crew calendar on their INTERSECTION; the slack axis stays the TASK calendar). **R-57 CLOSED — ADR-0502** (a BOOKING's own `LevelingDelay` on the TYPE AXIS). **R-61 CLOSED / SETTLED — ADR-0500 / 0501.** R-47 CLOSED (ADR-0495). R-46 CLOSED (ADR-0492). R-60 CLOSED (ADR-0491): regenerate a golden ONLY through `tools/regenerate_timephased_goldens.py`.

**Environment, re-measured 2026-09-17 (d): run the full sweep with `-v`, never `-q`.** This container
has NO pytest-timeout, so a stalled test never becomes a failure; the hang signal is no new results
while the load average is ~0 (the SRA Monte-Carlo oracles sit at one verdict for minutes at 86 % CPU —
that is not a stall). Expect **7 skips** locally: the urlparse pair, three INCIDENTAL_SVG axis cases,
and the two `test_pptx_libreoffice_interop` skips that are CORRECT here (no libreoffice-impress; CI
installs it and treats a skip as a FAILURE). The clone arrives SHALLOW — `git fetch --unshallow origin`
FIRST (~60 s). Install with `uv pip install --python /usr/local/bin/python3 --system -e '.[dev]' build
playwright` (never `playwright install`); re-`uv pip install -e . --no-deps` after a version bump.
`/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff` **0.16.8** on PATH — run both. Keep
the token-guardian's `token_audit.py` in the SCRATCHPAD (`ruff check .` is whole-tree). A `.pth`
editable install lets `PYTHONPATH` shadow the package for a mutation battery — assert the imported
module IS the copy every time (a `-p mutcheck` plugin does it) — and the same trick runs the working
tree's tests against a pristine worktree's `src/` for the red-first proof. Take the pristine baseline in
a SEPARATE WORKTREE (`git worktree add <scratch> origin/main`), never by mutating the tree under
measurement; **run the full suite in a worktree at the CODE commit while the docs are written in the
working tree** (with `PYTHONPATH` on the worktree's `src/` and the plugin asserting it) — and know that
such a worktree carries `main`'s OLD installers beside the new `src/`, so the four installer lockstep
pins are red there by construction and green on the final tree (rebuild, then run
`tests/installer/test_installers.py` in the working tree). **Sequence every test edit BEFORE the
mutation battery starts — a battery whose oracle is re-pinned mid-run is discarded**; read the stderr
of every battery row that is neither red nor green. The wheel must be built AFTER the last `src/` edit
and the last `ruff format` (the lockstep pin). `apt-get install faketime` works here; `faketime -f
"@YYYY-MM-DD hh:mm:ss"` (with `FAKETIME_DONT_FAKE_MONOTONIC=1`) moves the JVM's `LocalDateTime.now()`.
`bandit` B608 fires on an HTML f-string that contains `<select` and a later " from " — reword, do not
nosec. Set a shell variable on its own line, never inside a backgrounded `A && (B) &` list. Four-theme
screenshots: serve with uvicorn on a free loopback port, `chrome_kwargs()` from
`tests/web/browser_chrome.py`, set `data-theme` on the root. The 29 intake `.mpp` files convert in ~70 s
total with the vendored MPXJ (`java -cp tools/mpxj/classes:"tools/mpxj/lib/*" MpxjToMspdi <in> <out>`,
into the scratchpad).

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt.

## The next §3 unit is R-62.

**R-62** (T3, S) — every absent `TotalSlack` the MPXJ writer dropped is a zero, completed tasks
included (the ADR-0490 probe: NULL for none, 786 zeros in memory on Large Test File2, 634 of them
completed tasks); the importer infers only the `Critical` ones, so the Data Explorer's `Total Slack (d)`
reads `—` for a completed task where MS Project reads `0d` (ADR-0490). First executable step: widen the
inference to every absent slack when the file carries the element; census every metric that reads a
completed task's slack first (today none does). Oracle: the Data Explorer column equal to MS Project's;
`pytest -m parity` unmoved. **Before pricing it:** re-run ADR-0490's probe on the vendored jar (MPXJ's
`getTotalSlack` vs the writer's null-drop — the bytecode, not the ADR's memory of it); census the
completed tasks whose `<TotalSlack>` is absent across the 15 goldens AND the 29 `.mpp` conversions; read
every consumer of `stored_total_float_minutes` (the ribbon's Negative Float classifies the STORED slack
— ADR-0473 — and a widened inference could move it; `pytest -m parity unmoved` is the row's own pin);
and confirm the Data Explorer reads the stored field, not the engine's float, before writing a line.
The R-63 lesson applies: the row's first step may already be half true — measure the artefact first.

⇢ Traps paid for, by name (2026-09-17 (d) first): **a row's first step can already be TRUE — read the bytecode of the thing you are about to change** (`MSPDIWriter` already wrote the tables) · **fake the clock, don't reason about it** (`faketime` + `LD_PRELOAD` moves the JVM's `now()`; one save under three frozen clocks is a diff, not a memory) · **a number's provenance can be a stored field the getter ignores** (the `.mpp` stores MS Project's save-time `MaxUnits`; MPXJ recomputes it at the reader's clock) · **a surviving mutant is a hole in the CODE as often as in the tests** (the containing-row check was dead beside the latest-row-begun rule) · **a cut can be malformed and print no verdict — read every non-red row's stderr** · **write the corpus figure AFTER the census** (the FX rows do NOT contain every loaded day: 113 / 179 / 113 fall outside) · **a shell variable set inside a backgrounded list is unset in the foreground** (a false bandit red). (2026-09-17 (c):) **a number that appears in the file is not
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
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0506:) a converter change for R-63 (the tables are already written) · a zero-availability reading outside every row (R-68 — the operator's Resource Graph decides it) · the XER `RSRCRATE` rows onto the model (the XER scalar is already data-date resolved; no P6 witness) · rate tables B–E / `OvertimeRate` / `CostPerUse` / the formats · reading `OverAllocated` / `AvailableFrom` / `AvailableTo` / `CurrentDate` (the clock's) · regenerating the goldens' resource sections · a Java-gated CI test on the golden's blob (the checkout is shallow) · a "varies" roster marker · (ADR-0505:) the BACKWARD carry (a
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
⇢ Residuals registered, none taken: **R-68** (a day outside every availability row — ASK, question (f) in the report's §5: the three tampered `Project5_FX0x` saves book crews on 113 / 179 / 113 loaded days past their single bounded rows; the engine holds the latest row begun, the converter printed the default 1, MS Project's verdict unknown) · **R-67** (the backward mirror, above) · **R-65** · **the two
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
EIGHT checks when `installer/**` changes (this PR does), SIX for docs-only; `main`'s own run for a squash is read from its JOBS (the run object's `updated_at` sits at creation); `pull_request_read`
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
