# Handoff — 2026-08-09 (e) (phase 3 slice 14: the /performance family out — the first census-exact closure; ADR-0378; v1.0.186)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-v1-resume-w49pj3`
> (branch restarted from `main` a0d6124 after #562 squash-merged — this container's designated
> branch). **Shipped code changed** — version bumped **v1.0.185 → v1.0.186** BEFORE the suite;
> wheel + nine installers rebuilt once after the last code change (SCHEMA stays 2.11.0 — no
> persisted field changed). Highest ADR now **ADR-0378**.
>
> **Phase-3 slice 14 is CLOSED (queue item 1): the /performance family → NEW `web/performance.py`**
> (383 lines; **four movers in ONE contiguous block**, app.py 10761–11092: `_perf_version_block` ·
> `_performance_data` · `_how_we_execute_header` · `_performance_body`) and — for the first time
> since ADR-0364 — **NO descent**. app.py **11,735 → 11,403** wc-truth. `LAYER_ORDER`
> `… → analysis → evm → performance → app`; the re-export block lands ABOVE portfolio's (isort:
> performance < portfolio); performance.py joins the pyproject E501 list; EXTRACTED + LAYER_ORDER
> + VIEW_MODULES + both whole-view-layer guard tuples gain "performance.py".
>
> **Headline 1 — the closure is CENSUS-EXACT, the first in phase 3.** Every prior slice ran larger
> than its prefix (1.15× mildest, 3.6× widest); this one is **4 names / 326 ast lines both ways
> (1.00×)**. It is exact only because ADR-0375's ruling-lag finding had already been folded into
> the queue by hand. The walk still assigns membership — a census that agrees is a finder that got
> lucky, not a definition.
>
> **Headline 2 — the export route SHARES a mover, breaking the five-slice streak.**
> `export_performance` builds its five tables from `_performance_data`, so BOTH export formats sit
> inside the family's render-proven surface. **No descent** was needed: the only shared name the
> walk surfaced (`_sources_line`, 14 lines) is called by the ROUTE, not by any mover — and routes
> live in `create_app`, which imports downward and stays. The four movers reference NO other
> app.py-defined name at all.
>
> ## Verification
> Oracle rebuilt per ADR-0372/0375/0377: **498 labels** (60 `[empty]` + 146 × three target states;
> title-stripped TP4 pool asserted untitled BEFORE any render; target UID 22, POSTs 303-asserted;
> three normalizers, each made LOUD — a raise on zero-match, ADR-0377's flap lesson applied at
> design time). Determinism ×2 separate processes: **0 flapping**. **ADR-0377's fingerprint caught
> two harness errors before any claim**: the first build read 404:38 per loaded stage vs the
> recipe's 404:4 — adjudicated by payload to (1) the valid fmts are **xlsx and docx**, not csv, and
> (2) the `{name}` key **drops the `.xml`**. Corrected, the harness reproduces ADR-0377 exactly
> (`[empty]` {200:41,400:17,422:2}; each loaded {200:123,404:4,422:19}; 4xx **88 all-stages / 69
> loaded-stages**). Pre-flight probe **4/4 render-proven, ZERO dark members** (fifth consecutive):
> `_perf_version_block` **9** · `_performance_data` **9** (page AND xlsx AND docx × three states) ·
> `_how_we_execute_header` 3 · `_performance_body` 3. **Two anchors were re-cut after a weaker
> first reading** (ADR-0373's stronger-anchor round applied to a NON-zero move): a page-only anchor
> understated each 9-label member as 6 and 3. Proof: per-region byte-identity IDENTICAL (in-script,
> from disk, and again after `ruff --fix` dropped app.py's five mover-only imports; format-check
> zero reformats over 939 files) · multiset **51 added / 0 removed — ZERO code lines removed** ·
> dropped-import sweep **FOUR readers in two files — and the FIRST sweep MISSED them** (it was a
> regex over the alias `app_mod`; both spies spell it `app_module`, so it read 0 with its positive
> control live; the SUITE caught it. Corrected sweep is alias-agnostic — grep the bare NAME across
> tests/ — and both spies were repointed to performance.py, then PROVEN load-bearing: reverting the
> patch target to app_module fails exactly those two tests) · **498/498
> byte-identical pristine vs cut** · falsified in the new locations **4/4 EXACT label lists**
> (anchors also asserted ABSENT from post-cut app.py). Sweeps: monkeypatch+attr over all 27 bound
> names → **one hit, `compute_activity_makeup`** — slice 12's standing ADR-0291 adjudication, NOT a
> new one; re-verified green post-cut (the spy exercises `/api/dashboard`; the module never renders
> /performance). `non_summary` is NOT bound here, so that half does not grow. Source-text 5 readers
> → every hit adjudicated (`mission.js` appears ONLY inside `_performance_body`'s docstring, and
> test_axis_titles uses it as an `EXEMPT` static-JS FILENAME, never an app.py source assertion) —
> zero SOURCE-TEXT repoints, but **the zero-repoint streak ENDS at four** (the two spies above).
> Mutation battery **6/6 named** (1/35 ×4 · 1/5 · 1/6; enumeration guard's 19th/20th consecutive
> catches) PLUS a seventh proving the spy repoint can fail. Full suite: first run **2 failed /
> 3544 passed** (the sweep miss); after the repoint **3546 passed / 45 skipped, exit 0, 27:39**
> (+2 vs slice 13 — the performance.py contract params). Parity **52 passed / 15 skipped, exit 0,
> 14:11**; all skips environment-gated (playwright / Java / CUI intake). Statics green (python -m
> ruff check WHOLE TREE · format 940 files zero reformats · mypy strict 132 · bandit exit 0 ·
> node --check 60/60).
>
> ## Next
> The queue resumes at phase-3 slice 15 — by the post-cut prefix census (wc-truth; each family owes
> its OWN closure, membership NAMED because the prefix is a finder): **resources 306**
> (`_resources_body` 157 + `_resources_explainer` 20 + `_resource_loading_json` 51 +
> `_who_is_overloaded_header` 78) · **scurve 212** · **path 194** (incl. `_what_drives_header` 80) ·
> **compare 166** (incl. `_what_changed_header` 79) — EACH per the ADR-0365 recipe (closure before
> cut · span-scoped probe · six-mutation battery · the ADR-0372 oracle recipe; **the 498-label
> oracle is the current reference — fmts are xlsx/docx, `{name}` keys drop the `.xml`, the
> fingerprint is 88 ALL-stages / 69 loaded-stages, /openapi.json is the 60th parameterless GET**).
> groups (430 by prefix) stays OUTSIDE the phase-3 list while ADR-0343 feature work is queued.
> Then the standing queue unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture ·
> three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift sweep
> (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match";
> CLAUDE.md phase-3/E501 lines — performance.py now ALSO joins the E501 list unpatched there) ·
> ~150 MB RSS per loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04 (verify UID17=5d /
> UID131=1w before save) + re-run Fuse · one Acumen run on a crafted sub-day-negative-float
> schedule · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
> re-export decision.
>
> ## Carried forward
> ADR-0353..0378 closed — do not re-open. NEW this session: (1) **a census CAN be exact — and that
> is still not membership**; the walk stays the definition. (2) **the export-contributes-no-movers
> streak is over at five**; when an export route reads the page's own data builder, a page-only
> probe anchor UNDERSTATES the member — anchor on what the export's tables render. (3) **a
> route-only referrer never forces a descent** (`_sources_line` stays). (4) **a quiescence guard
> can match its own shell**: `pgrep -f pytest` fired on a clean tree because the checking shell
> carries the heredoc (and the `[p]ytest` bracket trick fails identically) — scan `/proc` for
> python processes excluding this pid, and adjudicate before deleting the guard. (5) **SWEEP BY
> BARE NAME, never by a module-qualified regex** — the dropped-import sweep aimed at `app_mod` and
> missed two `app_module` spies; a positive control proves the sweep RUNS, not that its PATTERN is
> right. (6) A repointed spy must be proven load-bearing (revert the target; it must fail). Standing traps
> unchanged (fingerprints carry their SCOPE · /openapi.json is the 60th parameterless GET · a
> normalizer that fails silently is a flap factory · closure can run 3.6× its prefix · never
> MEASURE a tree a battery is mutating · the monkeypatch adjudication list grows as families move ·
> census families can be phantoms · fixture population is a render condition · ruling-lag headers
> move retroactively · live-chain payload aim · patch the patcher with landed-count discipline ·
> `#:` blocks extended by eye · silent-405 setup · anchored splices with landed-count asserts ·
> ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives Duration · env-defect
> masquerade · binding-wrap spies · named-failure rule · empty sweep needs a positive control ·
> `grep -c` exits 1 on zero · three-tier parity evidence · B608 house nosec · pydantic 2.6 /
> fastapi 0.110.2 floors · five playwright-only failures pre-existing, CI-invisible · oracle
> telemetry normalized by VALUE · scratchpad harnesses hardcode the repo root · two ruffs on PATH —
> run `python -m ruff`). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
