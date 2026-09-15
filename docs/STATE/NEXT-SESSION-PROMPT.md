# Kickoff prompt — next session

PR state (2026-09-14): **#671 is MERGED** — `main` is **`6708cbff`** (ADR-0487 / 0488, v1.0.257; `main`'s
runs CI 1849 / installer-smoke 712 success, read from the Actions API). This session's two units —
**/margin on the Claude Design layout / ADR-0489** (the LAST Control screen; the artboard's status-date
chips are a KPI SELECTOR and are served as navigation to each version's analysis page; the glossary is
the masthead's callout; the two chart panels share the artboard's equal grid) and **R-49 / ADR-0490**
(an absent `TotalSlack` on a `Critical` activity is the zero the MPXJ writer dropped — the importer
infers it; proven on the `.mpp` through MPXJ itself) — are a **draft PR** from branch
`claude/confident-johnson-py46p9`, **v1.0.258**; its number and checks are in the SESSION-LOG's
close entry. **Always `git fetch origin` and read `git log origin/main` before trusting any sha written
here.** If that PR merged, restart the branch with `--prune` + `remote set-head` + `checkout -B`.

**The operator owes three things, none of which arrived last session; none is blocking:** **V-4** — the
gateway's own reason for refusing the saved key (the step-2 PowerShell: the `WWW-Authenticate` header
and the 401 body; the v1.0.257 banner quotes the same text); **whether a fresh NASA AI Hub key** made the
gateway catalog load (Opus in the Model dropdown); and the `"ok": false` lines of the 09-11 morning 403
(`Get-Content "$env:USERPROFILE\.local\state\schedule-forensics\ai-transactions.jsonl" -Tail 40`) —
still the only evidence that decides whether a prompt-size guard is a unit. Do NOT build one without them.

## R-60 is FIRST — and its plan changed: the save Fuse analysed is in git history

**R-60** — leveling SPLITS live only in the `.mpp`'s timephased data (Hard_File_updated3 UID 403: two
work pieces seven days apart — MPXJ `getWorkSplits` 10-19 15:00 → 10-21 12:00, then 10-28 13:00 →
10-30 15:00; the whole of updated3's remaining per-activity gap, 12.8 d on that chain; Hard_File's
UIDs 14 / 401 the same class). Last session's reconnaissance, all measured:
1. **The Revision-2 `Hard_File_updated3.mpp` Fuse analysed IS in git history** —
   `git show af4d154f:00_REFERENCE_INTAKE/mpp/Hard_File_updated3.mpp` (uploaded 2026-07-09; deleted
   `b2517780`; re-uploaded `dcacbf44` on 07-15 as Revision 5, the intake file today). ADR-0487's
   "NOT regenerated — the same save is not available" premise is LIFTED: the fixture CAN be
   regenerated from the same save WITH timephased data. Prove provenance the ADR-0487 way first
   (Fuse's Forensic Analysis Report records 403 at the fixture's 11-05 09:12 — the Revision-2 conversion
   must reproduce that stored date byte-for-byte before it replaces the golden).
2. The vendored MSPDIWriter 16.2.0 has **`setWriteTimephasedData(boolean)`** and
   `setGenerateMissingTimephasedData(boolean)` (`javap -cp 'tools/mpxj/lib/*' org.mpxj.mspdi.MSPDIWriter`).
   The converter is `tools/mpxj/MpxjToMspdi.java::convert()` — one `new MSPDIWriter().write(project,
   output)`; `setup.sh` / `setup.ps1` rebuild `classes/`. Price the output growth on the Large Test
   Files (1,723 activities) before flipping it for every ingest, and keep `--server` mode's
   heap in view.
3. The importer's assignment parse is `importers/mspdi.py::_parse_assignments` (~line 1007); the
   engine's leveling-delay path is `engine/cpm.py` ~1726 / 1870 / 1947 with `_task_shape` /
   `_recorded_span` / `_LegShape` / `_Exec` (ADR-0487 added the recorded-window leg there — the
   split gaps are the next leg kind, honoured like the leveling delay).
4. Red-first target unchanged: 403's stored 2026-11-05 09:12 on the SAME save; success = 403 and its
   chain within a day, Hard_File's 14 / 401 spans, everything else unmoved (the stored-dates oracle's
   `finish_1d` floors and `tf_exact` pins are the corpus instrument — re-pin only with a reason).

