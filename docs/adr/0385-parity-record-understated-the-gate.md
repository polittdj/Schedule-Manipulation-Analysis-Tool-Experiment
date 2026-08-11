# ADR-0385 — The parity record understated the gate, and the gate could silently stop measuring

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0112 (the authoritative Project5 refresh that made `ssi_uid143` stale),
  ADR-0115 (the focus-145 SSI export), ADR-0154/0155 (the focus-67 SSI Directional Path export
  that RETIRED the xfail), ADR-0151 (the Fuse-validated §E subset), ADR-0305 (the browser job's
  "fail loudly if the proof silently skipped" pattern this ADR applies to the parity gate),
  ADR-0346 (the `floor` job: a declared property nobody runs is decoration)
- **Related:** Law 2 (fidelity over speed); audit F-03 (the last time `PARITY-REPORT.md` drifted
  behind the golden)

## Context

The operator asked for whatever most improves the accuracy and consistency of the tool's numbers
against **Acumen Fuse**, **SSI** and **MS Project**. The obvious candidates — the missing
sub-day-negative-float Acumen run, the FX-03/04 re-convert — are operator-gated: they need
licences this session does not have. So the question became: *of the things reachable from here,
what actually moves measured fidelity?*

Measuring first produced three findings: one in the evidence, one in the gate, and one in a guard that was holding the bad evidence in place.

## Finding 1 — the parity record claimed an SSI gap that had been closed for a month

`tests/fixtures/golden/project2_5/case.json`'s `_deltas` and `docs/PARITY-REPORT.md` both stated
that SSI driving-slack parity had a **stale golden and a live `xfail`**, "pending a fresh SSI
export for the current file" (ADR-0112). Verified against the tree, every clause was false:

| claim | reality |
| --- | --- |
| `tests/fixtures/golden/ssi_uid143` is stale | the directory **does not exist** — it was removed |
| `test_ssi_driving_slack_exact` is `xfail` | the test **does not exist**; no SSI xfail remains |
| pending a fresh export | the export **arrived 2026-07-08** (ADR-0154/0155) |

What actually replaced it — both asserted **in the parity gate**, both **exact by UniqueID** on
the authoritative `Project5_TAMPERED.mpp`:

- `ssi_uid67` — SSI Directional Path Tool, *Driving Slack ≤ 0 d*: the exact **20-task** Path-01
  membership, every member at 0 days (`test_ssi_driving_slack_uid67_exact`).
- `ssi_uid145` — *Get all dependencies*: **108 UniqueIDs** plus the 2/3/8/95 tier counts
  (`test_ssi_driving_slack_uid145_exact`).

So the tool's own parity record **understated its measured SSI fidelity**. That is the expensive
direction to be wrong in: in a testimony context the report is the artifact a reader cites, and it
was volunteering an unvalidated gap that does not exist. Corrected in both places.

## Finding 2 — the Law 2 gate could silently stop measuring

The `browser` job already carries a step named *"Fail loudly if the proof silently skipped"*, with
a comment recording why it matches ANY skip rather than a reason string: an earlier version grepped
for one reason, went green in 59 s, and missed three tests skipping for a different one.

**The parity gate had no equivalent** — and it is conditional in three ways: `needs_java` (the SSI
SRA Monte-Carlo oracles convert `SRA Large Test File2.mpp` through the vendored MPXJ),
`needs_mpp` / `needs_artifacts` (reference files under `00_REFERENCE_INTAKE/`), and a
`pytest.skip` inside `_oracle_workbook()` when the SSI export glob finds nothing. Any of those
going missing narrows the gate **silently and green**.

Measured, not hypothesised — the same scoped command with `java` hidden from `PATH`:

```
8 skipped in 0.25s      # the SSI/Acumen Monte-Carlo oracles, gone
```

Eight of the gate's 52 tests — the strongest external-oracle tier — disappear in a quarter of a
second, and `pytest -m parity` exits **0**. A green "Parity gate" badge over a run that compared
nothing to Acumen or SSI.

## Finding 3 — a guard was pinning the stale claim in place

