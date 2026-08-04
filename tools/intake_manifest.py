"""Generate ``docs/INTAKE-MANIFEST.md`` — the provenance record for ``00_REFERENCE_INTAKE/``.

Why this exists
---------------
ADR-0152 committed the reference intake suite (non-CUI, operator-confirmed) to ``main`` via the
GitHub web UI. The 2026-08-03 external audit then found that the bulk upload arrived with a
**name/content rotation**: a large number of tracked intake files carry an extension that
disagrees with their actual bytes (``.png`` files that are JPEG, HTML or PDF; a ``.docx`` that is
a PDF; a ``.js`` that is the favicon ICO). Nothing the product reads is affected — but with no
manifest there was no way to tell an *inherited* mislabel from a *new* one, and no way to prove
the assets the engine actually depends on were untouched.

This module is the measurement. It walks the git-tracked files under ``00_REFERENCE_INTAKE/``,
records size / SHA-256 / declared extension / detected content family for each, and renders the
manifest. ``tests/guards/test_intake_manifest.py`` re-derives the same scan and fails if the tree
and the manifest disagree, so the provenance state is pinned: a new mislabel, a silent content
swap, or an added/removed intake file all fail loudly.

Detection is deliberately **decisive-or-silent**. A family is only asserted when the bytes say so
(a magic signature, an OOXML part name, an OLE2 stream name, a full JSON/XML parse). Anything else
is plain ``text`` or ``binary`` and is never reported as a mismatch — a fabricated mismatch would
be worse than the drift it chases (Law 2). Extensions with no standardised signature carry no
expectation at all and are recorded without judgement.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INTAKE = "00_REFERENCE_INTAKE"
MANIFEST = REPO / "docs" / "INTAKE-MANIFEST.md"

# Classification reads the WHOLE blob, never a prefix window. The July 2026 QC audit lost a day to
# a 64-byte magic window that invented three false positives, and a truncated head cannot be
# JSON/XML-parsed honestly — "the first 64 KB is valid JSON" is not "this file is JSON".

# --------------------------------------------------------------------------------------------
# content families
# --------------------------------------------------------------------------------------------

# (signature, offset, family) — checked in order, first hit wins.
_SIGNATURES: tuple[tuple[bytes, int, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", 0, "png"),
    (b"\xff\xd8\xff", 0, "jpeg"),
    (b"GIF87a", 0, "gif"),
    (b"GIF89a", 0, "gif"),
    (b"\x00\x00\x01\x00", 0, "ico"),
    (b"%PDF-", 0, "pdf"),
    (b"\x1f\x8b", 0, "gzip"),
    (b"BM", 0, "bmp"),
    (b"ftyp", 4, "mp4"),
    (b"RIFF", 0, "riff"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", 0, "ole2"),
    (b"PK\x03\x04", 0, "zip"),
    (b"PK\x05\x06", 0, "zip"),
    (b"PK\x07\x08", 0, "zip"),
)

# OOXML refinement: a part name that is unique to one Office application.
_OOXML_PARTS: tuple[tuple[str, str], ...] = (
    ("word/document.xml", "ooxml-word"),
    ("xl/workbook.xml", "ooxml-excel"),
    ("ppt/presentation.xml", "ooxml-ppt"),
)

# OLE2 refinement: a directory-entry name that is unique to one Office application.
_OLE2_STREAMS: tuple[tuple[str, str], ...] = (
    ("MSProject", "ole2-project"),
    ("Props", "ole2-project"),
    ("WordDocument", "ole2-word"),
    ("Workbook", "ole2-excel"),
    ("Book", "ole2-excel"),
    ("PowerPoint Document", "ole2-ppt"),
)

# Declared extension -> the families its bytes may legitimately carry.
# An extension absent from this table carries NO expectation and is never reported as a mismatch.
_EXPECTED: dict[str, frozenset[str]] = {
    ".png": frozenset({"png"}),
    ".jpg": frozenset({"jpeg"}),
    ".jpeg": frozenset({"jpeg"}),
    ".gif": frozenset({"gif"}),
    ".bmp": frozenset({"bmp"}),
    ".ico": frozenset({"ico"}),
    ".mp4": frozenset({"mp4"}),
    ".pdf": frozenset({"pdf"}),
    ".gz": frozenset({"gzip"}),
    # Acumen Fuse workbook: a gzip container over a proprietary binary record stream (verified —
    # all five decompress to the same UTF-16LE field-name layout beginning "ActivityCount").
    ".afw": frozenset({"gzip"}),
    # A .zip is a zip whatever it holds; OOXML packages are zips.
    ".zip": frozenset({"zip", "ooxml-word", "ooxml-excel", "ooxml-ppt"}),
    ".xlsx": frozenset({"ooxml-excel"}),
    ".xlsm": frozenset({"ooxml-excel"}),
    ".docx": frozenset({"ooxml-word"}),
    ".pptx": frozenset({"ooxml-ppt"}),
    ".xls": frozenset({"ole2-excel"}),
    ".doc": frozenset({"ole2-word"}),
    ".ppt": frozenset({"ole2-ppt"}),
    ".mpp": frozenset({"ole2-project"}),
    ".mpt": frozenset({"ole2-project"}),
    ".xml": frozenset({"xml"}),
    ".aft": frozenset({"xml"}),
    ".mspdi": frozenset({"xml"}),
    ".pmxml": frozenset({"xml"}),
    ".p6xml": frozenset({"xml"}),
    ".html": frozenset({"html"}),
    ".htm": frozenset({"html"}),
    ".json": frozenset({"json"}),
    # Source / prose text: JSON, XML or HTML in one of these is a real content swap, not a
    # stylistic choice, so plain "text" is the only accepted family.
    ".js": frozenset({"text"}),
    ".css": frozenset({"text"}),
    ".py": frozenset({"text"}),
    ".ps1": frozenset({"text"}),
    ".sh": frozenset({"text"}),
    ".md": frozenset({"text"}),
    ".txt": frozenset({"text"}),
    ".csv": frozenset({"text"}),
    ".tsv": frozenset({"text"}),
    ".yml": frozenset({"text"}),
    ".yaml": frozenset({"text"}),
    ".log": frozenset({"text"}),
}


def _ole2_entry_names(data: bytes) -> set[str]:
    """Directory-entry names of an OLE2 (Compound File Binary) document.

    Minimal MS-CFB walk: header -> sector size + DIFAT -> FAT -> directory chain -> 128-byte
    entries. Returns an empty set on any structural surprise rather than guessing.
    """
    if len(data) < 512:
        return set()
    try:
        sector_shift = struct.unpack_from("<H", data, 0x1E)[0]
        if not 7 <= sector_shift <= 16:
            return set()
        sector_size = 1 << sector_shift
        first_dir = struct.unpack_from("<I", data, 0x30)[0]
        difat = list(struct.unpack_from("<109I", data, 0x4C))

        def sector_bytes(idx: int) -> bytes:
            start = 512 + idx * sector_size
            return data[start : start + sector_size]

        fat: list[int] = []
        for fat_sector in difat:
            if fat_sector >= 0xFFFFFFFA:  # FREESECT / ENDOFCHAIN sentinels
                continue
            chunk = sector_bytes(fat_sector)
            if len(chunk) < sector_size:
                break
            fat.extend(struct.unpack_from(f"<{sector_size // 4}I", chunk, 0))

        names: set[str] = set()
        sector, seen = first_dir, 0
        while sector < 0xFFFFFFFA and seen < 4096:
            chunk = sector_bytes(sector)
            if len(chunk) < sector_size:
                break
            for off in range(0, sector_size, 128):
                name_len = struct.unpack_from("<H", chunk, off + 0x40)[0]
                if not 2 <= name_len <= 64:
                    continue
                raw = chunk[off : off + name_len - 2]
                try:
                    name = raw.decode("utf-16-le")
                except UnicodeDecodeError:
                    continue
                if name:
                    names.add(name)
            seen += 1
            if sector >= len(fat):
                break
            sector = fat[sector]
        return names
    except (struct.error, IndexError):  # pragma: no cover - malformed container
        return set()


def _zip_family(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return "zip"
    for part, family in _OOXML_PARTS:
        if part in names:
            return family
    return "zip"


def _ole2_family(data: bytes) -> str:
    names = _ole2_entry_names(data)
    for stream, family in _OLE2_STREAMS:
        if stream in names:
            return family
    return "ole2"


def _text_family(data: bytes) -> str | None:
    """Refine decoded text into json / xml / html, or plain ``text``. ``None`` = not text."""
    try:
        body = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    body = body.lstrip("﻿").lstrip()  # UTF-8 BOM, then leading whitespace
    if not body:
        return "text"
    lowered = body[:256].lower()
    if lowered.startswith("<?xml"):
        return "xml"
    if lowered.startswith("<!doctype html") or lowered.startswith("<html"):
        return "html"
    if body[0] in "{[":
        # Only a *complete* parse counts; a JS object literal that merely opens with "{" is text.
        try:
            json.loads(body)
        except ValueError:
            return "text"
        return "json"
    return "text"


def detect_family(data: bytes) -> str:
    """The content family these bytes actually carry. Never guesses."""
    if not data:
        return "empty"
    for sig, off, family in _SIGNATURES:
        if data[off : off + len(sig)] == sig:
            if family == "zip":
                return _zip_family(data)
            if family == "ole2":
                return _ole2_family(data)
            return family
    refined = _text_family(data)
    return refined if refined is not None else "binary"


def is_mismatch(ext: str, family: str) -> bool:
    """True only when the extension declares a family the bytes decisively contradict.

    ``binary`` is the *absence* of a signature, not the presence of a wrong one, so it is never a
    mismatch. Every other family is a positive identification: ``text`` under ``.png`` means the
    whole file decoded as UTF-8, which no PNG can do.
    """
    expected = _EXPECTED.get(ext)
    if expected is None or family == "binary":
        return False
    return family not in expected


# --------------------------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    path: str
    size: int
    sha256: str
    ext: str
    family: str

    @property
    def mismatch(self) -> bool:
        return is_mismatch(self.ext, self.family)


def tracked_blobs(repo: Path, prefix: str) -> list[tuple[str, str]]:
    """``(path, blob_sha1)`` for every git-tracked file under ``prefix``, sorted by path.

    NUL-separated so the one intake filename carrying an em dash survives verbatim.
    """
    out = subprocess.run(
        ["git", "ls-files", "-s", "-z", "--", prefix],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    rows: list[tuple[str, str]] = []
    for record in out.stdout.decode("utf-8").split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        fields = meta.split()
        if len(fields) >= 2 and path:
            rows.append((path, fields[1]))
    return sorted(rows)


def read_blobs(repo: Path, shas: list[str]) -> Iterator[bytes]:
    """Stream the raw content of each blob, in order, from one ``git cat-file --batch``.

    The manifest hashes the **committed blob**, not the working tree. ``.gitattributes`` sets
    ``* text=auto``, so 128 of these files check out CRLF on Windows and LF on Linux — hashing
    the working tree would make the manifest platform-dependent and fail the gate on the
    operator's own machine. The blob is the byte sequence git actually stores.
    """
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None  # noqa: S101 - Popen contract

    def feed() -> None:
        try:
            proc.stdin.write(("\n".join(shas) + "\n").encode("ascii"))  # type: ignore[union-attr]
            proc.stdin.close()  # type: ignore[union-attr]
        except BrokenPipeError:  # pragma: no cover - git died early
            pass

    # A writer thread is required: feeding every sha before reading would deadlock as soon as
    # git's stdout pipe fills.
    writer = threading.Thread(target=feed, daemon=True)
    writer.start()
    try:
        for sha in shas:
            header = proc.stdout.readline().decode("ascii").split()
            if len(header) != 3 or header[1] != "blob":
                raise RuntimeError(f"git cat-file did not return a blob for {sha}: {header!r}")
            body = proc.stdout.read(int(header[2]))
            proc.stdout.read(1)  # the record's trailing newline
            yield body
    finally:
        writer.join()
        proc.stdout.close()
        proc.wait()


def scan(repo: Path, prefix: str = INTAKE) -> list[Entry]:
    rows = tracked_blobs(repo, prefix)
    blobs = read_blobs(repo, [sha for _, sha in rows])
    return [
        Entry(
            path=path,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            ext=Path(path).suffix.lower(),
            family=detect_family(data),
        )
        for (path, _), data in zip(rows, blobs, strict=True)
    ]


def duplicate_groups(entries: list[Entry]) -> dict[str, list[Entry]]:
    by_hash: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        by_hash[e.sha256].append(e)
    return {h: sorted(v, key=lambda e: e.path) for h, v in by_hash.items() if len(v) > 1}


# --------------------------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------------------------

_PREAMBLE = """# Reference-intake manifest

