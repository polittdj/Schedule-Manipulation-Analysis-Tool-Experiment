"""Every MSPDI golden's header agrees with the provenance manifest that names its save
(ADR-0491).

``tests/fixtures/golden/PROVENANCE.json`` records, for each golden, the intake ``.mpp`` save it
was converted from — the git blob that IS that save, and the commit that carried it — matched
by measurement (the converter's plain output for the blob has task and assignment sections
byte-identical to the golden's). A golden regenerated from a different save would carry that
save's ``<Revision>`` / ``<LastSaved>``; this guard reads the golden's own header and pins it
to the manifest, so the file Fuse analysed (Hard_File_updated3: Revision 2, not the intake's
Revision 5) cannot be silently swapped. Red first: an entry with a wrong ``last_saved`` fails
by name.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
MANIFEST = json.loads((GOLDEN / "PROVENANCE.json").read_text(encoding="utf-8"))["goldens"]


def _header(rel: str) -> dict[str, str | None]:
    path = GOLDEN / rel
    raw = path.read_bytes()
    text = (gzip.decompress(raw) if path.suffix == ".gz" else raw)[:4096].decode("utf-8")
    out: dict[str, str | None] = {}
    for tag in ("Revision", "LastSaved"):
        m = re.search(rf"<{tag}>([^<]*)</{tag}>", text)
        out[tag] = m.group(1) if m else None
    return out


def test_the_manifest_names_every_golden_and_nothing_else() -> None:
    on_disk = sorted(str(p.relative_to(GOLDEN)) for p in GOLDEN.rglob("*.mspdi.xml*"))
    assert on_disk == sorted(MANIFEST)


@pytest.mark.parametrize("rel", sorted(MANIFEST))
def test_each_goldens_header_matches_its_recorded_save(rel: str) -> None:
    entry = MANIFEST[rel]
    header = _header(rel)
    assert header["Revision"] == entry["revision"], (rel, header, entry)
    assert header["LastSaved"] == entry["last_saved"], (rel, header, entry)


def test_every_sourced_entry_names_a_blob_a_commit_and_a_path() -> None:
    """The two EVM goldens have no committed source (their ``.mpp`` never entered the repo)
    and say so; every other entry addresses its save by blob and commit."""
    for rel, entry in MANIFEST.items():
        if entry.get("source") is None:
            assert rel.startswith("evm/") and entry.get("note"), rel
            continue
        assert re.fullmatch(r"[0-9a-f]{40}", entry["blob"]), rel
        assert re.fullmatch(r"[0-9a-f]{40}", entry["commit"]), rel
        assert entry["source"].startswith("00_REFERENCE_INTAKE/"), rel
