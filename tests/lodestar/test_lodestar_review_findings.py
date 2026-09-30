"""ADR-0539's security review of LODESTAR (LS-n) — the findings the other LODESTAR test files do
not already pin, each run RED on the reviewed build before its fix.

LS-03 a client stalling its body froze every page (the body was read under the state lock) ·
LS-04 a multipart body of many empty parts cost seconds of CPU per megabyte, under that lock ·
LS-04's re-review (2026-09-29): SLA-1 the prescan read the boundary one way and the email parser
another, and the parser also walked nested parts — 7 of 13 shapes (and 4 more found beside them)
reached it with thousands of parts; SLA-2 the many-parts pin could not tell "prescan, then parse"
from "parse, then prescan"; SLA-5 the whole-body deadline (408) had no pin ·
LS-10 ``--help`` / an unknown flag started the server and opened a browser · LS-11 a 64 KB form
cap was reported as "1 MB" · LS-12 a copy saved in a folder whose name holds "site-packages"
could not start · LS-13 the start banner crashed a console that cannot show "—".
"""

from __future__ import annotations

import datetime as dt
import email.message
import email.parser
import email.policy
import io
import select
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from lodestar_probe import raw_exchange

from schedule_forensics.lodestar import server as server_mod
from schedule_forensics.lodestar.server import MAX_PARTS, LodestarState, serve

PYZ = Path(__file__).resolve().parents[2] / "lodestar" / "LODESTAR.pyz"


@pytest.fixture
def port() -> Iterator[int]:
    srv = serve(0, LodestarState(onepager_today=dt.date(2027, 3, 1)))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield srv.server_port
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=10)


def _get(port: int) -> tuple[float, bytes]:
    started = time.monotonic()
    raw = raw_exchange(
        port, f"GET /onepager HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode(), timeout=40
    )
    return time.monotonic() - started, (raw or b"")[:15]


def test_ls03_a_client_stalling_its_body_holds_up_only_itself(port: int) -> None:
    stall = socket.create_connection(("127.0.0.1", port))
    try:
        stall.sendall(
            (
                f"POST /onepager/title HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n"
                "Sec-Fetch-Site: same-origin\r\nContent-Type: application/x-www-form-urlencoded\r\n"
                "Content-Length: 100\r\n\r\nti"
            ).encode()
        )
        time.sleep(0.5)
        took, status = _get(port)
    finally:
        stall.close()
    assert status == b"HTTP/1.0 200 OK" and took < 5, (took, status)


