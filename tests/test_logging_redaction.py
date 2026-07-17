"""CUI-redacting structured logging (§7)."""

from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path

import pytest

from schedule_forensics import logging_redaction as lr

_PRECOMMIT = Path(__file__).resolve().parent.parent / ".githooks" / "pre-commit"


def test_redacts_bare_schedule_filename() -> None:
    out = lr.redact("loaded Project2.mpp with 144 tasks")
    assert "Project2" not in out
    assert "<file:mpp#" in out  # extension retained for correlation
    assert "144" in out  # counts pass through untouched
    assert "loaded" in out and "tasks" in out  # surrounding prose preserved


def test_sensitive_extensions_cover_every_precommit_cui_extension() -> None:
    # Audit: the log redactor's SENSITIVE_EXTENSIONS omitted doc/docx/aft (and pkl/pickle), which
    # the pre-commit CUI guard DOES treat as CUI — so those file names leaked through logs. Pin the
    # two sets together: every extension the guard blocks as CUI must also be redacted in logs.
    text = _PRECOMMIT.read_text(encoding="utf-8")
    m = re.search(r"blocked_re='\\\.\(([^)]+)\)\$'", text)
    assert m, "could not read blocked_re from .githooks/pre-commit"
    blocked = set(m.group(1).split("|"))
    missing = blocked - set(lr.SENSITIVE_EXTENSIONS)
    assert not missing, f"log redactor omits CUI extensions the pre-commit guard blocks: {missing}"


@pytest.mark.parametrize("name", ["NASA Metrics.aft", "Reference Export.docx", "schedule.pkl"])
def test_redacts_the_newly_covered_cui_extensions(name: str) -> None:
    out = lr.redact(f"import failed for '{name}'")
    stem = name.rsplit(".", 1)[0]
    assert stem not in out and "<file:" in out


def test_redacts_posix_path_keeps_extension() -> None:
    out = lr.redact("reading /home/analyst/secret/Project5.xer now")
    assert "Project5" not in out
    assert "secret" not in out
    assert "analyst" not in out
    assert "<path:xer#" in out
    assert out.endswith(" now")


def test_redacts_windows_path() -> None:
    out = lr.redact(r"open C:\Users\jdoe\Schedules\Project2.mpp done")
    assert "jdoe" not in out
    assert "Project2" not in out
    assert "<path:mpp#" in out


def test_redaction_is_idempotent() -> None:
    # The formatter may redact an already-filtered message a second time.
    once = lr.redact("loaded /home/u/Project5.mpp and Project2.mpp")
    assert lr.redact(once) == once


def test_preserves_loopback_url() -> None:
    msg = "POST http://localhost:11434/api/generate ok"
    assert lr.redact(msg) == msg


def test_redaction_is_deterministic() -> None:
    assert lr.redact("Project2.mpp") == lr.redact("Project2.mpp")
    assert lr.redact("a.mpp") != lr.redact("b.mpp")  # distinct names → distinct tokens


def test_empty_string_is_noop() -> None:
    assert lr.redact("") == ""


def test_json_formatter_emits_object_with_required_keys() -> None:
    fmt = lr.CUIJsonFormatter()
    record = logging.LogRecord(
        "schedule_forensics.test", logging.INFO, "/x.py", 10, "opened %s", ("Project2.mpp",), None
    )
    record.task_count = 144  # operator-supplied structured extra
    payload = json.loads(fmt.format(record))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "schedule_forensics.test"
    assert "Project2" not in payload["msg"]
    assert payload["task_count"] == 144


def test_json_formatter_redacts_exception_text() -> None:
    fmt = lr.CUIJsonFormatter()
    try:
        raise ValueError("failed on /home/u/Project5.mpp")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "schedule_forensics", logging.ERROR, "/x.py", 1, "boom", None, sys.exc_info()
        )
    payload = json.loads(fmt.format(record))
    assert "Project5" not in payload["exc"]


def test_filter_redacts_record_in_place() -> None:
    filt = lr.CUIRedactingFilter()
    record = logging.LogRecord(
        "x", logging.INFO, "/x.py", 1, "file %s", ("/home/u/Project5.mpp",), None
    )
    assert filt.filter(record) is True
    assert "Project5" not in record.getMessage()


def test_filter_redacts_dict_args() -> None:
    filt = lr.CUIRedactingFilter()
    # A mapping arg must be wrapped in a 1-tuple for LogRecord to unwrap it,
    # exactly as ``logger.info("f %(p)s", {"p": ...})`` does internally.
    record = logging.LogRecord(
        "x", logging.INFO, "/x.py", 1, "f %(p)s", ({"p": "Project2.mpp"},), None
    )
    assert isinstance(record.args, dict)
    assert filt.filter(record) is True
    assert "Project2" not in record.getMessage()


def test_configure_and_get_logger_namespaces_and_redacts() -> None:
    stream = io.StringIO()
    lr.configure_logging(stream=stream)
    logger = lr.get_logger("ingest")
    assert logger.name == "schedule_forensics.ingest"
    logger.info("loaded /home/u/Project2.mpp", extra={"task_count": 144})
    line = stream.getvalue().strip()
    payload = json.loads(line)
    assert "Project2" not in payload["msg"]
    assert payload["task_count"] == 144
    assert payload["logger"] == "schedule_forensics.ingest"


def test_get_logger_default_namespace() -> None:
    assert lr.get_logger().name == "schedule_forensics"
    assert lr.get_logger("schedule_forensics.web").name == "schedule_forensics.web"


