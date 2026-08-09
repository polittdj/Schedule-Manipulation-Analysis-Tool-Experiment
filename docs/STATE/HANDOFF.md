# Handoff — 2026-08-09 (phase 3 slice 10: the /forecast page family out of the monolith; the first slice with no dark member; ADR-0374; v1.0.182)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-5t4g8w`
> (branched from `main` 6823d49 after #558 squash-merged). **Shipped code changed** — version
> bumped **v1.0.181 → v1.0.182** BEFORE the suite; wheel + nine installers rebuilt once after
> the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0374**.
>
> **Phase-3 slice 10 is CLOSED (queue item 1): the /forecast page family → `web/forecast.py`
> (830 lines; 9 names / one contiguous block, app.py 7534–8311), app.py 14,583 → 13,814
> (wc-truth).** The re-measured census: prefix 391 / 4 names, closure **9 names / 778 lines**
> — `_carnac_cards`, `_FORECAST_METHOD_COLORS` (+ its `#:` block, extended by eye),
> `_field_forecast_panel`, `_group_rollup_panel` and `_where_it_lands_header` carry no
> `_forecast` prefix (the prefix is a finder, the closure is the definition — fifth
> consecutive confirmation). **`_where_it_lands_header` was filed under the WHERE family by
> the prefix census** (its 77 lines are chapter 09's header; sole referrer `forecast_view`)
> — where re-prices 235 → 158. **NO descents, NO stays beyond the routes** (smallest closure
> shape since mission). The slice's 2-family ruling: `_field_forecast_panel` (forecast_view
> + evm_view, operator 2026-07-10) MOVES with its eponymous family — both referrers are
> create_app routes (never blockers, ADR-0373 CF#4), no mover references it (no forced
> descent, ADR-0351), 2 families < the components threshold of 3 (ADR-0350). /evm reaches
> it via the re-export; when /evm is cut the panel is already below it. `LAYER_ORDER`
> `… → mission → sra → forecast → app`; re-export block between evolution and help; E501
> travels (8 lines).
>
> ## Verification
> Oracle rebuilt per the ADR-0372 recipe and grown 294 → **420 labels** (every parameterless
> GET incl. validation-4xx bodies · both fmts × 27 exports · the 7 {name} pages AND all 8
> {name} exports both fmts on TP4 v5 · the established variants · [target-set]/
> [target-cleared] re-rendering the FULL GET+export surface, 303s asserted · **NEW: four
> [grouped] labels** — /forecast + /evm ?group_field=Resource and both field-forecast
> exports — without which `_group_rollup_panel` (renders ONLY when a field is chosen) and
> the panel's deep table would be oracle-dark by construction). Anchors on the live critical
> chain BY DESIGN (target UID 22, incomplete, finish-moving — ADR-0373's lesson applied at
> design time, not paid for again). Three normalizers inherited. Double-render determinism
> across two processes, 0 flapping. **Pre-flight probe: 9/9 render-proven — the first
> multi-member slice with ZERO oracle-dark members** (panel 8 moves incl. both /evm states —
> the 2-family reach measured live; body/header/cards/colors/ruler/explainer 4 each; data 3;
> rollup 1 = the grouped variant, its only render condition; exports moved for NO member —
> the routes never call the family). Proof: per-region byte-identity **9/9** (asserted in
> the cut script pre- AND post-write; format check zero reformats) · multiset **54 added /
> 0 removed — zero code lines removed**, the 3 ruff-dropped app.py imports (CarnacSummary /
> ForecastSet / compute_group_rollup, each mover-only) net out against forecast.py's
> identical member lines · dropped-import sweep clean (all consumers import engine.forecast
> directly; the web.app import pattern live elsewhere) · **420/420 routes byte-identical
> pristine vs cut** · falsified in the new locations **9/9 EXACT** (label LISTS, not counts),
> restores md5-verified. Sweeps: monkeypatch+attr over all 29 bound names — zero hits in
> both shapes (control `app_mod.non_summary` found: 1 setattr + 1 read = the prior "2×");
> source-text over all 5 app.py readers — 11 hits all adjudicated (control `panelkit.js` ∈
> axis_titles ∩ `_forecast_body`; chartframe reads chrome.py; CSS literals read css;
> `_TS_CAPTION_MARK`/`data-ts-caption`/`drilldown.js` verified ABSENT from moved text) —
> **first slice with zero reader repoints needed**. Mutation battery **6/6 named**, twins
> green (enumeration guard's 11th/12th consecutive live catch); mutations 2 and 5 used the
> in-body form from the start (ADR-0373's defensive-overlap finding applied, not re-derived).
> Statics green (python -m ruff check WHOLE TREE — two ruffs on PATH, `python -m` pins
> 0.16.2/931-file scope · format · mypy strict 128 · bandit exit 0 · node --check per file).
> Full suite + parity: counts in SESSION-LOG (this session).
>
> ## Next
> The queue resumes at phase-3 slice 11 — by the post-cut prefix census (wc-truth; each
> family owes its OWN closure): **what 289** · portfolio 253 · evm 239 · how 214 · where 158
> — EACH per the ADR-0365 recipe (closure before cut · span-scoped probe · the six-mutation
> battery · the ADR-0372 oracle recipe; the 420-label set from this slice is the current
> widest reference, and its [grouped] labels are the only execution proof for the rollup —
> keep them). When /evm is cut, `_field_forecast_panel` is already below it. Then the
> standing queue unchanged: stored-SRA-fields MSPDI fixture (would light ADR-0373's three
> oracle-dark members from a FILE) · driving-corridor fixture · three page-lede-less pages
> (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
> constraints · P80/P90 recurring-exception residual · doc-drift sweep (PARITY-REPORT
> git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match"; CLAUDE.md
> phase-3/E501 lines — forecast.py now ALSO joins the E501 list unpatched there) · ~150 MB
> RSS per loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04 (verify UID17=5d /
> UID131=1w before save) + re-run Fuse · one Acumen run on a crafted sub-day-negative-float
> schedule · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
> re-export decision.
>
> ## Carried forward
> ADR-0353..0374 closed — do not re-open. NEW this session: (1) **the prefix census can file
> a member under the WRONG family entirely** — `_where_it_lands_header` sat in the "where"
> number while belonging to /forecast; only the closure's referrer walk catches the
> misattribution (the census numbers are finders for SIZING, never membership). (2) **A
> render-conditional member needs its condition IN the oracle** — `_group_rollup_panel`
> renders only when `group_field` is set; the [grouped] variants were added at design time
> so the probe measured 1 real move instead of a false dark. (3) An informative suite run
> STARTED before the installer rebuild honestly fails the lockstep test — the final claim
> is the re-run on the final tree (bump → build → docs → full suite, in that order, next
> time). Standing traps unchanged (live-chain payload aim · patch the patcher with
> landed-count discipline · `#:` blocks extended by eye · route referrers never block, a
> nested create_app HELPER marks descent · silent-405 setup · anchored splices with
> landed-count asserts · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives
> Duration · env-defect masquerade · binding-wrap spies · named-failure rule · never mutate
> a running suite's tree, docs included · empty sweep needs a positive control · `grep -c`
> exits 1 on zero · three-tier parity evidence · stored-start floors / non-additive rows ·
> B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis focus→tip family
> load-sensitive · five playwright-only failures pre-existing, CI-invisible · oracle
> telemetry labels normalized by VALUE · scratchpad harnesses hardcode the repo root ·
> two ruffs on PATH — run `python -m ruff`). A number written mid-session is not a
> measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
