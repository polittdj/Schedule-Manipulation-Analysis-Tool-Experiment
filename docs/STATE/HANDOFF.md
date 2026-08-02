# Handoff — 2026-08-02f (Phase 3 UI: the DOM caption ledger reaches EMPTY; ADR-0340; v1.0.156)

> ## STATUS (current) — **IN FLIGHT.** `DOM_PENDING` is empty; AXIS-TITLES is CLOSED in both media.
> Branch `claude/polaris-phase3-dom-pending-frgdqj`, restarted from `origin/main` at **`d3ff6ed`**
> (#520 was already merged when this session opened — checked FIRST, as the kickoff asked).
> ADR-0340, **v1.0.156**. `DOM_PENDING` went **7 → 0**, and with `PENDING` empty since ADR-0330,
> **ADR-0298's deferral is closed for good**: every data visual in the tree, in BOTH media, names
> its own dimensions.
>
> ## What actually shipped (7 modules, but only 6 captions)
> Six gained a caption on the table they already built: `drilldown` (the shared drill MODAL),
> `driving_tiers`, `findings_drill`, `ribbon_drill`, `scorecards` (the ONE table whose row unit is a
> **percentile**, not an activity) and `whatif` (**both** grids — they share a column-header set, so
> the caption is the only thing distinguishing OFF-the-path from ADDED-to-the-path).
>
> **The seventh was never captionable.** `sra_risk.js` renders NO visual and never could — no
> `createElement`, no `appendChild`, no `innerHTML`; it writes `.value` back into server-rendered
> inputs and toggles `aria-invalid`. It was mis-triaged into the DOM ledger at ADR-0326 and had
> overstated the remaining work by one for four ADRs. Moved to `EXEMPT`, **re-triaged, not
> captioned** — and that is exactly why these ledgers are NAMED LISTS and not counts.
>
> ## The decision worth carrying: WHERE the helper lives is a load-order finding
> ADR-0326's mechanism was an inline `el("caption", {class:"ch-atd"}, …)`. That does not survive
> seven callers, because their module-local `el()` helpers take **three different signatures**
> (`(tag, attrs, text)` · `(tag, {text})` · `(tag, text, cls)`) — a detector accepting all three
> would be **looser than the rule**, the standing gate-shape #4. So it was promoted to ONE helper,
> `SFGantt.tableCaption`, exactly as ADR-0298 did for SVG; `workbench.js`'s two inline captions
> converted too, and no module outside `gantt.js` may now even name `.ch-atd`.
>
> **It is NOT in `chartframe.js`, and that is the finding.** `chartframe.js` owns the SVG helper and
> looks like the obvious home — but **the layout emits it AFTER `</main>`**, while every captioned
> table is built by a script INSIDE the body, and **`whatif.js` renders SYNCHRONOUSLY at parse
> time**. A `window.SFChartFrame` helper would have been `undefined` at the instant whatif draws:
> two grids silently uncaptioned, **with every source-level assertion in the suite still green**.
> `gantt.js` is head-loaded, already renders the OTHER B1 mechanism (the `buildTierScale` slot), and
> is already the shared DOM utility four of these six call for `fmtMDY`. The ordering that makes it
> correct is now **pinned by a test**, whose failure message says to RE-DERIVE the placement rather
> than delete the test. Also `insertBefore(firstChild)`, not `appendChild` — `<caption>` must be the
> table's first child, and six of seven call sites sit next to a `<thead>` append.
>
> ## Verification — three reverts, and the third is the one that matters
> | revert | result |
> | --- | --- |
> | `insertBefore` → `appendChild` in the helper | harness **4 assertions fail**, incl. first-child |
> | helper neutered to `return null` | chromium **11 of 11 fail** (229 s of real timeouts) |
> | **`whatif.js`'s caller removed only** | chromium **5 fail, 6 pass** |
>
> Two more, because a STYLE assertion's failure mode is SILENCE and needs its own CSS revert:
> `.sf-drill-dialog{background:var(--muted)}` fails **3 of 4** modal theme rows — **jarvis survives
> it**, because its broad `.panel` rules override the dialog background first (the known clobber
> family, behaving as documented) — so a second revert, `caption.ch-atd{color:transparent}`, was
> run and fails **all 8** theme rows across both rendering contexts.
>
> The whatif-only revert is the one an all-or-nothing revert cannot give: the 5 are the whatif test
> + the 4 theme rows (both driven on `/evolution`), and the other **six modules kept passing** — so
> each test tracks its OWN module rather than a shared global. New:
> `tests/web/js/dom_caption_harness.mjs` (**18** checks) and `tests/web/test_dom_captions_chromium.py`
> (**15** tests) driving every caption in a real browser through its REAL trigger — parse-time ·
> post-fetch · click · modal · a live Monte-Carlo run — in all four themes and in TWO rendering
> contexts (page flow + the drill overlay). `test_axis_titles.py` **29 → 37** collected (measured
> against `origin/main`'s own copy, not inferred).
>
> ## Full-suite triage — 6 failures, all adjudicated
> **3347 passed, 2 skipped, 6 failed** on the first full run; all six resolved or explained:
> * **4 installer failures** — the version bump invalidated the embedded wheel. Rebuilt
>   (`python -m build --wheel --outdir dist/wheel` then `tools/installer/build_installers.py`, nine
>   installers at ~1.67 MB); `tests/installer` now **52 passed**.
> * **`test_r11_panel_contract::test_the_seven_page_owned_scripts_are_byte_frozen`** — a REAL
>   consequence, re-baselined deliberately with a recorded reason (the ADR-0326/0329/0333
>   precedent): `driving_tiers.js`, `whatif.js`, `gantt.js`. The other **four frozen scripts were
>   untouched**, which is the freeze doing its job. `gantt.js`'s diff is **purely additive — zero
>   removed lines** (verified with `git diff`), and the sibling **28-call-site census PASSED
>   unchanged**, which is the independent check that no SVG caption moved. Module: **25 passed**.
> * **`test_float_tip_dismiss`** — the adjudicated intermittent. `app.py` is **untouched** by this
>   change, and rather than lean on the prior ruling I swapped all 8 statics to `origin/main`'s own
>   copies and re-ran: **run 1 = 1 failure, run 2 = 2 failures on the SAME pristine files**. The
>   variance is pre-existing and independent of this change. Still do NOT chase.
>
> ## Next: the DD-line ledger — RESEARCH DONE, ledger not yet written
> **No DD-line ledger exists** (searched `tests/` — confirmed). This is a BUILD. The population was
> censused this session **from evidence, not grep**: every chart DECLARES its own X axis in its
> `SFChartFrame.axisTitles` call, so the 28 call sites were parsed and split by `xLabel`. Start
> from this table, not from a fresh guess:
>
> | bucket | members (by call site) |
> | --- | --- |
> | **TIME-AXIS — the rule applies** | `cei` (Month) · `curves` (Month) · `drift` (Forecast finish date) · `margin_dashboard` ×2 (Status date) · `scurve` (Month) · `sra` ×2 (Finish date) · `sra_jcl` L136 (Finish date) · `sra_ssi` ×2 (Finish date) · `resources` (Period … commencing) |
> | **NOT time-axis — EXCLUDE** | `histogram` (Total float band) · `scatter` (Total float) · **`sra_jcl` L189 (EAC — the COST axis)** · `trend_drill` (Schedule-quality metric) · `wbs` (WBS branch) · `volatility` L367 (Versions on path) |
> | **VERSION-axis — EXCLUDE, and this one is NOT in the brief** | `margin` · `trend` ×5 · `volatility` L167/L208/L251 (all "Schedule version") |
> | **needs per-call classification** | `performance.js` L472 — its `opts` is a VARIABLE passed by the caller, so its xLabel cannot be read statically like the other 27 |
>
> **The version-axis category is the finding.** The brief named three exclusions; there are **nine
> more**, and the version-axis family is the interesting one: a "Schedule version" axis is ordered
> by time but CATEGORICAL — one tick per loaded file — so a DD line has no position on it (every
> version has its OWN data date). Excluding it is a judgment the ledger must state, not assume.
>
> **Two more measured facts before writing the ledger:**
> 1. **There is NO shared DD-line helper.** `cei.js` (L147) and `curves.js` (L339) each hand-roll a
>    dashed marker, and the label they render is lowercase **`"data date"`** — not the
>    `DD` / `DATA DATE` `DESIGN-SYSTEM.md` §chart-contract specifies. So this is the SVG-caption
>    situation before ADR-0298: several implementations, no convention. Decide helper-vs-ledger
>    FIRST — and mind the ADR-0340 lesson that WHERE a helper lives is a load-order question.
> 2. **Four time-axis charts have NO data-date mention at all** (`grep -ci`): `sra.js`,
>    `sra_jcl.js`, `sra_ssi.js`, `resources.js`. Those are the candidate PENDING bucket — but
>    VERIFY each by rendering it before recording it as a gap (a grep count is not a render, and
>    "74 sites" is already on this handoff's do-not-trust list for exactly that reason).
>
> Behind: **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
> half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith
> split 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. OR-04 stays with the operator.
> Carried UI gap (measured, NOT fixed): `/briefing`, `/path` and `/compare` render a bare takeaway
> h1 with NO `page-lede`, while `/evm`, `/scurve`, `/margin`, `/groups`, `/integrity` carry one.
>
> ## Carried forward, unchanged
> **Known intermittent: the `/analysis` focus→tip family** (`test_float_tip_dismiss` /
> `test_float_tip_scroll`) ALTERNATES between members run to run; confirmed pre-existing against
> `origin/main`'s own `app.py`. Adjudicated — do NOT chase.
> `pgrep -f <pat>` self-matches exactly like `pkill -f` — a waiter looping on its own pattern never
> exits (hit this session; use `[p]ytest` or just let the background task notify).
> pytest stdout to a FILE is block-buffered — an empty output file is not a stall.
> `cd` in a Bash call persists across calls — use absolute paths.
>
> **Standing rule:** do not put a test result in prose unless the number appeared in output you
> read that turn. **A launched run is not a result, and a piped exit code is not the command's.**


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
