# ADR-0411 — MF-02: the EVM workbook exported a fabricated `0.0` where the page honestly said NOT APPLICABLE

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** MF-02 (deep-dive audit round 2,
lead-verified) · **Severity:** high (Law 2) · **Version:** v1.0.208 → **v1.0.209**
(shipped code) — wheel + nine installers rebuilt, lockstep 64/64.

## Context

`/export/{fmt}/evm` wrote each index cell as:

```python
indices[k].value if k in indices and indices[k].value is not None else ""
```

That guard **never fires for a NOT_APPLICABLE index.** `_na_index()`
(`engine/metrics/evm.py:259`) builds the NA result as
`MetricResult(metric_id, name, 0, 0, 0.0, "ratio", CheckStatus.NOT_APPLICABLE)` — the value
is **0.0, not None** — and its own docstring reads *"NA, never a fabricated 0."* The
not-applicable-ness lives in `status`; the guard interrogated `value`.

**Measured on the golden Project5 (no cost loading).** The page and the workbook told the
analyst opposite things about the same file:

- **the page** renders NA and explains: *"NOT APPLICABLE rows mean the loaded file carries
  no cost data — that is a fact about the file, not a performance figure"*;
- **the workbook** wrote `['0.47', '0.91', '19.6', '22.9', '0.0', '0.0', '0.0', '-69.0', '60.0']`
  — three fabricated zeros where the page said NA.

An analyst reading that hand-out sees **CPI 0.00** — catastrophic cost performance — where
the truth is "this schedule has no cost data". The workbook is the artefact that *leaves the
tool and gets quoted*, which makes the export the worse place to be wrong, not the safer one.
It also violates the design system's standing rule: *missing shows an em dash, never a
fabricated figure.*

## Decision

Gate the cell on the field that carries the meaning. A module-level helper,
`_export_cell(result)`, returns `""` when the result is absent, NOT_APPLICABLE, or has no
value, and the value otherwise — so the workbook now blanks exactly the cells the page
renders as NA, and genuinely computed figures are untouched.

The helper is deliberately **named and shared** rather than inlined: `web/performance.py`
already used the correct idiom (`status is NOT_APPLICABLE or value is None`) while this
call site did not, and a named helper is what stops the two from drifting apart again.

## Verification (QC-1)

- **Red first.** `test_evm_export_leaves_na_indices_blank_instead_of_writing_a_fabricated_zero`
  failed by name against the unfixed export; module **14 passed** after. The test asserts
  **both halves**: no `0.0` cell, *and* the real figures (`0.47`, `0.91`) still travel — a
  fix that blanked everything would fail it.
- **Page-vs-export divergence is the oracle.** The test reads the page's own honesty
  (`"not cost-loaded"`, `"NA"`) in the same breath as the workbook's cells, so the claim
  being pinned is "these two agree", not "this cell has this value".
- **Mutation battery 3/3 caught by the named test** (PYTHONPATH shadow, import-origin
  canary, instrument md5-identical, pristine controls green both sides): M1 the original
  value-only guard · M2 the helper ignoring NOT_APPLICABLE · M3 the helper blanking
  correctly but emitting `0.0` instead of an empty cell.
- Statics green tree-wide; installer lockstep 64/64 against the v1.0.209 wheel.

## Deliberately NOT done

- **No sweep of every `value is not None` in the tree.** The survey found this call site to
  be the offender and `performance.py` already correct; a blanket rewrite would touch guards
  whose `value is None` test is the right one. The helper exists so the next EVM-ish export
  has an obvious thing to call.
- **No change to `_na_index`'s `value=0.0`.** Making it `None` would ripple through every
  consumer and arithmetic path; the defect was the *guard*, not the sentinel.

## Note for the next reader

This is the second finding in this audit where **the page was right and something else was
wrong** (see also MF-01, where the published `help.py` text was right and the engine was
wrong). When a claim concerns a displayed figure, compare the surfaces against each other —
the disagreement localises the defect faster than either surface read alone.