@pytest.fixture
def parses(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """A spy on the email parser's entry (``BytesParser.parsebytes`` — the one the server calls,
    and the one ``BytesHeaderParser`` and ``message_from_bytes`` reach): for every FULL parse, how
    many parts it walked (the message itself counted). A header-only read is not a parse of the
    body and is not recorded."""
    walked: list[int] = []
    real = email.parser.BytesParser.parsebytes

    def spy(
        self: email.parser.BytesParser, text: bytes, headersonly: bool = False
    ) -> email.message.Message:
        msg = real(self, text, headersonly)
        if not headersonly:
            walked.append(sum(1 for _part in msg.walk()))
        return msg

    monkeypatch.setattr(email.parser.BytesParser, "parsebytes", spy)
    return walked


def _parts(bound: str, n: int) -> bytes:
    """``n`` minimal form parts and the closing delimiter — the cheapest body per part."""
    return (
        b"".join(
            f'--{bound}\r\nContent-Disposition: form-data; name="x{i}"\r\n\r\nv\r\n'.encode()
            for i in range(n)
        )
        + f"--{bound}--\r\n".encode()
    )


def _post_upload(port: int, ctype: str, body: bytes) -> bytes:
    head = (
        f"POST /onepager/upload HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n"
        "Sec-Fetch-Site: same-origin\r\n"
        f"Content-Type: {ctype}\r\nContent-Length: {len(body)}\r\n\r\n"
    )
    return raw_exchange(port, head.encode() + body, timeout=60) or b""


def _many_parts(port: int) -> tuple[float, bytes]:
    """The LS-04 probe: 20,000 empty parts under a plain boundary — ``(seconds, reply)``."""
    started = time.monotonic()
    raw = _post_upload(port, "multipart/form-data; boundary=b0und4ry", _parts("b0und4ry", 20_000))
    return time.monotonic() - started, raw


def test_ls04_an_upload_of_many_parts_is_refused_before_it_is_parsed(
    port: int, parses: list[int]
) -> None:
    """Refused by name, and the email parser NEVER ran on it (review SLA-2, 2026-09-29: the time
    bound alone passed a server that parsed first and prescanned after — the spy does not)."""
    took, raw = _many_parts(port)
    assert raw.startswith(b"HTTP/1.0 400") and b"too many parts" in raw, raw[:120]
    assert parses == [], "the email parser ran on a body the prescan refuses"
    assert took < 5


def test_mutation_ls04_a_prescan_after_the_parse_is_seen_by_the_spy(
    port: int, parses: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (review SLA-2): the prescan moved AFTER the parse — the reply is still "too many
    parts", but the same spy sees the parser walk all 20,000 parts first."""

    def parse_first(self: server_mod._Handler) -> tuple[dict[str, str], str | None, bytes]:
        ctype = self.headers.get("Content-Type", "")
        body = self._body(server_mod.MAX_UPLOAD_BYTES)
        email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + ctype.encode("latin-1") + b"\r\n\r\n" + body
        )
        server_mod._prescan(ctype, body)
        raise AssertionError("unreachable: the prescan refuses this body")

    monkeypatch.setattr(server_mod._Handler, "_upload", parse_first)
    _took, raw = _many_parts(port)
    assert b"too many parts" in raw
    assert parses and parses[0] > 20_000


#: What each refusal says (the server's own words — the oracle is the SHAPE, below).
_MANY, _TWO = b"too many parts", b"more than one multipart boundary"
_NOT_PLAIN, _NESTED = b"boundary is not a plain one", b"may not itself hold parts"
#: The Content-Type shapes review SLA-1 sent (2026-09-29), where the prescan and the email parser
#: read the boundary differently, each with the refusal that must answer it; then two plain
#: boundaries the parser reads differently only when handed the CLIENT's header (unquoted
#: RFC 2045 specials: a comment is dropped, a ``:`` ends the value) — the witnesses that the
#: parser is handed a header rebuilt from the prescan's boundary. Each body is delimited by the
#: boundary the EMAIL PARSER reads from the client's header — the attacker's best choice.
_SLA1_HEADERS: tuple[tuple[str, bytes], ...] = (
    ("multipart/form-data; boundary=R", _MANY),
    ("multipart/form-data; boundary=R; boundary=DECOY", _TWO),
    ("multipart/form-data; boundary=DECOY; boundary=R", _TWO),
    ("multipart/form-data; boundary*=utf-8''R", _NOT_PLAIN),
    ("multipart/form-data; boundary*0=R; boundary*1=S", _TWO),
    ('multipart/form-data; boundary="R;x"', _NOT_PLAIN),
    ("multipart/form-data; boundary=R x", _NOT_PLAIN),
    ("multipart/form-data; boundary = R", _MANY),
    ('multipart/form-data; boundary="R\\"Q"', _NOT_PLAIN),
    ("multipart/form-data; BOUNDARY=R", _MANY),
    ("multipart/form-data;boundary=R,boundary=S", _TWO),
    ("multipart/form-data; charset=x; boundary=R (comment)", _NOT_PLAIN),
    ("multipart/form-data; boundary=(c)R", b"the upload carried no"),
    ("multipart/form-data; boundary=R:x", b"the upload carried no"),
)
_N = 2_000  # far past MAX_PARTS, and cheap enough that a bypass costs this test well under 1 s


def _nested(content_type: bytes, inner: bytes, *, close: bool = True) -> bytes:
    """ONE outer part (boundary OUTER) whose own headers carry ``content_type``, then ``inner``."""
    return (
        b'--OUTER\r\nContent-Disposition: form-data; name="file"; filename="a.xlsx"\r\n'
        + b"Content-Type: "
        + content_type
        + b"\r\n\r\n"
        + inner
        + (b"\r\n--OUTER--\r\n" if close else b"")
    )


def _sla1_cases() -> list[pytest.ParameterSet]:
    """``(Content-Type, body, the refusal)``: the twelve header shapes and review SLA-1's nested
    part (13), the two rebuilt-header witnesses, and — the class beside the nested part, each
    measured to make the parser walk every inner part — a ``message/rfc822`` wrapper, a
    ``message/delivery-status`` of many header blocks, a nested part left unclosed (the prescan
    once skipped the LAST piece), and an RFC 2047 encoded-word ``multipart/mixed`` the parser
    decodes (a byte search for "multipart" never sees it)."""
    cases = []
    for i, (ctype, says) in enumerate(_SLA1_HEADERS):
        read = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + ctype.encode("latin-1") + b"\r\n\r\n"
        )
        body = _parts(read.get_boundary() or "R", _N)
        cases.append(pytest.param(ctype, body, says, id=f"header-{i}"))
    outer = "multipart/form-data; boundary=OUTER"
    inner = _parts("INNER", _N)
    mixed = b"multipart/mixed; boundary=INNER"
    blocks = b"".join(b"X-A%d: v\r\n\r\n" % i for i in range(_N))
    encoded = b"=?utf-8?b?bXVsdGlwYXJ0L21peGVk?=; boundary=INNER"
    rfc822 = b"Content-Type: " + mixed + b"\r\n\r\n" + inner
    cases += [
        pytest.param(outer, _nested(mixed, inner), _NESTED, id="nested-multipart"),
        pytest.param(outer, _nested(b"message/rfc822", rfc822), _NESTED, id="rfc822"),
        pytest.param(
            outer, _nested(b"message/delivery-status", blocks), _NESTED, id="delivery-status"
        ),
        pytest.param(outer, _nested(mixed, inner, close=False), _NESTED, id="nested-unclosed"),
        pytest.param(outer, _nested(encoded, inner), _NESTED, id="encoded-word"),
    ]
    return cases


