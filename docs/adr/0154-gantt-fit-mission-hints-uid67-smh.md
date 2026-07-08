# ADR-0154 — Operator work order: Gantt fit-to-data-date, Mission Control visual explainers, SSI UID-67 re-pin, SMH threshold re-sweep

## Status

Accepted. Four deliverables from the 2026-07-08 operator message + the same day's uploads.

## Decisions

### 1. "Fit project" fits the REMAINING project, anchored on the status date

The old Fit squeezed the entire history into the viewport, so on a long-running schedule the
remaining work (the part being managed) was compressed into the far right. Per the operator
spec: Fit now places the **status date ~12% in from the left edge** of the visible timeline
(`FIT_LEAD`) and scales so **status date → project finish fills the rest of the page**; the
completed past stays on the track and scrolls off to the LEFT. Falls back to whole-project fit
when the schedule has no status date. The Scale slider steps at **0.05 px/day (min 0.2)** for
fine control, and the Name column defaults to the operator's preferred width (280–460 px).

### 2. Mission Control tiles explain themselves on hover

Every tile's NAME is now a hover target (dotted underline + help cursor) carrying a four-part
callout — **WHAT** it shows, a concrete **EXAMPLE**, **HOW TO READ** it, and what to **DECIDE**
from it — rendered pre-line in a wide `data-sf-hint` variant. All nine tiles covered (S-Curve,
Bow Wave/CEI, Forecast Drift, Quality Offenders, Finishes, Data-date Finishes, Slippage,
Critical-Path Evolution, Quality Trend); the prose is decision-focused and consistent with the
ADR-0146 page explainers.

### 3. SSI UID-67 export re-pins driving-slack parity; the stale ssi_uid143 golden retires

The operator delivered `00_REFERENCE_INTAKE/ssi/Project5_TAMPERED_UID_67_Directional_Path_
Analysis_2026-7-8-8-19-10.xlsx` (SSI Directional Path Tool, Predecessors, Driving Slack ≤ 0 d,
Waterfall). The engine reproduces it **UID-for-UID before pinning**: the exact 20-task Path-01
membership, 0 driving slack on every path task, correct chain order. New golden
`tests/fixtures/golden/ssi_uid67/case.json` (SSI Drag recorded provenance-only — the engine
does not compute drag); the two `ssi_uid143` xfails are REPLACED by live tests and the stale
golden (prior 37-critical file, ADR-0112) is deleted — **the suite now has zero xfails**.
SSI parity on the authoritative file is pinned by two independent exports (uid67 path-membership
+ uid145 all-dependencies).

### 4. Schedule Management Handbook re-sweep closes ADR-0153's caveat

The operator delivered the actual **NASA Schedule Management Handbook Rev 2 (2024-03-15)**
(409 pp). Re-sweep results, written at the points of use:

- **Path tiers:** SMH p.118 — "common practice to track the primary, secondary, and tertiary
  critical paths, at a minimum" (+ p.123, Fig. 6-12 p.183). Crucially, the SMH states the
  near-critical float threshold is set **"by the P/p management"** — the numeric day values are
  *deliberately project-defined per NASA's own handbook*, so this tool's operator-overridable
  defaults are the handbook-conformant design, not a documentation gap.
- **Hidden-duration lag check:** SMH p.172 — lags "tend to hide detail in schedules and cannot
  be statused": the check's rationale, nearly verbatim. No numeric ratio published → 35% stays
  a documented design choice.
- **Merge hotspot:** SMH p.207 — "Merge bias indicates the complexity of the start of an
  activity due to having a large number of predecessor activities." No numeric count published
  → the link-count floor stays a documented design choice.

F-14 is now closed at full strength: every threshold's practice AND the delegation of its
numeric value are handbook-cited.

### 5. Intake tidy

The root-level upload strays (2× SP-2024 PDFs, PM handbook, SOPI — byte-identical duplicates of
the intake copies) are removed; the SMH zip moves into `00_REFERENCE_INTAKE/`.

## Consequences

- Zero xfails and zero skips across the suite; SSI parity fully re-pinned on the authoritative file.
- The operator's remaining asks shrink to: SSI focus UID for `Large_Test_File.mpp` (A-4) and a
  Fuse export containing an elapsed in-progress activity (D7).
