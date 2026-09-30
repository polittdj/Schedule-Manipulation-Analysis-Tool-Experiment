"""LODESTAR.pyz — the ONE file the operator shares — is exactly what ``src`` says it is, runs on
bare Python, and says who made it (ADR-0539).

The operator asked (2026-09-29) for the One-Pager Timeline and Compare as "a separate program of
their own that I can share with others", citing "David Politte" and "david.j.politte@nasa.gov".
``tools/lodestar/build_lodestar.py`` packs files of ``src/`` VERBATIM into
``lodestar/LODESTAR.pyz``; this module pins, against the COMMITTED file (what is shared):

* **Lockstep** — the committed file is byte-identical to a fresh ``build()``, and a mismatch
  names the rebuild command and the members that differ; ``build()`` is deterministic, and blind
  to where the sources sit and to their mtime and mode.
* **Contents** — the member list is exactly ``members()`` (sorted, no directory entries, fixed
  stored headers) AND exactly the 34 names typed here (an oracle the builder cannot move — no
  ``docx.py``), and every member is its source file's bytes as committed (a CRLF checkout's
  text read as LF); a CRLF copy of every member source builds the identical archive (LS-08);
  every import in every member — a lazy one inside a function included — is std-lib or another
  member; no member name (and no file shipped beside it) is one the pre-commit hook's
  ``blocked_re`` refuses; with no python3 on the PATH each POSIX launcher says how it is started
  again and exits non-zero.
* **Runs on bare Python** — under ``python -I -S`` every module in the archive imports and brings
  in nothing but the std-lib and the archive's own package; started as the launchers start it,
  the archive's import path is itself plus the interpreter's own std-lib directories and nothing
  else (a PYTHONPATH entry under the install prefix included); ``--help`` prints on an ASCII
  console.
* **End to end** — the shipped file started as the operator starts it (``--no-browser``):
  the banner credits the author, the page's contact link is a bare ``mailto:``, a twin workbook in
  the C-start / D-finish / E-complete layout uploads, a logic link is added and exported to
  PowerPoint (a ``Logic link:`` group; the deck is LODESTAR's, never POLARIS'), Quit stops it with
  exit status 0 and an EMPTY stderr. The Linux launcher does the same. (Quit's own "has stopped"
  page could be cut off by the exit — found here, fixed by ADR-0539's review: the server stops
  only once that page is written, pinned by the Quit test at the end.)

Red-first (2026-09-29, ADR-0539): on the pristine tree (HEAD 0b45eb2) there is no
``tools/lodestar`` and no ``lodestar/`` — every test here fails. On the change's own worktree
the two lockstep tests were observed RED for real (``web/onepager.py`` gained a ``# nosec``
comment after the file was built) and green on a scratch copy after the rebuild. Each
load-bearing check has a ``test_mutation_*`` twin that breaks the thing and asserts the SAME
checker goes red by name: a flipped source byte, an mtime-dependent builder, a disguised CUI
member name, a lazy third-party import, and a foreign module riding into the archive (which the
archive's own ``__main__`` must refuse, exit 2, naming it).

The ADR-0539 review pins (2026-09-29) were each observed RED on HEAD f40faa04 for the stated
reason before the fix: the members test on a simulated CRLF checkout (33 members named, LSB-2);
the launchers with no python3 (Linux told to double-click; both exited 0 after Enter); the
import path (``/usr/lib``, ``/usr/include``, ``/usr/share`` kept ahead of the std-lib; a ``/``
prefix kept no std-lib at all, LSB-3); ``--help`` on an ASCII / cp437 console (exit 1,
UnicodeEncodeError, LSB-1). The LS-08 and 34-member pins cannot be red on a tree where the claim
holds; their twins are the pre-LS-08 builder (raw bytes) and ``docx.py`` added to ``MODULES``.
"""

from __future__ import annotations

import ast
import http.client
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from lodestar_probe import (
    AUTHOR,
    CONTACT,
    MAILTO,
    ROWS,
    Reply,
    deck_members,
    deck_shapes,
    form,
    request,
    upload,
)

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "lodestar" / "build_lodestar.py"
SHIPPED = ROOT / "lodestar"
PYZ = SHIPPED / "LODESTAR.pyz"
HOOK = ROOT / ".githooks" / "pre-commit"
#: Independent literals — what the file must start with and be built by (never read off the tool).
SHEBANG = b"#!/usr/bin/env python3\n"
REBUILD = "python tools/lodestar/build_lodestar.py"
#: Where the two renamed members come from (the tool's docstring, typed here as the oracle).
MAIN_SOURCE = ROOT / "src" / "schedule_forensics" / "lodestar" / "_pyz_main.py"
WEB_INIT_SOURCE = ROOT / "src" / "schedule_forensics" / "lodestar" / "_pyz_web_init.py"
ONEPAGER_MEMBER = "schedule_forensics/reports/onepager.py"

_RUNNING = re.compile(r"Running at http://127\.0\.0\.1:(\d+)/onepager\b")
_OPTION = re.compile(r'<option value="([^"]*)" title="([^"]*)">')
DR = "Alpha · Design Review (1/15/27)"
BUILD = "Alpha · Build (2/1/27 to 4/15/27)"


@pytest.fixture
def tool() -> ModuleType:
    """A fresh copy of the build tool per test, so a monkeypatched ``SRC`` never leaks."""
    spec = importlib.util.spec_from_file_location("build_lodestar_under_test", TOOL)
    assert spec is not None and spec.loader is not None, f"no build tool at {TOOL}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── helpers ───────────────────────────────────────────────────────────────────────────────────


