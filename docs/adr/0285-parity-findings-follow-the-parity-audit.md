# ADR-0285 — findings / narrative / briefing follow the parity audit when Acumen-parity mode is on

Status: accepted (2026-07-24) — resolves **ADR-0282** (proposed / open question) as **Option A**

## Context

ADR-0282 filed the open question and ADR-0281 pinned today's behaviour: with `dcma_acumen_parity`
ON, `_compute_analysis` computed the **displayed** DCMA audit with `acumen_parity=True`, but
`recommend()` — which produces the risk/opportunity/concern **findings**, and through them the
**narrative**, the **risk matrix** and the **executive briefing** — always derived from the DEFAULT
(pure-logic) audit. So a check could read PASS on the parity ribbon while a finding still called it
FAILED, on the same page.

ADR-0282 asked the operator to settle it against a real file where the two audits disagree on a
check that also drives a finding. **Large Test File2** is that file: default vs parity differ on
High Float (717/660), Negative Float (123/112), Missed (1221/1095), Resources (864/842), CPLI
(1.0/0.59), BEI (0.51/0.53) and — after ADR-0283 — Invalid Dates (182/173). Every one of those
checks produces a DCMA finding when it fails.

**Operator decision (2026-07-24): Option A.** When the operator opts into parity, they get parity
end-to-end; every surface agrees. This is what a testimony reviewer expects — a report whose ribbon
and whose narrative cite the same numbers.

## Decision

Thread a single `acumen_parity` flag from the session through every findings-derived surface:

- **`recommend(..., acumen_parity=False)`** — sources `_dcma_findings` from
  `audit_schedule(..., acumen_parity=...)` when no `precomputed_audit` is supplied. A supplied
  `precomputed_audit` MUST match the flag (documented in the docstring).
- **`_compute_analysis`** — the ADR-0281 pin is removed: the parity-aware audit it already computes
  is now passed as `precomputed_audit` in **both** modes, with `acumen_parity=dcma_acumen_parity`.
  This *also* removes parity mode's extra audit pass (2×/1×/1× → **1×/1×/1×**, matching default).
- **`build_narrative(..., acumen_parity=False)`** — its internal fallback `recommend()` (used only
  when no `precomputed_findings` are handed in) follows the flag.
- **`build_briefing(..., acumen_parity=False)`** — both the audit that produces `dcma_fails` (and
  therefore the **verdict**) and its `recommend()` call follow the flag, closing the gap where the
  `/briefing` page header was parity-aware while its body was not.
- **Web call sites** — `/risks`, `/export/{fmt}/risks`, `/briefing`, `/export/{fmt}/briefing`,
  `/api/ai/briefing` and `_the_briefing_header` all pass `st.dcma_acumen_parity`.

**Baseline compliance is mode-independent** (`compute_baseline_compliance` has one Acumen-validated
definition and takes no parity flag), so only the DCMA-check findings move with the toggle; the
compliance findings are unchanged in both modes.

**Default off is byte-identical** — verified: `recommend(sch)` equals `recommend(sch,
acumen_parity=False)` and `build_narrative(sch)` equals `build_narrative(sch, acumen_parity=False)`
on the 2,126-task golden fixture.

## Consequences

- With parity ON the findings, narrative, briefing verdict and risk matrix are derived from Acumen's
  definitions — the ribbon and the prose can no longer disagree. On the Large Test File golden the
  parity findings drop the DCMA-09 CONCERN (parity scopes that check out per ADR-0283), 9 findings
  → 8.
- Parity mode now costs **one** audit pass instead of two (a side-benefit of removing the pin).
- The default (pure-logic) forensic view is unchanged, so every golden, the P2/P5 parity gate, and
  the `ai.citations` re-verification goldens stay green — those are literal-fixture and
  mode-independent, so **no citation golden needed re-pinning** (contrary to ADR-0282's
  expectation; the concern was checked and did not materialize).
- The dashboard parity payload golden (`_SHA_TWO_VERSION_PARITY`) is unaffected: the dashboard
  renders the audit, which already followed parity.

## Verification

- `tests/engine/test_recommendations.py::test_acumen_parity_findings_follow_the_parity_audit` — a
  no-baseline task past the data date is a DCMA-09 CONCERN in default and absent under parity;
  `recommend(sch, acumen_parity=False)` equals `recommend(sch)` (default byte-identical).
- `tests/web/test_dashboard_perf_contract.py::test_findings_and_narrative_follow_the_active_audit_per_mode`
  — default findings/narrative equal the default path; parity findings equal
  `recommend(..., acumen_parity=True)` and the parity narrative is built from the parity findings.
- `…::test_cold_analysis_parity_mode_computes_each_dependency_once` — replaces the old
  `test_cold_analysis_parity_mode_is_documented`: parity is now **1×/1×/1×** with captured audit
  flags `[True]` (was `(2,1,1)` / `[True, "ABSENT"]`).
- Full suite green (2627 passed); `-m parity` green; ruff / ruff format / mypy-strict / bandit /
  `node --check` clean.
