# ADR-0112 — Refresh the Project5 golden to the authoritative file

Status: accepted (2026-06-22)

## Context

ADR-0109 found (and ADR-0111 / #207 confirmed against Acumen's `2345` Metric History Report) that
the committed `tests/fixtures/golden/project2_5/Project5.mspdi.xml` was a **stale capture**: it
carried **37 stored-critical** activities, while the authoritative current `Project5_TAMPERED.mpp`
on the operator's intake has **4** (Critical Path / Zero-Days-Float = 4). The stale golden forced
the parity gate to carry a `DCMA06` High-Float "+1 residual" (40 vs golden 41) and a cluster of §E
change-metric residuals that only existed because the golden disagreed with the live file. Build
step 3 is to refresh the golden so the committed fixture *is* the authoritative file.

The four candidate `Project5_TAMPERED.mpp` copies in the intake are byte-identical
(`md5 470fb216…`), so the source is unambiguous. The fresh MSPDI was produced with the vendored
MPXJ (`java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi`), same path the prior golden used.

## Decision

Replace the committed Project5 golden with the MSPDI conversion of the authoritative
`Project5_TAMPERED.mpp` (same 379-UID structure; 4 stored-critical, not 37) and re-pin the goldens:

- **`case.json` §A/§B/§C** updated to the authoritative figures. The headline set is **Acumen-exact**
  and independently anchored by `test_chain_acumen_reference.py` (ADR-0111) against the `2345`
  report: `DCMA01`=5, `DCMA05`=1, **`DCMA06`=44** (the former +1 residual is closed for *both*
  projects), `DCMA07`=0, `DCMA14`=0.59 / 27; schedule-quality `critical`=4, `hard_constraints`=1;
  §C baseline-compliance, single-schedule CEI and the pairwise bow-wave CEI are **unchanged** (the
  refresh did not move them) and stay exact.
- **§A `missing_logic`** is recorded all-activity-scoped (P5 = 7). Acumen's report-scoped Missing
  Logic is incomplete-scoped and equals `DCMA01` = 5 (exact via the chain test). Documented in
  `case.json._deltas`.
- **§E change metrics** (`change_P2_to_P5`) are pinned to the engine's **pure-logic CPM** output on
  the authoritative file. The date-deterministic subset (finish/start slips, net-finish-impact,
  completed, in-progress, activities-added) is Acumen-equivalent date arithmetic; the
  float/critical-dependent subset (`new_critical`, `no_longer_critical`, `float_erosion`) is
  pure-logic CPM by design (ADR-0010) and awaits a fresh Acumen §E PP&Change export for the current
  P5-vs-P2 pair for cross-tool re-validation. Documented in `case.json._deltas`.
- The parity gate (`test_parity_gate.py`) is **tightened**: `DCMA06` P5 is now asserted exact, and
  the §E residual deltas are replaced by exact assertions against the refreshed golden.
- The downstream **derived/tool** goldens (float bands, diff, forecast, manipulation, trend,
  recommendations, path-evolution, schedule-card and the web/AI views) are re-pinned to the engine's
  current output on the authoritative file — tool-truth regression locks, not Acumen parity.

### SSI driving slack — xfail, input-blocked

`tests/fixtures/golden/ssi_uid143/case.json` (107 UniqueIDs + a 36-task driving chain) was validated
against the **SSI** MS Project add-on run on the **prior** Project5 (37 stored-critical). With 4
critical the driving structure changes completely, and **no SSI export for the authoritative file is
in the intake**. Rather than re-pin it to engine output (which would silently relabel SSI-validated
provenance as engine-truth), `test_ssi_driving_slack_exact` and `test_golden_ssi_driving_slack_parity`
are marked `xfail` (non-strict) pending an SSI driving-slack export for the current
`Project5_TAMPERED.mpp`. The SSI golden file is left untouched so the re-pin is trivial when the
export lands.

## Consequences

- The committed Project5 golden now **is** the authoritative file; the stale-capture residuals
  (`DCMA06` +1, the §E deltas) are closed. The parity gate is exact on every Acumen-anchored figure.
- Two inputs remain confirmed-missing (tracked in `docs/STATE/HANDOFF.md`): an **SSI** driving-slack
  export for the current Project5 (to lift the xfail and re-pin `ssi_uid143`), and an **Acumen §E
  PP&Change** export for the current P5-vs-P2 pair (to cross-validate the float/critical change
  subset). Neither blocks the rest of the gate.
- The Large-Test-File CEI/HMI cross-version reference (ADR-0111) is still open and unaffected.
