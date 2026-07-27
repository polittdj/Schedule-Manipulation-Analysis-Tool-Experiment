# MPXJ capability reporting — verified diagnosis and ready-to-apply fix

- **Raised by:** operator, 2026-07-27, from a real upgrade run on their machine
- **Status:** diagnosed, evidence executable, **fix written and validated but NOT yet applied**
- **Owns:** `tools/installer/template.{ps1,sh,command}`, `installer/install-tier{1,2,3}.*`,
  `tests/installer/`, `installer/README-DISTRIBUTABLE.md`
- **Becomes** ADR-0299 when it lands. Companion to ADR-0193 (the converter ships beside the venv)
  and ADR-0293 (the runtime `.mpp` capability probe).

## The incident

Upgrading an existing install by running the downloaded `install-tier2.ps1` printed:

```
[!!] tools\mpxj not found next to this installer — native .mpp import stays OFF
```

…on a machine where native `.mpp` import was **ON**. The operator confirmed it directly:

```powershell
Test-Path "$env:LOCALAPPDATA\ScheduleForensics\tools\mpxj\classes\MpxjToMspdi.class"
True
```

The converter was already deployed from an earlier install and the installer never touches it — the
`else` branch only warns, it does not delete. So nothing was broken; **the installer simply asserted
the opposite of the truth about the tool it had just installed.** On a tool built for testimony
that is a correctness defect, not a cosmetic one: an operator who believes `.mpp` ingest is
unavailable will either work around it needlessly or distrust a later successful import.

## Verified diagnosis

The `# --- 3b.` section was lifted verbatim out of the generated `installer/install-tier2.sh` and
executed against fixture layouts (bash; the three families share this logic). Measured, not
reasoned:

| scenario | installer says | native `.mpp` actually available after | agree? |
| --- | --- | --- | --- |
| A. run from a checkout, fresh machine | "enabled" | yes | ✅ |
| B. run from Downloads, fresh machine | "stays OFF" | no | ✅ |
| **C. run from Downloads, upgrade over an existing install** | **"stays OFF"** | **yes** | ❌ **the bug** |
| D. run from Downloads, `SF_MPXJ_HOME` set to a real converter | "stays OFF" | no | ✅ but see below |

Four distinct defects fall out:

1. **The report describes the copy step, not the deployed tool.** Scenario C is the operator's case.
   The only thing the installer knows is whether *it* copied something; what matters is whether
   `$InstallRoot\tools\mpxj\classes\MpxjToMspdi.class` exists when it finishes, because that is
   exactly what the runtime's walk-up discovery looks for (`importers/mpp_mpxj.py::_mpxj_home`).
2. **One search path only.** `<parent of the installer's own folder>/tools/mpxj` — which resolves to
   `C:\Users\<user>` when the file is run from `Downloads`. Neither `$PSScriptRoot\tools\mpxj`
   (installer sitting at a repo root) nor the current directory is considered.
3. **`SF_MPXJ_HOME` is named in the advice and ignored by the code.** The not-found branch tells the
   operator to set it; the installer never reads it (scenario D). Setting it persistently *does*
   work at runtime, so the advice is not false — but the installer declines to act on the one
   variable it points at.
4. **The remediation is not actionable for this operator, who has no local clone.** "run the
   installer from the repository checkout" presumes git. The workable instruction is the GitHub web
   UI's **Code → Download ZIP**, which does carry the converter — verified: all 28 files under
   `tools/mpxj`, including `classes/MpxjToMspdi.class` and 24 jars, are tracked, with no LFS
   (`git ls-files tools/mpxj`). Only `sqlite-jdbc*.jar` is gitignored, and it is not needed.

### A destructive edge the fix must not open

Widening the search to `SF_MPXJ_HOME` / CWD makes it possible to select the **already-installed**
copy as the source. The copy step `rm -rf`s the destination first, so without a guard a re-run
**deletes the only converter**. Confirmed by mutation — removing the guard from the candidate block
and re-running scenario E:

```
GUARDED : OK:MPXJ converter already installed — native .mpp import stays ON (existing copy kept)
          converter still present afterwards: True
MUTANT  : cp: cannot stat '.../InstallRoot/tools/mpxj': No such file or directory
          converter still present afterwards: False
```

This path is **not** reachable in the shipped code (one candidate, never the destination). The guard
is a necessary companion to the widening, not a pre-existing bug.

## Decision

**The installer reports the capability of the deployed tool, not the outcome of its copy step.**
Three outcomes, and the printed sentence must always agree with the filesystem:

| condition | message |
| --- | --- |
| a source converter was found and copied | `MPXJ converter deployed (native .mpp import enabled)` |
| no source, but one is already installed | `MPXJ converter already installed — native .mpp import stays ON (existing copy kept)` |
| neither | `no MPXJ converter found — native .mpp import is OFF` + the ZIP remedy |

