"""Std-lib reader for the LODESTAR session payload a One-Pager PDF carries (ADR-0544).

:func:`read_pdf_payload` finds the embedded ``lodestar-session.json`` that
:mod:`schedule_forensics.reports.pdf` attaches (an ``/EmbeddedFile`` stream in the catalog's
``/EmbeddedFiles`` name tree) and hands back its bytes — the ONE payload every carrier shares,
opaque here — or ``None`` when the file carries none: a browser-printed PDF, a scan, a PDF
whose attachment is some other JSON. It is a byte scanner, not a PDF parser, on purpose: a
full object parser is a large surface (object streams, encryption, incremental updates) for a
file this program wrote itself, and what matters is being TOLERANT of what a re-save does to
the bytes. The refuter's probe (2026-10-01) measured the two ways a re-save moves the
goalposts, and both are covered here:

* **whitespace** — Acrobat and MuPDF write ``/Type/EmbeddedFile/Filter/FlateDecode`` with no
  spaces, so every match is ``\\s*``-agnostic and the dictionary's key ORDER is not assumed;
* **``/Length``** — direct (``/Length 123``) or indirect (``/Length 7 0 R``, the object
  resolved), and when neither resolves the data is taken up to ``endstream``.

Bounded work: an input past :data:`MAX_PDF_BYTES` is refused outright, an attachment that would
inflate past :data:`MAX_PAYLOAD_BYTES` is dropped mid-inflate (``decompressobj`` with a length
cap — never a full ``zlib.decompress`` of hostile bytes), at most :data:`MAX_CANDIDATES`
attachment streams are examined, and every pattern is a literal with ``\\s*`` joints — no
nested quantifiers, so no catastrophic backtracking.

:func:`check_xref` is the writer's self-check: every ``n`` entry of the classic cross-reference
table must point at exactly ``N G obj``, and ``startxref`` at ``xref``. The writer runs it on
every file before the bytes leave; the tests run it on a deliberately shifted table.
"""

from __future__ import annotations

import json
import re
import zlib

#: An input larger than this is refused unread: a One-Pager PDF is tens of kilobytes.
MAX_PDF_BYTES = 64 * 1024 * 1024
#: An attachment that inflates past this is not a session payload.
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
#: How many ``/EmbeddedFile`` streams are examined before giving up.
MAX_CANDIDATES = 64
#: The key the session payload's top-level object carries (``reports/session_payload.py``).
PAYLOAD_KEY = "lodestar"

_HEADER_RE = re.compile(rb"%PDF-\d\.\d")
#: ``/Type /EmbeddedFile`` with any whitespace between — and NOT ``/EmbeddedFiles`` (the name
#: tree's key in the catalog), hence the word boundary.
_EMBEDDED_RE = re.compile(rb"/Type\s*/EmbeddedFile\b")
#: The ``stream`` keyword and its end-of-line (CRLF or LF per the spec; a bare CR tolerated).
_STREAM_RE = re.compile(rb"\bstream(?:\r\n|\n|\r)")
#: ``/Length N`` direct, or ``/Length N G R`` indirect.
_LENGTH_RE = re.compile(rb"/Length\s*(\d+)(?:\s+(\d+)\s+R)?")
#: ``/Filter /Name`` or ``/Filter [/A /B]``.
_FILTER_RE = re.compile(rb"/Filter\s*(?:/([A-Za-z0-9]+)|\[([^\]]{0,200})\])")
_NAME_RE = re.compile(rb"/([A-Za-z0-9]+)")
_XREF_ENTRY_RE = re.compile(rb"(\d{10})\s(\d{5})\s([nf])")
_SUBSECTION_RE = re.compile(rb"\s*(\d+)\s+(\d+)\s*")
_STARTXREF_RE = re.compile(rb"startxref\s+(\d+)")


def read_pdf_payload(data: bytes) -> bytes | None:
    """The LODESTAR session payload embedded in ``data``, or ``None`` when there is none.

    Every ``/Type /EmbeddedFile`` stream is tried in file order (whitespace- and
    key-order-agnostic, direct or indirect ``/Length``, Flate-coded or raw); the first whose
    bytes are UTF-8 JSON with a top-level :data:`PAYLOAD_KEY` wins. A stream with any other
    filter, a broken inflate, a non-JSON body or a JSON body without the key is skipped, never
    raised on."""
    if len(data) > MAX_PDF_BYTES or not _HEADER_RE.search(data, 0, 1024):
        return None
    for n, m in enumerate(_EMBEDDED_RE.finditer(data)):
        if n >= MAX_CANDIDATES:
            break
        body = _stream_body(data, m.start())
        if body is not None and _is_payload(body):
            return body
    return None


