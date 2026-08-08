# Handoff — 2026-08-08 (the target-UID /integrity root cause fixed: pair scope; was→now, logic diagram, change-ledger export; ADR-0370; v1.0.178)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-schedule-tool-resume-wm2ipt`
> (branched from `main` 3de301f after #554 squash-merged). **Shipped code changed** — version
> bumped **v1.0.177 → v1.0.178** BEFORE the suite; wheel + nine installers rebuilt once after
> the last code change (SCHEMA stays 2.11.0 — the new ChangeEffect fields are computed, never
> persisted). Highest ADR now **ADR-0370**.
>
> **The operator's 2026-08-08 report is CLOSED.** "Select a target UID → change effects
> reversed to that UID are wrong" root-caused and fixed: `scope()` truncates every version to
> `subschedule_to_target` (the target's ancestors under EACH version's OWN logic), and
> /integrity diffed those two different cones as the files — (1) a restored link whose
> predecessor left the comparison cone DANGLED (cpm.py drops edges with a missing endpoint) so
> a true +7/+21 wd effect measured 0 "no effect"; (2) links/tasks present in both real files
> read as removed/added (fabricated rows); (3) edits outside the cone were invisible. Every
> gate stayed green because the only "target set" tests called GET /target — a POST-only route
> — so the 405 left the target unset and the pins rode the no-target path (the queued "3 web
> tests calling GET /target" item; all three now POST and assert the 303/banner).
> **Fix:** the target's two meanings are separated — single-version metric views keep the
> ADR-0268 truncation; version-PAIR forensics (/integrity page + /export/{fmt}/integrity +
> both ai/qa manipulation-facts call sites) run on `SessionState.scope_pair` /
> `cpm_pair_for` / app `_pair_versions()` (filter still applies; target = measurement anchor
> only). The pair epoch is the TARGET-LESS scope signature, so its cache entries are the
> ordinary epoch's whenever no target is set, and setting a target re-serves resident solves.
>
> **The same message's detail asks are DONE:** `ChangeEffect` carries structured before→after
> fields (link type + lag, prior/current duration minutes, prior/current constraint, % complete
> — computed, never persisted); the /integrity effects tables gain a "Was → is now" column
> ("was 5 wd → now 3 wd (-2 wd removed; 0% complete)"); `_shortened_durations` names each cut
> (UID, name, was→now wd, wd removed, % complete; first 6 + counted remainder — the ADR-0369
> shape) and both logic findings name their links ("Removed: FS 2→3"); a new "Logic changes —
> before → after" panel draws every removed/added relationship predecessor —TYPE lag—▶
> successor with names, struck-red/green, tag (removed/added in B) and the measured revert
> effect chip — built from the SAME ChangeEffect rows as the table; ⤓ EXCEL on all three
> panels exports the new "Change ledger" + "Logic changes" sheets
> (/export/{fmt}/integrity?a=&b= — was/now/delta/% complete, effects in wd AND exact minutes,
> artifact flag, aggregate row, every skipped revert NAMED; legacy no-a/b calls keep the
> findings-only shape).
>
> ## Verification
> Statics green (python -m ruff 0.16.1 check whole tree · format 923 files · mypy strict 125 ·
> bandit exit 0 · node --check per file). New tests: tests/web/test_integrity_target_scope.py
> (10 — including the truncated-pair POSITIVE CONTROL that demonstrates all three lies) +
> tests/web/test_integrity_logic_diagram_chromium.py (4-theme computed-style measurement,
> skip-gated). Mutation matrix — every guard proven able to fail with NARROW, NAMED sets:
> route→_solvable_versions = 3 named fails / cpm_pair_for→full scope = 5 / generic detail = 1 /
> link_type unpopulated = 3; tree restored byte-identical (cmp ×5). Renders verified in
> chromium: 4-theme probe green + console/daylight screenshots read correctly. Full suite +
> parity: see SESSION-LOG (this session) for counts.
>
> ## Next
> Queued NEW (same exposure class, operator scope was /integrity): `/compare`, `/trend`'s
> findings roll-up (web/trend.py:162), `/evolution`'s counterfactual (evolution.py:505) and
> app.py's other detect_manipulation / path_counterfactual call sites still receive
> target-truncated pairs; the reduce-FILTER can in principle fabricate pair-diffs the same way
> (documented caveat, ADR-0370). Then the standing queue unchanged: phase-3 monolith split
> mission 304 (stale census — RE-MEASURE first; expect sra ~700+) · how 290 · sra · what 257 ·
> where 235 · portfolio 231 · evm 208 · forecast 204 · stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages · /groups Activities (ADR-0343) ·
> installers vs known-good constraints · P80/P90 recurring-exception residual · doc-drift sweep
> (PARITY-REPORT git-ignored claim + Project2 "CUI intake"; FINAL-REPORT blanket "exact match";
> CLAUDE.md phase-3/E501 lines) · ~150 MB RSS per loaded file · Phase 6 docs. **Operator:**
> re-convert FX-03/04 (verify UID17=5d / UID131=1w before save) + re-run Fuse · one Acumen run
> on a crafted sub-day-negative-float schedule · license · branch-protection contexts ·
> proprietary reruns · OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0370 closed — do not re-open. NEW traps this session paid for: (1) **a session
> knob with two semantics collides silently** — the Target UID is both a population cut and a
> measurement anchor; on /integrity both landed at once and the cut was derived from the very
> logic being diffed. When one knob feeds two meanings, enumerate the pages where both land.
> (2) **a test whose setup can 405 silently tests nothing** — GET on the POST-only /target left
> the target unset for the pin's whole life; assert the setup took (the 303) in any test whose
> name claims state was set. (3) `_parse_uid` maps 0 → "clear", so the project-summary row
> cannot be set as focus via the form — derive a real ≥1 summary UID in tests. Standing traps
> unchanged (anchored splices · ADR-0259 dedupe vs memo · round-half-even 240→0 · MSPDI
> re-derives Duration · env-defect masquerade · binding-wrap spies · named-failure rule · never
> mutate a running suite's tree · empty sweep needs a positive control · `grep -c` exits 1 on
> zero · three-tier parity evidence · stored-start floors / non-additive rows · B608 house
> nosec · pydantic 2.6 / fastapi 0.110.2 floors · /analysis focus→tip family is load-sensitive
> — with playwright installed locally the tip family can fail intermittently; it is NOT a CI
> signal). A number written mid-session is not a measurement (wc decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
