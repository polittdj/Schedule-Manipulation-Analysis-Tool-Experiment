#!/usr/bin/env bash
# macOS: double-clickable launcher. Make executable once: chmod +x schedule-forensics.command
# Runs the local dashboard (127.0.0.1) and opens your browser. Nothing leaves the machine.
set -euo pipefail
cd "$(dirname "$0")"
exec schedule-forensics
