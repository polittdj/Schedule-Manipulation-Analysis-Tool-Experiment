"""Read a LODESTAR deck back — the import side of the PowerPoint carrier (ADR-0544).

:mod:`~.pptx` writes the session's record into a deck two ways: the record's bytes in a custom
XML part, and the same facts as alt text (``descr``) on the Title shape and every item shape.
This module reads both back, and says by name when it finds neither:

* the **custom XML part** is found by its NAMESPACE (``urn:lodestar:session``), never by a part
  name — a program that re-saves the deck may renumber ``item1.xml`` or move it;
* the **alt text** is the fallback for a deck whose re-save dropped the custom XML part (a part
  an editor does not understand is the first thing it loses; LibreOffice's behaviour is
  UNVERIFIED in this container, and CI's interop test measures it): the Title's
  ``LODESTAR slide: {json}`` gives the settings, each ``LODESTAR item: {json}`` an item;
* a deck that is not a zip, not a presentation, or carries neither is reported in
  :attr:`PptxRead.problem` — one sentence, never an exception for the caller to catch.

Hardened the way :mod:`~.xlsx_read` is, because the bytes come from a drop: a part carrying a
DTD or an entity declaration is refused (XXE), every part read counts against one decompression
budget (a zip bomb), and member names are looked up exactly. Std-lib only (``zipfile`` +
``xml.etree``), so LODESTAR carries it verbatim. Nothing here restores a session — the caller
hands the payload to :mod:`~.session_payload` and the fallback facts to its own rebuild.
"""

from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET  # nosec B405  # hardened in _parse_xml (DTD/entity rejected)
import zipfile
from dataclasses import dataclass, field
from typing import Any

from schedule_forensics.reports.pptx import CUSTOM_XML_NS, ITEM_DESCR, SETTINGS_DESCR

#: Cap on the TOTAL decompressed bytes read from one deck (the parts this reader opens, summed —
#: media and the parts it never opens cost nothing). A LODESTAR deck's parts are tens of
#: kilobytes; a PowerPoint re-save of one, a few hundred. Sixty-four megabytes is past any
#: slide a human made and far short of what a bomb inflates to.
_MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024
#: The presentation part every ``.pptx`` carries — its absence means "not a deck".
_PRESENTATION_PART = "ppt/presentation.xml"
#: A slide part, by its ECMA-376 name; sorted by number so slide 2 precedes slide 10.
_SLIDE_RE = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
#: A custom XML item part (its properties and rels parts are not candidates).
_CUSTOM_XML_RE = re.compile(r"^customXml/item\d*\.xml$")
_PML_CNVPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"
_NO_DATA = "the deck carries no LODESTAR data (no session part and no LODESTAR alt text)"


class PptxReadError(ValueError):
    """One part of the deck could not be read safely; the message names why."""


@dataclass(frozen=True)
class PptxRead:
    """What a deck gave back. ``payload`` is the custom XML part's record (bytes, as written);
    ``settings`` the Title shape's record and ``items`` every item shape's, each as its JSON
    object; ``problem`` is ``""`` for a LODESTAR deck and one sentence otherwise. ``notes`` name
    what was skipped or missing (an unreadable part, the absent session part) so the caller can
    say so — a restore from the fallback is never silent about being one."""

    payload: bytes | None
    settings: dict[str, Any] | None
    items: list[dict[str, Any]]
    problem: str
    notes: tuple[str, ...] = field(default=())


def _parse_xml(data: bytes) -> ET.Element:
    """Parse one part, hardened as the workbook reader's is: a DTD or entity declaration is
    refused before ElementTree sees it, and a malformed part is a named error."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise PptxReadError("a part with a DTD or entity declaration is rejected (XXE defense)")
    try:
        return ET.fromstring(data)  # nosec B314  # DTD/entity decls rejected above
    except ET.ParseError as exc:
        raise PptxReadError(f"malformed XML part: {exc}") from exc


class _Budget:
    """One decompression budget over every part read. ``zf.open`` streams, so reading
    ``remaining + 1`` bounds memory whatever the member's header claims."""

    def __init__(self, zf: zipfile.ZipFile) -> None:
        self._zf = zf
        self._remaining = _MAX_DECOMPRESSED_BYTES

    def read(self, name: str) -> bytes:
        with self._zf.open(name) as fh:
            chunk = fh.read(self._remaining + 1)
        if len(chunk) > self._remaining:
            raise PptxReadError("the deck decompresses past the size cap (possible zip bomb)")
        self._remaining -= len(chunk)
        return chunk


