# Kickoff prompt — next session

**R-61 is CLOSED — ADR-0500, and it is CLOSED as REFUTED. Do not re-open it, do not implement "a
fixed-duration leg spans the task's window", and do not re-run its census expecting a different
population.** The row was right about the arithmetic and wrong about the mechanism, and `engine/`
was deliberately left untouched — **v1.0.267 is unchanged, no wheel or installer rebuild**.

Measured, all of it on a shadow copy of `src/`, never the tree under measurement:

* **The census the row asked for returns ONE TASK.** Across all 15 MSPDI goldens the population of
  (active FIXED_DURATION task × off-pattern WORK leg) is **five rows = UID 210 in five snapshots of
  one file**. No second task, no unstarted witness, none without a project-calendar co-booking — so
  **no golden can discriminate the rule.** The witness's numbers are the row's: duration 1,920 min,
  leg 1,920 min of the 24-hour *Content Developer* calendar, recorded window **7,740**, and that
  window is the TASK's own (08-20 08:00 → 08-25 17:00), which MS Project writes onto all four of
  the task's assignments, work and material alike.
* **Neither mask the row names is the mask.** UID 210's primary (finish-placing) leg is the
  **`Standard`-calendar WORK leg** of the Logistics Apprentice booking — 1,920 min on the PROJECT
  calendar, landing on the stored finish exactly. The crew leg finishes 08-21 16:00, four days
  earlier, and has never placed the task. Cutting ADR-0476's pin reads 210 **+1,260 min LATE**, not
  early; cutting ADR-0487's material leg moves it **not at all** (that cut does move updated3's
  project finish 12-12 → 12-06 and within-a-day 106 → 44, so it has teeth — it just misses 210).
* **The proposed rule FIRES and changes nothing** (ratio 1.0000 → 4.0312, span 1,920 → 7,740, that
  leg's finish 08-21 16:00 → 08-25 17:00): every figure on all 15 goldens byte-identical, its only
  effect a LOST `booking_span_driven` disclosure.
* **Generalized it is refuted 315-to-0.** MS Project has no separate scheduler for FIXED_DURATION
  and 267 corpus tasks are placed by a ratio-1.0 WORK leg: within-a-day 1,666 → 1,568 ·
  1,687 → 1,585 · 1,645 → 1,567 on the three Large Test File goldens, every other golden unmoved,
  **315 activities AWAY / 0 TOWARD** (worst +309,865 min). A split booking's window spans the
  leveling gaps ADR-0491 honours separately — `Large_Test_File` UID 5231's window (89,760) is
  **26,880 crew minutes SHORTER** than the correct occupancy.
* **The alternative the row does not name is refuted too**: a fixed-duration leg on the TASK's axis
  is 0 toward / 5 away — it drops 210 off the wall path, so ADR-0476's pin lands at 16:00 (that
  ADR's own day-boundary residual).

**Shipped:** `tests/parity/test_r61_fixed_duration_leg_oracle.py` (10 pins) · ADR-0500 · the R-61
row → CLOSED. Battery **6 / 6 red by name**, control green, every one of the 10 pins red under at
least one mutant.

**The residual, named and OPEN — do NOT re-chase without it:** only a production IMS carrying a
FIXED_DURATION activity on an off-pattern crew **with NO project-calendar co-booking**, alongside
MS Project's stored dates, can settle the rule. **A sixth row appearing in the census test is the
signal to re-read ADR-0500.**

**FIRST: read `main`'s own CI runs for the merge of PR #686** (R-50 / ADR-0499, `0b010936`). They
were STILL IN PROGRESS when this was written — CI run 1893 (`35097402239`): `cui-guard` 12:42:51Z
SUCCESS, `browser` 13:00:24Z SUCCESS, `test (3.11)` / `test (3.13)` / `floor` in progress;
installer-smoke run 744 (`35097402279`) in progress. **Read them to conclusion; do not inherit this
line as a verdict.** (CI 1890 (`35051509437`) for `9cb46317` is already settled — completed /
SUCCESS, all five jobs. Do NOT re-read it.) Always `git fetch origin` and read `git log origin/main`
before trusting any sha written here.

**Environment, re-measured 2026-09-16: run the full sweep with `-v`, never `-q`.** This container
has NO pytest-timeout, so a stalled test never becomes a failure — the R-50 sweep sat at 78 % for
2 h 16 m with the machine IDLE (load 0.02, pytest 10 % CPU, a chromium alive 1 h 53 m, no test
server listening: a deadlocked browser test). Dots give no suspect; `-v` names the test in flight,
and the hang signal is no progress while the load average is ~0, which a percentage cannot tell
you. The hung test was NOT identified and did NOT recur (UNVERIFIED). Expect **7 skips** locally:
the urlparse pair, three INCIDENTAL_SVG axis cases, and the two `test_pptx_libreoffice_interop`
skips that are CORRECT here (no libreoffice-impress; CI installs it and treats a skip as a
FAILURE). The clone arrives SHALLOW — `git fetch --unshallow origin` FIRST. Install with
`uv pip install --python /usr/local/bin/python3 --system -e '.[dev]' build playwright` (never
`playwright install`). `/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff` 0.16.7 on
PATH — run both.

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the
scratchpad — `ruff check .` is whole-tree) and before each operator prompt.