**Generated — do not hand-edit.** Regenerate with `python tools/intake_manifest.py`;
`tests/guards/test_intake_manifest.py` fails if this file and the tree disagree.

`00_REFERENCE_INTAKE/` holds the **non-CUI** build/parity reference suite the operator committed
under ADR-0151/0152 (CLAUDE.md Law 1 names the boundary: real CUI is only ever a production
schedule loaded into the *deployed* tool). The 2026-08-03 external audit found the bulk upload
arrived with a **name/content rotation** — many files carry an extension their bytes contradict.
This manifest is the measurement of that state, so an *inherited* mislabel can be told apart from
a *new* one, and so a silent content swap in the parity inputs fails a test instead of a hearing.

**Nothing the product reads is affected.** The assets the engine depends on are asserted intact by
the guard test on every run, not merely recorded here.

## The rule

A family is asserted only when the bytes say so — a magic signature, an OOXML part name, an OLE2
stream name, or a *complete* JSON/XML parse. `binary` means "no decisive signal" and is never
called a mismatch; an extension with no standardised signature carries no expectation at all. A
fabricated mismatch would be worse than the drift it chases (Law 2).

### Reconciling with the audit's 89

The 2026-08-03 audit reported **89** mismatches; the rule above yields **99**. The gap is exactly
the two classes the audit did not count, and the arithmetic closes to the file:

