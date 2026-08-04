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
        # added 2026-08-03 (audit §5, ADR-0347): a real Primavera exchange format and the
        # macro-enabled workbook, both absent from the original denylist.
        "p6xml",
        "xlsm",
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


# ── suffix chain (audit 2026-08-03 §5, ADR-0347) ───────────────────────────────────────────
# The pattern used to anchor hard on `$`, so `data.mpp.bak` walked straight through. It now
# accepts a CLOSED set of backup/copy suffixes after the blocked extension.


@pytest.mark.parametrize(
    "name",
    ["data.mpp.bak", "export.xlsx.1", "sched.mpp~", "plan.csv.gz", "old.doc.old", "s.xer.orig"],
)
def test_backup_and_copy_suffixes_are_blocked(name: str) -> None:
    assert _blocked_re().search(name), f"{name} hides a CUI artifact behind a backup suffix"


@pytest.mark.parametrize(
    "name",
    [
        # The measured false positive: a Java package name that merely CONTAINS ".xml.".
        # "blocked ext followed by any dot" would wedge every MPXJ upgrade.
        "tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar",
        "report.mppx",  # a longer extension that merely starts with a blocked one
        "docs/schedule-forensics.md",
    ],
)
def test_lookalike_names_are_not_blocked(name: str) -> None:
    assert not _blocked_re().search(name), f"{name} is not a CUI artifact"


_REPO = Path(__file__).resolve().parents[2]


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=_REPO, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p]


def _allow_prefixes() -> tuple[str, ...]:
    text = _HOOK.read_text(encoding="utf-8")
    block = text.split("allow_prefixes=(", 1)[1].split(")", 1)[0]
    found = tuple(re.findall(r"'([^']+/)'", block))
    assert found, "could not read allow_prefixes from the hook"
    return found


def test_the_suffix_clause_does_not_widen_the_net_over_the_tracked_tree() -> None:
    """The backup-suffix clause must catch `data.mpp.bak` and NOTHING already in the repo.

    The intake legitimately tracks `.docx`/`.xlsx`/`.mpp` — ADR-0152's ``inherited_from_main``
    rule is what lets those ride a merge, and this test does not second-guess it. What it pins is
    that the 2026-08-03 widening added **no new** matches: the obvious "blocked ext followed by
    any dot" silently claimed `tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar`, whose Java package
    name merely contains ".xml.", which would wedge every MPXJ upgrade with a nonsense reason.
    Relying on the inherited-blob exception to paper over that would hide the wedge until the day
    the file legitimately changes.
    """
    new = _blocked_re()
    # the pre-2026-08-03 core: the same extensions, anchored hard on end-of-name
    core = re.compile(new.pattern.split("(~?$")[0] + "$", re.IGNORECASE)
    allowed = _allow_prefixes()
    widened = [
        p
        for p in _tracked()
        if not p.startswith(allowed) and new.search(p.rsplit("/", 1)[-1]) and not core.search(p)
    ]
    assert widened == []


def test_the_content_detector_finds_nothing_in_the_repos_own_sources() -> None:
    """No source, doc, test or config file trips the schedule sniff.

    Scoped off ``00_REFERENCE_INTAKE/`` (operator-uploaded through the GitHub web UI, where no
    local hook runs, and covered by the inherited-blob rule) and off the hook's own allow-prefixes.
    A guard that fired on the repo's own files would be switched off within a day, and then it
    guards nothing.

    Uses ``git grep -E`` rather than a hand-translated Python regex: the hook's pattern is POSIX
    ERE with ``[[:space:]]`` classes, and re-expressing it here would test the translation instead
    of the guard.
    """
    signature = re.search(r"signature_re='([^']+)'", _HOOK.read_text(encoding="utf-8"))
    assert signature, "could not read signature_re from the hook"
    excludes = [f":(exclude){p}" for p in ("00_REFERENCE_INTAKE/", *_allow_prefixes())]
    found = subprocess.run(
        ["git", "grep", "-aIl", "-E", signature.group(1), "--", "*.json", "*.txt", *excludes],
        cwd=_REPO,
        capture_output=True,
        check=False,
    )
    assert found.returncode in (0, 1), found.stderr.decode()
    assert found.stdout.decode().split() == []


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


