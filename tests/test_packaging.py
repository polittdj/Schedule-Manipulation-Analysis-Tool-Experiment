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
    assert "pythonw" in ps1 and "schedule_forensics.launcher" in ps1
    assert "Desktop" in ps1 and ".ico" in ps1  # creates a Desktop shortcut with the icon


def test_icon_is_a_valid_ico() -> None:
    data = (PKG / "windows" / "schedule-forensics.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0 and kind == 1 and count == 1  # ICO header
    width, _h, _c, _r, _planes, bpp, size, offset = struct.unpack("<BBBBHHII", data[6:22])
    assert (width or 256) == 64 and bpp == 32  # 64x64 RGBA
    assert data[offset : offset + 8] == b"\x89PNG\r\n\x1a\n"  # PNG-in-ICO payload
    assert size > 0 and len(data) == offset + size
