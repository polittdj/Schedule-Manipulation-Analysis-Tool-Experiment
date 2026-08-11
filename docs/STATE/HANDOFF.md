# Handoff — 2026-08-11 (b) (phase 4 slice 22: three families out + one descent; ADR-0387; v1.0.194)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice15-0153ur`
> (this container's designated branch; the branch NAME says slice15, the WORK is slice 22). It
> started AT `main` **a14ced0** — #571 had already squash-merged, so no restart was needed.
> **Shipped code changed** — version bumped **v1.0.193 → v1.0.194** BEFORE the suite; wheel + nine
> installers rebuilt once after the last code change (SCHEMA stays 2.11.0). Highest ADR now
> **ADR-0387** (re-fetched before numbering AND before committing; `origin/main` was still at
> a14ced0 both times).
>
> **Slice 22: THREE page families → `web/brief.py` (86 lines) · `web/card.py` (184) ·
> `web/scorecards.py` (204), plus ONE descent** — `_sources_line` → `components.py`. app.py
> **9,936 → 9,593** wc-truth (17,197 when phase 3 began). `LAYER_ORDER`
> `… → wbs → brief → card → scorecards → app`; all three join pyproject's E501 list, `EXTRACTED`,
> `LAYER_ORDER`, `VIEW_MODULES` and BOTH whole-view-layer guard tuples.
>
> **Three in one slice** because they are the zero-descent set the queue named and 339 mover lines
> is an ordinary slice size. Evidence is **per family** regardless.
>
> ## THE FINDING — a probe that could not have reported anything but zero
> The first probe scored `_brief_body` **oracle-dark**. It is not. The harness diffed
> `manifest.json`'s VALUES, and `oracle_corpus._iter_out` names each file
> `sha256(LABEL)[:16].bin` — **derived from the label, not the content**. That comparison is
> constant across every run of every tree: it could not have reported a difference for ANY member,
> including one that changed every byte of every page. It reported "0 moved" with the confidence of
> a measurement — the repo's most-repeated defect class, appearing inside the instrument built to
> catch it. Fixed two ways: the probe now compares **body bytes**, and a **positive control runs
> first and ABORTS on zero**, with a second independent check that the marker TEXT reached a
> rendered body. **The first draft of an instrument is not evidence until it has been shown to
> fail** — and a probe whose failure mode is silence cannot be sanity-checked by reading its output,
> because its broken output and its most interesting finding are the same string.
>
> ## The closures — the walk reproduced the record before it was trusted
> Rebuilt from scratch here, the walk independently reproduced ADR-0386's re-priced table
> (`brief` 1/44/**0**, `briefing` 4/194/**3** — not ADR-0383's 4). Then: `brief` **1 / 44** ·
> `card` **2 / 140** · `scorecards` **5 / 151**. **The prefix misses a member in two of three** —
> `_count_bar_table` (no `card` token), `_sc_status_class` and `_parse_committed_date` (no
> `scorecard` token; it lived **6,500 lines away** at 1206) — and in the OTHER direction a `brief`
> name census sweeps in all three `briefing` names. Bare-NAME sweeps confirm each independently.
> Two names reached but NOT members: `_unschedulable_panel` (route-shared with `/analysis`) and,
> before the descent, `_sources_line`.
>
> **The descent.** `_sources_line` is called by `_scorecards_body` AND eight other page routes.
> A route-only referrer never blocks — but a MOVER calling it means `scorecards.py` needs it, and a
> view module may only import DOWNWARD, so importing it from `app.py` would close a cycle. It
> descended to `components.py`, beside the provenance cluster — the same resolution ADR-0351/0376/
> 0377 each reached.
>
> **The exports split THREE ways, measured:** `brief` → **no movers** (renders via
> `ai.brief.brief_blocks` / `brief.sections`; call graph AND probe agree) · `card` → no export route
> · `scorecards` → **`_scorecard_export_table` moves 8 export labels**, the first family since
> ADR-0378 whose export shares the page's surface. A page-only anchor would have measured it ZERO.
>
> **The oracle was EXTENDED to light a real dark member.** `_parse_committed_date` was genuinely
> dark: `scorecards_buffer_json` REQUIRES `committed`, so the bare label is a 422 that returns
> before the parser runs. Added one variant (ADR-0374's rule, ADR-0379's precedent):
> `[buffer-committed] /api/scorecards/buffer?committed=2026-07-17&iterations=100` — the date is the
> TP4 pool's own deterministic finish, which is what makes it non-degenerate (confidence **0.49**,
> non-zero P70/P80; any later date returns the trivial 1.0/0.0). Corpus **648 → 652**; label list
> regenerated in this commit. The member then moves exactly those 4 labels and nothing else, so the
> variant is **proven load-bearing** (battery mutation 7).
>
> ## Verification
> Probe **9/9 render-proven, ZERO dark** (thirteenth consecutive). Fingerprint (scope: ALL FIVE
> stages) `[empty]` 60 `{200:41,400:17,422:2}` + four loaded stages of 148
> `{200:125,404:4,422:19}` = **652**; determinism ×2 processes on BOTH trees **0 flapping** ·
> **652/652 byte-identical** pristine vs cut · per-definition byte-identity **10/10 IDENTICAL**
> (re-read from disk AFTER `ruff --fix` + `format`), every `def` asserted ABSENT from post-cut
> app.py · multiset **152 added / 5 removed — ZERO code lines removed** (2 dropped-import members +
> 3 deliberately rewritten `#:` lines) · battery **7/7 caught BY NAME** (enumeration guard's 35th/
> 36th consecutive catches) · mypy strict clean over 142 files · `ruff check .` clean whole-tree.
>
> **Sweeps (population STATED: 511 .py files, build/dist/.venv/caches excluded).** Dropped-import
> **TWO** (`DiagnosticBrief`, `Scorecard`) — zero readers via `web.app`, control `create_app` = 177
> files. Monkeypatch/setattr run **TWICE**: ZERO on the 10 MOVED names, but the moved names are the
> wrong population — the ADR-0297 trap fires on the names a new module **BINDS**. Re-swept over all
> 43 bound names: **ONE hit — `card.py` binds `non_summary`**, patched as `app_mod.non_summary` by
> `test_manifest_projection_memo.py:77`. **NOT a new trap, and MEASURED:** the spy's subject
> `_dashboard_data` stays in app.py, and since that test asserts `(0,0,0)` on a WARM dashboard (an
> assertion a DEAD spy also satisfies) the cold case was forced — `scope=24 makeup=6
> non_summary=12`, so the patch target is still live. Import sweep **ZERO** live
> readers — unlike slices 19–21 there was no standing live check to preserve. Source-text: 9 files
> reference app.py by path; **zero repoints**, every `panelkit.js`/`drilldown.js`/`scorecards.js`/
> `sf-drill`/`&mdash;` guard classified BY NAME (all read the static file or the rendered page,
> except the two `&mdash;` source-text readers — one widened here, one adjudicated: its `&mdash;`
> assertion is on a rendered page and its `read_text` reads `drift.js`).
>
> **The one non-verbatim byte.** `_BRIEF_XLSX_TITLE` sat under a `#:` block documenting BOTH
> chapter-12 export titles — *"Both name a REAL endpoint…"*. The constant's bytes moved verbatim;
> the COMMENT was split, because once one leaves, "Both" is false in app.py and absent from
> brief.py. **A shared doc-comment is not a movable unit** — leaving it intact would have left a
> false statement behind.
>
> ## Next
> **Phase 4 slice 23.** Eight families remain outside `groups`, **all carrying descents** — the
> zero-descent set is exhausted. `briefing` (4 movers / 194 / **3** descents: `_ollama_or_none`,
> `_openai_or_none`, `_active_backend`, shared with `_ai_status_note`/`_settings_body`/
> `_polished_narrative`/`_translate_batch`) is next by size; `settings` (318) and `cei` (262) also
> carry real ones. **Re-price by referrer walk; do NOT assume ADR-0383's table** — it has now been
> wrong about `briefing` once. Then the standing queue: **`mpxj_ref()` shallow-clone hardening** ·
> stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages ·
> /groups Activities (ADR-0343) · installers vs known-good constraints · P80/P90 residual ·
> doc-drift sweep (CLAUDE.md phase-3/E501 — `brief.py`, `card.py`, `scorecards.py` now ALSO
> unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:** re-convert FX-03/04 +
> re-run Fuse · one Acumen run on a crafted sub-day-negative-float schedule · license ·
> branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0387 closed — do not re-open. **The oracle is committed: import it, don't rebuild it.**
> `python tests/web/oracle_corpus.py --out <dir>` with `PYTHONPATH=<tree>/src
> SF_ORACLE_FIXTURES=<repo>/tests/fixtures`, against a pristine worktree and the cut tree, then
> `diff -r` — **and `diff -r` on the DIRECTORIES is right where a manifest diff is not.** NEW
> lessons: (1) an instrument must be proven able to fail before its output is evidence, and a
> positive control that ABORTS beats one that prints; (2) content-addressed-looking filenames may be
> LABEL-addressed — check what a name is derived from before diffing it; (3) a descent is forced by
> a MOVER, not by sharing; (4) an export's relationship to its page is per-family and must be
> measured (three families, three answers); (5) extending the oracle is part of the method when a
> member is dark for want of a render condition; (6) a shared doc-comment is not a movable unit;
> (7) a plausible module name is not a measurement — this slice's ADR first named a
> `reports/brief_tables.py` that does not exist. Standing traps unchanged (`ast` col_offset is a
> BYTE offset · verify WHICH REPO before believing a resume prompt · a census can be exact and still
> not be membership · a page-only anchor understates an export-feeding member · route-only referrers
> never force a descent · sweep by BARE NAME · a sweep's POPULATION is part of its claim · a prefix
> that is a prefix OF ANOTHER FAMILY fuses two censuses — seed on exact route lists · a probe's
> marker must match the RETURN TYPE · the MPXJ pin drifts in a shallow clone · a parallel session can
> take your ADR number · a diff is the wrong surface for an import question · a quiescence guard can
> match its own shell · fingerprints carry their SCOPE · a normalizer that fails silently is a flap
> factory · never MEASURE a tree a battery is mutating · the monkeypatch adjudication list grows as
> families move · census families can be phantoms · ruling-lag headers move retroactively · the
> installer lockstep guard makes the rebuild a PREREQUISITE of the final suite · patch the patcher
> with landed-count discipline · silent-405 setup · ADR-0259 dedupe vs memo · round-half-even 240→0 ·
> MSPDI re-derives Duration · env-defect masquerade · binding-wrap spies · named-failure rule · empty
> sweep needs a positive control · `grep -c` exits 1 on zero · three-tier parity evidence · B608
> house nosec · pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing,
> CI-invisible · oracle telemetry normalized by VALUE · scratchpad harnesses hardcode the repo root ·
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
