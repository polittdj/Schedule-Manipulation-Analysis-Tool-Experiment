# Handoff — 2026-08-11 (phase 4 slice 21: the /wbs family out — app.py under 10k; ADR-0386; v1.0.193)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-uvrdwf`
> (this container's designated branch, restarted from `main` **4825c33** after #569 AND #570
> squash-merged — the branch NAME says slice14, the WORK is slice 21). **Shipped code changed** —
> version bumped **v1.0.192 → v1.0.193** BEFORE the suite; wheel + nine installers rebuilt once
> after the last code change (SCHEMA stays 2.11.0). Highest ADR now **ADR-0386**.
>
> **ADR NUMBER COLLISION, avoided by re-fetching.** This slice was written as ADR-0385; #570
> landed ADR-0385 on `main` mid-session. Renumbered to **0386** and rebased onto 4825c33. **A
> parallel session can take your ADR number** — `git fetch origin` before you write the number,
> and again before you commit.
>
> **Slice 21: the /wbs page family → NEW `web/wbs.py`** (154 lines; **THREE functions in ONE
> contiguous block**, app.py 7294–7407) and **NO descent**. app.py **10,046 → 9,937** wc-truth —
> **the monolith is below 10,000 lines for the first time** (17,197 when phase 3 began).
> `LAYER_ORDER` `… → standards → wbs → app`; wbs.py joins the pyproject E501 list; EXTRACTED +
> LAYER_ORDER + VIEW_MODULES + both whole-view-layer guard tuples gain "wbs.py".
>
> **The prefix misses a member again.** Prefix census 2 names / 107 ast lines; the walk over all
> THREE routes finds **3 / 110** — `_num`, a 3-line formatter, carries no `wbs` prefix and IS a
> member (bare-NAME sweep confirms independently: definition + 7 call sites, all inside
> `_wbs_body`). Slice 20 was census-exact 1.00×; this is the immediate counter-example.
>
> **`export_wbs` contributes NO movers, and TWO instruments say so.** Its app-level callee set is
> empty (re-derives via `reports/tables.py::wbs_breakdown_tables`), AND when each member was
> mutated the four `/export/{xlsx,docx}/wbs/…` labels did not move.
>
> ## Verification
> Oracle rebuilt the inherited fingerprint: `[empty]` 60 `{200:41,400:17,422:2}`, four loaded
> stages of 147 `{200:124,404:4,422:19}`, **648** total; determinism ×2 processes **0 flapping**.
> Probe **3/3 render-proven, ZERO dark** (twelfth consecutive) — `_num`/`_wbs_body` move the four
> loaded `/wbs/{name}` labels, `_wbs_data` the four `/api/wbs/{name}`. Per-region byte-identity
> IDENTICAL in-script, from disk, and after `ruff --fix` + `format` (sha256 `267f40832493`) ·
> **648/648 byte-identical** pristine vs cut · falsified in the new location **3/3 EXACT** (every
> `def` also asserted ABSENT from post-cut app.py) · multiset **45 added / 1 removed — ZERO code
> lines removed** (the removal is the parenthesized import member `    WBSGroup,`). Battery
> **6/6 named** (1/49 ×4 · 1/5 · 1/6; the enumeration guard's 33rd/34th consecutive catches).
>
> **NEW TRAP — a probe's marker must MATCH THE RETURN TYPE.** `_wbs_data` returns a `dict`;
> ADR-0384's str-concat marker would have raised TypeError, turning every `/api/wbs` render into a
> 500 — which the probe scores as "moves lots of labels". A dict member gets an additive KEY. A
> mis-typed marker does not measure a dark member; it measures the probe.
>
> **NEW TRAP — a sweep's POPULATION is part of its claim.** The sweeps first ran over 646 files vs
> slice 20's 507; the extra **138 were `build/`**, a stale copy of `src/` left by the v1.0.192
> wheel build (carrying `standards.py`, not `wbs.py`). No verdict changed (clean re-run: 508 files,
> same hits, control 177) but a stale snapshot can invent a reader OR miss one and says "0 hits"
> either way — and the positive control fires in the stale copy too, so it does NOT catch this.
> Sweeps now exclude build/dist/.venv/caches and STATE the file count beside the verdict.
>
> **NEW TRAP — the MPXJ installer pin DRIFTS to the container's clone boundary.** `mpxj_ref()`
> runs `git log -1 -- tools/mpxj`; in a `--depth 1` clone that returns the shallow boundary, so
> each session re-pins the nine installers to whatever commit it cloned at. Measured: committed
> installers pinned `f0634639` (did NOT touch tools/mpxj) · this container shallow pinned
> `41fb122` (did NOT) · after `git fetch --unshallow`, **`42d92dc`** (DID, ADR-0232 #370). Harmless
> so far — every candidate is a real commit with identical bytes — but **slice 20 shipped that
> drift**. This slice builds unshallowed. **Fix queued, NOT silently patched:** `mpxj_ref()` should
> refuse a shallow clone or deepen until the path is genuinely touched.
>
> **Sweeps.** Dropped-import: ONE (`WBSGroup`), zero callers reach it through `web.app` (AST,
> alias-agnostic; control `create_app` = 177 files). Monkeypatch/setattr **ZERO hits** on all 10
> bound names; no ADR-0297 trap (all three callers stay in app.py). Import sweep: **one live reader
> left un-repointed ON PURPOSE** — `tests/web/test_coverage_app_extra.py:228` imports `_wbs_body`
> from `web.app`; the `X as X` re-export keeps it working and it is a standing live check
> (ADR-0383's call for `test_risks.py`). Source-text: 13 readers, zero repoints; the region carries
> `wbs.js` but every `wbs.js` guard reads the STATIC FILE or the RENDERED page — disjoint from the
> 13, checked by name.
>
> ## Next
> **Phase 4 slice 22.** `brief` (44, 0 descents) is the LAST zero-descent family; then `scorecards`
> (151) and `card` (140) whose only shared names are route-only. **Re-price by referrer walk; do
> NOT assume ADR-0383's table.** Census-harness note paid for this session: its seed matches route
> paths by SUBSTRING, so seeding `brief` swallows `/briefing` and fuses two families — seed `brief`
> on `/brief` + `/export/{fmt}/brief` ONLY. Re-priced exactly: `brief` = 1 mover / 44 / 0 descents;
> `briefing` = 4 movers / 194 / **3** descents (the AI-backend helpers) — ADR-0383's table says 4,
> so **briefing must be re-priced before it is cut**. `settings` (318) and `cei` (262) also carry
> real descents. Then the standing queue: **`mpxj_ref()` shallow-clone hardening** ·
> stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages ·
> /groups Activities (ADR-0343) · installers vs known-good constraints · P80/P90 residual ·
> doc-drift sweep (CLAUDE.md phase-3/E501 — `wbs.py` now ALSO unpatched there) · ~150 MB RSS per
> loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04 + re-run Fuse · one Acumen run on a
> crafted sub-day-negative-float schedule · license · branch-protection contexts · proprietary
> reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0386 closed — do not re-open. **The oracle no longer needs rebuilding: import it.**
> `python tests/web/oracle_corpus.py --out <dir>`, run with `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures` against a pristine worktree and the cut tree, and diff.
> NEW lessons: (1) marker type must match return type; (2) a sweep's POPULATION is part of its
> claim; (3) a prefix that is a prefix OF ANOTHER FAMILY fuses two censuses — seed on exact route
> lists; (4) the MPXJ pin drifts in a shallow clone; (5) **a parallel session can take your ADR
> number** — fetch before numbering AND before committing; (6) two instruments agreeing beats
> either alone. Standing traps unchanged (`ast` col_offset is a BYTE offset — splice on bytes,
> re-parse before writing · verify WHICH REPO before believing a resume prompt · a census can be
> exact and still not be membership · a page-only anchor understates an export-feeding member ·
> route-only referrers never force a descent · sweep by BARE NAME · a diff is the wrong surface for
> an import question · a quiescence guard can match its own shell · fingerprints carry their SCOPE ·
> a normalizer that fails silently is a flap factory · mutate by OFFSET not permutation · never
> MEASURE a tree a battery is mutating · the monkeypatch adjudication list grows as families move ·
> census families can be phantoms · ruling-lag headers move retroactively · the installer lockstep
> guard makes the rebuild a PREREQUISITE of the final suite · patch the patcher with landed-count
> discipline · silent-405 setup · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives
> Duration · env-defect masquerade · binding-wrap spies · named-failure rule · empty sweep needs a
> positive control · `grep -c` exits 1 on zero · three-tier parity evidence · B608 house nosec ·
> pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing, CI-invisible ·
> oracle telemetry normalized by VALUE · scratchpad harnesses hardcode the repo root ·
> `python -m pytest` prepends CWD to `sys.path` and bare `pytest` does NOT · two ruffs on PATH, run
> `python -m ruff`). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
