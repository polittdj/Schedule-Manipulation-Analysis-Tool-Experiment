# Kickoff prompt — next session

**`main` @ `bb5cef0d` (#698, R-65 / ADR-0508, v1.0.274) — its OWN CI was read TO CONCLUSION on 2026-09-18: run 1926 (`35345800081`): `cui-guard` 12:39:26Z · `browser` 12:56:58Z · `floor` 13:06:07Z · `test (3.13)` 13:23:42Z · `test (3.11)` 13:29:33Z · `check` 13:30:16Z — six of six; installer-smoke 764 (`35345800104`): `linux` 12:39:48Z · `windows` 12:43:48Z. Nothing about `bb5cef0d` is outstanding. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one — the 2026-09-18 (c) session's kickoff named R-52 / ADR-0497 as current while the committed handoff was eleven ADRs ahead.**

**R-67 is CLOSED — ADR-0510, a draft PR on branch `claude/affectionate-heisenberg-e70kzd` (its number is in the handoff's follow-up commit; the OPERATOR merges; if it is merged when you arrive, `main` has moved past `bb5cef0d` — read ITS own six jobs AND its installer-smoke run to conclusion, since the diff touches `installer/**`, and expect EIGHT checks on the PR; the `check` job is listed only once its `needs` complete — five jobs, then six; a red cell on a tree identical to the green PR head is the RUNNER's claim — compare tree hashes before believing it; do NOT open a docs-only PR to record the merge).** A fast-path zero-duration task now carries its LATE instant from the need that binds it — a wall-path successor's late start less its elapsed leveling delay, a carried milestone's instant, or (on a file with wall-path tasks) a binding deadline / date constraint or the backward target — the EARLIEST such instant; a wall-path predecessor retreats from it; a milestone whose EARLY instant is carried measures its slack between its two instants. Hard_File 147's stored LateStart is SATURDAY 08-01 13:00 (178's late start less 72 elapsed hours), 157 retreats from it onto Friday 23:00 / 15:00 / 2,760, 94 onto 07-31 15:00 / 07-30 22:00 / 6,360; on the 24-hour snapshot the chain head is milestone 155's DEADLINE with no successor at all, and 146 → 145 → 144 → 9 → 36 → 156 → 141 land on every stored late date and slack. **Do not re-derive it; do not gate the mirror on a successor (the deadline case refutes it); do not carry a lagged BINDING link's rendering; do not put a late wall on a single-calendar file.** The plan was attacked before the first edit (QC-3): two of four assumptions fell — the successor gate and the one-milestone class (155 of 2,210 zero-duration tasks across the 44 files sit outside working time).

**Measured, pristine → this tree:** late-finish instants exact Hard_File 78 → 94 of 110, updated 83 → 87, updated2 27 → 37, updated3 30 → 45, the 24-hour snapshot 3 → 15; stored slack exact 101 → 108, 101, 36 → 38, 46 → 48, 7 → 15 (404's 9,480); across the 44 files 268 late finishes toward the stored instant, 17 away — every one on a chain MS Project derives past a COMPLETED / STARTED successor the engine still runs through (R-70) or a completed milestone's record — 50 slacks gained, 0 lost; 18 files byte-identical on every timing field, every single-calendar file among them; Project2 / Project5 unmoved; the Large Test Files' finishes unmoved. Red first on the pristine package 10 synthetic + 7 oracle pins by name; battery 17 / 17 red by name on shadow copies after ONE survivor (the binding check) exposed two missing pins. **R-69** registered (a block-exact late start written at the block's END where MS Project writes the next block's START — 178: 12:00 for 13:00; 742 across the corpus; the 13:00 form would push the lunch hour into every project-calendar predecessor's float through the contiguous projection) and **R-70** registered (the backward pass through a completed / started successor: updated3's 188 stored 12-12 17:00 while its completed successor 291's late start is 09-08; 67 across the corpus, the engine follows the completed successor on 34).

