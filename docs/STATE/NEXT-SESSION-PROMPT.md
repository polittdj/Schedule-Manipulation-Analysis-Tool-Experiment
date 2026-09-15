# Kickoff prompt — next session

PR state (2026-09-15 07:47Z): **#674 is MERGED** — `main` is **`9a9e400e`** (ADR-0492, v1.0.260; tree-identical to the PR head `ca1d35d4`, which read eight of eight checks green). `main`'s own runs for the squash (CI 1860 / installer-smoke 723) were in progress at the close — read them first. The branch `claude/exciting-curie-n0wghm` was restarted on the squash; the merge record itself is a docs-only draft PR from it (its number in the SESSION-LOG's merge entry's follow-up, if any). **Always `git fetch origin` and read `git log origin/main` before trusting any sha written here.** After the operator merges that record, restart the branch with `--prune` + `remote set-head` + `checkout -B`; the next unit is **R-47**.

**The operator owes three things, none blocking:** **V-4** (the gateway's own refusal reason — the step-2
PowerShell: `WWW-Authenticate` and the 401 body; the v1.0.257 banner quotes the same text); whether a fresh
NASA AI Hub key made the gateway catalog load; and the `"ok": false` lines of the 09-11 morning 403
(`Get-Content "$env:USERPROFILE\.local\state\schedule-forensics\ai-transactions.jsonl" -Tail 40`) — still
the only evidence that decides whether a prompt-size guard is a unit. Do NOT build one without them.

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
**ADR-0492 (R-46 CLOSED — this session)**.
⇢ NEXT — the report's §3 in order, one row per unit of work (red-first → the per-task toward/away census
across EVERY golden before the ADR → mutation proofs by name → the full gate → an ADR → the state docs →
a draft PR): **R-47** (SPI(t) 8.24 vs 8.22) · **R-52** (the `.pptx` LibreOffice
refuses) · **R-50** (expose the History variants) · **R-61** (a FIXED_DURATION leg on an off-pattern crew —
updated3 UID 210) · **R-57** (an assignment's OWN leveling delay — Hard_File UID 398's RA 277 is a split ON a
delayed assignment: its gap is honoured since ADR-0491, its delay is not; UID 188 on updated2) · **R-58** ·
**R-59** · **R-64** (Hard_File milestone 387 hangs on an external predecessor, UID −65535 — the one working
day the chain 400 → 404 still sits early; their spacing is MS Project's to the minute) · **R-63** (the
converter resolves `CurrentDate`, `MaxUnits`, `AvailableFrom/To` and the rates at CONVERSION time —
`MaxUnits` feeds the loading view) · **R-62** (in #672's register: every absent slack the writer dropped is
a zero, completed tasks included) · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The
design queue is 19 artboards — the operator's order picks the next screen (§6 lists them).
⇢ Traps paid for, by name (2026-09-15 first): **a register's "first executable step" is a hypothesis
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
⇢ Measured-false / deliberately held — do NOT re-chase: (ADR-0492:) re-deriving BCWS on the crew
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
