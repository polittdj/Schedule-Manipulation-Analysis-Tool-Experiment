"""AI transaction log — the durable local record of every off-machine AI transmission.

``docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md`` §6 step 5 (ADR-0402): *"a CUI tool that sends
anywhere needs a record; there is none today."* This module is that record. Every HTTP request
the approved-gateway backend makes — availability probes, model-catalog reads, and above all
generations carrying schedule content — appends one JSON line here: **what left, when, to which
endpoint, under which classification.**

Two rules shape the format:

* **The log itself must never become CUI.** Schedule content stays out: a generation is
  recorded as its SHA-256 and byte length, never its text (a plaintext prompt copy would be an
  uncontrolled CUI artifact on disk — the same discipline as ``logging_redaction``'s
  "no log file by default" rule). Endpoint, model and classification are operator
  configuration, not schedule data. Error text is :func:`error_summary`'s closed vocabulary —
  an HTTP status, a fixed transport reason, or an exception's class name — never ``str(exc)``
  (a ``BadStatusLine`` carries the reply's first line; ADR-0469).
* **An unrecorded transmission must not happen.** The caller writes the ``*.sent`` record
  *before* transmitting and lets a write failure propagate (fail closed — the gateway backend
  refuses to send what it cannot record). The ``*.done`` completion record is best-effort:
  the transmission already happened, so losing it must not turn a delivered answer into an
  error; the ``sent`` record has already documented the egress.

The log lives OUTSIDE the repo and outside the clear-on-quit cache (an audit record must
survive the session that wrote it): ``$SF_AI_LOG_DIR`` if set, else
``~/.local/state/schedule-forensics/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

#: File name of the append-only JSON-lines transaction log.
LOG_FILENAME = "ai-transactions.jsonl"

#: One process-wide lock: routes run in Starlette's threadpool, so two generations may try
#: to append concurrently; the lock keeps every JSON line whole.
_LOCK = threading.Lock()


def default_log_path() -> Path:
    """``$SF_AI_LOG_DIR``/ai-transactions.jsonl, else ``~/.local/state/schedule-forensics/``.

    Deliberately NOT the ``~/.cache`` schedule cache dir: that content is cleared on every
    quit (ADR-0335), while this record exists precisely to outlive the session.
    """
    env = os.environ.get("SF_AI_LOG_DIR")
    base = Path(env) if env else Path.home() / ".local" / "state" / "schedule-forensics"
    return base / LOG_FILENAME


def error_summary(exc: BaseException) -> str:
    """The bounded failure reason a ``*.done`` record may carry — never ``str(exc)``.

    ``probe_error_text``'s fallback is the exception's own text, which is right for a settings
    diagnostic rendered locally and wrong for a durable record: ``http.client.BadStatusLine``
    carries the RESPONSE's first line verbatim, so a misbehaving gateway could write its reply —
    model output derived from the prompt — into the audit log (WP7, ADR-0469, measured end to end
    through the real ``urllib`` opener). Here the vocabulary is closed: the HTTP status for an
    ``HTTPError``, one of three fixed transport reasons, else the exception's class name.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return f"server returned HTTP {exc.code}"
    low = str(getattr(exc, "reason", exc)).lower()
    if "refused" in low:
        return "connection refused — the model server isn't listening on this address"
    if "timed out" in low or "timeout" in low:
        return "timed out — the server didn't respond (wrong port, or still starting?)"
    if any(s in low for s in ("getaddrinfo", "name or service", "nodename", "no address")):
        return "host could not be resolved"
    return exc.__class__.__name__


def record(
    path: Path,
    *,
    kind: str,
    endpoint: str,
    model: str,
    classification: str,
    prompt: str | None = None,
    response_bytes: int | None = None,
    ok: bool | None = None,
    error: str | None = None,
) -> None:
    """Append one transaction record. Raises on failure — the CALLER decides what that means
    (the gateway backend treats a failed ``*.sent`` write as "do not transmit", fail closed).

    ``prompt`` is reduced to SHA-256 + byte length here, at the boundary — the text itself
    never reaches the file.
    """
    entry: dict[str, object] = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "endpoint": endpoint,
        "model": model,
        "classification": classification,
    }
    if prompt is not None:
        raw = prompt.encode("utf-8")
        entry["prompt_sha256"] = hashlib.sha256(raw).hexdigest()
        entry["prompt_bytes"] = len(raw)
    if response_bytes is not None:
        entry["response_bytes"] = response_bytes
    if ok is not None:
        entry["ok"] = ok
    if error is not None:
        entry["error"] = error
    line = json.dumps(entry, ensure_ascii=True, sort_keys=True)
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