**QC-3 is the third standing working rule — ADR-0509 (the same unit):** after the research and the plan, and before the first change, assume the plan is wrong, write down every load-bearing assumption, attack each with an executable check or an independent reading of the artifact, and prove the plan correct before making changes; record in the ADR which assumptions fell. Pinned by `tests/test_standing_rules.py` (QC-3 by ADR-0509; QC-1 / QC-2 by ADR-0393): 18 / 18 mutations red by name after one survivor (a bare "refute" token matched a bullet's "refuted" — pin the PHRASE). `CLAUDE.md`'s section is "The three non-negotiable working rules"; a doc line that names the guard and cites an ADR must cite the deciding ADR of every rule it names.

**Baselines to attribute against:** the full gate and `-m parity` for this unit were measured in a separate worktree at the code commit `da4f7e67` — their counts are in the handoff's STATUS section and the session log (the docs-only follow-up commit); the previous unit's baseline was 5,634 green / 0 failed / 7 skipped and parity 197. Expected red at the code commit by construction: the handoff's version pin and the two latest-ADR pins (the code commit carries ADR-0509 and the bump, not the rotated docs). This unit adds 14 synthetic pins, one oracle test and one oracle row column. Version 1.0.275; highest ADR 0510; schema 2.16.0.

**Environment, re-measured 2026-09-18 (c): run the full sweep with `-v`, never `-q`; never pass `-o cache_dir=`
(pytest 9.1.1 exits 4 on the unknown option in thirteen seconds, and a `(…; echo) > log` wrapper reports
exit 0 — read the log's `PYTEST_EXIT` line, never the notification).** This container has NO
pytest-timeout, so a stalled test never becomes a failure; the hang signal is no new results while the
load average is ~0 (the SRA Monte-Carlo oracles sit at one verdict for minutes at ~100 % of one core —
that is not a stall). Expect **7 skips** locally: the urlparse pair, three INCIDENTAL_SVG axis cases, and
the two `test_pptx_libreoffice_interop` skips that are CORRECT here (CI installs LibreOffice and treats a
skip as a FAILURE). The clone arrives SHALLOW — `git fetch --unshallow origin` FIRST (seven seconds this
time), then `git fetch --prune origin && git remote set-head origin -a`. Install with `uv pip install
--python /usr/local/bin/python3 --system -e '.[dev]' build playwright` (never `playwright install`);
re-`uv pip install -e . --no-deps` after a version bump (the installed metadata is what `/api/whoami`
and the wheel report). `/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff` **0.16.8** on
PATH — run both (`python -m ruff` is the 0.16.8). A `sed` rename that matches nothing exits 0 and the
`grep -c` after it exits 1: a `&&` chain stops there and the battery behind it runs ZERO rows — read
the count. `ruff format` wraps an over-long `def … -> (\n    None\n):`, so a rename written for the
unwrapped line misses. Keep the token-guardian's `token_audit.py` in the
SCRATCHPAD (`ruff check .` is whole-tree). A `.pth` editable install lets `PYTHONPATH` shadow the
package — assert the imported module IS the copy every time (a `-p mutcheck` plugin: `MUTCHECK_ROOT` +
`pytest_sessionstart`; it is NOT committed — write it into `<scratchpad>/plugins/mutcheck.py` and put
that directory on `PYTHONPATH`, or `-p mutcheck` cannot import it) — and the same trick runs the working
tree's tests against a pristine worktree's `src/` for the red-first proof. Take the pristine baseline in
a SEPARATE WORKTREE (`git worktree add <scratch> origin/main`), never by mutating the tree under
measurement; **run the full suite in a worktree at the CODE commit while the docs are written in the
working tree** (this unit's code commit carried the rebuilt installers, so only the handoff's version pin
is red there by construction). **Sequence every test edit BEFORE the mutation battery starts**; read the
stderr of every battery row that is neither red nor green, and save the battery's output to a file (a
`tail` loses the first rows). A probe that names a helper the patch renamed CRASHES — and behind a `sed`
filter it reports the pristine number; assert the artefact was written. The wheel must be built AFTER
the last `src/` edit and the last `ruff format`. A two-tree render diff lies until the version string,
the launch token, the pid in `/api/whoami` and the live telemetry in `/api/system` are normalised. A
two-tree GOLDENS diff lies at a day boundary — count toward / away in working minutes of the task's
execution calendar (`execution_calendar_of`), never in wall seconds. `javap -cp
tools/mpxj/lib/mpxj-16.2.0.jar -p -c <class>` reads the vendored bytecode; read a calculated field
cached-first (`getCachedValue`) before any getter. `support.microsoft.com` is blocked by the egress
proxy — Microsoft's field reference is reachable through the Microsoft Learn connector's fetch. `bandit`
B608 fires on an HTML f-string that contains `<select` and a later " from " — reword, do not nosec. Set a
shell variable on its own line, never inside a backgrounded `A && (B) &` list, and never after a `&&`
chain that can short-circuit before it. Four-theme screenshots: serve with uvicorn on a free loopback
port, `chrome_kwargs()` from `tests/web/browser_chrome.py`, set `data-theme` on the root. The 29 intake
`.mpp` files convert in 43 s total with the vendored MPXJ (`java -cp tools/mpxj/classes:"tools/mpxj/lib/*"
MpxjToMspdi <in> <out>`, into the scratchpad; assert every artefact exists, never the exit code).
`ruff` RUF002 refuses an EN DASH in a docstring — write "1 to 62", never "1–62", inside `src/`. **Run the full suite ALONE: a second pytest session beside it, plus ~1.6 GB of scratch, preceded a `Fatal Python error: Bus error` at the SQLite cache's WAL switch (exit 135, run 1 of ADR-0508's gate; mechanism UNVERIFIED — the shared-cache and basetemp-retention explanations were both refuted by evidence) — free the scratch first and give any concurrent pytest its own `--basetemp`.**

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt. **Then, under QC-3, write the plan down and attack it
before the first edit.**