@pytest.mark.parametrize(("ctype", "body", "says"), _sla1_cases())
def test_ls04_no_boundary_shape_or_nested_part_reaches_the_parser_with_many_parts(
    port: int, parses: list[int], ctype: str, body: bytes, says: bytes
) -> None:
    """Review SLA-1: every shape is refused (400) before the parser, or parsed with at most
    :data:`MAX_PARTS` parts — never walked part by part — and each is refused by the rule written
    for it (so no one rule can be dropped unseen)."""
    raw = _post_upload(port, ctype, body)
    assert all(n <= MAX_PARTS + 1 for n in parses), parses
    assert raw.startswith(b"HTTP/1.0 400") and says in raw, raw[:160]


def test_ls04_a_plain_browser_upload_still_parses_through_the_rebuilt_header(
    port: int, parses: list[int]
) -> None:
    """The class the fix must not break: Chrome's and Firefox's own boundaries, a quoted one, and
    one of every RFC 2046 character (with an inner space, quoted) — each body reaches the parser
    and the route (303)."""
    every = "0189AZaz'()+_,-./:=? x"
    for ctype, bound in (
        ("multipart/form-data; boundary=----WebKitFormBoundaryAbC123xYz", None),
        ("multipart/form-data; boundary=----geckoformboundary9f8e7d6c5b4a", None),
        ('multipart/form-data; boundary="quoted-boundary"', "quoted-boundary"),
        (f'multipart/form-data; boundary="{every}"', every),
    ):
        b = bound or ctype.split("=", 1)[1]
        body = (
            f'--{b}\r\nContent-Disposition: form-data; name="layout"\r\n\r\nauto\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="x.xlsx"\r\n'
            "Content-Type: application/octet-stream\r\n\r\nnot a workbook\r\n"
            f"--{b}--\r\n"
        ).encode()
        raw = _post_upload(port, ctype, body)
        assert raw.startswith(b"HTTP/1.0 303"), (ctype, raw[:120])
    assert parses == [3, 3, 3, 3], parses


