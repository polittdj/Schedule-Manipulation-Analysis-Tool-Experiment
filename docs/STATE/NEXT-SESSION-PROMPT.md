# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS² (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue.
As of last close: **v1.0.221 · highest ADR 0438 · SCHEMA 2.11.0 · main = dfa09acd** (the #610
squash). **NOTHING is in flight** — #609 and #610 are both merged, and the operator has
INSTALLED v1.0.221 on their PC (installer banner confirmed the version). **git fetch origin
before you branch, number an ADR, or commit — and RE-fetch before writing the docs** (main
moved UNDER the working branch twice in this arc).

⇢ WHAT'S DONE — do not re-open. 2026-08-21 (ADR-0437/0438, v1.0.221, merged AND installed):
**dropped folders traverse** — home.js captures entries SYNCHRONOUSLY in the drop handler,
drains `readEntries` to the empty batch (Chrome hands ≤100/call), and emits `preread()`-shaped
File-likes carrying `rel = "Folder/sub/file.ext"`, so N dropped folders land as N Projects
through the unchanged server pipeline; loose files keep `rel ''` · **/driving-path opens on the
COMPLETE schedule of ANY loaded file** — the `/path` workspace (`_path_body` + path.js) embeds
in the no-target state with every loaded session key selectable (same columns BY CONSTRUCTION;
browser-asserted header equality with /path), the trace form's File picker spans every Project
(optgrouped, value = session key, `?file=` accepts key OR legacy label via `_find_schedule`),
cross-project trace + tiers export resolve by key; r11 DP form freeze deliberately re-baselined
`ccd40241…/1925`. Before that: POLARIS² rename (ADR-0436, v1.0.220) and the 2026-08-20 four
asks (ADR-0431..0435, v1.0.219) — all merged and operator-verified.

