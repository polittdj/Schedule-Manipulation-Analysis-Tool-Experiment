# ADR-0277 — DCMA milestone scope: Acumen-parity population for the work checks

Status: accepted (2026-07-21)

## Context

The operator ran the tool against Acumen Fuse v8.11.0 on two real production schedules (the "Large
Test File" and "Large Test File2", ~2,100 activities each, delivered as a `.mpp` + `.afw` +
Acumen-vs-Program comparison workbooks) and reported that several DCMA-14 counts differ from Acumen's
ribbon values. Investigation (converted both `.mpp` → MSPDI via the vendored MPXJ, ran
`compute_dcma14`, and **set-differenced our offender lists against Acumen's actual flagged task-ID
lists** — no theorising) established the discrepancies empirically:

| Check (File 1) | Acumen ribbon | ours (before) |
|---|---|---|
| Hard Constraints (05) | 0 | 1 |
| Negative Float (07) | 35 | 41 |
| High Float (06) | 814 | 898 |
| Logic (01) | (ribbon 8 / detail 5) | 2 |
| SS/FF (04) | (ribbon 93 / detail 73) | 101 |

The **decisive** finding: excluding zero-duration **milestones** makes our offender *set* exactly
equal Acumen's on **Hard Constraints** (1→0) and **Negative Float** (41→35), and accounts for the
milestone portion of High Float / Logic / SS-FF. This matches Acumen's documented behaviour: a
milestone is not an *activity* whose total float, logic density, or constraint is a meaningful
work-health signal, so Acumen omits milestones from those checks. The distinction is coherent:

- **Work checks** — Logic (01), SS/FF relationships (04), Hard constraints (05), High float (06),
  Negative float (07) — omit milestones.
- **Completion checks** — Missed (11), BEI (14) — KEEP milestones: a *missed milestone* is a real
  missed deliverable. Verified: excluding milestones from Missed *over*shoots Acumen (File 1
  1197→1088 vs Acumen 1115), confirming Acumen keeps them there.
- Duration (08), Leads/Lags (02/03), Resources (10), Invalid dates (09) are unaffected — milestones
  are already screened by those checks' own predicates (zero baseline duration, zero duration, etc.),
  and "Lags" matched Acumen exactly with milestones in place.

Two other discrepancy classes were root-caused but are **out of scope** here (larger changes /
unresolved): **CPLI** (we take the recomputed CPM float, ~0 → CPLI 1.0; Acumen uses the stored,
constraint-aware float — stored float reproduces File 1's 0.97 exactly, but File 2's 0.59 needs
Acumen's stored-schedule critical-path length, an engine change) and a fixed set of **~24
non-milestone tasks** Acumen omits from every check that are structurally indistinguishable in the
`.mpp` (not a resource, calendar, type, WBS, work/cost, or create-date difference; the operator
confirmed no Acumen activity filter was applied — still unexplained). The operator's ribbon-vs-detail
note (Acumen "says 93 but only shows 73") is Acumen's own display truncation, not ours; the parity
diffs above are against Acumen's authoritative ribbon count.

The prior engine included milestones in the work checks, and the golden **P2/P5** parity fixtures were
validated that way. So the change must not silently move those numbers.

## Decision

`compute_dcma14(schedule, cpm_result=None, *, exclude_milestones=False)` gains an opt-in flag. When
enabled it drops zero-duration milestones from the **work** checks only (01/04-SSFF/05/06/07),
excluding them from both the offender set AND the population denominator (the logic *topology* —
`has_pred`/`has_succ` — is still built from ALL links, so a link *to* a milestone still gives an
activity an end). `audit_schedule` forwards the flag.

**Default off.** With `exclude_milestones=False` the output is byte-identical to before, so the P2/P5
golden parity gate is untouched — verified: on P2/P5 the flag changes *nothing* even when enabled
(their milestones don't fall in the affected checks); EVM1/EVM2 change only Logic and only when the
flag is on.

**Configurable in the deployed tool** (operator's choice, 2026-07-21). `SessionState` gains
`dcma_exclude_milestones` (default False), added to `_scope_signature` **only when enabled** (so the
default epoch's cache-key shape is unchanged) — the analysis cache re-keys on toggle, so the audit
recomputes and a flip can never serve a stale audit. A checkbox on the `/analysis` DCMA panel POSTs
to `/dcma/scope` → `set_dcma_exclude_milestones`; the executive-briefing DCMA snapshot honours it too.

## Consequences

- With the option enabled, Hard Constraints and Negative Float match Acumen's ribbon **exactly** on
  the operator's files, and High Float / Logic / SS-FF move to their milestone-free values (a residual
  remains from the unexplained 24-task class — tracked separately, not milestone-related).
- Default-off keeps every existing parity/golden test green; no engine math changes for anyone who
  does not opt in.
- Not addressed here (own follow-ups): CPLI stored-float / stored-CPL; the 24-task population
  mystery; BEI (0.51 vs 0.52/0.53); the ribbon-vs-detail counting basis for Logic/SS-FF/Lags/Invalid.

## Verification

`tests/engine/metrics/test_dcma14.py`: `test_exclude_milestones_scopes_work_checks_only` (a synthetic
schedule with one normal task + one milestone per work-check — the flag drops exactly the milestone
from 05/06/07 and their denominators), `test_exclude_milestones_keeps_missed_milestones` (a missed
milestone stays counted in 11 under both scopes), `test_exclude_milestones_default_is_identical_to_prior`.
`tests/web/test_dcma_scope.py`: the toggle renders, the POST flips the session flag + scope signature
(`M=1`), the checkbox reflects state, and the `next` redirect is local-only. Full local gate green;
the real-file verification (Hard 1→0, Negative Float 41→35 on the Large Test File) was run in a
sandbox against the MPXJ-converted MSPDI (the 20 MB files are not committed).
