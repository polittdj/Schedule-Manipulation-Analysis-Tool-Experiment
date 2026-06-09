# ADR-0015: M10 independent DCMA audit + risk/opportunity/concern recommendations

- **Status:** Accepted
- **Date:** 2026-06-08 (session A12 — Phase 2 build, milestone M10, continuous A7 sitting)
- **Relates to:** §6.E (independent audits + recommendations, cited), `BUILD-PLAN.md M10`, RTM E1/E2
- **Builds on:** ADR-0012 (DCMA-14 engine), ADR-0013 (§C/§E metrics), ADR-0014 (parity gate)

## Context
§6.E requires, per schedule: an **independent DCMA-compliance audit with suggested
improvements**, and a **risks / opportunities / concerns** set, each with a course of
action and **citations (≥ file + UniqueID + task name)**. M7–M9 produced the numbers;
M10 turns them into an analyst-facing, fully-cited report layer without new parity goldens.

## Decision
1. **`engine/dcma_audit.py`** — `audit_schedule(schedule)` wraps `compute_dcma14` into a
   `ScheduleAudit` of 16 `AuditCheck` rows (the 14 checks, with DCMA-04 split into FS /
   SS-FF / SF to mirror the Acumen ribbon). Each row carries pass/fail vs threshold, the
   **cited offending activities** (`Citation` = file + UID + task name), and a static,
   plain-language **suggested improvement** keyed by check id. Passing/NA rows read a
   fixed note. `Citation` is the shared provenance type (`__str__` → "Name (UID n, file)").
2. **`engine/recommendations.py`** — `recommend(current, prior=None, *, target_uid=None)`
   synthesizes a `Finding` set (Category RISK/OPPORTUNITY/CONCERN × Severity) from the
   deterministic signals: failed DCMA checks (high severity for negative-float / missed /
   CPT / CPLI / BEI), §C late/not-completed compliance, and — when a `prior` is supplied —
   the §E change metrics + Net Finish Impact (slip = high concern; finish slips, float
   erosion, no-longer-critical = a forensic watch-list whose deep detection is M11). A
   `target_uid` adds the driving-path **opportunity** (focus recovery on the zero-slack
   chain). Findings are ordered most-severe first.
3. **Every finding is cited (§6 — hard rule).** Per-activity metrics cite their offenders;
   the project-level **BEI** is enriched in `dcma14.py` to carry its baselined-due-but-
   -unfinished activities as offenders (count/value unchanged — the parity gate stays
   green); the **Net Finish Impact** finding cites the activities whose early finish equals
   the network finish (the finish-controlling chain). No finding ships uncited; a test
   asserts `all(f.citations for f in findings)`.
4. **Rule-based, deterministic, offline.** This layer is pure Python over the engine — no
   AI, no network. M12's local-AI narrative only *rephrases* these already-cited findings
   (it never invents facts), and M11's manipulation-trend detector deepens the §E
   watch-list signals; both consume `Finding`/`AuditCheck` as their input contract.

## Consequences
- RTM **E1 → ✔** (cited DCMA audit + improvements) and **E2 → ✔** (cited risk/opportunity/
  concern findings with courses of action). §6.E is met structurally; the AI narrative
  (§6.D) layers on at M12.
- `audit_schedule` / `recommend` are the data source for the M13 dashboard's audit and
  recommendations panels and the M17 final report; `Finding`/`Citation` are stable,
  serialisable records.
- dcma_audit 100% / recommendations 98% line+branch cov; full suite 374 passing; parity
  gate green; ruff/mypy(strict)/bandit clean.
