# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a **pointer, not a status
snapshot** — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. Refresh this file whenever the queue changes — a stale kickoff
steers a fresh session at work that is already done.)

> It once went EIGHT SLICES stale (slice 14 → 22) and handed a session work finished five slices
> earlier; only the auto-injected handoff caught it. It carries no drift guard, unlike `HANDOFF.md`
> — which is exactly why it rots. Refreshing it is part of session close, not an optional tidy.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST
(auto-injected). As of last close: **v1.0.197, highest ADR 0390, SCHEMA 2.11.0**. Slice 25 merged
(#575); the monolith's page-family queue is EMPTY.

⇢ THE JOB CHANGED. Read `docs/PLAN/DEFINITION-OF-DONE-V2.md` — the operator has declared a second
Definition of Done and made **every one of its 117 items a REQUIREMENT** ("I don't want to skip
anything"). Order is ours, and it is banded by HOW WRONG THE TOOL IS, not by effort. Work the bands
in order. The old "standing queue" in this file is superseded by that document.

⇢ BAND 1 — the tool states something untrue. Do these first.
1. **THE DATA DATE (ADR-0108 / audit F-02).** REPRODUCED 2026-08-12: TP4 v4 stored finish
   2026-06-26, engine 2026-06-26 (agrees); TP4 **v5 stored 2026-07-17, engine 2026-06-26 — 21 days
   early**. `cpm.py` has ZERO references to `status_date`, so in-progress remaining work is never
   floored at the data date and a real 21-day slip reports as **0**. Two fix attempts were reverted
   for breaking Project2/5 parity + EVM1, and it is guarded by NO test. For a forensic delay tool,
   understating a slip is the worst direction to be wrong in. If it cannot be fixed this round, the
   MINIMUM is a guard pinning the discrepancy plus an on-page disclosure wherever a finish or slip
   is shown — not an ADR footnote.
2. **SRA R-2 — the tornado is mislabelled.** MEASURED (`docs/PLAN/SRA-VS-SSI-LARGE-TEST-FILE2.md`):
   our OAT values match SSI to one decimal and the ranking is identical, but we print the HOST
   TASK's name for risk drivers, so UID 7443 appears twice under one name with 304.5 d and 9.9 d.
   Our Risk-register sheet already has the right names — the information exists and is not carried.
3. **SRA R-1 — disclose the basis** (working vs calendar days) for every SRA figure.

⇢ TWO PREMISES REVERSED BY MEASUREMENT — do NOT "fix" these
* **Mean/StdDev vs SSI.** SSI's headline cells (mean 2030-03-25, stdev 226.23) are NOT reproducible
  from SSI's OWN exported 2000-sample distribution, which recomputes to mean 2030-06-08 / stdev
  156.68 calendar (111.9 working). Ours: 2030-06-11 / 151.4 calendar (108.2 working) — **3 days and
  3.4% from SSI's own data**. Percentiles off SSI's own cumulative column: P10 +11 d, P50 +3 d,
  **P80 EXACT**, P90 +4 d. That is Monte-Carlo sampling noise between two engines, not a defect.
* **Sensitivity values.** They MATCH (304.5 / 108.7 / 35.0 / 20.4 / 14.5 / 14.1 / 13.1 / 10.8 /
  9.9 / 9.3 / 8.8 / 8.5 / 7.5, same order, same UIDs). Only the LABELS are wrong (above).

⇢ THE SRA PERFORMANCE WORK — measured, with the fix already sized
Parse 1.91 s · one CPM pass 0.08 s · SRA **84.6 ms/iter @50, 86.1 ms/iter @200 — LINEAR**, so no
algorithmic blow-up · **~2.9 min @2000** · peak RSS 290 MB flat. At 86 ms/iter against an 80 ms
bare CPM pass it is doing ONE FULL 2,125-task solve per iteration. Only the focus event's ancestors
can affect it: **783 of 2,125**; **1,342 tasks (63%) are re-solved every iteration and cannot
influence the answer** → ~2.7x from sub-network restriction alone (2.9 min → ~1.1 min).
**R-3 BEFORE R-4: reproduce the CRASH first.** The operator hit two crashes then a very slow
success — consistent with a ~3-min synchronous run hitting a timeout, but that path is UNVERIFIED
and "slow" and "killed" need different fixes. Then R-6: non-blocking with progress + cancel.
Repro: `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi "SRA Large Test File2.mpp" LTF2.xml`
then `compute_sra_ssi(sch, config=SRAConfig(iterations=N, target_uid=152))`.

⇢ THE JCL FIXTURE GAP ANALYSIS — UNVERIFIED, verify before acting
An operator-supplied doc (`claude_LPX-JCL-FIXTURE-CONTRACT-GAP-ANALYSIS-AND-PLAN_v1_0.md`) claims:
the SRA field contract is exactly `SRA Risk Ranking Factors` (Number20) / `Best Case Duration`
(Duration1) / `Worst Case Duration` (Duration2), read by `_file_stored_sra_inputs`; `_ssi_setup_dict`
offers a versioned setup JSON that bypasses field mapping; `compute_jcl` refuses a duration-only run
with a cost-loaded gate; `UnifiedRisk.impact_days` is a float scalar; and **ProbabilisticBranch
(ADR-0273) + ConditionalBranch (ADR-0274) have ZERO fixture coverage**. Every one is checkable in
this repo — check each, then plan. It also asserts `is_level_of_effort=False` is hard-coded in the
MSPDI importer: CONFIRMED here, and see the LOE gap below.

⇢ VERIFIED THIS SESSION — carry forward, do not re-derive
* `settings` cut: 12 names / 437 ast lines, regions 799-1033 + 8128-8356, ZERO forced descents;
  `_e` control 29 of 32 modules (31 extracted + `state.py`); the three misses are the no-HTML ones.
* **Acumen `7. Negative Float` has NO FORMULA because it is FILTER-DRIVEN** — Formula box empty,
  mode Basic, filters `Baseline Duration > 0` AND `Total Float < 0`, Planned+InProgress /
  Normal+Milestone, Summary and **Level of Effort** unchecked. Confirmed from BOTH the operator's
  v8.11.0CU1 screens AND the committed `.aft`. Our filter structure matches; the OPEN question is
  only whether Fuse's Total Float FIELD is whole-day-grained. `tests/fixtures/mspdi/
  NEGFLOAT_SubDay_Probe.xml` (+ its guard) is built and committed for exactly one Fuse run — read
  the Detailed Report's `Total Float` cell for `NEG-SUBDAY-025`.
* **LOE GAP (new):** Fuse excludes Level of Effort; `dcma14.py` has ZERO `is_level_of_effort`
  references; the XER importer DOES populate it (`TT_LOE`); MSPDI cannot represent it; the sole XER
  fixture has zero LOE rows — so the path has never been exercised. Latent, real on P6 files.
* RTM rows are NOT all stale: **C1 is stale, but C3 is satisfied by a DIFFERENT design** (thresholds
  live on `/path` as `pathSec`/`pathTer`, render-verified, not "at upload"), and **A1 has a
  permanent Java exception** (native `.mpp` conversion shells to MPXJ). Record, do not rubber-stamp.

⇢ TRAPS PAID FOR THIS SESSION — check BY NAME
NEVER MUTATE AN INSTRUMENT A MEASUREMENT IS USING (editing `oracle_corpus.py` mid-probe changed the
label set under a running probe; the probe's label-set guard caught it). ONE WORKTREE, ONE ACTOR —
two writers in one scratchpad worktree silently reverted each other; bracket a measurement with a
cheap identity check in the SAME shell invocation. A SWEEP'S PATTERN IS PART OF ITS CLAIM — a regex
anchored on `monkeypatch.setattr` missed four sites because one test binds `mp = monkeypatch`; the
mutation battery's pre-mutation GREEN control is what caught it. A CLOSURE IS NOT CLOSED UNTIL IT
STOPS GROWING — fixed-point the BLOCKERS, not the movers. VERBATIM TEXT IS NOT VERBATIM BEHAVIOUR —
`__name__`. THE MONKEYPATCH REPOINT IS PER CALL SITE, NOT PER NAME. A `pgrep -f` waiter can match
its OWN command line and never exit — wait on a PID. Plus the standing set (instrument shown to
FAIL first · marker matches RETURN TYPE · priced table is a snapshot · `ast` col_offset is BYTES ·
population is part of a sweep's claim · `grep -c` exits 1 on zero · two ruffs on PATH, use
`python -m ruff` · bare `pytest` does not prepend CWD · `git fetch origin` before taking an ADR
number, and again before committing).

⇢ TIMING — MEASURED
Full local suite ~29 min under load (~21 idle). CI ~60 min end-to-end; `check` is a gate job and its
absence early is sequencing, not failure. `cancel-in-progress: true` — never push while you need a
run's signal. Corpus render ~40 s (1096 labels, 8 stages incl. `[aiconfig]`).

⇢ Standing rules (binding)
Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING,
VERIFY EVERYTHING · ADR-0240 model protocol · full gate before every commit · handoff rotation +
SESSION-LOG + LESSONS-LEARNED + THIS FILE in the same commit · wheel + nine installers ONCE per
shipped-code change · a number written mid-session is not a measurement (`wc` decides). Skills:
`full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`,
`session-close`.