**Environment, re-measured 2026-09-14.** The clone arrives SHALLOW — **`git fetch --unshallow origin`
FIRST** (58 s), confirm `git log -1 -- tools/mpxj` reads `42d92dc9`, then build. Install with
`uv pip install --python /usr/local/bin/python3 --system -e '.[dev]' build playwright` (never
`playwright install`; `tests/web/browser_chrome.py::chrome_kwargs()`). Re-`uv pip install -e` after a
version bump or `__version__` lags. **`/root/.local/bin/ruff` 0.15.8 shadows CI's `/usr/local/bin/ruff`
0.16.7 on PATH — run both.** Keep the token-guardian's `token_audit.py` in the SCRATCHPAD (`ruff check
.` is whole-tree). No `openpyxl`: read the Fuse `.xlsx` with `zipfile` + `xml.etree` (the Metric History
harness `tests/parity/test_fuse_metric_history_oracle.py` has `_load_workbook`). MPXJ from Python-free
Java: `javac -cp 'tools/mpxj/lib/*' --release 17` a probe against `org.mpxj.*` — last session's 40-line
`SlackProbe` settled R-49's provenance in a minute. A `.pth` editable install lets `PYTHONPATH` shadow
the package for a mutation battery — assert the imported module IS the copy every time anyway.

**Three steward traps, all measured — do not re-learn any of them:**
1. `pull_request_read` method **`get_status`** returns `{"state":"pending","total_count":0}` on a PR
   whose checks are ALL green — the LEGACY commit-status API. Use **`get_check_runs`**.
2. A `check_suite.completed` event can carry a **superseded** `head_sha`. Re-read the current head.
3. Check set: **eight** when `installer/**` changes (this PR does), **six** for docs-only.

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read
`docs/STATE/HANDOFF.md` FIRST (auto-injected), then `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3 — the
roadmap by testimony tier, pinned by `tests/guards/test_audit_report_wp8.py`. QC-1/QC-2 bind every
session (ADR-0393). `git fetch origin` before you branch, number an ADR, or commit.

⇢ WHAT'S DONE — do not re-open. WP0–WP8 (ADR-0440..0472) · ADR-0473 (R-01) · ADR-0474 (R-44) ·
ADR-0475 (/standards) · ADR-0476 (R-55) · ADR-0477 (R-20 / UI-03) · ADR-0478 · ADR-0481 (OR-11e) ·
ADR-0482 (OR-12) · ADR-0483 (OR-13) · ADR-0484 (/scorecards) · ADR-0485 (OR-14) · ADR-0486 (OR-15) ·
ADR-0487 (R-56) · ADR-0488 (OR-16 / OR-16b) · **ADR-0489 (/margin on the design — the Control family
COMPLETE; `_solvable_versions_keyed`, `_margin_cursor_strip`, `cd-grid-11`, `cd-callout`; the KPI
selector, the confirm card, ▦ DATA, the two false SRA sentences, the verdict pill and the band toggle
refused by name)** · **ADR-0490 (R-49 CLOSED — `_stored_slack_minutes(zero_when_absent=)` bounded by
`file_carries_slack and stored_critical`; Hard_File 241 / 249 480 / 360 → 0; float ratio 3.99 → 3.98;
four stored-slack population pins re-baselined by the inferred count; ADR-0430's teeth pin re-aimed;
R-62 registered)**.

⇢ NEXT — **R-60 FIRST (above)**, then the report's §3 in order, one row per unit of work (red-first →
mutation proofs by name → the full gate → an ADR → the state docs → a draft PR): R-46 (BCWS +150) ·
R-47 (SPI(t) 8.24 vs 8.22) · R-52 (the `.pptx` LibreOffice refuses) · R-50 (expose the History
variants) · **R-61** (a FIXED_DURATION leg on an off-pattern crew — updated3 UID 210) · R-57 / R-58 /
R-59 · **R-62** (every absent slack the writer dropped is a zero, completed tasks included — the Data
Explorer's `Total Slack (d)` reads `—` where MS Project reads `0d`; census the consumers of a completed
task's slack first) · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. **The design
queue is 19 artboards** — the operator's order picks the next screen (§6 lists them; the Control
family is done).

⇢ Traps paid for, by name (2026-09-14 first): **a register's red-first can be impossible on every
fixture you own — census the corpus for the case that discriminates before writing the pin** · **a
"teeth" pin ages with the engine (ADR-0430's phantom set stopped recomputing negative at ADR-0474 and
stayed green for two months) — re-derive every pin that cites the OLD behaviour as its reason** ·
**settle a converter's behaviour on the binary (`javap` + a probe), not on its output** · **DRIVE a
mock's chips before naming them — a census records what is there, only a driver records what it
does** · **a chip-effect test that loops over the chips it finds passes on a page with none** ·
**"Where it lands" is the chrome's own chapter link (grep the artifact first — the third time)** ·
**`helper() in page` proves the embedding, not the helper** · **`json.dumps` rewrites a fixture's
serialisation — look at the golden's diff before committing it** · **stop before the unit that will
not fit**. (2026-09-12:) **the "contour" was a booking the engine SKIPPED** · **"the MSPDI cannot
explain it" is a statement about the converter's output, not the file** · **a register's count is a
threshold artefact until re-derived** · **the intake `.mpp` is not the fixture's file — provenance is
settled by the Fuse report's own figure** · **a set keyed on the frozen `Calendar` model costs 420
hashes per 20 solves** · **a rig whose legs all sit on the project pattern cannot see a disclosure
mutation** · **a 4 KB read limit dropped a long reason instead of bounding it** · **a page-wide
substring matched a field's TITLE text** · **one request made OUTSIDE the tool settled tool-vs-gateway
in one step**. (Earlier, still live:) a fixed bug is evidence against the hypothesis it lived under ·
"raise the limit to the max" has no number · read a completion as evidence, never `str()` it · a
diagnostic that names a PAGE is true and useless — name the FIELD · negative pins are green on the
pristine tree by construction; prove them with a mutant · read every green in a battery as a finding
about the instrument · a rect cannot see text spilling inside a fixed cell · measure every theme · a
green suite is not evidence the INPUTS are consistent · two errors can CANCEL · an inherited
attribution is TESTIMONY · Playwright's virtual mouse SURVIVES `goto()` — park it · an `assert` in
`src/` is a house-style violation · a design mock's status word, decomposition and export label are
claims about the ENGINE · a mock that HIDES is proposing a functionality change · MS Project's stored
dates are a per-activity CPM oracle · `LevelingDelay` is tenths of a minute · MPXJ writes no zero ·
`Large_Test_File.mpp` ≠ `Large Test File.mpp`.

⇢ Measured-false / deliberately held — do NOT re-chase: the KPI-tile selector on /margin (a state the
page does not have; priced in ADR-0489) · the wider zero-slack inference for completed tasks (R-62,
registered, not made) · a quantity-or-rate rule for material / cost spans (ADR-0487) · a data-date floor
(refuted twice) · the ribbon tiles' scopes · TP3's ribbon 8 / Lags 3 (R-53) · the DCMA08 baseline basis
(R-48) · Fuse's ACWP-to-time-now and updated3's BAC (R-45) · R-20 / UI-03 (ADR-0477) · the HELD and
CLOSED rows of the report · the S-curve & finish-window residuals of earlier sessions.

⇢ Residuals registered, none taken: **`test_driving_path_whole_schedule_browser.py:104` is WIDTH-RACY**
(registered by #667 — a race with a mechanism, not a flake; never fix it by widening a wait) ·
**`/settings` scrolls sideways — MEASURED: 1,877 px in console / apollo / jarvis, 1,641 in daylight at a
1,440 viewport; an over-wide `<select>`; its own UI unit** · **ADR-0489's own:** the KPI selector; the
callout collapsed where the mock's is open; two charts at 569 px each (⛶ ENLARGE gives either the
viewport) · **ADR-0488's own:** under the gateway a saved model the catalog cannot confirm reads "— not
installed", and a fresh config's default model is an Ollama id whatever the backend · **ADR-0486's
own:** `max_completion_tokens` as a second attempt; an Ollama output-side disclosure from `done_reason`;
the cross-check's `last_completion` not surfaced · **ADR-0485's remaining:** the model dropdown probes
with the SAVED token · **ADR-0483's own** (a live-peer response cut at 5 s) · **OR-11b** · **OR-11d** ·
the working-minute axis · the hint bubble · ADR-0484's in-grid rows.

⇢ Steward posture: draft PRs the OPERATOR merges (never mark ready, never merge, never approve); eight
checks when `installer/**` changes, six for docs-only; read a verdict on the FINAL head; a red cell on
`main` for a tree identical to the green PR head is the runner's claim — compare tree hashes first;
after a squash-merge restart the branch with `--prune` + `remote set-head` + `checkout -B`, never amend
the squash; the post-merge safety check is `HEAD^{tree}` vs `origin/main^{tree}`, NEVER
`git log origin/main..HEAD` (#666's correction). **Review cover is still absent** — Codex quota
EXHAUSTED through #671; the mutation batteries and the full gate are all this repo gets.
