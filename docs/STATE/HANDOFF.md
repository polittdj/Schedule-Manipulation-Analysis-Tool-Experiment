# Handoff — 2026-08-10 (d) (phase 4 scoped by measurement; slice 19: the /risks family out; ADR-0383; v1.0.191)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-jmti4s`
> (this container's designated branch, restarted from `main` 364c1f9 after #567 squash-merged —
> the branch NAME says slice14, the WORK is slice 19). **Shipped code changed** — version bumped
> **v1.0.190 → v1.0.191** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now **ADR-0383**.
>
> **TWO things closed this session.**
>
> **(1) Phase 4 is SCOPED, by measurement.** ADR-0382 declared the published phase-3 page-family
> list exhausted and asked for a fresh census before committing to a phase 4. Done: `app.py` at
> 10,505 lines is **585** import lines · **106** module-level functions / **3,806** ast lines ·
> 2 classes / 53 · 35 assignments / 105 · **`create_app` 5,503 ast lines (1294–6796) carrying
> 135 routes**. So routes are 52% of the file and module-level helpers 36%. A referrer walk
> seeded on every route's FULL surface (page + `/api` + `/export`) finds **fourteen page families
> still in there, worth 2,709 mover lines** — 2,279 excluding `groups` (430, still fenced by
> ADR-0343). *The published list was exhausted; the file was not.* Ranked, with "descent?" =
> names an outside MOVER also calls: `groups` 430 (fenced) · `settings` 318 (3 descents) ·
> **`risks` 275 (0/0)** · `cei` 262 (2) · `ribbon` 234 (1) · `briefing` 194 (4) · `volatility`
> 192 (1) · `standards` 161 (**0/0**) · `scorecards` 151 (0 descents, 1 route-only) · `card` 140
> (0 descents, 1 route-only) · `curves` 131 (1) · `wbs` 110 (**0/0**) · `workbench` 67 (1) ·
> `brief` 44 (**0/0**).
>
> **(2) Slice 19: the /risks family → NEW `web/risks.py`** (349 lines; **EIGHT functions + FOUR
> constants in ONE contiguous block**, app.py 7458–7759) and **NO descent**. app.py **10,505 →
> 10,215** wc-truth. `LAYER_ORDER` `… → compare → risks`; risks.py joins the pyproject E501 list;
> EXTRACTED + LAYER_ORDER + VIEW_MODULES + both whole-view-layer guard tuples gain "risks.py".
> The closure ran **2.27× the prefix by lines and 4.0× by names** (prefix `risks` = 2 names / 121;
> walk = 8 / 275) — `_risk_matrix`, `_risk_ranking`, `_finding_card`, `_finding_quant`,
> `_risk_band` and `_wd` carry no `risks` prefix at all. `export_risks` contributes **no movers,
> measured** (empty app-level callee set — it re-derives via `recommend` → `findings_table`),
> which is what licenses the page-only probe anchor; fifth consecutive.
>
> ## Verification
> **The oracle survived the container** — ADR-0382's committed corpus rebuilt the inherited
> fingerprint on a cold clone with no prose archaeology: `[empty]` 60 `{200:41,400:17,422:2}`,
> four loaded stages of 147 `{200:124,404:4,422:19}`, **648** total; determinism ×2 processes
> **0 flapping**. Probe **8/8 render-proven, ZERO dark** (tenth consecutive) — every member moves
> exactly the four loaded `/risks` labels; `[empty] GET /risks` correctly does NOT move (the
> placeholder branch calls no member); `_wd`, the 3-line formatter and likeliest dark member,
> fires. Per-region byte-identity IDENTICAL in-script, from disk, and again after `ruff --fix` +
> `format` (sha256 `154962d7e95b`) · **648/648 byte-identical** pristine vs cut · falsified in the
> new location **8/8 EXACT label lists** (anchors also asserted ABSENT from post-cut app.py) ·
> multiset **59 added / 0 removed — ZERO code lines removed**. Battery **6/6 named** (1/45 ×4 ·
> 1/5 · 1/6; the enumeration guard's 29th/30th consecutive catches).
>
> **The dropped-import sweep found THREE** (`SEVERITY_ORDER`, `Category`, `Finding` — the movers
> were app.py's last consumers), adjudicated safe: **zero** callers reach any through `web.app`
> (AST, alias-agnostic; positive control `create_app` = 177 files). **Its first run reported ZERO
> and was WRONG** — a line-prefix regex over the diff (`^-from`/`^-import`) cannot see a name
> dropped from a *parenthesized* import block (`-    Category,`); an independent AST comparison of
> the two trees' import SETS caught it. Monkeypatch/setattr sweep **ZERO hits** on all twelve
> names (196 setattrs; ADR-0378's control reproduces; no ADR-0297 trap — the caller `risks_view`
> stays in app.py). Import sweep: 3 live readers in `tests/web/test_risks.py:83` left
> un-repointed **on purpose** — they are a standing live check of the `X as X` re-export.
> Source-text sweep: 5 genuine readers, **zero repoints** (the region carries no
> `_TS_CAPTION_MARK`).
>
> ## Next
> **Phase 4 slice 20 comes off the table above, zero-descent first** — `standards` (161, 0/0),
> `wbs` (110, 0/0), `brief` (44, 0/0), then `scorecards` (151) and `card` (140) whose only shared
> names are route-only. Re-price by referrer walk at the time; do NOT assume this table's numbers
> (that is the whole lesson of this session). `settings`, `briefing` and `cei` carry real descents
> and cost more than their line counts suggest. Then the standing queue unchanged:
> stored-SRA-fields MSPDI fixture · driving-corridor fixture · three page-lede-less pages
> (/briefing, /path, /compare) · /groups Activities (ADR-0343) · installers vs known-good
> constraints · P80/P90 recurring-exception residual · doc-drift sweep (PARITY-REPORT git-ignored
> claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines
> — risks.py now ALSO joins the E501 list unpatched there) · ~150 MB RSS per loaded file ·
> Phase 6 docs. **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) +
> re-run Fuse · one Acumen run on a crafted sub-day-negative-float schedule · license ·
> branch-protection contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0383 closed — do not re-open. **The oracle no longer needs rebuilding: import it.**
> `python tests/web/oracle_corpus.py --out <dir>` renders the corpus; run it with
> `PYTHONPATH=<tree>/src SF_ORACLE_FIXTURES=<repo>/tests/fixtures` against a pristine worktree and
> the cut tree and diff. Regenerate the label list in the same commit as any route change. NEW
> lessons this session: (1) **a queue is a record of what was NOTICED, not of what exists** — "the
> published list is exhausted" was true and was still the wrong stopping signal; re-derive the
> population from the code before declaring a phase over; (2) **a closure computed over `def`s
> alone strands the constants the block owns** — the call graph cannot see `_IMPACT_LABELS` /
> `_RISKS_EXPORT`; the free-name pass (classify every referenced name as import / constant /
> app-fn / app-ASSIGNMENT) is what catches them, and a `#:` doc-comment block sits outside the
> constant's AST span (standing trap 21); (3) **the SHAPE of a sweep can be wrong even when its
> pattern is right** — a diff is the wrong surface for a question about imports; compare the two
> trees' import SETS by AST. Standing traps unchanged (a census can be exact and still not be
> membership · a page-only anchor understates an export-feeding member · route-only referrers
> never force a descent · sweep by BARE NAME · a quiescence guard can match its own shell ·
> fingerprints carry their SCOPE · a normalizer that fails silently is a flap factory · mutate by
> OFFSET not permutation · never MEASURE a tree a battery is mutating · the monkeypatch
> adjudication list grows as families move · census families can be phantoms · ruling-lag headers
> move retroactively · the installer lockstep guard makes the rebuild a PREREQUISITE of the final
> suite · patch the patcher with landed-count discipline · silent-405 setup · ADR-0259 dedupe vs
> memo · round-half-even 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap
> spies · named-failure rule (and its own parser) · empty sweep needs a positive control ·
> `grep -c` exits 1 on zero · three-tier parity evidence · B608 house nosec · pydantic 2.6 /
> fastapi 0.110.2 floors · five playwright-only failures pre-existing, CI-invisible · oracle
> telemetry normalized by VALUE · scratchpad harnesses hardcode the repo root · `python -m pytest`
> prepends CWD to `sys.path` and bare `pytest` does NOT — CI runs the bare one · two ruffs on PATH,
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
