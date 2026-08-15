"""Persistent AI settings — armed once, armed on every launch (ADR-0404).

Operator directive (2026-08-15): *"I do not want to have to put in the NASA API KEY everytime
I open the program. I want it to work when I click on the desktop icon."* This supersedes
ADR-0402's per-launch re-arming: the AI configuration — backend, endpoints, model, the
gateway approval acknowledgment, and the gateway key — persists in a small local JSON file
that the desktop launch path loads at startup. Consent stays explicit and revocable (the
acknowledgment is recorded durably instead of re-asked; unchecking it, Turn-the-AI-off, or a
session wipe persists the OFF state); the persistent warning banner never depended on this
file and still renders on every armed session.

Three rules shape the store:

* **No schedule content, ever.** The file holds operator configuration only — it can never
  become CUI, which is why persisting it is compatible with the clear-on-quit rules that
  govern schedule data (ADR-0335). It lives beside the AI transaction log, outside the
  wiped cache dir: ``$SF_SETTINGS_DIR`` else ``~/.local/state/schedule-forensics/``.
* **Loading is a trust boundary.** The file is operator-editable state, so loading re-applies
  the same sanitizers as the settings form POST — above all: a gateway endpoint that is not
  EXACTLY on ``net_guard.APPROVED_GATEWAY_ENDPOINTS`` clears to "" (a hand-edited file must
  never smuggle a destination past the allowlist). Missing or corrupt files yield pure
  defaults, never an error at launch.
* **The credential is never plaintext at rest where an OS protector exists.** On Windows the
  key is wrapped with DPAPI (user scope, via ctypes — stdlib only) into
  ``gateway_api_key_dpapi``; if protection FAILS the key is simply not persisted (fail
  closed on the credential, fail soft on convenience — a broken protector must never
  silently downgrade to plaintext). On POSIX there is no ubiquitous stdlib protector: the
  key is stored under the honestly-named ``gateway_api_key_plain`` in a 0600 file — the
  same protection class as the ``SF_GATEWAY_API_KEY`` user environment variable it
  substitutes for.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
from pathlib import Path

from schedule_forensics.ai.backend import AIConfig, Classification
from schedule_forensics.net_guard import is_approved_gateway_endpoint, is_local_http_endpoint

logger = logging.getLogger(__name__)

#: File name of the persistent AI settings document.
SETTINGS_FILENAME = "ai-settings.json"

#: Serialization schema version — bump on incompatible shape changes.
_SCHEMA = 1


def default_settings_path() -> Path:
    """``$SF_SETTINGS_DIR``/ai-settings.json, else ``~/.local/state/schedule-forensics/``.

    Deliberately NOT the ``~/.cache`` schedule cache dir: that content is cleared on every
    quit (ADR-0335), while this file exists precisely to survive the quit.
    """
    env = os.environ.get("SF_SETTINGS_DIR")
    base = Path(env) if env else Path.home() / ".local" / "state" / "schedule-forensics"
    return base / SETTINGS_FILENAME


# ── the key protector: DPAPI on Windows, honestly-plain elsewhere ──────────────────────────


def _dpapi_protect(raw: bytes) -> bytes:  # pragma: no cover - Windows-only, exercised in field
    import ctypes
    import ctypes.wintypes as wt

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    inblob = _BLOB(
        len(raw),
        ctypes.cast(ctypes.create_string_buffer(raw, len(raw)), ctypes.POINTER(ctypes.c_char)),
    )
    outblob = _BLOB()
    # user-scope protection (flag 0): only this Windows account can unprotect
    if not crypt32.CryptProtectData(
        ctypes.byref(inblob), None, None, None, None, 0, ctypes.byref(outblob)
    ):
        raise OSError("CryptProtectData failed")
    try:
        return ctypes.string_at(outblob.pbData, outblob.cbData)
    finally:
        kernel32.LocalFree(outblob.pbData)


def _dpapi_unprotect(blob: bytes) -> bytes:  # pragma: no cover - Windows-only
    import ctypes
    import ctypes.wintypes as wt

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32  # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    inblob = _BLOB(
        len(blob),
        ctypes.cast(ctypes.create_string_buffer(blob, len(blob)), ctypes.POINTER(ctypes.c_char)),
    )
    outblob = _BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(inblob), None, None, None, None, 0, ctypes.byref(outblob)
    ):
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(outblob.pbData, outblob.cbData)
    finally:
        kernel32.LocalFree(outblob.pbData)


def _plain_passthrough(raw: bytes) -> bytes:
    return raw


if sys.platform == "win32":  # pragma: no cover - the POSIX suite exercises the plain path
    _protect_key = _dpapi_protect
    _unprotect_key = _dpapi_unprotect
    _KEY_FIELD = "gateway_api_key_dpapi"
else:
    _protect_key = _plain_passthrough
    _unprotect_key = _plain_passthrough
    _KEY_FIELD = "gateway_api_key_plain"


# ── save / load ────────────────────────────────────────────────────────────────────────────


def save_ai_config(cfg: AIConfig, path: Path | None = None) -> None:
    """Persist ``cfg`` (best-effort atomic: temp file + replace). Raises on I/O failure —
    the CALLER decides what that means (the web layer logs and carries on; settings that
    fail to persist simply do not survive the quit)."""
    target = path if path is not None else default_settings_path()
    doc: dict[str, object] = {
        "schema": _SCHEMA,
        "classification": str(cfg.classification),
        "backend": cfg.backend,
        "model": cfg.model,
        "endpoint": cfg.endpoint,
        "qa_mode": cfg.qa_mode,
        "openai_endpoint": cfg.openai_endpoint,
        "second_backend": cfg.second_backend,
        "second_model": cfg.second_model,
        "gen_timeout": cfg.gen_timeout,
        "gateway_endpoint": cfg.gateway_endpoint,
        "gateway_approved": cfg.gateway_approved,
    }
    if cfg.gateway_api_key:
        try:
            wrapped = _protect_key(cfg.gateway_api_key.encode("utf-8"))
            doc[_KEY_FIELD] = base64.b64encode(wrapped).decode("ascii")
        except Exception:
            # fail CLOSED on the credential (it is simply not persisted), fail SOFT on the
            # rest — never downgrade a broken protector to plaintext behind the operator
            logger.warning("could not protect the gateway key; persisting settings without it")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    if _KEY_FIELD == "gateway_api_key_plain":
        os.chmod(tmp, 0o600)  # owner-only where the key may be stored plain (POSIX)
    tmp.replace(target)


def _load_key(doc: dict[str, object]) -> str:
    encoded = doc.get(_KEY_FIELD)
    if not isinstance(encoded, str) or not encoded:
        return ""
    try:
        return _unprotect_key(base64.b64decode(encoded)).decode("utf-8")
    except Exception:
        # a key protected by another account/machine (or corrupted) is unrecoverable by
        # design — come up keyless rather than fail the launch
        logger.warning("could not unprotect the stored gateway key; starting without it")
        return ""


def load_ai_config(path: Path | None = None) -> AIConfig:
    """The persisted config, sanitized at the boundary — or pure defaults on any problem."""
    target = path if path is not None else default_settings_path()
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return AIConfig()
    except Exception:
        logger.warning("unreadable AI settings file; starting from defaults")
        return AIConfig()
    if not isinstance(doc, dict):
        return AIConfig()

    def _s(name: str, default: str) -> str:
        value = doc.get(name)
        return value if isinstance(value, str) else default

    try:
        classification = Classification(_s("classification", "CLASSIFIED"))
    except ValueError:
        classification = Classification.CLASSIFIED
    qa_mode = _s("qa_mode", "annotate")
    if qa_mode not in ("annotate", "strict", "interpretive", "unrestricted"):
        qa_mode = "annotate"
    second_backend = _s("second_backend", "none")
    if second_backend not in ("none", "ollama", "openai"):
        second_backend = "none"
    endpoint = _s("endpoint", "http://127.0.0.1:11434").strip()
    if not is_local_http_endpoint(endpoint):
        endpoint = "http://127.0.0.1:11434"
    openai_endpoint = _s("openai_endpoint", "http://127.0.0.1:1234").strip()
    if not is_local_http_endpoint(openai_endpoint):
        openai_endpoint = "http://127.0.0.1:1234"
    # the allowlist holds at EVERY boundary: a hand-edited file cannot smuggle a destination
    gateway_endpoint = _s("gateway_endpoint", "").strip()
    if gateway_endpoint and not is_approved_gateway_endpoint(gateway_endpoint):
        gateway_endpoint = ""
    raw_timeout = doc.get("gen_timeout")
    gen_timeout = float(raw_timeout) if isinstance(raw_timeout, (int, float)) else 3600.0
    gen_timeout = min(3600.0, max(30.0, gen_timeout))
    return AIConfig(
        classification=classification,
        backend=_s("backend", "ollama"),
        model=_s("model", "qwen2.5:7b-instruct"),
        endpoint=endpoint,
        qa_mode=qa_mode,
        openai_endpoint=openai_endpoint,
        second_backend=second_backend,
        second_model=_s("second_model", ""),
        gen_timeout=gen_timeout,
        gateway_endpoint=gateway_endpoint,
        gateway_approved=doc.get("gateway_approved") is True,
        gateway_api_key=_load_key(doc),
    )