def test_get_logger_configures_on_first_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lr, "_configured", False)
    logger = lr.get_logger("once")
    assert lr._configured is True
    assert logger.name == "schedule_forensics.once"


def test_filter_passes_non_string_message_through() -> None:
    filt = lr.CUIRedactingFilter()
    record = logging.LogRecord("x", logging.INFO, "/x.py", 1, 42, None, None)
    assert filt.filter(record) is True
    assert record.getMessage() == "42"


def test_redacts_quoted_filename_with_spaces() -> None:
    out = lr.redact("could not import 'Site Alpha rebaseline.mpp': bad header")
    assert "Site Alpha" not in out and "rebaseline" not in out
    assert "<file:mpp#" in out and "bad header" in out


def test_redacts_unc_paths() -> None:
    out = lr.redact(r"reading \\hq-srv01\plans\ims\current.mpp now")
    assert "hq-srv01" not in out and "plans" not in out
    assert "now" in out


@pytest.mark.parametrize(
    "line",
    [
        r"opened \\fileserver\share\Site Alpha Rebaseline.mpp for parse",  # UNC
        r"path C:\Users\ProgramData\Site Alpha Rebaseline.xlsx failed",  # Windows drive
        r"read /mnt/cui/schedules/Site Alpha Rebaseline.xer done",  # POSIX
        r"deep \\srv\a\b\c\Q3 Program Baseline Rev 2.mpp end",  # multi-word, deep dirs
    ],
)
def test_spaced_path_filename_does_not_leak_middle_words(line: str) -> None:
    r"""Audit: a path ending in a file name WITH SPACES leaked the name's middle words.

    The space-free path regexes stop at the first space, so ``\\server\share\Site Alpha
    Rebaseline.mpp`` was redacted to ``<path#…> Alpha <file:mpp#…>`` — the middle word ``Alpha``
    (a CUI file-name token) survived in clear text. ``_SPACED_FILE_PATH_RE`` now consumes the whole
    path + spaced name first. Mutation check: without it every case leaks ``Alpha`` / ``Baseline``.
    """
    out = lr.redact(line)
    for leaked in ("Alpha", "Rebaseline", "Baseline", "Program", "Q3", "Rev"):
        assert leaked not in out, f"CUI file-name token {leaked!r} leaked: {out}"
    assert "<path:" in out  # whole path+name folded into one inert token, extension retained
    assert lr.redact(out) == out  # idempotent


def test_spaced_path_fix_still_spares_trailing_prose() -> None:
    """The spaced-name catch must not swallow ordinary prose after a space-free path: a path with
    no sensitive-extension file name still stops at the first space (the pre-existing guarantee)."""
    out = lr.redact(r"copied \\server\share\data to the archive")
    assert out == "copied <path#0e6bf4c8> to the archive" or (
        "<path#" in out and out.endswith(" to the archive")
    )


@pytest.mark.parametrize(
    "line",
    [
        r"open C:\Users\John Smith\Site Alpha Rebaseline.mpp failed",  # Windows profile has a space
        r"read \\server\CUI Share\Site Alpha\Rebaseline.mpp done",  # UNC share + dir with spaces
        r"parse /mnt/My Projects/Site Alpha.mpp error",  # POSIX dir with a space
        r"C:\Users\Jane Q. Public\OneDrive\Q3 Baseline Rev 2.xer",  # spaced dirs + spaced name
    ],
)
def test_spaced_INTERMEDIATE_directory_does_not_leak(line: str) -> None:
    r"""Audit ADR-0250: the ADR-0247 spaced-name catch only tolerated spaces in the FINAL file name,
    so a spaced INTERMEDIATE directory (``C:\Users\John Smith\…``, ``\\server\CUI Share\…``) broke
    whole-path match and leaked the surname / share / project words in clear — a real Law-1 leak
    (a Windows profile path near-always has a space). ``_SPACED_FILE_PATH_RE`` now allows spaces in
    interior segments. Mutation check: reverting the interior class to ``[\w.\-]+`` re-leaks these.
    """
    out = lr.redact(line)
    for leaked in (
        "Smith",
        "Alpha",
        "Rebaseline",
        "Share",
        "Projects",
        "John",
        "Jane",
        "Public",
        "OneDrive",
        "Baseline",
        "Q3",
    ):
        assert leaked not in out, f"CUI token {leaked!r} leaked from a spaced directory: {out}"
    assert "<path:" in out or "<file:" in out  # folded into one inert token, extension retained
    assert lr.redact(out) == out  # idempotent


def test_redacts_json_schedule_filenames() -> None:
    # "Save .json" writes the tool's own schedule format — those names are CUI too
    out = lr.redact("saved NSAT_deploy_rev3.json for review")
    assert "NSAT" not in out and "<file:json#" in out


def test_non_string_extras_are_redacted_in_json_lines() -> None:
    import io
    import json as jsonlib

    stream = io.StringIO()
    lr.configure_logging(stream=stream)
    logger = lr.get_logger("test_extras")
    logger.info(
        "batch done",
        extra={"names": ["Site Alpha rebaseline.mpp", 3], "meta": {"src": "Q3 IMS.xer"}},
    )
    payload = jsonlib.loads(stream.getvalue())
    blob = jsonlib.dumps(payload)
    assert "Site Alpha" not in blob and "rebaseline" not in blob and "Q3 IMS" not in blob
    # reset global handler state for other tests
    lr.configure_logging(stream=io.StringIO())
