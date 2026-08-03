---
name: metric-parity
description: Add, change or audit a POLARIS/SMAT metric, CPM/float calculation, or any number the tool reports, under Law 2 (fidelity over speed). Use whenever touching engine/, engine/metrics/, cpm.py, driving_slack, an importer's numeric field, a metric formula, a threshold, or a golden/parity expectation; whenever a figure disagrees with Acumen Fuse, SSI or MS Project; and whenever asked to "match the reference tool", explain a residual, or re-baseline a pin. A fast wrong number is worthless in a testimony context.
---

# Metric & parity work (Law 2)

**Numbers must match the reference tools on the same inputs.** Parity is gate-locked
(`pytest -m parity`). Never guess, never reverse-fit, never fabricate — an unreproducible figure is
**deferred or pinned with its delta**, not invented. Composite Acumen scores (SQ 88, DCMA 57/49) were
permanently deferred for exactly this reason: their weighting is unpublished, so reproducing them
would be fabrication.

## 1. Get the formula from the Bible — verbatim

Authoritative formulas come from the **NASA Acumen metric library**:
`00_REFERENCE_INTAKE/**/NASA Metrics_Complete_*.aft` — an XML `<MetricLibraryFile>` of `<Metric>`
Name/Formula (759 named metrics). It is committed (non-CUI, ADR-0151/0152), so
`tests/engine/test_aft_formula_audit.py` runs against the real library on CI.

- Pull the formula **verbatim**; do not paraphrase from memory or from another metric's family.
- Classify the correspondence honestly in the audit table: `match` · `variant` · `drift` ·
  `not_in_bible`. A **real** definitional difference is `drift` and gets an ADR — the `.aft` audit
  once found the tool's `SPI(t)` was *a different metric of the same name*.
- The guard audits **every** `.aft` under `00_REFERENCE_INTAKE/`, not `sorted(...)[0]`.

**Before reverse-engineering a reference tool's judgement, check whether it wrote it down.** The
authoritative source dissolved three sessions of proxy reasoning in one read.

## 2. Triage a slack/float variance as stored-vs-recomputed FIRST

`engine/metrics/_common.py::effective_total_float` / `is_effective_critical` prefer the source file's
**stored, progress-aware** Total Slack / Critical flag over recomputed pure-logic CPM float when the
file carries it. This is the single most-repeated engine ambiguity in the repo's history:

- "2 vs 76" critical-path bug (ADR-0150) and chapter-01's "90 vs 34" (ADR-0220) were both a display
  using the pure-logic critical set on a progressed file — **the correct instrument already existed**;
- the High-Float and §E change-metric residuals traced to the same split.

So: before hypothesising an engine defect, determine whether you are comparing a **stored** figure to
a **recomputed** one. Use the chokepoint; never re-derive float locally in a view.

## 3. Honor the model's contracts

- `Task.unique_id` is the **sole** cross-version identity — never the row id (renumbers), never the
  name. The XER importer once keyed on P6's renumbering `task_id` and produced flat-0.00 CEI across a
  series (ADR-0185).
- Durations are integer **working minutes** (480 = one 8-hour day). Convert to days **only** at the
  presentation boundary, and divide by the schedule's **real** minutes/day — never a hard-coded 480.
  Elapsed ("eday") durations are wall-clock: 1440 min/day, calendars ignored. Hard-coded 480 has
  fabricated negative float and mis-scaled SRA day counts (ADR-0139/0221/0224).
- CPM dates and float are **derived by the engine, never stored** on the task.
- Optional date/cost fields default to `None` meaning *"the source didn't provide it"* — **never
  assume 0**. Return `CheckStatus.NOT_APPLICABLE`, not a fabricated zero.
- Every metric returns the frozen `MetricResult` (`metric_id`, `name`, `count` numerator,
  `population` denominator, `value`, `unit`, `status`, `threshold`, `direction`, `offender_uids`) so
  every figure can cite file + UID + task.

## 4. Key applicability on the POPULATION COUNT, not on `value == 0`

The recurring falsy-zero class: `(x or 1)` / `(x or 0)` / truthiness tests turn an **absent** figure
into a measured zero. A CEI of `0.00` rendered green; `0.0` rates rendered "n/a"; an empty population
rendered `0%` next to a `—`. Decide applicability from the denominator's **count**, and let absence
stay absent all the way to the sentinel `—`.

## 5. Validate against the oracles

- The committed golden pair and hard-files under `tests/fixtures/golden/`.
- The operator's Acumen/SSI comparison exports under `00_REFERENCE_INTAKE/` (`.xlsx`).
- **Root-cause a parity gap by SET-DIFF against the reference tool's own output**, and distrust the
  first clean hypothesis. A whole-day "span snap" was added to cure a "+1-day raggedness" that was
  actually resource leveling; with the snap ON the engine matched only 325/783. It had been
  "spot-checked against a handful of activities; never run end-to-end against a full SSI export."
  Removing it and honoring lunch + per-task calendars reached **783/783**.
- **Pair every clean golden with synthetic blind-spot fixtures** (inactive / elapsed / 24-hour /
  progressed / ragged). Clean goldens do not exercise the forensic target
  (`tests/engine/test_blind_spot_populations.py`, institutionalized ADR-0136).
- A **stale golden hides real bugs** — a golden carrying 37 stored-critical activities vs the
  authoritative file's 4 sustained a phantom residual for many sessions.

## 6. Gates, and how a pin may legitimately move

```bash
python -m pytest -m parity                        # the acceptance gate — must stay green
python -m pytest tests/engine tests/parity -q
python -m pytest tests/engine/test_aft_formula_audit.py -q
```

A legitimately shifted pin gets a **deliberate, ADR-named re-baseline through that pin's own path** —
never a silent update, and never a weakened assertion. Assert the value **and** its delta
(the ratcheting residual gate) so an improvement cannot regress unnoticed.

## 7. Then regenerate the dictionary

Each metric's definition + formula + source lives in `web/help.py`; `docs/METRIC-DICTIONARY.md` is
**generated** from it and a test enforces sync:

```bash
python -c "from schedule_forensics.web.help import render_dictionary_markdown as r; open('docs/METRIC-DICTIONARY.md','w',encoding='utf-8').write(r())"
```

## 8. Known open gap — do not "fix" it casually

**ADR-0108, the in-progress data-date reschedule.** MS Project reschedules remaining duration from
the data date only when *behind*; the pure-logic CPM does not. **Two localized fix attempts each
regressed EVM1 and broke Project2/5 parity and were reverted.** It is surfaced as a labeled forecast
instead. A known gap beats a fast wrong number.

If the oracle and the file's bytes genuinely contradict, **STOP and ask the operator** rather than
fixing toward a misread oracle — an oracle can contradict its own file, and the bytes decide.