def _contents(data: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return {name: zf.read(name) for name in zf.namelist()}
    except zipfile.BadZipFile:
        return {}


def _differing(a: bytes, b: bytes) -> list[str]:
    """Member names whose bytes differ between two archives (or exist in only one)."""
    x, y = _contents(a), _contents(b)
    return sorted(n for n in x.keys() | y.keys() if x.get(n) != y.get(n))


def _lockstep_problem(committed: bytes, fresh: bytes, rebuild: str) -> str | None:
    """``None`` when the committed file IS the fresh build; else the sentence that says what to
    run and which members moved."""
    if committed == fresh:
        return None
    moved = ", ".join(_differing(committed, fresh)) or "(the header, order or framing)"
    return (
        f"lodestar/LODESTAR.pyz is not byte-identical to a fresh build — run: {rebuild} "
        f"(members that differ: {moved})"
    )


def _copy_sources(tool: ModuleType, dst: Path) -> None:
    """Every member's SOURCE file, copied under ``dst`` at its path relative to ``src/``."""
    for path in tool.members().values():
        rel = Path(path).relative_to(tool.SRC)
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_bytes(Path(path).read_bytes())


def _retouch(root: Path) -> None:
    """Change every file's mtime and mode, not its bytes."""
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, (1_000_000_000, 1_000_000_000))
            path.chmod(0o600)


def _naive_build(tool: ModuleType) -> bytes:
    """A builder that DOES depend on mtime and mode (``ZipFile.write``) — the determinism probe
    must be able to tell it from the real one."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for name, path in tool.members().items():
            zf.write(path, name)
    return buf.getvalue()


def _blocked_re() -> re.Pattern[str]:
    """The hook's own ``blocked_re`` (the ``tests/guards/test_precommit_blocklist.py`` idiom),
    case-insensitive as the hook's ``grep -qiE`` applies it."""
    match = re.search(r"blocked_re='([^']+)'", HOOK.read_text(encoding="utf-8"))
    assert match, "could not find blocked_re in .githooks/pre-commit"
    return re.compile(match.group(1), re.IGNORECASE)


def _blocked(names: list[str], pattern: re.Pattern[str]) -> list[str]:
    """The names the hook would refuse — matched on the base name, as the hook matches."""
    return [n for n in names if pattern.search(n.rsplit("/", 1)[-1].rstrip())]


def _module_file(module: str, names: set[str]) -> str | None:
    """The archive member that IS ``module`` (a module file or a package ``__init__``)."""
    stem = module.replace(".", "/")
    for cand in (f"{stem}.py", f"{stem}/__init__.py"):
        if cand in names:
            return cand
    return None


def _import_problems(members: dict[str, bytes]) -> list[str]:
    """Every import statement in every ``.py`` member — module level or inside a function —
    that names neither the std-lib nor another member (a from-import of a SUBMODULE that exists
    in ``src`` counts as importing it)."""
    names = set(members)
    std = set(sys.stdlib_module_names)
    problems: list[str] = []

    def check(member: str, module: str) -> None:
        top = module.split(".")[0]
        if top in std:
            return
        if top != "schedule_forensics":
            problems.append(f"{member} imports {module} (not std-lib)")
        elif _module_file(module, names) is None:
            problems.append(f"{member} imports {module} (not in the archive)")

    for member, data in sorted(members.items()):
        if not member.endswith(".py"):
            continue
        package = member[:-3].split("/")[:-1]
        for node in ast.walk(ast.parse(data)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    check(member, alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = package[: len(package) - node.level + 1] if node.level else []
                module = ".".join([*base, *(node.module or "").split(".")]).strip(".")
                check(member, module)
                if not module.startswith("schedule_forensics"):
                    continue
                for alias in node.names:
                    sub = f"{module}.{alias.name}"
                    rel = Path("src", *sub.split("."))
                    if (ROOT / f"{rel}.py").is_file() or (ROOT / rel / "__init__.py").is_file():
                        check(member, sub)
    return problems


_CENSUS = r"""
import importlib, json, sys
pyz, modules = sys.argv[1], sys.argv[2:]
sys.path.insert(0, pyz)
before = set(sys.modules)
for name in modules:
    importlib.import_module(name)
new = {n.split(".")[0] for n in set(sys.modules) - before}
print(json.dumps({
    "non_std": sorted(new - set(sys.stdlib_module_names)),
    "outside": sorted(
        n for n in modules if not (getattr(sys.modules[n], "__file__", "") or "").startswith(pyz)
    ),
}))
"""


def _census(pyz: Path, cwd: Path) -> dict[str, list[str]]:
    """Import every module of ``pyz`` under ``python -I -S`` (no site-packages, no user paths, no
    environment) and report the top-level names that import brought in that are not std-lib,
    and any module that loaded from somewhere other than the archive."""
    with zipfile.ZipFile(pyz) as zf:
        modules = [
            n[:-3].replace("/", ".").removesuffix(".__init__")
            for n in zf.namelist()
            if n.endswith(".py") and n != "__main__.py"
        ]
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-c", _CENSUS, str(pyz), *modules],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=cwd,
        check=False,
    )
    assert proc.returncode == 0, f"the archive did not import under -I -S:\n{proc.stderr}"
    return dict(json.loads(proc.stdout))


def _clean_env() -> dict[str, str]:
    """The environment a double-click gets: no PYTHONPATH into this checkout, no coverage hook."""
    drop = {"PYTHONPATH", "PYTHONSTARTUP", "COVERAGE_PROCESS_START", "COVERAGE_PROCESS_CONFIG"}
    return {k: v for k, v in os.environ.items() if k not in drop}


def _launch(cmd: list[str], work: Path) -> tuple[subprocess.Popen[bytes], int, Path, Path]:
    """Start LODESTAR, wait (bounded) for its banner, return ``(process, port, stdout, stderr)``
    — the two streams go to files, so nothing can block on a full pipe."""
    out, err = work / "stdout.txt", work / "stderr.txt"
    with out.open("wb") as fo, err.open("wb") as fe:
        proc = subprocess.Popen(
            cmd, cwd=work, stdout=fo, stderr=fe, stdin=subprocess.DEVNULL, env=_clean_env()
        )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        found = _RUNNING.search(out.read_text(encoding="utf-8", errors="replace"))
        if found:
            return proc, int(found.group(1)), out, err
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)
    pytest.fail(
        f"LODESTAR never printed its address (exit {proc.returncode}):\n"
        f"stdout: {out.read_text(errors='replace')!r}\nstderr: {err.read_text(errors='replace')!r}"
    )


