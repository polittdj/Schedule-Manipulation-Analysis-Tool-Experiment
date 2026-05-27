"""Local-only validation harness: read a ``.mpp`` via COM and cross-check vs MPXJ.

WINDOWS + MS PROJECT ONLY for the COM read. This script is a guarded no-op on every
other platform (this build is developed on Linux, where COM is unavailable -- see
docs/HAZARDS.md, H-NO-COM-HERE). On a Windows machine with MS Project installed it:

  1. opens the ``.mpp`` via the COM importer (headless, ReadOnly) and prints each
     task's key fields; then
  2. reads the SAME ``.mpp`` via the cross-platform MPXJ importer (if a Java/MPXJ
     runner is configured) and diffs the two reads field-by-field
     (:func:`schedule_forensics.schedule_compare.diff_schedules`).

Two independent readers agreeing on every field is the ground-truth check for the
COM mapping's ``source-pending`` assumptions -- gotcha 5 (durations/lags in MINUTES)
and gotcha 10 (the ConstraintType / Dependency.Type enum codes). Any disagreement is
printed for the operator to adjudicate against the MS Project UI (LAW 2). The MPXJ
cross-check is SKIPPED (not failed) when no runner is configured.

All output goes to stdout; nothing is written or transmitted. Real ``.mpp`` files
and any values derived from them are CUI and are NEVER committed (LAW 1).

Usage (Windows): python scripts/validate_against_msp.py path\\to\\schedule.mpp
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    try:
        import win32com.client  # noqa: F401  (presence check only)
    except ImportError:
        print(
            "validate_against_msp: COM (win32com) is unavailable on this platform.\n"
            "This harness runs only on Windows with MS Project installed. The "
            "cross-platform importers (MS Project XML / Primavera XER / MPXJ) are "
            "validated by the pytest suite instead. See docs/HAZARDS.md "
            "(H-NO-COM-HERE).",
        )
        return 0

    if len(argv) < 2:
        print("usage: python scripts/validate_against_msp.py <path-to.mpp>")
        return 2

    # Windows-only: read the same .mpp via the COM importer and report each task's
    # required fields. The COM driver opens headless + ReadOnly and tears the app
    # down in finally (see importers/com_msproject.py). This is the on-Windows
    # ground-truth check the Linux unit tests cannot perform (docs/HAZARDS.md
    # H-NO-COM-HERE). Results stay LOCAL (LAW 1).
    from schedule_forensics.importers.com_msproject import (
        ComUnavailableError,
        parse_mpp_via_com,
    )

    mpp_path = argv[1]
    try:
        schedule = parse_mpp_via_com(mpp_path)
    except ComUnavailableError as exc:
        print(f"validate_against_msp: {exc}")
        return 0
    except Exception as exc:  # noqa: BLE001 -- surface any import failure to the operator
        print(f"validate_against_msp: failed to read {mpp_path!r} via COM: {exc}")
        return 1

    print(f"validate_against_msp: COM read OK -- {schedule.name!r}")
    print(f"  project_start={schedule.project_start.isoformat()}")
    status = schedule.status_date.isoformat() if schedule.status_date else "None"
    print(f"  status_date={status}")
    print(f"  tasks={len(schedule.tasks)}  relations={len(schedule.relations)}")
    for task in schedule.tasks:
        print(
            f"    UID={task.unique_id} dur_min={task.duration_minutes} "
            f"constraint={task.constraint_type.value} pct={task.percent_complete} "
            f"name={task.name!r}"
        )

    # Cross-check: read the SAME .mpp via the cross-platform MPXJ importer and diff
    # field-by-field. Two INDEPENDENT readers agreeing is strong evidence the COM
    # gotcha-5 (minutes) and gotcha-10 (constraint/relation enum codes) mappings are
    # correct; any disagreement is printed for the operator to adjudicate against the
    # MS Project UI rather than silently trusted (LAW 2). MPXJ is optional, so this
    # cross-check is skipped (not failed) when no Java/MPXJ runner is configured.
    from schedule_forensics.importers.mpp_mpxj import ImporterError as MpxjError
    from schedule_forensics.importers.mpp_mpxj import mpxj_configured, parse_mpp
    from schedule_forensics.schedule_compare import diff_schedules

    if not mpxj_configured():
        print("  COM-vs-MPXJ cross-check skipped: no MPXJ runner (install Java / set SF_MPXJ_*).")
        return 0
    try:
        mpxj_schedule = parse_mpp(mpp_path)
    except MpxjError as exc:
        print(f"  COM-vs-MPXJ cross-check skipped: MPXJ read failed: {exc}")
        return 0

    diffs = diff_schedules(schedule, mpxj_schedule, a_label="COM", b_label="MPXJ")
    if not diffs:
        print("  COM vs MPXJ: identical on every compared field -- no drift.")
        return 0
    print(f"  COM vs MPXJ: {len(diffs)} field difference(s) -- verify against the MS Project UI:")
    for line in diffs:
        print(f"    - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
