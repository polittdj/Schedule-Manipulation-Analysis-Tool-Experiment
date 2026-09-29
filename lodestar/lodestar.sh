#!/bin/sh
# LODESTAR — One-Pager Studio (Linux). Created by David Politte (david.j.politte@nasa.gov).
# Run: sh lodestar.sh — keep the terminal open while you work; close it to stop.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 LODESTAR.pyz "$@"
fi
echo "LODESTAR needs Python 3.10 or newer, and none was found. Install it from python.org, then double-click LODESTAR again."
read -r _