def _trickle(port: int, budget: float) -> tuple[float, bytes | None]:
    """A form POST declaring 100 body bytes and sending ONE every 0.3 s, until the server
    answers or ``budget`` seconds pass: ``(seconds, reply)`` — ``None``: no answer (the server
    is still waiting for the body)."""
    body = b"title=" + b"t" * 94
    head = (
        f"POST /onepager/title HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n"
        "Sec-Fetch-Site: same-origin\r\nContent-Type: application/x-www-form-urlencoded\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode()
    sock = socket.create_connection(("127.0.0.1", port), timeout=budget + 5)
    started = time.monotonic()
    try:
        sock.sendall(head)
        for byte in body:
            if time.monotonic() - started > budget:
                break
            if select.select([sock], [], [], 0.3)[0]:
                break
            try:
                sock.sendall(bytes([byte]))
            except OSError:
                break
        left = budget - (time.monotonic() - started)
        if left <= 0 or not select.select([sock], [], [], left)[0]:
            return time.monotonic() - started, None
        took = time.monotonic() - started
        got = b""
        while chunk := sock.recv(65536):
            got += chunk
        return took, got
    finally:
        sock.close()


def test_ls03_a_body_trickled_past_the_whole_body_deadline_is_refused(
    port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review SLA-5: one byte every 0.3 s never trips the per-read timeout — only the deadline
    for the WHOLE body refuses it: 408 "took too long", about a second in (deadline 1 s here)."""
    monkeypatch.setattr(server_mod, "BODY_DEADLINE_S", 1)
    took, raw = _trickle(port, budget=10)
    assert raw is not None, "no answer: the server kept reading the trickle"
    assert raw.startswith(b"HTTP/1.0 408") and b"took too long" in raw, raw[:120]
    assert took < 6, took


def test_mutation_ls03_without_the_deadline_the_server_takes_the_trickle(
    port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (review SLA-5): ``_body`` with the deadline check deleted — the same probe gets no
    answer inside its budget: the thread is held for as long as the client likes."""

    def no_deadline(self: server_mod._Handler, cap: int) -> bytes:
        size = int(self.headers.get("Content-Length", "0"))
        chunks: list[bytes] = []
        while size > 0:
            chunk = self.rfile.read1(min(size, 65536))
            if not chunk:
                raise server_mod._Refused(400, "the request body ended early")
            chunks.append(chunk)
            size -= len(chunk)
        return b"".join(chunks)

    monkeypatch.setattr(server_mod, "BODY_DEADLINE_S", 1)
    monkeypatch.setattr(server_mod._Handler, "_body", no_deadline)
    assert _trickle(port, budget=4)[1] is None


def test_ls11_a_form_over_its_cap_is_refused_in_the_right_unit(port: int) -> None:
    big = b"title=" + b"x" * 100_000
    head = (
        f"POST /onepager/title HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n"
        "Sec-Fetch-Site: same-origin\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        f"Content-Length: {len(big)}\r\n\r\n"
    )
    raw = raw_exchange(port, head.encode() + big, timeout=20) or b""
    assert b"over 64 KB" in raw and b"MB" not in raw.split(b"\r\n\r\n", 1)[-1]


def test_ls10_help_and_an_unknown_flag_never_start_the_server() -> None:
    usage = subprocess.run(
        [sys.executable, "-I", str(PYZ), "--help"], capture_output=True, text=True, timeout=30
    )
    assert usage.returncode == 0 and usage.stdout.startswith("usage: LODESTAR")
    typo = subprocess.run(
        [sys.executable, "-I", str(PYZ), "--no-browsr"], capture_output=True, text=True, timeout=30
    )
    assert typo.returncode == 2 and "unrecognized arguments" in typo.stderr
    assert "Running at" not in usage.stdout + typo.stdout


def test_ls12_a_copy_in_a_folder_named_site_packages_still_starts(tmp_path: Path) -> None:
    folder = tmp_path / "shared site-packages review"
    folder.mkdir()
    copy = folder / "LODESTAR.pyz"
    copy.write_bytes(PYZ.read_bytes())
    got = subprocess.run(
        [sys.executable, "-I", str(copy), "--version"], capture_output=True, text=True, timeout=30
    )
    assert got.returncode == 0 and got.stdout.startswith("LODESTAR "), got.stderr[-300:]


def test_ls13_the_banner_never_crashes_a_console_that_cannot_show_a_dash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import schedule_forensics.lodestar.__main__ as entry

    ascii_out = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "stdout", ascii_out)
    entry._say(entry.banner("http://127.0.0.1:1/onepager"))
    ascii_out.flush()
    text = ascii_out.buffer.getvalue().decode("ascii")
    assert text.startswith("LODESTAR ") and "david.j.politte@nasa.gov" in text
