# Handoff — 2026-08-12 (b) (phase 4 slice 24: the last four zero-descent families out; ADR-0389; v1.0.196)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase4-slice24-05cpkn`
> (this container's designated branch). It started AT `main` **5e48f7a** — #573 had already
> squash-merged, so no restart was needed. **Shipped code changed** — version bumped
> **v1.0.195 → v1.0.196** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0). Highest ADR now **ADR-0389** (re-fetched before numbering
> AND before committing).
>
> **Slice 24: FOUR page families → `web/curves.py` (155 lines) · `web/ribbon.py` (300) ·
> `web/workbench.py` (94) · `web/volatility.py` (217), ZERO descents.** `app.py` **9,125 →
> 8,482** wc-truth (17,197 when phase 3 began). `LAYER_ORDER` `… → cei → curves → ribbon →
> workbench → volatility → app`; all four join pyproject's E501 list, `EXTRACTED`, `LAYER_ORDER`,
> `VIEW_MODULES` and BOTH whole-view-layer guard tuples.
>
> **THE ZERO-DESCENT SET IS NOW ACTUALLY EMPTY.** Outside `groups` (fenced, ADR-0343),
> **`settings` is the only page family left in `app.py`.**
>
> ## THE FINDING — `settings`' three descents are CANDIDATES, and none of them is FORCED
> ADR-0388 corrected *which* three names `settings` carries; it did not ask whether they must
> descend. ADR-0351's rule — "a symbol needed by an extracted module must live at or below that
> module's layer" — permits **two** remedies: descend into `components.py`, **or move into the
> family module**, because `app.py` is the TOP layer and reaches anything through the `X as X`
> re-export. Only a referrer in **another extracted module** forces the first. Measured: all
> three blockers live in `app.py` itself (`_ollama_or_none`/`_openai_or_none` ← `_active_backend`
> at module level; `_second_backend` ← `_ask_response` nested in `create_app`), and an AST scan
> over all 28 extracted view modules finds **ZERO** references to any of the three — positive
> control `_e`, same scan, **26** modules. ADR-0378 already ruled this way for `_sources_line`.
> **The walk's "descents" column counts candidates, not verdicts**, and is labelled that way now.
> `settings` is very likely a single-module cut with zero forced descents — slice 25's
> measurement to make, not a claim to bank.
>
> ## The walk reproduced the record, then was shown able to fail — and the table HELD
> Rebuilt from scratch, pointed at the pre-slice-23 tree, required to reproduce ADR-0388's two
> shipped modules exactly (names, counts AND spans): `briefing` 5/198, `cei` 4/262. **CONTROL
> PASSED.** Then shown able to FAIL two ways — the same control on the post-slice-23 tree
> (`([], 0)`) and with ADR-0388's defect #1 re-injected (`ast.walk` over `create_app` with no
> stop-set, also `([], 0)`). Re-priced, **ADR-0388's table reproduces EXACTLY** — the first
> carried-forward table this phase to survive a re-walk unchanged. The four cut here are
> **fully disjoint** (no shared mover, no cross-family reference) — measured, which is what makes
> a four-family slice no riskier than a one-family slice.
>
> ## The oracle grew a SEVENTH stage: 800 → 948
> Probe scored 14/15 with `_RIBBON_FLOAT_EXTRAS` **dark** — the audit NEW-1 Law-2 guard that
> renders "—" instead of a fabricated Avg/Max Float when a schedule has **no incomplete
> activities**. Measured: **every** MSPDI fixture (16) and the one XER carry at least one activity
> under 100% complete, so **the corpus had never rendered a fully-progressed as-built at all** —
> a gap wider than the member. **`[allcomplete]`** is a BYTE TRANSFORM of an existing fixture, not
> a new file: every `<PercentComplete>` in `TP1_Library_Progressed` → 100, and the transform
> **asserts its landed count against the `<Task>` count** (one task missing the element would
> leave the branch dark, silently). The member then moves **exactly `[allcomplete] GET /ribbon`
> and nothing else** — verified as *which label*, not as a count.
>
> ## Verification
> Probe **15/15 render-proven, ZERO dark** (fifteenth consecutive); every function member moves 6
> labels / 6 marker hits, `_RIBBON_FLOAT_EXTRAS` moves 1; control `_page` **263/263**. FOUR
> members are **byte-difference only** (a float threshold, two attribute-name sets cannot carry a
> string marker) and are reported as such, not counted as two agreeing instruments. Fingerprint
> (scope: ALL SEVEN stages) `[empty]` 60 `{200:41,400:17,422:2}` + six loaded stages of 148
> `{200:125,404:4,422:19}` = **948** · **948/948 byte-identical** pristine vs cut, `diff -r`
> itself SHOWN TO FAIL (one-byte append → exit 1, restored → exit 0) · determinism ×2 processes
> on BOTH trees **0 flapping**, second pair reproduces byte-identity independently ·
> per-definition byte-identity **15/15 IDENTICAL** (re-read from disk AFTER `ruff --fix` +
> `format`), every def asserted ABSENT from post-cut app.py · multiset **101 added / 2 removed —
> ZERO code lines removed** (both dropped-import fragments) · battery **6/6 caught BY NAME** ·
> mypy strict clean over **148** files · `ruff check .` clean whole-tree · corpus re-rendered
> AFTER the battery, byte-identical to the pre-battery cut render.
>
> **M7 — the mutation scored against the ORACLE, and its anchor had to be chosen.** The first
> candidate (`Schedule Quality Ribbon`) appears **4×** in `ribbon.py` (a colliding anchor is not
> span-scoped), and the obvious unique alternatives `>Missing Logic<` / `>Merge Hotspot<` are
> asserted by **11** and **2** test files — either would have scored for the WRONG reason.
> `>Click any metric cell<` is unique and pinned by NO test: unit selection **exit 0** (the unit
> tests genuinely do not pin moved markup), oracle **6 differing labels** — matching the probe's
> independent per-member count for `_ribbon_body` exactly.
>
> **Sweeps (population STATED: 517 `.py` files, build/dist/.venv/caches excluded; 513 + the four
> new modules).** Dropped-import **TWO** (`CheckStatus`, `MonthCurves` — zero readers via
> `web.app`, control `create_app` = **184** files). Monkeypatch over the names the new modules
> **BIND** (38 names, 196 setattr calls): **1 hit**, `test_manifest_projection_memo.py:74`
> patching `app_mod.compute_activity_makeup` — **adjudicated NOT the ADR-0297 trap by FORCING
> THE NON-ZERO CASE**: that test asserts `== (0,0,0)`, and a spy asserting ZERO cannot be checked
> by running it (ADR-0386). Patching it and driving a **cold** `/api/dashboard` reaches it **3×**
> (warm 0×) — the dashboard caller stayed in `app.py`; `ribbon.py`'s own call is in
> `_can_we_trust_header`, not on that path. Empty-sweep control: two known-patched names that did
> NOT move return **17** hits. Import sweep **ONE live reader** (`test_volatility.py:15`,
> `_volatility_data`) — green. Source-text **47 files**, zero repoints; both whole-view-layer
> guards widened (mutation M4 proves it).
>
> ## The mpxj trap was PRE-EMPTED, not paid
> This container is a `--depth 1` clone. `git fetch --unshallow` ran BEFORE the build, so
> `git log -1 -- tools/mpxj` returned **`42d92dc`** (not the clone boundary) and the nine
> installers pin it correctly. **The build still has no guard** — it prints the ref and trusts the
> operator to have unshallowed. Still queued.
>
> ## Next
> **Phase 4 slice 25 — `settings` (7 movers / 347 ast lines), the LAST page family outside the
> fenced `groups`.** Re-price by referrer walk anyway, and **test the finding above**: measure
> whether each of `_ollama_or_none` / `_openai_or_none` / `_second_backend` can simply move INTO
> `settings.py` (app.py's stayers reaching them through the re-export) rather than descending into
> `components.py`. Expect the ADR-0297 monkeypatch trap to be live here: `test_ai_wiring.py` and
> `test_coverage_app_extra.py` patch `app_module._ollama_or_none` / `_openai_or_none` and
> `_ai_status_note` resolves them — those tests need repointing in the same commit, and the
> sweep must FORCE the non-zero case rather than trust a green run.
> Then the standing queue: **`mpxj_ref()` shallow-clone hardening** · stored-SRA-fields MSPDI
> fixture · driving-corridor fixture · three page-lede-less pages · /groups Activities (ADR-0343)
> · installers vs known-good constraints · P80/P90 residual · doc-drift sweep
> (`docs/PARITY-REPORT.md` still calls the reference .mpps git-ignored; `docs/FINAL-REPORT.md`'s
> blanket "Exact match"; **`LESSONS-LEARNED` Part VIII's 2026-08-10(e) entry is still at the
> BOTTOM of the file instead of newest-first**) · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 + re-run Fuse · one Acumen run on a crafted sub-day-negative-
> float schedule · license · branch-protection contexts · proprietary reruns · OR-04 · July mpp/
> re-export decision.
>
> ## Carried forward
> ADR-0353..0389 closed — do not re-open. **The oracle is committed: import it, don't rebuild it.**
> `python tests/web/oracle_corpus.py --out <dir>` with `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and the cut tree, then
> `diff -r` on the DIRECTORIES (filenames are LABEL-addressed, so a manifest diff is the wrong
> surface). NEW lessons: (1) a rule can be written down and still under-applied — a count that
> reads as a verdict gets spent as one, so label it; (2) when a member is dark, ask what the
> corpus has never rendered, not what the member needs — the answer here was a whole CLASS of
> input; (3) an oracle stage can be a byte transform of an existing fixture, and it must assert
> its own landed count; (4) choosing a mutation's ANCHOR is part of the mutation — a colliding
> anchor is not span-scoped, and a unique anchor some test asserts scores for the wrong reason;
> (5) a zero-asserting spy is only adjudicated by FORCING the non-zero case. Standing traps
> unchanged (an instrument is not evidence until shown to FAIL · a probe's marker must match the
> RETURN TYPE · a priced table is a snapshot · a control that names a VALUE beats one that names a
> direction · `ast` col_offset is a BYTE offset · a census can be exact and still not be
> membership · route-only referrers never force a descent · sweep by BARE NAME · a sweep's
> POPULATION is part of its claim · a prefix that is a prefix OF ANOTHER FAMILY fuses two censuses
> — seed on exact route lists · the MPXJ pin drifts in a shallow clone · a parallel session can
> take your ADR number · never MEASURE a tree a battery is mutating · a normalizer that fails
> silently is a flap factory · fingerprints carry their SCOPE · the installer lockstep guard makes
> the rebuild a PREREQUISITE of the final suite · round-half-even 240→0 · MSPDI re-derives
> Duration · env-defect masquerade · named-failure rule · empty sweep needs a positive control ·
> `grep -c` exits 1 on zero · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five
> playwright-only failures pre-existing, CI-invisible · scratchpad harnesses hardcode the repo
> root · `python -m pytest` prepends CWD to `sys.path` and bare `pytest` does NOT · two ruffs on
> PATH, run `python -m ruff`). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