def _stop(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=10)


#: What a cut-off reply looks like to a client (the Quit race — see the Quit test below).
_CUT = (http.client.RemoteDisconnected, http.client.IncompleteRead, ConnectionResetError)


def _quit(port: int) -> Reply | None:
    """Press Quit. ``None`` when the reply was cut off (the race the Quit test below pins shut) —
    the tests that need the PROCESS to stop assert the exit; the Quit test asserts the page."""
    try:
        return form(port, "/quit", {})
    except _CUT:
        return None


def _keys(page: str) -> dict[str, str]:
    """Every linkable item's full label -> its key, read off the page's own From select."""
    select = re.search(r"<select\b[^>]*\bid=opLinkFrom\b[^>]*>(.*?)</select>", page, re.S)
    assert select, "no From select on /onepager"
    return {title: value for value, title in _OPTION.findall(select.group(1))}


# ── lockstep ──────────────────────────────────────────────────────────────────────────────────


def test_committed_pyz_is_byte_identical_to_a_fresh_build(tool: ModuleType) -> None:
    """The file that is shared IS ``src`` today — else the message says what to run."""
    assert tool.REBUILD == REBUILD, "the tool's rebuild command drifted from the documented one"
    assert (ROOT / REBUILD.split()[-1]).resolve() == TOOL.resolve()
    assert PYZ.is_file(), f"{PYZ} is missing — run: {REBUILD}"
    problem = _lockstep_problem(PYZ.read_bytes(), tool.build(), tool.REBUILD)
    assert problem is None, problem


def test_mutation_one_flipped_source_byte_changes_exactly_that_member(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: one byte of ``reports/onepager.py`` flipped in a copy of the sources — the build
    differs in exactly that member and the lockstep message names it AND the rebuild."""
    original = tool.build()
    src = tmp_path / "src"
    _copy_sources(tool, src)
    target = src / ONEPAGER_MEMBER
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x20
    target.write_bytes(bytes(data))
    monkeypatch.setattr(tool, "SRC", src)
    mutated = tool.build()
    assert _differing(original, mutated) == [ONEPAGER_MEMBER]
    problem = _lockstep_problem(original, mutated, tool.REBUILD)
    assert problem is not None and REBUILD in problem and ONEPAGER_MEMBER in problem, problem


def test_check_flag_goes_red_by_name_on_a_stale_file(
    tool: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--check`` (what CLAUDE.md and the full gate name) passes a current file and fails a
    stale one, printing the rebuild command — measured on a scratch output, never the real one."""
    out = tmp_path / "lodestar" / "LODESTAR.pyz"
    out.parent.mkdir()
    out.write_bytes(tool.build())
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "OUT", out)
    assert tool.main(["--check"]) == 0
    src = tmp_path / "src"
    _copy_sources(tool, src)
    target = src / ONEPAGER_MEMBER
    target.write_bytes(target.read_bytes() + b"\n")
    monkeypatch.setattr(tool, "SRC", src)
    capsys.readouterr()
    assert tool.main(["--check"]) == 1
    assert REBUILD in capsys.readouterr().out


def test_build_is_deterministic_and_blind_to_location_mtime_and_mode(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two builds are equal; so is a build of the same bytes elsewhere, and after every source's
    mtime and mode changed — the lockstep can only ever fail on a real content change."""
    first = tool.build()
    assert tool.build() == first
    src = tmp_path / "src"
    _copy_sources(tool, src)
    monkeypatch.setattr(tool, "SRC", src)
    assert tool.build() == first, "the same bytes in another place built differently"
    _retouch(src)
    assert tool.build() == first, "a new mtime or mode changed the archive"


def test_mutation_determinism_probe_catches_an_mtime_dependent_builder(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the same retouch DOES change a ``ZipFile.write`` build — so the probe above can
    see mtime/mode dependence, and its green is not vacuous."""
    src = tmp_path / "src"
    _copy_sources(tool, src)
    monkeypatch.setattr(tool, "SRC", src)
    before = _naive_build(tool)
    _retouch(src)
    assert _naive_build(tool) != before


# ── contents ──────────────────────────────────────────────────────────────────────────────────


def test_archive_starts_with_the_shebang() -> None:
    data = PYZ.read_bytes()
    assert data.startswith(SHEBANG), data[:40]
    assert zipfile.is_zipfile(PYZ)


def _git_text(data: bytes) -> bool:
    """What git calls text (and ``* text=auto`` converts on a Windows checkout): no NUL byte in
    the first 8000 — git's own test, independent of the builder's suffix list."""
    return b"\0" not in data[:8000]


def _as_committed(path: Path) -> bytes:
    """A source file's bytes as the COMMIT holds them: a text file's CRLF (a Git-for-Windows
    autocrlf checkout) read back as LF; a binary file as it is."""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if _git_text(data) else data


def test_members_are_exactly_the_allowlist_and_each_is_its_source_verbatim(
    tool: ModuleType,
) -> None:
    """The committed member list equals ``members()`` — same names, same (sorted) order, nothing
    extra — every member's bytes are its source file's bytes AS COMMITTED (a text file's CRLF
    read as LF, so a Git-for-Windows autocrlf checkout of the same commit passes too: LSB-2), the
    two renamed members come from the two ``src`` files the tool documents, and every header is
    the fixed stored one."""
    expected = tool.members()
    with zipfile.ZipFile(PYZ) as zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]
        assert names == list(expected), sorted(set(names) ^ set(expected))
        wrong = [n for n in names if zf.read(n) != _as_committed(Path(expected[n]))]
        assert not wrong, f"members that are not their source's bytes: {wrong}"
        assert zf.read("__main__.py") == _as_committed(MAIN_SOURCE)
        assert zf.read("schedule_forensics/web/__init__.py") == _as_committed(WEB_INIT_SOURCE)
    odd = [
        i.filename
        for i in infos
        if i.is_dir()
        or i.compress_type != zipfile.ZIP_STORED
        or i.date_time != (1980, 1, 1, 0, 0, 0)
        or i.create_system != 3
        or i.external_attr >> 16 != 0o644
    ]
    assert not odd, f"members without the fixed stored header: {odd}"


