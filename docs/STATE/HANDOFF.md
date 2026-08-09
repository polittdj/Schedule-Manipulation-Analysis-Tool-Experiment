# Handoff — 2026-08-09 (c) (phase 3 slice 12: the /analysis family out — the largest prefix undercount yet; ADR-0376; v1.0.184)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice11-a2syfo`
> (branch restarted from `main` ff2fe2b after #560 squash-merged; the branch NAME says slice11 —
> it is the container's designated branch, the WORK is slice 12). **Shipped code changed** —
> version bumped **v1.0.183 → v1.0.184** BEFORE the suite; wheel + nine installers rebuilt once
> after the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0376**.
>
> **Phase-3 slice 12 is CLOSED (queue item 1): the /analysis family → NEW `web/analysis.py`**
> (1,297 lines; **25 names in NINE regions**, app.py 6894–9201 non-contiguous; app.py
> **13,358 → 12,096** wc-truth) **plus the first descent since sra**: `_target_panel` (67) →
> `web/components.py` at the ADR-0350 3+-family threshold (referrers `_analysis_body` + the
> /card and /wbs routes; components' state import widened to `_Analysis, SessionState`).
> `_where_we_stand_header` moved WITH the family exactly as ADR-0375 ruled. `LAYER_ORDER`
> `… → forecast → portfolio → analysis → app`; analysis.py joins the E501 list; VIEW_MODULES +
> both whole-view-layer guard tuples gain "analysis.py" (alphabetically FIRST — before app.py).
>
> **The headline finding: the prefix undercounts by 3.6× — the largest ratio yet.** The queue
> said "analysis 356" (body 148 + data 50 + where header 158); the closure found **26 names /
> 1,275 region lines** — seventeen of the eighteen app.py names `_analysis_body` references are
> sole-referrer movers with NO `_analysis` prefix (the twelve page panels, the six DCMA
> cell/card builders minus the card, `_cites_cell`, two constants). Stays adjudicated by
> referrer: `_unschedulable_panel` (2 routes, shared) · `_find_schedule` (3 routes) ·
> `_FLOAT_HIST_BANDS`+`#:` (route-only) · `_HB_CONSUME_SEC`+comment (ZERO referrers, the
> components.py:335 documented stay) · `_BRIEFING/_BRIEF_XLSX_TITLE` · `_stack_not_measured` ·
> `_count_bar_table` · `_num`. The export route contributes NO movers (mission shape, 4th
> consecutive).
>
> ## Verification
> Oracle rebuilt per ADR-0372 recipe with the ADR-0375 TITLE-STRIPPED TP4 pool: **498 labels**
> (the 494 shape with the [empty] stage widened to ALL 60 parameterless GETs — the prior
> reference carried 56; no-silent-caps outranks count-matching). **The 4xx histogram of the
> three loaded stages — 88 (17×400 + 12×404 + 59×422) — matches ADR-0375's post-title-strip
> count EXACTLY: the population fingerprint.** The untitled-pool assert runs in the harness
> BEFORE any render (/evolution and /compare must not contain the placeholder). Target UID 22;
> three normalizers inherited (launch token normalized by exact VALUE — the harness owns the
> SessionState). Double-render determinism ×2 separate processes: **0 flapping, proven before
> any claim**. Pre-flight probe **26/26 render-proven, ZERO dark members** (third consecutive
> slice; branch states read off the rendered v5 body BEFORE anchor choice: margin takes its
> NO-candidates branch, erosion has groups, variance computable, 7 findings). Probe shape: 20
> page-side movers 3 each · the 3 API-side 3 each · `_dcma_label` 6 (the only two-surface
> member) · `_target_panel` 3 (target-set ONLY — its render condition, measured live). Proof:
> per-region byte-identity **9/9 + descent** (in-script pre AND post; re-verified after ruff
> import surgery; format-check zero reformats) · multiset **100 added / 3 removed — zero code
> lines removed** (ActivityVariance, + off_project_calendars, re-land in analysis.py
> single-line imports; components' state import superseded by its widened form) ·
> dropped-import sweep **0 readers of the 14 dropped names** (control live: 181 files import
> from web.app) · **498/498 byte-identical pristine vs cut** · falsified in the new locations
> **26/26 EXACT label LISTS** (anchors also asserted ABSENT from post-cut app.py). Sweeps:
> monkeypatch+attr over all 71 bound names → **two hits, both adjudicated** — the standing
> `app_mod.non_summary` control AND `app_mod.compute_activity_makeup` (NEW: analysis.py now
> binds a name the projection-memo spies patch; both spy /api/dashboard through app.py's OWN
> binding, no /analysis render in the test — the ADR-0297 shape, not tripped) · source-text 33
> readers → every hit adjudicated, `panelkit.js` ∈ axis_titles ∩ `_analysis_body` the positive
> control, `_TS_CAPTION_MARK`/`data-ts-caption`/drilldown tag ABSENT from moved text — **zero
> reader repoints, third consecutive slice**. Mutation battery **6/6 named** (enumeration
> guard's 15th/16th consecutive catches; mutations 2+5 in-body from the start). **One
> measurement discarded as self-polluted:** the first multiset ran while the falsify battery
> held a member mutated and the diff carried the battery's own PRB12X marker — never MEASURE a
> tree a battery is mutating; re-measured quiescent (md5-verified first), only the clean 100/3
> reported. Statics green (python -m ruff check WHOLE TREE · format zero reformats · mypy
> strict 130 · bandit · node --check per file). Full suite + parity: counts in SESSION-LOG
> (this session).
>
> ## Next
> The queue resumes at phase-3 slice 13 — by the post-cut prefix census (wc-truth; each family
> owes its OWN closure, and slice 12 re-prices the expectation: a page family's closure can run
> **3.6×** its prefix): **evm 299** (incl. `_how_we_execute_evm_header`;
> `_field_forecast_panel` already below it in forecast.py) · **performance 279** (incl. its
> header) · resources 255 (incl. `_who_is_overloaded_header`) · scurve 212 · path 194 (incl.
> `_what_drives_header`) · compare 166 (incl. `_what_changed_header`) — EACH per the ADR-0365
> recipe (closure before cut · span-scoped probe · six-mutation battery · the ADR-0372 oracle
> recipe; **the 498-label oracle with the TITLE-STRIPPED TP4 pool is the current widest
> reference — the title-strip is load-bearing, and the 88-count 4xx histogram is the
> population fingerprint: a differing count means a DIFFERENT population, adjudicate before
> use**). groups (315) stays outside the phase-3 list while ADR-0343 feature work is queued
> against it. Then the standing queue unchanged: stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages (/briefing, /path, /compare) · /groups
> Activities (ADR-0343) · installers vs known-good constraints · P80/P90 recurring-exception
> residual · doc-drift sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake";
> FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines — analysis.py now ALSO
> joins the E501 list unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse ·
> one Acumen run on a crafted sub-day-negative-float schedule · license · branch-protection
> contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0376 closed — do not re-open. NEW this session: (1) **a page family's closure can
> run 3.6× its prefix** — panels carry no family prefix; price closures by referrer walk, never
> by the census number. (2) **Never MEASURE a tree a battery is mutating** — the first multiset
> diff carried the battery's own PRB12X marker; the standing never-mutate-a-running-suite trap
> has a reverse form. (3) **The monkeypatch sweep's adjudication list GROWS as families move** —
> `compute_activity_makeup` joined `non_summary` because analysis.py now binds a name the
> projection-memo spies patch; the adjudication holds while the spied path stays in app.py, and
> a future dashboard-family slice must repoint those spies. (4) **The 4xx histogram is the
> oracle population's fingerprint** (88 on the title-stripped pool) — cheaper than re-deriving
> the population shape every slice. Standing traps unchanged (census families can be phantoms ·
> fixture population is a render condition · ruling-lag headers move retroactively ·
> live-chain payload aim · patch the patcher with landed-count discipline · `#:` blocks
> extended by eye · route referrers never block · silent-405 setup · anchored splices with
> landed-count asserts · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives
> Duration · env-defect masquerade · binding-wrap spies · named-failure rule · never mutate a
> running suite's tree (docs included) · empty sweep needs a positive control · `grep -c`
> exits 1 on zero · three-tier parity evidence · stored-start floors / non-additive rows ·
> B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis focus→tip family
> load-sensitive · five playwright-only failures pre-existing, CI-invisible · oracle telemetry
> labels normalized by VALUE · scratchpad harnesses hardcode the repo root · two ruffs on
> PATH — run `python -m ruff`). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
