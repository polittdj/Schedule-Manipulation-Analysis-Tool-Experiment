# Handoff — 2026-08-10 (e) (phase 4 slice 20: the /standards family out; ADR-0384; v1.0.192)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-phase3-slice14-uvrdwf`
> (this container's designated branch, created fresh from `main` 41fb122 after #568 squash-merged —
> the branch NAME says slice14, the WORK is slice 20). **Shipped code changed** — version bumped
> **v1.0.191 → v1.0.192** BEFORE the suite; wheel + nine installers rebuilt once after the last
> code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now **ADR-0384**.
>
> **Container note.** This session started attached to `polittdj/SMAT-SANDBOX` — the private
> mirror, frozen at its 2026-07-11 mirror commit (v1.0.4, ADR-0194, app.py 12,209 lines, no split
> modules at all). The resume prompt was ALSO five slices stale (it asked for slice 15:
> resources/scurve/path/compare, all shipped as ADR-0379..0382). Operator authorized attaching
> this repo with push access and branching fresh from `main`. **Verify which repo you are in
> before believing a resume prompt** — `pyproject.toml`'s version and `ls src/schedule_forensics/web/`
> settle it in one command each.
>
> **Slice 20: the /standards page family → NEW `web/standards.py`** (227 lines; **FOUR functions
> in ONE contiguous block**, app.py 8764–8930) and **NO descent**. app.py **10,215 → 10,046**
> wc-truth. `LAYER_ORDER` `… → risks → standards → app`; standards.py joins the pyproject E501
> list; EXTRACTED + LAYER_ORDER + VIEW_MODULES + both whole-view-layer guard tuples gain
> "standards.py".
>
> **The closure is CENSUS-EXACT (1.00×)** — prefix and referrer walk both give 4 names / 161 ast
> lines. That is the second exact closure of the split (ADR-0378 was the first) and it is still
> not what assigns membership: ADR-0383's own family ran 2.27× its prefix. **The walk decides;
> agreement is a coincidence of naming.** This is also the first family whose seed surface is a
> SINGLE page GET — `/standards` has **no export route at all** (route census + whole-tree grep
> agree), so ADR-0378's page-only-anchor trap is checked off by measurement, not waved past. The
> free-name pass found **zero** module-level constants owned by the block — a pass that finds
> nothing is still evidence.
>
> ## Verification
> **The oracle imported clean on a second cold container** — `python tests/web/oracle_corpus.py`
> rebuilt the inherited fingerprint with no prose archaeology: `[empty]` 60 `{200:41,400:17,422:2}`,
> four loaded stages of 147 `{200:124,404:4,422:19}`, **648** total; determinism ×2 processes
> **0 flapping**. Probe **4/4 render-proven, ZERO dark** (eleventh consecutive) — every member
> moves exactly the four loaded `/standards` labels; `[empty] GET /standards` correctly does NOT
> move (placeholder branch calls no member). Per-region byte-identity IDENTICAL in-script, from
> disk, and again after `ruff --fix` + `format` (sha256 `39f910ab432c`) · **648/648 byte-identical**
> pristine vs cut · falsified in the new location **4/4 EXACT label lists** (every `def` also
> asserted ABSENT from post-cut app.py) · multiset **60 added / 2 removed — ZERO code lines
> removed** (both removals are import-line rewrites from the dropped set:
> `…dcma_audit import AuditCheck, Citation` → `… import Citation`, and the parenthesized member
> `    metric_doc,`). Battery **6/6 named** (1/47 ×4 · 1/5 · 1/6; the enumeration guard's 31st/32nd
> consecutive catches).
>
> **NEW TRAP — `ast` `col_offset` is a UTF-8 BYTE offset.** The probe's first run character-indexed
> it and every marker on a line carrying `—`/`·`/`⤓`/`⛶` landed columns early, emitting
> `) + "SFPROBE1"   if m.unit == "count":` — a SyntaxError at import, the cheap failure. On a
> different line shape the same skew lands INSIDE a string literal and the probe measures a member
> it silently corrupted. Splice on `bytes` and `ast.parse` the result before writing: **a probe
> that does not parse is not a measurement.**
>
> **The dropped-import sweep found NINE** — `AuditCheck`, `metric_doc` and seven `compute_*`
> (`bri`, `cei`, `completion_performance`, `fei`, `float_ratio`, `hmi`, `sem`); the four movers
> were app.py's last consumers of all nine. Adjudicated safe: **zero** callers reach any through
> `web.app` (AST, alias-agnostic; positive control `create_app` = 177 files). `compute_evm_indices`
> is NOT in the set — `export_evm` still reads it, the shared-import shape ADR-0377 recorded. One
> drop (`    metric_doc,`) came out of a parenthesized block — ADR-0383's lesson held because the
> sweep compared import SETS by AST from the start. Monkeypatch/setattr sweep **ZERO hits** on all
> 29 bound names (196 setattrs / 507 files; ADR-0378's control reproduces). Import sweep **ZERO
> readers, ZERO repoints**. Source-text sweep: 13 app.py-source readers, zero repoints — the region
> carries no `drilldown.js`, no `"&mdash;"`, no `_TS_CAPTION_MARK`; it does carry TWO `panelkit.js`
> occurrences (a docstring mention + the real `<script src>`) so app.py's count falls 19 → 17, and
> every `panelkit` guard asserts over the RENDERED page, not app.py source.
>
> ## Next
> **Phase 4 slice 21, zero-descent first** — `wbs` (110, 0/0) and `brief` (44, 0/0) are what is
> left of the zero-descent set, then `scorecards` (151) and `card` (140) whose only shared names
> are route-only. **Re-price by referrer walk at the time; do NOT assume ADR-0383's table.**
> `settings` (318), `briefing` (194) and `cei` (262) carry real descents and cost more than their
> line counts suggest. Then the standing queue unchanged: stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages (/briefing, /path, /compare) · /groups
> Activities (ADR-0343) · installers vs known-good constraints · P80/P90 recurring-exception
> residual · doc-drift sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake";
> FINAL-REPORT blanket "exact match"; CLAUDE.md phase-3/E501 lines — `standards.py` now ALSO joins
> the E501 list unpatched there) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:**
> re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run on
> a crafted sub-day-negative-float schedule · license · branch-protection contexts · proprietary
> reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0384 closed — do not re-open. **The oracle no longer needs rebuilding: import it.**
> `python tests/web/oracle_corpus.py --out <dir>` renders the corpus; run it with
> `PYTHONPATH=<tree>/src SF_ORACLE_FIXTURES=<repo>/tests/fixtures` against a pristine worktree and
> the cut tree and diff. Regenerate the label list in the same commit as any route change. NEW
> lessons this session: (1) **`ast` col_offset is a BYTE offset** — splice on bytes, re-parse before
> writing; (2) **verify the REPO before believing the resume prompt** — a mirror and a stale prompt
> agreed with each other and disagreed with reality; (3) **a census can be exact twice and still
> not be membership** — the walk decides, every time. Standing traps unchanged (a page-only anchor
> understates an export-feeding member · route-only referrers never force a descent · sweep by BARE
> NAME · a diff is the wrong surface for an import question · a quiescence guard can match its own
> shell · fingerprints carry their SCOPE · a normalizer that fails silently is a flap factory ·
> mutate by OFFSET not permutation · never MEASURE a tree a battery is mutating · the monkeypatch
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
