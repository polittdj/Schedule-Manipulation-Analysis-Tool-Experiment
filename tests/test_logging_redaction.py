"""CUI-redacting structured logging (§7)."""

from __future__ import annotations

import io
import json
import logging

import pytest

from schedule_forensics import logging_redaction as lr


def test_redacts_bare_schedule_filename() -> None:
    out = lr.redact("loaded Project2.mpp with 144 tasks")
    assert "Project2" not in out
    assert "<file:mpp#" in out  # extension retained for correlation
    assert "144" in out  # counts pass through untouched
    assert "loaded" in out and "tasks" in out  # surrounding prose preserved


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
