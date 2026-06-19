# Handoff — 2026-06-19 (PRs #81–#155 MERGED; **`main` green at #155 (`f021805`)**; OPEN PR = ADR-0095 path-export custom columns)

> ## START HERE (post-#155) — all 3 operator asks DONE; clearing the polish backlog
> **`main` at #155 (`f021805`), green.** All three asks shipped/merged: custom-field **mapping** (#148),
> **driving path** between 2 UIDs across versions (#152), grouping/filter **engine + UI** (#150, #153),
> **custom-field display columns** (#154), and `/groups` value **autocomplete** (#155). Operator then said
> "complete all remaining backlog tasks" — working through them. **OPEN PR (this branch, ADR-0095):**
> custom-field columns in the **path export** — `driving_table(rows, target, custom_labels)` appends a
> column per label from each row's `custom` map; `export_path` takes `&cols=` (intersected w/ the file's
> own `custom_field_labels`); `path.js updateExportLinks()` syncs `&cols=` to the toggled-on custom
> columns. **STILL TODO this directive:** (next, separate PR) **animated date-axis Gantt for the
> driving-path corridor** (`/driving-path` is server-rendered chips today). **BLOCKED (can't do here):**
> CEI/critical-path value-validation vs the Acumen Ribbon sheet — **needs the CUI Acumen files
> re-attached** (uploads don't persist across sessions); Float Ratio™/Score — **no extractable formula**.
>
> **SHIPPED (merged, all green):** #145 BEI→Bible (ADR-0085, CORRECTED by #149); #146 CPLI (ADR-0086);
> #147 **HMI** (ADR-0087); #148 **custom-field mapping** (ADR-0088); #149 **BEI corrected & Acumen-validated**
> (ADR-0089); #150 **grouping ENGINE** (ADR-0090); #152 **driving path 2-UIDs** (ADR-0091); #153 **Groups &
> Filters UI** (ADR-0092 — `/groups`: ≤5 filter rows → DCMA-14 scorecard over `filter_schedule`; breakdown
> per value w/ **BEI**; extracted `metrics.compute_bei`, no-CPM, single source of truth); #154 **custom-field
> display columns** (ADR-0093 — `_driving_data` rows carry `custom`, payload carries `custom_field_labels`,
> `path.js syncCustomColumns` adds a toggle per field).
> - **VALUE-VALIDATION vs the operator's new Acumen ribbon reports (2 versions of the Large File):**
>   **HMI is EXACT** (Acumen v2 = 0 of 24 due tasks, milestone 0 of 1, v1 N/A — `compute_hmi_trend`
>   reproduces it). **BEI was WRONG** → fixed to Acumen "BEI - Value Tasks" = complete NORMAL tasks /
>   NORMAL baselined-due (no baseline-dur filter, no missing-baseline term); goldens EXACT 0.74/0.59,
>   Large-File denominator EXACT 1228, numerator within 2 of 632.
>
> **NEXT (after ADR-0094 merges) — the 3 asks are complete; remaining backlog is value-validation + polish:**
> keep value-validating CEI / critical-path against the Ribbon Analysis sheet (CEI/FEI/BRI/TC-BEI/EVM by
> absolute column index — header row 9, v1 row 10, v2 row 11; NEEDS the CUI Acumen files re-attached);
> optional polish (custom cols in path export; animated Gantt for the driving-path corridor; Float
> Ratio™/Score still DEFERRED — no extractable formula).
>
> **MODEL/ENGINE recap:** custom fields = `Task.custom_fields` (tuple of (label,value); alias e.g. `CA-WBS`
> wins over `Text20`) + helpers `custom_field(label)`/`custom_field_map`; `Schedule.custom_field_labels`
> (populated, declared order). Schema **2.2.0**. Grouping = `engine/grouping.py` (`MAX_FIELDS=5`;
> `filter_schedule` = sub-schedule of matching tasks + internal rels so all metrics run unchanged;
> `group_values` = per-value UID groups; STANDARD_FIELDS = WBS/Activity Type/Constraint Type/Resource/
> Critical/% Complete).
>
> **MORE ACUMEN OUTPUT to validate against (in the edited DCMA report's `Ribbon Analysis` sheet, by
> absolute column index — header row 9, v1 row 10, v2 row 11):** CEI, FEI, BRI, TC-BEI, EVM (PV/EV/AC/
> SPI/CPI/EAC/VAC/BAC), Phase Analysis, Started/Completed-Delayed buckets. Use these to value-validate
> CEI/critical-path next.
>
> **OPS:** convert mpp→MSPDI via `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <mpp> <out.xml>`
> (Java 21 ok; 9MB file ~30s). **CUI:** `.mpp`/`.xlsx`/`.aft` must NOT be committed (pre-commit guard).
> Uploaded files live in `/root/.claude/uploads/385dc707-.../` THIS session — a NEW session likely won't
> have them, so the kickoff prompt asks the operator to re-attach. **DEFERRED:** Float Ratio™ + composite
> Score (no extractable formula); D (Fuse year Trend/Phase — ASK binning); `/path` chart bug (needs shot).



> **External audit (7 roles, A1–A11) FULLY ADDRESSED (#133–#136 + ADR-0077).** Only easy
> follow-up left: **A3-follow-up** `.sr-only` data tables for the non-curves charts
> (cei/scurve/drift/trend/trend_drill/wbs — names already done; trivial with `SFA11y.table`).
> Operator feature backlog still open: **`/path` chart visual bug**
> (needs the operator's screenshot), **D** Fuse year Trend/Phase (parity-sensitive; binning ambiguous
> — ask the operator), **E** Data-Date/Slippage overlaid-line redesign w/ clickable legend, **F**
> Bow-Wave running totals + target highlight; **G** Fuse-proprietary metrics stay DEFERRED (no DAX). The operator backlog is being worked **bugs-first**:
> **#128 (ADR-0068) MERGED** the `/analysis` Gantt scaling fix (item A's `/analysis` half) + path
> filters/full-wrapped-names (item C); **#129 (ADR-0069) MERGED** item B (MS-Project checklist
> filters). The **OPEN draft PR on this branch carries ADR-0070** — an out-of-band operator fix:
> **the local AI (Ollama) wouldn't activate on the operator's corporate laptop** (system proxy
> intercepted the loopback probe) → bypass the proxy + actionable settings diagnostics + editable
> Ollama endpoint. The highest ADR on disk is **0070**. Recreate the work branch from fresh main,
> then continue the REMAINING items (the remaining **bug** — the `/path` driving-chart visual defect
> — needs the operator's screenshot; otherwise the Fuse year Trend/Phase view D, Data-Date/Slippage
> E, Bow-Wave F).
> **Container setup FIRST:**
> `pip install -e '.[dev]'` into the env, and drive the gate with **`python -m pytest`** (the PATH
> `pytest` is a separate uv tool that can't see the editable install). Gate: `ruff check .` ;
> `ruff format --check .` ;
> `python -m mypy` ; `python -m pytest --cov=schedule_forensics --cov-fail-under=70` ;
> `coverage report --include='*/schedule_forensics/engine/*' --fail-under=85` ;
> `python -m pytest -m parity` (10/10, non-negotiable) ; `bandit -q -r src`.

> **OPERATOR BACKLOG (the big multi-part request + follow-ups). SHIPPED this session:**
> 1. ~~Ask-the-AI + release local Ollama~~ — **MERGED #116, ADR-0059** (full local evidence; air-gap kept).
> 2. ~~Chart legibility + fullscreen/zoom + legends~~ — **MERGED #117, ADR-0060** (`chartframe.js`).
> 3. ~~Target-UID drives every page~~ — **MERGED #118, ADR-0061** (`target.js`; /card + /wbs panel).
> 4. ~~Critical-path "gained float" counterfactual~~ — **MERGED #119, ADR-0062** (/evolution What-if).
> 5. ~~Diagnostic Brief trends/risks/recovery~~ — **MERGED #120, ADR-0063**.
> 6. ~~DCMA 1–14 definitions on the Analysis page~~ — **MERGED #121, ADR-0064**.
> 7. ~~Animated S-Curve~~ — **MERGED #122, ADR-0065** + **#124** moved its data-date callout
>    bottom-right (no title overlap).
> 8. ~~Fuse workbook validation~~ — **MERGED #123, ADR-0066** (`docs/FUSE-VALIDATION.md`): tool
>    matches Fuse exactly on normal-completion (8/8) + TP4 v1–v4 finish; diffs documented.
> 9. ~~Fuse Ribbon metrics~~ — **MERGED #125, ADR-0067.** `engine/metrics/ribbon.py` + `/ribbon`
>    view, calibrated to Fuse: Logic Density™ (2L/N), Merge Hotspot (>2 preds), Missing Logic
>    (all open-ends), Critical (incomplete on path), Hard/NegFloat/Lags/Leads (DCMA), Avg/Max float.
>
> **REMAINING — each its own tested, parity-green draft PR (operator wants ALL):**
> A. **BUGS (do first — defects):**
>    - **Path Analysis driving/secondary/tertiary-to-target chart is WRONG** (`path.js` + `/api/driving`).
>      **STILL OPEN — needs the operator screenshot** (visual; can't verify rendering in-container).
>    - **Scaling wrong** on the per-project (`/analysis`) **driving-path trace + project-schedule
>      Gantt** — `app.js` positioned bars as % of the whole span squeezed into a fixed-width column
>      with NO adjustable scale/scroll. **✅ FIXED (ADR-0068, OPEN draft PR):** both `/analysis`
>      Gantts now use the `/path` px-per-day + horizontal-scroll model (shared `buildAxis`, a
>      `#vizZoom` scale slider, month ticks + data-date line in px, pixel-true header/body alignment).
>    - **OPEN QUESTION for operator (still owed):** a SCREENSHOT of the wrong `/path` chart + a
>      `/analysis` Gantt to fix the `/path` half precisely. The `/analysis` half above was fixed
>      against the known-good `/path` model without it; the `/path` defect needs the screenshot.
> B. **MS-Project-style dropdown filters** (select-all / deselect-some checklists) replacing the
>    substring filter inputs on the grid + path tier filter. **✅ DONE (ADR-0069, OPEN draft PR):**
>    reusable `static/checklist.js` (`window.SFChecklist`) — a search + Select-all/Clear checklist
>    of a column's distinct values; applied to the `/analysis` grid per-column filters and both tier
>    filters (`/path` `#pathTier`, `/analysis` trace `#ganttTier`, now multi-tier).
> C. **Path filter on BOTH pages** (operator-confirmed): `/analysis` gets Primary/Secondary/Tertiary
>    tier filter + hide-completed + adjustable time scale + full wrapped names; `/path` gets full
>    wrapped task names (it already has tiers/hide/px-day-zoom). **✅ DONE (ADR-0068, same OPEN draft
>    PR):** `/analysis` got the `#ganttTier` tier filter, the `#vizZoom` adjustable scale, and full
>    wrapped names (grid + trace); `/path` Name column now wraps to full text. (Overlaps A + B.)
> D. **Year Trend/Phase view** — Fuse Ribbon Browser + per-year (2017–2028) trend analysis
>    (reference values in docs/FUSE-VALIDATION.md).
> E. **Data-Date & Slippage redesign** — overlaid line families with a clickable show/hide legend (curves.js).
> F. **Bow-Wave (cei.js)** running totals + target-UID highlight during animation.
> G. **Deferred Fuse-proprietary metrics**: Insufficient Detail™, Float Ratio™ (+ EPI / RatioMeasure /
>    Start-and-Finish-Ratio) — NO simple formula matched in calibration; implement only when the
>    operator supplies the exact Fuse/DAX definition. Do NOT guess.
> **Ollama policy: free LOCAL analysis, KEEP the strict loopback-only air-gap (no data leaves the machine).**

> **PR — ADR-0078 (OPEN draft, this branch) — curves clickable show/hide legend (item E).** The
> `/curves` Data-Date + Slippage charts overlay one line per version (50+ lines on a real program);
> `curves.js` `buildLegend` replaces the static in-SVG legend with real `<button>` entries that toggle
> each line (`polyline.style.display`, `aria-pressed`, struck `.off`) — keyboard-operable + focus-ring;
> Show-all/Hide-all isolates one version from the clutter. Applied to all 3 curves charts; data-date
> marker / locked axis / accessible name / `.sr-only` table unchanged. Parity 10/10. Built on
> `main`@#137.

> **PR — ADR-0077 (MERGED as #137) — audit close-out (A9 / A10 / A11).** A9: a
> `@media (max-width:760px)` block wraps the header/nav and collapses the wide card grids to one
> column (also satisfies 200%-zoom reflow). A10: `theme.js` sets `aria-pressed` on the toggle and a
> first visit follows the OS `prefers-color-scheme` (saved choice still wins, no flash). A11:
> `test_state_docs.py` now requires the latest ADR in BOTH HANDOFF and SESSION-LOG (anchored on local
> ADR files). **External audit A1–A11 fully addressed.** Parity 10/10. Built on `main`@#136.

> **PR — ADR-0076 (MERGED as #136) — table scope + print stylesheet (audit A4 + A5).**
> A4: mechanical `scope=col` on every server-rendered `<th>` (all 43 are column headers). A5: a
> `@media print` block in `base.css` — hides chrome (`header`/`.cf-bar`/`.export-bar`/`.viz-controls`/
> `#askPanel`), forces light ink on white, `break-inside:avoid` on panels/cards/tables, prints the
> horizontal scrollers in full, `@page{margin:14mm}`. Parity 10/10. Built on `main`@#135.

> **PR — ADR-0075 (MERGED as #135) — chart accessible names + data tables (audit A3).**
> Shared `static/a11y.js` (`window.SFA11y`, shell-loaded): `label(svg, name)` gives every chart a
> real accessible name (`<title>` + `aria-label`) — fixes the nameless `role=img` on all 11 charts
> (trend ×4 by their title; curves ×3 via a name arg; cei/scurve/drift/path_evolution/trend_drill/wbs
> static); `table(caption, headers, rows)` builds a `.sr-only` data-table fallback, implemented on the
> curves page (Finishes / Data-date / Slippage). Parity 10/10; air-gap green. Built on `main`@#134.
> Follow-up: `.sr-only` tables for the other charts (names already done).

> **PR — ADR-0074 (MERGED as #134) — CSP + security headers (audit A7).** Every response
> now carries a `Content-Security-Policy` (`default-src`/`connect-src`/`img-src` = `'self'`,
> `frame-ancestors 'none'`, `object-src 'none'`) + `X-Content-Type-Options: nosniff`,
> `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, set in the `create_app` http middleware via
> `setdefault`. Enforces the no-remote-asset air-gap in the browser at runtime. Permissive-inline
> (`'unsafe-inline'` style+script) so the inline Gantt px-widths + the 2 inline handlers (Quit /
> wipe-confirm) keep working — but remote scripts/styles are still forbidden. Air-gap scan still
> green + a new header test. Parity 10/10. Built on `main`@#133. Follow-up: tighten to strict
> `script-src 'self'` after moving the 2 inline handlers to addEventListener.

> **PR — ADR-0073 (MERGED as #133) — accessibility foundations (audit Group 1).** Pure
> presentation: (A1) a theme-aware `:focus-visible` outline ring using the orphaned `--focus` token;
> (A2) a `prefers-reduced-motion` CSS block + a guard in all 5 auto-play `toggleAuto()` handlers
> (under reduce-motion, Auto-play advances one frame instead of timer-flipping; Prev/Next unaffected);
> (A6) define `--border`/`--grid-line` in both theme blocks (were used with hardcoded fallbacks);
> (A8) a diagonal `repeating-linear-gradient` hatch on critical/driving Gantt bars (non-colour cue);
> plus the `.sr-only` helper as A3 groundwork. Parity 10/10; air-gap green. Built on `main`@#132.

> **PR — ADR-0072 (MERGED as #132) — configurable generation timeout for big models.**
> Operator wants the most powerful llama3.1 "even if it takes my machine longer". Each generation was
> capped at 120 s, so a large model (e.g. `llama3.1:70b` on CPU) got cut off → deterministic
> fallback. Added `AIConfig.gen_timeout` (default 300 s, clamped 30 s..1 h) wired into every local
> backend + a `/settings` "Generation timeout" field; the short availability probe (8 s) is
> untouched. Installing the model is a manual `ollama pull` on the operator's box (the air-gapped
> tool never fetches over the network — instructions given in chat). Parity 10/10. Built on
> `main`@#131. (Stashed a11y WIP still on this branch — pop after.)

> **PR — ADR-0071 (MERGED as #131) — local AI that just works.** Two operator follow-ups
> after ADR-0070: (1) **auto-manage Ollama** — `ai/ollama_process.py` `OllamaLauncher` starts a local
> `ollama serve` on desktop launch (background thread, never blocks) and stops it on exit, but ONLY if
> we started it (an already-running Ollama is left alone); wired into `launcher.main` (finally +
> atexit). Loopback-only, never `ollama pull` (Law 1). (2) **probe 2 s → 8 s** so a corporate laptop's
> slow first local connection ("timed out") still reads reachable. (3) **install-aware Model dropdown**
> on `/settings` — when Ollama is reachable the Model field lists installed models (configured-but-
> missing kept + flagged), because the operator's `llama3.1:8b` wasn't installed (they have
> `llama3.2:latest` / `schedule-analyst:latest` / `qwen2.5:7b-instruct`). Parity 10/10; 922 passed.
> NOTE the **stashed a11y WIP** on this branch (audit Group 1) — `git stash pop` after this PR.

> **PR — ADR-0070 (MERGED as #130) — local AI works on a corporate laptop.** Operator
> screenshot showed `/settings` reading **Active backend: null** with Ollama + `llama3.1:8b`
> configured (model never activated → only deterministic facts, no interpretation). Root cause: the
> local-AI HTTP client used urllib's default opener, whose **`ProxyHandler` reads the machine proxy**
> — on a managed Windows laptop that routes even `127.0.0.1:11434` through the corporate proxy, which
> refuses it (and would be a Law-1 egress risk). Fix in `ai/ollama.py` `_make_opener()`:
> `build_opener(ProxyHandler({}), _NoRedirect())` → **direct, no-proxy** loopback connection (covers
> the OpenAI-compatible backend too). Plus: actionable `/settings` diagnostics (`unavailable_reason()`
> → *connection refused / timed out / model not pulled* with a fix hint) and an **editable Ollama
> endpoint** field. The interpretive full-evidence prompt (`ai/qa.py`) was already correct — the only
> blocker was connecting. Parity 10/10; 913 passed. **Operator: `git pull` + relaunch to get it.**

> **PR — ADR-0069 (MERGED as #129) — MS-Project checklist filters (item B).** New
> reusable `static/checklist.js` (`window.SFChecklist.filter`): a button + fixed-position popup
> with a search box, **Select-all / Clear**, and a checklist of a column's distinct values;
> `onChange` gets the selected `Set` (or `null` = all = unfiltered; empty Set hides every row).
> Loaded once from the page-shell `<head>` (air-gap scan extended). Applied to the `/analysis`
> grid per-column filters (`filters[key]` is now a `Set|null`; `rowMatches` is membership;
> `distinctValues` is numeric/ISO-date-aware) **replacing the substring inputs**, and to both tier
> filters (`/path` `#pathTier`, `/analysis` trace `#ganttTier`) which become **multi-tier**
> checklist mounts. Pure presentation → parity 10/10. Built on `main`@#128.

> **PR — ADR-0068 (MERGED as #128) — /analysis Gantts go scalable + path filters.** The
> per-project `/analysis` driving-path trace (`#gantt`) and activity Gantt (`#grid` timeline) no
> longer squeeze the whole span into a fixed-width column as a % of span — both now use the `/path`
> px-per-day + horizontal-scroll model: a shared `buildAxis` in `static/app.js`, one page-level
> **Scale** slider (`#vizZoom`, 2–40 px/day), month ticks + the gold data-date line positioned in
> pixels, and pixel-true header/body alignment (zeroed horizontal padding on `.g-head`/`.g-cell`).
> The `/analysis` trace also gained a Primary/Secondary/Tertiary **tier filter** (`#ganttTier`),
> keeps the show/hide-completed toggle, and shows **full wrapped task names** (no 22-char
> truncation); the `/path` Name column wraps to full text too (`pv-name`). This closes item A's
> `/analysis`-scaling half + all of item C. **Still owed:** the `/path` driving-chart *visual*
> defect (item A's first half) — a follow-up commit on this same PR once the operator sends the
> screenshot. Pure presentation → **parity 10/10**; full suite **908 passed**; engine cov 97%.
> Air-gap unchanged (app.js stays dependency-free, same-origin).

> **AUDIT NOTE (2026-06-17):** the operator's 4 Acumen Fuse exports (Schedule Quality docx +
> Ribbon/Phase xlsx + DCMA Report) live ONLY in the ephemeral session uploads — their values are
> captured durably in `docs/FUSE-VALIDATION.md`. The reference `.mpp`/`.pbix` are NOT in the
> container (`00_REFERENCE_INTAKE/` empty) — re-deposit to validate Large File / Duration Bomb /
> Project3/4 / Project5_TAMPERED, which the workbook covers but the repo fixtures don't.

> **PR — ADR-0060 (chart full-screen / zoom / legible labels).** New `static/chartframe.js` +
> `.cf-*` CSS: any `class=chart-host` container gets an overlay toolbar (⤢ full screen via the
> Fullscreen API w/ `.cf-max` fallback; − / ＋ / Reset zoom rescaling the SVG in a scroller).
> Loaded once from the page shell; a MutationObserver re-applies zoom across stepper re-renders.
> `chart-host` marks trend/finishes/data-date/slippage/CEI/WBS/drift/analysis containers (the
> evolution Gantt keeps its own ADR-0055 zoom). `trend.js`+`curves.js` `shortLabels` now prefer
> the **data date** (uniform, sorted, non-overlapping) over long filenames; `drift.js` axis ticks
> are **adaptive** (year/quarter/month). Pure presentation → parity 10/10; full suite 876 passed.

> **PR — ADR-0059 (Ask-the-AI: full local evidence).** `ai/qa.py`: a live local model now
> gets the WHOLE cited sheet (`model_evidence`, frame-first + relevance-ordered, cap 48) with a
> senior-analyst prompt (answer + interpret + name risks + suggest recovery), while the analyst
> is still SHOWN the question-relevant `relevant_facts` slice. Strict mode unchanged; air-gap
> unchanged (`OllamaBackend` loopback-only — further scheme/redirect-hardened by ADR-0058/#115,
> `route_backend` fail-closed). `build_fact_sheet` adds the finish-driving count; the ask panel
> links to AI Settings to enable Ollama. Branched from `main`@#114, then merged up to #115
> (ADR-0058); re-verified green after the merge.

> ## START HERE (next session)
> 1. **One OPEN draft PR awaiting your merge: ADR-0059 — Ask-the-AI full local evidence /
>    release local Ollama (item 1 of the operator backlog above), branched from `main`@#114
>    and merged up to #115.** The prior audit-remediation PR (ADR-0058 — loopback AI-endpoint
>    scheme/redirect hardening + native-`.mpp` parity confirmation) has since MERGED as #115.
>    Earlier, the previous handoff
>    called PR #102 "OPEN"; it has since merged (as `f9b5b10`), and **PRs #103–#113 landed
>    after it** (ADRs 0047–0057, the post-M18 "tab visuals" / operator-feedback tranche — see
>    "What shipped — PRs #103–#113" below). Verified locally this sitting (2026-06-17):
>    **849 passed, 3 skipped; parity 10/10; engine 97%; ruff/format/mypy/bandit clean.**
>    Recreate the work branch from fresh main before any new work:
>    `git fetch origin main && git checkout -B <fresh-branch> origin/main`.
>    **Container gotchas:** the preinstalled `.venv` ships WITHOUT the web/dev deps — run
>    `pip install -e '.[dev]'` FIRST or the gate's mypy/pytest/parity/bandit all spuriously
>    fail. And the PATH `pytest` is a separate uv tool that cannot see the editable install —
>    drive the gate with **`python -m pytest`**, not bare `pytest`.
> 2. **M18 is COMPLETE (items 1–8) AND the operator's tab-visuals follow-ups (#103–#113) are
>    done. No feature backlog remains.** The open follow-ups are VERIFICATION / real-data
>    items, none blocking:
>    - **✅ Native-`.mpp` battery — VALIDATED this sitting (2026-06-17).** Operator re-deposited
>      all 14 reference `.mpp`s (non-CUI test files, attested) into `00_REFERENCE_INTAKE/mpp/`
>      (git-ignored, never committed). Each was checked against its committed MSPDI twin / pinned
>      values (method: the MSPDI fixtures are verified ground truth, so model-equivalence ⇒ every
>      downstream number holds). Results:
>      - **Duration Bomb** computes finish **2027-02-24** → ADR-0043 owed item **CLOSED**.
>      - **Project2** native parse is a **full model match** to the golden (145 tasks / 176 links /
>        finish 2027-08-30, zero field diffs).
>      - **TP4 v3→v4** fires `MANIP_ACTUAL_ERASED` + `MANIP_BASELINE_CHANGE` citing UID 19;
>        **v2→v3** fires neither — manipulation detection confirmed on native `.mpp` (matches pin).
>      - **Project5_TAMPERED** → tool flags `MANIP_DELETED_LOGIC` (UIDs 135/138); finish slips
>        2027-12-07 → 2028-01-25. Detector works.
>      - **Large File** parses faithfully — **1723** non-summary activities (exact ADR-0045 match),
>        2702 links. The documented driving chain's relative spacing reproduces SSI's **0/9/12/13**
>        to the day. ⚠️ Absolute reproduction is blocked because **ADR-0045 never recorded SSI's
>        target/focus UID** (doc gap — capture it next time the file is in hand).
>      - **TP1 / TP3 / TP4(v1–v5)** native `.mpp` match their MSPDI twin on task topology, logic
>        links, and computed finish; they differ only on `percent_complete` (+ a few durations) for
>        in-progress/summary tasks — MS Project recomputes progress/roll-ups on XML→`.mpp` import.
>      - ⚠️ **TP2 round-trip caveat (NOT a tool bug):** `.mpp` computed finish is **2026-09-24**, not
>        2026-11-04, because MS Project dropped the **4×10 Crew project calendar's 4 holiday
>        exceptions** on save (confirmed via MPXJ: project CalendarUID=1 has 0 exceptions; stock US
>        holidays landed on the non-default "Standard" calendar UID 2). The tool reads the project
>        calendar correctly; the canonical committed XML (4 holidays → 2026-11-04) is authoritative.
>        Details in `docs/PARITY-REPORT.md` / `docs/risks.md` (R-04).
>      - Minor, pre-existing & format-independent: TP4 **v4 and v5** both compute finish 2026-06-26
>        from the `.mpp` **and** the committed MSPDI, while `TEST-PROJECTS.md` lists v5 as 7/17/26 —
>        a fixture-vs-manifest question, not a native-`.mpp` issue. Flagged for separate review.
>    - **Real-file feedback** — watch how Path Analysis, Critical-Path Evolution (now with grid
>      columns / zoom / filter-by-path / specific reasons), ask-the-AI, float bands, `/forecast`
>      (with the explainer), `/trend` drill-down, and the Dashboard health cards read on real
>      `.mpp`/`.xer`. Importer tolerance lives in `importers/_common.py`; ALWAYS re-run
>      `pytest -m parity`.
>    - **Deck measures awaiting a DAX export** (EPI / RatioMeasure / Start-and-Finish Ratio) —
>      implement exactly when the operator provides the measure text; do not guess.
>
> ## ⚠️ PROCESS — verify ruff/format with EXPLICIT exit codes
> Twice this sitting a real `ruff check`/`ruff format --check` failure slipped to CI because
> a `cmd && echo ok` chain swallowed the failure while test counts still printed. **Run the
> CI-exact gate and read each exit code:** `ruff check .` ; `ruff format --check .` ; `mypy`
> (BARE — that's what CI runs, src only; do NOT add `tests`, which has known mypy noise CI
> never checks) ; `pytest --cov=schedule_forensics --cov-fail-under=70` ; `pytest -m parity`.

## What shipped — PRs #103–#113 (post-M18 "tab visuals" / operator feedback, 2026-06-16→17)
All merged to `main`; `main` is green at #113. These are the operator's "tab visuals"
follow-ups after M18 closed — the previous handoff stopped recording at #102, so this section
restores the record. Newest first:
- **#113 (ADR-0057)** — Critical-Path Evolution **reason specificity**: entered/left
  attribution now NAMES the specific slip (which activity consumed the float), CITES the exact
  predecessor/successor link(s) for `logic_added`/`logic_removed`, and shows the signed
  duration delta + percent for `duration_up`/`duration_down`.
- **#112 (ADR-0056)** — Evolution **filter-by-path**: a selector with four switchable modes
  scoping which activities the Gantt shows; applied to both critical rows and the dashed
  "left the path" ghost rows, composed after the hide-completed filter.
- **#111 (ADR-0055)** — Evolution **axis zoom/pan + target-UID focus** (`/evolution?target=`,
  mirrors `/trend?target=`; the session-wide target carries over across views).
- **#110 (ADR-0054)** — Evolution **per-activity grid columns** (% complete / duration /
  start / finish), smaller wrapped readable names, and the view's own **hide-completed** toggle.
- **#109 (ADR-0053)** — **schedules listed earliest→latest data date in EVERY view**
  (`SessionState.ordered_versions()` via `engine/trend.order_versions`; undated keep load order).
- **#108 (ADR-0052)** — **CEI re-verification**: there are TWO distinct indices both named
  "CEI" — EVM CEI (`engine/metrics/evm.py`) vs Bow-Wave CEI (`engine/bow_wave.py`, `/cei`).
  Both re-derived from first principles against the golden Acumen exports and **pinned to exact
  golden values** (replacing weak `is not None` assertions).
- **#107 (ADR-0051)** — **hide-completed robust flag**: real `.mpp`/`.xer` exports report a
  finished activity at 99.x% (MSP rounding / XER `CP_Units`) while carrying an actual finish, so
  `percent>=100` left done tasks visible. The toggle now keys on a robust complete flag (goldens
  are exactly 100.0, which masked the bug); behavior unified everywhere it appears.
- **#106 (ADR-0050)** — **Dashboard health cards**: `/api/dashboard` (`_dashboard_data`) — one
  health snapshot per loaded schedule (status mix, critical %, finish vs baseline, DCMA
  pass/fail) that clicks through to the detailed report; reuses the cached `_Analysis` (no
  CPM recompute).
- **#105 (ADR-0049)** — **every chart carries a legend + description; labels de-overlapped**
  (`trend.js` was the worst offender — no legend, no per-chart description, unthinned rotated
  x-labels smearing on 10+ version workbooks).
- **#104 (ADR-0048)** — Critical-Path **Evolution Gantt + entered/left attribution**: bars
  instead of a flat list, strong visual emphasis on added/removed activities, and a per-activity
  reason (logic change / new task / duration change / constraint).
- **#103 (ADR-0047)** — **Ask-the-AI relevance fix**: `relevant_facts` no longer padded every
  answer with the same leading facts, so the Null-backend answer is now question-specific
  (air-gap unchanged — no LLM prose ever leaves the machine).

> **SSI DRIVING-SLACK PARITY FIX (ADR-0045) — DONE + VERIFIED, shipped as PR #101.**
> Operator compared the tool's Path Analysis vs SSI on `Large Test File.mpp` (USA OTB Master
> IMS, 1723 acts): the tool's tiers were a consistent **~+1 day** off SSI (SSI 0-day driving
> path read as secondary; SSI 9/13 read 10/14). **Root cause:** ragged stored TIMES of day
> (afternoon-shift activities stored 13:00→12:00 → 420-min "1-day" spans) made activity spans
> sub-day; the backward pass's span subtraction ACCUMULATED that raggedness down a long chain
> and tipped whole-day slack over a boundary. **Fix:** snap each activity's SPAN to the
> nearest whole working day in `compute_driving_slack` (display dates unchanged — `date_basis`
> untouched). An earlier attempt that snapped the FINISH broke TP1 (sub-day DRIVING → full-day
> SECONDARY); snapping only the span preserves TP1 exactly. Verified: Large File matches SSI
> exactly (driving 0, near-path 9 and 12/13); **TP1 parity preserved (13/1/2/2)**; parity
> 10/10; full suite 813. Regression: `tests/engine/test_driving_slack_daygrid.py` + the updated
> TP1 battery pins (UID 11/12 now 60 min, not 210 — same DRIVING tier).


**This sitting (2026-06-16, cont. 5):** **#101 merged** (SSI driving-slack day-grid fix,
ADR-0045). Then **PR #102 (ADR-0046) — M18 item 8, the LAST backlog item**: the **Forecast
explainer** on `/forecast` (a plain-English "How the three forecasts are computed" panel — one
card per method with the formula in words + symbols + this version's value — plus a static
single-version inline-SVG "spread ruler" placing the data date, baseline finish, and the three
method dates on one timeline; server-side, no new JS) and the **Trend page expansion**:
`MetricTrend.offenders_by_version` (the offending activities per metric PER version),
`/api/trend` per-version counts + offenders (uid+name) + lower_is_better/worst_index, a new
**"Quality drill-down & animation"** panel (`static/trend_drill.js`: a Prev/Next/Auto-play
version stepper over a LOCKED-axis bar chart of per-metric offender counts, with a metric
selector listing the exact offending activities for the current version), and a full
per-version **"Quality offenders by version"** Excel/Word export table. Additive (forecasting
math / CPM / quality definitions untouched) → parity **10/10**; full suite **818 passed**;
engine cov 97%. Air-gap extended over `/forecast` + `trend_drill.js`. **M18 COMPLETE.**
Model/mode: Opus 4.8 (1M).

**This sitting (2026-06-16, cont. 4):** **#99 merged** (summary-logic fix, ADR-0043). Then
**PR #100 (ADR-0044) — M18 item 7, Critical-Path Evolution animation**: a new
**`/evolution` page** with a Bow-Wave-style Prev/Next/Auto-play stepper over the versions
(`engine/path_evolution.py` `compute_path_evolution` → `PathEvolution`/`CriticalSnapshot`).
Per version: the critical path with **entered** (green) / **stayed** (grey) / **▲dur** badge
and **left** (struck) activities, plus a callout for the **finish movement** and
**schedule-optics signals** (durations cut on the path + logic removed — reusing
`detect_manipulation`), flagging a path that sheds work while the finish holds. Nav +
dashboard links + xlsx/docx export (`path_evolution_tables`); air-gap extended. Verified on
golden P2→P5 (critical 43→37, 6 left, finish +99d). Parity 10/10; full suite 810 passed;
path_evolution 100% cov. **Remaining M18: item 8 (forecast explainer + Trend expansion).**
Model/mode: Opus 4.8 (1M).

**Prior this sitting (2026-06-16, cont. 3):** **#98 merged** (Carnac cards, ADR-0042). Then
**PR #99 (ADR-0043) — logic on summary tasks**: the Duration-Bomb verification (below) was
RESOLVED here. Root cause: the test file (an MS Project sample) attaches predecessor/
successor logic to **summary** tasks (e.g. summary UID 151 on an FS chain with 40–60wd
lags), which MS Project applies to the summary's children; our CPM dropped summary tasks
from the network and so ignored it, packing children at the front (computed 2026-08 vs
MSP's 2027-02). Fix (`engine/summary_logic.py`): `lower_summary_relationships` replaces each
summary endpoint of a relationship with the summary's **leaf descendants** (cross-product,
type+lag preserved; WBS segment-prefix hierarchy); `compute_cpm` now builds edges from the
lowered relationships. No-op without summary logic, so the goldens (zero summary logic,
pinned) are byte-identical → **parity 10/10**. Plus a new MEDIUM finding
`logic_on_summary_tasks` (cited, in the metric dictionary) flagging the DCMA/PMI anti-pattern.
**Verified: the Duration Bomb now computes 2027-02-24** (its stored "Wedding COMPLETE"
date), UID 17 lands on its stored 2026-07-27, the finding cites all 18 summaries.
Full suite 799 passed; engine cov (summary_logic 100%). Model/mode: Opus 4.8 (1M).

**Prior this sitting (2026-06-16, cont. 2):** **#97 merged** (PBIX pages 8/9 WBS pivots,
ADR-0041). Then **PR #98 (ADR-0042) — M18 item 6, PBIX page 13 (Carnac forecast cards)**:
the deck's *Carnac* KPI card row on the existing `/forecast` page (no new route/JS) —
earliest start, latest finish, project + remaining duration (wd), Forecasted End Date
(rate), Estimated End Date (ES, to-go), avg tasks/month, SPI(t) [deck "SPI 2"], ES (wd),
to-go count [deck "Tasks Completion Forecast"]. New engine `compute_carnac_summary` →
`CarnacSummary` (reuses CPM + ForecastSet; lightweight dataclass). Also **unified the
Earned-Schedule definition**: `forecast._earned_schedule` now delegates to the public
`metrics.evm.earned_schedule` (shared by SPI(t), WBS, forecast — golden pins unchanged).
Export gains a Carnac summary table. Parity 10/10; engine cov 97% (forecast 97%, no
uncovered lines). **PBIX reproduction spine COMPLETE: pages 1,4,5,6,7,8,9,12,13 done;
pages 2/3/10/11 are restatements.** Model/mode: Opus 4.8 (1M).

> **✅ DURATION-BOMB VERIFICATION (owed since #91) — RESOLVED 2026-06-16 (ADR-0043).**
> The test file (`00_REFERENCE_INTAKE/mpp/Project2_Duration_Bomb.mpp`, non-CUI) is a
> downloaded MS Project sample ("Formal Wedding Planner", 71 activities, 0% complete) that
> attaches logic to **summary** tasks. Operator's call: calculate as MS Project does (lower
> summary logic to children) AND flag it. Implemented in PR #99 (ADR-0043). The CPM now
> computes **2027-02-24** (matching the file's stored dates; the earlier "2026-08-05" was
> our CPM dropping summary logic), and `logic_on_summary_tasks` fires citing the 18 summaries.

**Prior this sitting (2026-06-16, cont.):** **#96 merged** (item 6 PBIX pages 6/7/12 —
Finish & Slippage curves, ADR-0040; post-merge main green). Then **PR #97 (ADR-0041) —
M18 item 6, PBIX pages 8 + 9 (WBS pivots)**: a new **`/wbs/{name}` page** with the
**Completion Metrics by WBS** pivot (counts/%, ahead/on/behind + avg days, longer/shorter,
duration ratio) and the **SPI(t) & Earned Schedule by WBS** combo chart + table. New engine
`engine/metrics/wbs_breakdown.py` (`compute_wbs_breakdown` → `WBSGroup`, grouped by
top-level WBS segment; lightweight dataclass NOT MetricResult). The count-based SPI(t)
core was factored out of `evm.py` into a public `earned_schedule(schedule, tasks)`
(reused by `_spi_t` and the per-WBS breakdown — one ES definition). Dashboard row "WBS"
action, xlsx/docx export (`wbs_breakdown_tables`), shared ask panel. Air-gap extended over
`/wbs/{name}` + `wbs.js`; engine cov 97% (new module 100%, evm 100%); parity 10/10; golden
groups reconcile (126/27 in Project5). PBIX-VISUALS pages 8/9 marked REPRODUCED.
**Remaining PBIX: Carnac forecast cards (13); pages 2/3/10/11 are restatements.**
Model/mode: Opus 4.8 (1M).

**Prior sitting (2026-06-16):** **#95 merged** (item 6 PBIX pages 4+5 — Cross File
Comparison + Float Analysis charts on the Trend page, ADR-0039; post-merge main green).
Then **PR #96 (ADR-0040) — M18 item 6, PBIX pages 6, 7, 12 (Finish & Slippage curves)**:
a new **`/curves` page** with three dependency-free SVG line charts on one shared month
axis — **Finishes** (latest version: actual vs baseline finishes/month), **DATA Date
Finishes** (one actual-finish curve per version — the bow wave as a line family), and
**Slippage** (per version, a start curve + a finish curve). New engine:
`engine/month_axis.py` (the shared `month_index`/`month_label`/`bucket` primitives,
extracted from bow_wave which now imports them) + `engine/month_curves.py`
(`compute_month_curves` → `MonthCurves`/`VersionCurves`, lightweight dataclasses NOT
MetricResult). Stored-date view (no CPM gate — every loaded version contributes, works
single-version too). Nav link + dashboard multi-version row + xlsx/docx export
(`month_curves_tables`). Air-gap extended over `/curves` + `curves.js`; engine cov 97%
(new modules 100%); parity 10/10. PBIX-VISUALS pages 6/7/12 marked REPRODUCED.
**Remaining PBIX pages: WBS pivots (8–9), Carnac cards (13).** Model/mode: Opus 4.8 (1M).

**Prior sitting (2026-06-13, cont.):** **#93 merged** (item 5 — forecast-drift animation +
locked axes; post-merge main CI green). Then **PR #94 (ADR-0038) — M18 item 6, PBIX
page 1**: a new **`/card/{name}` Schedule Card** reproducing the deck's *Metrics* page —
activity makeup, status split, completion-performance split, the **primary-constraint
distribution**, and a KPI stat-card row — all from the schedule's existing analysis plus
two new tested engine helpers (`compute_activity_makeup`, `compute_constraint_distribution`
in `engine/metrics/schedule_card.py`; lightweight dataclasses, NOT MetricResult, so the
dictionary-coverage test is untouched). Linked from the dashboard ("Card" row action),
carries the shared ask panel. PBIX-VISUALS.md page 1 marked REPRODUCED; the
constraint-distribution gap closed. Remaining PBIX pages (4,5,6–9,12,13) are the next
tranches. Model/mode: Opus 4.8 (1M context).

