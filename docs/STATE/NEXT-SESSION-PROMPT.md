Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here disagrees with HANDOFF, HANDOFF wins. Refresh this file whenever the queue changes — a stale kickoff steers a fresh session at work that is already done.)

It once went EIGHT SLICES stale (slice 14 → 22) and handed a session work finished five slices earlier; only the auto-injected handoff caught it. It carries no drift guard, unlike `HANDOFF.md` — which is exactly why it rots. Refreshing it is part of session close, not an optional tidy. **It was wrong again this session**: it asserted the data-date gap was "guarded by NO test" when `tests/engine/test_data_date_finish_gap.py` had guarded it since #536, and it named the data date as the mechanism when the mechanism was an ignored `ActualStart`. Do not trust its diagnoses — re-derive from measurement.

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). Read `docs/STATE/HANDOFF.md` FIRST (auto-injected). As of last close: v1.0.198, highest ADR 0391, SCHEMA 2.11.0. The monolith's page-family queue is EMPTY.

⇢ THE JOB. `docs/PLAN/DEFINITION-OF-DONE-V2.md` — 117 items, every one a REQUIREMENT ("I don't want to skip anything"). Order is ours, banded by HOW WRONG THE TOOL IS. **BAND 1 item 001 is CLOSED** (ADR-0391). Band 1's remaining two are the SRA labelling items below.

⇢ WHAT ADR-0391 SETTLED — do not re-open, do not re-derive

* **The mechanism was never the data date.** A recorded `ActualStart` was ignored, so a task that started 91 days late was re-packed at its logic start and dragged the successor chain back. `_actual_start_bounds` now floors `es = max(logic_es, offset(actual_start))`. A stored-date READ (third of the family with ADR-0034/0309), not the data-date INFERENCE reverted twice. Needs no `Stop`/`Resume`.
* **Fuse agreement 4/5 → 5/5 on TP4; TP1's −1d closed too** (09-16 → 09-17). Both now ASSERTED in `test_fuse_reference.py`. **No project finish moved on any genuine MSPDI golden.** Engine-vs-MSP `EarlyFinish` disagreements 132 → 117, zero engine-later.
* **TP1/TP3/TP4 are GENERATOR OUTPUT, not MS Project exports** — zero `EarlyStart`/`EarlyFinish`/`TotalSlack`/`Critical`/`Stop`/`Resume`. Guarded by `tests/engine/test_fixture_provenance.py`. **Never validate an engine rule against a battery fixture's own `<Finish>`** — the generator pins started tasks at their actual dates, so it will agree with itself. Use `docs/FUSE-VALIDATION.md` (the operator's Acumen Fuse run) or the four real exports.
* **Regenerating TP4 with `Stop`/`Resume` would change NO number** — ADR-0309 fires only on `resume > stop`, and MSP writes `resume == stop` for contiguous progress. Realism only; not a prerequisite for anything.

⇢ NEAREST REAL WORK — measured, located, ready

1. **EVM2's sub-day / segmented-calendar divergence (DoD 050).** ADR-0108 blamed the data date; **all six divergent EVM2 activities are 0% complete with NO actuals**. The calendar carries a lunch break (08:00–12:00, 13:00–17:00) and the chain diverges at **UID 23, duration `PT12H`** — engine lands 12:00, MSP 17:00, half-day propagates to every successor including the finish. **UNEXPLAINED and worth starting there: why does MSP span a 12-hour duration across three days (09-19 → 09-21)?** Answer that and the residual likely falls out.
2. **Completed-task actual FINISH anchoring** — the deliberate remaining half of ADR-0391, named in `cpm.py`'s docstring. A completed activity's finish is still `start + duration`, so one that ran long still computes a finish that differs from the record.
3. **DoD 117 — a shallow-clone guard in `build_installers.py`.** No longer theoretical: the trap FIRED this session (pin resolved to `79865bc` instead of `42d92dc`) and only a diff against `origin/main`'s installers caught it. `git fetch --unshallow` before any build, and add the guard.
4. **SRA R-2 (Band 1)** — the tornado prints the HOST TASK's name for risk drivers, so UID 7443 appears twice under one name with 304.5 d and 9.9 d. The Risk-register sheet already has the right names; the information exists and is not carried.
5. **SRA R-1 (Band 1)** — disclose working-vs-calendar-day basis for every SRA figure.
6. TP3's −5d Fuse gap · SRA R-3 (reproduce the CRASH before optimising) → R-4 (sub-network restriction, ~2.7x) → R-6 (non-blocking + progress/cancel) · `/groups` Activities (ADR-0343) · installers vs known-good constraints · doc-drift sweep · Phase 6 docs.

⇢ TWO PREMISES REVERSED BY MEASUREMENT — do NOT "fix" these

* Mean/StdDev vs SSI. SSI's headline cells are NOT reproducible from SSI's OWN exported 2000-sample distribution. Ours sits 3 days / 3.4% from SSI's own data; P80 EXACT. Monte-Carlo sampling noise, not a defect.
* SRA sensitivity VALUES match SSI exactly (same order, same UIDs). Only the LABELS are wrong (R-2 above).

⇢ TRAPS PAID FOR — check BY NAME
A FIXTURE GENERATED BY A RULE CANNOT VALIDATE THAT RULE (cost the first cut of ADR-0391). THE CORROBORATING ORACLE MAY ALREADY BE IN THE REPO — grep before concluding a claim is unsupported (Fuse had the answer for months). AN ADR'S OBSERVATION CAN BE RIGHT AND ITS DIAGNOSIS WRONG — re-derive a carried finding before implementing against its description. A NEW DISCLOSURE NEEDS ITS OWN CHANNEL when the existing one carries a JUDGEMENT (`date_driven` accuses; a recorded actual does not). `| head -N` CAN SIGPIPE-KILL A BUILD MID-WAY and leave a partially-regenerated artifact set that looks done. THE MPXJ PIN DRIFTS IN A SHALLOW CLONE (fired). Plus the standing set (instrument shown to FAIL first · marker matches RETURN TYPE · never MEASURE a tree a battery is mutating · never MUTATE an instrument a measurement is using · monkeypatch repoint is per CALL SITE · verbatim text is not verbatim behaviour · `grep -c` exits 1 on zero · two ruffs on PATH, use `python -m ruff` · bare `pytest` does not prepend CWD · `git fetch origin` before taking an ADR number, and again before committing).

⇢ TIMING — MEASURED
Full local suite ~29 min under load (~21 idle); **`pytest -m parity` alone exceeds 900 s** — give it room or it dies to your own `timeout`. CI ~60 min end-to-end; `cancel-in-progress: true` — never push while you need a run's signal. The container starts with **no deps installed**: `python -m pip install -e ".[dev]"` plus `build` before anything runs.

⇢ Standing rules (binding)
Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test) · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING · ADR-0240 model protocol · full gate before every commit · handoff rotation + SESSION-LOG + LESSONS-LEARNED + THIS FILE in the same commit · wheel + nine installers ONCE per shipped-code change · a number written mid-session is not a measurement (`wc` decides). Skills: `full-gate`, `prove-able-to-fail`, `metric-parity`, `ui-change`, `cui-guard`, `render-verify`, `session-close`.
