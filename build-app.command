#!/bin/bash
# Double-click (macOS / Linux) to BUILD a self-contained app. The result needs no Python to run.
# (PyInstaller does not cross-compile: run this on the OS you want the app for.)

cd "$(dirname "$0")" || exit 1

if [ ! -d ".venv" ]; then
  if command -v python3.13 >/dev/null 2>&1; then PY=python3.13; else PY=python3; fi
  "$PY" -m venv .venv || { echo "Install Python 3.13 first, then try again."; read -r _; exit 1; }
fi

./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/python -m pip install --quiet -r requirements.txt pyinstaller || { echo "Install failed."; read -r _; exit 1; }
./.venv/bin/pyinstaller --noconfirm --clean schedule_tool.spec || { echo "Build failed."; read -r _; exit 1; }

echo
echo "Done! Your app is:  dist/ScheduleTool"
echo "Double-click it to run the tool (no Python needed). You can move it anywhere."
read -r _
