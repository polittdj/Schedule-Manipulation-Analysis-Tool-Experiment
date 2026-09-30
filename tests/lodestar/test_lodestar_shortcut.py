"""LODESTAR's first-run Desktop shortcut (ADR-0541): written once, best-effort, with the program's
own icon, and never at all when told not to. Linux is run FOR REAL through the committed
archive (a HOME of its own, a Desktop folder of its own). The Windows ``.lnk`` and the macOS
bundle are written by reading: their writers are held to the format's own rules here — the
PowerShell words, the plist, the launcher script — and stay UNVERIFIED on a real host (no such
host builds this; ADR-0541 says so)."""

from __future__ import annotations

import contextlib
import os
import plistlib
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lodestar.lodestar_probe import request
from schedule_forensics import desktop_icon
from schedule_forensics.lodestar import shortcut

ROOT = Path(__file__).resolve().parents[2]
PYZ = ROOT / "lodestar" / "LODESTAR.pyz"
_RUNNING = re.compile(r"Running at http://127\.0\.0\.1:(\d+)/onepager\b")


# ── the writers, by the format's own rules ───────────────────────────────────────────────────


def test_the_powershell_words_quote_every_path_and_point_the_lnk_at_the_archive(
    tmp_path: Path,
) -> None:
    lnk = tmp_path / "Desktop" / "LODESTAR.lnk"
    archive = tmp_path / "Bob's Files" / "LODESTAR.pyz"
    ico = tmp_path / "LODESTAR.ico"
    script = shortcut.powershell_script(lnk, archive, r"C:\Windows\py.exe", ["-3"], ico)
    assert script.startswith("$s = (New-Object -ComObject WScript.Shell).CreateShortcut('")
    assert f"CreateShortcut('{lnk}')" in script.replace("''", "'")
    assert "$s.TargetPath = 'C:\\Windows\\py.exe';" in script
    # the apostrophe in the folder is doubled — PowerShell's single-quote escape
    assert f"$s.Arguments = '-3 \"{tmp_path}\\Bob''s Files\\LODESTAR.pyz\"'".replace(
        "\\", os.sep
    ) in script.replace("/", os.sep)
    assert f"$s.IconLocation = '{ico},0';" in script and script.endswith("$s.Save()")
    assert "LODESTAR — One-Pager Studio" in script