Correcting the report turned `tests/web/test_docs.py::test_parity_report_states_the_headline_results`
red. Its assertion was `"107" in parity`, commented *"SSI 107/107"* — and `107` appeared **only** in
the two retired `ssi_uid143` lines. So a documentation guard had been holding the false statement
up: removing the obsolete row read as a regression, and the path of least resistance was to put the
stale number back.

This is the sharpest form of the session's lesson. An evidence record decays quietly; a **guard
pinned to the decayed statement actively resists the correction.** Repointed to the live oracles and
made strictly stronger (two assertions where there was one), then tightened again: `"108"` alone is
satisfied by the string `ADR-0108`, so a gutted SSI row would still have passed. The assertion is
`"108 UIDs"`, and the falsification gutted the SSI row while leaving every `ADR-0108` mention intact
to prove the guard was not passing incidentally.

## Decision

1. **Correct both parity records** to the measured truth, and state plainly that the entry had
   understated fidelity.
2. **Guard the parity gate against silent narrowing**, replacing the bare `pytest -m parity` step
   in BOTH the `test` and `floor` jobs with the `browser` job's proven pattern: run, `tee`, and
   fail on ANY skip. Scoped to the parity **paths** deliberately — a bare `pytest -m parity` also
   collects (and skips) the playwright modules, so a whole-run skip match would false-positive
   forever. Runtime is unchanged: the guarded step replaces the old one rather than adding a run.
3. **Do NOT add `setup-java` in the same change.** Pinning policy requires a 40-hex SHA, and more
   importantly: adding the JDK *and* the guard together would mask the answer. If CI has been
   running the oracles all along the guard passes; if it has not, the guard says so on this PR.
   Make the invisible visible first, then fix what it reveals.
4. **Pin the correction with a guard that generalises.** String-pinning the new prose would catch
   only this instance. The property that generalises is *the parity evidence may not cite a golden
   fixture that does not exist* — a path citation is an instruction to go and look. Historical
   mentions are written as bare names, not paths.

## Verification

- **Parity gate, full:** 52 passed, 0 failed, 12 m 35 s. Every skip in the unscoped run is
  playwright/UI; **no parity test skipped**. Scoped to the parity paths: **52 passed, 0 skipped**.
- **Every new or repointed guard was proven able to fail**, each by a NAMED test, restores md5-verified:

| mutation | named failure |
| --- | --- |
| cite `golden/ssi_uid999` (a fixture that does not exist) | `…never_cites_a_golden_that_does_not_exist` |
| resurrect the `⚠ stale, \`xfail\`` row | `…xfail_claim_stays_retired` |
| gut the SSI row, leave `ADR-0108` intact | `…test_parity_report_states_the_headline_results` |
| un-name the `ssi_uid67` oracle | `…test_parity_report_states_the_headline_results` |

- **The CI guard was proven end-to-end**, not just read: with `java` hidden the 8 oracle tests skip
  and the guard's own `grep` FIRES; against the real clean run it stays SILENT (no false positive).
- `case.json` edit is **one line** — verified structurally that only `_deltas.ssi_driving_slack_golden`
  changed, every other key byte-identical.
- Numbers written into the report were read from the goldens first: `ssi_uid67` = 20 UIDs / 20 at
  zero slack; `ssi_uid145` = 108 UIDs / tiers 2-3-8-95.

## Consequences

- **No version bump, no installer rebuild.** `src/` is untouched — this is evidence, tests and CI
  only, so the wheel and the nine installers stay at v1.0.192 and remain in lockstep.
- **The parity gate can no longer weaken quietly.** If Java or a reference artifact goes missing,
  CI reddens instead of shipping a green badge over an unmeasured gate.
- **A residual ledger is a claim, not a fact.** It was written when the gap was real and never
  re-read once it closed. Both parity records are now pinned by a test that fails when either drifts.
- **Still operator-gated, and now correctly ranked** (unchanged by this ADR, but the reason to
  prioritise them is sharper now that the evidence is true): the crafted sub-day-negative-float
  Acumen run closes the Negative-Float O1 oracle gap the `.aft` has no formula for, and the
  FX-03/04 re-convert plus Fuse re-run replaces the two stale FX oracles. Those are the only
  remaining ways to raise measured fidelity against the three reference tools.