| class | files | why this manifest counts it |
| --- | ---: | --- |
| `.XLS` holding an OOXML package | 7 | `.xls` denotes OLE2/BIFF; a zip-packaged workbook is `.xlsx`. Same application, wrong container — still a mislabel. |
| `.json` holding prose | 3 | `.json` is the tool's **own Save format**, so this is the one mislabel a user could actually hit. |

`99 − 7 − 3 = 89`. Neither count is wrong; this one states its rule and a test re-derives it.

### Known divergence — the two `Project5_TAMPERED.mpp` copies

`00_REFERENCE_INTAKE/Project5_TAMPERED.mpp` and `00_REFERENCE_INTAKE/mpp/Project5_TAMPERED.mpp`
are the **same size with different bytes** (102 of 817,152 differ — 0.0125%). The audit recorded
this file as tracked twice and did not report that the copies diverge. Measured, not assumed: the
differing runs sit entirely in the OLE2 **VBA-project storage**; converted through MPXJ both yield
MSPDI identical but for `<CurrentDate>` (the conversion clock), and through the product importer
both yield an equal `Schedule` — 145 tasks, identical calendars, identical CPM timings, the same
4-task critical path (ADR-0112's authoritative 4-stored-critical file) and the same project
finish. **No parity exposure**, and both hashes are pinned below so a future change is not silent.
`mpp/Project5.mpp` is byte-identical to `mpp/Project5_TAMPERED.mpp` — the duplication
`00_REFERENCE_INTAKE/FILE-NAMES.md` documents.
"""


def render_manifest_markdown(entries: list[Entry]) -> str:
    dupes = duplicate_groups(entries)
    mismatched = [e for e in entries if e.mismatch]
    total_bytes = sum(e.size for e in entries)
    by_family = Counter(e.family for e in entries)
    pairs = Counter((e.ext or "(none)", e.family) for e in mismatched)

    lines: list[str] = [_PREAMBLE, "## Summary", ""]
    lines += [
        "| measure | value |",
        "| --- | ---: |",
        f"| tracked files | {len(entries)} |",
        f"| total bytes | {total_bytes:,} |",
        f"| extension&harr;content mismatches | {len(mismatched)} |",
        f"| duplicate-content groups | {len(dupes)} |",
        f"| files in a duplicate group | {sum(len(v) for v in dupes.values())} |",
        "",
        "### Detected content families",
        "",
        "| family | files |",
        "| --- | ---: |",
    ]
    lines += [f"| `{fam}` | {n} |" for fam, n in sorted(by_family.items())]

    lines += [
        "",
        "## Extension&harr;content mismatches",
        "",
        f"{len(mismatched)} tracked files declare an extension their bytes contradict.",
        "",
        "| declared | actual family | files |",
        "| --- | --- | ---: |",
    ]
    lines += [f"| `{ext}` | `{fam}` | {n} |" for (ext, fam), n in sorted(pairs.items())]
    lines += [
        "",
        "| path | size | actual family | sha256 |",
        "| --- | ---: | --- | --- |",
    ]
    lines += [
        f"| `{e.path}` | {e.size:,} | `{e.family}` | `{e.sha256}` |"
        for e in sorted(mismatched, key=lambda e: e.path)
    ]

    lines += [
        "",
        "## Duplicate-content groups",
        "",
        "Files sharing a SHA-256. This is the rotation's signature: a bulk upload that reused one",
        "body under several names, not random corruption.",
        "",
        "| sha256 | files | paths |",
        "| --- | ---: | --- |",
    ]
    for h, group in sorted(dupes.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        joined = "<br>".join(f"`{e.path}`" for e in group)
        lines.append(f"| `{h[:16]}…` | {len(group)} | {joined} |")

    lines += [
        "",
        "## Full inventory",
        "",
        "| path | size | ext | family | mismatch | sha256 |",
        "| --- | ---: | --- | --- | :-: | --- |",
    ]
    lines += [
        f"| `{e.path}` | {e.size:,} | `{e.ext or '(none)'}` | `{e.family}` | "
        f"{'**yes**' if e.mismatch else '—'} | `{e.sha256}` |"
        for e in sorted(entries, key=lambda e: e.path)
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the manifest is stale")
    args = parser.parse_args(argv)

    rendered = render_manifest_markdown(scan(REPO))
    if args.check:
        current = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if current != rendered:
            print(f"{MANIFEST} is stale — run: python tools/intake_manifest.py", file=sys.stderr)
            return 1
        print(f"{MANIFEST} is current")
        return 0
    MANIFEST.write_text(rendered, encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0


def parse_xml_metric_count(path: Path) -> int:
    """`<Metric>` elements in an Acumen `.aft` metric library — used by the guard test."""
    root = ET.parse(path).getroot()  # noqa: S314 - local, operator-supplied reference library
    return len(root.findall(".//Metric"))


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
