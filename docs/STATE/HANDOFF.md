# Handoff — 2026-08-08 (c) (the ADR-0370 exposure sweep closed: every version-pair forensic surface on the pair scope; ADR-0371; v1.0.179)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-wm3gvt`
> (branched from `main` 72a7e1a after #555 squash-merged 04:52Z). **Shipped code changed** —
> version bumped **v1.0.178 → v1.0.179** BEFORE the suite; wheel + nine installers rebuilt once
> after the last code change (SCHEMA stays 2.11.0 — no persisted field changed). Highest ADR
> now **ADR-0371**.
>
> **The ADR-0370 exposure sweep is CLOSED (queue item 1).** The caller-by-caller census of
> every population call site found the truncated pairs still feeding ten surfaces, and the
> control pair measured the stakes: on the truncated pair `detect_manipulation` FABRICATES the
> tool's worst accusation — a HIGH "2 activities deleted since the prior version" — while
> hiding the real duration cut; unanchored `compute_path_evolution` near-inverts entered/left
> (Wire "entered", Dig+Pour "left" vs the truth: only Roof left); the counterfactual starves
> to None. Moved WHOLESALE to `_pair_versions()`: /compare (diff_versions header KPIs +
> signals + focus rows) · /export/{fmt}/compare · /evolution · /api/evolution ·
> /export/{fmt}/evolution · /export/{fmt}/whatif · /export/{fmt}/whatif-added ·
> /export/{fmt}/mission's path-evolution tables (its quality trend stays focused, same basis
> as /export/{fmt}/trend). SURGICAL dual-population (series keep ADR-0268 focus; pair diffs
> get pair populations): /trend's pairwise signal roll-up (`_trend_body` pair kwargs) ·
> `build_brief`'s manipulation + remaining-cut questions · `build_briefing` section 3.1's
> entered/left (threaded via `SessionState.briefing_for` from /mission, /briefing,
> /export/{fmt}/briefing, /api/ai/briefing; memo needs NO new key — pair populations are a
> pure function of files+filter, both already in the signature). STAYED focused (value series,
> the focus is the feature): trend series/header//api/trend//export/trend ·
> net-finish-impact · driving-path · forecast · evm · performance · volatility · cei/scurve/
> curves · the per-file report (narrative built with no prior). /api/evolution +
> /export/whatif-added are behavior-INVARIANT consistency moves (anchored chains ⊆ cone —
> no test CAN fail for them; recorded honestly in the ADR, no matrix row).
>
> ## Verification
> Statics green (python -m ruff check whole tree · format · mypy strict 125 · bandit exit 0 ·
> node --check per file). New tests: tests/web/test_pair_scope_exposure_sweep.py (11 — the
> tri-engine truncated-pair POSITIVE CONTROL, one page/export truth pin per moved surface,
> every web test POSTs /target and asserts the 303, function-tier build_brief/build_briefing
> pins whose in-test controls assert the truncated output differs). Mutation matrix 8/8:
> every route wiring reverted one at a time → exactly ONE named failure each, 10 green twins,
> tree restored byte-identical (cmp + anchor-grep ×10). Full suite + parity: see SESSION-LOG
> (this session) for counts. No markup/token/layout changed — population wiring only; the
> no-target render is byte-stable structurally (no target ⇒ scope_pair IS scope, ADR-0370).
>
> ## Next
> The queue resumes at phase-3 monolith split mission 304 (stale census — RE-MEASURE the
> closure first; expect sra ~700+ over its "264": panel 235 + _ssi_export_tables 248 +
> _file_stored_risks wait there). Then: how 290 · sra (re-measured) · what 257 · where 235 ·
> portfolio 231 · evm 208 · forecast 204 — EACH slice per the ADR-0365 recipe. Then the
> standing queue unchanged: stored-SRA-fields MSPDI fixture · driving-corridor fixture ·
> three page-lede-less pages (/briefing, /path, /compare) · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift
> sweep (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact
> match"; CLAUDE.md phase-3/E501 lines) · ~150 MB RSS per loaded file · Phase 6 docs.
> **Operator:** re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse ·
> one Acumen run on a crafted sub-day-negative-float schedule · license · branch-protection
> contexts · proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0371 closed — do not re-open. NEW this session: (1) the "one knob, two semantics"
> trap generalizes — the sweep found the SAME collision on ten more surfaces; when a fix
> separates two meanings of one knob, CENSUS every caller of the old accessor in the same
> round or queue it explicitly (ADR-0370 did; this session closed it). (2) An anchored
> computation can be truncation-INVARIANT (driving-slack chains ⊆ the target cone) — measure
> before pinning: two of the ten surfaces cannot produce an observable failure, and the
> honest record is an ADR paragraph, not a vacuous test. (3) Measure the control on EVERY
> engine the sweep re-bases (detect_manipulation / path_evolution / counterfactual gave three
> DIFFERENT lie shapes from one fixture). Standing traps unchanged (silent-405 setup ·
> anchored splices with landed-count asserts · ADR-0259 dedupe vs memo · round-half-even
> 240→0 · MSPDI re-derives Duration · env-defect masquerade · binding-wrap spies ·
> named-failure rule · never mutate a running suite's tree · empty sweep needs a positive
> control · `grep -c` exits 1 on zero · three-tier parity evidence · stored-start floors /
> non-additive rows · B608 house nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis
> focus→tip family load-sensitive · five playwright-only failures pre-existing, CI-invisible).
> A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
