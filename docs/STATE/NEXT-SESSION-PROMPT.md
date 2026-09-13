# Kickoff prompt — next session

PR state (2026-09-12): **#670 is MERGED** — `main` is **`c31259fe`** (ADR-0486, v1.0.256; `main`'s runs
CI 1846 / installer-smoke 709 success). This session's three units — **R-56 / ADR-0487** (a material /
cost booking occupies the span the file records for it; updated3's finish 13 d early → EXACT), **OR-16 /
ADR-0488** (the gateway refused the operator's key; the tool now quotes the gateway's own reason and names
the credential it sent) and **OR-16b** (AI Settings shows one backend's fields at a time) — are a **draft
PR** from branch `claude/jolly-bohr-cs1rze`, **v1.0.257**; its number and checks are in the SESSION-LOG's
follow-up entry. **Always `git fetch origin` and read `git log origin/main` before trusting any sha written
here.** If that PR merged, restart the branch with `--prune` + `remote set-head` + `checkout -B`.

**The operator owes two things, neither blocking:** **V-4** — the gateway's own reason for refusing the
saved key (the step-2 PowerShell: the `WWW-Authenticate` header and the 401 body; the v1.0.257 banner
quotes the same text) — the key the gateway accepted on 09-11 at 21:58Z and refused on 09-12 needs the
CURRENT key from the AI Hub, and no code here renews it; and the `"ok": false` lines of the 09-11 morning
403 (`Get-Content "$env:USERPROFILE\.local\state\schedule-forensics\ai-transactions.jsonl" -Tail 40`) —
still the only evidence that decides whether a prompt-size guard is a unit. Do NOT build one without them.

## The design page is OWED. **Take `/margin` first.**

`/margin` (Control Margin Dashboard, `setScreen('mg')`) is the last Control screen and was not delivered
this session (the operator's two mid-session reports took the slot). Recipe: ADR-0471 / 0475 / 0484 —
execute the canvas over loopback HTTP, census the artboard in four themes, port the layout with every id,
form byte, panel, glyph and figure, refuse and NAME every mock claim the engine does not make, measure in
four themes with element rects and per-cell spill (never a panel's `scrollWidth` — jarvis's brackets),
a battery whose greens are read. Executing the canvas: `npm pack react@18.3.1 react-dom@18.3.1
@babel/standalone@7.29.0`, repoint `support.js`'s three `*_URL` constants at `./pkgs/<name>/package/...`
and blank the `*_SRI` constants, `python -m http.server --bind 127.0.0.1` in the copy, seed
`sfredux-screen` / `sfredux-guided=1` / `sfops-boot.skipNext=true` / `sfredux-theme` via
`add_init_script`, wait for `section[data-screen-label="…"]` visible (Babel needs ~10 s), census the DOM.
**Never touch `engine/` for a UI change.**

**Environment, re-measured 2026-09-12.** The clone arrives SHALLOW: `git log -1 -- tools/mpxj` lies
(`844e1d3a` this time). **`git fetch --unshallow origin` FIRST** (765 commits, 1.3 GB, ~1 min), confirm
it reads `42d92dc9`, then build. Install with `uv pip install --python /usr/local/bin/python3 --system -e
'.[dev]' build playwright` (never `playwright install`; `tests/web/browser_chrome.py::chrome_kwargs()`).
Re-`uv pip install -e` after a version bump or `__version__` lags. **`/root/.local/bin/ruff` 0.15.8
shadows CI's `/usr/local/bin/ruff` 0.16.7 on PATH — run both.** Keep the token-guardian's
`token_audit.py` in the SCRATCHPAD — `ruff check .` is whole-tree. No `openpyxl` here: read the Fuse
`.xlsx` exports with `zipfile` + `xml.etree` (this session did, to settle the fixture's provenance).
MPXJ is readable from Python-free Java: `javac -cp 'tools/mpxj/lib/*' --release 17` a probe against
`org.mpxj.*` — `Task.getWorkSplits()`, `ResourceAssignment.getRawTimephasedRemainingRegularWork()`,
`Resource.getType()` — the `.mpp` carries what the MSPDI flattens.

**Three steward traps, all measured — do not re-learn any of them:**
1. `pull_request_read` method **`get_status`** returns `{"state":"pending","total_count":0}` on a PR
   whose checks are ALL green — that is the LEGACY commit-status API. Use **`get_check_runs`**.
2. A `check_suite.completed` event can carry a **superseded** `head_sha`. Re-read the current head.
3. Check set: **eight** when `installer/**` changes (this PR does), **six** for docs-only.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read
`docs/STATE/HANDOFF.md` FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the
roadmap by testimony tier, pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every
session (ADR-0393). `git fetch origin` before you branch, number an ADR, or commit.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards on the design) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481
(OR-11e) · ADR-0482 (OR-12) · ADR-0483 (OR-13) · ADR-0484 (/scorecards on the design) · ADR-0485 (OR-14)
· ADR-0486 (OR-15; OR-14 corrected — the gateway) · **ADR-0487 (R-56 CLOSED — `Assignment.start` /
`finish`; a MATERIAL / COST booking's recorded window is a leg of the execution plan, WORK bookings
never; `_recorded_span` segment-aware; `CPMResult.booking_span_driven`; updated3 exact, 103 / 110
within a day, stored slack 42 / 68; corpus unmoved; the fixture is Fuse's file, the intake `.mpp` a
later re-save — NOT regenerated)** · **ADR-0488 (OR-16 — `ai/refusal.py`: the server's own reason
quoted, bounded; the banner names the credential sent with its length; word-bounded refusal; OR-16b —
`data-backend-only` + `settings.js::syncVisibility`, four themes measured).**

⇢ NEXT — **`/margin` FIRST (above)**, then the report's §3 in order, one row per unit of work
(red-first → mutation proofs by name → the full gate → an ADR → the state docs → a draft PR): **R-49** —
MPXJ omits a ZERO `TotalSlack` (62 of Fuse's 66 zero-float activities on LTF2 carry none): the importer
infers 0 when the file carries the element elsewhere and the task carries `Critical`; red-first on Fuse's
Zero Days Float 66 / 2 · R-46 (BCWS +150) · R-47 (SPI(t) 8.24 vs 8.22) · R-52 (the `.pptx` LibreOffice
refuses) · R-50 (expose the History variants) · **R-60** — leveling SPLITS live only in the `.mpp`'s
timephased data (updated3 UID 403: two work pieces seven days apart — the whole of updated3's remaining
per-activity gap, 12.8 d on that chain); the vendored converter can emit MSPDI `TimephasedData`
(`MSPDIWriter.setWriteTimephasedData`), the importer read the zero-work gaps, the engine honour them like
the leveling delay; the fixtures must then be regenerated from the SAME saves Fuse analysed · **R-61** —
a FIXED_DURATION booking on an off-pattern crew spans the duration in CREW minutes where MS Project keeps
the task's window (updated3 UID 210) · R-57 / R-58 / R-59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 ·
R-22 · R-32 · R-39.

⇢ Traps paid for, by name (2026-09-12 first): **the "contour" was a booking the engine SKIPPED — list
what the engine ignores before tuning what it computes** · **"the MSPDI cannot explain it" is a statement
about the converter's output, not the file — read the `.mpp` through MPXJ** · **a register's count is a
threshold artefact until re-derived (seven heads → five)** · **the intake `.mpp` is not the fixture's
file — provenance is settled by the Fuse report's own figure, never by dates** · **a set keyed on the
frozen `Calendar` model costs 420 hashes per 20 solves — the perf count-gate is the instrument, identity
keys the rule** · **a rig whose legs all sit on the project pattern cannot see a disclosure mutation** ·
**a 4 KB read limit dropped a long reason instead of bounding it** · **a page-wide substring matched a
field's TITLE text — AGAIN; read the element** · **one request made OUTSIDE the tool (PowerShell against
the gateway) settled tool-vs-gateway in one step — build the discriminator before the fix**. (2026-09-11
e:) **a fixed bug is evidence against the hypothesis it lived under** · **"raise the limit to the max" has
no number** · **the battery found a FALSE claim ("the deployed wrapping")** · **read a completion as
evidence, never `str()` it**. (2026-09-11 c/d:) **a diagnostic that names a PAGE is true and useless —
name the FIELD** · **a page-wide substring assertion the page's own form satisfies cannot fail** ·
**negative pins are green on the pristine tree by construction; prove them with a mutant**. (2026-09-11
b:) **read every green in a battery as a finding about the instrument** · **grep the artifact FIRST for a
string you assert absent** · **a rect cannot see text spilling inside a fixed cell** · **measure every
theme**. (Earlier, still live:) a green suite is not evidence the INPUTS are consistent · when a change
makes the engine honour a previously-ignored input, sweep for code whose correctness depended on it being
ignored · two errors can CANCEL · an inherited attribution is TESTIMONY · Playwright's virtual mouse
SURVIVES `goto()` — park it · an `assert` in `src/` is a house-style violation · a design mock's status
word, decomposition and export label are claims about the ENGINE · a mock that HIDES is proposing a
functionality change · MS Project's stored dates are a per-activity CPM oracle · `LevelingDelay` is
tenths of a minute · a booking rule proven on one file breaks another · MPXJ writes no zero ·
`Large_Test_File.mpp` ≠ `Large Test File.mpp`.

⇢ Measured-false / deliberately held — do NOT re-chase: a quantity-or-rate rule for material / cost
spans (no candidate survives both updated3 heads — ADR-0487) · a data-date floor (refuted twice) ·
regenerating the updated3 fixture from the intake `.mpp` (it is Revision 5; Fuse saw Revision 2) · the
ribbon tiles' scopes · TP3's ribbon 8 / Lags 3 (R-53) · the DCMA08 baseline basis (R-48) · Fuse's
ACWP-to-time-now and updated3's BAC (R-45) · R-20 / UI-03 (ADR-0477) · the HELD and CLOSED rows of the
report · the S-curve & finish-window residuals of earlier sessions.

⇢ Residuals registered, none taken: **`test_driving_path_whole_schedule_browser.py:104` is
WIDTH-RACY** (registered by #667 — a race with a mechanism, not a flake; never fix it by widening a
wait) · **`/settings` scrolls sideways — MEASURED: 1,877 px in console / apollo / jarvis, 1,641 in
daylight at a 1,440 viewport; an over-wide `<select>`; its own UI unit** · **ADR-0488's own:** under the
gateway a saved model the catalog cannot confirm still reads "— not installed" (Ollama's wording), and a
fresh config's default model is an Ollama id whatever the backend (the screenshot's dropdown) ·
**ADR-0486's own:** `max_completion_tokens` as a second attempt; an Ollama output-side disclosure from
`done_reason`; the cross-check's `last_completion` not surfaced · **ADR-0485's remaining:** the model
dropdown probes with the SAVED token · **ADR-0483's own** (a live-peer response cut at 5 s) · **OR-11b**
· **OR-11d** · the working-minute axis · the hint bubble · ADR-0484's in-grid rows.

⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; read a verdict on the FINAL head; a red cell on
`main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
after a squash-merge restart the branch with `--prune` + `remote set-head` + `checkout -B`, never amend
the squash; the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER
`git log origin/main..HEAD` (#666's correction). **Review cover is still absent** — Codex quota
EXHAUSTED through #670; the mutation battery and the full gate are all this repo gets.