def _stream_body(data: bytes, at: int) -> bytes | None:
    """The decoded bytes of the stream object whose dictionary contains offset ``at``."""
    obj_at = data.rfind(b"obj", 0, at)
    if obj_at < 0:
        return None
    stream = _STREAM_RE.search(data, at)
    end_obj = data.find(b"endobj", at)
    if stream is None or (0 <= end_obj < stream.start()):
        return None  # a dictionary with no stream, or the stream of some later object
    dictionary = data[obj_at + 3 : stream.start()]
    start = stream.end()
    length = _length(data, dictionary)
    raw: bytes
    if length is not None and start + length <= len(data) and _ends_stream(data, start + length):
        raw = data[start : start + length]
    else:
        end = data.find(b"endstream", start)
        if end < 0:
            return None
        raw = data[start:end]
        for eol in (b"\r\n", b"\n", b"\r"):
            if raw.endswith(eol):
                raw = raw[: -len(eol)]
                break
    filters = _filters(dictionary)
    if not filters:
        return raw if len(raw) <= MAX_PAYLOAD_BYTES else None
    if filters != [b"FlateDecode"]:
        return None
    return _inflate(raw)


def _ends_stream(data: bytes, at: int) -> bool:
    """Whether ``endstream`` follows ``at`` after at most an end-of-line — the test that a
    declared ``/Length`` is honest."""
    tail = data[at : at + 2]
    skip = len(tail) - len(tail.lstrip(b"\r\n"))
    return data.startswith(b"endstream", at + skip)


def _length(data: bytes, dictionary: bytes) -> int | None:
    m = _LENGTH_RE.search(dictionary)
    if m is None:
        return None
    if m.group(2) is None:
        return int(m.group(1))
    ref = re.compile(
        rb"(?<![0-9])" + m.group(1) + rb"\s+" + m.group(2) + rb"\s+obj\s*(\d+)\s*endobj"
    )
    hit = ref.search(data)
    return int(hit.group(1)) if hit else None


def _filters(dictionary: bytes) -> list[bytes]:
    m = _FILTER_RE.search(dictionary)
    if m is None:
        return []
    if m.group(1) is not None:
        return [m.group(1)]
    return _NAME_RE.findall(m.group(2))


def _inflate(raw: bytes) -> bytes | None:
    d = zlib.decompressobj()
    try:
        out = d.decompress(raw, MAX_PAYLOAD_BYTES + 1)
    except zlib.error:
        return None
    if len(out) > MAX_PAYLOAD_BYTES:
        return None
    return out


def _is_payload(body: bytes) -> bool:
    try:
        obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return isinstance(obj, dict) and PAYLOAD_KEY in obj


def check_xref(data: bytes) -> str:
    """``""`` when the file's LAST classic cross-reference table is exact — ``startxref`` points
    at ``xref`` and every in-use entry at its ``N G obj`` — else one sentence naming the first
    thing wrong. A cross-reference STREAM (PDF 1.5) is named, not checked: this is the writer's
    own self-check, and the writer emits a classic table."""
    marks = list(_STARTXREF_RE.finditer(data))
    if not marks:
        return "no startxref"
    at = int(marks[-1].group(1))
    if not data.startswith(b"xref", at):
        if re.match(rb"\s*\d+\s+\d+\s+obj", data[at : at + 40]):
            return "cross-reference stream, not a classic table"
        return f"startxref {at} does not point at 'xref'"
    pos = at + 4
    trailer = data.find(b"trailer", pos)
    if trailer < 0:
        return "no trailer after xref"
    while pos < trailer:
        sub = _SUBSECTION_RE.match(data, pos, trailer)
        if sub is None:
            return f"unreadable xref subsection header at {pos}"
        first, count = int(sub.group(1)), int(sub.group(2))
        pos = sub.end()
        for i in range(count):
            entry = _XREF_ENTRY_RE.match(data, pos, trailer)
            if entry is None:
                return f"unreadable xref entry for object {first + i} at {pos}"
            pos = entry.end()
            while pos < trailer and data[pos : pos + 1] in (b" ", b"\r", b"\n"):
                pos += 1
            if entry.group(3) != b"n":
                continue
            off, gen = int(entry.group(1)), int(entry.group(2))
            head = rb"\s*" + str(first + i).encode() + rb"\s+" + str(gen).encode() + rb"\s+obj"
            if not re.match(head, data[off : off + 40]):
                return f"xref entry for object {first + i} points at {off}, not at its header"
    return ""
