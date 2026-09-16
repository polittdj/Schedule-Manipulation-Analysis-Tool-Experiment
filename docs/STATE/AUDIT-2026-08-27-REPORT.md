# POLARIS² full-tool audit (2026-08-27 → 2026-09-07) — consolidated report and repair roadmap, ordered by testimony risk (WP8 · ADR-0472)

This is the campaign's closing document. It consolidates every verdict the live ledger
(`docs/STATE/AUDIT-2026-08-27.md`, appended per work package under ADR-0440..0471) recorded, orders
what is still open by **what a wrong number would cost in testimony**, prices each open residual
(S / M / L) with its first executable step, and names what settles it. Nothing here is new evidence
except §4, whose figures were re-measured on this tree by a stated method that
`tests/guards/test_audit_report_wp8.py` recomputes on every run — a report that drifts behind the
code goes red by name, which is the discipline the campaign found the ledger itself needed (§4, the
`176`). Every row cites its ledger section and ADR; a row changes state only with an executable
proof (QC-1, ADR-0393).

## 0. How to read this

**Status vocabulary (the ledger's, unchanged):** CONFIRMED-FIXED · CONFIRMED-DEFERRED · CONFIRMED
(disclosed or documented, values kept) · REFUTED · NON-REPRODUCED · UNVERIFIABLE · MEASURED · PINNED ·
OBSERVED. The roadmap adds its own: **OPEN** (priced, a first step named) · **ASK** (the operator's
decision, the question lettered as in the kickoff) · **ORG** (organizational, not engineering) ·
**HELD** (measured and deliberately left, with what would reopen it) · **CLOSED-WP8** (closed by a
measurement made for this report) · **CLOSED** (closed earlier, registered so it is not re-chased).

**Testimony-risk tiers — the ordering key of §3:**

| tier | what a wrong item costs on the stand |
| --- | --- |
| **T1** | a FIGURE the analyst would cite is, or could be, WRONG — the engine, a metric basis, a CPM rule, a parity leg |
| **T2** | the figure is right but could be MISREAD — mislabelled, misattributed, a wrong unit, an unstated basis, a defaulted value that looks measured |
| **T3** | the RECORD — Law 1's transaction log, what the tool discloses about itself, the documents that describe it |
| **T4** | CONTROLS and RENDERING that could hide evidence or mislead a reader — a dead control, a race, an overflow, a stale header |
| **T5** | PROCESS — CI, instruments, tests that could not fail, figures of unknown provenance |
| **T6** | ORGANIZATIONAL — decisions that are not engineering's to make |

Within a tier, rows run from the cheapest to close to the dearest.

## 1. Verdict

The operator's 2026-08-27 directive — every interactive control driven with PASS and FAIL tests, a
report, a plan forward — was met by execution rather than inspection: a sitewide control census
(34 page states, 65 id'd controls, 358 id-less instances, 8 structural floor families), steppers
driven on a fake clock, the SRA grid driven with a real clipboard, the route population instrumented
(148 endpoints, none unreached, the 21 never-adverse routes driven adversely), the AI transaction
log refuted through the real `urllib` opener, and the six ledger highs plus the 27-row tail each
re-derived from the finder's line and probed with a check built to refute it.

**By the ledger's own tables (87 verdict rows, tabulated by the first bold verdict token in each row):
50 CONFIRMED-FIXED · 9 REFUTED · 5 PINNED · 4 CONFIRMED as disclosed or documented · 3 MEASURED ·
2 CLOSED · 1 NON-REPRODUCED · 1 UNVERIFIABLE row (four ids) · 3 builds (WP5) · the operator batches'
eight items (six fixed, one present-not-discoverable, one design page).** Every CONFIRMED-FIXED row
landed red-first with a mutation proof by name and an ADR; every REFUTED row cites its probe. The
operator's live defect (v1.0.221, "controls do nothing") was root-caused twice — a load-path
sanitizer that was real but not theirs, then the span/scale axis their screenshots exposed — and a
second operator defect (the diagonal header) turned out to be a tooltip anchor re-positioning every
Gantt element since July.

**What is still open, in one sentence per tier (the full pricing in §3):** T1 — (R-01 closed 2026-09-07,
ADR-0473) one parity-locked rounding rule awaiting an Acumen oracle, one census of 325 displayed
roundings to classify, the P6 baseline basis held with its disclosure, and the six rows the
multi-project oracle opened — Hard_File's resource-calendar CPM finish (R-44 closed 2026-09-07,
ADR-0474; the progress-semantics residual it exposed is R-55, the four unexplained bookings R-56), the updated3 cost ledger,
the BCWS residual, SPI(t)'s 0.02, the DCMA08 tile scope, MPXJ's zero-slack omission; T2 — thirteen page scripts that explain a render crash as a data
failure; T3 — two Law-1 record questions (the pre-consent catalog probe, a schema version), one
un-re-read parity wording, and two organizational disclosures; T4 — a new, attributed, sitewide
horizontal overflow (UI-03), the /analysis frozen pane at scale, one CI race, and five operator
asks on their own files; T5 — the instruments themselves are green, three prior residuals closed by
measurement this session; T6 — a license and a releasability determination that are not
engineering's.

## 2. The register — every ledger row, its verdict, what it carries forward

| row | where (WP · ADR) | verdict (the ledger's) | carried forward |
| --- | --- | --- | --- |
| **S1** | WP0 · ADR-0441 | CONFIRMED-FIXED | — |
| **S2** | WP0 · ADR-0441 | CONFIRMED-FIXED | — |
| **S3** | WP0 · ADR-0441 | CONFIRMED-FIXED | — |
| **S4** | WP0 · ADR-0441 | CONFIRMED-FIXED | — |
| **S5** | WP0 · ADR-0441 → WP1 · ADR-0442 | CONFIRMED-DEFERRED (M) then CONFIRMED-FIXED (windowed `paintRows`, 33×) | — |
| **UI-01** | WP1 · ADR-0442 (UI-01 re-diagnosed by ADR-0445 / HDR-03) | CONFIRMED-FIXED | — |
| **UI-02** | WP1 · ADR-0442 (UI-01 re-diagnosed by ADR-0445 / HDR-03) | CONFIRMED-FIXED | — |
| **M3-01** | WP2 · ADR-0443 | CONFIRMED-FIXED | — |
| **M3-02** | WP2 · ADR-0443 | CONFIRMED-FIXED | — |
| **M3-03** | WP2 · ADR-0443 | CONFIRMED-FIXED | — |
| **M5-01** | WP2 · ADR-0443 | CONFIRMED-FIXED | — |
| **M5-02** | WP2 · ADR-0443 | CONFIRMED-FIXED | — |
| **HDR-01** | operator defect · ADR-0444 / ADR-0445 | CONFIRMED-FIXED (HDR-02 was THE operator's defect) | — |
| **HDR-02** | operator defect · ADR-0444 / ADR-0445 | CONFIRMED-FIXED (HDR-02 was THE operator's defect) | — |
| **HDR-03** | operator defect · ADR-0444 / ADR-0445 | CONFIRMED-FIXED (HDR-02 was THE operator's defect) | — |
| **OBS** | operator defect · ADR-0445 | OBSERVED — the sticky controls bar over the sticky header at scroll top | R-25 (HELD, design question) |
| **M4-01** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **M4-02** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **M4-03** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **M4-04** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **M4-05** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **M4-06** | WP3 · ADR-0454 | CONFIRMED-FIXED | — |
| **CI-01** | WP4 · ADR-0455 | CONFIRMED — GitHub-side, ~70 min; attribution to a githubstatus incident UNVERIFIABLE | closed by the operator's answer (f); R-43 |
| **CI-02** | WP4 · ADR-0455 | REFUTED (50/50 main commits have a push run) | — |
| **RC-01** | WP4 · ADR-0455 | COMMITTED (the route-coverage instrument; 148 endpoints over the 139 floor) | R-40 (HELD: the instrument as a standing gate) |
| **RC-02** | WP4 · ADR-0455 → WP6b · ADR-0467 → WP7 · ADR-0469 | MEASURED (21 never-adverse · 3 never-2xx) → CLOSED (the three 2xx paths) → the 21 driven adversely: three CONFIRMED-FIXED, 18 PINNED | R-39 (the `workbench` 400 vs 422) |
| **HOOK-03** | WP4 · ADR-0455 | CONFIRMED-FIXED | R-16 (the intake channel warns on `main`) |
| **WF-01** | WP4 · ADR-0455 | CONFIRMED-FIXED | R-16 (the intake channel warns on `main`) |
| **WP5-A** | WP5 · ADR-0459 | BUILT (both folder-ask builds, the operator chose BOTH) and pinned | R-29 (the parent-folder question on `/` — the operator's read) |
| **WP5-B** | WP5 · ADR-0459 | BUILT (both folder-ask builds, the operator chose BOTH) and pinned | R-29 (the parent-folder question on `/` — the operator's read) |
| **WP5-G** | WP5 · ADR-0459 | BUILT (both folder-ask builds, the operator chose BOTH) and pinned | R-29 (the parent-folder question on `/` — the operator's read) |
| **CPM-01** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **CPM-02** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **MC-02** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **MC-03** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **MAN-01** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **REC-02** | WP6 · ADR-0463 | CONFIRMED-FIXED (six of six highs) | R-01 (evm's ACWP, WP6's own row) · R-05 (path_evolution's basis) |
| **CI-03** | ADR-0461 | CLOSED — root-caused (chartframe.js after `</main>`) and fixed | R-09 (the `.catch` conflation it left) |
| **T-01** | evening batch · ADR-0457 | MEASURED WORKING, NOT REPRODUCED — pinned | R-23 (ASK) |
| **I-01** | evening batch · ADR-0457 | ROOT-CAUSED to session population; the page names it | R-24 (ASK) |
| **CF-01** | evening batch · ADR-0462 | TWO DEFECTS, FIXED red-first (calendar days under a working-day label; two activities unnamed) | R-30 (ASK — does the working-day move read right) |
| **CPM-03** | WP6b · ADR-0467 | CONFIRMED-FIXED (the ADR-0391 floor under an MSO/MFO pin) | — |
| **CPM-04** | WP6b · ADR-0467 | CONFIRMED-FIXED (presentation: an activity-less file says so) | R-10 |
| **MF-03** | WP6b · ADR-0467 | CONFIRMED (critical) · REFUTED (negative_float) — doc fixed | — |
| **MF-04** | WP6b · ADR-0467 | CONFIRMED (doc) | — |
| **MF-06** | WP6b · ADR-0467 | REFUTED as a defect (the stored-flag basis is the Acumen-validated one) | — |
| **MF-08** | WP6b · ADR-0467 | CONFIRMED-FIXED (`round_half_up` at the 30 MetricResult sites) | R-03 (dcma14's two parity roundings) · R-04 (the sites outside `engine/metrics`, re-censused §4) |
| **MF-07** | WP6b · ADR-0467 | UNVERIFIABLE as filed (the round-3 detail did not survive) | R-06 (HELD) |
| **MF-09** | WP6b · ADR-0467 | UNVERIFIABLE as filed (the round-3 detail did not survive) | R-06 (HELD) |
| **MF-10** | WP6b · ADR-0467 | UNVERIFIABLE as filed (the round-3 detail did not survive) | R-06 (HELD) |
| **MC-08** | WP6b · ADR-0467 | UNVERIFIABLE as filed (the round-3 detail did not survive) | R-06 (HELD) |
| **MC-04** | WP6b · ADR-0467 | REFUTED as "silent" | — |
| **MC-05** | WP6b · ADR-0467 | CONFIRMED-FIXED (refuse by name) | — |
| **MC-06** | WP6b · ADR-0467 | REFUTED (identifiable guarantees hold) | — |
| **MC-07** | WP6b · ADR-0467 | CONFIRMED-FIXED (refuse by name) | — |
| **IMP-02** | WP6b · ADR-0467 | REFUTED as stated (tolerated gaps named) | — |
| **IMP-03** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **IMP-04** | WP6b · ADR-0467 | NON-REPRODUCED (no XER in the tree carries `status_code`) | R-07 (HELD) |
| **IMP-05** | WP6b · ADR-0467 | CONFIRMED — disclosed, values kept (P6 target dates are PLANNED dates) | R-02 (ASK b) |
| **IMP-06** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **MAN-02** | WP6b · ADR-0467 | CONFIRMED-FIXED (cited to the prior file) | — |
| **MAN-03** | WP6b · ADR-0467 | CONFIRMED-FIXED (wording) | — |
| **JS-02** | WP6b · ADR-0467 | REFUTED as a leak | — |
| **JS-03** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **JS-04** | WP6b · ADR-0467 | REFUTED by now | — |
| **JS-05** | WP6b · ADR-0467 | MEASURED, not removed (56 dead CSS tokens) | R-28 (HELD) |
| **JS-06** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **TST-02** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **TST-03** | WP6b · ADR-0467 | CONFIRMED-FIXED | — |
| **TX-01** | WP7 · ADR-0469 | CONFIRMED-FIXED (a closed error vocabulary) | — |
| **TX-02** | WP7 · ADR-0469 | PINNED | R-13 (the record's schema version / correlation — TX-02's key set moves with it) |
| **TX-03** | WP7 · ADR-0469 | REFUTED as a defect; DISCLOSED (the pre-consent catalog probe) | R-12 (ASK a) |
| **TX-04** | WP7 · ADR-0469 | PINNED | R-13 (the record's schema version / correlation — TX-02's key set moves with it) |
| **TX-05** | WP7 · ADR-0469 | REFUTED as a risk; PINNED (retention) | R-14 · R-15 (HELD) |
| **TX-06** | WP7 · ADR-0469 | PINNED | R-13 (the record's schema version / correlation — TX-02's key set moves with it) |
| **TX-07** | WP7 · ADR-0469 | CONFIRMED-FIXED (disclosure) | — |
| **UI-03** | WP8 · ADR-0472 (NEW, this report) | OBSERVED and ATTRIBUTED — every page scrolls horizontally at 1440 (headless): the hidden tooltip box | R-20 (CLOSED, ADR-0477) |
| **CI-04** | recorded 2026-09-04 (SESSION-LOG), not a ledger table row until WP8 | one strike (#632's docs-only head): the /driving-path header-row equality oracle read the two pages at different render states | R-32 (OPEN, S) |

The operator batches are registered by their ledger numbering: 2026-09-02 items 1 (the header
demote-on-zoom, CONFIRMED-FIXED; the blank-header banner UNKNOWABLE), 2 (target UIDs, FIXED),
3 (the One-Pager page PRESENT — a discoverability question), 4 (the /analysis DOM, FIXED: 1.8 M nodes
→ 26,926), 5 (field roles BUILT; the unscoped WBS pivot FIXED), 6 (/volatility on the design, DONE),
7 and 8 (the tier ladder, FIXED; Reset explained, NOT a defect); the 2026-09-03 evening batch (a)
UNKNOWABLE, (b) CLOSED, (c) MEASURED and improved (ADR-0458), (f) UNVERIFIABLE, and its three rows
T-01 · I-01 · CF-01 above.

## 3. The repair roadmap — ordered by testimony tier, then by cost

| # | tier | ledger row(s) | status | price | first executable step | what settles it |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | T1 | `evm.py`'s ACWP `actual_cost or 0.0` on a mixed cost-loaded population (WP6's own row) | CLOSED | — | the rule is the Bible's own (`sum(BCWPEV)/sum(ACWPAC)`, a blank evaluated as 0 — Fuse's evaluation, CPI 0.81 / 0.78 exact on Hard_File_updated / updated2); the started, budgeted activities with no actual cost now ride CPI/TCPI as count / population / offenders and the EVM page prints them (ADR-0473) | — |
| R-02 | T1 | IMP-05 — on a P6 XER the per-task baseline dates ARE the PLANNED (target) dates; disclosed by an import note, values kept | HELD | S | decided 2026-09-07 (ADR-0473): the planned-date basis and its disclosure stay — P6 itself shows those dates as BL dates while no baseline project is assigned; blanking HMI/BEI would remove a figure the source tool shows | a Fuse export on an XER settles the parity leg |
| R-03 | T1 | MF-08's residual in `dcma14.py`: the two parity-mode classifications `round(eff / mpd) < 0` and `> 44` use banker's rounding at exactly .5 (−0.5 d reads not-negative; 44.5 d reads not-high-float) | OPEN | S | a fixture whose total float is exactly −0.5 d and 44.5 d; pin what Acumen classifies for it (the operator's Acumen run) and switch to `round_half_up` only if the oracle says so — parity-locked classification, never a blind flip | the Acumen export for the half-day fixture |
| R-04 | T1 | MF-08's residual outside `engine/metrics`: 327 builtin `round()` call sites (census §4: web 161 · engine non-metrics 134 — two of them ADR-0474's plan-span roundings in `engine/cpm.py` · ai 18 · reports 10 · importers 4; top files `web/app.py` 54, `engine/sra.py` 44, `web/sra.py` 29, `engine/jcl.py` 28, `web/system.py` 23) | OPEN | M | classify the 325 by exposure with the census script (a figure that reaches a page or an export vs internal arithmetic); render /sra and /jcl on a half-day fixture and read each displayed rounding against `round_half_up`; fix family by family, red-first, parity unmoved | each family's rendered figure on the half-day fixture matches the stated rule |
| R-05 | T1 | `path_evolution`'s per-version critical list scores on pure-logic CPM while every other page reads the effective (stored-flag) basis — the page's forensic construction | HELD | S | state the basis on the page in one pinned sentence ("pure-logic CPM, not the stored Critical flag"); no figure changes | the operator's ruling that the page should read the effective basis instead |
| R-06 | T1 | MF-07 · MF-09 · MF-10 · MC-08 — UNVERIFIABLE as filed; nothing in the tree names them | HELD | — | no blind sweep; re-file each from the round-3 source with a mechanism and a line before any probe is built | the round-3 finder's original text |
| R-07 | T1 | IMP-04 — a P6 `status_code` the importer might mis-read; NON-REPRODUCED (the only XER in the tree carries none) | HELD | — | run the importer's status probe on a real P6 export that carries `status_code` | a P6 XER export from the operator |
| R-08 | T1 | measured-false or deliberately held: MC-01's parity leg · MF-05 · the ADR-0417/0419 fixtures · the `citations.reattach` pin · the evolution 0 % cell · `late_start` for a floored task (`LF − duration`, the start slack is real) · the change-effects deltas | HELD | — | listed so no session re-chases them; each carries its measurement in ADR-0463 / ADR-0467 | a new measurement that contradicts the recorded one |
| R-44 | T1 | Hard_File's CPM finish ran 42 days later than MS Project's stored finish (2026-12-17 vs 2026-11-05) — its crews sit on 16-hour and 24-hour calendars the base CPM did not model, and twelve activities carry a resource-leveling delay (ADR-0473) | CLOSED | — | closed 2026-09-07 (ADR-0474): execution plans schedule each WORK booking on the crew's calendar (FIXED_UNITS spans work / units, other types the duration), the leveling delay is elapsed time after the calendar admits the task, slack is measured on the task's calendar; MS Project's stored dates were the oracle — Hard_File / updated / updated2 within 1 d of the stored finish, Critical agreed 108 / 110 / 80 of 110 (was 54 / 59 / 73), Project2 / Project5 exact with every stored slack reproduced (65 / 65, 95 / 95), Net Finish Impact −134 = Fuse; updated3's −6 d is R-55, the four unexplained bookings R-56 | — |
| R-45 | T1 | Hard_File_updated3's BAC / BCWP read 133,400 / 59,340 where Fuse's ribbon reads 121,800 / 53,715, and Fuse's ACWP is to-time-now (64,105 vs the file's 63,763 on updated2) — no per-task cost oracle in the export (ADR-0473) | OPEN | M | read the Detailed Metric Report's per-activity cost columns if the export carries them, else ask for a per-task BAC / BCWP / ACWP export of updated3; diff by UID | the per-activity oracle |
| R-46 | T1 | BCWS on Hard_File_updated reads 16,150 where Fuse reads 16,000 — one activity straddling the status date on a 16-hour resource calendar, prorated on the project calendar (ADR-0473). **CLOSED 2026-09-15 (ADR-0492):** the Bible's PV (BCWS) is `sum(BCWSPV)` — each activity's BCWS as MS Project stores it, and the regenerated goldens (ADR-0491) carry exactly that series: the assignment's time-phased baseline cost (`TimephasedData` Type 5), which summed through the status date reads 16,000 / 64,240 / 110,440 on updated / updated2 / updated3 to the unit. The importer reads every valued block as a `CostPiece` (SCHEMA_VERSION 2.14.0), the engine sums a task's series (a block the status date falls inside prorated in working minutes of the booking's calendar — `cpm.booking_calendar`, the plan builder's own rule, now public) and accrues the budget no series carries by ADR-0473's linear rule (updated3's UID 257: 800 of baseline cost, no assignment series). The register's step was not taken as written: re-deriving MS Project's distribution on the crew calendar would have matched UID 187 (72 of 120 h → 3,600) and missed every contour the file records; reading the series matches by construction. Corpus census: ONE task moved (187: 3,750 → 3,600), every other golden and task unmoved; SPI on updated 1.04 → 1.05 = the ribbon; the EVM1 / EVM2 / Project goldens (no series) equal the old rule exactly. 18 mutants red by name (17 on the first pass; the one survivor an equivalent mutant below its guard, re-cut at the guard and red) | CLOSED | — | closed 2026-09-15 (ADR-0492) | — |
| R-47 | T1 | SPI(t)–Acumen reads 8.24 / 8.17 where Fuse reads 8.22 / 8.14 on the Large Test File / File2 (ADR-0473). **CLOSED 2026-09-15 (ADR-0495):** the Detailed Metric Report's SPI(t) column carries no per-activity value — only the total and a **Record Count, 717 / 726**, the one number nothing had read — and the engine's own sum of ratios over that count reproduces 8.22 / 8.14 exactly. The residual was the population: the engine required a baseline to admit a started activity; Fuse admits every started activity with a non-zero actual span and scores an unbaselined member as the formula's blank-as-0 term (UID 7260 in progress on both files; 7262 / 7551 completed on File2 — the workbook's own `Completed (w/o Baseline Duration)` = 2 names them; the zero-span milestone 7183 stays excluded). 18 Fuse SPI(t) oracles now pinned from the workbooks (all exact); the population pinned from the Record Count; the members disclosed by UID on the EVM page. Corpus census: 5 moved, all that class, none away | CLOSED | — | closed 2026-09-15 (ADR-0495) | — |
| R-48 | T1 | the DCMA tile "8. High Duration" carries IncludeComplete=true in the library where DCMA08 scores incomplete activities only; no Fuse figure in the repo discriminates (every Hard_File ribbon reads 0) (ADR-0473) | OPEN | S | a Fuse ribbon on a file with a completed activity of baseline duration > 44 d; pin whichever it reads | that ribbon figure |
| R-49 | T1 | MPXJ omits a ZERO `TotalSlack`: 62 of Fuse's 66 zero-float activities on Large Test File2 carry no stored slack, so `effective_total_float` falls back to the recomputed float for exactly the zero-slack tasks (ADR-0473). **CLOSED 2026-09-14 (ADR-0490):** the provenance was settled on the `.mpp` through the vendored MPXJ itself — the reader holds `0.0d` for all 62 (NULL for none; 786 zero slacks in memory, 0 literal zeros in the XML) — and the importer now infers the zero on a `Critical` activity whose element is absent when the file carries the element elsewhere. The register's red-first could not be the Fuse figure: on every fixture the recomputed float of those tasks is already exactly 0, so 66 / 2 were exact on the pristine tree (pinned so they cannot move); the red was the ONE file where the bases disagree — `Hard_File` UIDs 241 / 249 (480 / 360 min → 0; the float ratio 3.99 → 3.98) — and a synthetic file. 624 metric entries snapshotted on eight goldens: two moved, both those. Four stored-slack population pins re-baselined by exactly the inferred count (41 / 4 / 2 / 62), every inferred zero exact | CLOSED | — | closed 2026-09-14 (ADR-0490) | — |
| R-55 | T1 | progress semantics, not calendars: a STARTED activity is floored at its actual start (ADR-0391) so logic still pushes it later — updated3's completed UIDs 291–298 land 36 days after their actual finish — and a completed milestone's actual instant is snapped to the project calendar; updated3 reads −6 d, updated3_24hr +17 d (ADR-0474) | CLOSED | — | closed 2026-09-08 (ADR-0476): a COMPLETED activity (100 % and both actuals) is PINNED at both ends, in-progress work keeps ADR-0391's floor; the oracle was measured first — stored `Finish` == `ActualFinish` on 2,289 of 2,289 completed activities and stored `Start` == `ActualStart` on 2,601 of 2,601 started ones across six progressed goldens. updated3_24hr / updated4_24h +17 d → −2 d; engine-LATE disagreements 68 / 31 / 13 → 0; **no completed activity anywhere in the corpus is now scheduled past the date its file records** (50 / 21 / 13 / 11 → 0); Critical 62 → 70 and 96 → 103 of 110; Project2 / Project5 unmoved and still exact. updated3's finish widens −6 d → −13 d because the old engine's spurious lateness was masking R-56 — see R-56, whose row this session re-specified | — |
| R-56 | T1 | four Hard_File bookings the MSPDI cannot explain — UID 14 (200 % on a 24-hour task calendar, a 16-hour crew) spans 40 h for 24 h, UID 401 56 h for 40 h, UID 403 twelve working days for 4 days in every snapshot, UID 385 four bookings (two material); they put the three early snapshots one day early (ADR-0474). **RE-MEASURED 2026-09-08 (ADR-0476) and promoted from a snapshot nuisance to the whole remaining updated3 gap:** with R-55 closed it is what still holds updated3's finish 13 d early. It is a duration-CONTOUR defect on UNSTARTED work (`percent_complete == 0`), so no progress rule reaches it. updated3 has SEVEN chain heads (a disagreeing activity whose every predecessor already agrees) and 45 rows inherited from them; UID 385 is the LARGER driver, not 403 — MS Project spreads 385's 5,664 min over ~17 wd (333 min/d) where the booking rule gives ~6 (944 min/d), and 403's 1,920 min over ~14 wd (137 min/d) vs ~5 (384 min/d). Two of the seven heads are the day-boundary residual, not this row **CLOSED 2026-09-12 (ADR-0487):** the tally was executed against the `.mpp` itself (MPXJ 16.2.0, raw timephased work, splits): the engine's WORK legs are exact to the minute on both heads, and MS Project's task finish is the finish of a MATERIAL / COST booking the engine skipped — whose span no stored quantity determines (302's two bookings, different quantities and rates, share one 36 h span; 385's span 24 h and 125 h) but which the file RECORDS per assignment. The recorded window is now a leg of the execution plan (WORK bookings never; disclosed on `booking_span_driven`): updated3's finish −13 d → EXACT, within-a-day 60 → 103 / 110, stored slack 9 → 42 / 68, every other golden unmoved. UID 403 is a leveling SPLIT (R-60); UID 14 / 401 the same class. Fixture provenance settled: the committed fixture is the save Fuse analysed; the intake `.mpp` is a later re-save | CLOSED | — | closed 2026-09-12 (ADR-0487) | — |
| R-09 | T2 | the `.catch` conflation — 13 page scripts print "Failed to load the … data." from a catch that also swallows a RENDER throw (CI-03's residual; `path_evolution.js:515` the named instance) — a true figure hidden behind a false explanation | OPEN | M | one browser test that stubs `SFChartFrame.axisTitles` to throw on /cei and asserts the message names a render failure (red on this tree); then a shared helper that separates the fetch failure from the render throw, module by module, each byte-frozen script re-baselined and dated | the stub test green on each of the 13 modules |
| R-10 | T2 | CPM-04's presentation family — an activity-less FILE says so on eight surfaces; a FILTER that empties the scope stays I-01's disclosure (mutation M23) | CLOSED | — | pinned in ADR-0467; registered here so the two disclosures are not confused | — |
| R-11 | T2 | the WBS artboard's footnote wording ("duration-weighted percent complete", "planned-to-date") against the engine's COUNT-based SPI(t) and percent complete | CLOSED-WP8 | — | not ported (ADR-0471): the ES panel's read-me line states the count basis verbatim; a design mock is never a metric definition | — |
| R-50 | T2 | the library's same-named Metric History variants — Insufficient Detail™ (incomplete, no milestones: 22 vs the tile's 43), Merge Hotspot (Predecessors >2) (planned only: 125 vs 156), Total # Predecessor Lags (planned only: 2 vs 5) — are not exposed; a reader of the History report cannot find them in the tool (ADR-0473). **CLOSED 2026-09-16 (ADR-0499):** all three are published as their own metrics under the library's own row label **with the filter IN the name** (`Insufficient Detail™ (incomplete, no milestones)` · `Merge Hotspot (Predecessors >2, planned only)` · `Total # Predecessor Lags (planned only)`), in their own **Metric History variants** panel on `/ribbon` rather than as three more ribbon columns — the Ribbon and the Metric History are different reports, and a tile beside its variant in one matrix invites exactly the cross-report read this row exists to prevent. They ride the existing machinery (schedule-quality formula, `RibbonMetrics`, the click-drill, the catalog's new **Metric History** family, the help dictionary, the ribbon workbook), and the three same-stemmed tiles now name their variant in their own definitions. Pinned **UID-exact against Fuse's own per-activity X marks** in the Detailed Metric Report — 22 / 125 / 2 and 21 / 123 / 2, every mark, on the Large Test File / File2 — with the engine's populations equal to Fuse's own **Record Counts** (945 / 919 · 916 / 906 · 2 / 2). Red-first 8 of 11; mutation battery 14 / 14 by name (M11 survived the first pass and the survivor was a hole in the TEST: a header with no value beneath it survives the column being dropped); corpus census 15 goldens / 8,805 values, **zero moved**, 90 added; rendered in four themes at 1440 and 390 px with 0 px document overflow. **Two corrections to this row's own wording, measured:** `IncludeMilestone` is **false on BOTH** Insufficient Detail™ entries (only the tile's unused `TripwireFilter` carries true), so `IncludeComplete` alone separates them; and the tile's lag figure is **8, not 5**, and counts distinct ACTIVITIES where the variant counts LINKS | CLOSED | — | closed 2026-09-16 (ADR-0499) | — |
| R-51 | T2 | "Estimated Duration" reads 63 where Fuse reads 47 / 41 on Hard_File_updated2 / updated3 (ADR-0473) | OPEN | S | the library's inclusions for the Estimated Duration metric, then the X-marks by UID | the count |
| R-57 | T2 | assignment-level `LevelingDelay` (Hard_File UID 398's two bookings, UID 188) is not read — only the task's delay is honoured (ADR-0474) | OPEN | S | read `Assignment/LevelingDelay` onto the Assignment model and delay that leg alone; pin UID 398's stored finish 2026-08-27 11:59 | the stored finish of UID 398 |
| R-58 | T2 | a task calendar that is not 24-hour, intersected with a crew calendar, is approximated by the task calendar (Hard_File UID 14 on `Standard+Sat.` with the 16-hour crew) (ADR-0474) | OPEN | S | a calendar-intersection helper (weekdays ∩, segments pairwise ∩, holidays ∪) behind the plan builder; pin UID 14's stored span once R-56 explains its 40 h | the stored dates of a task with both calendars |
| R-60 | T2 | leveling SPLITS live only in the `.mpp`'s timephased data — Hard_File_updated3 UID 403 is two work pieces seven days apart (MPXJ `getWorkSplits`: 10-19 15:00 → 10-21 12:00, then 10-28 13:00 → 10-30 15:00 in the intake save), Hard_File's UIDs 14 / 401 the same class — and the MSPDI the converter writes carries no `TimephasedData` and no split element, so the engine runs the pieces contiguously (403: 10-23 vs the stored 11-05; its chain of four) (ADR-0487) **CLOSED 2026-09-14 (ADR-0491):** the fixture's own save was in git history (blob `1908d073`; task and assignment sections byte-identical to the golden — provenance by section diff, `tests/fixtures/golden/PROVENANCE.json`), and UID 403 on it is THREE pieces (14 h, eight working days of nothing, 12 h, 3.2 h of nothing, 6 h). The converter writes the timephased data, the importer reads a WORK booking's zero-work blocks as its `work_pieces`, and the engine carries every gap NO OTHER booking of the task works through in working minutes of the leg's calendar, forward and backward (the file's own LateStart arithmetic: 403's stored 11-25 13:48 and 12,888 min reproduced). The first cut honoured every gap and read Large_Test_File2 UID 5308's chain three weeks late — one of eight bookings delayed inside a fixed 228-h duration the other seven work through; the task-split test is the unit's finding. Measured: every Hard_File snapshot's project finish −1 d → EXACT, within-a-day 92 → 103 / 100 → 108 / 93 → 109 / 104 → 106, updated2's Critical 80 → 107, Large_Test_File 1569 → 1666 (slack 842 → 865, Critical 1682 → 1721), File2 1589 → 1687; 14 goldens regenerated from their own saves by splice; 18 / 18 mutants red by name. UID 14 spans its stored dates; 401's chain sits one day early on milestone 387's external link (R-64) | CLOSED | — | closed 2026-09-14 (ADR-0491) | — |
| R-61 | T2 | a FIXED_DURATION booking on an off-pattern crew spans the DURATION in crew minutes (ADR-0474's type rule) where MS Project keeps the task's window: updated3 UID 210's Content Developer booking is recorded over four project days and computed as 1.33 days on the 24-hour calendar — masked today by the completed-window pin (ADR-0476) and by the material leg (ADR-0487). **CLOSED 2026-09-16 (ADR-0500) — REFUTED, `engine/` untouched:** the census this row asked for was run over all 15 goldens and the POPULATION IS ONE TASK — UID 210 in five snapshots of one file, no unstarted witness and none without a project-calendar co-booking, so no golden can discriminate the rule. The row's arithmetic is right (1,920 crew minutes vs a 7,740-minute recorded window, the booking's window being the TASK's own) but its premise is mis-stated: the finish-placing PRIMARY leg is the `Standard`-calendar WORK leg of the Logistics Apprentice booking, landing on the stored finish exactly, and the crew leg — four days earlier — has never placed the task. Cutting ADR-0476's pin reads 210 **+1,260 min LATE**, not early; cutting ADR-0487's material leg moves 210 not at all (it moves the file's finish 12-12 → 12-06, so the cut has teeth). The proposed rule, implemented on a shadow engine, FIRES (ratio 1.0000 → 4.0312, span 1,920 → 7,740) and changes NOTHING: every figure on all 15 goldens byte-identical, its only effect a lost `booking_span_driven` disclosure. Generalized — MS Project has no separate scheduler for FIXED_DURATION — it moves **315 activities AWAY from their files' own stored finishes and ZERO toward**, because a split booking's window spans the leveling gaps ADR-0491 honours separately (UID 5231's window is 26,880 crew minutes SHORTER than the correct occupancy). The one alternative the row does not name — a fixed-duration leg on the TASK's axis — is 0 toward / 5 away. 10 pins shipped (census, witness, corrected premise, five stored-finish oracles, the ADR-0491 refutation witness, one labelled tripwire); battery 6 / 6 red by name, and it caught this unit's own first cut, a census that re-implemented the plan builder and was green under the mutant that breaks it | CLOSED | — | closed 2026-09-16 (ADR-0500) | — |
| R-64 | T2 | Hard_File's milestone 387 ("Business Performance Planning") hangs on an external predecessor link (`PredecessorUID` −65535) the MSPDI cannot resolve, so it sits one working day early (08-17 16:00 vs the stored 08-18 17:00) and the chain 400 → 399 → 401 → 402 → 403 → 404 inherits the day (ADR-0491: their spacing is now MS Project's to the minute) | OPEN | S | read the link's `CrossProject` / external-task fields if the MSPDI carries them, else treat a milestone whose only predecessor is external as stored-date driven and disclose it; red-first on 387's stored 08-18 17:00 | 387 and the chain 400 → 404 on their stored dates |
| R-62 | T3 | every absent `TotalSlack` the MPXJ writer dropped is a zero, completed tasks included (the ADR-0490 probe: NULL for none, 786 zeros in memory on Large Test File2, 634 of them completed tasks); the importer infers only the `Critical` ones, so the Data Explorer's `Total Slack (d)` reads `—` for a completed task where MS Project reads `0d` (ADR-0490) | OPEN | S | widen the inference to every absent slack when the file carries the element; census every metric that reads a completed task's slack first (today none does) | the Data Explorer column equal to MS Project's; `pytest -m parity` unmoved |
| R-12 | T3 | TX-03 — the model dropdown's catalog probe transmits a body-less, key-bearing `GET /v1/models` BEFORE the acknowledgment and is recorded (ADR-0402's design, disclosed) | CLOSED | — | decided 2026-09-07 (ADR-0473): kept — no schedule content, fired only by the operator's own endpoint choice from the approved list, recorded; gating would empty the dropdown until consent and protect nothing Law 1 protects | — |
| R-13 | T3 | the transaction record carries no schema version and no session correlation (by design: no CUI, no names) — a reader of the log years later cannot tell which shape they hold | OPEN | S | decide two fields (`v: 1`; a random per-process id — no names, no paths); re-baseline TX-02's ten-key pin deliberately, dated, and say so in the /settings retention sentence | the operator's ruling that a correlation id is acceptable (it carries no CUI) |
| R-14 | T3 | `~/.local/state` as the log's home on Windows — works, unidiomatic | HELD | S | a `%LOCALAPPDATA%` branch under a fake environment in a test, the POSIX default untouched | the operator's Windows machine |
| R-15 | T3 | two PROCESSES appending one log — the lock covers threads; the app is single-process | HELD | S | two processes × 1,000 records; count intact JSON lines; a single `O_APPEND` write per record if any line tears | the measured tear count |
| R-16 | T3 | the intake channel — a push to `main` under `00_REFERENCE_INTAKE/` only WARNS in CI (ADR-0455's sanctioned channel; ADR-0152) | ORG | — | the channel is the operator's own web upload; a hard fail would block their intake; keep the warning and the manifest guard | the operator's choice to close the channel |
| R-17 | T3 | DOC-01 — `docs/FINAL-REPORT.md`'s headline "COMPLETE and parity-green" blanketed what its own §6.B tempers (the 2026-08-13 plan's P5) | CLOSED-WP8 | — | the headline now names the gate and points at the residuals; `tests/web/test_docs.py` pins the phrase absent (red-first) and census §4 carries `final_report_headline_unqualified = 0` | — |
| R-18 | T3 | NUM-01 — "parity" language where a family is tolerance-accepted (the 2026-08-13 plan's P6) | OPEN | S | NOT re-read this session (UNVERIFIED): grep `docs/PARITY-REPORT.md` for each family whose test uses a tolerance and assert the doc says "within documented tolerance" beside it — a doc-lint, red where the word "exact" sits beside a tolerance test | the doc-lint green |
| R-19 | T3 | DISC-01 — the gateway host and the ITAR-tagged model id in a public repo and its history (ADR-0395's row: requires an authorizing official) | ORG | — | no engineering step precedes the releasability determination; after it, a history rewrite or a private repo | the releasability memo |
| R-59 | T3 | `off_project_calendars` and the /analysis calendar disclosure name task calendars only; the crews' calendars the CPM now honours (ADR-0474) are undisclosed on the page, so the analyst reads "single calendar" under a multi-calendar result | OPEN | S | list the crew calendars a plan uses beside the task calendars (uid-deduplicated) and pin the /analysis sentence on Hard_File | the sentence on the page |
| R-63 | T3 | the vendored converter's output depends on the CONVERSION date, not only the save: `CurrentDate`, and a resource's `MaxUnits` / `OverAllocated` / `AvailableFrom` / `AvailableTo` / `StandardRate` / `OvertimeRate` resolve at "now" from the availability and cost-rate tables (measured 2026-09-14: the same Hard_File_updated3 save converted 07-09 and 09-14 differs on exactly those 32 lines; `MaxUnits` feeds the resource-loading view's capacity) — two operators converting one file a month apart get different loading figures (ADR-0491) | OPEN | S | write the availability and cost-rate tables themselves (MSPDI `AvailabilityPeriods` / `Rates`) and have the importer resolve capacity at the STATUS date; red-first on a resource whose availability changes across the schedule | the loading view's capacity independent of the conversion date |
| R-20 | T4 | UI-03 (NEW) — every page's document scrolls horizontally ~280–300 px at a 1440-px viewport (`document.scrollingElement.scrollWidth` 1719 on `/`, 1734 with the family's strip): the hidden tooltip box `[data-sf-hint]::after` (340 px, `position:absolute; left:0; visibility:hidden`) on right-aligned hosts — the Reset-view button in every `.viz-controls` row — counts in scrollable overflow; `body` overflow-x is `visible`; headless hides the scrollbar the operator would see | CLOSED | — | closed 2026-09-08 (ADR-0477), pulled forward on the operator's instruction. Attribution proven by EXPERIMENT, not by reading: an element sweep sees nothing (the culprit is a pseudo-element), so injecting `[data-sf-hint]::after{content:none}` alone was the probe — it dropped `/`, `/driving-path`, `/evolution`, `/standards` and `/scorecards` from 1719 / 1734 / 1727 / 1720 to exactly 1440. The remedy collapses ONLY the resting box (`:not(:hover):not(:focus-visible)`), leaving the shown bubble, its fade and the 1.5 s delay byte-identical; `display:none` (this row's proposed step) was REJECTED as not animatable. All sixteen page × theme states now measure 1440, pinned red-first by `tests/web/test_no_horizontal_overflow.py`, which pins the mechanism as well as the symptom. Left, measured: an OPEN bubble near the right edge still widens the document — that needs edge-aware placement. This row's "75 hint hosts on /wbs" did not reproduce: /wbs carries 0 and does not overflow | — |
| R-21 | T4 | the /analysis residue at operator scale — Chromium's layout of ~700–800 sticky frozen cells (p95 83 ms; stripping them measured 50) | OPEN | M | a separate frozen pane behind a flag; ADR-0458's probe re-run on the 2,280-row corpus, links on and off | p95 ≤ 50 ms on the probe |
| R-22 | T4 | the WBS artboard's row click ("open this branch's activities") and its in-table encodings (percent bars, SPI(t) colour) — ADR-0471's named omissions | OPEN | S | `SFDrill.mark` per completion-table row in `wbs.js`'s fetch callback (a byte-frozen script: a dated re-baseline of the r11 digest and the DD-ledger line 133), the census drill floor for `/wbs/{name}` re-pinned, a browser drill test on a row | the drill test green; the census floor moved on the drill key only |
| R-23 | T4 | T-01 — "the timeline doesn't change when I tell it to" — MEASURED WORKING on v1.0.233+, NOT REPRODUCED, two pins added | HELD | — | decided 2026-09-07 (ADR-0473): the operator's box only — which page, which zoom, a screenshot of the dialog beside the header | the screenshot |
| R-24 | T4 | I-01 — the integrity page's findings, ROOT-CAUSED to the session population (the page now names its population and says "nothing to compare") | HELD | — | decided 2026-09-07 (ADR-0473): the operator's files only — which finding disappeared, on which two files, dropped as separate folders or carrying different Titles | the two files |
| R-25 | T4 | OBS — the sticky controls bar (`#pathControls.sf-freeze-bar`, z6) over the sticky header (`thead` z3 / frozen th z4) at the top scroll position | HELD | S | a z-order rule for the freeze bar against the header plus a browser pin at `scrollTop 0` that the grip is the top-most element | the operator's ruling whether the bar may cover the header |
| R-26 | T4 | the legal 25 % Size floor (a 120-px track) · /driving-path's empty-corridor hint · the Name column's 200-px CSS and ~53-px Chromium floors over the 28-px JS clamp | HELD | S | UI-map design questions, each documented and each a one-place change | the operator's ruling |
| R-27 | T4 | /evolution at operator scale — their session loads ONE file and the page needs two | HELD | — | watch on their next multi-version load; the TP5 long-span instrument covers the mechanism | a two-version load on their machine |
| R-28 | T4 | JS-05 — 56 CSS tokens matching nothing after crediting dynamic prefixes | HELD | S | ADR-0467's census script; remove; the four-theme render sweep before and after | the sweep identical before and after |
| R-29 | T4 | /forecast's chips with two files · /trend's chips · the parent-folder question on `/` | HELD | — | decided 2026-09-07 (ADR-0473): pinned in the repo by 24 passing layout, browser and folder-ask tests on two-file corpora; the operator's own files are the remaining reading | their report |
| R-30 | T4 | CF-01's follow-up — #635's /integrity working-day move for UID 152 | HELD | — | decided 2026-09-07 (ADR-0473): on the repo's Large Test File pair the counterfactual moves neither UID 152 nor the finish (0 working / 0 calendar days on the five-day calendar); the operator's #635 pair (2027 dates) is not in the repo | their reading on v1.0.236+ |
| R-31 | T4 | /onepager-compare's three rulings (swimlane move · threshold · one vs three slides) and its `.pptx` in PowerPoint (ADR-0465) | CLOSED | — | decided 2026-09-07 (ADR-0473): the rulings stand — a move is one removed plus one new, no slip threshold, one slide; the `.pptx` question moved to R-52 with an executable finding | — |
| R-52 | T4 | the exported `.pptx` — the one-pager AND the compare deck — does not load in LibreOffice 7 headless ("source file could not be loaded"); PowerPoint UNVERIFIED (not in the container) (ADR-0473) | CLOSED | — | **the finding was the INSTRUMENT, refuted 2026-09-15 (ADR-0498).** That sentence is what a LibreOffice with no PresentationML import filter says about *any* presentation: measured, the same install refuses a PowerPoint-authored `.pptx` (`00_REFERENCE_INTAKE/mpp/Politte Schedule Tool.pptx`) and a Microsoft-authored `.xlsx` with it, and `libreoffice-core` + `libreoffice-common` **without `libreoffice-impress`** is such an install — it was the container's. With the filter installed, LibreOffice 24.2.7.2 loads BOTH decks and parses every shape (1 slide · 54 custom shapes · 10 frames · 18 connectors · every label, the CUI banner top and bottom, and the selection-pane names). Pinned by `tests/reports/test_pptx_libreoffice_interop.py`, which SKIPS rather than accuses when the instrument cannot load the PowerPoint-authored control deck, and by the `browser` job, which installs the filter and treats a skip as a failure. The register's repair step was run anyway: `presProps` / `viewProps` / `tableStyles` were the whole structural delta against a PowerPoint-authored package and are now written (LibreOffice's import is byte-identical before and after — they change nothing it reads) | **PowerPoint itself stays UNVERIFIED** — no PowerPoint in any container we can reach; the operator opening either deck settles it (OR-21) |
| R-32 | T5 | CI-04 — the /driving-path header-row equality race: one strike on #632's docs-only head; the oracle read the embed and /path at different render/zoom states (extra timescale tick labels on one side) | OPEN | S | reproduce by an induced delay (the CI-03 method: hold a static asset); wait for both grids' settle signal before comparing header rows; a mutation that removes the wait must go red | the induced-delay test green |
| R-33 | T5 | the "other browser modules' expression-string waits" (ADR-0466 §3) | CLOSED-WP8 | — | census §4: 15 `wait_for_function` sites under `tests/`, 15 function strings, 0 expression strings — the residual is empty on this tree | — |
| R-34 | T5 | the runner's ordering that did not reproduce locally in 34 runs (ADR-0466) and Chrome 151's later-poll behaviour | HELD | — | only a runner-side trace settles it; no local step exists | a runner trace |
| R-35 | T5 | TEST-01 — chromium build numbers hard-coded in test modules (the 2026-08-13 plan's P3) | CLOSED | — | ADR-0406 and `tests/web/browser_chrome.py`; census §4: 0 path pins, 2 documentary mentions | — |
| R-36 | T5 | /volatility's four themes not each screenshotted (ADR-0451's residual) | CLOSED-WP8 | — | a four-theme DOM census this session: 13 `.panel` · 2 chips (the second on) · widest 1440 · 10 cf-bars · zero page errors, identical in every theme — a census, not screenshots, named as such | — |
| R-37 | T5 | /card's artboard read from the canvas markup, not executed (ADR-0470's residual) | CLOSED-WP8 | — | the canvas executed over loopback HTTP for `setScreen('ic')` in four themes: kicker · "Every version, on one card." · six version chips · the card · ⤓ EXCEL · footnote, zero page errors — the markup reading confirmed | — |
| R-38 | T5 | the ledger's "176 `round(` sites outside `engine/metrics`" (ADR-0467) — a number of unknown provenance | CLOSED-WP8 | — | not reproducible by four definitions on the ADR-0467 tree or this one (AST calls 325 · non-engine 193 · web+reports+importers 175 · web 161); replaced by the AST census the guard recomputes (§4) | — |
| R-39 | T5 | the `workbench` export answers 400 on an empty session where its five siblings answer 422 | OPEN | S | pin 422 on all six in `tests/web/test_rc02_adverse_paths.py` and flip the one status code | the pin green |
| R-40 | T5 | RC-01's route-coverage instrument runs only by hand (`SF_ROUTE_COVERAGE=…`) | HELD | S | run it on every full suite as a CI job and fail on a route that regresses to never-adverse | the instrument as a job |
| R-53 | T5 | TP3's 2026-06-12 ribbon values (Lags 3 · Insufficient Detail 8) were captured on the `.mpp`, whose in-progress percentages differ from the committed XML; no variant of either formula yields 8 on the XML (ADR-0473) | HELD | — | the battery keeps the XML's own pins; a Fuse run on the committed XML would settle which ribbon figure the XML earns | a Fuse run on the committed TP3 XML |
| R-54 | T5 | the `golden/ssi_uid152` Large Test File fixture is the underscore-named sibling `.mpp` (31 negative-float activities), not the Fuse-scored file (41) — it stays the SSI fixture; the Fuse oracles use fresh conversions under `golden/fuse_ltf/` (ADR-0473) | CLOSED | — | registered so no session re-chases the 31 vs 41; the provenance is in the oracle module's docstring | — |
| R-41 | T6 | LIC-01 — `LICENSE` is a placeholder | ORG | — | the rights-holder's choice; census §4 pins `license_placeholder = 1` so this report cannot outlive the fix silently | a real LICENSE |
| R-42 | T6 | the design migration queue — /compare (10) is a feature (M-L); /standards (ADR-0475), /scorecards (ADR-0484) and /margin (ADR-0489) shipped — the Control family is complete; 19 artboards remain (§6) | ORG | — | one page per session (the standing ask); /compare needs the cross-pair evidence ledger ("All five pairs × every edit") and a slip decomposition update by update that no page computes | the operator's order |
| R-43 | T6 | the blank-header banner (UNKNOWABLE) and the 08-26 incident's attribution (UNVERIFIABLE) | CLOSED | — | closed by the operator's answers of 2026-09-03; listed so nobody re-chases them | — |

## 4. Census — the figures this report states about the tree

Each row below is RECOMPUTED by `tests/guards/test_audit_report_wp8.py` by the method stated; a
figure the guard cannot re-derive fails the guard, and so does a figure the tree no longer matches.
Re-measure, never edit by hand.

| key | value | method |
| --- | --- | --- |
| `round_calls_outside_engine_metrics` | 328 | AST `Call` nodes whose callee is the bare name `round`, every `.py` under `src/schedule_forensics/` except `engine/metrics/` (44 files carry one); 325 → 327 on 2026-09-07 (ADR-0474): the plan builder's two span roundings in `engine/cpm.py` (`round(ratio * dur)`, the remaining-work scaling); 327 → 328 on 2026-09-14 (ADR-0491): the split gap's place in a scaled leg, `round(share * span)` in `_execution_plans` |
| `round_calls_inside_engine_metrics` | 46 | the same walk inside `engine/metrics/` (MF-08's `round_half_up` sites are not counted — they are not `round`); 45 → 46 on 2026-09-07 (ADR-0473): the ribbon's Negative Float now classifies the stored slack in whole days, Fuse's reading |
| `wait_for_function_expression_strings` | 0 | `wait_for_function(` sites under `tests/` whose literal predicate does not begin `() =>`, `(x) =>` or `function` (15 sites, all function strings) |
| `fetch_catch_failed_to_load_modules` | 13 | `web/static/*.js` files carrying the literal `Failed to load the` — the `.catch` conflation's population (R-09) |
| `evm_acwp_or_zero_sites` | 1 | occurrences of `actual_cost or 0.0` in `engine/metrics/evm.py` (R-01; 0 once fixed) |
| `dcma14_parity_round_sites` | 2 | occurrences of `round(` in `engine/metrics/dcma14.py` (R-03; the two parity-mode classifications) |
| `license_placeholder` | 1 | the first line of `LICENSE` contains `PLACEHOLDER` (R-41) |
| `chromium_build_path_pins_in_tests` | 0 | test files whose text matches TEST-01's own oracle, `chromium-` + three or more digits + `/` (R-35; the two remaining build-number mentions are documentary and carry no trailing slash) |
| `final_report_headline_unqualified` | 0 | `docs/FINAL-REPORT.md` contains `COMPLETE and parity-green` (R-17; tempered this session) |

**Provenance notes.** The ledger's "176 `round(` sites outside `engine/metrics`" (ADR-0467 §3) could
not be reproduced by any of four definitions on the ADR-0467 tree (`d61f6395`) or this one: AST calls
outside `engine/metrics` **325**; outside all of `engine/` **193**; `web` + `reports` + `importers`
**175**; `web` alone **161**. The figure is retired (R-38) and the AST census above replaces it — a
count with a method is a measurement, a count without one is a rumour. The expression-string waits
ADR-0466 §3 observed in "other browser modules" were three sites in `test_trend_design_browser.py`
on the pre-fix tree (`b8e8aa42`), converted by that ADR; every site on this tree is a function
string (R-33). The 2026-08-13 plan's P8 (`actual_start_driven` exposed but unconsumed) is consumed
by `engine/recommendations.py`, `web/driving.py`, `static/path.js` and `help.py` — closed, not
registered as a row.

**Measurements made for this report that closed rows (each in §3):** the four-theme DOM census of
/volatility (R-36); the canvas executed for the Schedule ID Card screen (R-37); the attribution of the
horizontal overflow to the tooltip pseudo-box (R-20, the new UI-03); the FINAL-REPORT headline
tempered under a red-first pin (R-17).

## 5. Operator questions — do not build on an assumed answer

| letter | question | the rows it decides |
| --- | --- | --- |
| (a) | TX-03: keep the model dropdown's catalog probe firing BEFORE the acknowledgment (a body-less `GET /v1/models` carrying the session's key, recorded), or gate it behind the acknowledgment too? | R-12 |
| (b) | IMP-05: on a P6 XER should HMI/BEI keep reading the PLANNED (target) dates as the baseline, or read N/A until a baseline project is exported? A Fuse export on an XER settles the parity leg. | R-02 |
| (c) | /onepager-compare: do the three rulings stand as stated on the page (swimlane move · threshold · one vs three slides) — and does its `.pptx` open in PowerPoint? | R-31 |
| (d) | #635's /integrity with UID 152: does the working-day move read right against the file's calendar? | R-30 |
| (e) | the standing asks: /forecast's chips with two files; the parent-folder question on `/`; /trend's chips; T-01 (which page, which zoom, a screenshot) · I-01 (which finding, which two files) · the /analysis lag on their box | R-23 · R-24 · R-29 |

UNKNOWABLE and closed by the operator's own answers: the blank-header banner, the 08-26 incident
(R-43).

**Decided 2026-09-07 (ADR-0473), on the operator's instruction to answer them from the evidence:**
(a) the probe stays — no schedule content, operator-initiated, recorded (R-12 CLOSED); (b) the
planned-date basis stays with its disclosure — P6 shows those dates as BL dates when no baseline
project is assigned (R-02 HELD on a Fuse-on-XER export); (c) the three rulings stand; the `.pptx`
does not load in LibreOffice 7 and PowerPoint is unverified (R-31 CLOSED, R-52 OPEN — **the LibreOffice half was REFUTED 2026-09-15: that
install had no presentation import filter and refused a PowerPoint-authored deck too; R-52 CLOSED,
ADR-0498. PowerPoint stays unverified**); (d) on the
repo's Large Test File pair UID 152 does not move — 0 working days on the five-day calendar; the
operator's 2027-dated pair is not in the repo (R-30 HELD); (e) the chips and the folder ask are
pinned by 24 tests on two-file corpora; T-01, I-01 and the /analysis lag are the operator's box
(R-23 / R-24 / R-29 HELD).

## 6. The Claude Design migration — where the queue stands

Design truth: `00_REFERENCE_INTAKE/references/design_handoff_mission_ops_redesign/Mission Ops Redesign
v2.dc.html`, 31 screens (`section[data-screen-label]`); method ADR-0451/0456/0460/0464/0465/0468/
0470/0471; rules `docs/DESIGN-SYSTEM.md` §9. The recipe now boots the Library screens over loopback
HTTP with the canvas's own `setScreen` keys (`wr` = WBS Rollup, `ic` = Schedule ID Card; the
registry lists `wb` Metric Workbench · `ml` Metric Lab · `wf` Segment Forecast · `ev` EVM · `sl`
Portfolio at Scale · `bs` Beyond the Schedule · `op` One-Pager Timeline).

**Done (11):** /volatility (04) · /cei (06) · /trend (05) · /forecast (09) · /onepager-compare
(Library One-Pager Timeline, built new on the design) · /performance (07) · /card (Library Schedule
ID Card) · /wbs (Library WBS Rollup, ADR-0471) · /standards (Control Standards and Execution
Indices, ADR-0475 — the first Control screen; the artboard's `· 16 / · 14 / · 10`
were measured to BE the page's own live counts) · /scorecards (Control Assessment Scorecards,
ADR-0484 — the second Control screen; the artboard's three-card grid holds the page's verbatim
four-column tables, which overflowed a third of the page in every theme until they laid out fixed) ·
/margin (Control Margin Dashboard, ADR-0489 — the third and LAST Control screen; the artboard's
status-date chips were DRIVEN and found to be a KPI selector, so they are served as navigation to
each version's analysis page; the glossary is the masthead's callout; the two chart panels share
the artboard's equal grid; the one mock sentence true of the engine is the erosion panel's read-me).

**Priced as a feature, not a migration:** /compare (10 What changed) — M-L (R-42).

**Remaining (19 artboards):** 00 Import · 01 Where we stand · 02 Can we trust the plan · 03 What
drives the date · 08 Who is overloaded · 11 What could go wrong · 12 The briefing · Forensics
Schedule Integrity · Library Beyond the Schedule · Library EVM · Library Metric Lab · Library Metric
Workbench · Library Portfolio · Library Segment Forecast · Mission Control · Program Portfolio ·
Setup AI Settings · Setup Groups and Filters · Setup Metric Dictionary. The Control family is
complete (ADR-0475 / 0484 / 0489); the next screen is the operator's order.

## 7. The earlier plans, reconciled

The 2026-08-13 remediation plan (`docs/STATE/AUDIT-2026-08-13-REMEDIATION-PLAN.md`) had eight items;
their state on this tree, by grep and by ADR: **P0 DISC-01** ORG, standing (R-19) · **P1 GW-02** done —
the banner is observed (ADR-0396) · **P2 SEC-01** done — `tests/web/test_sec01_host_allowlist_closure.py`
(ADR-0400) · **P3 TEST-01** done (ADR-0406; R-35) · **P4 HOOK-01** done — disguises and containers
(ADR-0399) · **P5 DOC-01** closed here (R-17) · **P6 NUM-01** open, UNVERIFIED this session (R-18) ·
**P7 LIC-01** ORG (R-41) · **P8 ENG-DEAD-01** closed — the channel is consumed (§4). The 2026-08-16
deep-dive's rows are the ledger's `CPM-* · MF-* · MC-* · IMP-* · MAN-* · JS-* · TST-* · REC-*`
families, every one registered in §2.

## 8. What this report does not claim

It does not claim the tool is defect-free: the census that found 358 id-less control instances and
21 never-adverse routes found them because it looked; the next instrument will find what this one
could not see. It does not claim parity beyond what `docs/PARITY-REPORT.md` says row by row
(R-18 is the check that the wording there matches the tests). It does not claim the operator's
machine matches this tree — five rows (R-23 · R-24 · R-27 · R-29 · R-30) wait on their files. And
it does not price what it could not measure: the four round-3 rows (R-06) and the runner's ordering
(R-34) stay unpriced on purpose.
