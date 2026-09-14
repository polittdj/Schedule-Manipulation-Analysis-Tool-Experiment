# ADR-0490 — An absent `TotalSlack` on a `Critical` activity is the ZERO the MPXJ writer dropped: the importer infers it when the file carries the element elsewhere, so the stored-preferring float basis now covers the zero-slack subset (R-49 CLOSED)

- **Status:** Accepted — 2026-09-14 (the plan-forward's §3, first row after the design page: R-49)
- **Version:** 1.0.258
- **Extends:** ADR-0473 (the multi-project Fuse oracle, which registered the row), ADR-0080 / ADR-0010 (`effective_total_float`: the source tool's stored, progress-aware slack over the engine's pure-logic float, with the recomputed float as the fallback), ADR-0430 (Negative Float on the stored slack), ADR-0474 / ADR-0487 (MS Project's stored values as the per-activity CPM oracle; read the `.mpp` through the vendored MPXJ before declaring what a file carries)
- **Shipped:** `importers/mspdi.py` (`_stored_slack_minutes(zero_when_absent=)`; `_parse_task(file_carries_slack=)`; the file-level `file_carries_slack` census), `tests/importers/test_mspdi_zero_slack_inference.py` (7, NEW), `tests/parity/test_hard_file_stored_dates_oracle.py` (four stored-slack population pins re-baselined, dated, with the reason), `docs/STATE/AUDIT-2026-08-27-REPORT.md` (R-49 CLOSED), `docs/PARITY-REPORT.md`

## Context

`effective_total_float` (ADR-0080) scores a task on the source tool's **stored** Total Slack when
the file carried one and falls back to the engine's pure-logic CPM float otherwise — the rule that
made the DCMA float checks agree with Acumen on progressed schedules. ADR-0473's oracle found the
hole in it: on Large Test File2, **62 of Fuse's 66 zero-float activities carry no `TotalSlack`
element at all**, so exactly the zero-slack subset was scored on the *other* basis. The register
priced the row as "the importer reads an absent `TotalSlack` as 0 when the file carries the element
elsewhere and the task carries `Critical`; red-first on Fuse's Zero Days Float 66 / 2, with the
SSI driving-slack gates as the arbiter".

**The provenance, settled on the binary rather than the XML (QC-2, the ADR-0487 lesson).** A Java
probe against the vendored `org.mpxj` read the intake `.mpp` files themselves:

| file | non-summary | Critical | Critical & slack **NULL** | Critical & slack **0.0d** | Critical & negative | zero slacks in memory | literal zeros in the written XML |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Large Test File2.mpp` | 1 722 | 185 | **0** | **62** | 123 | 786 | **0** |
| `Large Test File.mpp` | 1 723 | 43 | 0 | 2 | 41 | 701 | 0 |
| `Hard_File_updated3.mpp` | 110 | 49 | 0 | 0 | 49 | 42 | 0 |

The reader holds `TotalSlack = 0.0d` for every one of the 62 (and NULL for none); the MSPDI writer
emits none of the 786 zeros (a written XML with 1 202 slack elements and not one literal zero). The
critical-slack threshold on every file is `0.0d`. So "MPXJ omits a ZERO `TotalSlack`" is the
converter's own behaviour, measured — and an absent element on a task the file flags `Critical` can
only be a zero: MS Project flags Critical exactly when slack ≤ the threshold, and a negative slack
is always written (123 of them on that file).

**What the register's red-first could not be.** On every fixture in the repo the engine's
pure-logic float for those tasks is *already* exactly 0 minutes — 41 / 4 on Project2 / Project5,
2 / 62 on the Large Test Files, all of them — so Fuse's Zero Days Float **66 / 2 was already exact
on the pristine tree**, and no whole-day count could go red. The census of all 28 MSPDI fixtures
found **one** file where the two bases disagree for such a task: `Hard_File`, UIDs **241** (pure
logic 480 min, MS Project 0) and **249** (360 min, 0). That, and a synthetic file, are the red.

## Decisions

1. **The importer infers the dropped zero, bounded twice.** `_stored_slack_minutes(task_el,
   zero_when_absent=…)` returns 0 for an absent element only when the caller passes
   `file_carries_slack and stored_critical`: the FILE carries `TotalSlack` on some task (a writer
   that never emits the element dropped nothing — a hand-written or third-party MSPDI keeps
   `None`), and THIS task is flagged `Critical`. Everything else is unchanged: a written slack is
   read as before (tenths of a minute → minutes); an absent slack on a non-critical or unflagged
   task stays `None`.
2. **A completed task's zero stays `None` — deliberately, and priced.** The writer drops those
   too (634 completed tasks on Large Test File2 read `0.0d` in memory and carry no element), and MS
   Project shows them as `0d`; but no metric reads a completed task's slack (DCMA-06/07, the ribbon
   Negative Float, the float ratio and the scatter score incomplete work), and the only visible
   difference is the Data Explorer's `Total Slack (d)` column reading `—` where MS Project reads
   `0d`. Widening the inference to every absent slack is the faithful reading of the probe (NULL
   for none) and is its own row (R-62), never a blind edit inside a metric fix.
3. **The stored basis now covers the zero-slack subset, and the numbers say what moved.** Every
   single-schedule metric family was snapshotted on eight goldens before and after (624 entries):
   **two moved**, both on `Hard_File` — the float ratio 3.99 → 3.98 and its aggregate 2.82 → 2.80
   (UIDs 241 / 249 scored on the file's own zero) — and nothing else, on any file. The SSI
   driving-path gates on `Hard_File` / `Hard_File_updated` (the register's arbiter) are unmoved: the
   driving-slack engine never read the stored slack.
4. **Four population pins in the stored-dates oracle were re-baselined ON PURPOSE, with the reason
   beside them:** the oracle counts the tasks that carry a stored slack (`tf_n`) and how many of
   those the engine reproduces exactly (`tf_exact`); both grew by exactly the inferred zeros —
   Project2 65 → 106, Project5 95 → 99, Large Test File (842, 1 022) → (844, 1 024), File2 (668, 936)
   → (730, 998) — and every inferred zero is exact, which is the same fact as decision 3 read from
   the other side.

## Verification (QC-1)

- **Red first, on the pristine importer:** `test_mspdi_zero_slack_inference.py` **5 failed / 2
  passed** — the synthetic file's Critical tasks read `None`; `effective_total_float` on the
  synthetic task B read the pure-logic 1 440 min; Hard_File UIDs 241 / 249 read 480 / 360; Large
  Test File2 carried 0 inferred zeros; the Save format round-tripped `None`. The two passes are
  green on both trees by construction and say so in their docstrings: no inference on a file
  without the element (there is nothing to infer from on the pristine tree either), and Fuse's
  Zero Days Float **66 / 2** — pinned so the inference can never move them, not as the red.
- **Green:** the module **7** · `tests/importers` + `tests/engine` + `tests/model` **1 581 passed**
  · `pytest -m parity` **97 passed** after the four dated re-pins and one re-aimed pin (the run
  before them read **5 failed / 92** — the four population pins, each moved by exactly the
  inferred count, and ADR-0430's "teeth" pin in `test_fuse_hardfile_parity.py`, which asserted
  that Hard_File still carries 34 Critical activities with NO stored slack so that a recompute
  fallback re-counting them as negative float would go red by name) · both ruff binaries ·
  `ruff format --check` · mypy --strict 165 files.
- **A pin whose teeth had already gone, found by this change and recorded:** ADR-0430's phantom
  population (34 stored-less Critical activities) was the set whose RECOMPUTED float read negative
  on the 2026-07 engine; on the post-ADR-0474 engine those 34 recompute to 0 (32) and to +480 /
  +360 (UIDs 241 / 249) — never negative — so a reintroduced fallback would have counted nothing
  and the pin could no longer fail for its stated reason. It is re-aimed at the inference: the 34
  carry the inferred zero and none is `None`, which the r01 mutant (the inference never fires)
  turns red by name.
- **Mutation, on scratch copies of the FINAL src imported through `PYTHONPATH`** (the imported
  importer asserted to BE the copy; one landing each; a green control first), **6 / 6 RED BY
  NAME:** the inference never fires · the file-carries guard dropped · the Critical guard dropped
  (every absent slack a zero — the completed tasks then carry 0 and the LTF2 pin names it) · the
  Critical guard inverted · the inferred value 1 minute instead of 0 · the carries-guard reading
  `Critical` instead of `TotalSlack`.
- **Measured, not assumed:** the before / after family snapshot (decision 3); the MPXJ probe
  (Context); the 28-fixture census that found Hard_File's two UIDs and nothing else.

## Consequences

- R-49 is **CLOSED**. Fuse's zero-float sets on the Large Test Files are reproduced on the STORED
  basis now, not by the coincidence that the fallback also read zero.
- A Save (`.json`) made from an MSPDI source before this version carries `None` for those tasks;
  re-import the source to get the inferred zero (the same posture as ADR-0473's currency note).
- **R-62 registered:** every absent slack the MPXJ writer dropped is a zero (the probe's NULL-for-
  none), completed tasks included; the Data Explorer's `Total Slack (d)` reads `—` for them where
  MS Project reads `0d`. S; the same guard census, one probe on a completed task's metrics.
- `_parse_task` takes a keyword `file_carries_slack` (default `False`); the two other MSPDI
  walks (`_project_baseline_finish`, the views) are untouched.
