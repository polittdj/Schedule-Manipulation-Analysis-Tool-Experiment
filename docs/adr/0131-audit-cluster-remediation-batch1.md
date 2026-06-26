# ADR-0131 — Audit-cluster remediation, batch 1 (the orphaned internal-audit findings + NEW-1)

## Status

Accepted.

## Context

The master re-verification (`audit/VERIFICATION-REPORT.md`, PR #271) found that the two prior audit
trails were never merged: the F-set roadmap (`audit/PATH-FORWARD.md`) was remediated by ADR-0130, and
the internal audit's two operator-decision items by ADR-0128 (M1) / ADR-0129 (C2) — but the rest of the
internal audit's own 3-wave plan (`docs/STATE/AUDIT-2026-06-25.md`) was **orphaned and left OPEN**,
including a CRITICAL (C1). The re-audit also found one defect neither trail had: **NEW-1**, a Float-Ratio
day-axis mismatch. The operator directed: start closing C1 and the orphaned cluster.

This ADR records the first remediation batch. Every fix is in-environment (no external artifact needed)
and is guarded by a new or updated test; **no parity number moves** (the goldens don't exercise any of
these paths — which is exactly why the gate was blind to them).

## Decision

1. **C1 (CRITICAL) — full Save .json fidelity.** `importers/json_schedule.py` `to_json_text` now emits,
   and `_task` / `_calendar` / `_from_friendly` now read back, every fidelity-bearing field the model
   carries: Task `is_active`, `calendar_uid`, `outline_level`, `is_estimated_duration`,
   `is_level_of_effort`, `physical_percent_complete`, `stored_total_float_minutes`, `stored_is_critical`,
   `custom_fields`; `Schedule.custom_field_labels`; Calendar `uid`, `working_days`, `day_segments`. A new
   `test_save_json_round_trips_every_fidelity_field` diffs the **full** field set, so a future schema add
   not wired into JSON I/O fails loudly. This closes the silent Law-2 break where a re-opened progressed
   file lost the Acumen-parity stored float/critical (and silently re-activated an inactive task,
   defeating ADR-0128).

2. **H1 — SSI load can't 500 / half-mutate on a non-list `affected`.** `_apply_ssi_setup` guards the
   per-risk `affected` with an `isinstance(list/tuple)` check like its sibling dict fields, so a
   hand-edited `affected: 5` / `null` drops that risk instead of raising mid-write and leaving the
   session partially overwritten.

3. **H3 / H4 — one malformed XER id no longer sinks the file.** A new tolerant `_drop_int` builds the
   cross-project task-id universe and parses `TASKPRED` endpoints; a non-integer id in a non-selected
   project (H3) or a `TASKPRED` row (H4) is dropped-and-counted (the existing dangling/out-of-scope
   tolerance class) rather than refusing an otherwise-valid multi-project export. In-scope task rows are
   still validated loudly by `_parse_task`. The prior `test_taskpred_missing_task_id_raises` is updated to
   assert the corrected drop-not-fatal behavior.

4. **M3 — friendly JSON no longer fabricates `project_start`.** A missing/null `project_start` now raises
   `ImporterError`, matching MSPDI / XER, instead of inventing a `2025-01-06` CPM anchor that masked
   truncated/hand-edited files.

5. **M4 — UID-0 baseline-finish leak closed.** `_project_baseline_finish` now mirrors the model's
   effective-summary rule (`is_summary or uid == 0`), so a UID-0 project-summary row whose XML omits
   `<Summary>` cannot leak its project-spanning rollup baseline into the CPLI basis. Goldens are
   unaffected (their UID-0 row carries `Summary=1`).

6. **M2 — pre-commit guard + `.gitignore` now block `.aft` / `.docx` / `.doc`.** CLAUDE.md Law 1 names
   these CUI extensions; the hook regex and `.gitignore` now cover them. A new
   `tests/guards/test_precommit_blocklist.py` reads the hook's actual regex and asserts every named CUI
   extension is blocked (case-insensitively) so spec and implementation can't drift again.

7. **M6 — figure-gate is sign-aware.** `ai/citations._FIGURE_RE` gains an optional leading `-`, so a
   rephrase that flips `-5 days` (ahead) to `5 days behind` changes the multiset and forces the verbatim
   fallback. Sign is load-bearing in schedule forensics (variance / float / slip direction).

8. **NEW-1 — Float Ratio is single-axis.** `engine/metrics/float_ratio` now divides float on the **same
   axis** as remaining duration (wall-clock 1440 for an elapsed-duration activity, working-day `per_day`
   otherwise). Previously float used the working-day axis while an elapsed activity's remaining used the
   wall-clock axis, distorting the ratio by `1440/per_day` (reporting 1.0 where the unit-consistent value
   is 0.33). The metric's docstring (which had falsely claimed unit-consistency) is corrected. Non-elapsed
   activities — every golden — are unchanged.

9. **L2 / L7 / M8 (low / doc).** `_to_float` rejects non-finite (`inf`/`nan`) input at the web boundary
   (`math.isfinite`) instead of accepting it and 422-ing every later SRA sim. MSPDI's cosmetic
   `OutlineLevel` uses a new tolerant `_cosmetic_int` (non-integer → default 0) so a presentational field
   can't refuse the whole file; identity/structural fields keep the loud `_int`. The MEI help entry now
   documents that the index can read above 1.0 (milestones met ahead of baseline), and
   `docs/METRIC-DICTIONARY.md` is regenerated from `help.py`.

## Consequences

- **No parity number moves**: the goldens carry no inactive tasks, no elapsed in-progress Normal
  activity, no UID-0-without-Summary row, and no malformed ids, so `non_summary` / CPLI / float-ratio /
  importer results are identical; `pytest -m parity` stays green. Each fix is pinned by a new/updated
  test, since no golden exercised these paths.
- The CRITICAL C1 fidelity break is closed and guarded; a Save → reopen now round-trips every model field.
- Importer crash-safety (H1/H3/H4/L7) and the AI sign-gate (M6) are hardened without touching the
  validated numbers.
- **Deferred to a follow-up batch** (flagged, not forgotten): M5 (days↔% client/server rounding — needs
  coordinated JS + server change), M7 (path-filter debounce — JS perf), L3 (offload atexit hook), and H2
  (the prose-tamper denylist — a design decision left for operator input, since CLAUDE.md already
  documents the "digits, not prose" scope). F-11 (interpretive-mode role re-labeling) remains an accepted,
  documented design choice.

## Alternatives considered

- **Switch Save .json to strict `model_dump_json` (C1).** Rejected: the friendly format is also the
  hand-authored import format and the bundled example; extending it to full fidelity keeps it readable and
  re-openable while closing the loss. The new full-field round-trip test makes any future drift loud.
- **Make the CPM data-date-aware to also close F-02 in the engine.** Out of scope for this batch (ADR-0108
  records two reverted attempts; it is artifact-gated). F-02 stays disclosed+guarded per ADR-0130.
- **Unify the "Critical" definition (F-04 / L1).** Still deferred per ADR-0130 §5 (it would move the
  engine-pinned §E values); only the labeling fix from ADR-0130 stands.
