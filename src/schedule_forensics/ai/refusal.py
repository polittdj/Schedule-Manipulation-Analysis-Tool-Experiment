"""The server's OWN reason for an HTTP refusal, bounded (OR-16, ADR-0488).

A probe or a generation that a server answers with 401 / 403 / 400 almost always carries a
one-line reason: RFC 6750 puts it in the ``WWW-Authenticate`` challenge (``error`` /
``error_description``), OpenAI-style servers in the JSON body (``error.message``), simpler
ones in a bare ``error`` / ``message`` / ``detail`` string or a plain-text body. The tool used
to discard all of it and report the status code alone — the operator then had nothing to act
on but "HTTP 401" (field report 2026-09-12: a saved key the approved gateway refused, and the
request had to be re-made in PowerShell to learn anything more). Reading the body has two
constraints, both enforced here:

* **Once.** ``HTTPError.read()`` consumes the response. ``completion.limit_rejected`` reads a
  400's body to see whether it names ``max_tokens``; the diagnostics read it for the reason.
  :func:`http_error_body` reads at most once and caches the bytes ON the exception, so every
  reader sees the same bytes in any order.
* **Bounded, one line, never markup.** At most :data:`MAX_REASON_CHARS` characters on one
  line; an HTML error page names nothing an operator can act on and is dropped whole. The
  response never carries the credential, and the transaction log keeps its closed vocabulary
  (``txlog.error_summary``) — the reason reaches the settings page and the Ask panel only.
"""

from __future__ import annotations

import contextlib
import json
import re
import urllib.error
from typing import Any

#: The longest reason the diagnostics will quote (one line).
MAX_REASON_CHARS = 160
#: The most of a refused response that is ever read.
MAX_BODY_BYTES = 4096
_CACHE_ATTR = "_sf_error_body"
_CHALLENGE_FIELD = re.compile(r'(error_description|error)\s*=\s*"([^"]*)"')
#: The opening run of a JSON reason field, closing quote NOT required (a truncated body).
_JSON_FIELD = re.compile(
    r'"(?:message|error|detail|reason|error_description)"\s*:\s*"([^"\\]{1,'
    + str(MAX_REASON_CHARS * 4)
    + "})"
)


def http_error_body(exc: BaseException, limit: int = MAX_BODY_BYTES) -> bytes:
    """Up to ``limit`` bytes of the refused response, read ONCE and cached on ``exc``.

    Anything that is not readable (a bodiless error, a non-HTTP exception, a closed stream)
    is the empty body — never an exception out of a diagnostic.
    """
    cached = getattr(exc, _CACHE_ATTR, None)
    if isinstance(cached, bytes):
        return cached
    body = b""
    reader = getattr(exc, "read", None)
    if callable(reader):
        try:
            raw = reader(limit)
            body = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
        except Exception:
            body = b""
    with contextlib.suppress(Exception):  # an exception type refusing attributes
        setattr(exc, _CACHE_ATTR, body)
    return body


def _one_line(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) > MAX_REASON_CHARS:
        flat = flat[: MAX_REASON_CHARS - 1].rstrip() + "…"
    return flat


def _json_reason(doc: Any, depth: int = 0) -> str:
    """The first human-readable reason string in an error document, at most two levels deep
    (``{"error": {"message": ...}}`` is the common OpenAI shape)."""
    if not isinstance(doc, dict) or depth > 2:
        return ""
    for key in ("error", "message", "detail", "reason", "error_description"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            inner = _json_reason(value, depth + 1)
            if inner:
                return inner
    return ""


def http_refusal_detail(exc: BaseException) -> str:
    """The server's own one-line reason for ``exc``, or ``""`` when it gave none.

    Order of authority: the ``WWW-Authenticate`` challenge (``error_description``, then
    ``error``), then the body — a JSON error document's reason string, or the first line of a
    plain-text body. Markup is never quoted. Bounded by :func:`_one_line`.
    """
    if not isinstance(exc, urllib.error.HTTPError):
        return ""
    challenge = ""
    headers = getattr(exc, "headers", None)
    if headers is not None:
        try:
            challenge = str(headers.get("WWW-Authenticate") or "")
        except Exception:
            challenge = ""
    fields = {m.group(1): m.group(2) for m in _CHALLENGE_FIELD.finditer(challenge)}
    for key in ("error_description", "error"):
        if fields.get(key, "").strip():
            return _one_line(fields[key])
    text = http_error_body(exc).decode("utf-8", "replace").strip()
    if not text:
        return ""
    if text[0] in "{[":
        try:
            doc = json.loads(text)
        except ValueError:
            # a body longer than the read limit is cut mid-document: still quote the reason
            # field's opening run, bounded — a truncated reason beats none
            m = _JSON_FIELD.search(text)
            return _one_line(m.group(1)) if m else ""
        found = _json_reason(doc)
        return _one_line(found) if found else ""
    if text.startswith("<"):
        return ""  # an HTML error page names nothing an operator can act on
    return _one_line(text.splitlines()[0])
