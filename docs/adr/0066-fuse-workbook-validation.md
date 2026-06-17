# ADR-0066 — Validate the tool against the operator's Acumen Fuse workbook exports

Date: 2026-06-17 · Status: accepted

## Context

The operator ran Acumen Fuse on a single workbook of all 14 test projects (2945 activities) and
provided the exports (Schedule Quality docx + Ribbon/Phase workbooks + the DCMA Report), asking
to (1) validate the tool against them, (2) add the missing Fuse metrics, and (3) add the year
Trend/Phase view. This ADR covers (1); (2) and (3) follow as their own PRs.

## Decision

Record the Fuse reference values and compare the tool to them on the fixtures that live in the
repo (TP1–TP4 v1–v5, Project2), in `docs/FUSE-VALIDATION.md`, with a regression test
(`tests/engine/test_fuse_reference.py`). **No engine/CPM change** — the engine stays pinned to
the curated Acumen-parity goldens (`pytest -m parity` 10/10); the validation is documentation +
tests, and any difference is categorized rather than "fixed" into the engine.

## Findings

- **Completion matches exactly.** Counting normal (non-milestone) completed activities, the tool
  equals Fuse on all eight in-container fixtures (20 / 4 / 8 / 1 / 3 / 5 / 7 / 7). The tool's
  headline "N complete" reads one higher wherever a milestone is complete because it counts
  milestones in the activity-completion figure; Fuse narrates normal-only. Definition difference,
  not a defect — pinned by the test.
- **Finish dates match on the unambiguous cases** (TP4 v1–v4). The gaps are documented causes:
  TP2 (MS Project dropped the 4×10 calendar's holiday exceptions on `.mpp` save — committed XML
  authoritative, PARITY-REPORT R-04); TP4 v5 (committed MSPDI computes 06-26 vs Fuse's `.mpp`
  07-17 — fixture/manifest); and the workbook's Project2 reading 09-14 while the committed golden
  + native `.mpp` both compute 08-30 (operator to confirm the workbook used the same file).
- The Fuse **proprietary metrics** (Logic Density™, Insufficient Detail™, Merge Hotspot, Float
  Ratio™, Avg/Max Float, Fuse's Leads/Lags counts) and the **year Trend Analysis** are recorded
  as the calibration targets for the follow-on PRs.

## Scope / safety

Docs + tests only → **parity 10/10**, full suite **894 passed**, no source change. The committed
`.mpp`-only projects (Large Test File, Duration Bomb, Project3/4, Project5_TAMPERED) are recorded
for the operator to reconcile locally (they do not travel to the container).
