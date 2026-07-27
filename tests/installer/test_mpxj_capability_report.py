"""The installer must report the DEPLOYED tool's .mpp capability, not the copy it just made.

Operator incident 2026-07-27 (ADR-0299): upgrading an existing install by running the
downloaded ``install-tier2.ps1`` printed

    [!!] tools\\mpxj not found next to this installer — native .mpp import stays OFF

on a machine where native ``.mpp`` import was in fact **ON** — the converter was already
deployed under ``%LOCALAPPDATA%\\ScheduleForensics\\tools\\mpxj`` and the installer never
touches it. The installer had asserted the opposite of the truth about the tool it had just
installed, which on a testimony-context tool is a correctness defect, not a cosmetic one.

**What is executed here.** The ``# --- 3b.`` section is lifted VERBATIM out of the generated
``installer/install-tier2.{sh,command}`` and run under the same ``set -euo pipefail`` the
installer uses, with only ``ok``/``warn``/``INSTALL_ROOT`` stubbed. Nothing is re-typed, so
what these tests assert is what actually ships (ADR-0289: execute the behaviour, do not pin
the source).

**The invariant** is not "some string appears". It is: *whatever the installer claims about
native .mpp, the filesystem must agree* — checked after every scenario by looking for the
converter where the runtime's walk-up discovery will look for it.

``pwsh`` does not exist in the build container (see ``test_installers.py``), and the
windows-latest smoke workflow only ever runs the installer FROM the checkout — i.e. scenario
A alone. The Windows family is therefore covered here by structural parity with the bash
logic that IS executed, which is stated plainly rather than dressed up as execution.
"""

from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH_FAMILIES = ("sh", "command")

#: Stubs for the three names the block borrows from the installer around it.
_PRELUDE = textwrap.dedent(
    """\
    set -euo pipefail
    INSTALL_ROOT="$SF_TEST_INSTALL_ROOT"
    mkdir -p "$INSTALL_ROOT"
    ok()   { printf 'OK:%s\\n' "$1"; }
    warn() { printf 'WARN:%s\\n' "$1"; }
    """
)

#: How the block may describe the outcome, and what each phrasing claims.
_CLAIMS = (
    ("native .mpp import enabled", True),
    ("native .mpp import stays ON", True),
    ("native .mpp import is OFF", False),
)


def _block(family: str) -> str:
    """The shipped 3b section, verbatim, from the generated tier-2 installer."""
    text = (ROOT / "installer" / f"install-tier2.{family}").read_text(encoding="utf-8")
    m = re.search(r"(# --- 3b\..*?)\n# --- 4\.", text, re.S)
    assert m, f"the 3b MPXJ section was not found in install-tier2.{family}"
    return m.group(1)


def _converter(at: Path) -> Path:
    """A stand-in converter tree — the probe only tests for classes/MpxjToMspdi.class."""
    (at / "classes").mkdir(parents=True, exist_ok=True)
    (at / "classes" / "MpxjToMspdi.class").write_bytes(b"\xca\xfe\xba\xbe")
    (at / "lib").mkdir(exist_ok=True)
    (at / "lib" / "mpxj-16.2.0.jar").write_bytes(b"jar")
    return at


def _claimed_on(out: str) -> bool:
    """Which claim the installer made. Exactly one must be present, or the block is ambiguous."""
    hits = [on for phrase, on in _CLAIMS if phrase in out]
    assert len(hits) == 1, f"expected exactly one capability claim, got {hits!r} in:\n{out}"
    return hits[0]


def _deployed(install_root: Path) -> bool:
    """What the RUNTIME will conclude: is there a converter beside the venv? (ADR-0193)"""
    return (install_root / "tools" / "mpxj" / "classes" / "MpxjToMspdi.class").is_file()


def _run(
    tmp_path: Path,
    family: str,
    *,
    sibling: bool = False,
    installed: bool = False,
    cwd_tools: bool = False,
    mpxj_home: str | None = None,
) -> tuple[str, Path]:
    """Lay out one machine state and execute the real block against it.

    ``sibling`` mirrors running from a checkout (``<here>/../tools/mpxj`` exists);
    ``installed`` mirrors an upgrade over a previous install; ``cwd_tools`` mirrors being
    ``cd``-ed into an extracted ZIP while the installer sits in Downloads.
    """
    here = tmp_path / "downloads"
    here.mkdir(parents=True, exist_ok=True)
    script = here / f"runner.{family}"
    script.write_text(_PRELUDE + _block(family) + "\n", encoding="utf-8")

    install_root = tmp_path / "InstallRoot"
    install_root.mkdir(parents=True, exist_ok=True)
    if sibling:
        _converter(tmp_path / "tools" / "mpxj")
    if installed:
        _converter(install_root / "tools" / "mpxj")
    workdir = tmp_path / "work"
    workdir.mkdir(exist_ok=True)
    if cwd_tools:
        _converter(workdir / "tools" / "mpxj")

    env = {"PATH": "/usr/bin:/bin", "SF_TEST_INSTALL_ROOT": str(install_root)}
    if mpxj_home is not None:
        env["SF_MPXJ_HOME"] = mpxj_home
    proc = subprocess.run(  # fixed argv, no shell
        ["bash", str(script)], capture_output=True, text=True, env=env, cwd=str(workdir)
    )
    assert proc.returncode == 0, f"the block aborted:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout + proc.stderr, install_root


