# Kickoff prompt — next session

**`main` @ `a95482c1` (#693, R-58 / ADR-0503, v1.0.269) — its OWN CI was read TO CONCLUSION: run 1911 (`35221600468`) SUCCESS, all six jobs (`cui-guard` 12:31:51Z · `browser` 12:49:04Z · `floor` 12:59:18Z · `test (3.13)` 13:07:18Z · `test (3.11)` 13:20:46Z · `check` 13:20:53Z), and installer-smoke 749 (`35221600523`) SUCCESS 12:36:31Z, which EXISTS because #693 rebuilt the installers. Nothing about `a95482c1` is outstanding; do NOT re-read it. Always `git fetch origin` and read `git log origin/main` before trusting any sha written here, including this one — the merge-record treadmill was deliberately ended, so this head block will lag `main` by design.**

**R-59 is CLOSED — ADR-0504, draft PR [#694](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/694) (the OPERATOR merges; if it is merged when you arrive, `main` has moved past `a95482c1` — read ITS own six jobs AND its installer-smoke run to conclusion, since the diff touches `installer/**`, and expect EIGHT checks on the PR). The `/analysis` Working-calendar panel now names EVERY calendar the base pass runs on, read off the engine's own execution plans: `plan_calendars(schedule) -> PlanCalendars` in `engine/cpm.py` beside `off_project_calendars` — `axes` (the calendars total float is measured on), `legs` (the calendars execution legs run on: a crew's own, a task calendar the crew restricts nothing of, or their intersection, on the calendar OBJECT, never a parent; `derived` = uid −2, `<task> ∩ <crew>`), `elapsed` (counted, not listed), `population` (ADR-0128's); dedup by object, registered first by uid, derived after by name. Do not re-derive it, and do not "widen" `off_project_calendars` — it is structurally blind to a crew's calendar (the assignment's resource carries it) and was kept as public API only.**

**The page's old sentence was FALSE, not incomplete:** it still said the base CPM "models the single
project calendar (ADR-0028) … a single-calendar approximation" — retired by ADR-0322 / 0474 / 0503.
On Hard_File the page named `24 Hours` + `Standard+Sat.` while the plans ran legs on **Customer
Service Team** (25 activities), **Content Developer** (18), **Logistics** (1) and the derived
**`Standard+Sat. ∩ Customer Service Team`** (UID 94). Now: *"Standard (8 h/day, a 5-day work week,
0 holiday(s)) is the time basis for 65 of 110 activities; the other 45 run wholly or partly on 6
other calendars, named below."* Single-calendar files render BYTE-IDENTICAL; `/api/analysis`
byte-identical on Hard_File, Project5 and Large_Test_File (no number moved).

**The seam was a decision, not a reflex:** the listing lives in `engine/cpm.py` although the design
system says a UI change never touches `engine/` — that rule protects calculations (proven
untouched); `web/` has never imported a private engine name; ADR-0492 is the precedent. The
operator may overrule; the move is trivial. **A per-booking `booking_calendar` listing was REFUSED
as the source** — it over-claims against the plan (`24 Hours` on 9 bookings no leg runs on, under
`IgnoreResourceCalendar`; the crew of the ELAPSED UID 146).

**Traps this unit paid for:** **an over-claimed LIMITATION is as false as an over-claimed rule** —
a disclosure is a claim about the engine and is re-verified when the engine changes, like a parity
pin · **read the plans, not the inputs to the plans** — only the plan builder knows which bookings it
dropped · **the rig was refuted THREE times before the engine was, all three an unstated population
filter** (crews 4 / 5 / 7 on the project pattern — the registry is a PREMISE, assert it; the elapsed
UID 146 excluded before a loop that then asserted its booking; summary UID 5334 in the shape map,
which covers EVERY task — apply ADR-0128's population to it explicitly) · **probe the pristine tree
before writing what the red run "would show"** — the pristine panel was SILENT on the crewed
schedule, not carrying the stale sentence · **write the seam tension down rather than pick
silently**.

**Baselines to attribute against: the previous unit's 5,539 passed / 7 skipped and `-m parity` 170 / 0
until this unit's measured figures land in the follow-up docs-only commit on #694 (expected 5,561
collected = 5,546 + 19 − 4). Version 1.0.270; highest ADR 0504; schema 2.15.0.**

**R-58 is CLOSED — ADR-0503 (#693, `main` @ `a95482c1`).** A task calendar meets a crew calendar on
their INTERSECTION — `_calendar_intersection` behind `_task_shape` and `booking_calendar`: weekdays
∩, intraday blocks pairwise ∩, holidays ∪, an extra working day only when both work it; a calendar
the other restricts nothing of stands for the intersection BY IDENTITY; WORK crews that NAME a
calendar only; disjoint calendars fall back to the task calendar (UNVERIFIED — no witness); the
slack axis stays the TASK calendar (ADR-0474). The row's witness was UID 94, not UID 14. **R-67**
(147's Saturday late start on the elapsed axis — 157's late finish and 94's float) is registered,
not taken. Do not re-derive any of it.

**R-57 is CLOSED — ADR-0502 (#691).** A BOOKING's own `Assignment/LevelingDelay` is honoured on
that leg alone, on ADR-0474 / ADR-0501's TYPE AXIS — a leg with its OWN span (`FIXED_UNITS`, ratio
< 1) is PUSHED by its delay; a leg that SPANS THE TASK (ratio 1.0) ABSORBS it. Do not "fix" the
absorb half (it cost `Large_Test_File` 93 finishes-within-a-day before the census refuted it).
**R-66** (UID 381's day on the base snapshot) is registered, open.

**R-61 is CLOSED — ADR-0500 (refuted) and SETTLED — ADR-0501 (the 29 `.mpp` files).** ADR-0474's
type rule stands: a non-`FIXED_UNITS` leg spans ratio 1.0 × the effective duration on its leg
calendar, and a WORK booking's recorded window is never read (ADR-0487). **R-65** (the 1–28-minute
gap granularity) is registered.

## R-47 is CLOSED (ADR-0495). The population is Fuse's Record Count — do not re-gate it on a baseline.

## R-46 is CLOSED (ADR-0492). BCWS is the file's own series — do not re-derive it. R-60 is CLOSED (ADR-0491): regenerate a golden ONLY through `tools/regenerate_timephased_goldens.py`.

**Environment, re-measured 2026-09-17 (b): run the full sweep with `-v`, never `-q`.** This container
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
add <scratch> origin/main`), never by mutating the tree under measurement — and **run the full
suite in a worktree at the CODE commit while the docs are written in the working tree** (this
session's pattern: the suite never measures a tree being edited). The wheel must be built AFTER the
last `ruff format` (the lockstep pin). Four-theme screenshots: serve with uvicorn on a free
loopback port, `chrome_kwargs()` from `tests/web/browser_chrome.py`, set `data-theme` on the root.

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad) and before each operator prompt.

## The next §3 unit is R-64.

**R-64** (T2, S) — Hard_File's milestone 387 ("Business Performance Planning") hangs on an external
predecessor link (`PredecessorUID` −65535) the MSPDI cannot resolve, so it sits one working day
early (08-17 16:00 vs the stored 08-18 17:00) and the chain 400 → 399 → 401 → 402 → 403 → 404
inherits the day (ADR-0491: their spacing is now MS Project's to the minute). First executable step:
read the link's `CrossProject` / external-task fields if the MSPDI carries them, else treat a
milestone whose only predecessor is external as stored-date driven and disclose it; red-first on
387's stored 08-18 17:00. Oracle: 387 and the chain 400 → 404 on their stored dates. **Read the
activity's own XML before pricing the rule** (the R-58 lesson): dump 387's `PredecessorLink`
elements and the chain's stored dates from EVERY Hard_File snapshot first; count the population of
external links across the 15 goldens and the 29 `.mpp` files before writing a line.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481 (OR-11e) ·
ADR-0482 (OR-12) · ADR-0483 (OR-13) · ADR-0484 (/scorecards) · ADR-0485 (OR-14) · ADR-0486 (OR-15) ·
ADR-0487 (R-56) · ADR-0488 (OR-16 / OR-16b) · ADR-0489 (/margin) · ADR-0490 (R-49) · ADR-0491 (R-60) ·
ADR-0492 (R-46) · ADR-0493 (OR-17 in part) · ADR-0494 (OR-18) · ADR-0495 (R-47) · ADR-0496 (OR-19) ·
ADR-0497 (OR-20) · ADR-0498 (R-52) · ADR-0499 (R-50) · ADR-0500 (R-61 refuted) · ADR-0501 (R-61
settled on the `.mpp` corpus) · ADR-0502 (R-57, v1.0.268) · ADR-0503 (R-58, v1.0.269) · **ADR-0504
(R-59 CLOSED — the calendar disclosure; v1.0.270; this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away
census across EVERY golden AND the 29 `.mpp` files before the ADR → mutation proofs by name → the full
gate → an ADR → the state docs → a draft PR): **R-64** (above) · **R-63** (the converter resolves
`CurrentDate`, `MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time) · **R-62** (every
absent slack the writer dropped is a zero, completed tasks included) · **R-65** (the 1–28-minute gap
granularity) · **R-66** (UID 381's day on the base snapshot) · **R-67** (147's Saturday late start on
the elapsed axis — 157's late finish and 94's float) · **R-45** · then R-03 · R-04 · R-09 · R-13 ·
R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards — the operator's order picks the
next screen.
⇢ Traps paid for, by name (2026-09-17 (b) first): **an over-claimed LIMITATION is as false as an
over-claimed rule** · **read the plans, not the inputs to the plans** · **a derivation from the
engine's own maps owes the population filter explicitly** (three refutations, one class) · **probe
the pristine tree before writing what the red run "would show"** · **write the seam tension down** ·
**the version bump and the handoff's version pin ride ONE push** — a code-only push with a bump
goes red on `test_state_docs` (a wasted CI cycle on #694's first run).
(2026-09-17:) **a row's WITNESS is testimony too** — one XML dump settles which activity a row is
about · **a five-value oracle beats a finish** · **the rig can be wrong twice before the engine is** ·
**a survivor that is not dead code is a missing pin** and its case is the finding · **count the
artefacts of every sweep** (28 ≠ 29) · **name a residual with its mechanism** · **a battery that
prints no verdict has run no mutant** (`set -u` + `local a=$1 b=$a`). (2026-09-16 (d):) **an audit
row's REMEDY is testimony too** — price it against the whole population before writing a line ·
**a SURVIVOR is worth more than the cuts that go red** · **a line that cannot fire must be DELETED**
· **a disclosure that over-claims is worse than none** · **`ruff format` after the wheel build
breaks the lockstep pin**. (2026-09-16 (c):) **a residual must name the POPULATION it was measured
against** · **a completed task cannot adjudicate a scheduling rule** · **print the PLAN, sorted, with
every leg's finish** before believing a diagnosis about one leg · **an instrument that cannot
detect its own failure reports a confident zero** · **a non-mutation is not a survivor**. (Earlier,
still live:) **a register row can be RIGHT about the arithmetic and WRONG about the mechanism** ·
**run the census before pricing the fix** · **proving a patch inert requires proving it FIRED** ·
**test a vendor-rule claim at the vendor's scale** · **a parallel implementation in a test is an
oracle for itself** · **an additive change to a metric catalog is NOT additive to the guards** ·
**an error message is a statement by the INSTRUMENT** · **a converter that exits 0 on refusal** —
assert the artefact exists · **prove a CI fragment under the CI shell** · **a gate that can SKIP
silently measures nothing** · **a model's memo about its own error is testimony** · **rebuild the
wheel after the LAST edit** · **a verdict quoted on the page is evidence** · **"replaced" for an
identical paste is a false statement of change** · **a register's step can name a column that is
EMPTY** · **pin the population from the reference tool's own count** · **the branch you stack on can
move — and MERGE — under you** · **a figure with no test behind it is testimony however many ADRs
repeat it** · **a number written mid-session is not a measurement** · **provenance is a diff, not a
report** · **`git log -1 -- tools/mpxj` changes when the converter changes** · a fixed bug is
evidence against the hypothesis it lived under · negative pins are green on the pristine tree by
construction; prove them with a mutant · read every green in a battery as a finding about the
instrument · MS Project's stored dates are a per-activity CPM oracle · `LevelingDelay` is tenths of
a minute · MPXJ writes no zero · `Large_Test_File.mpp` ≠ `Large Test File.mpp`.
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0504:) a per-booking
`booking_calendar` listing as the disclosure's source (over-claims: 9 `24 Hours` bookings with no
leg, the elapsed UID 146's crew) · widening `off_project_calendars` (blind to the assignment's
resource by construction) · re-implementing the plan builder's filters in `web/` · importing
`_plan_shapes` into `web/` · the elapsed clock as a calendar line · a `calendar_basis` on
`/api/analysis` (one dict if the operator wants it) · a calendar table on the panel (a design-queue
question) · (ADR-0503:) intersecting a MATERIAL / COST leg · re-anchoring the slack axis on the
intersection · a `CPMResult` disclosure for the intersection · registering the derived calendar in
`Schedule.calendars` · intersecting a crew that names NO calendar · (ADR-0502:) pushing an absorbing
leg's delay · a post-delay snap in `_leg_finish` · (ADR-0500/0501:) "a fixed-duration leg spans the
task's window" (315-to-0) · a fixed-duration leg on the task's axis · (ADR-0498:) the exported
`.pptx` as a malformed package · (ADR-0496:) the tool's gateway key path as the cause of the 401 ·
(ADR-0495:) re-gating the SPI(t) population on a baseline · (ADR-0492:) re-deriving BCWS on the crew
calendar · (ADR-0491:) an ELAPSED reading of a split gap · dropping the baseline timephased series
from the converter · a task-level `<Splits>` model field · regenerating a golden from the intake
path's CURRENT bytes · the KPI-tile selector on /margin (ADR-0489) · a quantity-or-rate rule for
material / cost spans (ADR-0487) · a data-date floor (refuted twice) · the DCMA08 baseline basis
(R-48) · Fuse's ACWP-to-time-now and updated3's BAC (R-45) · R-20 / UI-03 (ADR-0477) · the HELD and
CLOSED rows of the report.
⇢ Residuals registered, none taken: **R-67** · **R-66** · **R-65** · **the daylight telemetry HUD**
(observed 2026-09-17 (b) on the 1440-px `/analysis` screenshot: the fixed CPU / RAM / GPU / DISK
widget overlays the right edge of every full-width panel in daylight — pre-existing chrome, no row;
the operator's call) · the task-level `LevelingDelay` reader's truncation (`// 10`; measure before
changing) · the all-bookings-delayed task start (no witness; UNVERIFIED) ·
`test_driving_path_whole_schedule_browser.py:104` is WIDTH-RACY (#667; never fix it by widening a
wait) · `/settings` scrolls sideways (an over-wide `<select>`) · UID 5306's chain on the leveled SSI
golden (a 2:36 daily gap read as 2) · ADR-0489's own (the KPI selector; the callout collapsed; two
charts at 569 px) · ADR-0488's · ADR-0486's · ADR-0485's · ADR-0483's · OR-11b · OR-11d · the
working-minute axis · the hint bubble · ADR-0484's in-grid rows ·
`Hard_File_updated_with_logic_reestablished`'s negative float chain (−7,440 vs a stored 0; not a
golden, no row).
⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve);
EIGHT checks when `installer/**` changes (this PR does), SIX for docs-only; `pull_request_read`
`get_status` returns `pending / 0` on a fully green PR (the legacy API) — use `get_check_runs`; a
`check_suite.completed` event can carry a superseded `head_sha` — re-read the current head; a red
cell on `main` for a tree identical to the green PR head is the runner's claim — compare tree hashes
first; the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER `git log
origin/main..HEAD`; after a squash-merge restart the branch with `git fetch --prune origin && git
remote set-head origin -a && git checkout -B <branch> origin/main`, never amend or rebase the squash
commit. `actions_list` with a branch filter can return a stale page for a workflow — filter by the
workflow file (`ci.yml` / `installer-smoke.yml`) and check the `head_sha`. Review cover is still
absent — Codex quota EXHAUSTED; the mutation batteries and the full gate are all this repo gets.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md`
FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the roadmap by testimony tier,
pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every session (ADR-0393). `git fetch
origin` before you branch, number an ADR, or commit.
