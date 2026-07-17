# ADR-0237 — /standards: the Standards & Execution Indices page (PR-M1)

## Status

Accepted. The operator-requested dedicated page for the Acumen/NASA metrics, the DCMA metrics,
and the Schedule Execution Metrics from the metrics library. This PR is presentation-only
(re-projection of existing, parity-validated engine calls); the 9 unbuilt SEM metrics land next
(PR-M2) with engine math + MetricDocs + formula-audit pins against the committed Fuse goldens.

## Context

A metrics-library audit found all three families lacked a formula-first home: DCMA-14 was
scattered over five surfaces; the NASA/Acumen-Fuse execution indices existed only as trend
charts; and the Bible's "Industry Standards / Schedule Execution Metrics (SEM)" group (10
metrics) had exactly one implemented member (BRI-Cumulative) and zero UI presence. Formulas and
sources lived only in /help, decoupled from live values.

## Decision

One new SETUP page, `/standards` ("Standards & Execution Indices"), three sections, one row per
metric: Value · Status pill · Threshold · verbatim Formula · Source — all doc fields from the
single `help.py` dictionary (the same entries the formula-audit test pins to the `.aft` Bible).

- **DCMA-14 (16 rows):** re-projects the cached `analysis.audit` (`audit_schedule`) — no new math.
- **NASA/Acumen-Fuse indices (~14 rows):** the single-file forms of HMI, CEI (needs a prior
  version; the page says so when only one file is loaded), FEI, BRI, Float Ratio™ (canonical +
  aggregate), MEI, and SPI(t)-Acumen — the same engine calls /performance trends.
- **SEM (10 rows, Bible header names verbatim):** BRI-Cumulative live; the other nine read "—"
  with an explicit "not built — PR-M2" status. Never a fabricated number (Design-System DoD).

Values are computed on the LATEST loaded file (stated on-page, with the prior file feeding the
period metrics). Verified in all four themes (Chromium). An Excel/Word export for the page joins
PR-M2 with the SEM math so the export is complete rather than shipping a 9-dash artifact.

## Consequences

- Every metric the tool implements in these families now shows its live value beside the pinned
  formula and source on one page, and the SEM gap is visible and honest instead of silent.
- PR-M2 fills the nine SEM rows from `engine/metrics/sem.py`, each with a MetricDoc + an AUDIT
  row (the help↔AUDIT 1:1 test enforces that path) and parity against the committed SEM goldens
  (P2/P5: 20|5|0|0.74|… / 27|2|0|0.59|…; Large Test File/File2: 609|49|0.03|0.51|… /
  630|24|0|0.51|…), reconciling the SEM-vs-DCMA BEI-Cumulative definitional divergence per the
  ADR-0176 dual-metric precedent.
