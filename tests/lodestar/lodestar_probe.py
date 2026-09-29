"""What the LODESTAR tests share (ADR-0539): an HTTP client that can send exactly the request a
test means (a foreign Host, no Host, no Content-Length, a chunked header), a raw-socket exchange
for the framing tests, a multipart body the way a browser builds one, and readers for a deck.

Client code is allowed here: this is a test helper, never shipped (the Law-1 transport census
scans ``src/`` only). Every call is bounded by a timeout.

The oracle values are LITERALS typed from the operator's request (2026-09-29), not imported from
``lodestar_shell`` — a test that read the credit out of the module it checks could never catch
that module saying the wrong thing.
"""

from __future__ import annotations

import http.client
import io
import socket
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlencode

from web.onepager_twin import twin_xlsx

#: Who built LODESTAR and where to reach him — the operator's own words (not the module's).
AUTHOR = "David Politte"
CONTACT = "david.j.politte@nasa.gov"
MAILTO = f"mailto:{CONTACT}"

#: The list layout the operator asked for: C start · D finish · E complete (ADR-0539).
HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")
ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "4/15/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Ship", "7/15/2027", "7/15/2027", ""),
)
#: The compare page's PRIOR list: Build slipped, no Ship yet.
PRIOR_ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "3/31/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
)

_BOUNDARY = "----lodestar-probe-7d3f9c"
_PML = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@dataclass(frozen=True)
class Reply:
    """One HTTP response: status, protocol version (10 / 11), headers (lower-cased names)."""

    status: int
    version: int
    headers: dict[str, str]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def request(
    port: int,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: Iterable[tuple[str, str]] = (),
    no_host: bool = False,
    content_length: bool = True,
    timeout: float = 15.0,
) -> Reply:
    """Send exactly this request. ``http.client`` adds ``Host: 127.0.0.1:<port>`` unless the
    headers carry their own Host (or ``no_host``); a ``Content-Length`` is added for a body
    unless ``content_length`` is False or the headers carry one or a Transfer-Encoding."""
    hdrs = list(headers)
    names = {k.lower() for k, _v in hdrs}
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.putrequest(
            method, path, skip_host=no_host or "host" in names, skip_accept_encoding=True
        )
        for key, value in hdrs:
            conn.putheader(key, value)
        framed = {"content-length", "transfer-encoding"} & names
        if body is not None and content_length and not framed:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        resp = conn.getresponse()
        return Reply(
            resp.status, resp.version, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
        )
    finally:
        conn.close()


def form(
    port: int,
    path: str,
    fields: dict[str, str],
    *,
    headers: Iterable[tuple[str, str]] = (),
    no_host: bool = False,
    timeout: float = 15.0,
) -> Reply:
    """A urlencoded POST — the page's own forms."""
    return request(
        port,
        "POST",
        path,
        body=urlencode(fields).encode(),
        headers=[("Content-Type", "application/x-www-form-urlencoded"), *headers],
        no_host=no_host,
        timeout=timeout,
    )


def multipart(fields: dict[str, str], filename: str, data: bytes) -> tuple[bytes, str]:
    """``(body, content type)`` of a multipart form with one file part — a browser's upload."""
    parts = [
        f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, v in fields.items()
    ]
    parts.append(
        f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"'
        "\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
        + data
        + b"\r\n"
    )
    parts.append(f"--{_BOUNDARY}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={_BOUNDARY}"


def upload(
    port: int,
    path: str,
    rows: tuple[tuple[object, ...], ...],
    filename: str,
    **fields: str,
) -> Reply:
    """Upload ``rows`` as a twin workbook (Excel's own cell encoding) to ``path``."""
    body, ctype = multipart(fields, filename, twin_xlsx(rows, omit_blank=True))
    return request(port, "POST", path, body=body, headers=[("Content-Type", ctype)])


def raw_exchange(port: int, data: bytes, *, timeout: float) -> bytes | None:
    """Send ``data`` on one fresh connection, read until the server closes it. ``None`` when the
    server sent nothing for ``timeout`` seconds (it is WAITING — for a body, say)."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    try:
        sock.sendall(data)
        got = b""
        while True:
            try:
                chunk = sock.recv(65536)
            except TimeoutError:
                return got or None
            if not chunk:
                return got
            got += chunk
    finally:
        sock.close()


def deck_shapes(pptx: bytes) -> dict[str, str]:
    """``shape name -> its text`` for every named shape or group on the deck's one slide."""
    with zipfile.ZipFile(io.BytesIO(pptx)) as zf:
        root = ET.fromstring(zf.read("ppt/slides/slide1.xml"))
    out: dict[str, str] = {}
    for holder in (*root.iter(f"{_PML}sp"), *root.iter(f"{_PML}grpSp")):
        c_nv = holder.find(f".//{_PML}cNvPr")
        if c_nv is None or not c_nv.get("name"):
            continue
        text = "".join(t.text or "" for t in holder.iter(f"{_A}t"))
        out.setdefault(str(c_nv.get("name")), text)
    return out


def deck_members(pptx: bytes) -> dict[str, bytes]:
    """Every part of a deck (or any OOXML package) by name."""
    with zipfile.ZipFile(io.BytesIO(pptx)) as zf:
        return {name: zf.read(name) for name in zf.namelist()}