## The next §3 unit is R-45; R-70 follows it.

**R-45** (T1, M) — Hard_File_updated3's BAC / BCWP read 133,400 / 59,340 where Fuse's ribbon reads
121,800 / 53,715, and Fuse's ACWP is to-time-now (64,105 vs the file's 63,763 on updated2) — no
per-task cost oracle in the export (ADR-0473). First executable step: read the Detailed Metric
Report's per-activity cost columns under `00_REFERENCE_INTAKE/` if the export carries them (every
`.xlsx` there, every sheet — a register's step can name a column that is EMPTY), diff by UID; else
the operator owes a per-task BAC / BCWP / ACWP export of updated3 and the unit stops at the census.
**Attack first:** the row's four figures are testimony (re-read them off the export and off the
engine on the committed golden); "no per-task oracle" is a claim about the export's columns (open
every sheet); Fuse's "to-time-now" ACWP is a claim about Fuse's own definition (the `.aft` library's
formula, verbatim — metric-parity skill §1); and the population (which activities are cost-loaded,
which are baselined) must be counted before the 11,600 / 5,625 gap is priced. **R-70** (T2, M) next:
the repo carries its oracle (updated3's 188 stored 12-12 17:00 against its completed successor 291's
09-08 08:00; the 67 / 34 census in ADR-0510) — a recorded-complete successor's need dropped from the
backward pass is the candidate rule; a STARTED successor's remaining work needs its own measurement
first (the logic-reestablished file's 187 is the witness). Then R-03 · R-04 · R-09 · R-69 · R-13 ·
R-18 · R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)).

