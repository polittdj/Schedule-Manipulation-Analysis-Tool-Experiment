# ADR-0282 — should findings/narrative follow the parity audit when Acumen-parity mode is on?

Status: **proposed / open question for the operator** (2026-07-23) — no code change; behaviour pinned
by ADR-0281

## Context

The 2026-07-23 performance-fix validation (ADR-0281) surfaced a pre-existing behavioural
inconsistency that pre-dates the ChatGPT audit and was caught only because the validation re-ran the
op-count check with parity mode ON (`A=1`):

- When `SessionState.dcma_acumen_parity` is **on**, `_compute_analysis` computes the **DISPLAYED**
  DCMA audit with `acumen_parity=True` (so the Analysis page's DCMA-14 verdicts, and the dashboard
  cards, reflect Acumen's exact definitions).
- But `recommend()` — which produces the risk/opportunity/concern **findings**, and through them the
  **narrative** and the executive briefing — calls `audit_schedule(...)` with the DEFAULT
  (`acumen_parity=False`) definitions. Captured audit kwargs on a cold parity-mode analysis were
  `[True, ABSENT, ABSENT]`: the displayed audit is parity, the findings-driving audits are not.

So with parity mode on, a DCMA check can read (say) PASS in the parity view while a finding derived
from the non-parity audit still flags it as FAILED (or vice-versa). The two surfaces can disagree.

ADR-0281 **deliberately did not change this.** Its acceptance line was byte-identical findings and
narrative in both modes; silently re-sourcing findings from the parity audit would have changed the
findings whenever parity is on, which is a product decision, not a performance fix. ADR-0281's
`_compute_analysis` therefore passes `precomputed_audit=None` in parity mode so the recommender keeps
recomputing the default audit exactly as before (the cost is one extra audit pass in parity mode,
pinned and documented by `test_cold_analysis_parity_mode_is_documented`).

## The question for the operator

When Acumen-parity mode is on, should the findings / narrative / briefing be derived from the
**parity** audit (so every surface agrees), or stay on the **default** audit (today's behaviour)?

- **Option A — findings follow the parity audit when parity is on.** Every surface agrees; the
  operator who opts into parity gets parity end-to-end. Costs: findings/narrative/briefing text and
  the risk matrix change whenever parity is on (new golden captures under `A=1`), and the citation
  re-verification goldens (`ai.citations`) must be re-pinned for the parity variant. This is the
  more internally-consistent behaviour and is likely what a testimony reviewer expects.
- **Option B — keep findings on the default (pure-logic) audit (today).** The findings stay the
  forensic pure-logic read regardless of the parity toggle (which is framed as a *comparison* view of
  the DCMA numbers, not a re-basing of the whole analysis). Zero change; the two surfaces can
  disagree under parity, which must then be documented in `docs/ACUMEN-PARITY-MODE.md`.

Recommendation: decide with the operator against a real file where the parity and default audits
differ on a check that also drives a finding (e.g. a sub-day-baseline High-Float or a Missed-Task
case), so the disagreement is concrete before choosing. Whichever way it goes, it lands in its own PR
with fresh parity-variant goldens under the parity gate (Law 2 / ADR-0240) — never bundled with a
performance change.
