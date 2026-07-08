# ADR-0153 — F-14 threshold-citation sweep against the delivered NASA handbooks

## Status

Accepted. Closes audit F-14 / PARK-LIST A-8 (the last handbook-gated documentation item).

## Context

The 2026-06 audit flagged three display thresholds as unsourced in-repo design choices (F-14):
the driving-slack secondary/tertiary tiers (10/20 working days), the hidden-duration lag ratio
(35% of activity duration), and the WBS float-erosion band (10 working days). ADR-0143 documented
them as design choices "re-source when the handbook lands." The operator has now delivered nine
NASA handbooks into `00_REFERENCE_INTAKE/` (PPC SP-2016-3424, PM SP-20220009501, WBS, IBR, SRB
SP-20230001306, SOPI 6.0, EVM implementation, Risk Management v2 ×2).

## Decision

All nine PDFs were text-extracted and swept page-by-page for float/slack day-bands, lag ratios,
near-critical language, path-tier terminology, and merge/convergence guidance. Findings, written
at each point of use:

1. **Float-erosion 10-day band — SOURCED.** The PPC Handbook's schedule health check
   (Fig. 3.4-3, p.138) scores **"Tasks Less than or equal to 10 days Total Slack"** as its
   near-critical Total Slack screen — exactly the band `float_erosion._LOW_FLOAT_DAYS` uses.
2. **Secondary/tertiary path tiers — practice SOURCED, day values not published.** The
   primary/secondary/tertiary monitoring convention is NASA practice (PPC p.125 and §3.4.3.2D
   p.151 waterfall report; SOPI 6.0 p.37 — "near critical … also referred to as secondary or
   tertiary paths"; SRB Handbook PDF p.48). No delivered handbook fixes the numeric cutoffs:
   the 10-day secondary default aligns with the PPC Fig. 3.4-3 slack screen; the 20-day
   tertiary default remains this tool's (operator-overridable) convention.
3. **35% lag ratio and merge-hotspot link count — remain design choices.** Lag *scrutiny* is
   handbook-mandated (PPC p.136: lead/lag is not schedule margin; §3.4.3.2B p.145: validate lag
   values; Fig. 3.4-3 counts lags per relationship type), but no delivered handbook publishes a
   lag-to-duration ratio or a merge/diverge link count. Both stay documented design choices.

Ledger updates: VERIFICATION-REPORT F-14 → CLOSED; PARK-LIST A-8 → CLOSED with the explicit
caveat that the **NASA Schedule Management Handbook (SP-2010-3403) itself is not in the intake**
— it is cited BY the PPC handbook and is the one document that could still put numbers on the
two unsourced values. If the operator delivers it, re-run the sweep for those two.

## Consequences

- Every F-14 threshold now states its authority (or its absence) at the point of use, with
  document number, section/figure, and printed page — testimony-grade provenance.
- No numeric threshold changed: the sweep found the 10-day band already agreed with the PPC
  screen, and changing the unsourced two without authority would be guessing (Law 2).
- The audit's F-series is now fully closed in-env; remaining parity asks are operator artifacts
  (SSI export A-4/A-5, elapsed-activity Fuse export D7, SP-2010-3403).
