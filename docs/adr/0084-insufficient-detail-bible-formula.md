# ADR-0084 — Insufficient Detail™: adopt the Bible formula (current duration / project calendar span)

Date: 2026-06-18 · Status: accepted · Supersedes the ADR-0012 Insufficient Detail decode

## Context

`Insufficient Detail™` was the one Schedule-Quality metric still diverging from Acumen on the operator's
Large Test File (tool **41** vs Acumen **43**). The tool used an empirically-decoded heuristic —
*baseline* duration > 10% of the project's *working*-day duration. The authoritative library
(`NASA_Metrics_Complete.aft`, declared the Bible by the operator) defines it as:

```
SUM((OriginalDuration / (ProjectFinish - ProjectStart) > 0.1) * 1)
```

From Acumen's offender rows on the Large File, **OriginalDuration is the activity's current duration in
working days** and **(ProjectFinish − ProjectStart) is the project's CALENDAR span in days** (the date
subtraction — Acumen does not convert the denominator to working time). That mixed-unit ratio reproduces
Acumen's **43** exactly.

The wrinkle, now resolved: the Bible (current-duration) formula reproduces the Large File's 43, but the
operator's *earlier* TP3 Fuse capture (8, 2026-06-12) matched only with *baseline* duration (current
gives 9). To settle it, **the operator re-ran TP3 through *this* library in Acumen and got 9** — exactly
the Bible formula's value. So there is no contradiction: the earlier 8 came from an older library, and
under the authoritative library both the Large File (43) and TP3 (9) confirm the current-duration formula.

## Decision

`compute_schedule_quality` computes Insufficient Detail™ as the Bible formula: an activity's **current
(Original) duration in working days** divided by the project's **calendar span**
(`max(activity finish) − project_start`, in days) **> 10%**. Current duration (not baseline); 0-duration
milestones never qualify.

## Validation / re-pins (operator-approved)

* **Large Test File: 43 exact** (was 41) — matches Acumen's report.
* **Project2: 1** (unchanged). **Project5: 1 → 0.** **TP3: 8 → 9** (offenders now
  `13,14,23,24,25,26,27,29,31`). The older captures (Project5 decode; TP3 2026-06-12 Fuse run) predate
  this library and are superseded by it.

`case.json`, the TP3 battery test, and the two synthetic unit tests are re-pinned to the Bible formula
(the synthetic tests now exercise current-duration / calendar-span, replacing the old baseline/working-day
decode). `pytest -m parity` **10/10** (Project2 unchanged at 1; Project5 0). `docs/METRIC-DICTIONARY.md`
regenerated; `docs/FUSE-VALIDATION.md` updated. Full gate green; ruff/format/mypy/bandit clean.

## Audit status

With this, the tool matches Acumen **exactly on every metric for which the operator supplied authoritative
output** on the Large Test File: Schedule-Quality ribbon **9/9** (ADR-0079/0080/0081/0084) and Baseline
Compliance **10/10** (ADR-0083). Half-Step-Delay is all-zero for a single snapshot. The remaining library
families (BEI/HMI/CEI, critical-path, Industry Standards) have no Acumen *output* in the supplied reports;
per the operator they are being **formula-audited** against the Bible (verify each implemented tool
formula/inclusion matches the library definition). The Fuse **proprietary** Float Ratio™ and composite
Score still lack an extractable formula and stay deferred.
