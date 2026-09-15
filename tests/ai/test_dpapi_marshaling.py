"""The Windows DPAPI branch of the key store, exercised as CODE on every platform (OR-17).

``config_store._dpapi_protect`` / ``_dpapi_unprotect`` are two Win32 calls behind ctypes, marked
``pragma: no cover`` since ADR-0404 and pinned by nothing: every store test injects a lambda
protector, so the struct layout, the buffer lifetime, the length passed, the flags, the read of
the output blob and the ``LocalFree`` were never executed by a test. The field then reported a
saved gateway key the gateway refuses (OR-16 / OR-17) — and a key that reads "saved" but does
not survive the wrap is exactly what a marshaling defect would produce. Here a FAKE ``crypt32``
stands in for Windows: it reads the input blob through the same pointer and length the real
``CryptProtectData`` would, at call time, so a freed temporary buffer, an off-by-one length or a
wrong field layout surfaces as a wrong byte string. The real Win32 call is measured on a real
Windows runner by the installer-smoke workflow's DPAPI step (ADR-0493); this module proves the
Python around it.
"""

from __future__ import annotations

import base64
import ctypes
import json
import types
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.ai import config_store as cs
from schedule_forensics.ai.backend import AIConfig

ENDPOINT = "https://proxy.fast.luna.nasa.gov"


class _FakeCrypt32:
    """A stand-in for ``crypt32`` + ``kernel32`` with the two DPAPI entry points and ``LocalFree``.

    ``wrap`` is deliberately not the identity (reversed bytes inside a frame) so a passthrough
    or a half-read shows; a blob outside the frame is REFUSED like a tampered real blob.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []
        self.read_lengths: list[int] = []
        self._keep: list[Any] = []  # output buffers must outlive the caller's string_at

    @staticmethod
    def wrap(raw: bytes) -> bytes:
        return b"FAKE-DPAPI[" + raw[::-1] + b"]"

    @staticmethod
    def unwrap(blob: bytes) -> bytes:
        if not (blob.startswith(b"FAKE-DPAPI[") and blob.endswith(b"]")):
            raise ValueError("not a wrapped blob")
        return blob[len(b"FAKE-DPAPI[") : -1][::-1]

    def _read(self, byref_arg: Any) -> bytes:
        blob = byref_arg._obj
        import gc

        gc.collect()  # a temporary buffer the caller failed to keep alive dies here
        self.read_lengths.append(int(blob.cbData))
        return ctypes.string_at(blob.pbData, blob.cbData)

    def _write(self, byref_arg: Any, data: bytes) -> None:
        out = byref_arg._obj
        buf = ctypes.create_string_buffer(data, len(data))
        self._keep.append(buf)
        out.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
        out.cbData = len(data)

    # the seven-argument Win32 signatures, positionally, exactly as the store calls them
    def CryptProtectData(
        self, pin: Any, desc: Any, entropy: Any, reserved: Any, prompt: Any, flags: int, pout: Any
    ) -> int:
        self.calls.append(("protect", flags))
        self._write(pout, self.wrap(self._read(pin)))
        return 1

    def CryptUnprotectData(
        self, pin: Any, desc: Any, entropy: Any, reserved: Any, prompt: Any, flags: int, pout: Any
    ) -> int:
        self.calls.append(("unprotect", flags))
        try:
            plain = self.unwrap(self._read(pin))
        except ValueError:
            return 0  # the real call returns FALSE on a tampered / foreign blob
        self._write(pout, plain)
        return 1

    def LocalFree(self, handle: Any) -> None:
        self.calls.append(("localfree", None))


@pytest.fixture
def crypt32(monkeypatch: pytest.MonkeyPatch) -> _FakeCrypt32:
    fake = _FakeCrypt32()
    windll = types.SimpleNamespace(crypt32=fake, kernel32=fake)
    # ``ctypes.windll`` does not exist on POSIX; on Windows this shadows the real one
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)
    return fake


@pytest.mark.parametrize(
    "key",
    [
        b"k",
        b"k" * 25,
        b"sk-nasa-hub-KEY-0123456789-" + b"x" * 40,
        "clé-ünïcode".encode(),
        b"y" * 4096,
    ],
    ids=["one-byte", "25-chars", "67-chars", "utf-8", "4-KiB"],
)
def test_the_wrap_reads_every_byte_and_the_unwrap_gives_them_back(
    crypt32: _FakeCrypt32, key: bytes
) -> None:
    wrapped = cs._dpapi_protect(key)
    assert wrapped == crypt32.wrap(key)  # the fake saw the whole key, nothing else
    assert crypt32.read_lengths[-1] == len(key)  # cbData is the key's length, not len - 1
    assert cs._dpapi_unprotect(wrapped) == key


def test_user_scope_flags_and_one_local_free_per_call(crypt32: _FakeCrypt32) -> None:
    cs._dpapi_unprotect(cs._dpapi_protect(b"k" * 25))
    assert [c[0] for c in crypt32.calls] == ["protect", "localfree", "unprotect", "localfree"]
    assert all(flags == 0 for kind, flags in crypt32.calls if kind != "localfree")


def test_a_tampered_or_foreign_blob_is_refused_not_garbled(crypt32: _FakeCrypt32) -> None:
    wrapped = bytearray(cs._dpapi_protect(b"k" * 25))
    wrapped[-1] ^= 0x5A  # the frame no longer closes: the "CryptUnprotectData failed" path
    with pytest.raises(OSError, match="CryptUnprotectData failed"):
        cs._dpapi_unprotect(bytes(wrapped))
    with pytest.raises(OSError):
        cs._dpapi_unprotect(b"not a blob at all")


def test_the_store_over_the_dpapi_functions_never_writes_plaintext_and_round_trips(
    crypt32: _FakeCrypt32, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Windows wiring end to end: the store's protector IS the DPAPI function pair (not an
    injected lambda), the file carries base64 of the wrapped bytes under the dpapi field, and a
    flipped byte in that field comes up keyless while the other credential survives."""
    monkeypatch.setattr(cs, "_protect_key", cs._dpapi_protect)
    monkeypatch.setattr(cs, "_unprotect_key", cs._dpapi_unprotect)
    monkeypatch.setattr(cs, "_KEY_FIELD", "gateway_api_key_dpapi")
    monkeypatch.setattr(cs, "_OPENAI_KEY_FIELD", "openai_api_key_dpapi")
    path = tmp_path / "ai-settings.json"
    key = "k" * 25
    cs.save_ai_config(
        AIConfig(
            backend="gateway",
            gateway_endpoint=ENDPOINT,
            gateway_approved=True,
            gateway_api_key=key,
            openai_api_key="lm-" + key,
        ),
        path,
    )
    raw = path.read_text(encoding="utf-8")
    assert key not in raw and "gateway_api_key_plain" not in raw
    doc = json.loads(raw)
    assert base64.b64decode(doc["gateway_api_key_dpapi"]) == crypt32.wrap(key.encode())
    loaded = cs.load_ai_config(path)
    assert loaded.gateway_api_key == key and loaded.openai_api_key == "lm-" + key
    blob = bytearray(base64.b64decode(doc["gateway_api_key_dpapi"]))
    blob[-1] ^= 0x5A
    doc["gateway_api_key_dpapi"] = base64.b64encode(bytes(blob)).decode("ascii")
    path.write_text(json.dumps(doc), encoding="utf-8")
    tampered = cs.load_ai_config(path)
    assert tampered.gateway_api_key == "" and tampered.openai_api_key == "lm-" + key
