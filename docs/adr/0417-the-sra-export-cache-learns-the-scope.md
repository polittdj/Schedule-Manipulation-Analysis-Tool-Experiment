# ADR-0417 — SRA-EXPORT-STALE-SCOPE: the SRA reuse key omitted the session scope

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** SRA-EXPORT-STALE-SCOPE (audit
2026-08-16) · **Extends:** ADR-0360 · **Ships:** `web/app.py`

## Context

ADR-0360 made `/export/{fmt}/sra` reuse the page's Monte-Carlo result rather than re-running it
on every ⤓ EXCEL click — measured at 140 s on the committed 2,125-task schedule, which reads as
a dead button. The reuse is keyed on `_sra_reuse_key`, described in its own docstring as the run's
"full resolved-input identity", with the promise that *"a cached result can never be served
across an input edit"*.

The key listed the focus, the register, the factors, the Best/Worst pairs, the sampler, the
correlation spec and `content_hashes` — and **not the session scope**.

That matters because the SRA does not run on the raw file. `_sra_selected` resolves through
`st.analysis_for(...)` and returns **`analysis.scoped`** — the group/filter-scoped schedule. The
active filter is therefore a genuine input to the cached computation, and `content_hashes` cannot
stand in for it: that hashes the *file*, which a filter does not touch.

## The measurement

With the session's own `scope_signature()` moving from `A=1` to
`F=(('name', ['Design', 'Framing']))A=1`:

| observation | pre-fix |
| --- | --- |
| reuse key across the two scopes | **identical** |
| `/export/xlsx/sra` after the scope change | cache **hit** |
| result object served | **the same object** the unfiltered page produced (`is`) |

So the export can hand the operator a workbook computed under a scope they are no longer looking
at — the same family as MF-02 (ADR-0411): an export disagreeing with the screen.

## Decision

Add `st.scope_signature()` to the reuse key.

This is safe on the mechanism alone, without waiting for an end-to-end reproduction: a cache key
that gains a component can only ever cause a **recomputation**, never a wrong number. The cost of
being wrong in that direction is bounded (one extra run); the cost of the omission is an exported
figure that does not match the analysis.

## Scope of the verification — one leg is UNVERIFIED, and says so

**Verified (executable):** the key collision, and the stale result object being served across a
changed scope signature; the fix flips both; ADR-0360's reuse still hits when nothing changed
(the negative control that stops a "fix" from silently disabling reuse and restoring the
140-second dead button).

**UNVERIFIED:** an end-to-end reproduction in which a filter visibly moves the *exported
percentiles*. The shipped example schedule is degenerate for SRA — every percentile lands on one
date at deterministic percentile 100.0 — so it cannot show the figures diverge, and the
`/groups` query shapes tried in-session did not move the scoped population. What would settle it:
a fixture whose filtered population changes the focus distribution, exported under two scopes and
diffed. Recorded here rather than asserted, per QC-1: an unverifiable leg reported as fact is the
failure the rule exists to prevent.

## Verification (QC-1)

- **Red first, by name:** `test_a_scope_change_invalidates_the_sra_reuse_cache` failed on the
  shipped tree; the two controls passed pre-fix by construction and are there to constrain the
  fix, not to certify it.
- Assertions use **identity** (`is`), not equality: on this fixture the two runs may well produce
  equal numbers, and what must not happen is the export *skipping the computation*.
- Blast radius: 107 passed across the SRA report/grid/risks/web/Excel-template suites and the
  scope-epoch cache suite.
