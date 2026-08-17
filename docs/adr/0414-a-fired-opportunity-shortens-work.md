# ADR-0414 — MC-01: a fired register opportunity shortens the work, it does not delete it

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** MC-01 (audit 2026-08-16, critical) ·
**Extends:** ADR-0359 (does not overturn it) · **Ships:** `engine/sra.py`, `engine/jcl.py`

## Context

`ScheduleRisk.impact_days` is documented *"additive working days when it fires (>=0 risk,
**<0 opportunity**)"*, and opportunities are a first-class product feature with their own 5x5
Opportunity matrix and their own web surface. Both Monte-Carlo engines nonetheless collapsed a
fired opportunity through the same expression:

```python
overrides[u] = max(0, impact)  # sra.py:1701, and the twin at jcl.py:319
```

For a negative impact that is **0** — the affected activity is replaced by a zero-duration task
instead of being shortened by the opportunity.

## The measurement

20-working-day driver into a 5-working-day focus, duration noise switched off so the register is
the only variable, focus = uid 2, one certain −5 d opportunity on the driver:

| run | P50 |
| --- | --- |
| no register | 25.0 wd |
| −5 d opportunity | **5.0 wd** |
| correct if honoured | 20.0 wd |
| +5 d risk (the ADR-0359 control) | 10.0 wd |

The finish collapsed by the driver's **full 20 days**, not by the opportunity's 5 — a
**15-working-day optimistic error** in a figure an SRA quotes. The `+5 d` row is the control that
matters: it lands at 10.0 wd, confirming ADR-0359's replacement is live and correct, so the
defect is specific to the negative branch and the fix must not touch the positive one.

The JCL twin was confirmed to have the identical defect by the same probe (5.0 wd where 20.0 is
correct) — ADR-0408 made the two engines mirror each other deliberately, and ADR-0269 pins their
finish marginals byte-identical, so a one-engine fix would have broken that equivalence *and*
left the JCL page quoting the optimistic number.

## Decision

Sum the impacts on an activity first, then branch on the **sign of the total**:

```python
overrides[u] = impact if impact >= 0 else max(0, overrides[u] + impact)
```

- **Net risk (>= 0): REPLACES.** ADR-0359 verbatim, parity-locked, byte-unchanged. `0` stays on
  this branch — it is a risk by the documented `>= 0` boundary.
- **Net opportunity (< 0): SUBTRACTS** from the sampled duration, floored at 0.
- **Summing first** keeps ADR-0359's own sentence ("several risks firing on one activity replace
  with their summed impacts") literally true, and is the only reading that stays continuous
  across the sign boundary: `+3` with `−5` gives an 18 d duration, where "replace if any positive
  is present" would give 0 — the very collapse this ADR exists to remove.

Applied identically, statement-for-statement, in both engines.

## The parity leg is UNVERIFIED — stated, not buried

ADR-0359 measured replacement against SSI's own export, but **only for positive impacts**, where
replacement and "additive minus the ML" are distinguishable and replacement won (a 321-wd impact
on a 16.52-wd-ML task produced a 304.48 wd fired-alone slip — short of the impact by exactly the
ML). Replacement is meaningless for a negative value, so that measurement says nothing here.

**No committed SSI artifact settles it.** The reference exports under `00_REFERENCE_INTAKE/ssi/`
were searched: the genuine-SSI results workbooks carry the aggregate finish distribution beneath
an `Includes Risks/Opportunities? | Yes` header toggle, and never a per-risk register listing, so
no fired negative impact is observable in any of them. (The `sra-Polaris *` workbooks in the same
directory are **POLARIS's own output** and are not an oracle — a value written by our own
generator is not the reference tool's value.)

So this ADR ships the **documented-additive** semantic — the one `impact_days`' own field comment
has always specified — and marks the parity leg **UNVERIFIED**. What would settle it: an SSI run
on a known schedule with a single certain negative-impact register entry on a known activity,
exported so the affected activity's realized duration (or the fired-alone focus slip) is legible.
`tests/engine/test_register_opportunity.py` is the module to re-baseline if that export ever
arrives and disagrees — deliberately, in daylight, not silently.

## Verification (QC-1)

- **Red first, by name:** 3 of 10 tests failed against the pre-fix tree — the SRA opportunity,
  the net-negative mix, and the JCL twin. The other 7 pin behaviour the fix had to leave alone
  (both baselines, both replacement controls, the zero floor, the sign boundary), so they pass
  pre-fix by construction and their teeth come from mutation.
- **Mutation battery 7/7 caught by name** in a PYTHONPATH shadow of `src/` (origin asserted,
  pristine control green both sides, test file md5-identical after). M1/M2 each engine reverted
  to `max(0, impact)` · M3/M4 each engine made wholly additive (breaks ADR-0359) · M5 the zero
  floor removed · M6 the sign boundary loosened to `> 0` · M7 the register switched off.
- **M5 initially SURVIVED, and the test was the thing at fault.** Aimed at the *driver*, the floor
  is invisible: `compute_cpm` does **not** clamp a negative duration (measured — an override of
  −14400 min yields `early_finish = −14400`), but the successor floors at the project start
  anyway, so the focus P50 reads 5.0 wd with or without the floor. The assertion was re-pointed
  at the *focus*, where a missing floor puts the project finish 45 working days before its own
  predecessor, and it then caught M5. Recorded because it is this repo's signature defect —
  a green test that could never fail — caught in a test written *by the fix that names it*.
- **Blast radius:** 190 passed across the SRA/JCL engine and web suites with zero moved pins.
  Parity gate re-run in full (figures in the handoff's Gate-at-close).

## Consequences

- The `ScheduleRisk` docstring is corrected in the same commit: it previously opened *"whose
  schedule impact … REPLACES the affected task(s)' remaining duration"* while its own field
  comment two lines down said *"additive … <0 opportunity"*. That contradiction **is** the defect,
  written down a year before it was measured. The class now states both rules, which one is
  parity-locked, and which one is not.
- A reader who trusts the class docstring and a reader who trusts the field comment now reach the
  same answer. That is the actual repair; the arithmetic was downstream of it.
