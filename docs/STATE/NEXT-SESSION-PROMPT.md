# Kickoff prompt — next session

**`main` @ `b7c76ece` (#696, R-63 / ADR-0506, v1.0.272) — its OWN CI was read TO CONCLUSION on 2026-09-18: run 1920 (`35286496419`): `cui-guard` 23:22:13Z · `browser` 23:39:21Z · `floor` 23:47:23Z · `test (3.13)` 00:04:42Z · `test (3.11)` 00:10:22Z · `check` 00:10:27Z — six of six; installer-smoke 758 (`35286496424`): `linux` 23:22:37Z · `windows` 23:26:29Z. Nothing about `b7c76ece` is outstanding. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one.**

**R-62 is CLOSED — ADR-0507, draft PR [#697](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/697) (the OPERATOR merges; if it is merged when you arrive, `main` has moved past `b7c76ece` — read ITS own six jobs AND its installer-smoke run to conclusion, since the diff touches `installer/**`, and expect EIGHT checks on the PR; the `check` job is listed only once its `needs` complete — five jobs, then six; a red cell on a tree identical to the green PR head is the RUNNER's claim — compare tree hashes before believing it; do NOT open a docs-only PR to record the merge).** The mechanism was confirmed at the bytecode: the MPXJ writer's `printDurationInIntegerTenthsOfMinutes` returns null for a zero-valued duration, so a zero `TotalSlack` is never an element, whatever the task's class; MPXJ's Total Slack is a CALCULATED field — the MPP reader maps the file's `START_SLACK` / `FINISH_SLACK` and never a total, and `MicrosoftSlackCalculator` derives it by MS Project's documented rule (the smaller of the two; a started activity's finish slack). Measured cached-first over the 29 intake `.mpp` files (17,402 tasks): the element is absent for exactly the **7,095** tasks whose computed total is 0.0, NULL for none — 5,466 completed, 583 Critical incomplete, 1,046 summaries, **0 other**; 7,030 store the pair (0, 0), the 65 others one zero member; every finished activity stores (0, 0), carries an `ActualFinish`, carries no element. **The importer reads an absent slack as 0 whenever the FILE carries the element anywhere (ADR-0490's guard; its Critical bound retired). Float erosion by WBS — the ONE metric the census found reading finished work, on the engine's recomputed float — scores incomplete activities only and does not list a group with no remaining work. The stored-dates oracle's slack census excludes finished work (load-bearing: Project2 would read tf_n 126 for 106).** Two inherited numbers were wrong and are corrected in the report row: Large Test File2's 786 zeros are 724 completed (90 of them milestones) + 62 Critical, not "634 completed"; and "today none does" was one metric. Do not re-derive it, do not put finished work back into float erosion's population, do not read a completed activity's stored zero as a scheduling verdict.

**Measured, pristine → this tree:** 15 goldens' float erosion, 13 moved — 121 → 100 groups (21 held finished work only), red 35 → 27, amber 49 → 41 (the two 24-hour Hard_File snapshots' groups 4 / 5 read −9.6 / −7.9 wd RED on finished work and 14.6 / 93.3 wd green on the remaining); a sandboxed snapshot of 18 metric families × 15 goldens moved float erosion and nothing else; rendered through the real app (4 goldens × every GET route) 250 successful, 238 byte-identical, the movers `/analysis`, `/download` (the Save now carries the zeros) and `/api/whoami` (the pid). The Data Explorer — the drill grid's addable `Total Slack (d)` — reads `0` for Hard_File_updated3's 42 finished activities where the pristine app read `—`.

**Baselines to attribute against:** **full suite 5 failed / 5,613 passed / 7 skipped in 36:46** (00:04–00:41Z, `-v`, the package under test asserted by the plugin, no stall). The five failures are all attributable and none is the change's: the four installer lockstep pins (`test_embedded_wheel_decodes_byte_exact_with_static_assets[ps1 / sh / command]` and `test_embedded_wheel_is_in_lockstep_with_the_source_tree`) are red by construction in a worktree that carries `main`'s old installers beside the new `src/` — the final tree's rebuilt installers pass that module 68 / 68 — and `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version` is red on the code commit's unrotated handoff and green on the final tree (the docs commit carries the pin); the final tree differs from the measured one under `docs/` and `installer/` only — so the final tree reads **5,618 green / 0 failed / 7 skipped** and **`-m parity` **187 passed / 0 failed in 5:07****, measured in a separate worktree at the code commit `96e4a624`. Attributed: **5,625 collected = 5,616 + 9** (the new module's 6 + float erosion's 2 + the drill's 1); the previous unit's 5,609 green + 9 = 5,618; parity **187 = 187** (no new parity-marked test). The 7 skips are the documented set (the loopback-allowlist pair, the three INCIDENTAL_SVG axis cases, the two LibreOffice interop skips that are correct in this container). Version 1.0.273; highest ADR 0507; schema 2.16.0.

**R-63 is CLOSED — ADR-0506 (#696, `main` @ `b7c76ece`).** The model carries the availability table (`Resource.availability`, schema 2.16.0); the MSPDI importer resolves `max_units` and `standard_rate` at the STATUS date, else the project start, reading the scalar only for a resource with no table; ONE resolution rule (`value_in_effect`); the loading engine earns each working day's capacity from the row in force; the converter was not touched (it already writes the tables; its scalars are the JVM's clock — never read them as a file's statement). **R-64 / R-66 CLOSED — ADR-0505** (a zero-duration task carries its driving predecessor's wall instant; do not snap a milestone to its calendar). **R-59 CLOSED — ADR-0504. R-58 CLOSED — ADR-0503. R-57 CLOSED — ADR-0502. R-61 CLOSED / SETTLED — ADR-0500 / 0501.** R-47 (ADR-0495), R-46 (ADR-0492), R-60 (ADR-0491: regenerate a golden ONLY through `tools/regenerate_timephased_goldens.py`) closed.

**Environment, re-measured 2026-09-18: run the full sweep with `-v`, never `-q`; never pass `-o cache_dir=`
(pytest 9.1.1 exits 4 on the unknown option in thirteen seconds, and a `(…; echo) > log` wrapper reports
exit 0 — read the log's `PYTEST_EXIT` line, never the notification).** This container has NO
pytest-timeout, so a stalled test never becomes a failure; the hang signal is no new results while the
load average is ~0 (the SRA Monte-Carlo oracles sit at one verdict for minutes at ~100 % of one core —
that is not a stall). Expect **7 skips** locally: the urlparse pair, three INCIDENTAL_SVG axis cases, and
the two `test_pptx_libreoffice_interop` skips that are CORRECT here (CI installs LibreOffice and treats a
skip as a FAILURE). The clone arrives SHALLOW — `git fetch --unshallow origin` FIRST (~60 s), then
`git fetch --prune origin && git remote set-head origin -a`. Install with `uv pip install --python
/usr/local/bin/python3 --system -e '.[dev]' build playwright` (never `playwright install`); re-`uv pip
install -e . --no-deps` after a version bump (the installed metadata is what `/api/whoami` and the wheel
report). `/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff` **0.16.8** on PATH — run both.
Keep the token-guardian's `token_audit.py` in the SCRATCHPAD (`ruff check .` is whole-tree). A `.pth`
editable install lets `PYTHONPATH` shadow the package — assert the imported module IS the copy every
time (a `-p mutcheck` plugin: `MUTCHECK_ROOT` + `pytest_sessionstart`; it is NOT committed — write it
into the scratchpad) — and the same trick runs the working tree's tests against a pristine worktree's
`src/` for the red-first proof. Take the pristine baseline in a SEPARATE WORKTREE (`git worktree add
<scratch> origin/main`), never by mutating the tree under measurement; **run the full suite in a
worktree at the CODE commit while the docs are written in the working tree** — such a worktree carries
`main`'s OLD installers beside the new `src/`, so the four installer lockstep pins are red there by
construction and green on the final tree (rebuild, then run `tests/installer/test_installers.py` in the
working tree). **Sequence every test edit BEFORE the mutation battery starts**; read the stderr of every
battery row that is neither red nor green. The wheel must be built AFTER the last `src/` edit and the
last `ruff format`. A two-tree render diff lies until the version string (`1.0.NNN` in every page), the
launch token (`<meta name=sf-launch>` / `launch_token`, sixteen hex + `.0`), the pid in `/api/whoami`
and the live telemetry in `/api/system` are normalised or excluded — find each by diffing ONE page, not
by reasoning about the count. `javap -cp tools/mpxj/lib/mpxj-16.2.0.jar -p -c <class>` reads the
vendored bytecode; a Java probe compiles with `javac -cp "tools/mpxj/lib/*" --release 17`; read a
calculated field cached-first (`getCachedValue`) before any getter, and `getCritical()` is calculated too
(its cache is null). `support.microsoft.com` is blocked by the egress proxy — Microsoft's field
reference is reachable through the Microsoft Learn connector's fetch. `bandit` B608 fires on an HTML
f-string that contains `<select` and a later " from " — reword, do not nosec. Set a shell variable on
its own line, never inside a backgrounded `A && (B) &` list. Four-theme screenshots: serve with uvicorn
on a free loopback port, `chrome_kwargs()` from `tests/web/browser_chrome.py`, set `data-theme` on the
root. The 29 intake `.mpp` files convert in ~70 s total with the vendored MPXJ (`java -cp
tools/mpxj/classes:"tools/mpxj/lib/*" MpxjToMspdi <in> <out>`, into the scratchpad).

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt.

## The next §3 unit is R-65.

**R-65** (T2, S) — the engine's honoured leveling gaps (ADR-0491) land **1–28 minutes** short of the
window MS Project records for the same split booking — systematic and one-directional across ~100
bookings in the 29-file `.mpp` corpus (UID 5342 occupancy 2,757 vs window 2,758; UID 5316 9,329 vs
9,333; UID 5273 4,687 vs 4,688). Below the resolution of every parity pin and it moves no verdict, but
it is real and it was folklore until ADR-0501 measured it. First executable step: compare `_split_gaps`'
minute sum against the file's own recorded window on the ~100 split bookings where they differ; decide
whether the residual is rounding in `_recorded_span`, in the share→`after` conversion, or in MPXJ's
timephased block boundaries. Oracle: the recorded window of those bookings; `pytest -m parity`
unmoved. **Before pricing it:** re-count the population on fresh conversions of the 29 files (the "~100"
is a tilde — name the exact count per file, and whether the duplicated saves are counted once); read
`_split_gaps`, `_recorded_span` and the timephased reader in `importers/mspdi.py` before believing any
of the three named suspects; dump the converter's `<TimephasedData>` block boundaries (they carry
SECONDS) beside the engine's minute axis for the three witnesses and test whether the residual is the
sum of per-block sub-minute truncations (ADR-0502's "17 / 24 to the nearest minute, truncation 14"
class; R-57's seven sub-minute misses of 12–78 s) before touching a rounding; a fix that rounds without
a named mechanism is measured-false by construction. The R-63 and R-62 lessons apply: measure the
artefact before the row's first step, and the row's numbers are testimony.

⇢ Traps paid for, by name (2026-09-18 first): **a getter that answers 0.0 for "none" may be COMPUTING, not reading — the provenance of a calculated field is the reader's field map, read cached-first** · **count the class beside the one you were told about** (786 − 634 was 90 completed milestones, not 62) · **"no metric reads it" is falsified by running the metrics, not by reading them** (the sandboxed family snapshot found float erosion) · **a metric with a fallback basis reads the ENGINE where the source tool shows 0 — a red stoplight on finished work** · **a render diff lies until every per-process value is normalised** (version, launch token, pid, telemetry: 130 false movers, then 12 true ones) · **a wrapper that exits 0 around a pytest that exits 4 has measured nothing — read `PYTEST_EXIT`** · **a row's remedy can be right and its scope wrong** (the inference was one line; the census it demanded was the unit). (2026-09-17 (d):) **a row's first step can already be TRUE — read the bytecode of the thing you are about to change** (`MSPDIWriter` already wrote the tables) · **fake the clock, don't reason about it** (`faketime` + `LD_PRELOAD` moves the JVM's `now()`; one save under three frozen clocks is a diff, not a memory) · **a number's provenance can be a stored field the getter ignores** (the `.mpp` stores MS Project's save-time `MaxUnits`; MPXJ recomputes it at the reader's clock) · **a surviving mutant is a hole in the CODE as often as in the tests** (the containing-row check was dead beside the latest-row-begun rule) · **a cut can be malformed and print no verdict — read every non-red row's stderr** · **write the corpus figure AFTER the census** (the FX rows do NOT contain every loaded day: 113 / 179 / 113 fall outside) · **a shell variable set inside a backgrounded list is unset in the foreground** (a false bandit red). (2026-09-17 (c):) **a number that appears in the file is not
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
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0507:) letting the inferred zeros into float erosion's OLD population (measured: every group with a finished activity reads min 0 and goes amber — a fabricated warning; the population was fixed instead) · the XER importer's absent `total_float_hr_cnt` (no P6 witness for finished work) · a pre-1.0.273 Save's `None` for finished work (re-import the source) · a row for MPXJ's started-task branch (699 written elements are a started activity's finish slack; read verbatim, reproduced by the engine's own float on the stored-dates oracle) · re-deriving MS Project's Total Slack for a finished activity from anything but its stored (0, 0) pair · (ADR-0506:) a converter change for R-63 (the tables are already written) · a zero-availability reading outside every row (R-68 — the operator's Resource Graph decides it) · the XER `RSRCRATE` rows onto the model (the XER scalar is already data-date resolved; no P6 witness) · rate tables B–E / `OvertimeRate` / `CostPerUse` / the formats · reading `OverAllocated` / `AvailableFrom` / `AvailableTo` / `CurrentDate` (the clock's) · regenerating the goldens' resource sections · a Java-gated CI test on the golden's blob (the checkout is shallow) · a "varies" roster marker · (ADR-0505:) the BACKWARD carry (a
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
⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); the `check` job appears in a run's job list only once its `needs` complete (five jobs, then six — a five-job list is not a missing job);
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