⇢ Traps paid for, by name (2026-09-18 (c) first): **attack the plan before the first edit — two of four assumptions fell** (the successor gate; the one-milestone class; the deadline-headed chain the mirror-by-reflex would never have touched) · **a survivor is a missing pin as often as a code hole — twice in one session** (the bare "refute" token; the non-binding successor nobody exercised) · **measure both candidate rules on the population before choosing** (the slack-between-instants form: +4 exact, 0 lost) · **key an oracle's stored values by PATH, never by project name** (five Hard_File snapshots share one name; four rows went red against the wrong file) · **read the count, not the `&&` chain** (a `sed` that matched nothing, a `grep -c` of 0, a battery of zero rows) · **say what moved and why** ("the offsets are untouched" was false for ten milestone minutes — the successors' retreat moved them, the carry did not) · **a T2 row inserted after a T3 row fails the tier-order guard** · **a stale kickoff steers a fresh session at finished work** (R-52 / ADR-0497 named as current, eleven ADRs late). (2026-09-18 (b):) **a residual's range is the range the last census printed** (1–28 was 1–62; print the distribution) · **count the class beside the row before pricing the row** (70 of the 173 differing bookings were never the mechanism) · **name the mechanism at the resolution the file speaks** (3,742 boundaries, all tenths of a minute; `hour * 60 + minute` drops both ends) · **measure every candidate rounding on the population before choosing one** (per-gap rounding reads right and drifts six minutes) · **a wall-clock census lies at a day boundary — count toward / away in WORKING minutes** (20 false "away" milestones rendered at the next morning) · **a probe that crashes behind a `sed` filter reports the pristine number** (assert the artefact was written, never the pipeline's exit) · **a rename in `src/` breaks every probe that named the old helper — re-run the probes, do not re-read them**. (2026-09-18:) **a getter that answers 0.0 for "none" may be COMPUTING, not reading — the provenance of a calculated field is the reader's field map, read cached-first** · **count the class beside the one you were told about** (786 − 634 was 90 completed milestones, not 62) · **"no metric reads it" is falsified by running the metrics, not by reading them** (the sandboxed family snapshot found float erosion) · **a metric with a fallback basis reads the ENGINE where the source tool shows 0 — a red stoplight on finished work** · **a render diff lies until every per-process value is normalised** (version, launch token, pid, telemetry: 130 false movers, then 12 true ones) · **a wrapper that exits 0 around a pytest that exits 4 has measured nothing — read `PYTEST_EXIT`** · **a row's remedy can be right and its scope wrong** (the inference was one line; the census it demanded was the unit). (2026-09-17 (d):) **a row's first step can already be TRUE — read the bytecode of the thing you are about to change** (`MSPDIWriter` already wrote the tables) · **fake the clock, don't reason about it** (`faketime` + `LD_PRELOAD` moves the JVM's `now()`; one save under three frozen clocks is a diff, not a memory) · **a number's provenance can be a stored field the getter ignores** (the `.mpp` stores MS Project's save-time `MaxUnits`; MPXJ recomputes it at the reader's clock) · **a surviving mutant is a hole in the CODE as often as in the tests** (the containing-row check was dead beside the latest-row-begun rule) · **a cut can be malformed and print no verdict — read every non-red row's stderr** · **write the corpus figure AFTER the census** (the FX rows do NOT contain every loaded day: 113 / 179 / 113 fall outside) · **a shell variable set inside a backgrounded list is unset in the foreground** (a false bandit red). (2026-09-17 (c):) **a number that appears in the file is not
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
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0508:) per-gap rounding of a split's gaps (measured: six minutes adrift on UID 5316) · a seconds axis in the model or the leg (integer working minutes are a Law) · the duration's seconds surviving import (UID 5268's one minute — pinned, not chased) · the START's own truncated seconds (`_snap_to_working`; ≤ 59 s) · re-reading the 70 negative-class bookings as gap granularity (records and ADR-0502's absorbed delays) · a render diff for an engine-only change (the suite's web tests render every page) · (ADR-0507:) letting the inferred zeros into float erosion's OLD population (measured: every group with a finished activity reads min 0 and goes amber — a fabricated warning; the population was fixed instead) · the XER importer's absent `total_float_hr_cnt` (no P6 witness for finished work) · a pre-1.0.273 Save's `None` for finished work (re-import the source) · a row for MPXJ's started-task branch (699 written elements are a started activity's finish slack; read verbatim, reproduced by the engine's own float on the stored-dates oracle) · re-deriving MS Project's Total Slack for a finished activity from anything but its stored (0, 0) pair · (ADR-0506:) a converter change for R-63 (the tables are already written) · a zero-availability reading outside every row (R-68 — the operator's Resource Graph decides it) · the XER `RSRCRATE` rows onto the model (the XER scalar is already data-date resolved; no P6 witness) · rate tables B–E / `OvertimeRate` / `CostPerUse` / the formats · reading `OverAllocated` / `AvailableFrom` / `AvailableTo` / `CurrentDate` (the clock's) · regenerating the goldens' resource sections · a Java-gated CI test on the golden's blob (the checkout is shallow) · a "varies" roster marker · (ADR-0505:) the BACKWARD carry (a
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
⇢ Residuals registered, none taken: **R-68** (a day outside every availability row — ASK, question (f) in the report's §5: the three tampered `Project5_FX0x` saves book crews on 113 / 179 / 113 loaded days past their single bounded rows; the engine holds the latest row begun, the converter printed the default 1, MS Project's verdict unknown) · **R-67** (the backward mirror, above) · **File2's UID 5268** (one minute LONG by the duration's own import rounding — ADR-0508's residual, pinned by name) · **UID 401 on the 24-hour snapshot** (a completed booking whose recorded Start precedes its first worked block by 540 minutes on a `Customer Service Team` calendar that save declares no segments for — no row) · **the START's truncated seconds** (≤ 59 s; no golden turns on it) · **the two
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
