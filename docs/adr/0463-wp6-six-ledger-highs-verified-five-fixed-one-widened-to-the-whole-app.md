# ADR-0463 — WP6: the six ledger highs verified by execution — CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02 all CONFIRMED and fixed, and REC-02 was the whole app, not the recommender

- **Status:** Accepted — 2026-09-04 (POLARIS² audit campaign, WP6; SOLO lead, fix-as-verified)
- **Version:** 1.0.237
- **Extends:** ADR-0309 (the progress-override floor), ADR-0118/0251 (SSI driving slack), ADR-0308 (finished work cannot be delayed by a future risk), ADR-0269 (JCL cost co-sampling), ADR-0080/0150/0151 (the effective critical basis; the Fuse §E re-pin), ADR-0128 (inactive tasks are out of the network), ADR-0393 (QC-1/QC-2)
- **Ledger:** `docs/STATE/AUDIT-2026-08-27.md` (WP6 row) · row source `docs/STATE/AUDIT-2026-08-16.md` (REPORTED — round 2/3 finder claims)
- **Shipped:** `engine/cpm.py` · `engine/driving_slack.py` · `engine/sra.py` · `engine/jcl.py` · `engine/metrics/_common.py` · `engine/metrics/change_metrics.py` · `engine/manipulation.py` · `engine/recommendations.py` · `web/state.py` · `web/app.py` (one JCL disclosure row + payload key) · six NEW engine test modules · `tests/web/test_inactive_target_scope.py` (NEW) · `tests/parity/test_fuse_export_parity.py` (one pin DELIBERATELY re-baselined) · `tests/engine/test_jcl_joint_statement_closure.py` (one fixture re-baselined with its reason)

## Context

Six rows had sat REPORTED since 2026-08-16 — finder claims from a round this audit has already
caught wrong in both directions. Each was re-derived from the finder's cited line **as it read on
2026-08-16** (`git show 1b833c6a:…`; three weeks of edits had moved every line number), then probed
with an executable check built to refute it, on the goldens where a Law-2 oracle existed. Every one
of the six survived its refutation. One of them was far larger than filed.

