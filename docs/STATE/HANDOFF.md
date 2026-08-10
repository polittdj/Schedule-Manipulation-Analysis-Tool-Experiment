# Handoff — 2026-08-10 (b) (phase 3 slice 17: the /path family out — the instrument that did not survive the container; ADR-0381; v1.0.189)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-j11xxf`
> (this container's designated branch, restarted from `main` f766270 after #565 squash-merged —
> the branch NAME says slice14, the WORK is slice 17). **Shipped code changed** — version bumped
> **v1.0.188 → v1.0.189** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now **ADR-0381**.
>
> **Phase-3 slice 17 is CLOSED (queue item 1): the /path family → NEW `web/path.py`**
> (240 lines; **two movers in ONE contiguous block**, app.py 6972–7167: `_what_drives_header` ·
> `_path_body`) and **NO descent**. app.py **10,871 → 10,675** wc-truth. `LAYER_ORDER`
> `… → resources → scurve → path`; the re-export block sorts below `offload`'s (isort:
> offload < path < performance); path.py joins the pyproject E501 list; EXTRACTED + LAYER_ORDER
> + VIEW_MODULES + both whole-view-layer guard tuples gain "path.py".
>
> **HEADLINE — the oracle did not survive the container, and this is the first slice to MEASURE
> that.** The closure is **census-EXACT (2 names / 194 ast lines both ways, 1.00×)** — and unlike
> slice 14's exactness (ADR-0378, exact only because a prior ruling had been hand-folded) nothing
> was folded in first. Every other name the two members touch resolves to an **import** from an
> already-cut module, so there was nothing to descend into and no shared name to adjudicate.
> But the ORACLE is a different story: every slice since ADR-0372 has inherited a harness that
> lives ONLY in the scratchpad, and a fresh container has none. Rebuilt from the route surface,
> **everything `app.routes` determines reproduced exactly** — `[empty]` 60 `{200:41,400:17,422:2}`
> on the nose, the 60 parameterless GETs, the `404:4` per loaded stage ADR-0379 repaired — but the
> ~14 hand-authored variant labels per loaded stage did NOT: **the ADRs name some in prose and
> record none of their URLs.** So this slice's corpus is **592 labels, not 648**, and every number
> below carries that scope. *The parts of an oracle added because they were hard to reach are the
> parts most likely to be lost.*
>
> ## Verification
> Corpus **592 labels** (`[empty]` 60 `{200:41,400:17,422:2}` · four loaded stages 133 each
> `{200:111,404:4,422:18}`; 4xx 107 over all five stages) — scope stated, per ADR-0377.
> Determinism ×2 separate processes: **0 flapping**. One purely-additive family-specific
> extension: `[path-export]` ×2 fmts with `?target=22`, because `export_path` declares
> `target: int = Query(...)` REQUIRED, so the inherited label is a 422 that never renders the
> export body. Pre-flight probe **2/2 render-proven, ZERO dark** (eighth consecutive) —
> `_what_drives_header` 4 · `_path_body` 4, each the four loaded `/path` labels; `[empty] GET
> /path` correctly does NOT move (the placeholder branch calls neither member). Proof: per-region
> byte-identity IDENTICAL in-script, from disk, and again after `ruff --fix` re-sorted the
> re-export block (`sha256 d85a3c7698e8…`) · **592/592 byte-identical** pristine vs cut ·
> falsified in the new location **2/2 EXACT label lists** (anchors also asserted ABSENT from
> post-cut app.py) · multiset **44 added / 0 removed — ZERO member code lines removed**. Sweeps:
> dropped-import by BARE NAME **0 dropped** (imports 443 → 445, ruff removed nothing;
> set-difference positive-controlled); monkeypatch/attr (AST, alias-agnostic) **ZERO hits** on
> both names (192 setattr calls found, ADR-0378's control reproduced; **no ADR-0297 trap** — the
> caller `path_view` STAYS in app.py, so `app_mod._path_body` would still rebind the global it
> reads); source-text sweep **widened to THREE detectors** (path literal · `__file__` ·
> `getsource`) after the first pass reproduced the very blind spot `test_gantt_find_coverage.py`
> documents — **203 readers, ZERO moved literals asserted**, four first-pass candidates
> adjudicated false (three read the RENDERED page, one reads `static/path.js`). Battery **6/6
> named** (1/40 ×4 · 1/4 · 1/5; enumeration guard's 25th/26th consecutive catches). A harness bug
> was caught BEFORE it produced a false finding: the origin resolver checked the nested scope
> before the local one, so `_what_drives_header`'s own PARAMETER `analysis` read as a shared name.
>
> ## Next
> The queue resumes at phase-3 slice 18 — by the post-cut prefix census (wc-truth; each family
> owes its OWN closure, membership NAMED because the prefix is a finder): **compare 166** (incl.
> `_what_changed_header` 79). **After that the published phase-3 page-family list is EXHAUSTED.**
> Per the ADR-0365 recipe (closure before cut · span-scoped probe · six-mutation battery · the
> ADR-0372 oracle recipe). **Inherit the oracle as 592 labels with the `[path-export]` pair** —
> and read ADR-0381's consequence first: **commit the harness or its label list**, else every
> future slice re-derives a slightly smaller oracle and reports the shortfall as byte-identity.
> fmts are xlsx/docx, `{name}` keys drop the `.xml`, /openapi.json is among the 60 parameterless
> GETs, the TP4 title-strip is load-bearing, target UID 22. groups (430 by prefix) stays OUTSIDE
> the phase-3 list while ADR-0343 feature work is queued against it. Then the standing queue
> unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less
> pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
> constraints · P80/P90 recurring-exception residual · doc-drift sweep (PARITY-REPORT git-ignored
> claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines
> — path.py now ALSO joins the E501 list unpatched there) · ~150 MB RSS per loaded file · Phase 6
> docs. **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse ·
> one Acumen run on a crafted sub-day-negative-float schedule · license · branch-protection
> contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0381 closed — do not re-open. NEW this session: (1) **an instrument that lives only
> in the scratchpad is RE-DERIVED, not inherited, and gets quietly weaker every rebuild** — the
> mechanically-derived core heals itself from `app.routes`; hand-authored labels do not, and they
> are exactly the ones added to reach hard-to-reach code. Commit the recipe or lose it a slice at
> a time. (2) **Check the SHADOWING ORDER in any origin resolver** — a parameter sharing a name
> with an outer binding reads as a shared name, and a phantom shared name costs a descent
> argument. (3) **A sweep's blind spot is often already documented in the code it sweeps** —
> `test_gantt_find_coverage.py`'s own comment named the `__file__`-vs-`"app.py"` gap that the
> first source-text pass then walked straight into. (4) A route's URL does not assign it to a
> family: `/export/{fmt}/path/{name}` serves the DRIVING trace. Standing traps unchanged (a
> census can be exact and still not be membership · a page-only anchor understates an
> export-feeding member · route-only referrers never force a descent · sweep by BARE NAME · a
> quiescence guard can match its own shell · fingerprints carry their SCOPE · a normalizer that
> fails silently is a flap factory · mutate by OFFSET not permutation · never MEASURE a tree a
> battery is mutating · the monkeypatch adjudication list grows as families move · census
> families can be phantoms · ruling-lag headers move retroactively · the installer lockstep guard
> makes the rebuild a PREREQUISITE of the final suite · patch the patcher with landed-count
> discipline · `#:` blocks extended by eye · silent-405 setup · ADR-0259 dedupe vs memo ·
> round-half-even 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap spies ·
> named-failure rule · empty sweep needs a positive control · `grep -c` exits 1 on zero ·
> three-tier parity evidence · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five
> playwright-only failures pre-existing, CI-invisible · oracle telemetry normalized by VALUE ·
> scratchpad harnesses hardcode the repo root · two ruffs on PATH — run `python -m ruff`). A
> number written mid-session is not a measurement (wc decides).


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
