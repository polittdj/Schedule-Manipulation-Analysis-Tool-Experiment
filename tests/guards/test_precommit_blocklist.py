"""Audit M2: the pre-commit CUI guard must block every extension CLAUDE.md Law 1 names.

CLAUDE.md states the guard "blocks ``.mpp``/``.xlsx``/``.aft``/``.xer``/``.docx``". This test reads
the *actual* ``blocked_re`` from ``.githooks/pre-commit`` and asserts each named CUI extension is
matched (case-insensitively, as the hook's ``grep -iE`` runs it) and that synthetic fixtures under
``tests/fixtures/`` stay exempt — so the spec and the hook implementation can't silently drift apart
again.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import zipfile
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


def _extension_alternation() -> str:
    """The blocked-extension alternation, read off the hook's own ``blocked_re``.

    Read the alternation itself rather than splitting on a literal tail: ADR-0399 turned the
    single-suffix clause into a chain, so the old ``split("(~?$")`` derivation would silently
    yield core == new and let the sweep below pass vacuously — the phase-2 trap (a source-text
    guard that stays green when its subject changes shape).
    """
    match = re.match(r"\\\.\(([a-z0-9|]+)\)", _blocked_re().pattern)
    assert match, "could not read the extension alternation from blocked_re"
    return match.group(1)


def test_the_suffix_clause_does_not_widen_the_net_over_the_tracked_tree() -> None:
    """The suffix chain must catch `data.mpp.bak`/`data.mpp.png` and NOTHING already in the repo.

    The intake legitimately tracks `.docx`/`.xlsx`/`.mpp` — ADR-0152's ``inherited_from_main``
    rule is what lets those ride a merge, and this test does not second-guess it. What it pins is
    that the 2026-08-03 widening and the 2026-08-14 disguise-suffix chain (ADR-0399) added
    **no new** matches: the obvious "blocked ext followed by any dot" silently claimed
    `tools/mpxj/lib/jakarta.xml.bind-api-3.0.1.jar`, whose Java package name merely contains
    ".xml.", which would wedge every MPXJ upgrade with a nonsense reason. Relying on the
    inherited-blob exception to paper over that would hide the wedge until the day the file
    legitimately changes.
    """
    new = _blocked_re()
    # the original core: the same extensions, anchored hard on end-of-name
    core = re.compile(r"\.(" + _extension_alternation() + r")$", re.IGNORECASE)
    allowed = _allow_prefixes()
    widened = [
        p
        for p in _tracked()
        if not p.startswith(allowed) and new.search(p.rsplit("/", 1)[-1]) and not core.search(p)
    ]
    assert widened == []


def test_the_suffix_sweep_can_detect_a_widening() -> None:
    """Negative control: the sweep's population and method CAN go red.

    The known-bad "blocked ext followed by any dot" mutant must claim the MPXJ jar over the
    same population the sweep scans. If this stops matching, the sweep above is measuring
    nothing (empty population, moved jar, or broken derivation) and its green is vacuous.
    """
    mutant = re.compile(r"\.(" + _extension_alternation() + r")(\..*)?$", re.IGNORECASE)
    core = re.compile(r"\.(" + _extension_alternation() + r")$", re.IGNORECASE)
    claimed = [
        p
        for p in _tracked()
        if mutant.search(p.rsplit("/", 1)[-1]) and not core.search(p.rsplit("/", 1)[-1])
    ]
    assert any("jakarta.xml.bind-api" in p for p in claimed), (
        "the any-dot mutant no longer claims the MPXJ jar — the widening sweep is vacuous"
    )


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


# ── HOOK-01: disguise suffixes, renamed schedules, containers (audit 2026-08-13, ADR-0399) ──
# The audit's scratch-repo battery proved a schedule renamed .png/.svg/.md, a blocked-ext
# double-extension (data.mpp.png), and a schedule-bearing PDF/ZIP all slipped both detectors.
# These tests are that battery, committed. Every BLOCK case was observed to ALLOW under the
# pre-ADR-0399 hook (red first), and every ALLOW case pins the false-positive boundary that
# keeps the guard from firing on legitimate content — a guard that fires on real screenshots
# or prose gets switched off, and then it guards nothing.

_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 504  # OLE2 CFB magic (.mpp/.xls/.doc)
_PNG_REAL = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
_SVG_REAL = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
_PROSE_MD = (
    b"# Audit notes\n\nThe save format looks like this:\n\n"
    b'```json\n{"tasks": [{"unique_id": 1}]}\n```\n\nAlso `ERMHDR` headers and\n'
    b'xmlns="http://schemas.microsoft.com/project" get quoted in docs.\n'
)
_PDF_PLAIN = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << >>\n%%EOF\n"
_PDF_EMBED = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Filespec /F (real.mpp) /EF << /F 2 0 R >> >> endobj\n"
    b"2 0 obj << /Type /EmbeddedFile /Length 4 >> stream\nDATA\nendstream endobj\n"
    b"trailer << >>\n%%EOF\n"
)


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # blocked extension hiding behind a disguise suffix — caught by NAME, any bytes
        ("data.mpp.png", b"junk"),
        ("sched.mpp.zip", b"junk"),
        ("export.xer.png", b"junk"),
        ("data.mpp.png.bak", b"junk"),  # a two-deep chain
        # a schedule renamed to an image/doc extension — caught by anchored CONTENT
        ("sched.png", _SAVED_SCHEDULE),
        ("notes.md", _MSPDI),
        ("chart.svg", _MSPDI),
        ("fake.pdf", _MSPDI),
        ("plan.md", _XER),
        # container renames — caught by MAGIC BYTES
        ("legacy.png", _OLE),
        ("legacy.json", _OLE),
        ("OLDSCHED", _OLE),  # extension-less OLE2 container
        ("archive.png", _zip_bytes({"logo.png": _PNG_REAL})),  # a ZIP is never a PNG
        # schedule-bearing containers under their own names
        ("data.zip", _zip_bytes({"real.mpp": b"bytes", "readme-file.rst": b"hi"})),
        ("book_renamed.zip", _zip_bytes({"[Content_Types].xml": b"<Types/>"})),
        ("report.pdf", _PDF_EMBED),
    ],
)
def test_hook_blocks_disguised_and_container_schedules(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) != 0, f"{name} hides a schedule artifact and must be blocked"


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # A guard that fired on legitimate images, diagrams, prose or reports would be
        # turned off, and then it guards nothing (the remediation plan's stated failure mode).
        ("screenshot.png", _PNG_REAL + b"image data"),
        ("diagram.svg", _SVG_REAL),
        # the measured false-positive shape: docs/STATE/AUDIT-2026-06-25.md QUOTES the save
        # signature mid-file; the anchored serialization-start gate must keep prose committable
        ("guide.md", _PROSE_MD),
        ("manual.pdf", _PDF_PLAIN),
        ("assets.zip", _zip_bytes({"logo.png": _PNG_REAL, "notes-file.rst": b"hi"})),
    ],
)
def test_hook_allows_legitimate_images_docs_and_archives(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) == 0, f"{name} is legitimate content and must commit freely"


# ── 2026-08-14 attack battery (ADR-0399): fail-open names, signature variants, FP bounds ──
# Three adversarial agents (evasion / false-positive / bash robustness) ran POC batteries
# against the fixed hook and found five defect classes; every case below was observed
# red (mis-verdict) against the pre-fix hook before the fix landed.

_MSPDI_SQ = b"<?xml version='1.0'?><Project xmlns='http://schemas.microsoft.com/project'/>"
_HUGO_MD = (
    b'{{< callout type="note" >}}\nThe save file is plain JSON:\n\n'
    b'```json\n{ "tasks": [ {"unique_id": 1} ] }\n```\n{{< /callout >}}\n\nMore prose here.\n'
)
_JEKYLL_MD = b'{% raw %}\n```json\n{ "tasks": [ {"unique_id": 1} ] }\n```\n{% endraw %}\n'
_PDF_EMBED_SPACED = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Filespec /F ( real.xer ) /EF << /F 2 0 R >> >> endobj\n"
    b"2 0 obj << /Type /EmbeddedFile /Length 4 >> stream\nDATA\nendstream endobj\n"
    b"trailer << >>\n%%EOF\n"
)
_PDF_BENIGN_ATTACH = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Filespec /F (notes.txt) /UF (notes.txt) /EF << /F 6 0 R >> >> endobj\n"
    b"6 0 obj << /Type /EmbeddedFile /Length 4 >> stream\nDATA\nendstream endobj\n"
    b"5 0 obj << /Length 62 >> stream\n"
    b"BT /F1 12 Tf 72 720 Td (For raw data see attached schedule.xml) Tj ET\n"
    b"endstream endobj\n"
    b"trailer << >>\n%%EOF\n"
)


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # C-quoting fail-open: git C-quotes non-ASCII names unless read with -z, and the
        # escaped token matched no detector while `git show` failed on it — a real CUI
        # schedule under an accented name committed SILENTLY (all three detectors bypassed).
        ("schädule.mpp", _OLE),
        ("xér häder.txt", _XER),
        ("café", _SAVED_SCHEDULE),
        ("plané.json", _OLE),
        # single-quoted xmlns is XML-spec-valid and loads as the identical schedule; the
        # old double-quote-literal signatures (bash AND python) both missed it
        ("s_sq_mspdi.png", _MSPDI_SQ),
        ("SCHEDULE_SQ", _MSPDI_SQ),
        # spaces inside the filespec parens are legal PDF syntax
        ("spaced_filespec.pdf", _PDF_EMBED_SPACED),
    ],
)
def test_hook_blocks_fail_open_names_and_signature_variants(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) != 0, f"{name} slipped a detector it must not slip"


@pytest.mark.skipif(sys.platform == "win32", reason="NTFS cannot create these names")
@pytest.mark.parametrize(
    ("name", "body"),
    [
        ('evil"quote.mpp', _OLE),  # double-quote in the name triggered C-quoting too
        ("sched.mpp ", _OLE),  # trailing space defeated every end-anchor
    ],
)
def test_hook_blocks_hostile_filename_shapes(scratch_repo: Path, name: str, body: bytes) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) != 0, f"{name!r} slipped past the name normalization"


@pytest.mark.parametrize(
    ("name", "body"),
    [
        # a templated doc STARTS with '{' ('{{<' Hugo, '{%' Jekyll) yet is prose; the brace
        # must open a JSON OBJECT before the save signature counts
        ("hugo_shortcode.md", _HUGO_MD),
        ("jekyll_raw.md", _JEKYLL_MD),
        # a benign-attachment PDF whose PRINTED page text mentions 'schedule.xml': the
        # attachment rule must bind to the /F filespec, not any paren-string in the blob
        ("benign_attach_mention.pdf", _PDF_BENIGN_ATTACH),
    ],
)
def test_hook_allows_templated_docs_and_benign_attachments(
    scratch_repo: Path, name: str, body: bytes
) -> None:
    _stage(scratch_repo, name, body)
    assert _hook_exit(scratch_repo) == 0, f"{name} is legitimate content and must commit freely"


def test_container_detector_reads_the_staged_bytes_not_the_working_tree(
    scratch_repo: Path,
) -> None:
    """Staging an OLE2 container then scrubbing the file on disk must NOT get it through."""
    _stage(scratch_repo, "sneaky.png", _OLE)
    (scratch_repo / "sneaky.png").write_bytes(_PNG_REAL)  # working tree innocent, index is not
    assert _hook_exit(scratch_repo) != 0


def test_hook_without_python3_keeps_the_extension_and_text_floor(scratch_repo: Path) -> None:
    """With python3 absent the guard must hold its pre-ADR-0399 floor and say what it skipped.

    Detectors 1-2 (extension chain + .json/.txt/extension-less text sniff) are pure
    bash/git/grep and must still block; the container detector is documented as requiring
    python3, and the hook must WARN rather than silently narrow.
    """
    thin = scratch_repo / "thinbin"
    thin.mkdir()
    for tool in ("git", "grep"):
        located = shutil.which(tool)
        assert located, f"{tool} not on PATH"
        (thin / tool).symlink_to(located)
    bash = shutil.which("bash")
    assert bash

    def run_bare() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [bash, str(_HOOK)],
            cwd=scratch_repo,
            env={"PATH": str(thin), "HOME": str(scratch_repo)},
            capture_output=True,
            text=True,
            check=False,
        )

    # floor holds: the classic text sniff still blocks the tool's own save format
    _stage(scratch_repo, "sched.json", _SAVED_SCHEDULE)
    assert run_bare().returncode != 0
    _run(scratch_repo, "git", "reset")
    # the container-only case is skipped WITH a warning — never silently
    _stage(scratch_repo, "legacy.png", _OLE)
    bare = run_bare()
    assert bare.returncode == 0  # documented fallback limitation, not an endorsement
    assert "python3 not found" in bare.stderr


def test_the_full_detector_stack_finds_nothing_in_the_repos_own_tree(tmp_path: Path) -> None:
    """Stage every tracked file outside the intake/allow-prefixes and run the REAL hook: zero hits.

    This is the behavioural companion to the git-grep census above, run through the actual
    hook so the anchored text rules and container checks are exercised on the repo's real
    bytes — a guard that fires on the repo's own sources gets switched off within a day.

    Two controls make the green meaningful: a planted schedule canary MUST be the one and only
    flagged path (an empty sweep with no positive control proves nothing), and the staged-file
    count must equal the copied population (the 2026-08-13 audit found a sandbox census whose
    ``git add`` silently skipped gitignored-but-tracked files — a census that cannot see part
    of its population under-reports by construction).

    ``00_REFERENCE_INTAKE/`` is excluded exactly as the sibling census excludes it:
    operator-uploaded through the GitHub web UI and covered by ``inherited_from_main``.
    """
    skip = ("00_REFERENCE_INTAKE/", *_allow_prefixes())
    tracked = [p for p in _tracked() if not p.startswith(skip)]
    assert len(tracked) > 900, f"population implausibly small: {len(tracked)}"

    repo = tmp_path / "census"
    repo.mkdir()
    _run(repo, "git", "init", "-q", "-b", "main")
    _run(repo, "git", "config", "user.email", "t@t")
    _run(repo, "git", "config", "user.name", "t")
    for rel in tracked:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((_REPO / rel).read_bytes())
    canary = "schedule_canary.png"
    (repo / canary).write_bytes(_MSPDI)

    listing = repo / "population.nul"
    listing.write_text("\0".join([*tracked, canary]), encoding="utf-8")
    _run(repo, "git", "add", "-f", "--pathspec-from-file=population.nul", "--pathspec-file-nul")
    staged = [
        p
        for p in _run(repo, "git", "diff", "--cached", "--name-only").stdout.splitlines()
        if p and p != "population.nul"
    ]
    assert len(staged) == len(tracked) + 1, "census population and staged set diverge"

    proc = _run(repo, "bash", str(_HOOK))
    assert proc.returncode != 0, "the planted canary was not caught — the census is vacuous"
    flagged = [ln.strip() for ln in proc.stderr.splitlines() if ln.strip().startswith("- ")]
    assert flagged == [f"- {canary}  (MSPDI XML content under a non-schedule name)"], (
        f"the hook flagged the repo's own files: {flagged}"
    )
