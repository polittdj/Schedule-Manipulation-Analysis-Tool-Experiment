# Handoff — 2026-08-02e (Phase 3 UI: /sra joins the panel contract — Act III complete; ADR-0339; v1.0.155)

> ## STATUS (current) — **MERGED. `/sra` converted; Act III's panel contract is COMPLETE.**
> PR **#519** (ADR-0339, **v1.0.155**) merged as **`17a9c64`**. `/sra` was the last unconverted Act
> III route and is now inside both census modules, so every route in the act is covered. Branch
> restarted from `origin/main` with `--prune`, working tree clean, **no check-ins armed** (the PR
> check-in was deleted on merge). Full suite **on the merged tree: 3329 passed, 2 skipped, 1
> failed** — the single failure is the ADJUDICATED `/analysis` focus→tip intermittent
> (`test_float_tip_dismiss` this run, `test_float_tip_scroll` the run before — the family alternates,
> which is itself the evidence). Confirmed pre-existing by running those modules against
> `origin/main`'s own `app.py` **before** this change: 2/1/1 failures there vs 1/1/1 on the branch.
> Do NOT chase it.
>
> ## `/sra`, before → after (panel count UNCHANGED at 15)
> heads/tools/⛶/takes/chips **0,0,0,0,0 → 12,12,12,12,12**, panelkit **0 → 1**, and it gained the
> DoD **context line** it never had (`page-lede` **0 → 1**; the takeaway h1 was already there).
> Three panels stay bare by the standing scope note: the two `_status_stack` header bars and the
> global Ask panel. Contract module **9 → 18** tests, chromium **6 → 9** (the 9→14 figure that
> appeared here mid-session predated the audit's four extra gates — 18 is the merged count).
>
> ## Two carried figures were wrong — both corrected
> 1. **`_sra_report_blocks` does not render `/sra`.** The carried ≈550-line estimate attributed 295
>    lines to it; it builds the **`.docx`** report for `/export/{fmt}/sra`. The page's 15 panels come
>    from `_sra_body`, `_sra_explainers`, `_sra_overrides_table`, `_ssi_panel`,
>    `_correlation_matrix_panel`, `_jcl_panel` and `_what_could_go_wrong_header`.
> 2. **15 panels re-confirmed** on this tree (the long-carried "13" stays dead).
>
> ## Three decisions worth carrying
> 1. **The chip is the SINGLE-file chip** — deliberately the mirror image of ADR-0338. Every model
>    on `/sra` (SSI, OAT, JCL, legacy MC) resolves through `_sra_selected`, and the top panel exists
>    to say which file that is. A series chip would render `v1→v2` and claim versions no figure on
>    the page came from. `/risks` went the other way because its change findings really are a pair.
> 2. **⤓ EXCEL is SHORT BY TWO, on purpose.** This is the first route where rank 3 ("never a dead
>    **or lying** link") costs something: the "which risk model" explainer is guidance prose, and the
>    JCL panel's sheets ride `/export/xlsx/sra` only once the file is cost-loaded. Both keep head +
>    ⛶ + chip and lose only the glyph that would lie. The test asserts the **shortfall**, so
>    "give every strip a ⤓ for consistency" fails.
> 3. **Four takes are figure-free by necessity.** Those panels are empty chart hosts until `sra.js`
>    fetches `/api/sra` — quoting a P50 at render time would be fabricating one (Law 2). They state
>    what the panel will draw and from what; the other eight quote figures the panel itself renders,
>    each worded to read correctly at **zero**.
>
> ## The gate that was vacuous — found by RUNNING the revert, again
> `test_the_sra_takeaway_quotes_figures_the_page_renders_below_it` **could not fail**: it searched
> the KPI strip for "label … number" with `.*?` under `re.DOTALL`, and that dot-star spans the whole
> six-card strip, so **any card's digit satisfied any label**. Rewriting the headline to quote two
> figures the page never renders (`incomplete`, `neg`) left it green. Fixed by parsing the strip into
> `label -> value` pairs and comparing each figure to **its own** card. **NEW named shape: an
> assertion whose wildcard crosses the very boundary the rule is about.** Four PRs in a row have now
> shipped a would-be-vacuous gate caught only by the revert pass.
>
> ## The adversarial audit found SIX more real defects — all in my own new code
> A four-lens audit (vacuous gates · Law-2 · render-correctness across session states · consistency
> with the converted routes) ran over the diff; **every finding was re-verified by the lead against
> the code before anything was touched** (ADR-0240). Six confirmed and fixed:
> 1. **The ⤓ was a DEAD LINK whenever no version solves** — `/export/xlsx/sra` answers **400** in
>    that state. The export attr, the ⤓ and the chip now degrade together (`solvable`); head + ⛶ stay.
> 2. **The JCL take said "No budgeted cost on this file" when the real reason was that nothing
>    solved** — a false claim about a possibly cost-loaded file. Third branch added.
> 3. **The JCL loaded take read a SETTING as a result** — `st.jcl_confidence` is the target the
>    frontier is drawn at, not a computed JCL. Reworded.
> 4. **"N versions loaded" counted `len(st.schedules)`** — every loaded file, across other Projects
>    and EXCLUDED versions — while the picker beside it is built from `ordered_versions()`.
> 5. **The takeaway gate bound only the FIRST TWO figures** — the h1 appends ", with N risks
>    registered", so a fabricated third passed. Every figure in the h1 is now bound.
> 6. **The ⤓ test asserted only the NEGATIVE half of rank 3** — a ⤓ on a panel with no `data-export`
>    is an inert button and passed. Glyph and export are now paired per panel.
>
> Three were **REFUTED** by the lead and not acted on: the "Risk inputs" take does mirror the panel's
> own semantics (`st.sra_overrides` IS the legacy per-activity override set); the correlation take
> reuses the panel's pre-existing "drives the run" wording verbatim (re-litigating that is not a UI
> conversion's job); and two constant-vs-constant assertions were flagged as tautological — which was
> **correct**, so they were DELETED rather than defended.
>
> ## The real defect this round, caught by an EXISTING gate
> `test_no_mdash_entity_sentinel_values_remain_in_app_source` failed on my own new take: I wrote the
> missing-file sentinel as `'&mdash;'` when the required form is the literal `'—'` (the line
> directly below mine already used it). Fixed in the render. **A blanket source-level ban is worth
> more than it looks — it caught a value that would have rendered fine and escaped wrong later.**
>
> ## Verification (every number read from a run this session)
> **14 reverts, all confirmed to change the RENDERED page before the module ran, every module run
> WHOLE** (a `-k` filter can silently deselect the target): W1 extra panel · W2 head dropped · W3
> panelkit dropped · W4 / W4b the explainer given a ⤓ (markup + browser) · W5a chip names the wrong
> file · W5b chip becomes a series chip · W6a the lede dropped · **W7 the vacuous one** · W8 a
> fabricated P50 in a take · W9 panelkit dropped (browser) · W10 `/sra`'s heads removed · **C1**
> jarvis hides `.sf-tools` · **C2** apollo renders the chip transparent. C1/C2 fail **all four**
> theme rows including `/sra`, so the style probe is live on this route.
> **Plus 8 audit-driven reverts:** **A1** the export attr stops degrading · **A2** the ⤓ stops
> degrading · **A3** the JCL take reverts to the false claim · **A4** the version count reverts to
> `len(st.schedules)` — which needed an **EXCLUDED version** to discriminate, since the two counts
> are identical on the goldens · **A5** the h1 appends an unbound figure · **A6** a fabricated
> mean-finish **DATE**, which the guard's original pattern missed · **J1/J2** the cost-loaded JCL
> branch, where **J2 is the lying-link regression itself** (the panel keeps its ⤓ while the export
> stops carrying the JCL sheets). Contract module **9 → 18** tests, chromium **6 → 9**.
>
> ## Two limits worth carrying
> When NOTHING solves, `_what_could_go_wrong_header` returns `""` so `/sra` has **no takeaway at
> all** — pre-existing empty-state behaviour, recorded not widened into this PR.
>
> ## A limit worth carrying (found by W10)
> `test_the_head_strip_survives_all_four_themes` probes only the **FIRST** `.panel-head` on a page —
> removing three of `/sra`'s heads left it green because another panel's head was still first. It is
> not vacuous (C1/C2 fail it) but its per-route strength is "at least one head renders". The markup
> census counts; the NEW ⛶-only strip shape got its **own** four-theme test.
>
> ## ⇢ NEXT — the queue
> 1. **`DOM_PENDING`'s 7 modules**, then the **DoD ledgers** — the DD-line ledger must **EXCLUDE**
>    non-time-axis charts (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis).
> 2. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering half
>    — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith
>    split 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. OR-04 stays with the operator.
> 3. **Carried UI gap (measured, not fixed):** `/briefing`, `/path` and `/compare` render a bare
>    takeaway h1 with **no** `page-lede`. The lede is the majority pattern (`/evm`, `/scurve`,
>    `/margin`, `/groups`, `/integrity` carry one). Each is another page's PR.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** (the in-memory `_ANALYSIS_CACHE_MAX`, ADR-0292 — the
> DISK cache is ADR-0335/0336, untouched by it) · **SPLIT-23** · **A0293-UI** · Project5's SSI
> export contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass
> packing · ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase (it failed once in this session's `tests/web` run and passed alone
> immediately after) · ADR-0332/0333 scope notes · ADR-0335 scope note · **ADR-0336 scope note:**
> two concurrent processes sharing one `$SF_CACHE_DIR` read each other's marker as a dead run and
> clear — correctness-safe, accepted not engineered · **ADR-0337/0338/0339 scope note:** the Ask
> panel and the shared `_status_stack` bars stay bare, pinned by a test on BOTH `/briefing` and
> `/sra`.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus:** the caption/halo
> set; "listing the fields to reset is maintainable"; a blanket `sf-` localStorage sweep;
> "`tooltips.js` is one of the observer defects" (it is the EXEMPLAR); "querySelectorAll CALL COUNT
> measures observer cost" (measure NODES RETURNED); "a shared observer helper module is the clean
> fix" (ADR-0316 load-order); "`sysmon.js` is an unfixed idle pump" (the cost was the SERVER loop);
> "two servers bound 8321 simultaneously" (MEASURED false) · "the surviving server is itself the
> bug" (false: `idle_grace=600` is by design) · "a bind-probe answers 'is the port taken?'" (false
> on Windows — connect-probe) · "a hardened opener contains an empty ProxyHandler" (false — assert
> ABSENCE) · "`secure_delete=ON` is the obvious Law-1 cache hardening" (MEASURED false: 26 s on the
> quit path) · "a bare DELETE leaves plaintext so a residue test is a real gate" (false on Debian —
> assert RECLAIMED SIZE) · "`wipe_gen` stops a late write re-populating the cache" (only
> `/session/wipe` bumps it) · "`atexit`/`finally` cover a graceful stop" (false for SIGTERM) ·
> "a pid identifies the run that holds the cache" (false: reused, and `os.kill(pid, 0)` TERMINATES
> on Windows) · "asserting a clean quit leaves no claim is a real gate" (false on the unlink path —
> force the Windows FALLBACK) · "`/driving-path` is a fifth unconverted page" (false: that is its
> EMPTY STATE) · "counting `<div class=panel` finds every panel" (false: it misses the QUOTED form) ·
> "a DoD rule tested on one route is tested" (false) · "`/sra` is 13 panels" (measured: **15**) ·
> **NEW — "`_sra_report_blocks` renders `/sra`"** (false: it builds the **.docx** export) ·
> **NEW — "a rank-3 ⤓ rule that has always passed is tested"** (false: it was FREE on all three
> earlier routes; it only bites where a panel's data is genuinely not in the workbook) ·
> **NEW — "a four-theme head-strip probe covers a page's heads"** (false: it reads only the FIRST
> `.panel-head`).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary
> mutation — `cp` from a scratchpad copy.** **When reverting to prove able-to-fail, revert the
> CALLER — and check the revert actually removed the behaviour** (this session's harness re-rendered
> the page after every revert before running the module). **A `-k` filter can silently DESELECT the
> very test the revert targets — run the whole module.** **A theme/computed-style assertion needs
> its own CSS revert to prove it can fail.** **`re.DOTALL` + `.*?` across a repeated element makes a
> "this value belongs to that label" assertion vacuous — parse into pairs instead.** **pytest stdout
> to a FILE is block-buffered — the dot count lags badly; not a stall.** **The missing-value sentinel
> in `app.py` is the literal `—`, never `&mdash;`** (a source-level gate enforces it). **The /risks
> page title is `Risks & Opportunities` in source (NOT `&amp;`).** **A hash-for-hash `sed` does NOT
> update abbreviated digests quoted in prose — grep the prefix too.** `pkill -f` with the pattern in
> the killer's own command line kills the killer. CI can take ~11 min to register check runs;
> `test (3.11)`/`(3.13)` run ~30 min. Full local suite ≈17 min. `TestClient` follows 303 and CONSUMES
> one-shot banners; **plain `TestClient(app)` does NOT run the lifespan — only `with` does.** Parity
> marker ≈2m38s. Headless Chromium hides scrollbars. `caplog` needs
> `logger="schedule_forensics.<module>"`. **Playwright `bounding_box` / `page.screenshot(clip=…)` are
> VIEWPORT-relative.** **localStorage is per-ORIGIN.** Bundled chromium:
> `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Containers RESTART mid-run: statics
> FOREGROUND first, reinstall pip after resume. After a squash-merge:
> `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
> origin/main` — **NEVER amend the merged commits.** **Version-bump sequencing:** bump BEFORE the
> suite (this session's 4 installer failures were exactly that, and are expected). Never sleep in a
> sync-Playwright route handler. Never `from tests.web...` in a test. **A parse-time-rendering JS
> module + a later chartframe.js = first-paint crash** (ADR-0316). **A stray `*/` makes CSS
> error-recovery swallow the NEXT rule silently.** **`cd` in a Bash call persists across calls — use
> absolute paths.**
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
