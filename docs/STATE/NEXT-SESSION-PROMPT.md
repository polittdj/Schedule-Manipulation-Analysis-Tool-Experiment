# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume POLARIS² (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then docs/STATE/AUDIT-2026-08-16.md — that ledger IS the standing work queue.
As of last close: **v1.0.221 · highest ADR 0439 · SCHEMA 2.11.0 · main = 30f90f1** (the #612
squash). **NOTHING IS IN FLIGHT** — #612 merged 2026-08-26 15:27 UTC and was verified on `main`
afterwards (ADR-0439 + both guard modules present; the escaping census re-ran 4 passed against
merged `main`). The operator has INSTALLED v1.0.221 on their PC (installer banner confirmed the
version). **git fetch origin
before you branch, number an ADR, or commit — and RE-fetch before writing the docs** (main
moved UNDER the working branch twice in this arc).

⇢ WHAT'S DONE — do not re-open. **2026-08-25/26 (ADR-0439, MERGED @ 30f90f1, no version bump):
PAGE MODULES got their first-ever audit** — operator file content is DATA, not markup. Verdict **CLEAN and
MEASURED**: 81 scored server responses · 33 rendered pages in real Chromium · 44 export archives
under an XML-hostile name, zero leaks; the vendored JS is structurally immune (createElement +
textContent) and the NINE non-clearing innerHTML sinks are literals, esc()'d text, host
telemetry, or server-built HTML. Two standing censuses hold it
(`tests/web/test_operator_content_escaping.py` + `test_operator_content_dom_browser.py`,
auto-discovered by `tools/browser_modules.py`; CI's browser job ran it green in 9m).
**MF-02 was found STALE IN THE LEDGER** — it shipped as ADR-0411 — and is corrected; the
`value is not None` class it asked about is closed (3 AST sites, all correct). Before that:
2026-08-21 (ADR-0437/0438, v1.0.221, merged AND installed):
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

1. **DOCS/CONFIG/CI — the LAST never-audited dimension.** 2026-08-25 gave it only a PARTIAL
   pass: CLAUDE.md's documented gate was verified against `.github/workflows/ci.yml` and
   `[tool.mypy]` (they agree; bare `mypy` == `mypy src/` strict via `files=["src"]`), and two
   stale pyproject comments were fixed. UNTOUCHED: `.githooks`, `installer-smoke.yml`,
   `constraints/`, the docs guards themselves, `.gitattributes`/`.gitignore`, the SessionStart
   hook. **Page modules A/B is no longer a zero** — the escaping / fabricated-zero /
   export-integrity classes are done and guarded; other page-module classes remain fair game.
2. **The AI figure-gates ADVERSARIAL pass** — `ai/qa.py::_figure_roles`, `_classify_figures`
   (`handled` added on the first non-value occurrence), `_MAX_GATED_FIGURES = 24`,
   `ai/derivation.py` Layer B. Fold in the f.text-never-f.rendered() finding (Ask prompt
   assembly, ai/qa.py ~910/931/942). Annotate-mode gap: gate scores against `model_evidence`
   while the analyst sees `relevant_facts`.
3. **The 25-route adverse gap** (19 are `POST /sra/*`; `/sra/factor-table` never touched at
   all). Report coverage as the bracket 25 <= gap <= 66.
4. Remaining REPORTED ledger rows: CPM-01..04 · MF-03/04/06..10 · MC-02..08 · IMP-02..06 ·
   MAN-01..03 · REC-02 · JS-02..06 · TST-02/03. (**MF-02 REMOVED** — it was stale, see above.)
5. Smaller carried-forward items: sibling degrade notes (/trend /cei /evolution /volatility
   /integrity) could gain ADR-0431's other-projects tail · consider a browser assertion for the
   Utilization panel rows (currently server+probe-verified) · ADR-0424's leftover:
   `engine/pair_series.py` + `ai/pair_facts.py` never audited.

⇢ DO-NOT-FIX-BLIND LIST (unchanged from the ledger): MF-05 (empty-population PASS may be
correct Acumen parity) · MC-01's parity leg UNVERIFIED by design (ADR-0414) · ADR-0417 needs a
non-degenerate SRA fixture · ADR-0419's MinutesPerDay leg needs an operator file ·
`citations.reattach` drops `pinned` — measured unreachable; fix only if made reachable.
**NEW 2026-08-25:** the SIX dead E501 per-file-ignores (`scurve`, `standards`, `brief`,
`briefing`, `curves`, `workbench`) — provably dead by two oracles, but the stated policy attaches
the exemption to what a module IS, so removing them fights the intent and breaks the next HTML
edit · **`evolution.py`'s completed-on-path table renders `0%` for an absent activity** beside a
cell that correctly renders `—` — measured UNREACHABLE, latent.

⇢ MEASURED-FALSE / BLOCKED — do NOT re-chase. Insufficient Detail V05/V06 and TP2's 6-vs-7:
six hypotheses measured and refuted (ADR-0430); blocked on ONE operator artifact — the named
activities behind Fuse's "Insufficient Detail — 5" cell (click it in the Fuse Starlight
workbook or export the ribbon to Excel), then re-upload. The /path timescale screenshot:
NOT reproducible on >= v1.0.219; property-guarded in chromium. **The folder-picker dialog's
inability to multi-select** (above) is now on this list too — it is a platform fact, not a bug.

⇢ TRAPS PAID FOR THIS ARC — check BY NAME.
NEW 2026-08-25: **a census that HAND-WRITES its population will always find it clean** —
`/analysis` and `/wbs` are `/{name}` routes, so a hand-listed page sweep 404'd on them and scored
the 404s as ESCAPED while skipping every parameterized route (enumerate from the app object;
NEVER score a non-success response) · **a positive control can be wrong about WHERE the defect
lands**: `</td></tr>` assigned to a `<td>`'s own innerHTML is discarded by the parser, so that
symptom only exists when a whole table STRING goes into a container · **a population FLOOR placed
before the substantive assertion reports the wrong cause** (a corruption shrank the population and
the guard cried "enumerator broken") · **a half-covered guard reads exactly like a whole one** —
the export census built xlsx URLs only, leaving `docx.py`'s separate `_esc` unguarded while its
teeth test passed anyway · **a work QUEUE is data and goes stale unless something asserts it**
(MF-02 sat "unfixed" for a week after ADR-0411 shipped it) · **main moved under the branch AGAIN**
(#611 merged mid-CI, conflicting all four state docs) — merge-resolve, never rebase, and re-do the
rotation on the NEW main's docs.
Prior: **a browser test that patches `webkitGetAsEntry` proves your TRAVERSAL, not the platform
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
`pip install build playwright` first. Full suite **~32-41 min** (measured twice on
different containers: 4431 passed / 5 skips in 32:07 on 2026-08-25; 4424 / 5 in ~41 min before
that — treat the spread as container variance, not drift); `pytest -m parity` ~9-15 min; browser
census `pytest $(python tools/browser_modules.py)` ~7-9 min (the new DOM census adds ~1 min).
CI budget ~75 min for a full verdict, MEASURED on #612: `check` seconds · `browser` **9m** ·
`floor` **33m** · `test (3.11)` **56m** · `test (3.13)` **70m** — the `test` pair is the slow one
because it adds coverage instrumentation + parity + pip-audit on top of the suite, so 56-70 min is
normal, not a hang. `cancel-in-progress: true` — never push while you need a run's signal. Installer build needs an UNSHALLOW clone; `python -m build --wheel
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
