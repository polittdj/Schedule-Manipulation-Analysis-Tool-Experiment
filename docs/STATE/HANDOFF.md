# Handoff — 2026-08-09 (d) (phase 3 slice 13: the /evm family out — the fingerprint re-scoped to all four stages; ADR-0377; v1.0.185)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-v1-resume-s4h74l`
> (branch restarted from `main` e9c7ef8 after #561 squash-merged — this container's designated
> branch). **Shipped code changed** — version bumped **v1.0.184 → v1.0.185** BEFORE the suite;
> wheel + nine installers rebuilt once after the last code change (SCHEMA stays 2.11.0 — no
> persisted field changed). Highest ADR now **ADR-0377**.
>
> **Phase-3 slice 13 is CLOSED (queue item 1): the /evm family → NEW `web/evm.py`** (378 lines;
> **six movers in ONE contiguous block**, app.py 9816–10149: `_threshold_legend` ·
> `_evm_idx_str` · `_evm_days_str` · `_evm_explainer` · `_how_we_execute_evm_header` (moved
> WITH its family exactly as ADR-0375 ruled) · `_evm_body`) **plus one descent**:
> `_metric_scorecard_table` (19 lines, app.py 9795–9813) → `web/components.py` under the
> ADR-0351/0365 mover+stayer rule (mover `_evm_body` + stayer `_groups_body`; components'
> import surface gains `MetricResult`). app.py **12,082 → 11,735** wc-truth (the prior
> handoff's carried 12,096 was superseded by the measured tree — wc decides). `LAYER_ORDER`
> `… → portfolio → analysis → evm → app`; evm.py joins the pyproject E501 list (ten 101–107
> char lines); EXTRACTED + LAYER_ORDER + VIEW_MODULES + both whole-view-layer guard tuples
> gain "evm.py" (between driving and evolution). The export route contributes NO movers
> (mission shape, FIFTH consecutive). Closure vs prefix: 299 → 343 ast lines (1.15× — the
> mildest since mission; both unprefixed members adjudicated by referrer, not census).
>
> **The headline finding: the 88-count 4xx fingerprint spans ALL FOUR stages, not "the three
> loaded stages" as ADR-0375/0376's prose said.** The first check here compared the loaded
> stages and read 69 (12×404 + 57×422) — tripping adjudicate-before-use exactly as designed.
> All seventeen 400s are `[empty]`-stage no-schedule guards; 69 IS ADR-0374's own three-state
> histogram; per-stage shape [empty] {200:41, 400:17, 422:2}, each loaded {200:123, 404:4,
> 422:19}. Same population, wrong prose scope — compare 88 all-stages or 69 loaded-stages.
> Second recipe pin: the 60-count parameterless-GET class includes **/openapi.json** (a plain
> starlette Route — an isinstance-filtered enumeration reads 59 and undercounts).
>
> ## Verification
> Oracle rebuilt per ADR-0372/0375/0376: **498 labels** (60 [empty] + 146 × three target
> states; title-stripped TP4 pool asserted untitled BEFORE any render; target UID 22
> live-chain, POSTs 303-asserted; three normalizers). Double-render determinism ×2 separate
> processes: **0 flapping** (one bring-up flap — 4 whoami labels — adjudicated by payload:
> a non-UTF-8 token placeholder broke the pid normalizer's JSON parse; fixed, re-proven).
> Pre-flight probe **7/7 render-proven, ZERO dark members** (fourth consecutive; branch
> states read off the rendered v5 body first: header BEI-FAIL clause + SPI(t) 0.62 + SVt −40,
> body not-cost-loaded branch, sv.worst non-empty, CEI clause). Probe shape: six movers 6
> each (/evm bare + [grouped] × 3 states) · the descent **9** (those six PLUS /groups × 3 —
> the first descent whose second family was measured LIVE in the same probe). Proof:
> per-region byte-identity **1/1 + descent** (in-script pre AND post; re-verified after ruff
> dropped app.py's single mover-only import `compute_baseline_compliance,`; format-check zero
> reformats) · multiset **48 added / 1 removed — zero code lines removed** (the 1 re-lands in
> evm.py's single-line import; measured QUIESCENT, md5-verified first — ADR-0376's reverse
> trap applied, not re-paid) · dropped-import sweep **0 readers** (control live: 181 files
> import from web.app) · **498/498 byte-identical pristine vs cut** · falsified in the new
> locations **7/7 EXACT label lists** (anchors also asserted ABSENT from post-cut app.py).
> Sweeps: monkeypatch+attr over all 25 bound names → **one hit, the standing
> `app_mod.non_summary` control**, adjudication re-verified green post-cut (evm.py now also
> binds non_summary; `compute_activity_makeup` NOT bound — slice 12's second adjudication
> does not grow) · source-text 5 readers → every hit adjudicated (`panelkit.js` the positive
> control; `"BEI (throughput)"` in test_presentation_fixes is a `_stat_cards` CALL ARGUMENT,
> not a source assertion; `_TS_CAPTION_MARK`/`data-ts-caption`/drilldown tag ABSENT from
> moved text) — **zero reader repoints, fourth consecutive slice**. Mutation battery **6/6
> named** (1/33 ×4 · 1/5 · 1/6; enumeration guard's 17th/18th consecutive catches; in-body
> forms from the start). Statics green (python -m ruff check WHOLE TREE · format zero
> reformats · mypy strict 131 · bandit · node --check 60/60). Full suite **3544 passed / 45
> skipped, exit 0, 24:48**; parity **52 passed / 15 skipped, exit 0, 11:52** — all skips
> environment-gated (playwright / Java / CUI intake).
>
> ## Next
> The queue resumes at phase-3 slice 14 — by the post-cut prefix census (wc-truth; each
> family owes its OWN closure, and membership is named because the prefix is a finder, not
> the definition): **performance 326** (`_performance_body` 121 + `_performance_data` 75 +
> `_perf_version_block` 47 + `_how_we_execute_header` 83) · **resources 306**
> (`_resources_body` 157 + `_resources_explainer` 20 + `_resource_loading_json` 51 +
> `_who_is_overloaded_header` 78) · scurve 212 · path 194 (incl. `_what_drives_header` 80) ·
> compare 166 (incl. `_what_changed_header` 79) — EACH per the ADR-0365 recipe (closure
> before cut · span-scoped probe · six-mutation battery · the ADR-0372 oracle recipe; **the
> 498-label oracle with the title-stripped TP4 pool is the current widest reference — the
> fingerprint is 88 ALL-stages / 69 loaded-stages, and /openapi.json is the 60th
> parameterless GET**). groups (430 by prefix post-cut, `_saved_*` included) stays OUTSIDE
> the phase-3 list while ADR-0343 feature work is queued against it — this slice's descent
> already serves it. Then the standing queue unchanged: stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages (/briefing, /path, /compare) ·
> /groups Activities (ADR-0343) · installers vs known-good constraints · P80/P90
> recurring-exception residual · doc-drift sweep (PARITY-REPORT git-ignored claim + Project2
> "CUI intake"; FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines — evm.py now
> ALSO joins the E501 list unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse ·
> one Acumen run on a crafted sub-day-negative-float schedule · license · branch-protection
> contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0377 closed — do not re-open. NEW this session: (1) **the 88 fingerprint spans
> ALL FOUR stages** (69 = the three loaded stages; comparing loaded-stages to 88 false-alarms
> every time). (2) **/openapi.json is the 60th parameterless GET** — enumerate app.routes by
> method + path, never by route class. (3) **a normalizer that fails silently is a flap
> factory** — the whoami pid normalizer's JSON parse died on a non-UTF-8 placeholder and
> `except: pass` swallowed it; adjudicate every flap by payload diff before touching the
> harness. (4) **a descent's second family can be probe-proven live** — the scorecard table's
> /groups labels moved in the same pre-flight that proved its /evm labels. Standing traps
> unchanged (closure can run 3.6× its prefix · never MEASURE a tree a battery is mutating ·
> the monkeypatch adjudication list grows as families move · census families can be phantoms ·
> fixture population is a render condition · ruling-lag headers move retroactively ·
> live-chain payload aim · patch the patcher with landed-count discipline · `#:` blocks
> extended by eye · route referrers never block · silent-405 setup · anchored splices with
> landed-count asserts · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives
> Duration · env-defect masquerade · binding-wrap spies · named-failure rule · never mutate a
> running suite's tree (docs included) · empty sweep needs a positive control · `grep -c`
> exits 1 on zero · three-tier parity evidence · stored-start floors / non-additive rows ·
> B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis focus→tip family
> load-sensitive · five playwright-only failures pre-existing, CI-invisible · oracle
> telemetry labels normalized by VALUE · scratchpad harnesses hardcode the repo root · two
> ruffs on PATH — run `python -m ruff`). A number written mid-session is not a measurement
> (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