#: The archive's members, typed here from ADR-0539 (LS-07: 34 members, no ``docx.py`` — LODESTAR
#: serves no Word export) and ADR-0541 (42: the launch page — ``lodestar_launch.py``, the boot
#: screen's ``launch.js`` / ``launch_audio.js`` / ``launch.css`` and LODESTAR's own
#: ``lodestar_launch.css`` — the first-run Desktop shortcut ``shortcut.py`` with the icon writer
#: ``desktop_icon.py`` and LODESTAR's own ``lodestar.ico``). An INDEPENDENT oracle: the lockstep
#: and the test above both judge the archive against the builder's own list, so a module added to
#: ``MODULES`` and rebuilt would pass them both (SLA-7). Changing what LODESTAR ships means
#: changing this list, on purpose.
MEMBERS = (
    "__main__.py",
    "schedule_forensics/__init__.py",
    "schedule_forensics/desktop_icon.py",
    "schedule_forensics/lodestar/__init__.py",
    "schedule_forensics/lodestar/__main__.py",
    "schedule_forensics/lodestar/server.py",
    "schedule_forensics/lodestar/shortcut.py",
    "schedule_forensics/reports/__init__.py",
    "schedule_forensics/reports/onepager.py",
    "schedule_forensics/reports/onepager_compare.py",
    "schedule_forensics/reports/onepager_links.py",
    "schedule_forensics/reports/pptx.py",
    "schedule_forensics/reports/tableset.py",
    "schedule_forensics/reports/xlsx.py",
    "schedule_forensics/reports/xlsx_read.py",
    "schedule_forensics/web/__init__.py",
    "schedule_forensics/web/htmlkit.py",
    "schedule_forensics/web/lodestar_launch.py",
    "schedule_forensics/web/lodestar_shell.py",
    "schedule_forensics/web/onepager.py",
    "schedule_forensics/web/onepager_actions.py",
    "schedule_forensics/web/onepager_common.py",
    "schedule_forensics/web/onepager_compare.py",
    "schedule_forensics/web/security.py",
    "schedule_forensics/web/static/app.css",
    "schedule_forensics/web/static/base.css",
    "schedule_forensics/web/static/chartframe.js",
    "schedule_forensics/web/static/favicon.ico",
    "schedule_forensics/web/static/gantt.js",
    "schedule_forensics/web/static/hud.css",
    "schedule_forensics/web/static/launch.css",
    "schedule_forensics/web/static/launch.js",
    "schedule_forensics/web/static/launch_audio.js",
    "schedule_forensics/web/static/lodestar.css",
    "schedule_forensics/web/static/lodestar.ico",
    "schedule_forensics/web/static/lodestar_launch.css",
    "schedule_forensics/web/static/onepager.js",
    "schedule_forensics/web/static/onepager_compare.js",
    "schedule_forensics/web/static/onepager_links.js",
    "schedule_forensics/web/static/panelkit.js",
    "schedule_forensics/web/static/sf-themes.css",
    "schedule_forensics/web/static/theme.js",
)


def _member_list_problem(names: list[str]) -> str | None:
    """``None`` when ``names`` are exactly :data:`MEMBERS`, in order, and none is a Word writer."""
    docx = [n for n in names if "docx" in n.lower()]
    if names == list(MEMBERS) and not docx:
        return None
    extra, missing = sorted(set(names) - set(MEMBERS)), sorted(set(MEMBERS) - set(names))
    return f"archive members: extra {extra}, missing {missing}, a Word writer {docx}"


def test_the_archive_holds_exactly_the_42_members_adr_0539_and_0541_name(tool: ModuleType) -> None:
    assert len(MEMBERS) == 42
    with zipfile.ZipFile(PYZ) as zf:
        problem = _member_list_problem(zf.namelist())
    assert problem is None, problem
    assert _member_list_problem(list(tool.members())) is None