@pytest.mark.parametrize("family", BASH_FAMILIES)
@pytest.mark.parametrize(
    ("label", "state", "expect_on"),
    [
        ("from a checkout, fresh machine", {"sibling": True}, True),
        ("from Downloads, fresh machine", {}, False),
        ("from Downloads, upgrading an install that has it", {"installed": True}, True),
        ("cd-ed into an extracted ZIP", {"cwd_tools": True}, True),
    ],
)
def test_the_claim_matches_what_the_deployed_tool_can_do(
    tmp_path: Path, family: str, label: str, state: dict[str, bool], expect_on: bool
) -> None:
    """The regression itself: the installer's sentence and the filesystem must agree.

    The third row is the operator's exact case — it printed "stays OFF" while the tool could
    in fact still open .mpp files.
    """
    out, install_root = _run(tmp_path, family, **state)
    assert _deployed(install_root) is expect_on, f"{label}: unexpected deployed state\n{out}"
    assert _claimed_on(out) is _deployed(install_root), (
        f"{label}: the installer claimed native .mpp "
        f"{'ON' if _claimed_on(out) else 'OFF'} but the deployed tree says "
        f"{'ON' if _deployed(install_root) else 'OFF'}\n{out}"
    )


@pytest.mark.parametrize("family", BASH_FAMILIES)
def test_sf_mpxj_home_is_honoured_not_merely_named(tmp_path: Path, family: str) -> None:
    """The not-found message names SF_MPXJ_HOME, so the installer must actually consult it.

    Before ADR-0299 the variable was mentioned in the advice and ignored by the code.
    """
    src = _converter(tmp_path / "elsewhere" / "mpxj")
    out, install_root = _run(tmp_path, family, mpxj_home=str(src))
    assert _deployed(install_root), f"SF_MPXJ_HOME was ignored\n{out}"
    assert _claimed_on(out) is True


@pytest.mark.parametrize("family", BASH_FAMILIES)
def test_a_rerun_never_destroys_the_installed_converter(tmp_path: Path, family: str) -> None:
    """Self-copy guard. Widening the search to SF_MPXJ_HOME/CWD made it possible to select
    the ALREADY-INSTALLED copy as the source; the copy step ``rm -rf``s the destination
    first, so without the guard a re-run deletes the only converter and leaves native .mpp
    broken. Removing the guard fails this test with the converter gone."""
    dest = _converter(tmp_path / "InstallRoot" / "tools" / "mpxj")
    out, install_root = _run(tmp_path, family, installed=True, mpxj_home=str(dest))
    assert _deployed(install_root), f"the installed converter was destroyed by a re-run\n{out}"
    assert _claimed_on(out) is True


def test_the_zip_remedy_the_installer_advises_is_actually_available() -> None:
    """The not-found branch tells the operator to download the repository ZIP. That advice is
    only true while the converter is committed — GitHub's ZIP carries tracked files only."""
    tracked = subprocess.run(
        ["git", "ls-files", "tools/mpxj"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=True,
    ).stdout.split()
    assert "tools/mpxj/classes/MpxjToMspdi.class" in tracked, (
        "the installer advises downloading the repo ZIP to enable native .mpp, but the "
        "converter class is no longer committed — the advice would not work"
    )
    assert sum(1 for t in tracked if t.endswith(".jar")) >= 20, (
        "the MPXJ jars are no longer committed — the ZIP remedy would install a converter "
        "that cannot run"
    )


def test_powershell_mirrors_the_bash_logic_that_is_executed() -> None:
    """pwsh is absent from the build container and the windows smoke run only exercises the
    run-from-a-checkout case, so the Windows family is held to structural parity with the
    bash block these tests actually execute: same four sources, same three outcomes, same
    self-copy guard."""
    ps1 = (ROOT / "tools" / "installer" / "template.ps1").read_text(encoding="utf-8")
    section = ps1.split("# --- 3b.", 1)[1].split("\n# a stale", 1)[0]

    for source in ("$env:SF_MPXJ_HOME", "Split-Path -Parent $here", "$PWD.Path"):
        assert source in section, f"Windows installer does not search {source}"
    assert "$PSScriptRoot" in section, "the installer's own folder is not part of the search"
    # Join-Path THROWS on an empty base under ErrorActionPreference="Stop" (Split-Path -Parent of
    # a drive root returns ""), which would abort the install before it reached the report.
    assert "if ($base) { $mpxjCandidates += (Join-Path $base" in section, (
        "the empty-base guard around Join-Path is missing"
    )

    for phrase, _ in _CLAIMS:
        assert phrase in section, f"Windows installer cannot report {phrase!r}"
    assert "-ieq $destReal" in section, "the self-copy guard is missing from the Windows family"

    for tier in ("tier1", "tier2", "tier3"):
        shipped = (ROOT / "installer" / f"install-{tier}.ps1").read_text(encoding="utf-8-sig")
        assert "native .mpp import stays ON" in shipped, tier
        assert "-ieq $destReal" in shipped, tier
