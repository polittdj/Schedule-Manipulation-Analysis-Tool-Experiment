# ADR-0254 — parameterized expected-margin panel: Fig 5-30 editable band + SRA percentile spread (F3c-fuller)

## Status

Accepted. Completes the operator's verbatim F3c spec — *"parameterized expected-margin panel —
tier-a Fig 5-30 editable band + tier-b SRA percentile spread"* (the Thursday directive,
`00_REFERENCE_INTAKE/references/CLAUDE CODE NEXT PROMPT FOR THURSDAY 07162026.docx`). ADR-0253's
Gold-Rule rate parameter was the narrower first cut (its closing line queued "a per-phase margin
table" as future work — this is that work). Designed by a Fable 5 Max deep dive; every handbook
quote and code claim **adversarially verified against the PDF and the source** by a 4-agent
workflow before build (ADR-0240 protocol), with the lead independently re-reading the primary
pages.

## Grounding (verified verbatim against SMH Rev 2, 2024-03-15; printed page = PDF − 1)

- **Figure 5-30** (§5.5.11.2 «"How Much" Margin to Establish», printed p.120) is a three-row
  TABLE, "Established standards for margin allocation" — per-phase margin *rate ranges*, each
  explicitly "Varies" ("Example guidelines … consolidated from several NASA Centers"):
  CR→I&T "1-2 month of schedule margin per year"; I&T→ship "2-2.5 months …"; delivery→launch
  "1 day per week, 1 week per month, 1 month per year".
- **The band-vs-time chart form** comes from §7.3.3.1.6 (printed p.309: margin burndown tracking)
  and the Figure 7-32 prose (printed p.312): "Shown is a linear burndown but **stepped burndowns
  that mimic the margin guidelines over time** are sometimes used as well."
- **Deviation semantics** (§7.3.3.1.6 Thresholds, printed p.314): "Deviations from the guidelines
  trigger a requirement for either an explanation about why the deviation is acceptable or for the
  initiation of activities to mitigate the trend"; thresholds are program-set in the SMP.
- **Tier-b** is §7.3.3.2.3 "Sufficiency of Margin" (printed p.322): "using a stochastic tracking
  curve takes the results from a routine SRA and plots the results against organizational margin
  requirements", with the 70/50 Watch/Corrective percentiles quoted as the handbook's **example**
  values (Fig 7-45 prose, printed p.323; §7.3.3.2.1 "reasonable threshold recommendations",
  printed p.320) and §6.3.2.5.3.6's "For example, the P/p can select the 50th percentile as the
  planned schedule completion date and hold schedule margins to the 70th percentile" (printed
  p.267).

## Decision

**Tier-a — the editable Fig 5-30 band.** New pure module `engine/margin_guideline.py`:
`FIG_5_30_ROWS` (verbatim), `FIG_5_30_DEFAULT_RATES` with full provenance comments (the
`DEFAULT_SECONDARY_MAX_DAYS` pattern), `GuidelineBandConfig` (four operator-entered phase dates —
program facts, never derived — + three (low, high) wd/yr rates), `expected_margin_band` (the
stepped band: `edge(t) = Σ rate_edge × overlap_days(phase ∩ [t, launch]) / 365`, piecewise linear,
kinking at the boundaries, 0 after launch), `band_position` (below / within / above). Conversion
convention **1 month = 30 work days** — the ADR-0230/0253 Gold-Rule reading, which §6.3.2.5.3.6
says Fig 5-30 itself summarizes; row 3's three verbatim alternatives span (30, 84) wd/yr and all
three are quoted beside the inputs. Session state (`margin_band_dates`/`margin_band_rates`,
fail-soft setters, cleared on wipe), `POST /margin/band`, a cited control panel, the band overlay +
below-band hollow-diamond markers on the burn-down (theme tokens; legend wraps), month verdicts
suppressed on a mixed work-day basis (the erosion-fit refusal, disclosed identically).

**Tier-b — the SRA percentile sufficiency read.** `margin_risk_read` consumes the EXISTING
`sra` step-CDF — no new sampling: covered percentile = `CDF(D)` (pinned equal to the engine's own
`deterministic_percentile`), inverse step reads for each percentile, `covered(P) ⇔ finish(P) ≤ D ⇔
margin_needed(P) ≤ margin_wd` by construction. The margin window `[E, D]` is computed EXACTLY on
the run's own all-ML axis by the additive `sra.deterministic_margin_bounds` (the same
`{uid: _ml_minutes}` override map + `_finish_of` read as `compute_sra_ssi`'s anchor — pinned by
test; margin set = the confirmed overlay else the name-based default). `GET /api/margin/risk` is
button-triggered (never on page load), seeded/deterministic, offload-guarded, and echoes every
parameter; verdicts classify against operator-editable Watch/Corrective percentiles
(`margin_risk_pcts`, 70/50 prefilled AS EXAMPLES). Fail-soft: no schedule, a raised run, a
degenerate point-mass distribution (no uncertainty inputs), and no-margin each produce an honest
disclosure — never a fabricated verdict. The panel disclosed caveat: the simulation carries margin
in-network at plan (the handbook's Fig 7-43 curves are zero-margin, e.g. "Current Plan, Zero
Margin, With Risks"); a handbook-faithful zero-margin run via the existing three-point surface is
a documented follow-up.

**Export.** Three new tables on the Excel/Word margin export: the per-status-date band read (or
"not configured"), the band parameters (dates, six rates, the verbatim rows, the conversion), and
the SRA sufficiency read with full seeded provenance — computed at export time, byte-identical by
determinism.

**Citation correction (doc-truth, verified).** The sentence "The corrective action threshold is
set where the margin is 50% consumed" lives in **§7.3.3.2.3** (printed p.324) and is
**example-framed** ("In this example case, the P/p has chosen…") — NOT in §7.3.3.1.6 as ADR-0230
recorded (whose own Thresholds paragraph is deliberately non-numeric). The existing 50%-consumed
flag's *behavior is unchanged* (merged, pinned); its on-page copy and comments now cite
§7.3.3.2.3 as the handbook's example threshold. ADR-0230 stands as the historical record; this
ADR documents the correction.

## Consequences

- **No parity impact.** `margin_guideline` is pure arithmetic over engine outputs; the two
  `MarginMonth` offset fields are additive (assigned from existing locals — a test pins
  `D − E ≡ effective_margin_wd`); `deterministic_margin_bounds` is additive in `sra.py` (nothing
  existing calls it); the `parity` gate is untouched.
- Tests: `tests/engine/test_margin_guideline.py` (hand-computed band values, the two Law-2
  equivalence pins, CDF breakpoint semantics, degenerate/validation paths),
  `tests/web/test_margin_band_and_risk.py` (verbatim rows + cited defaults render, POST persists +
  fail-soft + clear, band JSON gating, month classification, degenerate disclosure + determinism +
  provenance echo, the corrected citation, export statements), + the additive-offsets pin in
  `test_margin_dashboard.py`. 4-theme Chromium check green (both visuals, zero console errors).
- Deferred (documented, not guessed): the zero-margin SRA toggle (Fig 7-43 fidelity); extending
  the band read to the per-version `/analysis` panel (it links to the dashboard instead — the band
  is inherently cross-version).
