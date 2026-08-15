# Handoff — 2026-08-15 (e) (JCL-BR-01 closed: the branch registers carry through compute_jcl, the last strict xfail flips, the repo is xfail-FREE and the agent queue is EMPTY; ADR-0408; v1.0.207 shipped)

> ## STATUS (current) — ADR-0408 unit complete on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0408**. **SHIPPED code changed** (`engine/jcl.py`, `web/app.py`,
> `web/sra.py`) — version **v1.0.206 → v1.0.207**, SCHEMA 2.11.0 unchanged, wheel + nine
> installers rebuilt (lockstep 64/64). **ZERO xfail markers remain in the whole tree**
> (grep-proven; the four remaining `xfail(` matches are prose about flipped findings).
> **The 2026-08-13 audit's agent queue is EMPTY** — every remaining item is operator-owned
> (see OPERATOR-REQUESTS.md).
>
> ## What landed — ADR-0408 (JCL-BR-01: the last equivalence gap closes)
> `compute_jcl` accepted no branch inputs, so the web layer fed the session's
> probabilistic/conditional branches to the SSI run only — with a branch configured the
> JCL finish marginal silently left the SSI S-curve (ADR-0401's measured defect), and the
> SRA Excel export wrote a TWO-STORY workbook (SSI sheets branched, JCL sheets not).
> Now: **(1)** `compute_jcl` takes `branches=`/`conditionals=` and mirrors the SSI blocks
> statement-for-statement via the SAME imported private helpers (augment → disjoint draw
> streams → in-loop fragnet/plan overrides, probe solve included) — same augmentation
> ORDER (branches first; a combined-register test pins it). **(2)** Both web call sites
> (`/api/sra/jcl` + the export's JCL sheets) pass the session registers — one workbook,
> one story. **(3)** Fragnets are COST-INERT by the data (zero budget, never elicited):
> no multiplier draw, no duration draw, cost CDF + provenance byte-identical to the
> no-branch run — a branch moves the finish axis only; the JCL panel explainer now names
> the branch registers in its shared-inputs enumeration and states the zero-budget
> disclosure. The strict xfail flipped loudly (XPASS) and its marker is REMOVED.
> **QC-1:** red-first (7 new tests failed by name pre-change); mutation battery **6/6
> caught by the named test** (PYTHONPATH shadow, import-origin canary, pristine controls
> both sides, instruments md5-identical); the planned "fragnet consumes a draw" mutant
> was REPLACED in design (fragnet uids sort last — that mutant cannot fail) by "fragnet
> fabricates cost", which can. Blast radius: all 8 JCL-consuming test files green
> (37+31+138); mdash sentinel + audit module checked by name, unaffected.
>
> ## Next — in order (ALL remaining items are operator-owned)
> **The V-1/V-2/V-3 verification table in OPERATOR-REQUESTS.md** (arm-once on the NASA
> machine; catalog populating = Bearer accepted; still-401-with-key → capture the AI
> Hub's documented scheme) → **DISC-01** (authorizing official) → **PO-04/05** (BLOCKED
> on the CEI/HMI export) → 8 stale remote branches + SMAT-SANDBOX names (operator UI;
> sessions cannot push ref deletions, ADR-0401). Agent work: NONE queued — a new audit
> sweep or a new operator directive opens the next arc.
>
> ## Carried forward
> ADR-0353..0408 closed — do not re-open. NEW lessons this session: **a mutant that
> cannot fail is not a mutant** — check the mutation's reachability before counting it
> (fragnet uids sort last, so a wasted trailing draw shifts nothing; the battery got a
> reachable "fabricates cost" mutant instead); **an engine that replicates another
> engine's discipline extends by IMPORTING its helpers, never by copying them** (the
> jcl.py import list IS the architecture; the branch fix was ~60 lines because the
> helpers were already shared). Standing traps unchanged (see the archive — data pins vs
> guarantees · mutation-green vs adversarial · monkeypatch per CALL SITE · never measure
> a mutating tree · never mutate a measuring instrument · two ruffs, use `python -m
> ruff` · parity >900 s · container starts with NO deps · fetch before numbering and
> before committing · `wc` decides). QC-1/QC-2 are ADR-0393, pinned by
> `tests/test_standing_rules.py`.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree, 1018 files formatted · mypy strict
> 155 files · bandit · node per-file). Full suite on the final tree: **4079 passed, 47
> skipped (env-gated playwright), 0 xfailed — the repo's FIRST zero-xfail run — 0
> failed, exit 0, 22:28**. Parity: **72 passed, 15 skipped, exit 0, 10:37**. Installer
> lockstep 64/64 against the v1.0.207 wheel. Drift guards 17/17.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