## The next §3 unit is R-57.

**R-57** — an assignment's OWN leveling delay is not read: only the task's is honoured (ADR-0474).
`Hard_File` UID 398's RA 277 is a split ON a delayed assignment — its gap has been honoured since
ADR-0491, its delay is not; UID 188 on updated2 is the same class. First executable step: read
`Assignment/LevelingDelay` onto the `Assignment` model and delay that leg alone; pin UID 398's
stored finish **2026-08-27 11:59**. The oracle is the stored finish of UID 398. Read
`engine/cpm.py`'s plan builder and ADR-0474 / 0487 / 0491 / **0500** before touching a leg — 0500
is why the leg you are looking at may not be the leg that places the finish.

**Traps R-61 paid for, carried forward:** **a register row can be RIGHT about the arithmetic and
WRONG about the mechanism** — print the PLAN, sorted, with every leg's finish, before believing any
diagnosis about one leg; a leg that computes wrong is not a defect until it is the leg that PLACES
the finish · **run the census before pricing the fix** — a row is only as real as its population,
and this one's was a single task masked three ways · **proving a patch inert requires proving it
FIRED** — an unchanged corpus is otherwise indistinguishable from a patch that never ran (this one
moved a ratio 1.0000 → 4.0312 and changed nothing) · **test a vendor-rule claim at the vendor's
scale** — "the window is the rule" is a claim about every ratio-1.0 WORK leg, and there it is
315-to-0 wrong · **a parallel implementation in a test is an oracle for itself** — the first census
re-implemented the plan builder's three leg-calendar lines and was GREEN under the mutant that
breaks exactly that resolution; route it through the engine's own entry point and let a mutant
prove it · **the deliverable of a refuted row is a pinned measurement, not a shrug** — ship the
population, the corrected premise, the refutation witness and a labelled tripwire, and name what
would settle it.

