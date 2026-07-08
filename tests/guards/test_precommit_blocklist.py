"""Audit M2: the pre-commit CUI guard must block every extension CLAUDE.md Law 1 names.

CLAUDE.md states the guard "blocks ``.mpp``/``.xlsx``/``.aft``/``.xer``/``.docx``". This test reads
the *actual* ``blocked_re`` from ``.githooks/pre-commit`` and asserts each named CUI extension is
matched (case-insensitively, as the hook's ``grep -iE`` runs it) and that synthetic fixtures under
``tests/fixtures/`` stay exempt — so the spec and the hook implementation can't silently drift apart
again.
"""

from __future__ import annotations

import re
import subprocess
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


# ── inherited-blob exception (operator-approved 2026-07-08) ────────────────────────────────
# The operator committed the reference exports to main via the GitHub web UI, so a merge of
# main inherits blocked-extension files. The hook now allows a staged file ONLY when its blob
# is byte-identical to origin/main's blob at the same path; anything new or modified stays
# blocked. These tests run the real hook script inside a scratch repo.


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


@pytest.fixture()
def scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(repo, "git", "init", "-q", "-b", "main")
    _run(repo, "git", "config", "user.email", "t@t")
    _run(repo, "git", "config", "user.name", "t")
    (repo / "ref.xlsx").write_bytes(b"upstream-bytes")
    _run(repo, "git", "add", "ref.xlsx")
    _run(repo, "git", "commit", "-q", "-m", "upstream", "--no-verify")
    # simulate the remote-tracking ref the hook consults
    _run(repo, "git", "update-ref", "refs/remotes/origin/main", "main")
    # start a fresh orphan branch so staged files are Adds (like a merge bringing them in)
    _run(repo, "git", "checkout", "-q", "--orphan", "work")
    _run(repo, "git", "rm", "-rq", "--cached", ".")
    return repo


def _hook_exit(repo: Path) -> int:
    return _run(repo, "bash", str(_HOOK)).returncode


def test_hook_allows_blob_identical_to_origin_main(scratch_repo: Path) -> None:
    (scratch_repo / "ref.xlsx").write_bytes(b"upstream-bytes")  # identical to origin/main
    _run(scratch_repo, "git", "add", "ref.xlsx")
    assert _hook_exit(scratch_repo) == 0


def test_hook_still_blocks_a_modified_upstream_file(scratch_repo: Path) -> None:
    (scratch_repo / "ref.xlsx").write_bytes(b"TAMPERED-bytes")  # same path, different blob
    _run(scratch_repo, "git", "add", "ref.xlsx")
    assert _hook_exit(scratch_repo) != 0


def test_hook_still_blocks_a_new_cui_file(scratch_repo: Path) -> None:
    (scratch_repo / "leak.mpp").write_bytes(b"new-schedule")  # not on origin/main at all
    _run(scratch_repo, "git", "add", "leak.mpp")
    assert _hook_exit(scratch_repo) != 0
