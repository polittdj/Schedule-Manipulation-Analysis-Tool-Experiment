# Handoff — 2026-09-16 (R-50 CLOSED (ADR-0499): the library's same-named **Metric History variants** are exposed as their own metrics — each under the library's own row label with the filter IN the name, in their own panel so a tile and its variant are never read across; pinned UID-exact against Fuse's own per-activity marks on the Large Test File / File2; v1.0.267)

STATUS (current) — `main` @ **`9cb46317`** (#685, the docs-only merge record of #684 + R-50 recon; tree-identical to its head `4aeaabc5`; merged 03:21:51Z). Before it `93593ef5` (#684 — R-52, ADR-0498, v1.0.266), whose own `main` runs CI 1886 (35044973862) and installer-smoke 741 (35044973863) were READ and BOTH SUCCESS last session. **`main`'s own run for `9cb46317` — CI 1890 (35051509437) — was IN PROGRESS at this session's start; it was read as it went and then read to CONCLUSION: `status: completed`, `conclusion: SUCCESS`, all five jobs, completed 04:07:52Z (`cui-guard` 03:22:10Z · `browser` 03:38:14Z, the R-52 interop gate run-and-NOT-skipped on `main` itself, 3 s · `floor` 03:47:19Z with its parity gate · `test (3.11)` / `test (3.13)` last). Nothing about `9cb46317` is outstanding.** No `installer-smoke` run exists for `9cb46317` and that absence is CORRECT (docs-only; `installer-smoke.yml` is path-filtered to `installer/**`). Branch `claude/polaris-r50-audit-xi4ow6` was restarted on `9cb46317`. Highest ADR **0499**. Version **1.0.267**. QC-1/QC-2 bind every session — ADR-0393.

**What landed — R-50, the next row of the report's §3.** The register said three library metrics that share a name with a ribbon tile are not exposed, so *a reader of the History report cannot find them in the tool*. The tool knew about all three — three code comments said so in as many words — and showed none of them, which in a testimony context is the worst failure mode of a parity tool: the same NAME carrying two numbers reads as a disagreement rather than as two metrics. **Measured first, from the Bible:** each is its own `<Metric>` and the discriminator is the `PrimaryFilter`, not the formula — `Insufficient Detail™` (GUID `c71b82fe…`, `IncludeComplete=false`), `Merge Hotspot (Predecessors >2)` (`c5196e05…`, planned only), `Total # Predecessor Lags` (`37c0df8f…`, planned only, `sum(numberoflags)`). **Shipped:** three `MetricResult`s in `schedule_quality`, three `RibbonMetrics` fields with their drill sets, a new **Metric History** catalog family, three help-dictionary entries (so each column header's ⓘ states the filter) plus a cross-reference added to all three tiles, a **Metric History variants** panel on `/ribbon` (its own panel, NOT three more ribbon columns — the Ribbon and the Metric History are different reports, and a reader who finds a tile beside its variant in one matrix is being invited to make exactly the comparison this row exists to prevent), the ribbon workbook's last three columns, and the regenerated `METRIC-DICTIONARY.md`.

