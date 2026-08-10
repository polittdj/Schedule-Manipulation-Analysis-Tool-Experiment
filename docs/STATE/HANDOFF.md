# Handoff — 2026-08-10 (c) (phase 3 slice 18: the /compare family out — and the oracle finally committed; ADR-0382; v1.0.190)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-hcymqt`
> (this container's designated branch, restarted from `main` 24e9dd1 after #566 squash-merged —
> the branch NAME says slice14, the WORK is slice 18). **Shipped code changed** — version bumped
> **v1.0.189 → v1.0.190** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now **ADR-0382**.
>
> **TWO things closed this session.**
>
> **(1) Phase-3 slice 18: the /compare family → NEW `web/compare.py`** (218 lines; **two movers
> in ONE contiguous block**, app.py 7762–7929: `_what_changed_header` · `_compare_body`) and
> **NO descent**. app.py **10,675 → 10,505** wc-truth. `LAYER_ORDER` `… → path → compare`;
> compare.py joins the pyproject E501 list; EXTRACTED + LAYER_ORDER + VIEW_MODULES + both
> whole-view-layer guard tuples gain "compare.py". Closure **census-EXACT** (2 names / 166 ast
> lines both ways, 1.00×) with **nothing hand-folded first** — every other name resolves to an
> import from an already-cut module. `export_compare` contributes **no movers, measured**: its
> app-level callee set is EMPTY (it re-derives the signals itself), which is what licenses a
> page-only probe anchor here. **This EXHAUSTS the published phase-3 page-family list.**
>
> **(2) ADR-0381's open item is CLOSED: the oracle is COMMITTED** —
> `tests/web/oracle_corpus.py` (builder: a self-healing `app.routes`-derived half + a
> hand-authored variant half, written out by URL), `tests/guards/render_oracle_labels.txt` (the
> 648 labels, by name) and `tests/guards/test_render_oracle_corpus.py` (four guards, all four
> **proven able to fail**). The rebuild reproduces the inherited fingerprint **exactly at every
> stage** — `[empty]` 60 `{200:41,400:17,422:2}` and four loaded stages of 147
> `{200:124,404:4,422:19}`, total 648. That is **shape identity, NOT proven label-for-label
> recovery** (the original list was never recorded, so it cannot be diffed) — what removes the
> risk permanently is that the list is now in the repo, not the match.
>
> **Committing it immediately found three things prose had hidden:** SIX of twelve prose-drafted
> variants were **decoration** (FastAPI ignores an undeclared query param, so they rendered
> byte-identical to their bare label and reached no new code) — rewritten against the real route
> SIGNATURES, all ten now distinct and guarded; the launch-token normalizer had been pinning ONE
> of **two** spellings (`<meta name=sf-launch>` and `/api/whoami`'s `"launch_token"` JSON key),
> leaving five labels flapping until adjudicated by payload diff; and `[empty]` deliberately
> excludes the `{name}` labels (they 404 on the same missing file, measuring the fixture pool).
>
> ## Verification
> Corpus **648 labels**, determinism ×2 separate processes **0 flapping**. Pre-flight probe
> **2/2 render-proven, ZERO dark** (ninth consecutive) — each member moves exactly the four
> loaded `/compare` labels; `[empty] GET /compare` correctly does NOT move (the placeholder
> branch calls neither member). Proof: per-region byte-identity IDENTICAL in-script, from disk,
> and again after `ruff --fix` + `format` (sha256 `b667721aebe1…` / `ea823b325325…`) ·
> **648/648 byte-identical** pristine vs cut · falsified in the new location **2/2 EXACT label
> lists** (anchors also asserted ABSENT from post-cut app.py) · multiset **49 added / 1 removed —
> ZERO member code lines removed**. **The dropped-import sweep found drops for the first time:**
> `ruff --fix` removed `compute_net_finish_impact`, `diff_versions`, `trend_across_versions` from
> app.py (the movers were their only app.py consumers) — adjudicated safe, **zero** callers reach
> any of them through `web.app` (AST, alias-agnostic; positive control `create_app` = 184 files).
> Monkeypatch/attr sweep ZERO hits (193 setattrs; ADR-0378's control reproduced; no ADR-0297 trap
> — the caller `compare` stays in app.py). Source-text sweep: the first filter called 178 files
> readers and produced 665 junk candidates; sharpened to require a real view-source idiom it
> finds **6** genuine readers (incl. `test_gantt_find_coverage.py`) and **zero** repoints — all
> nine candidates are `"schedule_forensics"` as a PATH SEGMENT. Battery **6/6 named** (1/42 ×4 ·
> 1/4 · 1/5; enumeration guard's 27th/28th consecutive catches), plus four more falsification
> runs for the new oracle guards — **ten** in total.
>
> ## Next
> **The published phase-3 page-family list is EXHAUSTED — do not look for slice 19 on it.**
> app.py is 10,505 lines (16,685 when phase 3 began). What remains is routes (`create_app`), the
> residual shared helpers, and `groups` (430 by prefix, still OUTSIDE the list while ADR-0343
> feature work is queued against it). The next monolith decision is a **scoping** decision: take
> a FRESH prefix census against the post-cut app.py and price the candidates by referrer walk
> before committing to a phase 4 — do not assume the old queue's numbers. Then the standing queue
> unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less
> pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
> constraints · P80/P90 recurring-exception residual · doc-drift sweep (PARITY-REPORT git-ignored
> claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines
> — compare.py now ALSO joins the E501 list unpatched there) · ~150 MB RSS per loaded file ·
> Phase 6 docs. **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) +
> re-run Fuse · one Acumen run on a crafted sub-day-negative-float schedule · license ·
> branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0382 closed — do not re-open. **The oracle no longer needs rebuilding: import it.**
> `python tests/web/oracle_corpus.py --out <dir>` renders the corpus; run it with
> `PYTHONPATH=<tree>/src` against a pristine worktree and the cut tree and diff. Regenerate the
> label list in the same commit as any route change. NEW lessons this session: (1) **a
> hand-authored oracle label must be checked against the route SIGNATURE, not an ADR's prose** —
> half a prose-derived variant set was inert and nothing reported it; (2) **ending a zero-finding
> streak is a result** — sixteen slices reported "0 dropped imports", the seventeenth found three
> because this family was app.py's last consumer of them; a streak is a property of the code met
> so far, not evidence the sweep is redundant; (3) **the named-failure rule's own instrument
> needs the same scepticism as the code under it** — the mutation runner parsed pytest's
> `FAILED …` line with `split(" ")[0]`, which is the literal word `FAILED`, and reported NOT
> PROVEN against a guard that had failed correctly; (4) **a filter that flags nearly everything
> has not swept** — `__file__` appears in almost every test, so "178 source-text readers, 665
> candidates" was noise until the filter demanded a real view-source idiom (6 readers, 0
> repoints). Standing traps unchanged (a census can be exact and still not be membership · a
> page-only anchor understates an export-feeding member · route-only referrers never force a
> descent · sweep by BARE NAME · a quiescence guard can match its own shell · fingerprints carry
> their SCOPE · a normalizer that fails silently is a flap factory · mutate by OFFSET not
> permutation · never MEASURE a tree a battery is mutating · the monkeypatch adjudication list
> grows as families move · census families can be phantoms · ruling-lag headers move
> retroactively · the installer lockstep guard makes the rebuild a PREREQUISITE of the final
> suite · patch the patcher with landed-count discipline · `#:` blocks extended by eye ·
> silent-405 setup · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI re-derives Duration ·
> env-defect masquerade · binding-wrap spies · named-failure rule · empty sweep needs a positive
> control · `grep -c` exits 1 on zero · three-tier parity evidence · B608 house nosec ·
> pydantic 2.6 / fastapi 0.110.2 floors · five playwright-only failures pre-existing,
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