| row | finder claim (08-16) | what execution showed | verdict |
| --- | --- | --- | --- |
| **CPM-01** (*critical*, `cpm.py:1316`) "progress-override floor vs the project axis" | line 1316 was the backward pass's `total = late_start - early_start`. The ADR-0309 resume floor moves EF, but LS was derived as `LF - stored duration`, so the floor's gap never reached the float. **Golden EVM2, UID 20** (Resume > Stop, gap 10 wd): engine TF **10.0 wd / non-critical**, `LF - EF` **0.0**, MS Project's stored Critical flag **Yes**, the engine's own EF already the stored finish to the day (2012-09-13). Project2 (UIDs 12/17/29) and Project5 (34/35) carry the reschedule with a ZERO gap — untouched. The execution-calendar branch already measured slack from the floored finish and was correct. | **CONFIRMED-FIXED** |
| **CPM-02** (*high*, `driving_slack.py:314`) "`endpoint()` measures a link's two ends on different rulers when one end is dated" | line 314 was exactly the `date_basis` fallback. A stored date is measured on the SUCCESSOR's calendar; an undated end returned a PROJECT-calendar offset. Synthetic: a 5-day undated predecessor of a 24/7 successor read **3,840 min (8.00 d) of slack, OFF the driving path**; dated at exactly its own CPM dates it read **0, ON** it. Reach: XER / hand-written MSPDI can leave `start`/`finish` absent; every MS Project export is dated, and the SSI 783/783 parity file is fully dated (byte-identical). | **CONFIRMED-FIXED** |
| **MC-02** (*high*) "ADR-0308's rule missing from a third code path" | every loop over `risk.affected` enumerated: `compute_sra_ssi` (guarded), `compute_jcl` (guarded), `oat_sensitivity` (guarded), and the legacy whole-project **`compute_sra`** — LIVE on /sra's run, fed the unified register through `_risk_events` as point multipliers — which multiplied a COMPLETED activity's point-mass duration. A certain ×2 on a 100 %-complete 10-day driver: P50 **8,148 → 12,948** min, P90 8,286 → 13,086 (+10 wd on finished work); the same risk on open work moved P50 to 10,544 (the control). | **CONFIRMED-FIXED** |
| **MC-03** (*high*, `jcl.py:284`) "a missing `actual_cost` on an in-progress task treated as 0 spent" | still line 284: `spent = actual_cost if not None else 0.0`. The performed share of the budget vanished from the EAC: a 1,000 task at 50 % with NO actual contributed **680** vs **1,180** with the actual recorded at budget; **99 % → 100 %** complete jumped the EAC by **990**, because the completed branch had always assumed the budget when actuals were absent. The EVM goldens carry actuals on every in-progress costed task (0 assumed); the TP corpus is not cost-loaded — no golden moved. | **CONFIRMED-FIXED** |
| **MAN-01** (*high*) "`_critical_incomplete` scores on pure-logic `is_critical` instead of `is_effective_critical`" | two private twins (`change_metrics`, `manipulation`) while every other Critical figure goes through `_common.is_effective_critical` (the stored, progress-aware flag — Acumen's basis, ADR-0080/0150; the Bible's *Critical* metric is type `ActivityAttribute`). Golden P2→P5 on the effective basis: SN03 **1 [131]** unchanged; SN04 **34** unchanged and the membership **UID-exact with the Fuse export** — the documented 96↔99 swap (`test_fuse_export_parity.py`) disappears; the trend count 41 / 4 unchanged (membership 99,143 ↔ 96,144 · 143 ↔ 144); manipulation findings P2→P5 **5 = 5, identical**. A file without stored flags is unchanged. | **CONFIRMED-FIXED** (a measured parity IMPROVEMENT, re-baselined through the pin's own path) |
| **REC-02** (*high*) "`recommend(schedule, target_uid=<inactive>)` calls `compute_driving_slack` unguarded" | true (`KeyError(5)` on `commercial_construction.xml`) — and the recommender was the small half. `SessionState.scope()` truncated to the target whenever a NON-SUMMARY task carried its UID, inactive or not, and `subschedule_to_target` raises for a UID outside the network (ADR-0128). POST /target accepted the inactive UID (303) and the next GET was a 500: a sweep of every parameterless GET route read **51 of 63 → 5xx** (`/` included) with the inactive target, **0** with an absent UID (the "not in this version" branch), **0** in the control. | **CONFIRMED-FIXED, widened to the whole app** |

## Decisions

1. **CPM-01 — total float is the smaller of start slack and finish slack on the project axis**:
   `total = min(LS - ES, LF - EF)`. Byte-identical for a contiguous task (`EF == ES + duration`);
   the two differ only when the resume floor moved the finish, and then the finish slack is the
   truth — the start can slip to LS without moving the floored finish, but the finish drives what
   follows. `late_start` stays `LF - duration` (the start really can slip that far; the predecessor's
   float — measured 9 wd on the synthetic chain — is untouched). The module's rulebook docstring
   carries the rule under ADR-0309's paragraph. Blast radius: only floored tasks; on the goldens only
   EVM2 UID 20, which MS Project flags Critical.
2. **CPM-02 — the fallback endpoint is re-measured on the successor's calendar** when that
   calendar's working pattern materially differs from the project's (`_working_pattern_key`):
   `_stored_offset(ps, offset_to_datetime(ps, off, project_cal), cal)`. A same-pattern calendar keeps
   the project-axis integer path (pinned), a fully dated file never takes the fallback, and
   `ignore_leveling_delay` still measures every endpoint on the project axis (ADR-0251) — the SSI
   parity gate is byte-identical.
3. **MC-02 — the legacy model gets ADR-0308's guard**: `done = {completed uids}`; a fired multiplier
   is applied only to open work. A risk whose every affected activity is complete now reports
   `hits == iterations` and `mean_delta_days == 0.0` in its `RiskDriver` — inert, and visibly so.
4. **MC-03 — an absent actual on open work is the performed share of the budget**
   (`budgeted_cost · pc/100`), the same on-budget assumption the completed branch documents, so the
   EAC is continuous at 100 %; a RECORDED actual (a zero included) is never overridden. The count of
   open tasks the assumption touched is `JCLResult.actuals_assumed_count`, on the /jcl summary
   ("Open tasks with no recorded actual (spent assumed at budget)") and in the JSON provenance.
5. **MAN-01 — one shared helper**, `_common.effective_critical_incomplete(schedule, cpm)`; both
   twins delegate. `test_no_longer_critical_count_matches_fuse_and_the_one_membership_swap_is_exact`
   becomes `test_no_longer_critical_membership_is_uid_exact_with_fuse` — the ratchet is the EMPTY
   symmetric difference, the source-data premise (96 stored-critical / CPM not; 99 the reverse) is
   still pinned so the ratchet keeps its meaning, and the docstring records the re-baseline date.
6. **REC-02 — the target's presence test is the network's membership** (non-summary AND active) in
   `SessionState.scope()`, so an inactive target keeps the full (filtered) population exactly like an
   absent one; `_driving_path_findings` treats an inactive target like a summary (nothing to trace).
   `set_target` still accepts any UID — a target set on one version legitimately goes inactive in a
   later one, and the page-level behaviour ("not in this version's network") is the honest one.

## Verification (QC-1)

- **Red first, on a pristine worktree of HEAD on `PYTHONPATH`** (never the working tree): the seven
  new modules + the re-baselined parity pin — **16 failed / 8 passed**, each failure the defect its
  module names (the 8 passes are the guards that hold on both trees: the predecessor's start slack,
  the same-pattern byte-identity, the control risk on open work, a recorded actual never overridden,
  a completed flagged task never counted, an absent UID, the EVM goldens' 0 assumed).
- **Green:** the seven modules 23/23; the six pinning goldens' engine + parity suites **1,137 passed /
  1 failed** on the first full run — the one failure `test_default_cost_target_compares_unrounded_and_
  displays_rounded`, whose fixture (999 budget, 33.4 %, NO actual) lost its 665.334 rounding edge once
  the performed share counted (EAC exactly 999). Re-baselined **through its own path**: the actual is
  RECORDED as `0.0` — MC-03's none-vs-zero distinction — so its 665.334 and its purpose survive; the
  three JCL modules 51 green after.
- **Mutation, on scratch copies of the FINAL code (never `git checkout --`), each red BY NAME:**
  the `min` reverted → 3 CPM-01 tests · the re-measure removed → the invariant test · the legacy guard
  dropped → the completed-driver test · `0.0` restored → 3 MC-03 tests · the helper back to pure
  logic → 3 basis tests + the parity ratchet · the engine guard dropped → the inactive-target test ·
  `is_active` dropped from `scope()` → both web pins.
- **Oracles:** MS Project's own stored Critical flag on EVM2 UID 20 (CPM-01); the invariant "dating a
  task at its CPM dates cannot change its slack" (CPM-02); the no-register run (MC-02); continuity at
  100 % and the completed branch's documented assumption (MC-03); the Fuse export's UID lists
  (MAN-01); the route sweep against a no-target control (REC-02).

## Deliberately NOT done (measured, left alone)

- `engine/metrics/evm.py::compute_evm_indices` sums `actual_cost or 0.0` into ACWP — the same
  none-vs-zero class on a mixed population. It is an EVM parity family with an Acumen oracle
  (EVM1/EVM2 carry every actual, so parity is unaffected today); it gets its own row, never a blind
  edit alongside MC-03.
- `path_evolution.CriticalSnapshot.critical` (the /evolution per-version critical list) is a pure-logic
  set by construction of that forensic page; not a MAN-01 twin, not touched.
- `late_start` for a floored task stays `LF - duration` (decision 1): the start slack is real.
- The RC-02 never-adverse routes stay a WP7 queue; this WP paid for the six highs.

## Consequences

- Six ledger rows move from REPORTED to CONFIRMED-FIXED with their measurements; the Fuse §E
  membership is UID-exact for the first time; a floored finish is critical when MS Project says so; the
  legacy SRA cannot delay finished work; the JCL's EAC no longer drops performed work; an inactive
  target can no longer 500 the app.
- `JCLResult` gains `actuals_assumed_count` (default 0); `/api/sra/jcl` gains `provenance.actuals_assumed`.
- Version 1.0.236 → **1.0.237** with ADR-0464; wheel + nine installers rebuilt in lockstep as the
  LAST step.
