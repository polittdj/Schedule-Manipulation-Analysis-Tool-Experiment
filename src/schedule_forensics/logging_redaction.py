"""Structured, CUI-redacting logging (``AUTONOMOUS-BUILD-PROMPT.md`` §7).

Logs must carry operational metadata only — paths, counts, timings — and never
Controlled Unclassified Information such as schedule file names, task names, or
the contents of a CUI schedule. This module provides:

* :func:`redact` — scrubs CUI-bearing tokens (schedule/Office file names and
  absolute filesystem paths) from a string, replacing each with a stable,
  non-reversible token (``<file:mpp#a1b2c3d4>``) so log lines stay correlatable
  without leaking the underlying name. The token is inert (``redact`` is
  idempotent) and loopback URLs (the local Ollama endpoint) are preserved.
* :class:`CUIRedactingFilter` — a :class:`logging.Filter` that applies
  :func:`redact` to every record's message and string arguments (defense in
  depth; the contract is still to log only safe fields).
* :class:`CUIJsonFormatter` — emits one JSON object per record
  (``ts`` / ``level`` / ``logger`` / ``msg`` plus any structured ``extra``
  fields, themselves redacted).
* :func:`configure_logging` / :func:`get_logger` — install the formatter+filter
  on a ``stderr`` handler (no log file is written by default, so no CUI ever
  lands on disk) and hand back a namespaced logger.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from typing import TextIO

#: Schedule / Office / Power BI extensions whose *file names* are treated as CUI.
SENSITIVE_EXTENSIONS: tuple[str, ...] = (
    "mpp",
    "mpt",
    "mpx",
    "xer",
    "pmxml",
    "mspdi",
    "pbix",
    "xls",
    "xlsx",
    "csv",
    "xml",
)

# A bare file name ending in a sensitive extension, anchored at a token boundary
# so it never swallows preceding safe words.
_SENSITIVE_FILE_RE = re.compile(
    r"(?<![\w./\\-])[\w.\-]*\.(?P<ext>" + "|".join(SENSITIVE_EXTENSIONS) + r")\b",
    re.IGNORECASE,
)

# Absolute filesystem paths (POSIX or Windows), excluding URL paths (no preceding
# word char, ``:`` or ``/``). Segments exclude spaces so trailing prose is safe.
_POSIX_PATH_RE = re.compile(r"(?<![\w:/])(?:/[\w.\-]+){2,}")
_WINDOWS_PATH_RE = re.compile(r"(?<![\w/])[A-Za-z]:\\[\w.\-\\]+")

# Standard LogRecord attributes — anything else in ``record.__dict__`` is an
# operator-supplied ``extra`` field and is carried through (redacted).
_RESERVED_RECORD_KEYS: frozenset[str] = frozenset(vars(logging.makeLogRecord({})))

_configured = False


def _hash(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8", "replace"), digest_size=4).hexdigest()


def _redact_sensitive_file(match: re.Match[str]) -> str:
    # No literal dot before the extension keeps the token inert under the regexes
    # above, so redact() is idempotent (the formatter may redact a second time).
    ext = match.group("ext").lower()
    return f"<file:{ext}#{_hash(match.group(0))}>"


def _redact_path(match: re.Match[str]) -> str:
    text = match.group(0)
    tail = text.replace("\\", "/").rpartition("/")[2]
    stem, dot, ext = tail.rpartition(".")
    suffix = f":{ext.lower()}" if dot and stem else ""
    return f"<path{suffix}#{_hash(text)}>"


def redact(text: str) -> str:
    """Return ``text`` with CUI-bearing file names and absolute paths removed."""
    if not text:
        return text
    text = _WINDOWS_PATH_RE.sub(_redact_path, text)
    text = _POSIX_PATH_RE.sub(_redact_path, text)
    return _SENSITIVE_FILE_RE.sub(_redact_sensitive_file, text)


def _redact_value(value: object) -> object:
    return redact(value) if isinstance(value, str) else value


class CUIRedactingFilter(logging.Filter):
    """Apply :func:`redact` to each record's message and string arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: _redact_value(val) for key, val in record.args.items()}
            else:
                record.args = tuple(_redact_value(arg) for arg in record.args)
        return True


class CUIJsonFormatter(logging.Formatter):
    """Render each record as one JSON object, with the message redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = _redact_value(value)
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(level: int = logging.INFO, *, stream: TextIO | None = None) -> None:
    """Install the CUI-redacting JSON handler on the ``schedule_forensics`` root.

    Idempotent: replaces any handlers previously installed by this function.
    Logs go to ``stderr`` (or ``stream``); nothing is written to a file, so no
    CUI is ever persisted by the logging layer.
    """
    global _configured
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(CUIJsonFormatter())
    handler.addFilter(CUIRedactingFilter())
    root = logging.getLogger("schedule_forensics")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
    _configured = True


def get_logger(name: str = "schedule_forensics") -> logging.Logger:
    """Return a logger under the ``schedule_forensics`` namespace.

    Configures redacting logging on first use.
    """
    if not _configured:
        configure_logging()
    if name != "schedule_forensics" and not name.startswith("schedule_forensics."):
        name = f"schedule_forensics.{name}"
    return logging.getLogger(name)
