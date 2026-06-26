# ADR-0130 — Audit remediation (in-environment PATH-FORWARD items)

## Status

Accepted.

## Context

The read-only master verification & parity audit (`audit/AUDIT-REPORT.md`, `audit/PATH-FORWARD.md`)
found no CRITICAL defect but raised a set of HIGH/MEDIUM issues that were fixable **without any external
artifact** (no Acumen Fuse export, `.aft` Bible, or native `.mpp` required). The operator directed:
"execute everything you can that doesn't require me to submit anything." This ADR records the decisions
for that batch; the artifact-gated items (true Fuse numeric re-validation, the `.mpp` round-trip, the
literal `.aft` match, the Large-File absolute SSI reproduction) remain open and are listed in
`PATH-FORWARD.md` §D.

## Decision

1. **Parity transparency, not new claims (F-01 / F-03 / F-07).** `docs/PARITY-REPORT.md` was stale behind
   the ADR-0112 Project5 refresh; it is updated to the authoritative `case.json` (Critical P5 4, High Float
   44/44, Baseline-Start-Compliance 41/25, Net Finish Impact −148, SSI focus 145) and the §E
   **float/critical change subset is explicitly labeled engine-pinned / NOT Fuse-validated** (the gate
   asserts engine self-consistency for those rows, pending a fresh Acumen §E export). A new
   `tests/test_parity_report_sync.py` pins the report's headline numbers to `case.json` so it cannot drift
   silently again. `risks.md` R-02 and `ADR-0045` carry dated errata; the report's scope ("engine ==
   recorded golden" vs "golden == Fuse") is stated up front.

2. **Surface + guard the finish gap, do NOT reschedule (F-02).** The pure-logic CPM does not floor
   in-progress remaining work at the data date (the standing ADR-0108 gap), so it can understate a slip
   (TP4 v5: CPM 2026-06-26 vs stored 2026-07-17). Rather than make the CPM data-date-aware (two prior
   attempts regressed Acumen/EVM parity and were reverted — ADR-0108), the finish forecast gains a new
   **"As-scheduled (stored dates)"** method that surfaces the source tool's progress-aware finish next to
   the CPM finish, and `tests/engine/test_data_date_finish_gap.py` pins both. `TEST-PROJECTS.md`'s
   "every number pinned by tests" over-claim is corrected (the battery only asserts `finish > 0`).

3. **Two new manipulation detectors (F-05).** The namesake detector gained, as MEDIUM cited "review"
   findings: **`MANIP_CONSTRAINT_ADDED`** — an incomplete activity that gained a hard date constraint
   (MSO/MFO/SNLT/FNLT) since the prior version **and is now at ≤ 0 total float** (the constraint is
   actually clamping the date — fires on the masking signature, not on every benign constraint edit); and
   **`MANIP_CALENDAR_LOOSENED`** — the project calendar gained working time (longer day, added working
   weekday, removed holidays, extra worked-day exceptions), cited to the project calendar (UID 0). Both
   validated on synthetic positive/negative fixtures; the constraint detector also correctly surfaces the
   real UID-131 ASAP→MSO clamp in `Project5_TAMPERED` that the prior detector set missed.

4. **Close the latent XSS, surgically (F-06).** `_LAYOUT` is a bare `jinja2.Template` (autoescape OFF,
   because `body`/`banner` are already-built raw HTML) and the CSP allows `'unsafe-inline'`, so escaping is
   the sole barrier. The one untrusted value, `title` (the schedule key from the filename), is now escaped
   at the render boundary (`_e(title)`); autoescape is **not** flipped on (it would double-escape the raw
   `body`/`banner`). `tests/web/test_title_escaping.py` proves a hostile filename is inert in `<title>`.

5. **"Critical" definition split labeled, not unified (F-04).** `float_analysis` uses pure-logic
   `is_critical` while the DCMA/quality metrics use stored-flag `is_effective_critical`; on a progressed
   file the two can name different UID sets. The float-view docstring is labeled as the pure-logic critical
   set (distinct from the Acumen-parity metric); the bases are **not** merged, because the §E change
   metrics' "critical" basis is engine-pinned (decision 1) and re-routing it would deepen that circularity
   rather than resolve it — that waits on the Fuse §E export.

6. **Honest coverage config (F-08).** `pyproject` `fail_under` 99.9 (dead, contradicted CI's 70 and
   exceeded the real ~98% coverage) → 70.0 with an accurate comment; coverage stays CI-enforced.

7. **Docstring fix (F-12).** `ai/qa.py`'s module docstring is updated from two-modes/interpretive-default
   to the three-mode / annotate-default reality (ADR-0129).

## Consequences

- No parity number moves: the parity gate stays green (the forecast set and the manipulation findings are
  not gate-pinned; the goldens carry no calendar/constraint changes that the new detectors would alter).
  Full gate green.
- The §E circularity and the finish-understatement are now **disclosed at the point of use** (the report,
  the forecast page, the test names) rather than hidden; the engine's pure-logic behavior is unchanged.
- The tool now detects two manipulation vectors it is literally named for; both are MEDIUM review flags
  (confirm-authorized), specificity-gated to avoid false positives.

## Alternatives considered

- **Make the CPM data-date-aware (close F-02 in the engine).** Rejected for this batch: ADR-0108 records
  two reverted attempts that regressed parity; it requires the Fuse re-validation artifact to do safely.
- **Unify the "Critical" definition (F-04).** Rejected now: it would move the engine-pinned §E values and
  deepen the F-01 circularity; gated on the Fuse §E export.
- **Flip Jinja autoescape on globally (F-06).** Rejected: `body`/`banner` are intentionally raw HTML;
  global autoescape would double-escape them. The surgical `_e(title)` is correct and low-risk.