Search order: `$SF_MPXJ_HOME` → `<installer dir>/../tools/mpxj` → `<installer dir>/tools/mpxj` →
`<cwd>/tools/mpxj`; skip any candidate that resolves to the destination itself.

### Explicitly out of scope: embedding MPXJ in the installers

Rejected on repo-health grounds, recorded so it is not re-litigated. The converter is 17 MB; base64
in a one-file installer is ~23 MB, times nine installers, **regenerated on every version bump**.
Git would accumulate ~200 MB per release. The installers are self-contained *for the Python tool*
(that is what the embedded wheel is for); the Java converter is an optional add-on, and the ZIP
route already delivers it in one download. If a single-file `.mpp`-enabled deploy is ever wanted,
the right shape is a **separate `install-mpxj.*` payload generated once per MPXJ upgrade**, not per
release — but the ZIP instruction makes even that unnecessary today.

## Ready-to-apply

Both blocks below were written against the real templates; the bash one was **executed** across all
five scenarios plus the mutation above. They replace the `# --- 3b.` section in
`tools/installer/template.sh`, `template.command`, and `template.ps1` respectively.

### bash (`template.sh` and `template.command`, identical)

```sh
# --- 3b. vendored MPXJ converter (native .mpp support) --------------------------------
# The wheel is pure Python; the 17 MB Java converter (tools/mpxj) is NOT embedded in this
# file — it rides in the repository and is copied beside the venv, where the runtime's
# walk-up discovery finds it (ADR-0193). Several layouts are searched, because this file
# is run from a download folder at least as often as from a checkout.
# What is REPORTED is the capability of the DEPLOYED TOOL, not of this copy step: an
# upgrade that finds no source but already has a converter installed leaves native .mpp
# ON, and saying "stays OFF" there was simply false (ADR-0299).
MPXJ_DEST="$INSTALL_ROOT/tools/mpxj"
sf_realpath() { (cd "$1" 2>/dev/null && pwd) || printf '%s\n' "$1"; }
MPXJ_DEST_REAL="$(sf_realpath "$MPXJ_DEST")"
MPXJ_SRC=""
SF_HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd || printf '%s\n' ".")"
for cand in "${SF_MPXJ_HOME:-}" "$SF_HERE/../tools/mpxj" "$SF_HERE/tools/mpxj" "$PWD/tools/mpxj"; do
  if [ -z "$cand" ]; then continue; fi
  if [ ! -f "$cand/classes/MpxjToMspdi.class" ]; then continue; fi
  # never copy the installed copy over itself — that would rm -rf the only converter
  if [ "$(sf_realpath "$cand")" = "$MPXJ_DEST_REAL" ]; then continue; fi
  MPXJ_SRC="$cand"
  break
done
if [ -n "$MPXJ_SRC" ]; then
  mkdir -p "$INSTALL_ROOT/tools"
  rm -rf "$MPXJ_DEST"
  cp -R "$MPXJ_SRC" "$MPXJ_DEST"
  ok "MPXJ converter deployed (native .mpp import enabled)"
elif [ -f "$MPXJ_DEST/classes/MpxjToMspdi.class" ]; then
  ok "MPXJ converter already installed — native .mpp import stays ON (existing copy kept)"
else
  warn "no MPXJ converter found — native .mpp import is OFF"
  warn "  to turn it on: download the repository ZIP (green 'Code' button -> Download ZIP),"
  warn "  extract it, then re-run this installer from inside the extracted folder"
  warn "  until then: export MSPDI XML from MS Project and analyse that instead"
fi
```

`set -euo pipefail` is already in force, hence `${SF_MPXJ_HOME:-}` and `if …; then continue; fi`
rather than `[ … ] && continue` (a false `&&` list as the last statement in a loop body aborts).

### PowerShell (`template.ps1`) — mirrors the above, not executable in this container

```powershell
# --- 3b. vendored MPXJ converter (native .mpp support) --------------------------------
# (same rationale as the bash families — see ADR-0299)
function Resolve-SfPath([string]$p) {
    try { return (Resolve-Path -LiteralPath $p -ErrorAction Stop).ProviderPath } catch { return $p }
}
$destMpxj = Join-Path $InstallRoot "tools\mpxj"
$destReal = Resolve-SfPath $destMpxj
$srcMpxj = $null
foreach ($cand in @($env:SF_MPXJ_HOME,
                    (Join-Path (Split-Path -Parent $PSScriptRoot) "tools\mpxj"),
                    (Join-Path $PSScriptRoot "tools\mpxj"),
                    (Join-Path $PWD.Path "tools\mpxj"))) {
    if (-not $cand) { continue }
    if (-not (Test-Path (Join-Path $cand "classes\MpxjToMspdi.class"))) { continue }
    # never copy the installed copy over itself — that would delete the only converter
    if ((Resolve-SfPath $cand) -ieq $destReal) { continue }
    $srcMpxj = $cand
    break
}
if ($srcMpxj) {
    New-Item -ItemType Directory -Force -Path $destMpxj | Out-Null
    Copy-Item -Recurse -Force -Path (Join-Path $srcMpxj "*") -Destination $destMpxj
    Ok "MPXJ converter deployed (native .mpp import enabled)"
} elseif (Test-Path (Join-Path $destMpxj "classes\MpxjToMspdi.class")) {
    Ok "MPXJ converter already installed — native .mpp import stays ON (existing copy kept)"
} else {
    Warn2 "no MPXJ converter found — native .mpp import is OFF"
    Warn2 "  to turn it on: download the repository ZIP (green 'Code' button -> Download ZIP),"
    Warn2 "  extract it, then re-run this installer from inside the extracted folder"
    Warn2 "  until then: export MSPDI XML from MS Project and analyse that instead"
}
```

