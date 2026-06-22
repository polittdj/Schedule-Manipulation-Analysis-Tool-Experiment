# ADR-0111 — P2→P5 cross-version Acumen reference; CEI/HMI cross-version deferred

Status: accepted (2026-06-22)

## Context

Build-order step 2 was "CEI/HMI cross-version validation against the Large-Test-File (LTF→LTF2)
Metric History Report." Inventorying the re-attached corpus showed the inputs for *that specific*
run are not present this session, but a richer cross-version reference is: the operator's
`2345 - Metric History Report.xlsx` scores the manipulation series as **four consecutive snapshots**
of one schedule — `Project2` (2026-05-24) → `Project3` (06-30) → `Project4` (07-29) →
`Project5_TAMPERED` (08-27) — and the source `.mpp` for all four are on disk.

Two facts decided the scope:

1. **CEI is N/A on every chain with source schedules.** Acumen reports `Critical CEI` as **N/A**
   for every snapshot of the 2345 (P2→P5), TP, and TP4 chains — they carry no consecutive-period
   `Previous*` linkage, so Acumen itself does not compute CEI on them. The only non-N/A CEI
   reference on hand is `L12` (Large-Test-File v1→v2, Critical CEI 0.19), whose source `.mpp` is
   **not** in the intake this session.
2. **No Metric-History report carries HMI rows at all.** HMI cannot be referenced from this corpus.

So a CEI/HMI cross-version reference test is **input-blocked**; what the corpus fully supports is a
per-version DCMA / schedule-quality / BEI validation across the P2→P5 chain — which newly covers
**Project3 and Project4** (Project2/Project5 were already in the parity goldens).

## Decision

Add **`tests/engine/test_chain_acumen_reference.py`** — load the four source `.mpp` (converted fresh
via the vendored MPXJ) and assert the tool reproduces Acumen's `2345` per-version numbers across the
chain. Like `test_mpp_mpxj` and the `.aft` audit, it **skips** when the (git-ignored, non-CUI)
schedules or a JVM are absent (CI), and runs on an operator machine with the intake. **No committed
goldens** (MPXJ output is not byte-deterministic and the files are large; runtime conversion keeps
the PR lean and fully decoupled from the Project5 golden refresh — step 3). NOT marked `parity` — a
forward-looking Acumen reference harness (modelled on `test_evm_acumen_reference.py`), currently
all-exact.

## Result — exact across the chain

| Metric (P2 / P3 / P4 / P5) | Acumen `2345` | Tool |
|---|---|---|
| BEI - Value Tasks | 0.74 / 0.67 / 0.58 / 0.59 | exact |
| BEI - Complete Tasks | 20 / 24 / 25 / 27 | exact |
| Critical Path (T&M) = Zero Float | 41 / 40 / 37 / 4 | exact |
| High Float (44d) | 44 / 42 / 41 / 44 | exact |
| Hard Constraints | 0 / 0 / 0 / 1 | exact |
| Negative Float | 0 / 0 / 0 / 0 | exact |
| Missing Logic (incomplete) | 4 / 4 / 4 / 5 | exact (`DCMA01`) |
| Status date | exact (serials 46166 / 46203 / 46232 / 46261) | exact |

P5 High Float lands at an exact **44** on the authoritative file — confirming the stored-Total-Slack
fix (ADR-0109 / #204) and the ADR-0109 finding that the committed `project2_5/Project5` golden is
stale (step 3 refreshes it). As with the `.aft` audit, Acumen's report "Missing Logic" is the
incomplete-scoped count (`DCMA01`), not the full open-ends count.

## Consequences

- The full P2→P5 manipulation chain is now validated against Acumen, exact on every cross-version
  metric the corpus carries; Project3 / Project4 are covered for the first time.
- **CEI/HMI cross-version remains open**, awaiting the Large-Test-File source `.mpp` (the only non-N/A
  CEI reference). Recorded in `docs/STATE/HANDOFF.md` as a confirmed-missing input.
- No coupling to the Project5 golden refresh (step 3), which proceeds independently.
