"""LODESTAR's Desktop shortcut — written the FIRST time the program runs (ADR-0541, operator ask
2026-09-30: "when run for the first time, create a shortcut on the desktop which launches the
program moving forward, if possible").

What is written, per desktop, each carrying LODESTAR's own icon (:mod:`schedule_forensics.
desktop_icon`, the ✦ lodestar) so it is told apart from Polaris²'s:

* **Windows** — ``Desktop\\LODESTAR.lnk``, made through PowerShell's ``WScript.Shell`` COM object
  (the standard library has no shortcut writer): its target is the Python launcher ``py.exe``
  with ``-3 "<LODESTAR.pyz>"`` where ``py`` exists, else the very interpreter running now with
  the archive as its argument; its working folder is the archive's; its icon the ``.ico``.
* **macOS** — ``Desktop/LODESTAR.app``, a minimal application bundle: an ``Info.plist``, a
  ``MacOS/LODESTAR`` shell script that ``exec``\\s the interpreter on the archive, and the
  ``.icns`` — the same shape Polaris²'s installer writes (ADR-0540).
* **Linux** — ``Desktop/LODESTAR.desktop`` (``Terminal=true``, so the console window that IS
  LODESTAR's lifetime opens), executable, marked trusted through ``gio`` where a desktop asks
  for that.

Three rules keep it honest: it is written **once** — a marker in LODESTAR's own per-user data
folder (``%LOCALAPPDATA%\\LODESTAR``, ``~/Library/Application Support/LODESTAR``,
``$XDG_DATA_HOME/lodestar``) records the archive it was made for, so a shortcut the operator
deleted is never put back unbidden (``--shortcut`` makes it again, ``--no-shortcut`` never
makes one); it is **best-effort** — no Desktop folder, no archive (a source-tree run), a
refusal from the desktop — each is a sentence on the console, never a stopped program, never a
line on stderr; and it carries **nothing of the operator's data** — a path, an icon, a name.
Std-lib only. Windows and macOS are written by reading (no such host builds this): UNVERIFIED
there, stated in ADR-0541; Linux is run for real by ``tests/lodestar/test_lodestar_shortcut.py``.
"""

from __future__ import annotations

import os
import plistlib
import shlex
import shutil
import subprocess  # nosec B404 — the desktop's own tools (powershell, gio), fixed argv, no shell
import sys
from dataclasses import dataclass
from pathlib import Path

from schedule_forensics import desktop_icon
from schedule_forensics.web.lodestar_shell import AUTHOR, NAME, TAGLINE

#: The marker's name in the data folder: the archive path the shortcut was made for.
MARKER = "shortcut-made.txt"
#: How long a desktop tool (PowerShell, gio) may take before the attempt is given up.
TOOL_TIMEOUT_S = 30.0
#: Windows-only ``CREATE_NO_WINDOW`` (0 on POSIX): a child console must never flash a window.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class Outcome:
    """What the attempt did: whether a shortcut was written NOW, where the shortcut is (or would
    be), and the sentence the console prints (``""`` for nothing to say)."""

    made: bool
    path: Path | None
    note: str


def data_dir() -> Path:
    """LODESTAR's per-user data folder — the icon files and the once-only marker live here,
    never beside the archive (a shared or read-only folder)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), "AppData", "Local")
        return Path(base) / NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAME
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(Path.home(), ".local", "share")
    return Path(base) / NAME.lower()


def desktop_dir() -> Path | None:
    """The operator's Desktop folder, or ``None`` when there is none to write on."""
    found: Path | None = None
    if sys.platform == "win32":
        found = _windows_desktop()
    elif sys.platform != "darwin":
        found = _xdg_desktop()
    if found is None:
        found = Path.home() / "Desktop"
    return found if found.is_dir() else None


