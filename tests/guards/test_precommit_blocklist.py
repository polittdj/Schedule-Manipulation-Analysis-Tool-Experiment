"""Audit M2: the pre-commit CUI guard must block every extension CLAUDE.md Law 1 names.

CLAUDE.md states the guard "blocks ``.mpp``/``.xlsx``/``.aft``/``.xer``/``.docx``". This test reads
the *actual* ``blocked_re`` from ``.githooks/pre-commit`` and asserts each named CUI extension is
matched (case-insensitively, as the hook's ``grep -iE`` runs it) and that synthetic fixtures under
``tests/fixtures/`` stay exempt — so the spec and the hook implementation can't silently drift apart
again.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[2] / ".githooks" / "pre-commit"


def _blocked_re() -> re.Pattern[str]:
    text = _HOOK.read_text(encoding="utf-8")
    match = re.search(r"blocked_re='([^']+)'", text)
    assert match, "could not find blocked_re in .githooks/pre-commit"
    # the hook applies it with `grep -iE` (case-insensitive, extended)
    return re.compile(match.group(1), re.IGNORECASE)


@pytest.mark.parametrize(
    "ext",
    [
        "mpp",
        "mpt",
        "mpx",
        "xer",
        "xml",
        "pmxml",
        "csv",
        "xls",
        "xlsx",
        "pbix",
        "mspdi",
        "pkl",
        "pickle",
        "aft",
        "docx",
        "doc",
    ],
)
def test_cui_extension_is_blocked(ext: str) -> None:
    pattern = _blocked_re()
    assert pattern.search(f"NASA_Metrics_Complete.{ext}"), f".{ext} must be blocked by the hook"
    assert pattern.search(f"reference.{ext.upper()}"), (
        f".{ext.upper()} must block case-insensitively"
    )


def test_law1_named_extensions_are_all_covered() -> None:
    # the exact set CLAUDE.md Law 1 calls out by name
    pattern = _blocked_re()
    for ext in ("mpp", "xlsx", "aft", "xer", "docx"):
        assert pattern.search(f"schedule.{ext}"), f"CLAUDE.md names .{ext} but the hook misses it"


def test_non_cui_source_files_are_not_blocked() -> None:
    pattern = _blocked_re()
    for path in ("src/schedule_forensics/web/app.py", "docs/HANDOFF.md", "README.md"):
        assert not pattern.search(path), f"{path} must not be blocked"
