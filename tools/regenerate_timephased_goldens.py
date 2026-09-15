"""Regenerate the MSPDI goldens from THEIR OWN saves with the converter's timephased data on
(ADR-0491, R-60).

Every MSPDI golden under ``tests/fixtures/golden/`` was converted from one specific save of an
intake ``.mpp`` — a save that lives in git history as a blob, named in
``tests/fixtures/golden/PROVENANCE.json`` (matched by measurement: the vendored converter's plain
output for that blob has task and assignment sections byte-identical to the golden's). The
vendored converter now writes the MSPDI ``TimephasedData`` (a resource-leveling SPLIT lives only
there), so each golden must carry it — from the SAME save, or the golden is a different file.

For each golden with a source this tool:

1. extracts the exact blob (``git cat-file blob <sha>``) — never the intake path's current
   bytes, which may be a later re-save (Hard_File_updated3: the intake is Revision 5, the golden
   Fuse analysed Revision 2);
2. converts it with the vendored converter (``tools/mpxj``, the class the tool ships);
3. PROVES it is the same save: the ``<Tasks>`` section byte-identical to the golden's, and the
   ``<Assignments>`` section identical once every ``<TimephasedData>`` element is removed —
   refusing loudly otherwise;
4. writes the new golden as the OLD golden with the new ``<Assignments>`` section spliced in —
   so the only change is the timephased data. The header, calendars and resources keep the
   values the golden was converted with: the writer resolves ``CurrentDate``, a resource's
   ``MaxUnits`` / ``OverAllocated`` / ``AvailableFrom`` / ``AvailableTo`` and its rates at
   CONVERSION time (measured 2026-09-14 on Hard_File_updated3: a 07-09 conversion and a 09-14
   one of the same save differ on exactly those elements) — a wall-clock dependence of the
   converter, not a property of the save, and not something a fixture should inherit.

Gzipped goldens are rewritten with a zero mtime and no name, so the bytes are reproducible.
Local only (LAW 1): the JVM runs here, on committed non-CUI build inputs.

    python tools/regenerate_timephased_goldens.py            # every sourced golden
    python tools/regenerate_timephased_goldens.py fuse_hardfile/Hard_File_updated3.mspdi.xml.gz
"""

from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "golden"
MPXJ = ROOT / "tools" / "mpxj"
_TP = re.compile(r"\n[ \t]*<TimephasedData>.*?</TimephasedData>", re.S)


def _read_golden(path: Path) -> str:
    raw = path.read_bytes()
    return (gzip.decompress(raw) if path.suffix == ".gz" else raw).decode("utf-8")


def _write_golden(path: Path, text: str) -> None:
    data = text.encode("utf-8")
    if path.suffix == ".gz":
        data = gzip.compress(data, mtime=0)
    path.write_bytes(data)


def _section(text: str, tag: str) -> tuple[int, int]:
    """``[start, end)`` of ``<tag>...</tag>`` in ``text`` (the tags included)."""
    start = text.index(f"<{tag}>")
    end = text.index(f"</{tag}>", start) + len(f"</{tag}>")
    return start, end


def _convert(blob: str, name: str, workdir: Path) -> str:
    """The vendored converter's MSPDI text for the git blob ``blob``."""
    mpp = workdir / name
    with mpp.open("wb") as out:
        subprocess.run(["git", "cat-file", "blob", blob], cwd=ROOT, stdout=out, check=True)
    xml = workdir / (name + ".xml")
    java = shutil.which("java")
    if java is None:
        raise SystemExit("java not found on PATH — the vendored converter needs a JRE 17+")
    classpath = os.pathsep.join([str(MPXJ / "classes"), str(MPXJ / "lib" / "*")])
    subprocess.run(
        [java, "-Xmx1g", "-cp", classpath, "MpxjToMspdi", str(mpp), str(xml)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return xml.read_text(encoding="utf-8")


def regenerate(rel: str, blob: str, workdir: Path) -> str:
    path = GOLDEN / rel
    old = _read_golden(path)
    name = Path(rel).name.replace(".mspdi.xml.gz", ".mpp").replace(".mspdi.xml", ".mpp")
    new = _convert(blob, name, workdir)
    ot0, ot1 = _section(old, "Tasks")
    nt0, nt1 = _section(new, "Tasks")
    if old[ot0:ot1] != new[nt0:nt1]:
        raise SystemExit(f"{rel}: the blob's <Tasks> differs from the golden's — not the same save")
    oa0, oa1 = _section(old, "Assignments")
    na0, na1 = _section(new, "Assignments")
    new_assignments = new[na0:na1]
    if _TP.sub("", new_assignments) != old[oa0:oa1]:
        raise SystemExit(
            f"{rel}: the blob's <Assignments> section differs from the golden's beyond the "
            "timephased data — not the same save"
        )
    if _TP.search(old[oa0:oa1]):
        raise SystemExit(f"{rel}: the golden already carries timephased data")
    spliced = old[:oa0] + new_assignments + old[oa1:]
    if _TP.sub("", spliced) != old:  # the construction's own proof: nothing else moved
        raise SystemExit(f"{rel}: splice changed more than the timephased data")
    _write_golden(path, spliced)
    added = len(_TP.findall(new_assignments))
    return f"{rel}: +{added} TimephasedData elements, {len(old):,} -> {len(spliced):,} bytes"


def main(argv: list[str]) -> int:
    manifest = json.loads((GOLDEN / "PROVENANCE.json").read_text(encoding="utf-8"))["goldens"]
    wanted = argv or [rel for rel, entry in manifest.items() if entry.get("blob")]
    with tempfile.TemporaryDirectory(prefix="sf-goldens-") as tmp:
        for rel in wanted:
            entry = manifest.get(rel)
            if entry is None or not entry.get("blob"):
                raise SystemExit(f"{rel}: no sourced entry in PROVENANCE.json")
            print(regenerate(rel, entry["blob"], Path(tmp)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
