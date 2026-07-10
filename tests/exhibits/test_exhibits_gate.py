"""SSI-ambiguity gate (master prompt §2.4 fallback): NEW code (the exhibits package) must
never use the bare token 'SSI' — write StructuredSolutions* (the vendor) or
ScheduleSensitivityIndex* (the SRA metric). The legacy occurrences elsewhere are allowlisted
until the full rename (audit/PARK-LIST.md P3)."""

from __future__ import annotations

import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "exhibits"


def test_no_bare_ssi_in_exhibits() -> None:
    offenders = []
    for f in PKG.rglob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bSSI\b", line):
                offenders.append(f"{f.name}:{i}: {line.strip()}")
    assert not offenders, "bare 'SSI' is ambiguous (vendor vs metric):\n" + "\n".join(offenders)
