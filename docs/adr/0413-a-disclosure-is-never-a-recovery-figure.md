# ADR-0413 — REC-01: a provenance disclosure is never a recovery figure (and ADR-0407 was wrong)

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** REC-01 (audit 2026-08-16) ·
**Corrects:** ADR-0407 · **Ships:** engine + AI layer (`recommendations.py`, `briefing.py`)

## Context — an audit auditing its own output

ADR-0407 (shipped by the session immediately before this one) wired
`CPMResult.actual_start_driven` to the analyst as an INFO/OPPORTUNITY finding, and justified
that category choice in these words:

> **Category.OPPORTUNITY is load-bearing, not cosmetic**: `web/risks.py` builds the risk
> matrix, the risk ranking, and the recovery plan from RISK + CONCERN only, so an
> OPPORTUNITY/INFO disclosure informs without ever becoming a threat row or a recovery action.

Round 3 of the audit filed REC-01 against exactly that sentence. The ledger's own instruction
was to verify it first and, if it held, *correct* ADR-0407 rather than defend it.

**It holds.** The claim was verified against `web/risks.py` and nothing else. It is true of
that module — the matrix, the ranking and the recovery-plan panel really do take
`risks + issues`. It is false of the tree, because `ai/briefing.py` applies no category gate
at all, and because `_quantify` (`recommendations.py`) attaches exposure to *every* finding
uniformly, from its citations.

## The measurement

One started activity, floored at its recorded actual start (ADR-0391) and 20 working days
behind its deadline. Measured on the shipped tree, `v1.0.210`:

| surface | column / sentence | pre-fix | post-fix |
| --- | --- | --- | --- |
| briefing §5.2 Opportunities | **"Potential recovery"** | `20 wd` | `—` |
| briefing §6 Recommended Actions | **"Expected effect"** | `20 wd` | `—` |
| briefing §6.2 | the headline sentence | *"up to about **20 workday(s)** of slip are potentially recoverable"* | *"risk-mitigation rather than direct slip recovery"* |
| `/risks` finding card | risk score badge | `20/25`, `rk-extreme`, "Likelihood: Certain · Impact: Major · Schedule exposure: 20.0 wd" | `1/25`, `rk-min`, "Likelihood: Rare · Impact: Negligible" |

The disclosure's own course of action reads *"re-tying logic cannot and should not move a date
that already happened"* — so the days it could recover are **zero by its own wording**, and it
was the sole source of that 20. The number was not computed wrongly; it was **relabelled**. The
worst negative float among the activities the note cites — a population selected for what it
*records*, not for how much float it carries — was carried into three columns headed as
recovery, in the leadership deliverable that leaves the tool. That is Law 2, and it is the
design system's standing rule (*missing shows an em dash, never a fabricated figure*) inverted,
in the same family as MF-02/ADR-0411.

Two independent instruments agreed: the engine probe (`recommend` → `build_briefing` section
dump) and the rendered `/risks` card HTML.

## Decision

**Declare the kind on the finding; skip quantification for it; em-dash the cells.**

- `Finding.is_disclosure: bool = False`. **Declared by the producer, never inferred.** Neither
  category nor severity can carry this: `driving_path` is *also* INFO/OPPORTUNITY and *is* a
  genuine recovery lever ("recovering any of them pulls the focus date in"), so any fix keyed
  on category or severity would have silently de-quantified a real lever. A hard-coded
  metric-id set in the consumer would rot at the second disclosure.
- `_quantify` skips a disclosure, applying only the severity-fallback likelihood.
  **This is the single point**, deliberately not doubled: every downstream surface already
  renders a figure only when `impact_days is not None`, so one skip closes all of them. A
  second guard in `briefing.py` would be a defence-in-depth twin — and this arc has already
  paid for one (3 of 4 HOOK-02 mutants survived because a twin masked a dead layer).
- `_recovery_cell(f, none_label=…)` in `briefing.py` for §5.2 and §6. The existing `None`
  fallbacks ("risk reduction" / "risk mitigation") are *also* wrong for a disclosure — it
  neither reduces nor mitigates risk — so a disclosure prints `—`.
- The finding is **still disclosed**, cited, in both briefing tables and on `/risks`.
  ADR-0407's purpose was visibility; only the fabricated figure is removed.
- `_SEVERITY_LIKELIHOOD` hoisted to a module constant so the quantified path and the
  disclosure path share one table rather than two that can drift.

## Verification (QC-1)

- **Red first, by name:** 7 of 11 new tests failed against the pre-fix tree, including §6.2
  quoting the 20 wd. The other 4 are negative controls and a premise guard that pass pre-fix
  *by construction* — so their teeth are proven by mutation, not by their green.
- **Mutation battery 7/7 caught by name**, in a PYTHONPATH shadow of `src/` (import origin
  asserted; pristine control green before *and* after; both test files md5-identical at the
  end). M1 producer stops declaring the kind · M2 `_quantify`'s branch deleted · M3 the
  em-dash cell removed · M4 likelihood forced to CERTAIN · M5 *every* finding treated as a
  disclosure (gives `test_a_real_recovery_lever_keeps_its_quantification` its teeth) · M6
  disclosures filtered out of the briefing entirely (gives `test_the_disclosure_is_still_disclosed`
  its teeth — a "fix" that just deleted the row would otherwise have passed) · M7 ADR-0391's
  floor disabled (gives the premise guard its teeth).
  **M7 initially SURVIVED**: it was aimed at `recommendations.py` while the test it targets
  asserts on `cpm.py`. A mutant that cannot fail is not a mutant — it was re-aimed at the real
  subject and then caught. Recorded because the battery caught its own defect, not the code's.
- **Blast radius:** 275 passed across `test_recommendations` · `test_actual_start_disclosure` ·
  `test_risks` · all of `tests/ai/` · `test_briefing_memo` · `test_path_view` ·
  `test_manipulation`, with **zero moved pins**. No test in the tree named "Potential
  recovery", "Expected effect" or "potentially recoverable" before this ADR — which is why a
  fabricated figure in a leadership deliverable survived a full green gate.
- Full gate figures on the final tree in the handoff's Gate-at-close.

## Consequences

- ADR-0407 stands as to *what* it wired and *why the channel is separate from* `date_driven`.
  Its **category justification is superseded**: OPPORTUNITY never held that separation;
  `is_disclosure` does. The docstring in `_actual_start_floor_findings` that restated the
  false claim is corrected in the same commit, as is the ADR-0407 header note.
- `is_disclosure` is now the hook for any future provenance note. The next one gets the
  behaviour for free — and gets it *because it declares itself*, not because a consumer
  remembered to special-case it.

## The lesson this cost

**A claim verified against one module is a claim about that module.** ADR-0407's sentence was
not sloppy — it was precise, correct about `web/risks.py`, and generalised one module's
behaviour to "ever". QC-2 already says to scope a finding before acting on it; this is the
same error made in the *writing* direction. When an ADR justifies a decision by asserting what
the rest of the tree does, that assertion is a claim under QC-1 and needs its own executable
check — here, a two-line grep for the other consumers of `Category.OPPORTUNITY` would have
found `briefing.py` in seconds.
