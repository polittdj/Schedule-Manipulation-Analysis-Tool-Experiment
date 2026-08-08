# Handoff — 2026-08-08 (d) (phase 3 slice 8: the mission wall out of the monolith; the oracle that measured the weather; ADR-0372; v1.0.180)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-obnrld`
> (branched from `main` 6975145 after #556 squash-merged). **Shipped code changed** — version
> bumped **v1.0.179 → v1.0.180** BEFORE the suite; wheel + nine installers rebuilt once after
> the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR now
> **ADR-0372**.
>
> **Phase-3 slice 8 is CLOSED (queue item 1): `_mission_body` → `web/mission.py` (329
> lines), app.py 16,685 → 16,384.** The re-measured census CONFIRMED the closure exactly for
> the first time (mission 304 = the one function; no descents — externals are only `_e` /
> `Schedule` / `ExecutiveBriefing`; the export route contributes NO movers). `LAYER_ORDER`
> `… → trend → ssi → mission → app`; E501 exemption travels; re-export sorts mid-list
> (margin < mission < offload). The re-measure re-priced the WHOLE queue (wc-truth, prefix
> census): sra 840 — and its closure will pull `_ssi_panel` 235 + `_ssi_export_tables` 248 +
> `_file_stored_risks` + both risk-field constants (ADR-0365 measured them out of ssi), so
> expect ~1,300+ · forecast 391 · what 289 · portfolio 253 · evm 239 · where 235 · how 214
> (the stale "how 290 · what 257 · portfolio 231 · evm 208 · forecast 204" queue numbers are
> superseded).
>
> ## Verification
> Oracle rebuilt 96 → **151 labels** (every parameterless GET incl. APIs · both export fmts
> ×25 exports · 8 named exports on TP4 v5 · the evolution/trend variants · ssi api/grid/save
> · a [target-set] sequence POSTing REAL UID 17 with 303 asserted, ten pages + seven exports,
> then cleared). Double-render determinism across two separate processes BEFORE any claim;
> three normalizers, each earned by evidence (launch token `{hex16}.{wipe_gen}` · whoami
> `"pid"` · **/api/system VALUES — the falsification run moved a 4th label, payload-diffed to
> `memory.percent` 4.6→4.7: live host telemetry crossing a 1-dp boundary, the env-masquerade
> trap caught by diffing the payload, not believing the label**). Pre-flight probe:
> `_mission_body` moves exactly 3 labels (/mission bare + [target-set] + [target-cleared]);
> the mission exports do NOT move (the export never calls the body); zero oracle-dark members
> — the first slice with none. Proof: per-definition byte-identity 1/1 (asserted inside the
> cut script) · multiset 28 added / 0 removed (first slice with zero removals — nothing
> narrowed) · **151/151 routes byte-identical pristine vs cut** · falsified in the new
> location, EXACT pre-flight set, restore md5-verified. Sweeps: monkeypatch + attr-read over
> the 4 bound names — zero hits, positive-controlled by the standing `app_mod.non_summary`
> patch; source-text sweep over all 12 app.py readers, positive-controlled (`mission.js` ∈
> axis_titles ∩ body), every hit adjudicated (EXEMPT lists / rendered pages / generic words).
> Mutation battery 6/6: re-export deletion · deferred upward import · both enumeration drops
> · `"&mdash;"` sentinel · drilldown double-load — each exactly ONE named failure, twins
> green (the enumeration guard's 7th/8th consecutive live catch), tree restored from
> scratchpad copies, md5 + anchor-grep ×4. Statics green (python -m ruff check WHOLE TREE ·
> format · mypy strict 126 · bandit exit 0 · node --check per file). Full suite + parity:
> counts in SESSION-LOG (this session).
>
> ## Next
> The queue resumes at phase-3 slice 9 — by re-measured size: **sra** (~1,300+ closure;
> descents pre-staged by ADR-0365; the slice-7 crafted v4/v2 setup-load oracle sequences MUST
> return for it) · forecast 391 · what 289 · portfolio 253 · evm 239 · where 235 · how 214 —
> EACH per the ADR-0365 recipe (closure before cut · span-scoped probe · this battery). Then
> the standing queue unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture ·
> three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift
> sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact
> match"; CLAUDE.md phase-3/E501 lines — mission.py joins the E501 list, deliberately NOT
> patched into CLAUDE.md here) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:**
> re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen
> run on a crafted sub-day-negative-float schedule · license · branch-protection contexts ·
> proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0372 closed — do not re-open. NEW this session: (1) **an oracle label serving
> live telemetry is weather, not behavior** — /api/system was byte-stable across three runs
> by LUCK and flipped during the falsification render; normalize VALUES (keep shape) up
> front, and adjudicate every unexpected mover by payload diff before believing a dependency
> (stability observed n times is not determinism). (2) A scratchpad-resident harness must
> hardcode the repo root — a walk-up from OUTSIDE the repo loops at `/` (a silent 5-min
> hang); any root-walk must fail loudly at `/`. (3) The prefix census CAN equal the closure
> (mission: 1 function, 0 descents) — it is a fine finder when the family is one function;
> the closure check cost minutes and is still owed every slice. Standing traps unchanged
> (silent-405 setup · anchored splices with landed-count asserts · ADR-0259 dedupe vs memo ·
> round-half-even 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap
> spies · named-failure rule (pytest exit ≠ failing test — assert the test RAN) · never
> mutate a running suite's tree · empty sweep needs a positive control · `grep -c` exits 1
> on zero · three-tier parity evidence · stored-start floors / non-additive rows · B608
> house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis focus→tip family
> load-sensitive · five playwright-only failures pre-existing, CI-invisible). A number
> written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
