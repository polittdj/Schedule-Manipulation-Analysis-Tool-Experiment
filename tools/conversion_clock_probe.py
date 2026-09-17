"""Convert ONE schedule save under two or more frozen JVM clocks and report exactly which MSPDI
elements the vendored converter resolves at CONVERSION time (ADR-0506, R-63).

MPXJ 16.2.0's ``Resource.getMaxUnits`` / ``getAvailableFrom`` / ``getAvailableTo`` /
``getStandardRate`` / ``getOvertimeRate`` and the resource ``OverAllocated`` flag resolve the
resource's availability and cost-rate tables at ``LocalDateTime.now()`` (read off the bytecode:
``getCurrentAvailabilityTableEntry`` / ``getCurrentCostRateTableEntry``), and ``CurrentDate``
defaults to the same clock — so the same save converted a month apart carries different scalars
while the tables (``AvailabilityPeriods`` / ``Rates``) and every task, assignment and calendar are
byte-identical. This probe makes that a reproducible measurement rather than a memory. Measured
2026-09-17 on the Hard_File_updated3 golden's own save: a 07-09 clock reproduces the committed
golden to the second; 09-14 and 11-01 change 9 and 13 element pairs, all of the kinds above.

Needs ``faketime`` (libfaketime, ``apt install faketime``) and a JRE 17+. Local only (LAW 1): the
JVM runs here, on committed non-CUI build inputs.

    python tools/conversion_clock_probe.py <save.mpp> "2026-07-09 14:56:59" "2026-09-14 10:00:00"
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MPXJ = ROOT / "tools" / "mpxj"
_ELEMENT = re.compile(r"^[+-]\s*<(/?)(\w+)>")
_UID = re.compile(r"<UID>(\d+)</UID>")


def _convert(save: Path, clock: str, workdir: Path) -> str:
    java, faketime = shutil.which("java"), shutil.which("faketime")
    if java is None or faketime is None:
        raise SystemExit("needs `java` (JRE 17+) and `faketime` (libfaketime) on PATH")
    out = workdir / f"{save.stem}.{clock.replace(' ', '_').replace(':', '')}.xml"
    env = dict(os.environ, FAKETIME_DONT_FAKE_MONOTONIC="1")
    cmd = [faketime, "-f", f"@{clock}", java, "-cp", f"{MPXJ}/classes:{MPXJ}/lib/*"]
    cmd += ["MpxjToMspdi", str(save), str(out)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0 or not out.exists():
        raise SystemExit(f"conversion at {clock!r} failed: {result.stderr[-800:]}")
    return out.read_text(encoding="utf-8")


def _section(text: str, tag: str) -> str:
    start = text.index(f"<{tag}>")
    return text[start : text.index(f"</{tag}>", start)]


def _changed(base: str, other: str) -> list[tuple[str, str, str | None]]:
    """``(sign, element, resource UID)`` per changed line between two conversions."""
    lines = base.splitlines()
    uid_of_line: list[str | None] = []
    current: str | None = None
    for line in lines:
        if line.strip() == "<Resource>":
            current = "?"
        elif current == "?" and (m := _UID.search(line)):
            current = m.group(1)
        elif line.strip() == "</Resource>":
            current = None
        uid_of_line.append(current)
    out: list[tuple[str, str, str | None]] = []
    matcher = difflib.SequenceMatcher(None, lines, other.splitlines())
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        for i in range(i1, i2):
            m = _ELEMENT.match("-" + lines[i])
            out.append(("-", m.group(2) if m else "?", uid_of_line[i]))
        for line in other.splitlines()[j1:j2]:
            m = _ELEMENT.match("+" + line)
            out.append(("+", m.group(2) if m else "?", uid_of_line[min(i1, len(lines) - 1)]))
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1
    save, clocks = Path(argv[0]), argv[1:]
    with tempfile.TemporaryDirectory() as tmp:
        texts = {clock: _convert(save, clock, Path(tmp)) for clock in clocks}
    base_clock, base = clocks[0], texts[clocks[0]]
    for clock in clocks[1:]:
        other = texts[clock]
        changed = _changed(base, other)
        elements = sorted({e for _, e, _ in changed})
        uids = sorted({u for _, _, u in changed if u}, key=int)
        print(f"{base_clock} -> {clock}: {len(changed)} changed lines; elements {elements}")
        print(f"   resources touched (UID): {uids}")
        for tag in ("Tasks", "Assignments", "Calendars"):
            same = _section(base, tag) == _section(other, tag)
            print(f"   <{tag}> byte-identical: {same}")
        tables = re.compile(r"<(AvailabilityPeriods|Rates)>.*?</\1>", re.S)
        same_tables = tables.findall(base) == tables.findall(other)
        print(f"   availability / rate tables byte-identical: {same_tables}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
