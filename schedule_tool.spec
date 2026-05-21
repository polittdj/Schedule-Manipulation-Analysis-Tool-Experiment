# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds ONE self-contained executable from launch.py.

The end user needs no Python. PyInstaller does NOT cross-compile, so build on the OS you want
the app for (CI does all three automatically — see .github/workflows/build-apps.yml):

    pip install pyinstaller && pyinstaller schedule_tool.spec

Output: dist/ScheduleTool  (dist/ScheduleTool.exe on Windows).
"""

import os

from PyInstaller.utils.hooks import collect_all

# Bundle the Jinja template, and fully collect pydantic (its core is a compiled extension).
datas = [("app/templates", "app/templates")]
binaries = []
hiddenimports = []
for _pkg in ("pydantic", "pydantic_core"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# Optional native-.mpp support: bundle MPXJ + JPype when installed, plus a jlink'd JRE in ./jre
# (the build workflow creates it). When present, the frozen app reads .mpp with no separate Java.
for _pkg in ("mpxj", "jpype"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:  # noqa: S110, BLE001 - package simply absent in a lean build
        pass
if os.path.isdir("jre"):
    datas.append(("jre", "jre"))

a = Analysis(
    ["launch.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "mypy", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ScheduleTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,  # shows the URL and lets the user Ctrl+C / close to stop the tool
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