# ── content detector (audit 2026-08-03 §5, ADR-0347) ───────────────────────────────────────
# Extension alone could never cover `.json`: it is deliberately absent from .gitignore (tracked
# config must stay visible) and it is the tool's OWN "Save .json" format. The hook now sniffs the
# STAGED bytes of .json / .txt / extension-less files for three decisive schedule signatures.

_SAVED_SCHEDULE = (
    b'{"name":"Runway","project_start":"2026-01-05T08:00:00",'
    b'"tasks":[{"unique_id":1,"name":"Mobilize","duration_minutes":480}]}'
)
_MSPDI = b'<?xml version="1.0"?><Project xmlns="http://schemas.microsoft.com/project"/>'
_XER = b"ERMHDR\t19.12\t2026-08-03\tProject\n"


def _stage(repo: Path, name: str, body: bytes) -> None:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    _run(repo, "git", "add", "-f", name)


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("schedule.json", _SAVED_SCHEDULE),  # the tool's own Save format
        ("notes.txt", b"handover notes\n" + _SAVED_SCHEDULE),  # renamed to dodge the denylist
        ("plan.json.bak", _SAVED_SCHEDULE),  # ...and backed up
        ("export", _XER),  # extension-less P6 export
        ("readme", _MSPDI),  # extension-less MSPDI
    ],
)
def test_hook_blocks_schedule_content_under_a_non_schedule_name(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) != 0, f"{name} carries a schedule and must be blocked"


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # A guard that fired on prose or config would be turned off, and then it guards nothing.
        ("README.txt", b"# Notes\nWe track tasks: design, build, close out.\n"),
        (".claude/settings.json", b'{"model":"opus","permissions":{"allow":[]}}'),
        ("package-ish.json", b'{"name":"x","scripts":{"test":"pytest"}}'),
        # Both allow-prefixes hold synthetic, hand-authored, non-CUI schedules by design.
        ("tests/fixtures/synthetic.json", _SAVED_SCHEDULE),
        ("src/schedule_forensics/web/examples/house_build.json", _SAVED_SCHEDULE),
    ],
)
def test_hook_allows_prose_config_and_the_synthetic_allowlists(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) == 0, f"{name} is not CUI and must commit freely"


def test_content_detector_reads_the_staged_bytes_not_the_working_tree(scratch_repo: Path) -> None:
    """Staging a schedule then scrubbing the file on disk must NOT get it through."""
    _stage(scratch_repo, "sneak.json", _SAVED_SCHEDULE)
    (scratch_repo / "sneak.json").write_bytes(b"{}")  # working tree now innocent, index is not
    assert _hook_exit(scratch_repo) != 0


def test_content_detector_does_not_fail_open_on_a_large_schedule(scratch_repo: Path) -> None:
    """A REAL schedule is hundreds of KB, and that size is where the detector nearly failed open.

    `git show ":$path" | head -c N | grep -q` looks correct and passes every small fixture. But a
    truncating reader SIGPIPEs its upstream, and under the hook's `set -o pipefail` the pipeline
    then reports failure *even though the signature matched* — so the guard allowed the commit.
    Measured 2026-08-03: a 281 KB saved schedule was ALLOWED while a 4 KB one was blocked. The fix
    reads through a process substitution, keeping `git show` out of the pipeline status entirely.

    Two things this test earned the hard way. The size must be well past the pipe buffer — below
    it, git finishes writing before the reader exits and the bug is invisible. And the *shape*
    matters: reverting only to the two-stage `git show | grep -q` does NOT reproduce it (that form
    happens to win the race), so falsifying this test requires the exact three-stage original.
    """
    tasks = ",".join(
        f'{{"unique_id":{i},"name":"Activity {i}","duration_minutes":480}}' for i in range(1, 4000)
    )
    big = f'{{"name":"Big","project_start":"2026-01-05T08:00:00","tasks":[{tasks}]}}'.encode()
    assert len(big) > 250_000, "the fixture must be large enough to expose the SIGPIPE race"
    _stage(scratch_repo, "big.json", big)
    assert _hook_exit(scratch_repo) != 0, "a large saved schedule must not slip through"