def test_mutation_a_module_added_to_the_builder_is_named(
    tool: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (SLA-7): ``reports/docx.py`` added to ``MODULES`` and the archive rebuilt — the
    lockstep's oracle moves with it, this one does not."""
    monkeypatch.setattr(tool, "MODULES", (*tool.MODULES, "schedule_forensics/reports/docx.py"))
    names = list(_contents(tool.build()))
    problem = _member_list_problem(names)
    assert problem is not None and "schedule_forensics/reports/docx.py" in problem, problem


def _crlf_copy(tool: ModuleType, dst: Path) -> int:
    """Every member's source copied under ``dst`` the way Git for Windows checks it out
    (``* text=auto``, autocrlf): each git-text file with CRLF line ends. Returns how many."""
    _copy_sources(tool, dst)
    converted = 0
    for path in dst.rglob("*"):
        data = path.read_bytes() if path.is_file() else b""
        if data and _git_text(data):
            path.write_bytes(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            converted += 1
    return converted


def _crlf_problem(tool: ModuleType, lf: bytes, crlf: bytes) -> str | None:
    if crlf == lf:
        return None
    return f"a CRLF checkout builds a different archive (members: {_differing(lf, crlf)})"


def test_ls08_a_crlf_checkout_builds_the_identical_archive(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LS-08: every member source a Windows (autocrlf) checkout would convert, converted to CRLF
    — the build is byte-identical to the LF build. Every member git treats as text is covered,
    whatever its suffix, so a future text asset the builder does not normalise goes red here."""
    lf = tool.build()
    src = tmp_path / "src"
    converted = _crlf_copy(tool, src)
    assert converted == len(MEMBERS) - 2, converted  # all but the two icons (binary; ADR-0541)
    monkeypatch.setattr(tool, "SRC", src)
    problem = _crlf_problem(tool, lf, tool.build())
    assert problem is None, problem


def test_mutation_a_builder_that_packs_raw_bytes_fails_the_crlf_pin(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the builder before LS-08 (members packed as read) — the CRLF build differs and
    the same checker names the text members."""
    lf = tool.build()
    src = tmp_path / "src"
    _crlf_copy(tool, src)
    monkeypatch.setattr(tool, "SRC", src)
    monkeypatch.setattr(tool, "_member_bytes", lambda path: path.read_bytes())
    problem = _crlf_problem(tool, lf, tool.build())
    assert problem is not None and "schedule_forensics/lodestar/server.py" in problem, problem


def test_static_members_are_exactly_what_the_server_serves(tool: ModuleType) -> None:
    """The tool reads the server's ``STATIC_ASSETS`` by parsing source; the server imports its
    own dict. The two readings must agree, and every served asset must be in the archive."""
    from schedule_forensics.lodestar.server import STATIC_ASSETS

    assert tool.static_assets() == tuple(sorted(STATIC_ASSETS))
    with zipfile.ZipFile(PYZ) as zf:
        static = {
            n.removeprefix("schedule_forensics/web/static/")
            for n in zf.namelist()
            if n.startswith("schedule_forensics/web/static/")
        }
    assert static == set(STATIC_ASSETS)


def test_every_import_in_every_member_resolves_inside_the_archive() -> None:
    """A lazy import inside a function is invisible to an import census; read every import
    statement instead. Each must be std-lib or another member of the archive."""
    problems = _import_problems(_contents(PYZ.read_bytes()))
    assert problems == []


def test_mutation_import_scan_names_a_lazy_third_party_and_a_missing_module() -> None:
    """MUTATION: a function-level ``import requests`` and a lazy import of the engine appended to
    one member — the scan names both."""
    members = _contents(PYZ.read_bytes())
    members[ONEPAGER_MEMBER] += (
        b"\n\ndef _later():\n    import requests\n"
        b"    from schedule_forensics.engine import cpm\n    return requests, cpm\n"
    )
    problems = "\n".join(_import_problems(members))
    assert "imports requests (not std-lib)" in problems
    assert "imports schedule_forensics.engine (not in the archive)" in problems
    assert "imports schedule_forensics.engine.cpm (not in the archive)" in problems


def test_no_shipped_name_is_one_the_precommit_hook_blocks() -> None:
    """Neither a member of the archive nor a file shipped beside it carries a name the hook's
    ``blocked_re`` refuses (a blocked member would make the hook's ZIP detector refuse the file)."""
    pattern = _blocked_re()
    with zipfile.ZipFile(PYZ) as zf:
        names = zf.namelist()
    shipped = [f"lodestar/{p.name}" for p in SHIPPED.iterdir()]
    assert _blocked(names + shipped, pattern) == []


def test_mutation_blocked_member_names_are_caught() -> None:
    """MUTATION: a workbook and a disguised schedule added to the member list are named."""
    pattern = _blocked_re()
    with zipfile.ZipFile(PYZ) as zf:
        names = zf.namelist()
    bad = ["schedule_forensics/web/static/plan.xlsx", "schedule_forensics/sched.mpp.zip"]
    assert _blocked(names + bad, pattern) == bad


def test_launchers_and_readme_credit_the_author_and_keep_their_line_ends() -> None:
    """Every file shipped beside the archive names the author and his address; the launchers
    start the archive beside them; ``LODESTAR.bat`` is CRLF throughout (cmd.exe misreads labels in
    an LF file) and the two POSIX launchers are LF-only, executable, ``#!/bin/sh`` scripts; the
    README states the operator's column layout (C start, D finish, E complete)."""
    for name in ("LODESTAR.bat", "LODESTAR.command", "lodestar.sh", "README.md"):
        text = (SHIPPED / name).read_text(encoding="utf-8")
        assert AUTHOR in text and CONTACT in text, name
    for name in ("LODESTAR.bat", "LODESTAR.command", "lodestar.sh"):
        assert "LODESTAR.pyz" in (SHIPPED / name).read_text(encoding="utf-8"), name
    bat = (SHIPPED / "LODESTAR.bat").read_bytes()
    assert bat.count(b"\n") == bat.count(b"\r\n") > 0, "LODESTAR.bat must be CRLF throughout"
    for name in ("LODESTAR.command", "lodestar.sh"):
        data = (SHIPPED / name).read_bytes()
        assert data.startswith(b"#!/bin/sh\n") and b"\r" not in data, name
        if os.name != "nt":
            assert (SHIPPED / name).stat().st_mode & stat.S_IXUSR, f"{name} is not executable"
    readme = (SHIPPED / "README.md").read_text(encoding="utf-8")
    assert f"(mailto:{CONTACT})" in readme
    for col, word in (("C", "start"), ("D", "finish"), ("E", "complete")):
        assert re.search(rf"^\| \*\*{col}\*\* \|[^\n]*\b{word}\b", readme, re.M | re.I), col


#: What each POSIX launcher tells a recipient with no Python, and how it is started again
#: (DOC-LS-08: Linux runs ``sh lodestar.sh`` — README — and is never told to double-click).
_NO_PYTHON = {
    "lodestar.sh": "Install it from python.org, then run sh lodestar.sh again.",
    "LODESTAR.command": "Install it from python.org, then double-click LODESTAR again.",
}


def _no_python_run(launcher: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run a POSIX launcher with a PATH that holds ``dirname`` and nothing else — no python3 —
    and press Enter at its pause (at end-of-input ``read`` itself fails, and its status would
    mask the launcher's own)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    dirname = shutil.which("dirname")
    assert dirname, "no dirname on this machine"
    link = bin_dir / "dirname"
    if not link.exists():
        link.symlink_to(dirname)
    return subprocess.run(
        ["/bin/sh", str(launcher)],
        env={"PATH": str(bin_dir)},
        input="\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.skipif(os.name == "nt", reason="the POSIX launchers run under /bin/sh")
@pytest.mark.parametrize("name", sorted(_NO_PYTHON))
def test_a_launcher_with_no_python_says_how_to_start_again_and_fails(
    name: str, tmp_path: Path
) -> None:
    """No python3 on the PATH: the launcher says so in words that fit how it is started, and
    exits NON-zero (a script that failed must not report success to whatever ran it)."""
    proc = _no_python_run(SHIPPED / name, tmp_path)
    said = " ".join(proc.stdout.split())
    assert "none was found" in said and _NO_PYTHON[name] in said, said
    if name == "lodestar.sh":
        assert "double-click" not in said, said
    assert proc.returncode != 0, (proc.returncode, said)


# ── runs on bare Python ───────────────────────────────────────────────────────────────────────


def test_pyz_imports_under_isolated_python_with_no_third_party_module(tmp_path: Path) -> None:
    """Under ``python -I -S`` every module of the shipped file imports, from the file, bringing
    in no top-level name but the std-lib's and ``schedule_forensics``."""
    census = _census(PYZ, tmp_path)
    assert census == {"non_std": ["schedule_forensics"], "outside": []}


def _evil_pyz(tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the archive plus a top-level ``evil_client`` module that LODESTAR's own
    ``__main__`` imports — a network client riding in unnoticed."""
    evil = tmp_path / "evil_client.py"
    evil.write_text('"""A stand-in third-party network client."""\n', encoding="utf-8")
    real = tool.members()
    main_member = "schedule_forensics/lodestar/__main__.py"
    source = Path(real[main_member]).read_text(encoding="utf-8")
    anchor = "import webbrowser\n"
    assert anchor in source, "the mutation's anchor line moved"
    bad_main = tmp_path / "bad_main.py"
    bad_main.write_text(source.replace(anchor, anchor + "import evil_client\n", 1), "utf-8")
    patched = {**real, "evil_client.py": evil, main_member: bad_main}
    monkeypatch.setattr(tool, "members", lambda: dict(sorted(patched.items())))
    out = tmp_path / "EVIL.pyz"
    out.write_bytes(tool.build())
    return out


def test_mutation_a_foreign_module_is_refused_at_start_and_seen_by_the_census(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the archive's ``__main__`` refuses to start (exit 2, naming the module, before
    it ever serves) when anything non-std-lib was imported — and the ``-I -S`` census names it."""
    bad = _evil_pyz(tool, tmp_path, monkeypatch)
    proc = subprocess.run(
        [sys.executable, str(bad), "--no-browser"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=tmp_path,
        env=_clean_env(),
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert "evil_client" in proc.stderr
    assert "Running at" not in proc.stdout
    assert _census(bad, tmp_path)["non_std"] == ["evil_client", "schedule_forensics"]


# ── the import path (LS-12 / DOC-LS-03 / LSB-3) ──────────────────────────────────────────────

#: A ``sitecustomize`` that, the moment the program binds its socket (AFTER the archive's
#: ``__main__`` has cleaned the path and imported LODESTAR), writes ``sys.path`` and exits.
_PATH_HOOK = r"""
import json, os, sys
def _hook(event, args):
    if event == "socket.bind":
        with open(os.environ["LS_PATH_OUT"], "w", encoding="utf-8") as f:
            json.dump(sys.path, f)
        os._exit(0)
sys.addaudithook(_hook)
"""


def _default_path(cwd: Path) -> list[str]:
    """The oracle: THIS interpreter's own std-lib directories — its default module path, as
    ``python -I -S`` computes it (no environment, no site, no user dirs), never the rule under
    test."""
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-c", "import json, sys; print(json.dumps(sys.path))"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
        check=True,
    )
    return [p for p in json.loads(proc.stdout) if p and p != str(cwd)]


def _foreign_under_prefix() -> list[str]:
    """Existing directories under this interpreter's install prefix that are NOT the std-lib's
    (the one the old rule kept: ``<prefix>/lib`` on a POSIX Python, e.g. ``/usr/lib``)."""
    base = Path(sys.base_prefix)
    cands = [base / sys.platlibdir, base / "include", base / "share", base / "Tools"]
    return [str(p) for p in cands if p.is_dir()]


def _path_inside(pyz: Path, extra: list[str], tmp_path: Path) -> list[str]:
    """``sys.path`` inside the running archive, started as the launchers start it (no ``-I``),
    with ``extra`` on PYTHONPATH."""
    hook = tmp_path / "hook"
    hook.mkdir(exist_ok=True)
    (hook / "sitecustomize.py").write_text(_PATH_HOOK, encoding="utf-8")
    out = tmp_path / "path.json"
    out.unlink(missing_ok=True)
    env = {
        **_clean_env(),
        "PYTHONPATH": os.pathsep.join([str(hook), *extra]),
        "LS_PATH_OUT": str(out),
    }
    proc = subprocess.run(
        [sys.executable, str(pyz), "--no-browser", "--port", "0"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert out.is_file(), f"the archive never bound its socket: {proc.returncode} {proc.stderr}"
    return list(json.loads(out.read_text(encoding="utf-8")))


def _path_problem(got: list[str], pyz: Path, oracle: list[str]) -> str | None:
    want = [str(pyz), *oracle]
    if got == want:
        return None
    extra = [p for p in got if p not in want]
    return f"sys.path inside the archive is {got}, not {want} (not the std-lib's: {extra})"


def test_ls12_only_the_archive_and_the_std_lib_are_on_the_path(tmp_path: Path) -> None:
    """A PYTHONPATH naming a directory UNDER the interpreter's prefix that is not the std-lib's
    (``/usr/lib`` on a distro Python — the old rule kept anything under the prefix that was not
    ``*-packages``), and one outside it: inside the running archive neither is on the path; the
    std-lib's own directories are, in the interpreter's own order."""
    foreign = _foreign_under_prefix()
    assert foreign, f"no non-std-lib directory under {sys.base_prefix} to put on PYTHONPATH"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    got = _path_inside(PYZ, [*foreign, str(elsewhere)], tmp_path)
    problem = _path_problem(got, PYZ, _default_path(tmp_path))
    assert problem is None, problem


#: The rule LS-12 first shipped: "under the prefix and no ``*-packages`` part" — typed here as
#: the mutation.
_OLD_ISOLATE = """def _isolate() -> None:
    roots = {os.path.normcase(os.path.abspath(p)) for p in (sys.base_prefix, sys.base_exec_prefix)}

    def standard(entry: str) -> bool:
        full = os.path.normcase(os.path.abspath(entry))
        inside = any(full == root or full.startswith(root + os.sep) for root in roots)
        parts = set(full.replace("\\\\", "/").split("/"))
        return inside and not parts & {"site-packages", "dist-packages"}

    archive, rest = sys.path[:1], sys.path[1:]
    sys.path[:] = archive + [p for p in rest if p and standard(p)]

"""


def _old_rule_main(tmp_path: Path) -> Path:
    source = MAIN_SOURCE.read_text(encoding="utf-8")
    anchor = r"def _isolate\(\) -> None:.*?(?=\ndef _foreign)"
    mutated, n = re.subn(anchor, lambda _: _OLD_ISOLATE, source, flags=re.S)
    assert n == 1, "the mutation's anchor (def _isolate … def _foreign) moved"
    path = tmp_path / "old_main.py"
    path.write_text(mutated, encoding="utf-8")
    return path


def test_mutation_the_old_prefix_rule_keeps_a_foreign_directory(
    tool: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the archive rebuilt with the old prefix rule — the same checker names the
    directory under the prefix that stayed on the path."""
    patched = {**tool.members(), "__main__.py": _old_rule_main(tmp_path)}
    monkeypatch.setattr(tool, "members", lambda: dict(sorted(patched.items())))
    old = tmp_path / "OLD.pyz"
    old.write_bytes(tool.build())
    foreign = _foreign_under_prefix()
    problem = _path_problem(_path_inside(old, foreign, tmp_path), old, _default_path(tmp_path))
    assert problem is not None and foreign[0] in problem.split("not the std-lib's")[1], problem


def _pyz_main() -> ModuleType:
    """The archive's ``__main__`` source (byte-identical to the member — the lockstep), as a
    module whose ``_isolate`` can run on a crafted ``sys.path``."""
    spec = importlib.util.spec_from_file_location("lodestar_pyz_main_under_test", MAIN_SOURCE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _isolated(
    isolate: Callable[[], None], monkeypatch: pytest.MonkeyPatch, prefix: str, path: list[str]
) -> list[str]:
    monkeypatch.setattr(sys, "base_prefix", prefix)
    monkeypatch.setattr(sys, "base_exec_prefix", prefix)
    monkeypatch.setattr(sys, "platlibdir", "lib")
    crafted = list(path)
    monkeypatch.setattr(sys, "path", crafted)
    isolate()
    return list(crafted)


def _posix_layout(prefix: str) -> tuple[list[str], list[str]]:
    """``(std-lib dirs, foreign dirs)`` for a POSIX Python installed at ``prefix`` — the std-lib
    spelled as CPython's getpath spells it."""
    major, minor = sys.version_info[:2]
    lib = os.path.join(prefix, "lib")
    std = [
        os.path.join(lib, f"python{major}{minor}.zip"),
        os.path.join(lib, f"python{major}.{minor}"),
        os.path.join(lib, f"python{major}.{minor}", "lib-dynload"),
    ]
    foreign = [
        lib,  # the std-lib's parent
        os.path.join(prefix, "share", "doc"),
        os.path.join(lib, f"python{major}.{minor + 1}"),  # ANOTHER Python's std-lib: a crash
        os.path.join(lib, f"python{major}.{minor}", "idlelib"),  # inside the std-lib, not it
        os.path.join(lib, f"python{major}.{minor}", "site-packages"),
        "/opt/other",
    ]
    return std, foreign


@pytest.mark.skipif(os.name == "nt", reason="a POSIX install layout")
@pytest.mark.parametrize("prefix", ["/usr", "/"], ids=["usr-prefix", "root-prefix"])
def test_ls12_isolate_keeps_exactly_the_std_lib_whatever_the_prefix(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In process, on a crafted path: an interpreter installed at ``/usr`` (a distro Python) keeps
    its std-lib and drops every other directory under ``/usr``; one installed at ``/`` (where
    the old ``root + os.sep`` became ``//``) still keeps its std-lib."""
    std, foreign = _posix_layout(prefix)
    archive = "/x/LODESTAR.pyz"
    path = [archive, foreign[0], foreign[1], std[0], std[1], *foreign[2:], std[2]]
    assert _isolated(_pyz_main()._isolate, monkeypatch, prefix, path) == [archive, *std]


@pytest.mark.skipif(os.name == "nt", reason="a POSIX install layout")
@pytest.mark.parametrize("prefix", ["/usr", "/"], ids=["usr-prefix", "root-prefix"])
def test_mutation_the_old_prefix_rule_fails_both_prefixes(
    prefix: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the old rule keeps the foreign ``/usr`` directories, and at ``/`` drops the
    std-lib itself — the same crafted path and assertion go red both ways."""
    scope: dict[str, object] = {"os": os, "sys": sys}
    exec(_OLD_ISOLATE, scope)  # the mutation: a literal typed in this file
    std, foreign = _posix_layout(prefix)
    archive = "/x/LODESTAR.pyz"
    path = [archive, foreign[0], foreign[1], std[0], std[1], *foreign[2:], std[2]]
    got = _isolated(scope["_isolate"], monkeypatch, prefix, path)  # type: ignore[arg-type]
    assert got != [archive, *std]
    if prefix == "/":
        assert got == [archive], got
    else:
        assert foreign[0] in got and foreign[2] in got, got


# ── the console (LSB-1) ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("encoding", ["ascii", "cp437"])
def test_help_prints_on_a_console_that_cannot_show_a_dash(encoding: str, tmp_path: Path) -> None:
    """``--help`` run as the launchers run it (no ``-I``, so the console's encoding applies) on
    an ASCII / cp437 console prints the usage and exits 0 — never a UnicodeEncodeError."""
    proc = subprocess.run(
        [sys.executable, str(PYZ), "--help"],
        capture_output=True,
        timeout=60,
        cwd=tmp_path,
        env={**_clean_env(), "PYTHONIOENCODING": encoding},
        stdin=subprocess.DEVNULL,
        check=False,
    )
    tail = proc.stderr.decode("utf-8", "replace")[-300:]
    assert proc.returncode == 0, (proc.returncode, tail)
    assert proc.stdout.decode(encoding).startswith("usage: LODESTAR"), proc.stdout[:80]


# ── end to end ────────────────────────────────────────────────────────────────────────────────


def test_end_to_end_the_shipped_file_serves_links_exports_and_quits(tmp_path: Path) -> None:
    """The committed file, started the way the launchers start it, does the operator's whole
    job and stops cleanly. The subprocess keeps its own clock, so a date window pins the
    slide's axis and nothing asserted depends on the day the test runs."""
    proc, port, out, err = _launch(
        [sys.executable, str(PYZ), "--no-browser", "--no-shortcut"], tmp_path
    )
    try:
        banner = out.read_text(encoding="utf-8")
        assert AUTHOR in banner and CONTACT in banner, banner

        page = request(port, "GET", "/onepager")
        assert page.status == 200
        mailtos = re.findall(r'href="(mailto:[^"]*)"', page.text)
        assert len(mailtos) >= 2 and set(mailtos) == {MAILTO}, mailtos

        assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
        window = {"start": "2027-01-01", "end": "2027-12-31", "action": "apply"}
        assert form(port, "/onepager/window", window).status == 303
        keys = _keys(request(port, "GET", "/onepager").text)
        added = form(
            port,
            "/onepager/links",
            {"action": "add", "pred": keys[DR], "succ": keys[BUILD], "kind": "FS"},
        )
        assert (added.status, added.headers.get("location")) == (303, "/onepager#opLinks")

        deck = request(port, "GET", "/export/pptx/onepager")
        assert deck.status == 200, deck.text[:200]
        links = [n for n in deck_shapes(deck.body) if n.startswith("Logic link:")]
        assert links == [f"Logic link: {DR} → {BUILD} (FS)"]
        parts = deck_members(deck.body)
        core = ET.fromstring(parts["docProps/core.xml"])
        assert core.findtext("{http://purl.org/dc/elements/1.1/}creator") == "LODESTAR"
        assert [n for n, b in parts.items() if re.search(rb"(?i)polaris", b)] == []
        # the credit is the PAGE's (header and footer), never the slide's or the author field's
        assert [n for n, b in parts.items() if AUTHOR.encode() in b or CONTACT.encode() in b] == []

        bye = _quit(port)
        assert bye is None or bye.status == 200
        code = proc.wait(timeout=30)
    finally:
        _stop(proc)
    assert code == 0
    assert err.read_bytes() == b"", err.read_text(errors="replace")
    assert "LODESTAR stopped." in out.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name == "nt", reason="lodestar.sh is the POSIX launcher")
def test_linux_launcher_starts_the_file_beside_it_and_quits_cleanly(tmp_path: Path) -> None:
    """``sh lodestar.sh`` — the README's Linux path — from ANOTHER directory finds the archive
    beside it, serves the page with the credit, and Quit ends it with status 0, stderr empty."""
    proc, port, out, err = _launch(
        ["sh", str(SHIPPED / "lodestar.sh"), "--no-browser", "--no-shortcut"], tmp_path
    )
    try:
        page = request(port, "GET", "/onepager")
        assert page.status == 200 and MAILTO in page.text
        bye = _quit(port)
        assert bye is None or bye.status == 200
        code = proc.wait(timeout=30)
    finally:
        _stop(proc)
    assert code == 0
    assert err.read_bytes() == b""
    assert AUTHOR in out.read_text(encoding="utf-8")


#: The shipped modules, run from the archive, with ONE change: the Quit reply takes 3 s to write
#: — the race window made wide enough to land in every run (the process stops within ~0.5 s of
#: Quit: ``serve_forever``'s poll). Everything else is the archive's own code.
_SLOW_QUIT = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
import schedule_forensics.lodestar.server as server
from schedule_forensics.lodestar.__main__ import main
_send = server._Handler._send
def slow_send(self, reply, *, head_only):
    if self.path == "/quit":
        time.sleep(3.0)
    _send(self, reply, head_only=head_only)
server._Handler._send = slow_send
raise SystemExit(main(["--no-browser", "--no-shortcut"]))
"""


def test_quit_reply_reaches_the_browser_before_the_process_exits(tmp_path: Path) -> None:
    """Pressing Quit shows the "has stopped" page (with the credit) — the process must not exit
    before that reply is on the wire. A 3 s write makes the race deterministic. What delivers it
    is the order in the server's ``_dispatch``: the Quit reply is written and flushed FIRST, and
    only then does the server start its shutdown (the handler threads stay daemons,
    ``daemon_threads = True``) — shutdown begun before the write lost the page (ADR-0539
    review LS-05), and the same run with the write first delivers it every time, so this is not
    an impossible test."""
    proc, port, _out, _err = _launch([sys.executable, "-c", _SLOW_QUIT, str(PYZ)], tmp_path)
    try:
        bye = form(port, "/quit", {}, timeout=20)
        code = proc.wait(timeout=30)
    finally:
        _stop(proc)
    assert bye.status == 200 and "LODESTAR has stopped" in bye.text
    assert AUTHOR in bye.text and code == 0


def test_the_readme_states_the_version_the_program_reports() -> None:
    """Rendering review of ADR-0540 (F4): the README said 1.0.1 while ``--version`` and every
    page footer said 1.0.0. One number, held in lockstep."""
    from schedule_forensics.web.lodestar_shell import VERSION

    readme = (ROOT / "lodestar" / "README.md").read_text(encoding="utf-8")
    assert f"Version {VERSION}." in readme, VERSION
