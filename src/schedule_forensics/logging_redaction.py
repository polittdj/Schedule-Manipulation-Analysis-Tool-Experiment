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

At runtime the handler is installed at every entry path — ``launcher.main()``,
``web.app.create_app()`` (idempotently), and ``exhibits.cli.main()`` — so every
``schedule_forensics.*`` logger is redacting from process start and no record
reaches ``logging.lastResort`` unredacted (``tests/web/test_startup_guards.py``
asserts the wiring).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from typing import TextIO

#: Schedule / Office / Power BI extensions whose *file names* are treated as CUI
#: (``json`` included: "Save .json" writes the tool's own schedule format).
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
    "json",
)

# A bare file name ending in a sensitive extension, anchored at a token boundary
# so it never swallows preceding safe words (no spaces — prose stays intact).
_SENSITIVE_FILE_RE = re.compile(
    r"(?<![\w./\\-])[\w.\-]*\.(?P<ext>" + "|".join(SENSITIVE_EXTENSIONS) + r")\b",
    re.IGNORECASE,
)

# A string that IS a file name in its entirety (a structured extra, a list element)
# may contain spaces — the string boundary bounds the match, no prose to protect.
_WHOLE_SENSITIVE_FILE_RE = re.compile(
    r"^[^\n]{1,200}\.(?P<ext>" + "|".join(SENSITIVE_EXTENSIONS) + r")$",
    re.IGNORECASE,
)

# A QUOTED file name may contain spaces ("Site Alpha rebaseline.mpp") — quoting is how
# spaced names reach logs (exception reprs, f-string quoting), and the quotes bound the
# match so surrounding prose is never swallowed.
_QUOTED_SENSITIVE_FILE_RE = re.compile(
    r"""(?P<q>["'])(?P<name>[^"'\n]{1,160}?\.(?P<ext>"""
    + "|".join(SENSITIVE_EXTENSIONS)
    + r"""))(?P=q)""",
    re.IGNORECASE,
)

# Absolute filesystem paths (POSIX, Windows drive, or UNC), excluding URL paths (no
# preceding word char, ``:`` or ``/``). Segments exclude spaces so trailing prose is
# safe; the UNC form (\\server\share\…) is the realistic case on CUI networks.
_POSIX_PATH_RE = re.compile(r"(?<![\w:/])(?:/[\w.\-]+){2,}")
_WINDOWS_PATH_RE = re.compile(r"(?<![\w/])[A-Za-z]:\\[\w.\-\\]+")
_UNC_PATH_RE = re.compile(r"(?<![\w\\])\\\\[\w.\-]+(?:\\[\w.\-]+)+")

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


def _redact_quoted_file(match: re.Match[str]) -> str:
    quote = match.group("q")
    ext = match.group("ext").lower()
    return f"{quote}<file:{ext}#{_hash(match.group('name'))}>{quote}"


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
    whole = _WHOLE_SENSITIVE_FILE_RE.match(text.strip())
    if whole is not None:  # the string IS a file name (spaces and all)
        return f"<file:{whole.group('ext').lower()}#{_hash(text.strip())}>"
    text = _UNC_PATH_RE.sub(_redact_path, text)
    text = _WINDOWS_PATH_RE.sub(_redact_path, text)
    text = _POSIX_PATH_RE.sub(_redact_path, text)
    text = _QUOTED_SENSITIVE_FILE_RE.sub(_redact_quoted_file, text)
    return _SENSITIVE_FILE_RE.sub(_redact_sensitive_file, text)


def _redact_value(value: object) -> object:
    """Redact strings; recurse into containers; stringify-and-redact anything else.

    A non-str ``extra`` (a list of names, a dict, a ``Path``) must not bypass
    redaction on its way into the JSON line.
    """
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {key: _redact_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_redact_value(item) for item in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact(str(value))  # Path and friends serialize via str — redact that form


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