## The test to add

`tests/installer/test_mpxj_capability_report.py` — drafted in full and validated against the
candidate block. It extracts the `# --- 3b.` section **verbatim from the generated installer** and
executes it under `set -euo pipefail` with only `ok`/`warn`/`INSTALL_ROOT` stubbed (ADR-0289: run
the behaviour, do not pin the source). Its assertions:

- **the invariant** — whatever the installer claims about native `.mpp`, the filesystem must agree,
  checked where `_mpxj_home()` will look, across four layouts × the `sh` and `command` families;
- `SF_MPXJ_HOME` is *honoured*, not merely named;
- a re-run never destroys an installed converter (the mutation above, as a permanent test);
- the ZIP remedy the installer advises is real — `git ls-files tools/mpxj` still carries the
  converter class and ≥20 jars, so the advice cannot rot silently;
- the PowerShell family mirrors the executed bash logic (same four sources, same three outcomes,
  same self-copy guard) — stated as parity, not dressed up as execution.

**Why the harness is load-bearing:** `installer-smoke.yml` runs the installer *from the checkout*
(`bash installer/install-tier1.sh`), so real-OS CI only ever exercises scenario A. Scenarios B–E
have no other coverage.

### Existing pins that will fail and must be updated

In `tests/installer/test_installers.py::test_installers_deploy_mpxj_and_a_single_self_stopping_icon`:

- `assert "native .mpp import stays OFF" in tpl_ps1` — the string is retired;
- `assert 'cp -R "$REPO_MPXJ"' in tpl` (sh/command) — the variable becomes `MPXJ_SRC`/`MPXJ_DEST`;
- `assert 'Join-Path (Split-Path -Parent $PSScriptRoot) "tools\\mpxj"' in tpl_ps1` — still true, it
  remains one of the four candidates.

## Documentation drift found while diagnosing (fix in the same PR)

- **`installer/README-DISTRIBUTABLE.md` never mentions `tools/mpxj`** while promising "give the
  recipient **one** file" — so the documented distribution model structurally cannot deliver native
  `.mpp`. It needs a sentence pointing at the ZIP route.
- **`README-DISTRIBUTABLE.md` says the installer finishes by creating "Start Schedule Forensics"
  and "Stop Schedule Forensics" icons.** True on Linux/macOS; **wrong on Windows** since ADR-0193,
  which collapsed those to the single `Schedule Forensics.lnk` and actively deletes the old two.
- **`tools/installer/template.ps1`'s own header (§6) makes the same stale two-icon claim**, directly
  contradicting its own code ~260 lines below (`foreach ($old in @("Start Schedule Forensics.lnk",
  "Stop Schedule Forensics.lnk")) { … }` then one `Schedule Forensics.lnk`).
- **`docs/STATE/HANDOFF.md`'s DEPLOY NOTE** told the operator to download the single `.ps1` into
  `Downloads` — the instruction that *guarantees* the converter is not found. Superseded by the ZIP
  route (already corrected in the handoff that ships with this document).

## Appendix — the drafted test, verbatim

Written and validated against the candidate block during the diagnosis session. Drop in at
`tests/installer/test_mpxj_capability_report.py` **after** the template change lands (it fails
against the current installers, which is the point).

```python
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
    proc = subprocess.run(  # noqa: S603  # nosec B603  # fixed argv, no shell
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
    tracked = subprocess.run(  # noqa: S603  # nosec B603
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

    for source in ("$env:SF_MPXJ_HOME", "Split-Path -Parent $PSScriptRoot", "$PWD.Path"):
        assert source in section, f"Windows installer does not search {source}"
    assert "Join-Path $PSScriptRoot" in section, "installer-at-repo-root layout not searched"

    for phrase, _ in _CLAIMS:
        assert phrase in section, f"Windows installer cannot report {phrase!r}"
    assert "-ieq $destReal" in section, "the self-copy guard is missing from the Windows family"

    for tier in ("tier1", "tier2", "tier3"):
        shipped = (ROOT / "installer" / f"install-{tier}.ps1").read_text(encoding="utf-8-sig")
        assert "native .mpp import stays ON" in shipped, tier
        assert "-ieq $destReal" in shipped, tier
```