def _windows_desktop() -> Path | None:
    """Where Windows keeps this user's Desktop (a redirected one included), from the registry."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            value, _kind = winreg.QueryValueEx(handle, "Desktop")
        return Path(os.path.expandvars(str(value)))
    except (OSError, ValueError):
        return None


def _xdg_desktop() -> Path | None:
    """The XDG user directory for the Desktop, read from ``user-dirs.dirs`` (no tool run)."""
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.join(Path.home(), ".config")
    try:
        text = (Path(config) / "user-dirs.dirs").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("XDG_DESKTOP_DIR="):
            raw = line.split("=", 1)[1].strip().strip('"')
            return Path(raw.replace("$HOME", str(Path.home())))
    return None


def archive_path() -> Path | None:
    """The ``LODESTAR.pyz`` this program was started from, or ``None`` (a source-tree run, which
    no shortcut could start again)."""
    candidate = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
    if candidate is None or candidate.suffix.lower() != ".pyz" or not candidate.is_file():
        return None
    return candidate.resolve()


def _interpreter() -> tuple[str, list[str]]:
    """``(program, leading arguments)`` the shortcut starts: on Windows the Python launcher
    (``py -3``) when it exists — it survives the interpreter that made the shortcut being
    upgraded or removed — else the interpreter running now."""
    if sys.platform == "win32":
        py = shutil.which("py")
        if py:
            return py, ["-3"]
    return sys.executable, []


# ── the three writers (each returns the shortcut's path) ─────────────────────────────────────


def _ps_quote(text: str) -> str:
    """A PowerShell single-quoted string literal (a quote inside doubles)."""
    return "'" + text.replace("'", "''") + "'"


def powershell_script(lnk: Path, archive: Path, program: str, args: list[str], ico: Path) -> str:
    """The PowerShell that writes the ``.lnk`` — the words handed to ``powershell -Command``."""
    arguments = " ".join([*args, f'"{archive}"'])
    return (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + _ps_quote(str(lnk)) + "); "
        "$s.TargetPath = " + _ps_quote(program) + "; "
        "$s.Arguments = " + _ps_quote(arguments) + "; "
        "$s.WorkingDirectory = " + _ps_quote(str(archive.parent)) + "; "
        "$s.IconLocation = " + _ps_quote(f"{ico},0") + "; "
        "$s.Description = " + _ps_quote(f"{NAME} — {TAGLINE}") + "; "
        "$s.Save()"
    )


def write_windows(desktop: Path, archive: Path, program: str, args: list[str], ico: Path) -> Path:
    lnk = desktop / f"{NAME}.lnk"
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None:
        raise OSError("PowerShell was not found")
    script = powershell_script(lnk, archive, program, args, ico)
    done = subprocess.run(  # nosec B603 — a fixed program, its own argv, no shell
        [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=TOOL_TIMEOUT_S,
        check=False,
        stdin=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )
    if done.returncode != 0 or not lnk.is_file():
        raise OSError(f"PowerShell could not write the shortcut (exit {done.returncode})")
    return lnk


def bundle_files(archive: Path, program: str, args: list[str]) -> dict[str, bytes]:
    """The members of the macOS application bundle, relative to ``LODESTAR.app`` — the
    ``Info.plist``, the launcher script and ``PkgInfo`` (the icon is written beside them)."""
    plist = {
        "CFBundleName": NAME,
        "CFBundleDisplayName": NAME,
        "CFBundleIdentifier": "studio.onepager.lodestar",
        "CFBundleVersion": "1",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": NAME,
        "CFBundleIconFile": f"{NAME}.icns",
        "NSHighResolutionCapable": True,
    }
    launcher = (
        "#!/bin/sh\n"
        f"# {NAME} — {TAGLINE}. Created by {AUTHOR}. Written by LODESTAR itself on its first run.\n"
        f"cd {shlex.quote(str(archive.parent))} || exit 1\n"
        f"exec {shlex.quote(program)} {' '.join(shlex.quote(a) for a in args)} "
        f'{shlex.quote(str(archive))} "$@"\n'
    ).replace("  ", " ")
    return {
        "Contents/Info.plist": plistlib.dumps(plist),
        f"Contents/MacOS/{NAME}": launcher.encode("utf-8"),
        "Contents/PkgInfo": b"APPL????",
    }


def write_macos(desktop: Path, archive: Path, program: str, args: list[str], icns: Path) -> Path:
    app = desktop / f"{NAME}.app"
    for rel, data in bundle_files(archive, program, args).items():
        target = app / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (app / "Contents" / "MacOS" / NAME).chmod(0o755)
    resources = app / "Contents" / "Resources"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icns, resources / f"{NAME}.icns")
    return app


def desktop_entry_quote(text: str) -> str:
    """One ``Exec=`` argument per the Desktop Entry specification: double-quoted, with the
    characters the specification reserves escaped by a backslash."""
    out = "".join("\\" + ch if ch in '"`$\\' else ch for ch in text)
    return f'"{out}"'


def desktop_entry(archive: Path, program: str, args: list[str], png: Path) -> str:
    exec_line = " ".join(desktop_entry_quote(a) for a in (program, *args, str(archive)))
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={NAME}\n"
        f"Comment={TAGLINE} — created by {AUTHOR}\n"
        f"Exec={exec_line}\n"
        f"Path={archive.parent}\n"
        f"Icon={png}\n"
        "Terminal=true\n"
        "Categories=Office;\n"
    )


def write_linux(desktop: Path, archive: Path, program: str, args: list[str], png: Path) -> Path:
    entry = desktop / f"{NAME}.desktop"
    entry.write_text(desktop_entry(archive, program, args, png), encoding="utf-8")
    entry.chmod(entry.stat().st_mode | 0o111)
    gio = shutil.which("gio")
    if gio:  # a desktop that gates launchers behind a "trusted" mark (GNOME) is told so
        subprocess.run(  # nosec B603 — a fixed program, its own argv, no shell
            [gio, "set", str(entry), "metadata::trusted", "true"],
            capture_output=True,
            timeout=TOOL_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
        )
    return entry


# ── the once-only attempt ─────────────────────────────────────────────────────────────────────


def ensure(*, force: bool = False, skip: bool = False) -> Outcome:
    """Write the Desktop shortcut if this is the first run for this archive (or ``force``);
    ``skip`` writes nothing at all. Never raises: every failure is a sentence in the outcome."""
    if skip:
        return Outcome(False, None, "")
    archive = archive_path()
    if archive is None:
        return Outcome(False, None, f"No Desktop shortcut: {NAME} is not running from {NAME}.pyz.")
    desktop = desktop_dir()
    if desktop is None:
        return Outcome(False, None, "No Desktop shortcut: no Desktop folder was found.")
    marker = data_dir() / MARKER
    try:
        already = marker.read_text(encoding="utf-8").strip() == str(archive)
    except OSError:
        already = False
    if already and not force:
        return Outcome(False, None, "")
    program, args = _interpreter()
    try:
        data = data_dir()
        data.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            ico = desktop_icon.write("lodestar-ico", data / f"{NAME}.ico")
            path = write_windows(desktop, archive, program, args, ico)
        elif sys.platform == "darwin":
            icns = desktop_icon.write("lodestar-icns", data / f"{NAME}.icns")
            path = write_macos(desktop, archive, program, args, icns)
        else:
            png = desktop_icon.write("lodestar-png", data / f"{NAME}.png")
            path = write_linux(desktop, archive, program, args, png)
        marker.write_text(str(archive), encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return Outcome(False, None, f"Desktop shortcut not created: {exc}")
    return Outcome(
        True,
        path,
        f"A Desktop shortcut “{NAME}” was created ({path}) — double-click it to start {NAME} "
        "from now on.",
    )
