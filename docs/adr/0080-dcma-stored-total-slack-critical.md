# ADR-0080 — DCMA float metrics: consume MS Project's stored Total Slack / Critical (Acumen fidelity)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0010, ADR-0012, ADR-0079

## Context

Loading the operator's progressed real schedule (the "Large Test File") into Acumen Fuse and into
the tool gave wildly different float-based numbers:

| Metric | Tool (before) | Acumen | 
|---|---|---|
| Critical | 2 | **33** |
| Negative Float | 0 | **31** |

(Missing Logic 22, Logic Density 3.14, Hard Constraints 1, Merge Hotspot 156 already matched.)

**Root cause.** Acumen reads MS Project's **stored, progress-aware** `Critical` flag and
`TotalSlack`. The engine, by design (ADR-0010), *recomputes* pure-logic CPM float for independence
and auditability and does **not** consume the source tool's stored values. On a clean schedule the
two agree (which is why the goldens passed parity); on a heavily-progressed schedule — actuals, a
data date, deadlines, out-of-sequence work — MS Project's stored slack goes negative on paths where
the engine's independent recompute stays positive, so the tool reported 2 critical / 0 negative
where the source (and Acumen) say 33 / 31.

That independence is correct for the forensic *driving-path* analysis (the whole point is to recheck
the network), but the **DCMA-14 / Schedule-Quality audit is meant to report the schedule as the
source tool computed it** — which is exactly what Acumen does. So for those float-based counts the
faithful answer is the stored value.

## Decision

Capture and prefer the source tool's stored values for the float-based metrics, when the file
provides them:

1. **Model** (`model/task.py`): two new optional fields, `stored_total_float_minutes: int | None`
   and `stored_is_critical: bool | None` (default `None` = the source did not provide it).
2. **MSPDI importer** (`importers/mspdi.py`): read `Task/TotalSlack` and `Task/Critical`. MS Project
   stores slack in **tenths of a minute** — verified against the goldens, where `stored ÷ 10` equals
   the engine's recomputed CPM float on clean tasks — so it is converted to whole working minutes.
3. **Effective-value helpers** (`metrics/_common.py`): `effective_total_float(task, recomputed)`
   returns the stored slack when present, else the recomputed float; `is_effective_critical(task,
   recomputed)` returns the stored Critical flag when present, else pure-logic critical excluding
   completed work (ADR-0010 §3).
4. **Metrics**: `schedule_quality` **Critical** and **Negative Float**, **DCMA-07** (Negative Float,
   which also feeds the Ribbon), and the Ribbon's **Critical** now score through those helpers.
   **High Float (DCMA-06)** is deliberately left on the recomputed float — it is a separately pinned
   documented residual (ADR-0012), not part of this reconciliation.

## Scope / safety — parity preserved

Verified parity-safe on the committed golden fixtures, which **carry** stored values: their stored
`Critical=1` count is **41 / 37** and stored `TotalSlack < 0` is **0 / 0** — *exactly* the pinned
Acumen golden values, so the gate is unmoved (the goldens now reach those numbers via the stored
basis instead of the coincidentally-equal recompute). The synthesized **TP1–TP4** Fuse-calibrated
fixtures carry **no** stored `Critical`/`TotalSlack`, so they fall back to the recompute and their
pinned Ribbon values (incl. TP3 critical 5 / negative 3 / leads 1) are unchanged. The operator's real
progressed file carries stored values and now matches Acumen (33 / 31).

`pytest -m parity` **10/10**. New tests: the effective-float helpers prefer stored over recomputed
(and exclude completed work on fallback); a stored negative slack flips Negative Float where the
recompute would not; the MSPDI importer reads `TotalSlack` (÷10) + `Critical`, absent → `None`. Full
gate green; ruff/format/mypy/bandit clean.

## Follow-up

**Number of Lags (5 vs 8) and Number of Leads (0 vs 1)** also diverge on the operator's file, but
those are **not** stored-value issues — they are link/lag *detection* differences (Acumen counts
activities, including milestones and completed work; the tool currently restricts to incomplete
successors). That fix is a definitional change to link counting with its own parity exposure and is
tracked as the next step (it needs validation against the goldens' pinned Lag/Lead counts, and ideally
confirmation of Acumen's exact population). High Float (DCMA-06) remains the ADR-0012 residual.
