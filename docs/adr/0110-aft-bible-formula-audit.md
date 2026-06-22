# ADR-0110 — `.aft` Bible formula audit: tool metric formulas vs the NASA Acumen library

Status: accepted (2026-06-22)

## Context

The operator delivered the authoritative metric library — `NASA Metrics_Complete_20260423.aft`, an
Acumen Fuse "Metric Library File" XML carrying **759 named metrics** (≈941 `<Formula>` nodes), the
verbatim formulas Acumen/NASA actually evaluate. Prior parity work validated *numbers* on specific
schedules; this audit validates *definitions* — does each metric the tool documents in
`src/schedule_forensics/web/help.py` mean the same thing NASA's formula says it means? "Assume
nothing": surface any hidden definitional drift **before** the next engine change, not after a
testimony-context number is challenged.

The `.aft` is CUI-class intake (`.gitignore` + the pre-commit guard block `*.aft`); it lives under
git-ignored `00_REFERENCE_INTAKE/audit/cei/` and is **never committed**.

## Decision

Add **`tests/engine/test_aft_formula_audit.py`** — a *definitional* check (NOT marked `parity`).
The tool's `help.py` formulas are plain-language pseudocode while the `.aft` uses Acumen's own
formula notation, so a literal string match is meaningless. The audit is therefore a **curated
correspondence table** (`AUDIT`), one row per documented metric, recording the matching NASA metric
`Name`, its **verbatim** `<Formula>`, a human verdict, and a note. Four tests:

1. `test_audit_covers_every_documented_metric` — the table and `help.py` stay in 1:1 sync (a new
   metric forces a classification decision).
2. `test_verdicts_are_valid_and_internally_consistent` — verdict vocabulary + formula/name presence.
3. `test_definitional_drift_is_documented_in_an_adr` — every `drift` row references this ADR.
4. `test_bible_sourced_metrics_map_to_a_bible_formula` — any metric whose `help.py` source cites the
   Bible must map to a verbatim Bible formula.
5. `test_pinned_nasa_formulas_match_the_live_bible` — when the `.aft` is on disk, each pinned NASA
   formula must still match the live file (a Bible-drift guard and the canonical record of which NASA
   formula each metric was built against). **Skips when the Bible is absent** (e.g. CI), exactly like
   the existing `.mpp` skips.

No engine or `help.py` changes — this PR only records the audit. (`help.py` accurately documents what
the **engine** computes; the drifts below are *engine-vs-NASA* differences, not *help-vs-engine*.)

## Audit result (93 documented metrics)

| Verdict | Count | Meaning |
|---|---|---|
| `match` | 34 | Semantically equivalent; only notation/wording differs. |
| `variant` | 3 | Deliberate, Acumen-validated tool extension/variant of a Bible metric. |
| `drift` | 4 | A **real** definitional difference (below). |
| `not_in_bible` | 52 | No formula-bearing Bible counterpart (DCMA-standard / EVM-standard / SSI / reference-deck / cross-version / tool-proprietary). |

All 34 `match` + 3 `variant` + 4 `drift` rows pin a NASA formula that was **confirmed verbatim against
the live `.aft`** (the pinning test passed with the Bible present). Highlights confirmed exact:
the baseline-compliance / Half-Step-Delay family (`Forecast to be Finished/Started`, `Completed On
Time/Late`, `Started On Time/Late`, `Not Started`, `Baseline Start/Finish Compliance`), the EVM indices
(`SPI`, `CPI`, `TCPI(BAC)`), the Bible-sourced HMI/CEI/FEI/BRI/Float-Ratio family (ADRs 0087/0098/0100/
0103), `Logic Density`, `Merge Hotspot`, `Insufficient Detail`, `Missing Logic`, `CPLI`, `BEI - Value
Tasks`, the duration ratios, and `Net Finish Impact`.

### The 4 definitional drifts

1. **DCMA-05 Hard Constraints** (and the schedule-quality `hard_constraints`). The engine counts
   `{MSO, MFO, SNLT, FNLT}` as hard. NASA's headline `Hard Constraints` formula counts
   `MandatoryStart, MandatoryFinish, MustStartOn, MustFinishOn, StartAndFinish` — i.e. **excludes
   SNLT/FNLT**. NASA's *other* variant, `B.03.12 FC IMS with hard constraints`, **does** include
   `StartOnOrBefore`/`FinishOnOrBefore` — so the tool follows the DCMA-14 / forecast-IMS convention,
   not NASA's headline one. **Latent**: no parity impact unless a schedule actually carries SNLT/FNLT
   constraints (the validated files did not).

2. **DCMA-08 High Duration.** The engine keys on **baseline** duration `> 44d`; NASA keys on current
   `OriginalDuration > 44d` **and** `ActivityType = "Normal"`. Differs whenever current duration ≠
   baseline duration, or for non-Normal activities. (On the validated files these coincided, hence the
   earlier "match"; the definitions still differ.)

3. **SPI(t).** The biggest find. The tool's SPI(t) = **Earned Schedule / Actual Time** (count/time-based
   ES). The Bible's `SPI(t)` is a **per-activity duration-ratio average** — `AVERAGE(IF(complete,
   baseline_dur/actual_dur, (baseline_dur − (Finish − ProjectTimeNow))/actual_dur))` — a *different
   metric of the same name*. This explains the documented **EVM2 residual (engine 0.27 vs Acumen
   0.56)**: it is not a value-vs-count earned-schedule gap alone but a different formula entirely.
   Directly informs the cost/value Earned-Schedule work (mandate item #2).

These four are **documented, not fixed** here. They feed the campaign backlog; any engine change to
close one is a separate, parity-gated PR.

### Notable `variant` rows
`cei_tasks_adjusted` (credits early completions; same denominator — validated 0.22), `avg_days_late`
(same kernel as NASA `Avg Days Late`, averaged over completed-behind only), `float_ratio_aggregate`
(ratio-of-means; the Bible metric with that exact formula is critical-path-scoped).

## Consequences

- The tool's metric definitions are now **machine-checked against NASA's verbatim library** wherever a
  formula-bearing counterpart exists; a future Bible refresh that changes a pinned formula fails the
  test loudly, and a new documented metric cannot ship without a conscious Bible classification.
- Three engine-vs-NASA definitional differences are on record (Hard Constraints constraint set,
  High Duration duration basis) plus the SPI(t) formula difference that frames the Earned-Schedule work.
- CI stays green without the CUI Bible (the pinning test skips); operator machines with the `.aft`
  run the full check.