**Earlier 2026-06-13:** **#92 merged** (M18 item 4 — AI at full power; post-merge
main CI green). Then **PR #93 (ADR-0037) — M18 item 5**: the **forecast-drift animation**
(`/static/drift.js`, a Bow-Wave-style Prev/Next/Auto-play stepper on the /forecast page,
shown with ≥2 versions) plotting the three forecasts per version on a **LOCKED date axis**
(`_forecast_data` → `axis.min/max` across every version's forecasts + data dates +
baseline finishes), and the **Bow Wave count axis now locked** to the max bar across all
snapshots (`_cei_data` → `max_count`; `cei.js` no longer rescales each frame). Trend line
charts were already locked-by-construction (all versions on one fixed per-metric scale)
and the Path Gantt is a single-schedule timeline — both assessed, no change (ADR-0037 §4).
Pure presentation; parity untouched. **VERIFICATION STILL OWED (item 3, #91): the Duration
Bomb .mpp is NOT in this container** — on operator re-deposit, confirm computed finish
**2027-03-04**, completed tasks visible on /path, the "dates not supported by logic"
finding citing the template tasks. Model/mode: Opus 4.8 (1M context).

**Prior sitting (2026-06-12):** **#90 merged** (the eday fix), then **#91 merged** (M18 items 1–3,
ADR-0034: the **stored-date CPM mandate** — unstarted MANUAL tasks pin at their stored
start, unstarted logic-unbound auto tasks floor there, `CPMResult.date_driven` + the
cited **"N dates are not supported by logic"** finding, `Task.is_manual` model v2.1.0;
the **Path-Analysis stored-date display** — completed work at ACTUAL dates, per-row
`date_driven`, trace-coverage status line; the **full-width layout**). Post-merge main
CI green. Then **PR #92 (ADR-0035) — AI at full power, part 1**: `AIConfig.qa_mode`
(**interpretive default** — the model may analyze/derive grounded in the cited facts;
strict = the old wholesale figure-discard, still selectable), the **ask panel on EVERY
page** via the page shell (`_ask_panel_html` + `static/ask.js`, scope select = workbook
or any version; the /path-local panel removed, same ids/endpoint), **workbook-wide
facts** (`build_workbook_fact_sheet` reusing the briefing's cited statements +
latest-pair manipulation signals + latest forecasts; `POST /api/ask`), and the standing
**"AI can err — verify against citations"** disclaimer. The narrative/briefing
`reattach` gates and loopback-only egress are UNCHANGED. **VERIFICATION OWED: the
Duration Bomb .mpp is NOT in this container** — on operator re-deposit, confirm computed
finish **2027-03-04**, completed tasks visible on /path, and the logic finding citing
the template tasks. Model/mode: Fable 5 (1M context).