def _record(text: str, prefix: str) -> dict[str, Any] | None:
    """The JSON object after ``prefix`` in one alt text, or ``None`` when it is not one."""
    try:
        got = json.loads(text[len(prefix) :])
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def _slide_number(name: str) -> int:
    m = _SLIDE_RE.match(name)
    return int(m.group(1)) if m else 0


def read_pptx(data: bytes) -> PptxRead:
    """Read a deck's LODESTAR record(s) — see the module doc for what is read, from where, and
    how a deck that carries none is reported. Never raises on the bytes a drop can hand it."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return PptxRead(None, None, [], "not a PowerPoint deck (not a zip package)")
    with zf:
        names = zf.namelist()
        if _PRESENTATION_PART not in names:
            return PptxRead(None, None, [], "not a PowerPoint deck (no ppt/presentation.xml)")
        budget = _Budget(zf)
        notes: list[str] = []
        try:
            payload = _payload(budget, names, notes)
            settings, items = _alt_text(budget, names, notes)
        except PptxReadError as exc:
            # only the budget escapes the per-part handling: a bomb ends the read, by name
            return PptxRead(None, None, [], str(exc))
    if payload is None and settings is None and not items:
        return PptxRead(None, None, [], _NO_DATA, tuple(notes))
    if payload is None:
        notes.append("the deck's session part is absent — the slide is read from its alt text")
    return PptxRead(payload, settings, items, "", tuple(notes))


def _payload(budget: _Budget, names: list[str], notes: list[str]) -> bytes | None:
    """The first custom XML item whose root is ``{urn:lodestar:session}lodestar`` — its text as
    UTF-8 bytes. Candidates are every ``customXml/item*.xml`` member, in name order; one that
    cannot be parsed is noted and the next tried."""
    for name in sorted(n for n in names if _CUSTOM_XML_RE.match(n)):
        raw = budget.read(name)  # the budget's refusal ends the whole read; only a parse is skipped
        try:
            root = _parse_xml(raw)
        except PptxReadError as exc:
            notes.append(f"{name}: {exc}")
            continue
        if root.tag == f"{{{CUSTOM_XML_NS}}}lodestar":
            return (root.text or "").encode("utf-8")
    return None


def _alt_text(
    budget: _Budget, names: list[str], notes: list[str]
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The settings (the FIRST ``LODESTAR slide:`` alt text) and every ``LODESTAR item:`` alt
    text, over every slide part in slide order. A record that is not a JSON object is counted
    and noted, never guessed at."""
    settings: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    unread = 0
    for name in sorted((n for n in names if _SLIDE_RE.match(n)), key=_slide_number):
        raw = budget.read(name)  # the budget's refusal ends the whole read; only a parse is skipped
        try:
            root = _parse_xml(raw)
        except PptxReadError as exc:
            notes.append(f"{name}: {exc}")
            continue
        for el in root.iter(_PML_CNVPR):
            descr = el.get("descr") or ""
            if descr.startswith(SETTINGS_DESCR):
                got = _record(descr, SETTINGS_DESCR)
                if got is None:
                    unread += 1
                elif settings is None:
                    settings = got
            elif descr.startswith(ITEM_DESCR):
                got = _record(descr, ITEM_DESCR)
                if got is None:
                    unread += 1
                else:
                    items.append(got)
    if unread:
        notes.append(f"{unread} LODESTAR alt-text record(s) could not be read and were skipped")
    return settings, items
