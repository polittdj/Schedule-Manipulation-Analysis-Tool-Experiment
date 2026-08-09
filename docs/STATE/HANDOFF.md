# Handoff — 2026-08-09 (f) (phase 3 slice 15: the /resources family out — the oracle that was blind to it; ADR-0379; v1.0.187)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-nvtp39`
> (branch restarted from `main` 70b0c4b after #563 squash-merged — this container's designated
> branch; the branch NAME says slice14, the WORK is slice 15). **Shipped code changed** — version
> bumped **v1.0.186 → v1.0.187** BEFORE the suite; wheel + nine installers rebuilt once after the
> last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0379**.
>
> **Phase-3 slice 15 is CLOSED (queue item 1): the /resources family → NEW `web/resources.py`**
> (362 lines; **four movers in ONE contiguous block**, app.py 9807–10118: `_resource_loading_json`
> · `_resources_explainer` · `_who_is_overloaded_header` · `_resources_body`) and **NO descent**.
> app.py **11,403 → 11,095** wc-truth. `LAYER_ORDER` `… → evm → performance → resources → app`;
> the re-export block lands BELOW portfolio's (isort: portfolio < resources < sra); resources.py
> joins the pyproject E501 list; EXTRACTED + LAYER_ORDER + VIEW_MODULES + both whole-view-layer
> guard tuples gain "resources.py".
>
> **HEADLINE — the inherited 498-label oracle was STRUCTURALLY BLIND to this family.** The first
> pre-flight probe read **0 labels for all four movers**. Not a product finding, not a probe
> defect: the five-snapshot TP4 pool carries **zero `<Assignment>`, zero `<Resource>`, zero
> `<Work>`** elements, so `_who_is_overloaded_header` returns `""` and `_resources_body` takes its
> no-loading branch — the whole family short-circuits BY DESIGN on the population every slice
> since ADR-0372 has rendered. Adjudicated by payload before anything was touched, then the oracle
> was **extended, not reinterpreted**: a fifth stage `[resloaded]` uploads the `project2_5`
> goldens (164/165 assignments over 33 resources) with the render CONDITION asserted before the
> stage is measured. **The inherited 498 are untouched**, so ADR-0377's fingerprint stays
> checkable as a subset — and reproduces exactly. *A dark reading is a claim about the INSTRUMENT
> first; prove the oracle CAN render a member before recording it dark.*
>
> **Closure census-EXACT again (2nd consecutive), and it found a route the prefix never would.**
> Movers 4 names / 306 ast lines vs the census's 4 / 306 (1.00×); the closure itself is 5 / 308.
> The behaviour seed surfaced a THIRD entry point — `export_resource_drill`
> (`/export/{fmt}/resource-drill`), unreachable by any `_resource*` prefix — and that route is the
> only reason the closure exceeds the census: it pulls in `_cell` (2 lines), which is referred to
> by six other export routes and two importers and by **no mover**. Route-only referrer ⇒ no
> descent (ADR-0378). **The export-contributes-no-movers streak RESUMES** (broken at five by
> ADR-0378): both export routes build their tables straight from `compute_resource_loading`.
>
> ## Verification
> Oracle **644 labels** = the inherited 498 + the new `[resloaded]` 146. Fingerprint reproduced
> EXACTLY: `[empty]` {200:41,400:17,422:2} · `[loaded]`/`[target]`/`[cleared]`/`[resloaded]`
> {200:123,404:4,422:19} each · 4xx **69 loaded-stages / 88 inherited-all / 111 all-five**.
> Determinism ×2 separate processes: **0 flapping**. The fingerprint caught a harness error before
> any claim (first build read 404:6 — payload diff named it: two `[grouped]` labels pointed at
> routes that DON'T EXIST, `/dashboard` and `/activities`; re-pointed at `/scorecards` and
> `/resources`). Pre-flight probe **4/4 render-proven, ZERO dark** (sixth consecutive) — 2 labels
> each, all in `[resloaded]`. Proof: per-region byte-identity IDENTICAL (in-script, from disk, and
> again after `ruff --fix` dropped app.py's two mover-only imports — `sha256 ab1eb5e7…` both
> sides; format-check zero reformats over 941 files) · multiset **54 added / 0 removed — ZERO code
> lines removed** (measured on a quiescent tree, md5-verified first, `/proc` quiescence check) ·
> dropped-import sweep by BARE NAME: `bucket_key` 0 readers, `ResourceLoading` 2 hits both
> importing straight from the ENGINE, never through `web.app` — harmless · **644/644
> byte-identical pristine vs cut** · falsified in the new location **4/4 EXACT label lists**
> (anchors also asserted ABSENT from post-cut app.py). Sweeps: monkeypatch/attr (AST, alias-agnostic) over all 18 bound
> names → **one hit**, `test_r10_resources_contract.py:274` patching
> `app_mod.compute_resource_loading` — the **ADR-0297 phase-1 trap live**; repointed to
> `web.resources` and PROVEN load-bearing (reverting the target fails exactly
> `…nothing_is_over_allocated`). Source-text 5 readers → every hit adjudicated, zero repoints.
> Battery **6/6 named** (1/36 ×4 · 1/4 · 1/5; enumeration guard's 21st/22nd consecutive catches)
> plus a seventh for the spy repoint. Full suite **3548 passed / 45 skipped, exit 0**. Parity
> **52 passed / 15 skipped, exit 0**; all skips environment-gated. Statics green (python -m ruff
> check WHOLE TREE · format --check 942 files zero reformats at the final gate, 941 at cut time ·
> mypy strict 133 · bandit exit 0 · node --check 60/60).
>
> ## Next
> The queue resumes at phase-3 slice 16 — by the post-cut prefix census (wc-truth; each family
> owes its OWN closure, membership NAMED because the prefix is a finder): **scurve 212** ·
> **path 194** (incl. `_what_drives_header` 80) · **compare 166** (incl. `_what_changed_header`
> 79) — EACH per the ADR-0365 recipe (closure before cut · span-scoped probe · six-mutation
> battery · the ADR-0372 oracle recipe). **The oracle to inherit is now 644 labels with the
> `[resloaded]` stage**; fmts are xlsx/docx, `{name}` keys drop the `.xml`, /openapi.json is the
> 60th parameterless GET. groups (430 by prefix) stays OUTSIDE the phase-3 list while ADR-0343
> feature work is queued. Then the standing queue unchanged: stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages (/briefing, /path, /compare) · /groups
> Activities (ADR-0343) · installers vs known-good constraints · P80/P90 recurring-exception
> residual · doc-drift sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake";
> FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines — resources.py now ALSO joins
> the E501 list unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:**
> re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run on
> a crafted sub-day-negative-float schedule · license · branch-protection contexts · proprietary
> reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0379 closed — do not re-open. NEW this session: (1) **an oracle can be BLIND to a
> whole family** — four dark members on one page was the signal that the POPULATION, not the code,
> was wrong; prove the instrument can render a member before recording it dark. (2) **Extend the
> oracle, never re-base it** — keeping the inherited 498 byte-comparable is what let ADR-0377's
> fingerprint act as a self-check. (3) **A positive control that cannot see the pattern it
> certifies is worthless**: the monkeypatch sweep's line-regex returned ZERO on ADR-0378's own
> control name, because `monkeypatch.setattr(` calls WRAP ACROSS LINES. Replaced with an AST sweep
> (188 setattr calls found, control reproduced, one real hit). The alias census is the
> quantitative case for sweep-by-bare-name: `appmod` 18 · `app_module` 15 · `app_mod` 3 — three
> aliases for `web.app`, and the "dominant idiom" is only the third most common. **Prefer a parser
> to a regex when the thing matched is syntax.** (4) The behaviour seed can surface an ENTRY POINT
> the prefix cannot (`export_resource_drill`). Standing traps unchanged (a census can be exact and
> still not be membership · a page-only anchor understates an export-feeding member · route-only
> referrers never force a descent · sweep by BARE NAME · a quiescence guard can match its own
> shell · fingerprints carry their SCOPE · /openapi.json is the 60th parameterless GET · a
> normalizer that fails silently is a flap factory · closure can run 3.6× its prefix · never
> MEASURE a tree a battery is mutating · the monkeypatch adjudication list grows as families move ·
> census families can be phantoms · ruling-lag headers move retroactively · the installer lockstep
> guard makes the rebuild a PREREQUISITE of the final suite · live-chain payload aim · patch the
> patcher with landed-count discipline · `#:` blocks extended by eye · silent-405 setup · anchored
> splices with landed-count asserts · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI
> re-derives Duration · env-defect masquerade · binding-wrap spies · named-failure rule · empty
> sweep needs a positive control · `grep -c` exits 1 on zero · three-tier parity evidence · B608
> house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing,
> CI-invisible · oracle telemetry normalized by VALUE · scratchpad harnesses hardcode the repo
> root · two ruffs on PATH — run `python -m ruff`). A number written mid-session is not a
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
