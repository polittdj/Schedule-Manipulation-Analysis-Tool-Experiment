"""Local-only validation harness: diff the importer output vs. live MS Project COM.

WINDOWS + MS PROJECT ONLY. This script is intentionally a guarded stub on every
other platform (this build is developed on Linux, where COM is unavailable -- see
docs/HAZARDS.md, H-NO-COM-HERE). On a Windows machine with MS Project installed,
it opens the same `.mpp` file via COM and via the (future) COM importer and diffs
every field for every task, field-by-field.

Results are written under ``local_validation_results/`` (gitignored). Real `.mpp`
files and their derived results are NEVER committed (LAW 1).

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

    # TODO (Windows-only, deferred): open argv[1] via COM (ReadOnly, headless),
    # parse the same file via the COM importer, diff every field per task, and
    # write a field-by-field report under local_validation_results/.
    print(
        "validate_against_msp: COM is present but the COM importer is not yet "
        "implemented (Windows-only enhancement, deferred). Nothing to validate.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