**Measured.** **Red first, by name:** the new oracle failed **8 of 11** on the pristine tree — *"`Insufficient Detail™` is not exposed as its own metric — a reader of the Metric History report cannot find its figure (22) in the tool (R-50)"* — with the three green being the vendor-report cross-check, which must pass without the engine. **The oracle is independent of the engine on both sides:** the Detailed Metric Report's per-activity `X` marks and the Metric History's labelled rows are cross-checked against EACH OTHER first, columns addressed **by metric name** (a moved column is a missing-label failure, never a silent read of the neighbour), and only then is the engine asked to reproduce the marks **by UniqueID**. **Exact on both files: 22 / 125 / 2 and 21 / 123 / 2, every mark, and the populations equal Fuse's own Record Counts (945 / 919, 916 / 906, 2 / 2)** — a check the rule did not get to choose. **Mutation battery 14 of 14 red BY NAME** on a shadow copy of `src/` (a `-p mutcheck` plugin asserts the modules measured ARE the copy). **M11 SURVIVED the first pass, and the survivor was a hole in the TEST:** it asserted the workbook carried the three HEADERS, and a header with nothing under it survives the column being dropped from the row — the writer just emits a shorter row. Each value is now addressed by its own header's column letter. **Corpus census, 15 goldens, before vs after on a `git archive HEAD` pristine tree measured by the same script: 8,805 pre-existing values — schedule quality, `RibbonMetrics`, every DCMA check WITH its citation UIDs, float bands, completion performance, every task's six CPM values — ZERO moved, ZERO removed, 90 added (the six new keys × 15).** **Rendered, not inspected:** `/ribbon` in a real Chromium, **four themes × 1440 px and 390 px** — the panel exists exactly once in all eight, **document overflow 0 px in all eight** (no sideways scroll added), every header carries its ⓘ call-out, and a click opens the existing drill: *"10 activities behind Merge Hotspot (Predecessors >2, planned only) — Project2.mspdi.xml"*. Wheel + nine installers rebuilt after the last source edit, the wheel's six changed files byte-identical to `src/` by sha. **The full gate on the final tree: 5,479 passed / 0 failed / 7 skipped in 39:48; `-m parity` 131 passed / 0 failed in 5:43.** Parity moved **120 → 131** and the delta is attributed, not assumed: `pytest -m parity tests/parity/test_fuse_history_variants_oracle.py --collect-only` collects **exactly 11**. The 7 skips are the documented set plus two: the `urlparse` pair, the three `INCIDENTAL_SVG` axis cases, **and the two `test_pptx_libreoffice_interop` skips — correct in THIS container, which has no `libreoffice-impress`; CI installs the filter and treats a skip there as a FAILURE (ADR-0498).**

**TWO CORRECTIONS to ADR-0473's wording, both measured — do not re-inherit the old text.**

1. **`IncludeMilestone` is NOT the discriminator for Insufficient Detail™.** ADR-0473 says the variant is `IncludeComplete=false` **and** `IncludeMilestone=false`, which reads as though the tile were `IncludeMilestone=true`. **Both** entries are `IncludeMilestone=false` in their `PrimaryFilter`; only the tile's unused `TripwireFilter` carries `true`. `IncludeComplete` alone separates them.
2. **The register's "2 vs 5" is "2 vs 8".** The tool's `Number of Lags` tile reads **8** on the Large Test File and 8 on File2, not 5 — and they are not the same UNIT: the Bible's own Description makes `Total # Predecessor Lags` a count of **relationships**, where the tile counts distinct **activities**.

## UNVERIFIED / held, stated

- **The three variants are pinned on the Large Test File / File2 pair only** — the one corpus pair whose Detailed Metric Report carries these columns. Their figures on Hard_File / Project2/5 / EVM are the engine's own and are UNPINNED; no Fuse export in the repo scores them there.
- **Further same-stemmed library metrics remain unexposed** and were out of R-50's scope: `Critical w/Insufficient Detail™`, `Merge Hotspot w/Predecessor Lags` (& Low Total Float), the whole successor-side lag family (`Activities w/Lags on Successor` = 8 on both files), `Max/Min Predecessor Lag (days)`, `Max # of Predecessor Lags on an Activity`. Named so a later row can price them.
- `NumberofExternalPredecessors` in the Bible's merge formula is a term the MSPDI cannot supply (R-64's external-link problem); on this corpus it is zero everywhere the marks agree, so it is UNTESTED, not proven absent.

## Traps this session paid for, by name

* **A stalled test is indistinguishable from a slow one when the suite runs `-q`, and this repo
  has no `pytest-timeout`.** The post-repair sweep sat at **78 % for 2 h 16 m** while the machine
  was IDLE — load average 0.02, pytest at 10 % CPU, a chromium alive 1 h 53 m, and **no test server
  listening**: a deadlocked browser test waiting on a page that was never coming. The same tree had
  run end to end in 37:23 an hour earlier, so it was a hang, not a regression. Dots gave no suspect;
  the re-run with **`-v`** names the test in flight at any instant (and it completed clean, 39:48).
  **Run the sweep verbosely, and treat "no progress while the load average is ~0" as the hang
  signal — a percentage cannot tell you.** The hung test was never identified (the run was killed
  to recover the wall clock) and it did NOT recur; `test_driving_path_whole_schedule_browser.py:104`
  is the register's known width-racy case (#667) but nothing here implicates it — **UNVERIFIED.**
