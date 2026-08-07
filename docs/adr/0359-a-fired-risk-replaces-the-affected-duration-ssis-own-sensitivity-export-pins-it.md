# ADR-0359 — A fired risk REPLACES the affected duration; SSI's own Sensitivity export pins it

- **Status:** Accepted
- **Date:** 2026-08-06
- **Supersedes:** the ADR-0307 reading "a risk-bearing task carries no Best/Worst uncertainty
  — the risk drives it" and the additive fold-in both models used since ADR-0123
- **Related:** ADR-0356 (the first stale-setup exoneration), ADR-0309 (the weighted-histogram
  reading discipline), ADR-0269 (JCL shares the finish marginal)

## Context

The operator reported a significant delta between the tool's SRA + Duration-Sensitivity
results and SSI's, and committed a fresh oracle set (main `f1f13f9`): the schedule
(`00_REFERENCE_INTAKE/SRA Large Test File2.mpp`, 2,125 tasks / 998 stored factors / 919
stored Best-Worst pairs / 2 stored register risks), SSI's 5000-iteration SRA histogram, and —
new — SSI's **Sensitivity** export.

**Inputs before engines (the ADR-0356 lesson, applied first).** The operator's session had
replayed a setup captured against a 783-task vintage: all 783 setup UIDs exist in the
committed file, but only 98 of the 435 comparable factors agree and **0 of 406** Best/Worst
pairs agree. That input mismatch is the largest term of the on-screen delta and is
session-side. The v4 fingerprint warning fired as designed; what was missing was an effortless
remedy (ADR-0360 adds the one-click).

## The measurement that found the engine's own term

On **file-true inputs** the engine still ran +25 mean / +32–35 cal days long at P50–P90
against the weighted histogram (sigma +7.6%). The deterministic OAT comparison then isolated
it beyond argument:

- All **64 duration rows** of SSI's Sensitivity sheet matched the engine's one-at-a-time
  re-solves to ≤0.01 wd / ≤0.05 cal d — CPM, calendars, ML basis and duration application are
  EXACT.
- The two **R/O rows** disagreed by exactly the affected tasks' ML durations:
  SSI fired-alone slip **304.48 wd for a 321-wd impact** on a 16.52-wd-ML task, and
  **35.03 for 45** on a 9.97-wd ML. `321 − 304.48 = 16.52`. `45 − 35.03 = 9.97`.

**A fired risk's impact REPLACES the affected activity's remaining duration. The engine was
ADDING it on top.** And SSI lists both R/O tasks as duration-sensitivity rows too, so the
affected activity samples its own Best/Worst in the iterations the risk does not fire — the
forced point-mass was the same misreading's other half.

## Decision

1. `compute_sra_ssi` and `compute_jcl` (the shared marginal): a fired risk's impact replaces
   the affected activity's sampled duration; several risks firing on one activity in one
   iteration replace with their summed impacts; the ADR-0308 completed-work guard stands.
2. Risk-affected activities keep their three-point sampling when not fired.
3. `compute_oat_sensitivity` gains register R/O rows (fired-alone, replace semantics) ranked
   among the duration rows — the SSI-parity tornado, which the /sra page and exports surface.

## Verification

- With replacement the full MC lands **mean +414.6 vs SSI +417.9 cal, sigma 155.2 vs 152.4,
  P10/P50/P80/P90 within 1–3 days** of the occurrence-weighted histogram (never the workbook's
  unweighted summary cells). Per-risk outcome means land at 305.9/37.9 wd vs SSI's
  deterministic 304.48/35.03.
- New parity oracle `tests/parity/test_sra_ssi_oracle_uid152_v2.py`: OAT row-for-row against
  the full Sensitivity sheet (≤0.06 wd), the weighted-histogram distribution, and the
  per-risk outcomes. The July uid152 oracle still passes 5/5.
- Old additive pins rewritten as sharper replace discriminators (an impact SMALLER than the
  ML pulls the finish BELOW deterministic — impossible under add); all four new pins
  mutation-proven (replace→add: 4 failed; restored: green), the OAT row separately.

## Deliberately NOT done

The legacy multiplicative-% model keeps its own semantics (a percentage uplift has no
replace/add ambiguity). The `impact_pct` derivation in the register is presentation-side and
unchanged.
