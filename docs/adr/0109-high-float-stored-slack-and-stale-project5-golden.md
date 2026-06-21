# ADR-0109 — Close the DCMA-06 High Float residual (stored Total Slack); Project5 golden is stale

Status: accepted (2026-06-21)

## Context

The operator supplied the authoritative reference bundle the parity gate had been missing: the source
`.mpp` files (`Project2.mpp`, `Project5_TAMPERED.mpp`, the `TP*`/`EVM*`/Large-Project test suite) **and**
the Acumen Fuse exports run on them (DCMA / Metric History / Detailed / Quick-Add). All operator-
confirmed **test files, not CUI**. This is the first time the engine can be diffed metric-by-metric
against Acumen on the same inputs Acumen actually scored.

Auditing Project2/Project5 against the `P2-P5 - Metric History Report` (converting the source `.mpp`
fresh via the vendored MPXJ) produced two findings:

1. **High Float (DCMA-06) was the one structural gap.** It was a long-standing documented residual
   (ADR-0012): the engine scored it on **recomputed pure-logic CPM float** with `> 44` working days,
   giving 43 (P2) / 56 (P5-authoritative), while Acumen reports **44 / 44**. Negative Float (DCMA-07)
   and the Critical metric already score on the source tool's **stored, progress-aware Total Slack**
   via `effective_total_float` / `is_effective_critical`; High Float was the lone hold-out. Scoring it
   on stored Total Slack reproduces Acumen **exactly (44 / 44)**.

2. **The committed `Project5.mspdi.xml` golden is STALE.** The current `Project5_TAMPERED.mpp` carries
   **4** stored-critical activities (= Acumen's "Critical Path" 4 and "Zero Days Float" 4); the
   committed golden has **37**. The engine reads whichever file it is given correctly — on the fresh
   authoritative conversion every audited metric matches Acumen (Missing Logic 4/5, Hard Constraints
   0/1, Critical 41/4, BEI 0.74/0.59, …). The divergence is the golden, not the engine.

## Decision

1. **DCMA-06 High Float scores on `effective_total_float`** (stored Total Slack when the source carries
   it, else recomputed CPM float) — identical treatment to DCMA-07. Verified 44/44 against the
   authoritative Acumen export; closes the ADR-0012 residual. Project2 (golden == authoritative file)
   is now an **exact** parity assertion.

2. **Do NOT refresh the Project5 golden in this change.** It is stale, but refreshing it ripples
   through every test that asserts a Project5-derived value (trend, manipulation, web views, baseline
   compliance) and must be re-pinned against the full set of authoritative Acumen values — a dedicated
   re-baseline. Until then Project5's High Float stays a +1 residual (engine 40 vs stale golden 41),
   and the parity gate documents *why*.

## Consequences

- One more DCMA-14 metric is now exact against Acumen; the engine matches Acumen on the entire audited
  Project2 ribbon.
- The **Project5 golden refresh** is the next required step for true P5 parity, and is the safe
  foundation (now that the authoritative `.mpp` + Acumen exports are in hand) for the in-progress
  progress-scheduler work (ADR-0108): the prior attempts could not be validated because the P5 golden
  did not match any Acumen reference — it now can.
- Audit still open (operator mandate "validate everything"): Large-Project2 and Workbook1
  (Large-Test-File) Acumen exports, the `TP*` suite (no Acumen export yet — schedules only), SSI
  parity, and the cost/value-based Earned Schedule (Acumen SPI(t)).

## Verification pointers
`P2-P5 - Metric History Report.xlsx` (Project2 sheet): High Float 44d = 44 (P2) / 44 (P5); Critical
Path 41 / 4; Zero Days Float 41 / 4. Engine: `engine/metrics/dcma14.py` DCMA-06 (now
`effective_total_float`); `engine/metrics/_common.py` `effective_total_float`. Authoritative source
files + Acumen exports held read-only under the git-ignored `00_REFERENCE_INTAKE/audit/`.