* **The FULL SUITE found four failures the targeted runs could not see, and the push was held for
  them.** After the static gate, the targeted modules, the 14-mutant battery, the corpus census and
  the four-theme render were ALL green, the first whole-tree run came back **5,475 passed / 4
  failed / 7 skipped in 37:23** — and every one of the four was a real consequence of this change,
  not a flake: the catalog family tuple (two guards pin it, `test_catalog_shape_and_families` and
  `/api/workbench`, the latter also pinning `len(metrics) == 21` → 24), the monolith-split contract
  (`_HISTORY_VARIANT_COLS` / `_history_variants_panel` were not re-exported `X as X` from
  `web.app`), and the `/ribbon` panelkit census (4 `.panel` → 5). **Six guards were re-aimed in
  total; the targeted runs found two of them.** An additive metric is never additive to the
  guards — price the guard surface, not just the code.
* **A page-wide guard is under-specified the moment the page grows a second matrix** — the page-level twin of `CLAUDE.md`'s phase-2 trap. `test_ribbon_row_labels_wear_the_left_edge` counted row labels page-wide (2 → 4) and now counts them PER PANEL: a page-wide 4 cannot tell "both panels label both rows" from "one panel labels four and the other none". M14 proves the re-aimed guard still has teeth.
* **A test that asserts a HEADER exists has not asserted a VALUE exists.** M11's survival is the whole lesson: the xlsx writer emits a shorter row and the header string stays. Address the value by its header's column.
* **The `.aft` names metrics in `<Name>` ELEMENTS, not `Name="…"` attributes**, and escapes the values (`&gt;`, `&amp;`). An attribute regex returns ZERO for all three and reads exactly like "these are Acumen built-ins, not library metrics".
* **A same-named metric needs its GUID, not its name, as the key.** Two Bible entries are both called `Insufficient Detail™` with DIFFERENT formulas; the formula-audit guard's per-name formula SET is what makes pinning one of them possible.
* **Fuse's Record Count is a second, independent oracle** — the count of rows contributing a term. It caught the population question the totals cannot: 945 / 916 / 2 discriminate three different filters that could all produce the same total by accident.
* **Two matrices sharing one `data-export` make a selector ambiguous under Playwright strict
  mode.** The variants panel carries `id=metricHistoryVariants` (a real anchor, not a test hook)
  and the ribbon panel is addressed as the one that is NOT it; the panelkit census was
  *strengthened* rather than renumbered — both matrices are proved click-driven BY NAME and the
  `[data-sf-big]` count is pinned at 2, so a third panel must force a decision rather than ride
  along unproved. **M15: deleting that id turns the named test red.**
* **A shared tooltip vocabulary is cheaper than a second one.** The first cut of the variant cells wrote their own `title=` and broke a page-wide tooltip guard; reusing `_ribbon_cell_class` / `_ribbon_cell_title` deleted the new helper and the failure together.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here.** **First:** re-read CI 1890 for `9cb46317` (two jobs were still running), then this unit's draft PR (eight checks — `installer/**` is touched); after the operator merges it, restart the branch with `--prune` + `remote set-head` + `checkout -B`. Then the report's §3 in order: **R-61** · **R-57** · **R-58** · **R-59** · **R-64** · **R-63** · **R-62** · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design queue is 19 artboards. **Operator-owned, none blocking:** V-5 (PowerPoint opens the `.pptx`); OR-20's Jan-2024 fact line or the same question re-asked on v1.0.265+; decisions on OR-20b / OR-20c; the 09-11 `"ok": false` transaction-log lines (a 403); an ON-banner screenshot on v1.0.264+; `test_driving_path_whole_schedule_browser.py:104` width-racy (#667); `/settings` sideways scroll; the residuals of ADR-0488 / 0486 / 0485 / 0483; OR-11b, OR-11d; the working-minute axis; the hint bubble; ADR-0484's in-grid rows.

**Review cover is still absent** — Codex quota EXHAUSTED; the mutation batteries and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
