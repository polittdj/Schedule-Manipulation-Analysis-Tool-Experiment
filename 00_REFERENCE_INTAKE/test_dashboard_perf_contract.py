"""Packaging artifacts — the desktop shortcuts + the generated icon are present and valid."""

from __future__ import annotations

import struct
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "packaging"


def test_os_shortcuts_present() -> None:
    for rel in (
        "README.md",
        "schedule-forensics.desktop",  # Linux
        "schedule-forensics.command",  # macOS
        "schedule-forensics.bat",  # Windows (console fallback)
        "windows/Install-Desktop-Shortcut.ps1",  # Windows desktop-icon installer
        "windows/Schedule Forensics.vbs",  # Windows no-console launcher
    ):
        assert (PKG / rel).is_file(), f"missing packaging artifact: {rel}"


def test_windows_installer_targets_pythonw_launcher() -> None:
    ps1 = (PKG / "windows" / "Install-Desktop-Shortcut.ps1").read_text()
    assert "pythonw" in ps1 and "-m schedule_forensics" in ps1
    # The shortcut ARGUMENTS must target the guarded package bootstrap `-m schedule_forensics`,
    # NOT the unguarded `-m schedule_forensics.launcher` (a comment may still explain the switch,
    # so assert against the actual assignment line rather than the whole file).
    args_line = next(ln for ln in ps1.splitlines() if "$lnk.Arguments" in ln)
    assert '"-m schedule_forensics"' in args_line
    assert "schedule_forensics.launcher" not in args_line  # the unguarded target is retired
    assert "Desktop" in ps1 and ".ico" in ps1  # creates a Desktop shortcut with the icon


def test_icon_is_a_valid_multi_entry_ico() -> None:
    data = (PKG / "windows" / "schedule-forensics.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0 and kind == 1 and count == 5  # 256/128/64/32/16 entries
    sizes = []
    for i in range(count):
        w, _h, _c, _r, _planes, bpp, size, offset = struct.unpack(
            "<BBBBHHII", data[6 + 16 * i : 22 + 16 * i]
        )
        assert bpp == 32
        assert data[offset : offset + 8] == b"\x89PNG\r\n\x1a\n"  # PNG-in-ICO payload
        assert size > 0 and offset + size <= len(data)
        sizes.append(w or 256)
    assert sizes == [256, 128, 64, 32, 16]


def test_icon_generator_is_deterministic_and_all_copies_are_in_sync() -> None:
    # the committed Windows icon, the Linux PNG, and the served favicon must all be
    # exactly what the generator produces — regenerate-and-commit, never hand-edit
    import sys

    sys.path.insert(0, str(PKG))
    try:
        from make_icon import build_assets  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    ico, png = build_assets()
    ico2, png2 = build_assets()
    assert ico == ico2 and png == png2  # deterministic
    assert (PKG / "windows" / "schedule-forensics.ico").read_bytes() == ico
    assert (PKG / "schedule-forensics.png").read_bytes() == png
    favicon = PKG.parent / "src" / "schedule_forensics" / "web" / "static" / "favicon.ico"
    assert favicon.read_bytes() == ico  # browser tab == desktop icon