> READ THIS FILE FIRST to resume. Durable state lives here + `docs/STATE/SESSION-LOG.md` (append-only
> per-session history) + `docs/adr/` (decisions) + `docs/PLAN/RTM.md` (requirements). Never rely on
> chat history — everything important is committed to git.

## Repo / branch / PR mechanics (how this build runs)
- Repo: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`. Everything ships to **`main`** via PRs.
- The harness assigns a fresh work branch each session (this sitting:
  `claude/inspiring-davinci-tez1dv`). Recreate it from `origin/main` for each new PR (the prior
  branch is deleted on squash-merge). To start fresh work:
  `git fetch origin main && git checkout -B <fresh-branch> origin/main`.
- Commit identity must be `Claude <noreply@anthropic.com>` (a Stop hook checks this — if it flags
  unverified commits run `git config user.email noreply@anthropic.com && git config user.name Claude`
  then `git rebase --exec "git commit --amend --no-edit --reset-author" origin/main`). **Force-push is
  blocked**; to publish a rebased branch whose remote tip moved, do an empty `git merge -s ours <old-tip>`
  so the push is a fast-forward (used this trick once already).
- After each push, open a **draft PR**. The operator merges PRs themselves (do NOT merge). Watch CI via
  the github MCP tools; CI **success is not delivered by webhook** — verify it explicitly. `send_later`
  is NOT available in this environment, so for the post-merge `main` run, use a short background
  `sleep` then re-check `actions_list`/`get_check_runs`. Unsubscribe once a PR is merged.
- CI: ruff + ruff format + mypy --strict + pytest (cov ≥70 overall, engine ≥85) + `pytest -m parity`
  (10/10, **non-negotiable**) + bandit + pip-audit, on push-to-main + every PR, Python 3.11 & 3.13.

## Build status
**COMPLETE — all milestones M1–M17 delivered** (M15 closed by PR #74/ADR-0030 after the operator
deposited the `.pbix`). The deck stays git-ignored CUI in `00_REFERENCE_INTAKE/pbix/` on the machine
that received it; it does NOT travel between cloud sessions (R-12) — if a future session needs it
again, ask the operator to re-deposit. Its DAX is XPress9-compressed: the reconstructed formulas are
in the metric dictionary; EPI / RatioMeasure / Start-and-Finish-Ratio await a DAX export.

## What shipped earlier sittings (PRs #58–#68)
- **#58** Full-audit remediation (ADR-0024): dropzone native form-submit; Windows `.mpp` temp-file fix;
  POST-only wipe/example; never-uncited citation; SPI(t); cached UID maps; one `_Analysis`/CPM per
  schedule; O(weeks) CPM date math (equivalence-swept); 2s Ollama probes; CI push-main-only + action
  bumps + pip cache; conftest golden fixtures; CSS/JS → `static/`; pyproject 1.0.0.
- **#59 / #60** Java discovery without admin: `SF_JAVA`→`JAVA_HOME`→PATH→**portable `tools/jre/` drop-in**
  (gitignored)→`%LOCALAPPDATA%\Programs`→machine roots, newest-version wins; actionable not-found error.
- **#61** Compare ordered by **data date** (not load order) + Net Finish Impact on the page.
- **#62** (ADR-0025) Trend across 10+ versions; Executive Briefing; **MS-Project-style Gantt** (timeline
  column, add/remove fields, milestones/summaries/critical/data-date). New `engine/trend.py`,
  `ai/briefing.py`.
- **#63** Docs/state refresh.
- **#64** Real-world `.mpp` tolerance (see lessons) + **schedule-level DCMA findings stay cited** (root-
  cause of the operator's "Internal Server Error") + resilient `/trend` `/compare` `/briefing` (skip &
  name unschedulable versions) + grid **per-column filters** + trace "show completed" toggle + waterfall
  driving Gantt + milestone diamonds.
- **#65** (ADR-0025 line) **Bow Wave / CEI** animated view (`engine/bow_wave.py`, `/cei`,
  `static/cei.js`): per-snapshot monthly finish bars (baselined/scheduled/finished), dashed
  data-date marker, "CEI – x.xx" callout, **Prev/Next + Auto-play movie**; CEI = finished ÷ what the
  prior snapshot planned for the month after its data date. Plus **Trend focus UID**
  (`/trend?target=<uid>`) and **de-overlapped chart labels** (strip common filename prefix, rotate −35°).
- **#67** Bow Wave / CEI hardening: capped month axis sheds the OLDEST months first (the newest
  status month + CEI period never fall off); CEI exactly 0.00 styles red/fail (falsy-zero bug).
- **#68** (ADR-0026) Full audit (3-agent fan-out; ~25 findings fixed: §6 citation crash class
  closed via NA-on-empty-populations + terminal citation anchors; BEI early completions;
  XER got MSPDI's tolerance classes + `complete_pct_type`-aware percents + UTF-16; MSPDI
  percent lags; NaN/Infinity = noise; `MANIP_ACTUAL_ERASED`; CUI redaction + JSON round-trip
  fidelity) + operator features: **session-wide Target UID** (`POST /target`, report panel +
  auto-trace, trend default focus, compare movement), **light/dark theme** (`theme.js`,
  CSS variables, live-re-theming SVG), **batch cap 10 → 20**.
  All of #58–#68 are **merged to `main`**.

## What shipped this session — PRs #69–#80 (all merged)

**PR #69 (ADR-0027) — the four ADR-0026 deferred items, MERGED:**
1. **Calendar-true day math**: every day↔minute boundary derives from
   `calendar.working_minutes_per_day` — the DCMA "44 working days" tripwire is now
   `forty_four_days_min(schedule)` (`metrics/_common.py`; DCMA06/DCMA08/Insufficient Detail),
   DCMA12 injects `100 working days` on the schedule's calendar, driving-slack tier bands +
   `driving_slack_days` convert per-calendar, and `float_analysis` day rendering does too.
2. **XER `CP_Units`** percent complete from TASKRSRC quantities (`_units_percent_by_task`):
   actual (`act_reg_qty`+`act_ot_qty`) ÷ at-completion (actual+`remain_qty`), summed per task;
   actual dates still rule; quantity-less / zero-at-completion falls back to the duration share.
3. **AI figure gate + per-request backend**: `reattach` keeps a rephrase only if it preserves
   the source's numeric figures exactly (`preserves_figures`, multiset; fail-closed to the
   verbatim sentence) — with that in place, the settings-selected backend now actually drives
   the prose: the report narrative is polished once per (schedule, backend, model)
   (`SessionState.polished`, `_polished_narrative`), the briefing builds with the routed
   backend, generation failure degrades deterministic (never a 500), and routing is cached 15s
   (`SessionState.backend_cache`, reset on settings save) so a down Ollama can't slow renders.
4. **Trend labels**: identical filenames no longer collapse to "…" — a label that empties
   after the common-prefix strip falls back to the version's data date (`trend.js shortLabels`).

**PR #70 (ADR-0028) — MSPDI/XER project-calendar parsing, MERGED:**
- Importers fill `Schedule.calendar` from the source's project calendar: **work weekdays**
  (source day 1=Sun..7=Sat → `weekday_from_source`), **per-day minutes** (span sums; differing
  days use the **dominant/modal** total — single-block model approximation), **holidays**
  (full non-working exceptions; working exceptions skipped + logged; weekend holidays dropped;
  ranges capped at 366 days).
- **MSPDI**: `Project/CalendarUID` resolved with a cycle-safe **base-calendar chain** (derived
  calendars inherit the base week; exceptions collect across the chain); legacy `DayType=0`
  and modern `<Exceptions>` both read; `DayWorking` with no times → 480. `.mpp` via MPXJ gets
  this for free.
- **XER**: `PROJECT.clndr_id` → CALENDAR row (fallback `default_flag=Y`); packed `clndr_data`
  read with anchored patterns (`(0||<1-7>()` day nodes, `s|HH:MM|f|HH:MM` spans,
  `(0||N(d|<serial>)` exceptions, Excel serial epoch 1899-12-30); grid-less rows walk
  `base_clndr_id`, then `day_hr_cnt`, then default.
- **Fail-soft**: any calendar surprise logs + degrades to the 8h/Mon-Fri default — never sinks
  the file. `Save .json` round-trips **holidays** now. Goldens' calendar IS the textbook
  standard (verified + pinned) → parity untouched.

**PR #71 (ADR-0029) — XER per-task cost roll-up:**
- `xer._costs_by_task` sums TASKRSRC assignment costs + PROJCOST expenses per task:
  `actual_cost` = act_reg+act_ot+expense act (ACWP basis); `cost` = actual + remaining
  (at-completion total); `budgeted_cost` = Σ target_cost **clamped ≥ 0** (the BAC/EV rule;
  credits in actual/remaining preserved). **Absence is honest**: fields set only when the
  file carried a value — cost-less `.xer` identical (EVM stays NA); the curated fixture has
  no cost columns (pinned). Cost-loaded `.xer` now drives real SPI/CPI/TCPI.

**PR #72 (merged) — self-review fix:** **recurring MSPDI exceptions** (Occurrences ≠ day
span) are skipped + logged instead of contiguously expanding into weeks of false holidays
(one weekly "Fridays off" pattern erased ~36 working days).

**PR #73 (merged) — calendar visibility:** the report page shows a **Working calendar** panel
(name, h/day + exact minutes, work week, holidays w/ 10-date preview) and `/api/analysis`
carries a `calendar` object — the imported time basis is verifiable on the page.

**PR #74 (merged, ADR-0030) — M15, the last milestone:** deck read locally (Layout JSON;
DataModel XPress9-compressed → reconstructed formulas, ambiguous measures deferred pending DAX
export); adopted **float bands** (0/<5/<10d, calendar-aware, offenders cited; 0-day band ==
Acumen Critical 41/37), **completion performance** (ahead/on/behind, avg days, duration
ratios, **MEI**, staleness), and the **three-method `/forecast`** (CPM / completion-rate /
IEAC(t)) with the per-version drift table; 22 metric-dictionary entries; RTM A6 +
FINAL-REPORT closed.

**PR #75 (merged) — exact-ratio IEAC(t):** the forecast divided by the 2-decimal display
SPI(t) (golden P5 read 9 days early); the math now uses the exact ES/AT ratio (display still
rounds). Plus a /forecast falsy-zero display trap (#67 class).

**PR #76 (merged) — user-docs catch-up:** USER-GUIDE + README now cover the imported
calendar, the three new report panels, and the /forecast page (everything #70–#75 shipped).

**PR #77 (merged) — the unique desktop icon + favicon:** `packaging/make_icon.py` redesigned
(stdlib, 4x supersampled, deterministic): dark tile + white ▲ + Gantt waterfall + gold
data-date line, 5-entry 256..16 PNG-in-ICO; same bytes = `/static/favicon.ico` + Linux PNG;
sync/determinism pinned by tests. Installer: `packaging\windows\Install-Desktop-Shortcut.ps1`.

**PR #78 (merged) — the icon opened a dead port:** `pythonw.exe` starts with
stdout/stderr = None; uvicorn's logging setup touched them and the server died right after
the browser-open timer. `launcher._ensure_streams()` rebinds missing streams to devnull
(never a log file — request paths carry schedule names). Regression drives the real
uvicorn.Config with None streams.

**PR #79 (merged, ADR-0031) — Path Analysis + ask-the-AI:** `/path` over the SSI-parity
driving-slack engine: target UID (session target pre-fills), user secondary/tertiary
day-bands, data grid LEFT (add/remove MS-Project fields; tier/substring filters;
hide-100%-complete), **scalable** Gantt RIGHT (px/day zoom, month ticks, gold data-date
line); `/api/driving` extended with grid fields + ISO dates. **Ask the AI** (`ai/qa.py`,
`POST /api/ask/{schedule}`): engine-computed cited fact sheet; Null backend = matching
facts verbatim; a model answer containing any figure the engine never computed is
discarded wholesale.

**PR #80 (merged, ADR-0032) — real-file fixes:**
- **Driving tiers classify on whole working days** (slack floored on the schedule's
  calendar): real stored dates carry time-of-day raggedness, so chains SSI shows at
  "0 days" carried 30–450 minutes here and fell out of DRIVING (operator measured **4 vs
  SSI's ~66**). Goldens are exact day multiples → parity untouched; boundaries pinned.
- **The server killed itself mid-load**: async `/upload` parsed on the event loop, starving
  heartbeats past the 10s grace → the auto-shutdown watchdog fired. Upload now runs in the
  threadpool; an in-flight request counter holds the watchdog; completions refresh the beat.

**PR #81 (merged) — state-docs recovery:** the prior session's final HANDOFF consolidation
was stranded on the work branch after #80's merge snapshot; restored as base + updated for
the merged state (this file's lineage).

**PR #82 (merged) — the synthetic verification battery (`docs/TEST-PROJECTS.md`):**
`tools/make_test_projects.py` deterministically generates 8 fictional MSPDI files into
`tests/fixtures/test_projects/` with an **MS-Project-faithful block calendar**: **TP1**
progressed + ragged actual times (driving tiers to UID 43 = 13/1/2/2; completed UIDs carry
210/210/120 MINUTES that floor to DRIVING — the #80 4-vs-66 class as a fixture); **TP2**
4×10 Mon–Thu 600-min calendar + 4 holidays (float bands 7/12/13; the exactly-44-day task
stays OUT of High Duration — calendar-true boundary); **TP3** hand-seeded DCMA counts
(Logic 4 / Leads 2 / Lags 3 / FS 76% / Hard 2 / Neg-float 3 / High-dur 2 / Invalid 4 /
BEI 0.62); **TP4 v1–v5** monthly series whose v4 erases UID 19's actual start AND quietly
slips its baseline (both MANIP signals fire, pinned; honest v2→v3 fires neither). Plus the
MSP **VBA module** (SF_VerifyImport / SF_SaveAsMpp / SF_ImportFolderToMpp) and per-file
SSI/Fuse recipes with pinned expected values. The operator's MSP import caught a real
generator bug (top-down summary rollup gave UID 0 a year-0001 baseline) — fixed
deepest-first + a battery-wide date/duration sanity guard.

## Lessons learned (carry forward)
- **Real stored dates are ragged to the minute; SSI thinks in whole days.** Any tier/driving
  classification must compare on the floored-day axis or real files undercount the driving
  path drastically (4 vs 66). And **never run imports on the event loop** — heartbeats starve
  and the auto-shutdown watchdog kills the server mid-load (in-flight requests now hold it).
- **The curated goldens (Project2–Project5) are self-contained; real `.mpp` exports are NOT.** The MSPDI
  importer (the `.mpp`→MSPDI→model path) was stricter than both the CPM engine and the XER importer.
  Real files need tolerance for: **external/cross-project predecessor links** (drop), self/duplicate
  links (drop), **ALAP** and **dateless constraints** (→ASAP), **timezone-tagged dates** (→naive local),
  **out-of-range %-complete** (clamp 0–100), **negative scheduled/actual costs** (keep; clamp only the
  baseline/BAC to ≥0). All in `importers/mspdi.py` + `importers/_common.py` + `model/task.py`.
- **The §6 "every statement cited" gate is a real crash surface.** A schedule-level DCMA check (Critical
  Path Test, CPLI) that FAILS had no per-activity offenders → uncited finding → `UncitedStatementError`
  → every page for that schedule 500'd. Fixed by citing the tested/most-negative-float activities AND a
  fallback in `recommendations._dcma_findings` (cite the finish-controlling chain for any offender-less
  failed check). **Any new finding source must guarantee a citation.**
- **Multi-version views must degrade, never 500** on one bad file — see `_solvable_versions()` in
  `web/app.py` (skip + name unschedulable versions).
- **Parity is the guardrail for all of this:** every tolerance/normalization only fires on constructs the
  curated files lack, so goldens parse byte-identically (145 tasks, 176/178 links) and `pytest -m parity`
  stays 10/10. Run it after any importer/engine change.
- **Acumen "summary" count excludes the UID-0 project row** (briefing uses 18, not 19).

- **Re-create the branch from origin/main after EVERY merge** before new work — building on
  the stale pre-squash tip made PR #80 initially dirty (it dragged the merged #79 commits);
  repair = cherry-pick onto fresh main + `-s ours` absorb of the old tip (no force-push).
- **The Stop hook flags GitHub's own squash commits** (committer noreply@github.com) when the
  local branch sits on main with nothing pushed: resolve with
  `git reset --hard origin/claude/clever-carson-uovtkk` — never rewrite merged history.
- **The GitHub MCP token can expire mid-session** ("requires re-authorization"): PR
  state can still be inferred via `git ls-remote origin main` (tip changes on merge);
  creating PRs/reading CI needs the operator to re-authorize the connector.
- **Heavy work must never run on the event loop** and **classification must use SSI's
  whole-day axis** (see PR #80 above) — both bit on the operator's first real-file run.

## Operator environment (CRITICAL — this caused most friction)
- **Windows, work laptop, NO admin rights.** Cannot run MSI installers (`winget` Java install exits 1602).
  → Java via the **portable JRE zip extracted into `…\tools\jre\`** (no admin). Steps are in
  `docs/USER-GUIDE.md` + `README.md`.
- Install folder: `C:\Users\dpolitte\Documents\Schedule-Manipulation-Analysis-Tool-Experiment`.
  PowerShell needs the `.\` prefix: `.\.venv\Scripts\Activate.ps1`. Editable install — after
  `git pull origin main` no reinstall is needed unless deps changed.
- The launcher prints `…serving the dashboard at http://127.0.0.1:<RANDOM-PORT>`; the dark
  **"▲ SCHEDULE FORENSICS"** page is the real tool. A separate **OLD program on `127.0.0.1:5000`**
  (white, "Schedule Manipulation Analysis **Tool**", JSON paste box) is a stale pre-greenfield app — NOT
  this codebase; tell the operator to ignore `:5000`.
- Operator workflow: merge each PR on GitHub, then `git pull origin main` + relaunch. They paste
  PowerShell logs/screenshots; red import notices name the file + reason (CUI-safe) — ask for that text.

## Green state
**Re-audited 2026-06-17 on fresh `main`@#126 (`d468bf8`) from scratch — full CI-exact gate:
906 passed, 3 skipped; parity 10/10; engine cov 97%; overall 95.21%; ruff/format/mypy/bandit all
exit 0.** The doc-guard `tests/test_state_docs.py` passes (this HANDOFF names ADR-0067, the highest
on disk); the air-gap/egress guards pass (36). The 3 skips are the real-`.mpp`/Java cases — no
`.mpp` fixture travels into the container (`00_REFERENCE_INTAKE/` is git-ignored + empty).
CI also runs pip-audit on Python 3.11 + 3.13. Verify locally:
`ruff check . && ruff format --check . && python -m mypy && python -m pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && python -m pytest -m parity && bandit -q -r src`.
(In a fresh remote container run `pip install -e '.[dev]'` FIRST — the preinstalled venv ships
without the web/dev deps. Use `python -m pytest`, not bare `pytest`: the PATH `pytest` is a
separate uv tool that cannot see the editable install. A doc-guard test
`tests/test_state_docs.py` requires this HANDOFF to name the highest ADR on disk.)

## Next steps / open items — THE M18 WORK ORDER (operator, 2026-06-12) — **COMPLETE**

**ALL EIGHT M18 ITEMS SHIPPED (see the strikethroughs below); the post-M18 tab-visuals
follow-ups #103–#113 are also merged.** This section is retained as the work-order record.
The only outstanding verification is real-data: re-deposit `Project2_Duration_Bomb.mpp` and
confirm the ADR-0043 computed finish **2027-02-24** (the pre-ADR-0043 mandate below quoted
2027-03-04 / 8-5-2026 — superseded once summary logic was lowered; see ADR-0043), completed
tasks visible on /path at their actual dates, the "dates not supported by logic" finding
citing the template tasks, and the hide-completed toggle (ADR-0051) acting on real rows.
The original backlog, for the record:

1. ~~Path Analysis completed tasks never show~~ (PR #91, merged; Duration Bomb
   re-verification owed, see above).
2. ~~Use the FULL screen width~~ (PR #91, merged).
3. ~~Sparse-logic CPM mandate~~ (PR #91/ADR-0034, merged; re-verification owed).
4. ~~AI at full power~~ (PR #92, COMPLETE: interpretive mode + ask panel on ALL
   pages with workbook-wide facts + standing disclaimer + Briefing reformat
   [ADR-0035] + the OpenAI-compatible second local backend with the dual-model
   figure-agreement cross-check [ADR-0036]; loopback-only egress preserved).
5. ~~Forecast-drift ANIMATION + locked axes on the animated visuals~~ (PR #93/ADR-0037:
   the /forecast Bow-Wave-style drift stepper on a locked date axis + the Bow Wave count
   axis locked to the global max across snapshots. Trend charts were already
   locked-by-construction across versions; the Path Gantt is a single-schedule timeline
   with no animated metric axis — both assessed, no change needed).
6. **PBIX visual reproduction** — docs/PLAN/PBIX-VISUALS.md is the spec (14 pages,
   engine coverage map; DAX intake complete, RatioMeasure is a dangling binding).
   **Page 1 (Metrics / Schedule Card) REPRODUCED** (PR #94/ADR-0038). NEXT tranches:
   Cross File Comparison (pg 4), Float Analysis (pg 5), the Finishes month curves
   (pg 6–7), WBS-grouped Completion + SPI/ES pivots (pg 8–9), Slippage curves (pg 12),
   the Carnac forecast cards (pg 13). Remaining gaps: activity-type profile, WBS
   pivots, start/finish curves, TotalFloat/FreeFloat sums, avg-tasks-per-month.
7. ~~CPM path-evolution animation~~ (PR #100/ADR-0044: the `/evolution` Bow-Wave-style
   stepper — per version the critical path with entered/left/stayed + duration-change
   badges, and a callout for finish movement + schedule-optics signals [durations cut on
   path, logic removed], flagging a path that sheds work while the finish holds steady).
8. ~~Forecast explainer + Trend page expansion~~ (PR #102/ADR-0046: the `/forecast`
   methodology explainer + static spread ruler; `MetricTrend.offenders_by_version` + the
   `/trend` "Quality drill-down & animation" panel [locked-axis per-metric offender-count
   stepper + per-version offender lists] + the full per-version Excel/Word offenders table).
   **M18 COMPLETE — all eight items shipped.**

1. **TP1-vs-SSI: CLOSED with full parity (2026-06-12).** All 18 traced tasks matched;
   live driving path UID-for-UID; non-zero slacks exact to SSI's display rounding;
   sub-day completed-task fractions are a documented model residual the whole-day floor
   absorbs (PARITY-REPORT + TEST-PROJECTS carry the verified tables). Remaining battery
   work: **Fuse re-run on a rebuilt TP3.mpp** (the Leads tasks-vs-links and
   Insufficient-Detail definitional rows), and **TP4 v1–v5 in the tool** (Compare must
   flag the UID-19 manipulation pair; Trend + Bow Wave/CEI on the five snapshots).
   The real-file 4-vs-66 re-test from #80 remains worthwhile but is now low-risk.
2. **Respond to operator feedback** on real `.mpp`/`.xer` files — tolerance classes live in
   `importers/_common.py`; ALWAYS re-run `pytest -m parity`. Watch how the new surfaces
   (Path Analysis, ask-the-AI, float bands, `/forecast`) read on real data.
3. **Deck measures awaiting a DAX export** (ADR-0030): EPI, RatioMeasure, Start-and-Finish
   Ratio — implement exactly when the operator provides the measure text; do not guess.
4. **per-task calendars** (P6 `TASK.clndr_id`, MSP resource calendars) — only if the
   operator's real programs mix calendars materially.
5. If the operator enables real Ollama generation: watch quality — narrative/briefing
   rephrases are figure-gated (`reattach`), ask-the-AI is figure-subset-gated (`ai/qa.py`).
6. **Tune the Bow Wave / CEI visuals** against real data vs the reference decks if they don't match.
7. Keep `docs/STATE/HANDOFF.md`, `SESSION-LOG.md`, and `docs/FINAL-REPORT.md` test counts current.

## Resume command for a NEW session
Paste this as the first message:
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first — work the OPERATOR
> BACKLOG in its listed order. `main` is green & current at **#126** (`d468bf8`); the last CODE PR
> was #125 (Fuse Ribbon), #126 was a docs-only reconcile — there is no open code PR.
> Recreate the work branch from fresh main (`git fetch origin main && git checkout -B
> <fresh-branch> origin/main`), then tackle the REMAINING items, **bugs first**: (A) the Path
> Analysis driving/secondary/tertiary-to-target
> chart is wrong (`path.js` + `/api/driving`) and the `/analysis` driving-path + project-schedule
> Gantt scaling is wrong (it's %-squeezed with no adjustable scale — convert to the `/path`
> px-per-day + scroll model); **I owe you a question — please attach a screenshot of the wrong
> `/path` chart and a `/analysis` Gantt so I fix them precisely.** Then (B) MS-Project-style
> dropdown filters (select-all/deselect), (C) the path filter on BOTH `/analysis` and `/path`
> with hide-completed + adjustable scale + full wrapped task names, (D) the Fuse year Trend/Phase
> view, (E) Data-Date/Slippage redesign (overlaid lines + show/hide legend), (F) Bow-Wave totals
> + target-UID highlight. Insufficient Detail™ / Float Ratio™ / EPI / RatioMeasure stay DEFERRED
> until you supply the exact Fuse/DAX formula — don't guess. Setup: `pip install -e '.[dev]'`
> first; drive the gate with `python -m pytest` (PATH `pytest` is a separate uv tool); keep
> `pytest -m parity` 10/10; run bandit UNPIPED; open DRAFT PRs (don't merge — I do that); never
> let schedule data leave the machine (loopback-only air-gap). Model: Opus 4.8 (1M context).