def test_the_macos_bundle_launches_the_archive_with_the_interpreter_that_made_it(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "My Lists" / "LODESTAR.pyz"
    files = shortcut.bundle_files(archive, "/usr/local/bin/python3", [])
    plist = plistlib.loads(files["Contents/Info.plist"])
    assert (
        plist["CFBundleExecutable"] == "LODESTAR" and plist["CFBundleIconFile"] == "LODESTAR.icns"
    )
    assert plist["CFBundlePackageType"] == "APPL" and plist["CFBundleName"] == "LODESTAR"
    launcher = files["Contents/MacOS/LODESTAR"].decode("utf-8")
    assert launcher.startswith("#!/bin/sh\n")
    assert f"cd '{tmp_path}/My Lists' || exit 1" in launcher
    assert f"exec /usr/local/bin/python3 '{tmp_path}/My Lists/LODESTAR.pyz' \"$@\"" in launcher
    assert files["Contents/PkgInfo"] == b"APPL????"
    # written to a Desktop: the bundle's shape, the launcher executable, the icon in Resources
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    icns = desktop_icon.write("lodestar-icns", tmp_path / "LODESTAR.icns")
    app = shortcut.write_macos(desktop, archive, "/usr/local/bin/python3", [], icns)
    assert app == desktop / "LODESTAR.app"
    assert (app / "Contents" / "MacOS" / "LODESTAR").stat().st_mode & stat.S_IXUSR
    assert (app / "Contents" / "Resources" / "LODESTAR.icns").read_bytes() == icns.read_bytes()


def test_the_desktop_entry_quotes_exec_per_the_specification(tmp_path: Path) -> None:
    archive = tmp_path / 'a "quoted" $dir' / "LODESTAR.pyz"
    png = tmp_path / "LODESTAR.png"
    entry = shortcut.desktop_entry(archive, "/usr/bin/python3", [], png)
    assert entry.startswith("[Desktop Entry]\nType=Application\nName=LODESTAR\n")
    exec_line = next(ln for ln in entry.splitlines() if ln.startswith("Exec="))
    assert exec_line == (f'Exec="/usr/bin/python3" "{tmp_path}/a \\"quoted\\" \\$dir/LODESTAR.pyz"')
    assert f"Icon={png}\n" in entry and "Terminal=true\n" in entry
    assert "Created by David Politte" not in entry and "David Politte" in entry


# ── the once-only attempt, without a desktop ─────────────────────────────────────────────────


def test_ensure_says_why_when_nothing_can_be_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    got = shortcut.ensure(skip=True)
    assert got == shortcut.Outcome(False, None, "")
    monkeypatch.setattr(shortcut, "archive_path", lambda: None)
    assert "not running from LODESTAR.pyz" in shortcut.ensure().note
    monkeypatch.setattr(shortcut, "archive_path", lambda: tmp_path / "LODESTAR.pyz")
    monkeypatch.setattr(shortcut, "desktop_dir", lambda: None)
    got = shortcut.ensure()
    assert not got.made and "no Desktop folder" in got.note
    assert not (tmp_path / "data").exists()  # nothing written when there is nowhere to write


@pytest.mark.skipif(sys.platform != "linux", reason="the Linux writer runs for real on Linux")
def test_ensure_writes_once_and_honours_a_deleted_shortcut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archive = tmp_path / "LODESTAR.pyz"
    archive.write_bytes(b"#!x\n")
    desktop, data = tmp_path / "Desktop", tmp_path / "data"
    desktop.mkdir()
    monkeypatch.setattr(shortcut, "archive_path", lambda: archive)
    monkeypatch.setattr(shortcut, "desktop_dir", lambda: desktop)
    monkeypatch.setattr(shortcut, "data_dir", lambda: data)
    first = shortcut.ensure()
    entry = desktop / "LODESTAR.desktop"
    assert first.made and first.path == entry and "double-click it" in first.note
    assert (data / "shortcut-made.txt").read_text(encoding="utf-8") == str(archive)
    png = data / "LODESTAR.png"
    assert png.read_bytes() == desktop_icon.png_bytes(desktop_icon.lodestar_ico_bytes())
    text = entry.read_text(encoding="utf-8")
    assert f'Exec="{sys.executable}" "{archive}"' in text and f"Icon={png}" in text
    assert entry.stat().st_mode & stat.S_IXUSR
    stamp = entry.stat().st_mtime_ns
    second = shortcut.ensure()  # the marker: nothing written, nothing said
    assert second == shortcut.Outcome(False, None, "") and entry.stat().st_mtime_ns == stamp
    entry.unlink()  # the operator deleted it: it stays deleted
    assert shortcut.ensure() == shortcut.Outcome(False, None, "") and not entry.exists()
    assert shortcut.ensure(force=True).made and entry.exists()  # --shortcut makes it again
    # a different archive is a different first run
    other = tmp_path / "elsewhere" / "LODESTAR.pyz"
    other.parent.mkdir()
    other.write_bytes(b"#!x\n")
    monkeypatch.setattr(shortcut, "archive_path", lambda: other)
    assert shortcut.ensure().made and str(other) in entry.read_text(encoding="utf-8")


def test_a_refusal_from_the_desktop_is_a_sentence_never_a_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archive = tmp_path / "LODESTAR.pyz"
    archive.write_bytes(b"#!x\n")
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(shortcut, "archive_path", lambda: archive)
    monkeypatch.setattr(shortcut, "desktop_dir", lambda: desktop)
    monkeypatch.setattr(shortcut, "data_dir", lambda: tmp_path / "data")

    def refuse(*_a: object, **_k: object) -> Path:
        raise OSError("the Desktop is read-only")

    monkeypatch.setattr(shortcut, "write_linux", refuse)
    monkeypatch.setattr(shortcut, "write_macos", refuse)
    monkeypatch.setattr(shortcut, "write_windows", refuse)
    got = shortcut.ensure()
    assert not got.made and got.note == "Desktop shortcut not created: the Desktop is read-only"
    assert not (tmp_path / "data" / "shortcut-made.txt").exists()  # no marker: tried again next run


# ── the committed archive, for real (Linux) ──────────────────────────────────────────────────


def _run_pyz(work: Path, home: Path, *flags: str) -> tuple[str, str]:
    """Start the committed archive with ``home`` as HOME (and its own XDG folders), wait for the
    banner, stop it with Quit, return ``(stdout, stderr)``."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONSTARTUP", "COVERAGE_PROCESS_START"}
    }
    env.update(
        {
            "HOME": str(home),
            "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_CONFIG_HOME": str(home / ".config"),
        }
    )
    work.mkdir(parents=True, exist_ok=True)
    out, err = work / "out.txt", work / "err.txt"
    with out.open("wb") as fo, err.open("wb") as fe:
        proc = subprocess.Popen(
            [sys.executable, str(PYZ), "--no-browser", *flags],
            cwd=work,
            stdout=fo,
            stderr=fe,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    try:
        port = None
        for _ in range(1200):
            found = _RUNNING.search(out.read_text(encoding="utf-8", errors="replace"))
            if found:
                port = int(found.group(1))
                break
            if proc.poll() is not None:
                break
            time.sleep(0.05)
        assert port is not None, out.read_text(errors="replace") + err.read_text(errors="replace")
        with contextlib.suppress(OSError):
            request(
                port,
                "POST",
                "/quit",
                body=b"",
                headers=[("Content-Type", "application/x-www-form-urlencoded")],
            )
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
    return out.read_text(encoding="utf-8"), err.read_text(encoding="utf-8", errors="replace")


@pytest.mark.skipif(sys.platform != "linux", reason="the Linux writer runs for real on Linux")
def test_the_archives_first_run_puts_the_shortcut_on_the_desktop_and_the_second_does_not(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    out, err = _run_pyz(work, home)
    assert err == "", err
    entry = home / "Desktop" / "LODESTAR.desktop"
    assert "A Desktop shortcut “LODESTAR” was created" in out and str(entry) in out
    text = entry.read_text(encoding="utf-8")
    assert f'Exec="{sys.executable}" "{PYZ}"' in text and "Terminal=true" in text
    png = home / ".local" / "share" / "lodestar" / "LODESTAR.png"
    assert f"Icon={png}" in text and png.is_file()
    w, h, pixels = desktop_icon.png_pixels(png.read_bytes())
    assert (w, h) == (256, 256) and pixels == desktop_icon.lodestar_rgba(256)
    stamp = entry.stat().st_mtime_ns
    out2, err2 = _run_pyz(tmp_path / "work2", home)
    assert err2 == "" and "Desktop shortcut" not in out2 and entry.stat().st_mtime_ns == stamp


@pytest.mark.skipif(sys.platform != "linux", reason="the Linux writer runs for real on Linux")
def test_no_shortcut_writes_nothing_and_no_desktop_folder_is_said(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    work = tmp_path / "work"
    work.mkdir()
    out, err = _run_pyz(work, home, "--no-shortcut")
    assert err == "" and "shortcut" not in out.lower()
    assert list((home / "Desktop").iterdir()) == [] and not (home / ".local").exists()
    bare = tmp_path / "bare"
    bare.mkdir()
    out, err = _run_pyz(tmp_path / "work3", bare)
    assert err == "" and "No Desktop shortcut: no Desktop folder was found." in out
    assert not (bare / ".local").exists()