⇢ **OPEN OPERATOR ASK — START HERE.** After installing v1.0.221 the operator reported they
*still* cannot load multiple folders at once, and want **ctrl-click / shift-click multi-select**.
Three facts were established BY MEASUREMENT on 2026-08-21 — do NOT re-derive them:
1. **The folder-picker DIALOG can never multi-select.** Chromium treats "pick folder" and
   "multi-select" as exclusive modes; `webkitdirectory` overrides `multiple` (WICG
   entries-api #24). Not fixable in our code — say so plainly rather than promising a fix.
2. **Dropping N folders WORKS** — proven with *real* Chrome directory entries via CDP
   `Input.dispatchDragEvent` with actual directory paths:
   `[('Apollo', folder, 2), ('Artemis', folder, 1), ('Loosey', title, 1)]`, nested file included.
3. **Ctrl/shift multi-select of FILES already works today** via "choose files…" (`#fileInput`
   carries `multiple`) — proven: four ctrl-selected files →
   `[('JUICE UVS', title, 3), ('Other Program', title, 1)]`. This is very likely the whole
   answer for the operator's `.xer` JUICE workflow; confirm they tried that button.

Two candidate builds were offered and **the operator has NOT chosen — ask before building**:
(a) clearer labels ("choose files… (Ctrl/Shift for several)"); (b) **parent-folder pick → one
Project per sub-folder**, which MUST ask rather than guess, because a folder of year
sub-folders (`Apollo\2023\`, `Apollo\2024\`) is legitimately ONE Project with versions
(ADR-0258's no-guessing rule, reaffirmed by ADR-0431's explicit Combine control).

⇢ OPERATOR FOLLOW-THROUGH (ask, don't assume): has the JUICE UVS .xer update set been re-loaded
on v1.0.221? The Mission Control wall should light; if the per-update exports rename the project
NAME too, Portfolio → Combine Projects is the remedy. Check any render report against the BUILD
it came from (the v1.0.148 lesson, ADR-0435).

⇢ RESUME ORDER once the open ask is settled — start at 1.

1. **PAGE MODULES A/B and DOCS/CONFIG/CI — still NEVER audited.** The last two whole dimensions
   with zero coverage (unchanged from the 2026-08-16 ledger).
2. **The AI figure-gates ADVERSARIAL pass** — `ai/qa.py::_figure_roles`, `_classify_figures`
   (`handled` added on the first non-value occurrence), `_MAX_GATED_FIGURES = 24`,
   `ai/derivation.py` Layer B. Fold in the f.text-never-f.rendered() finding (Ask prompt
   assembly, ai/qa.py ~910/931/942). Annotate-mode gap: gate scores against `model_evidence`
   while the analyst sees `relevant_facts`.
3. **The 25-route adverse gap** (19 are `POST /sra/*`; `/sra/factor-table` never touched at
   all). Report coverage as the bracket 25 <= gap <= 66.
4. Remaining REPORTED ledger rows: CPM-01..04 · MF-02/03/04/06..10 · MC-02..08 · IMP-02..06 ·
   MAN-01..03 · REC-02 · JS-02..06 · TST-02/03.
5. Smaller carried-forward items: sibling degrade notes (/trend /cei /evolution /volatility
   /integrity) could gain ADR-0431's other-projects tail · consider a browser assertion for the
   Utilization panel rows (currently server+probe-verified) · ADR-0424's leftover:
   `engine/pair_series.py` + `ai/pair_facts.py` never audited.

⇢ DO-NOT-FIX-BLIND LIST (unchanged from the ledger): MF-05 (empty-population PASS may be
correct Acumen parity) · MC-01's parity leg UNVERIFIED by design (ADR-0414) · ADR-0417 needs a
non-degenerate SRA fixture · ADR-0419's MinutesPerDay leg needs an operator file ·
`citations.reattach` drops `pinned` — measured unreachable; fix only if made reachable.

⇢ MEASURED-FALSE / BLOCKED — do NOT re-chase. Insufficient Detail V05/V06 and TP2's 6-vs-7:
six hypotheses measured and refuted (ADR-0430); blocked on ONE operator artifact — the named
activities behind Fuse's "Insufficient Detail — 5" cell (click it in the Fuse Starlight
workbook or export the ribbon to Excel), then re-upload. The /path timescale screenshot:
NOT reproducible on >= v1.0.219; property-guarded in chromium. **The folder-picker dialog's
inability to multi-select** (above) is now on this list too — it is a platform fact, not a bug.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
NEW: **a browser test that patches `webkitGetAsEntry` proves your TRAVERSAL, not the platform
integration** — the honest oracle for a browser-native object is CDP
`Input.dispatchDragEvent` with REAL directory paths (that is how the drop was finally proven);
reach for it whenever a claim depends on objects only the browser can mint · **never revert a
mutation with `git checkout <file>` while that file carries uncommitted work** — it restores
HEAD and destroys the work; mutate/restore through a scratch `.bak` copy, always · **this
remote container's clone is SHALLOW** — the installer build refuses at the mpxj graft boundary;
`git fetch --unshallow origin` first · **a new always-on panel flips an absence census** (r11
"panelkit absent on /driving-path" is now the ?target=absent branch only) · **key-valued options
with a label-accepting resolver** (_find_schedule) is the shape that widens a picker without
breaking bookmarks or label pins.
Prior: a screenshot is testimony about a VERSION · an "identity" must survive the workflow
that produces the files (proj_short_name renames per copy) · seat scrolls from LIVE geometry ·
a new sentinel sweeps the existing pins · contract growth is a NAMED re-baseline · a div-list
chart must not wear `.chart-host` · ruff B008 rejects `Form([])` AND `Form(default_factory=…)`;
`Form(())` passes · **a first-run green is a twin or a vacuum**.
Standing: a bounded sweep looks exhaustive and is not · a fix can be wrong in the direction you
did not test · the product is often its own oracle · a refuted hypothesis is a result · a count
may be counting the SYMPTOM · an oracle giving the same verdict in both worlds is BLIND · a red
for the WRONG REASON is not a red · monkeypatch per CALL SITE · never measure a tree a battery
is mutating · use `python -m ruff` · `ruff format` also formats python inside MARKDOWN — re-run
the WHOLE gate after the LAST file change · `| tail` masks exit codes · fetch before numbering
AND committing · wc decides.

⇢ TIMING — MEASURED. Container starts with NO deps: `python -m pip install -e ".[dev]"` +
`pip install build playwright` first. Full suite **~41 min** (4424 passed / 5 known env skips);
`pytest -m parity` ~15 min; browser census `pytest $(python tools/browser_modules.py)` ~6-7 min.
CI budget ~75 min for a full seven-check verdict; `cancel-in-progress: true` — never push while
you need a run's signal. Installer build needs an UNSHALLOW clone; `python -m build --wheel
--outdir dist/wheel && python tools/installer/build_installers.py dist/wheel/*.whl` ~2 min,
rewrites all nine.

⇢ OPERATOR-OWNED, not agent work: the Fuse Insufficient-Detail artifact (above) · V-1/V-2/V-3
gateway verification · DISC-01 · the CEI/HMI vendor export blocking PO-04/05 · an SSI export
showing a fired negative-impact register entry (ADR-0414) · an MSPDI DayWorking=1-no-times file
(ADR-0419) · branch cleanup · re-loading the JUICE set on v1.0.221 · CHOOSING between the two
candidate builds in the OPEN OPERATOR ASK above.

⇢ Standing rules (binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) ·
QC-1 / QC-2 (CLAUDE.md; ADR-0393, pinned by tests/test_standing_rules.py) · ADR-0240 model
protocol (the LEAD re-verifies every finding)
· full gate before every commit · handoff + SESSION-LOG + LESSONS-LEARNED + kickoff in the same
commit · wheel + nine installers ONCE per shipped-code change (ADR-0148) — check
`git status src/` before assuming you owe one.
Skills: full-gate, prove-able-to-fail, metric-parity, render-verify, cui-guard, ui-change,
session-close.
