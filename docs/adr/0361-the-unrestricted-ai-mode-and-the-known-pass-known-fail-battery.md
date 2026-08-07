# ADR-0361 — The unrestricted AI mode, and the known-pass / known-fail battery

- **Status:** Accepted
- **Date:** 2026-08-06
- **Related:** ADR-0129 (the mode gate), ADR-0137/0138/0145 (the role-aware figure gates that
  stay untouched in the other modes), Law 1 (unmoved), the TP1–TP4 battery this extends

## Half one — Ask-the-AI: unrestricted (operator directive)

A fourth opt-in answer mode past strict/annotate/interpretive. The model is explicitly
INVITED to calculate new figures and interpret without restraint; its text returns verbatim —
no figure, identifier, or unit gate — and it additionally receives a bounded per-activity
data table (UID/Name/WBS/durations/%complete/dates/float/critical/constraint/resources, first
400 rows, truncation disclosed IN the block) as raw material for those calculations, on the
single-file ask, the all-files ask, and the cross-check second model alike.

**What does not move: Law 1.** The backend is the same loopback-validated construction every
mode uses; the Null backend still answers nothing (pinned); the standing "AI can err — verify
against the citations" disclaimer rides every answer, and the AI Settings picker states the
trade plainly. Strict/annotate/interpretive are byte-untouched.

## Half two — the known-pass / known-fail battery (operator directive)

`tests/test_projects/test_pass_fail_battery.py`: a hand-built CLEAN 25-activity program that
every populated DCMA check PASSES on (with real populations — the one terminal open end rides
inside DCMA01's 5% tolerance exactly as real programs do), and per check a seeded twin
carrying one known defect class the check MUST flag. Each seed declares its expected
collateral flips and the battery asserts **no undeclared check moves** — an over-broad seeder
and an over-eager check both fail loudly. The same pair discipline covers the float-band
split, completion performance, and the manipulation detector (an honest re-status raises NO
findings; a 40% driving-path duration cut does). Every GET page must render 200 on the clean
corpus, the all-14-defects corpus, and the TP4 five-version family.

**Building it was itself a measurement.** Nine seed assumptions died on contact and each
correction encodes a real property of the checks: DCMA08 flags on the BASELINE duration; a
late-vs-baseline seed must not cross the data date (that is DCMA09's defect); an orphaned
task legitimately trips high-float AND invalid-forecast (declared collateral, not noise); and
the critical-path test is only defeated by a mid-chain MFO pinning a task's own finish — a
far-out pin merely empties the target set to NA, and pure logic always propagates the probe.

**Coverage stated plainly:** DCMA01–14 (all fourteen), float bands, completion performance,
manipulation, page renders ×3 corpora. Queued on the same framework: cei, hmi, fei/bri, evm,
schedule_quality, forecast, and the SRA readiness gate.
