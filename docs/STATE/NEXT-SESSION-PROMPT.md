# Kickoff prompt — next session

**OR-20 is SHIPPED (ADR-0497, v1.0.265) — do not re-open.** The 32-version Ask-the-AI answer tabled a "driving-path finish" of 2028-02-22 for `USA IPMR Format 6_January 2024.mpp` where MS Project shows 2026-05-07, and the model's own memo blamed a routine that "populated the focus finish with the network finish". **Measured on the operator's own IMS in the repo (`ssi_uid152`): refuted** — the builder read the focus's OWN early finish (2026-10-02 = its stored Finish = SSI's export), two years from the network finish (2028-09-28). **The real defect:** drivers measured on the file's stored dates (SSI's axis) with the engine's logic-only finish printed beside them, unlabelled, next to a network-finish series of the same shape; the two disagree on 50 of 1,723 activities on that IMS. Now the line carries the stored Finish, discloses the logic-only finish with its working-day gap only where they disagree (compared on the project axis), says whose date it is, and the movement census counts the disagreeing versions. Red-first 8 / 10, two SSI oracles in `-m parity`, mutation 7 / 7, `-m parity` 118 / 0 on the pristine tree. **The operator owes, not blocking:** the Jan 2024 DRIVING-PATH SERIES line from the original session (cited facts under the answer, or `/export/{fmt}/ask`), or the same question re-asked on v1.0.265; and a decision on OR-20b (a stored project finish beside the CPM one in the finish series) / OR-20c (the focus's stored Total Slack per line). **`main`'s runs for `69607e3b` (#681) are read: CI 1878 SUCCESS; installer-smoke has no run (docs-only, path-filtered).** First: OR-20's draft PR **#682** (head `c942e741`; eight checks); after the operator merges, restart the branch with `--prune` + `remote set-head` + `checkout -B`. **Always `git fetch origin` and read `git log origin/main` before trusting any sha written here.** Everything below OR-20 is unchanged: OR-19 / OR-18 / R-47 / R-46 / R-60 are CLOSED or SHIPPED as stated; the next §3 unit is **R-52**.

**Run the session-token-guardian's `scripts/token_audit.py` as the FIRST action** (copy it to the scratchpad — `ruff check .` is whole-tree) and before each operator prompt.

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
MERGED) · ADR-0496 (OR-19 — OR-17 §4 answered and OR-17 CLOSED; #680 MERGED) · **ADR-0497 (OR-20 —
the driving-path series on the stored Finish; the model's self-diagnosis refuted; this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away census
across EVERY golden before the ADR → mutation proofs by name → the full gate → an ADR → the state docs →
a draft PR): **R-52** (the `.pptx` LibreOffice
refuses) · **R-50** (expose the History variants) · **R-61** (a FIXED_DURATION leg on an off-pattern crew —
updated3 UID 210) · **R-57** (an assignment's OWN leveling delay — Hard_File UID 398's RA 277 is a split ON a
delayed assignment: its gap is honoured since ADR-0491, its delay is not; UID 188 on updated2) · **R-58** ·
**R-59** · **R-64** (Hard_File milestone 387 hangs on an external predecessor, UID −65535 — the one working
day the chain 400 → 404 still sits early; their spacing is MS Project's to the minute) · **R-63** (the
converter resolves `CurrentDate`, `MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time —
`MaxUnits` feeds the loading view) · **R-62** (in #672's register: every absent slack the writer dropped is
a zero, completed tasks included) · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The
design queue is 19 artboards — the operator's order picks the next screen (§6 lists them).
⇢ Traps paid for, by name (2026-09-15 (e) first): **a model's memo about its own error is testimony** — measure the mechanism on the real file before adopting it, and build the alleged defect as a mutant · **two per-version date series of one shape in one prompt get cross-wired** — say whose date each line carries · **drivers and the finish beside them must share an axis** · **"do two instants disagree" is a project-axis question** — `working_minutes_between(Fri 17:00, Mon 08:00)` reads 480 on a segment-less calendar · **rebuild the wheel after the LAST edit** · **the transaction log cannot replay a prompt** (Law 1) — the cited facts under the answer and the ask export are the record · (2026-09-15 earlier:) **a verdict quoted on the page is evidence** — a server cannot call an
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
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0496:) the tool's gateway key path as the cause of the
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