**Traps R-50 paid for, still live:**
**an additive change to a metric catalog is NOT additive to the
guards** — with the static gate, every targeted module, a 14-mutant battery, the corpus census and a
four-theme render all green, the first FULL-SUITE run still returned **4 failed** (the catalog family tuple,
pinned in two places, plus `len(metrics) == 21`; the monolith-split contract's `X as X` re-exports; the
`/ribbon` panelkit `.panel` census), every one a real consequence and none a flake. **Six guards were
re-aimed across the unit; the targeted runs found only two.** Price the GUARD surface before adding a
metric, a family or a panel, and re-aim a fired guard while KEEPING its teeth rather than renumbering it.
Also: a **page-wide** guard is under-specified the moment the page grows a second
matrix — count PER PANEL (the page-level twin of `CLAUDE.md`'s phase-2 source-path trap) · asserting a **header**
exists is not asserting a **value** exists (a header with nothing beneath it survives the column being dropped from
the row) · the `.aft` names metrics in `<Name>` **elements**, not `Name="…"` attributes, and a zero-result search must
be proven able to return non-zero before the zero is believed · a same-named Bible metric needs its **GUID** as the
key · the reference tool's **Record Count** is a second independent oracle the totals cannot replace · reuse the
page's existing tooltip vocabulary rather than writing a second one.

## R-47 is CLOSED (ADR-0495). The population is Fuse's Record Count — do not re-gate it on a baseline.

What is now true, measured: the Detailed Metric Report's per-activity SPI(t) column is EMPTY on every activity
row (both reports); it carries the total and a **Record Count (717 / 726)**, and the engine's sum of ratios over
that count reproduces 8.22 / 8.14 exactly. The engine now admits every started activity with a non-zero actual
span and scores an unbaselined one as 0 (UID 7260 in progress on both files; 7262 / 7551 completed on File2 —
the workbook's `Completed (w/o Baseline Duration)` = 2; the zero-span milestone 7183 stays excluded). Corpus
census 27 fixtures: 5 moved, all that class, none away (the `ssi_uid152*` saves → 8.22, NOT pinned as oracles;
TP3 0.53 → 0.48 on UID 34, no oracle). Mutation battery 5 / 5 by name. **Held (operator-owned):** the VALUE of a
completed-unbaselined term — 0 by the formula's blank-as-0; File2's 2-dp total cannot discriminate it from a
substituted duration (two of 726). Only a Fuse run on a small file with a completed, never-baselined activity
would. Do not build on either assumption.

## R-46 is CLOSED (ADR-0492). BCWS is the file's own series — do not re-derive it.

What is now true, measured: the Bible's `PV (BCWS) = sum(BCWSPV)` is each activity's BCWS as MS Project
stores it, and the regenerated goldens carry it — the assignment baseline-cost series (`TimephasedData`
Type 5). The importer reads every valued block as a `CostPiece` on `Assignment.baseline_cost_pieces`
(SCHEMA_VERSION 2.14.0; the JSON Save round-trips it), and `evm._planned_value` sums a task's series
through the status date, prorates a block the status date falls inside in working minutes of the
booking's calendar (`cpm.booking_calendar` — the plan builder's rule, public; `cpm.working_minutes_between`
its ruler) and accrues the budget no series carries by ADR-0473's linear rule. The three Hard_File
ribbons are exact (16,000 / 64,240 / 110,440 — the last pinned from `Hard_File_update2 vs update3_Fuse -
Excel .xlsx`, a workbook no test had read); ONE task moved in the whole corpus (updated UID 187, 3,750 →
3,600); SPI on updated 1.04 → 1.05 = the ribbon. The register's step (re-derive on the crew calendar) was
refused with the reason in the ADR. R-45 (updated3's BAC / BCWP / ACWP) stays open.

## R-60 is CLOSED (ADR-0491). Read the ADR before touching a leg, a golden or the converter.

What is now true, measured: the vendored converter writes MSPDI `TimephasedData` on every ingest
(`MSPDIWriter.setWriteTimephasedData(true)`; +7 % bytes on the 1,723-activity file, +0.4 s of parse,
the same JVM wall time under `-Xmx1g`); a WORK booking's zero-work blocks bound its `work_pieces`
(`WorkPiece` model, SCHEMA_VERSION 2.13.0); the engine's `_Leg` carries `gaps` and honours, in WORKING
minutes of the leg's calendar forward and backward, every gap **no other WORK booking of the task works
through** (`_split_gaps` / `_covered_span` — a gap another booking works through is that booking's own
contour, already inside the Duration: Large_Test_File2 UID 5308's chain read three weeks late before this
test existed). Every Hard_File snapshot's project finish is EXACT; updated3's UID 403 lands on 11-05 09:12
with the stored LateStart 11-25 13:48 and slack 12,888; Large_Test_File within-a-day 1569 → 1666. **Every
MSPDI golden except EVM1/2 was regenerated from ITS OWN save** by `tools/regenerate_timephased_goldens.py`
(the blob in git, the same-save proof by section diff inside the tool, the new `<Assignments>` spliced
into the old golden) — `tests/fixtures/golden/PROVENANCE.json` names each save, pinned by
`tests/guards/test_golden_provenance.py`. Regenerate a golden ONLY through that tool.

Environment, re-measured 2026-09-14: the clone arrives SHALLOW — `git fetch --unshallow origin` FIRST
(~60 s), confirm `git log -1 -- tools/mpxj` reads the ADR-0491 commit (it touched `tools/mpxj`), then
build. Install with `uv pip install --python /usr/local/bin/python3 --system -e '.[dev]' build playwright`
(never `playwright install`). Re-`uv pip install -e` after a version bump. `/root/.local/bin/ruff` 0.15.8
shadows CI's `/usr/local/bin/ruff` 0.16.7 on PATH — run both. Keep the token-guardian's `token_audit.py`
in the SCRATCHPAD (`ruff check .` is whole-tree). `/usr/bin/time` is absent — a `&&` chain that needs it
prints nothing and starts nothing; launch background jobs through the tool's own runner and check the
log exists. MPXJ from Java: `javac -cp 'tools/mpxj/lib/*' --release 17` a probe against `org.mpxj.*` and
let the compiler refuse the method names you remember (`getWorkSplits`, `getRawTimephasedRemainingRegularWork`,
`getAmountPerHour` are the real ones). A `.pth` editable install lets `PYTHONPATH` shadow the package for a
mutation battery — assert the imported module IS the copy every time (a `-p mutcheck` plugin does it).

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) · ADR-0475
(/standards) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481 (OR-11e) · ADR-0482 (OR-12) ·
ADR-0483 (OR-13) · ADR-0484 (/scorecards) · ADR-0485 (OR-14) · ADR-0486 (OR-15) · ADR-0487 (R-56) · ADR-0488
(OR-16 / OR-16b) · ADR-0489 (/margin — the Control family COMPLETE) · ADR-0490 (R-49) · ADR-0491 (R-60 CLOSED, #673) ·
ADR-0492 (R-46 CLOSED) · ADR-0493 (OR-17 in part, #677) · ADR-0494 (OR-18, #678) · ADR-0495 (R-47 CLOSED, #679
MERGED) · ADR-0496 (OR-19 — OR-17 §4 answered and OR-17 CLOSED; #680 MERGED) · ADR-0497 (OR-20 —
the driving-path series on the stored Finish; the model's self-diagnosis refuted) · **ADR-0498
(R-52 CLOSED — the `.pptx` loads; the LibreOffice refusal was an install with no presentation import
filter)** · **ADR-0499 (R-50 CLOSED — the library's same-named Metric History variants exposed as their own metrics, #686 MERGED)** · **ADR-0500 (R-61 CLOSED as REFUTED — the census returns one task; the window rule is inert as written and 315-to-0 wrong generalized; `engine/` untouched; this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away census
across EVERY golden before the ADR → mutation proofs by name → the full gate → an ADR → the state docs →
a draft PR): **R-57** (an assignment's OWN leveling delay — Hard_File UID 398's RA 277 is a split ON a
delayed assignment: its gap is honoured since ADR-0491, its delay is not; UID 188 on updated2) · **R-58** ·
**R-59** · **R-64** (Hard_File milestone 387 hangs on an external predecessor, UID −65535 — the one working
day the chain 400 → 404 still sits early; their spacing is MS Project's to the minute) · **R-63** (the
converter resolves `CurrentDate`, `MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time —
`MaxUnits` feeds the loading view) · **R-62** (in #672's register: every absent slack the writer dropped is
a zero, completed tasks included) · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The
design queue is 19 artboards — the operator's order picks the next screen (§6 lists them).
⇢ Traps paid for, by name (2026-09-15 (f) first): **an error message is a statement by the INSTRUMENT, not about the file** — hand the same tool a known-good artifact the reference implementation authored BEFORE diagnosing your own · **a converter that exits 0 on refusal** (`soffice`) — assert the artifact exists, never the exit code · **a mutant that does not change the thing under test proves nothing** — two cuts of the CUI-marking mutant were NON-mutations, not survivors · **prove a CI fragment under the CI shell** (`bash -e`, `set -o pipefail`) — the first local proof exited 0 on a collection error · **a gate that can SKIP silently measures nothing** — install the instrument in CI and make a skip a failure. (2026-09-15 (e):) **a model's memo about its own error is testimony** — measure the mechanism on the real file before adopting it, and build the alleged defect as a mutant · **two per-version date series of one shape in one prompt get cross-wired** — say whose date each line carries · **drivers and the finish beside them must share an axis** · **"do two instants disagree" is a project-axis question** — `working_minutes_between(Fri 17:00, Mon 08:00)` reads 480 on a segment-less calendar · **rebuild the wheel after the LAST edit** · **the transaction log cannot replay a prompt** (Law 1) — the cited facts under the answer and the ask export are the record · (2026-09-15 earlier:) **a verdict quoted on the page is evidence** — a server cannot call an
unrecognised credential "expired"; read the quoted reason before re-testing the tool · **"replaced" for an identical
paste is a false statement of change** — compare with the held value · **a wire test proves the path it drives** — a
fresh-process test is not an in-process re-paste · **a register's step can name a column that is EMPTY** — the
Detailed report's per-activity SPI(t) cells hold nothing; its Record Count row is the discriminating number, and
membership is settled by the COUNT before any ratio is compared · **pin the population from the reference tool's own
count, not only the 2-dp figure** · **an oracle's total at 2 dp cannot always discriminate a member's TERM** — say what
the corpus settles and what it cannot · **SpreadsheetGear omits `r=` on cells AND rows** — a std-lib reader needs both
counters · **the branch you stack on can move — and MERGE — under you** — fetch before basing and before committing; compare tree hashes before restarting · **a register's "first executable step" is a hypothesis
about the mechanism** — the file carried the output (the Type-5 series) since the last unit and nobody
re-priced the row; measure whether the file records the answer BEFORE re-deriving it · **a figure with no
test behind it is testimony however many ADRs repeat it** — grep the intake workbooks' sheet XML for the
NUMBER · **a number written mid-session is not a measurement** — write the row after the log · **a survivor
below a guard is an equivalent mutant** — re-cut it AT the guard · **a wide red can be the contract** —
durations read as numbers fail the import loud on purpose · **the environment is cold every time** (shallow
clone; no package; CI's ruff only after the dev install). (2026-09-14:) **"honour what the file records" is not a rule until the
corpus says WHOSE fact it is** — a golden-level count hid 24 regressions behind 80 improvements on one file;
run the per-task toward/away census and derive the away-mover whose predecessors are not away-movers ·
**provenance is a diff, not a report** — the save an ADR called unavailable was in `git log --all`; address
a save by its BLOB, never by a path at a commit (`--follow` invents history) · **the rig can be wrong before
the engine is** — recompute every expectation from the rig's own numbers · **the compiler is the API
reference** · **a launch line is not a launch** — check the log exists · **`git log -1 -- tools/mpxj`
changes when the converter changes** — the installers' `SF_MPXJ_REF` must be the commit that carries the new
class, tree-identical to the working tree (commit the converter FIRST, then build). (2026-09-12:) the
"contour" was a booking the engine SKIPPED · "the MSPDI cannot explain it" is a statement about the
converter's output, not the file · a register's count is a threshold artefact until re-derived · a set keyed
on the frozen `Calendar` model costs 420 hashes per 20 solves · a rig whose legs all sit on the project
pattern cannot see a disclosure mutation · a 4 KB read limit dropped a long reason instead of bounding it ·
a page-wide substring matched a field's TITLE text · one request made OUTSIDE the tool settled
tool-vs-gateway in one step. (Earlier, still live:) a fixed bug is evidence against the hypothesis it lived
under · read a completion as evidence, never `str()` it · a diagnostic that names a PAGE is true and
useless — name the FIELD · negative pins are green on the pristine tree by construction; prove them with a
mutant · read every green in a battery as a finding about the instrument · a rect cannot see text spilling
inside a fixed cell · measure every theme · two errors can CANCEL · an inherited attribution is TESTIMONY ·
Playwright's virtual mouse SURVIVES `goto()` — park it · an `assert` in `src/` is a house-style violation ·
a design mock's status word, decomposition and export label are claims about the ENGINE · MS Project's
stored dates are a per-activity CPM oracle · `LevelingDelay` is tenths of a minute · MPXJ writes no zero ·
`Large_Test_File.mpp` ≠ `Large Test File.mpp`.
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0498:) the exported `.pptx` as a malformed package (refuted — the refusing LibreOffice had no presentation import filter and refused a PowerPoint-authored deck too) · `presProps`/`viewProps`/`tableStyles` as the CAUSE of anything (they are written now, and LibreOffice's import is byte-identical with and without them) · re-creating "LibreOffice 7" (the mechanism is a missing filter, not a version) · `python-pptx` as a second reader (a dev dep for one test, and it is not PowerPoint) · (ADR-0496:) the tool's gateway key path as the cause of the
401 (refuted by the gateway's own "Expired Key" and on the wire) · any code that "renews" a key · a key-expiry
countdown (the tool learns the expiry only when refused) · (ADR-0495:) re-gating the SPI(t) population on a
baseline (Fuse's Record Count refutes it) · the completed-unbaselined TERM's value beyond blank-as-0 (the corpus cannot
discriminate; the operator's Fuse run would) · pinning the `ssi_uid152*` Large Test File saves as Fuse oracles
(different saves) · TP3's 0.53 (synthetic, no oracle) · (ADR-0492:) re-deriving BCWS on the crew
calendar instead of reading the series · a status date inside a merged block with unequal days (no oracle;
the booking calendar's working time is the pinned ruler) · a series exceeding the task's baseline cost
(left as recorded) · Type 4 / Type 10 as cost · an ELAPSED reading of a split gap (the file's own
LateStart arithmetic is working-minute; the corpus cannot discriminate on a moved start — the chosen reading
is pinned by name) · dropping the baseline timephased series from the converter (MPXJ exposes no setter;
priced at +7 % and left) · a task-level `<Splits>` model field (derived data) · regenerating a golden from the
intake path's CURRENT bytes (Revision 5 is not the file Fuse analysed) · a full regeneration that inherits
today's wall-clock resource values · the KPI-tile selector on /margin (ADR-0489) · a quantity-or-rate rule
for material / cost spans (ADR-0487) · a data-date floor (refuted twice) · the ribbon tiles' scopes · TP3's
ribbon 8 / Lags 3 (R-53) · the DCMA08 baseline basis (R-48) · Fuse's ACWP-to-time-now and updated3's BAC
(R-45) · R-20 / UI-03 (ADR-0477) · the HELD and CLOSED rows of the report.
⇢ Residuals registered, none taken: `test_driving_path_whole_schedule_browser.py:104` is WIDTH-RACY (#667;
never fix it by widening a wait) · `/settings` scrolls sideways (1,877 px console / apollo / jarvis, 1,641
daylight at 1,440; an over-wide `<select>`) · UID 5306's chain on the leveled SSI golden: the engine's
integer minutes read a 2:36 daily gap as 2 (8 of MS Project's 10:24) on a start already a day late ·
ADR-0489's own (the KPI selector; the callout collapsed; two charts at 569 px) · ADR-0488's (a saved model
the catalog cannot confirm reads "— not installed"; a fresh config's default model is an Ollama id) ·
ADR-0486's (`max_completion_tokens` as a second attempt; an Ollama `done_reason` disclosure; the
cross-check's `last_completion`) · ADR-0485's (the model dropdown probes with the SAVED token) · ADR-0483's
(a live-peer response cut at 5 s) · OR-11b · OR-11d · the working-minute axis · the hint bubble · ADR-0484's
in-grid rows.
⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; `pull_request_read` `get_status` returns
`pending / 0` on a fully green PR (the legacy API) — use `get_check_runs`; a `check_suite.completed`
event can carry a superseded `head_sha` — re-read the current head; a red cell on `main` for a tree
identical to the green PR head is the runner's claim — compare tree hashes first; the post-merge safety
check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER `git log origin/main..HEAD`. Review cover is still
absent — Codex quota EXHAUSTED through #672; the mutation batteries and the full gate are all this repo
gets.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md`
FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the roadmap by testimony tier,
pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every session (ADR-0393). `git fetch
origin` before you branch, number an ADR, or commit.
