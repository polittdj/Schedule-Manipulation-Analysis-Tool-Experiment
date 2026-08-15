# ADR-0405 — The final report stops overclaiming: conditional locality, tempered parity, the M15 contradiction resolved, and the JCL EAC gloss transcribes the engine

**Status:** Accepted · **Date:** 2026-08-15 · **Extends:** ADR-0396/0402 (the observed-banner
conditionality now reaches the closeout document) · **Closes:** the DOC-01 audit remainder
("FINAL-REPORT overclaims") and ADR-0401's two JCL docs follow-ups.

## Context

Two long-queued documentation-truth items, both agent-only (no operator input), taken together as
one small release unit:

1. **`docs/FINAL-REPORT.md` overclaims (DOC-01, audit 2026-07-13, urgency raised by ADR-0402):**
   §6.G stated *"No data off-machine"* absolutely and cited *"`.gitignore` blocks all schedule
   formats"* — the first became conditionally false the moment the approved gateway shipped (an
   operator-armed session DOES send AI prompts off-machine, by design, bannered and logged), and
   the second has been stale since ADR-0152 committed the intake (the pre-commit guard, not
   `.gitignore`, is the enforcement). §6.B's evidence read as a blanket "all reproduced exact"
   while `docs/PARITY-REPORT.md` is exact-with-documented-residuals. §6.F still described the
   removed `cloud` option. §7 presented the original closeout's counts (645 tests, 32 ADRs) as
   current. And the Definition-of-Done section still listed **M15 as "◻ BLOCKED on the operator's
   `.pbix` deposit"** while the report's own header said the deposit happened and ADR-0030 adopted
   it — an internal contradiction that `tests/web/test_docs.py` actively **pinned in place**
   (`assert "BLOCKED" in report`): the exact stale-guard class ADR-0385 recorded, again.
2. **ADR-0401's JCL docs follow-ups:** `web/help.py`'s `eac` gloss wrote
   `EAC_i = actuals + Σ(remaining budget × sampled/ML duration …)` — omitting the
   time-independent `(1−τ)` share that does NOT scale with duration (the gloss and the engine
   coincide only at the τ=1 default), and stated `deterministic EAC = AC + (BAC − EV)` without its
   precondition (recorded actuals; EV = Σ budget × %complete — clean EVM data; the engine falls
   back to budgeted cost where actuals are missing, which breaks the identity).

## Decision

- **§6.G is now conditional, stated the way the on-page banner states it:** compute/serving/parsing
  local-offline unconditionally; the ONE sanctioned exception is AI prompt egress through the
  operator-armed approved gateway — allowlist-pinned, acknowledgment-gated, bannered
  (`_observed_banner`), and recorded per-transmission. The repo-hygiene sentence now names the
  pre-commit guard and the committed non-CUI intake truthfully.
- **§6.B's evidence names the tempering:** "exact or with documented, gate-locked residuals",
  pointing at the parity report as the row-by-row truth. **§6.F** describes the current backend
  surface (cloud option removed; the gateway as the sole, never-fallback non-local path).
- **§7's counts are labeled as the original closeout's** with a pointer to the handoff's live
  Gate-at-close figures (a hard count in a narrative doc is a claim that rots; the pointer cannot).
- **The M15 contradiction is resolved in the delivered direction** (per the header, the §6.A row,
  and ADR-0030), with a one-line note that the contradiction existed. The pinning test is
  **repointed**: `"BLOCKED" not in report` + `"ADR-0030" in report` — the guard now holds the
  resolution in place instead of the contradiction.
- **A new guard pins the conditionality itself**
  (`test_final_report_states_locality_conditionally_and_names_the_gateway_record`): the report must
  keep "Conditional since ADR-0402", name `_observed_banner` and the transaction log, and keep the
  "gate-locked residuals" tempering — a future edit cannot quietly restore the absolute.
- **The `eac` gloss transcribes the engine** (`engine/jcl.py:255–258, 266, 297` verified, not
  inherited): the (1−τ)/τ split over `rem = budget × (1 − %complete)`, multipliers applied to the
  remaining-cost term, and the AC + (BAC − EV) identity stated WITH its clean-EVM precondition.
  `docs/METRIC-DICTIONARY.md` regenerated (sync test green).

**Shipped code changed** (`help.py` ships in the wheel) → **v1.0.204 → v1.0.205**, wheel + nine
installers rebuilt (lockstep 64/64).

## Verification (QC-1)

*Red first:* with the edits stashed, the repointed + new doc guards ran against the pre-edit
`FINAL-REPORT.md` — **2 FAILED by name** (the M15 resolution pin and the conditionality pin);
restored, the module runs 10/10 green. The gloss correction's oracle is the engine source itself,
read and cited line-by-line (QC-2's provenance rule); the dictionary sync test pins help.py ↔
METRIC-DICTIONARY. Full gate figures on the final tree in the handoff.

## Deliberately NOT done

- **`docs/PARITY-REPORT.md` untouched** — it was already the row-by-row honest document; the fix
  points at it rather than duplicating it.
- **No broader FINAL-REPORT rewrite** — the document remains the historical closeout narrative;
  only the claims that had become false, contradictory, or stale-as-current were corrected, each
  labeled where the history matters.
