# ADR-0279 — CPLI stored-float / stored-finish: Acumen-parity option for DCMA-13

Status: accepted (2026-07-21)

## Context

CPLI (DCMA-13, Critical Path Length Index) = (remaining critical-path length + project total float)
÷ remaining critical-path length. Our engine computes it from the **recomputed pure-logic CPM**
(`_cpli` over `CPMResult.timings`): the min recomputed total float and the recomputed project finish.
On the operator's two heavily progressed production schedules this disagreed with Acumen Fuse:

| File | ours (before) | Acumen ribbon |
|---|---|---|
| Large Test File | 1.00 | **0.97** |
| Large Test File2 | 1.00 | **0.59** |

Root cause, established against the ground-truth ribbon values (`00_REFERENCE_INTAKE/acumen_v8.11.0/
… Analyst Quick Add Metrics.xlsx`, "Ribbon Analysis" sheet) on the committed `.mpp`s:

- **Project float.** With no imposed deadline in the *logic*, the recomputed min CPM float is ~0, so
  our CPLI pins to 1.00. Acumen uses the file's **stored, progress-aware Total Slack**, which is
  negative on a behind-schedule file (min −28 d on File 1, −435.7 d on File 2). This is the same
  stored-vs-recomputed divergence `effective_total_float` already resolves for DCMA-06/07 — CPLI was
  simply never switched over.
- **Remaining critical-path length.** Acumen's denominator is the **stored** remaining duration (data
  date → the stored project finish). Our recomputed pure-logic CPM collapses File 2's finish to ~2025
  (a chain resolves early), giving a 78-day remaining length; the stored schedule finishes ~2028
  (~1053 working days). File 1's recomputed and stored finishes nearly coincide, so File 1 is fixed
  by the stored-float change alone; File 2 needs the stored finish too. The two are **inseparable**:
  min stored float with the recomputed (collapsed) length gives File 2 a nonsense −4.55.

Using **both** stored inputs reproduces Acumen **exactly**: File 1 → 0.9698 ≈ 0.97, File 2 → 0.5863 ≈
0.59.

The golden **P2/P5** CPLI is 1.0 and must not move.

## Decision

`compute_dcma14(schedule, cpm_result=None, *, exclude_milestones=False, cpli_stored_float=False)`
gains an opt-in flag; `audit_schedule` forwards it. When enabled, `_cpli` computes:

- **project float** = `min(effective_total_float(t, recomputed) for t in non_summary(schedule))` — the
  stored Total Slack when the file carries it (else the recomputed fallback), matching DCMA-06/07;
- **remaining length** = `max(stored activity finish) − status_offset` — the stored project finish,
  falling back to the recomputed `project_finish` when no stored finishes exist.

The offender citation on FAIL follows the same float basis (the most-negative effective-float chain).

**Default off.** With `cpli_stored_float=False` the computation is byte-identical to before, so the
P2/P5 golden is untouched. Even *enabled*, P2/P5 stay at CPLI 1.0: their min stored slack is a small
**positive** value (+1 day) against a long remaining length, so the ratio rounds to 1.00 (verified).

**Configurable in the deployed tool.** `SessionState.dcma_cpli_stored_float` (default False), added to
`_scope_signature` **only when enabled** (a second key part `C=1`, so the default epoch's cache-key
shape is unchanged and toggling re-keys → never a stale CPLI). A second checkbox on the `/analysis`
DCMA panel shares the milestone-scope form and POSTs to `/dcma/scope`; the executive-briefing DCMA
snapshot honours it too. It composes with the milestone scope (both on → signature `M=1`+`C=1`).

## Consequences

- With the option enabled, CPLI matches Acumen's ribbon **exactly** on the operator's files (0.97 /
  0.59) and correctly reports a behind-schedule project as < 1 (< the 0.95 bar → FAIL), where the
  recomputed default reads a misleading 1.00.
- Default-off keeps every existing parity/golden test green; no CPLI math changes for anyone who does
  not opt in. This mirrors the ADR-0277/0278 milestone-scope option (both are "read Acumen's stored,
  progress-aware view"); a future consolidation into one "Acumen parity mode" is possible but not done
  here (the milestone toggle already shipped standalone).

## Verification

`tests/engine/metrics/test_dcma14.py`: `test_cpli_stored_float_reads_stored_slack_and_finish` (a
behind-schedule synthetic — default 1.0, stored scope < 1 and FAIL, exact against the stored
finish/slack) and `test_cpli_stored_float_keeps_one_when_ahead` (the P2/P5 shape rounds to 1.0 under
the stored scope). `tests/web/test_dcma_scope.py::test_cpli_stored_float_toggle_flips_flag_and_signature`
(the checkbox renders, flips the flag + `C=1`, composes with `M=1`, clears). The real-file result
(0.97 / 0.59 exact) was reproduced in a sandbox against the MPXJ-converted MSPDI of the committed
`.mpp`s; the 9 MB `.mpp` / 20 MB MSPDI are not re-committed.
