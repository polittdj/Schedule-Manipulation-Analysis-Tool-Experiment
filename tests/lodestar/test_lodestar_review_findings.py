"""ADR-0539's security review of LODESTAR (LS-n) — the findings the other LODESTAR test files do
not already pin, each run RED on the reviewed build before its fix.

LS-03 a client stalling its body froze every page (the body was read under the state lock) ·
LS-04 a multipart body of many empty parts cost seconds of CPU per megabyte, under that lock ·
LS-10 ``--help`` / an unknown flag started the server and opened a browser · LS-11 a 64 KB form
cap was reported as "1 MB" · LS-12 a copy saved in a folder whose name holds "site-packages"
could not start · LS-13 the start banner crashed a console that cannot show "—".
"""

from __future__ import annotations

import datetime as dt
import io
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from lodestar_probe import raw_exchange

from schedule_forensics.lodestar.server import LodestarState, serve

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


def test_ls04_an_upload_of_many_parts_is_refused_before_it_is_parsed(port: int) -> None:
    bound = "b0und4ry"
    body = (
        b"".join(
            f'--{bound}\r\nContent-Disposition: form-data; name="x{i}"\r\n\r\nv\r\n'.encode()
            for i in range(20_000)
        )
        + f"--{bound}--\r\n".encode()
    )
    head = (
        f"POST /onepager/upload HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n"
        "Sec-Fetch-Site: same-origin\r\n"
        f"Content-Type: multipart/form-data; boundary={bound}\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    )
    started = time.monotonic()
    raw = raw_exchange(port, head.encode() + body, timeout=60) or b""
    assert raw.startswith(b"HTTP/1.0 400") and b"too many parts" in raw
    assert time.monotonic() - started < 5


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
