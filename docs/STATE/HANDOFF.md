# Handoff — 2026-08-09 (b) (phase 3 slice 11: the /portfolio family out, and the census families that dissolved; ADR-0375; v1.0.183)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-m2ulco`
> (branched from `main` 6f5d816 after #559 squash-merged). **Shipped code changed** — version
> bumped **v1.0.182 → v1.0.183** BEFORE the suite; wheel + nine installers rebuilt once after
> the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0375**.
>
> **Phase-3 slice 11 is CLOSED (queue item 1): three moves, one slice.** (1) The /portfolio
> page family → NEW `web/portfolio.py` (287 lines; 3 names, one contiguous block, app.py
> 7286–7542; **census-exact** — prefix 253/3 = closure 253/3, the second after mission; NO
> descents, NO stays beyond the route). (2) `_what_could_go_wrong_header` (130) →
> `web/sra.py` and (3) `_how_stable_header` (71) → `web/evolution.py` — the two headers
> stranded when slices 9 and 3 cut their families BEFORE ADR-0374's header ruling existed;
> both moved to their families' EXISTING modules now. app.py **13,814 → 13,359** (wc-truth).
> `LAYER_ORDER` `… → sra → forecast → portfolio → app`; portfolio.py joins the E501 list.
>
> **The headline finding: the queue's "what 289" was not a family.** The referrer walk
> dissolves ALL THREE question-word censuses — what 289 = three headers of three families
> (path/compare/sra) · how 214 = three more (evm/evolution/performance) · where 158 =
> `_where_we_stand_header`, an /analysis-family member (sole referrer `_analysis_body`).
> SEVEN misfiled members where ADR-0374 found one. The five headers whose family modules
> don't exist yet STAY in app.py and move with their families' slices (deliberately NOT
> moved — a header must not invent its family's module).
>
> ## Verification
> Oracle rebuilt per ADR-0372 recipe: **494 labels** (60 parameterless GETs incl. 4xx bodies
> · both fmts × 27 exports · 7+8 {name} pages/exports on TP4 v5 · established variants incl.
> the [grouped] four · [target-set]/[target-cleared] over the FULL surface incl. variants —
> wider than slice 10's 420). Target UID 22 (live chain head, 50%, finish-moving).
> **The slice's oracle lesson: the first shape manufactured a FALSE DARK** — the five TP4
> snapshots carry five DISTINCT Titles → five 1-version projects → ADR-0258's active
> population = v5 alone → every multi-version page rendered its placeholder, and
> `_how_stable_header` probed 0. Adjudicated by PAYLOAD (the body held the placeholder)
> before any stronger-anchor round; fixed by uploading with `<Title>` STRIPPED so the five
> join the untitled pool as ONE 5-version population (4xx 133 → 88; 45 labels switched to
> real bodies). Double-render determinism ×2 processes, 0 flapping — proven twice (pre- and
> post-fix). Pre-flight probe **5/5 render-proven, zero dark** (body/panel/li 3 each ·
> wcgw-header 3 · how-stable 12 = /evolution bare + 3 variants × 3 states). Proof:
> per-region byte-identity **3/3** (in-script pre AND post; format-check zero reformats;
> region P re-verified after ruff's import-sort fix) · multiset **44 added / 3 removed —
> zero code lines removed** (the 3: `ProjectVersion,` re-lands in portfolio.py; sra's cpm
> line CPMError-widened; app's path_evolution line narrowed, `PathEvolution` lives on in
> evolution.py) · dropped-import sweep 0 readers (SessionState control live) · **494/494
> byte-identical pristine vs cut** · falsified in the new locations **5/5 EXACT** (label
> LISTS). Sweeps: monkeypatch+attr 24 names → 0 hits on moved names (SessionState.scope
> class-wrap + the standing `app_mod.non_summary` control adjudicated, 1 setattr + 1 read)
> · source-text 7 readers → all hits adjudicated (`panelkit.js` ∈ axis_titles ∩
> `_portfolio_body` the positive control; `_TS_CAPTION_MARK`/`data-ts-caption`/the drilldown
> script tag ABSENT from moved text — the `# drilldown.js` in `_how_stable_header` is a
> comment, not the counted tag) — **zero reader repoints, second consecutive slice**.
> Mutation battery **6/6 named** (enumeration guard's 13th/14th consecutive live catches);
> mutations 2 and 5 in-body from the start. Statics green (python -m ruff check WHOLE TREE ·
> format · mypy strict 129 · bandit · node --check per file). Full suite + parity: counts in
> SESSION-LOG (this session).
>
> ## Next
> The queue resumes at phase-3 slice 12 — by the closure-re-priced census (wc-truth; each
> family owes its OWN closure): **analysis 356** (incl. the where header) · **evm 299**
> (incl. its header; `_field_forecast_panel` already below it in forecast.py) ·
> **performance 279** · resources 255 · scurve 212 · path 194 · compare 166 — EACH per the
> ADR-0365 recipe (closure before cut · span-scoped probe · six-mutation battery · the
> ADR-0372 oracle recipe; **the 494-label oracle with the TITLE-STRIPPED TP4 pool is the
> current widest reference — the title-strip is load-bearing, a verbatim TP4 upload
> re-manufactures the five-project placeholder surface**). groups (315) stays outside the
> phase-3 list while ADR-0343 feature work is queued against it. Then the standing queue
> unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture · three
> page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift
> sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket
> "exact match"; CLAUDE.md phase-3/E501 lines — portfolio.py now ALSO joins the E501 list
> unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:** re-convert
> FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run on a
> crafted sub-day-negative-float schedule · license · branch-protection contexts ·
> proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0375 closed — do not re-open. NEW this session: (1) **a census family can be a
> phantom** — what/how/where were question-word header groups, not families; only the
> referrer walk assigns membership, and SEVEN members were misfiled across three phantom
> censuses. (2) **The oracle's fixture POPULATION is a render condition** — five distinct
> TP4 titles formed five projects and blanked every multi-version page (ADR-0258); a false
> dark was manufactured by the oracle itself and caught by payload adjudication, then fixed
> by title-stripping into the untitled pool. (3) **A header stranded by ruling-lag moves
> retroactively once its family's module exists** (sra slice 9 / evolution slice 3 →
> ADR-0374's ruling applied this slice). Standing traps unchanged (live-chain payload aim ·
> patch the patcher with landed-count discipline · `#:` blocks extended by eye · route
> referrers never block · silent-405 setup · anchored splices with landed-count asserts ·
> ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives Duration · env-defect
> masquerade · binding-wrap spies · named-failure rule · never mutate a running suite's tree
> · empty sweep needs a positive control · `grep -c` exits 1 on zero · three-tier parity
> evidence · stored-start floors / non-additive rows · B608 house nosec · pydantic 2.6 /
> fastapi 0.110.2 floors · /analysis focus→tip family load-sensitive · five playwright-only
> failures pre-existing, CI-invisible · oracle telemetry labels normalized by VALUE ·
> scratchpad harnesses hardcode the repo root · two ruffs on PATH — run `python -m ruff`).
> A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
